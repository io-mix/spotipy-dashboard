import os
import asyncio
from datetime import datetime, timezone, timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheFileHandler
from sqlalchemy import select, and_, or_
from models import Track, ListeningHistory, TrackGenre, GlobalStat, DailyTrackStat
from database import AsyncSessionLocal
from strings import STRINGS
from utils import get_data_dir


GENRES_NO = 1
SYNC_DUPLICATE_THRESHOLD = 0.95
SKIP_THRESHOLD = 0.5


class SpotifyService:
    def __init__(self):
        scope = "user-read-recently-played,user-read-currently-playing"

        cache_path = os.path.join(get_data_dir(), ".cache")

        self.auth_manager = SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
            scope=scope,
            cache_handler=CacheFileHandler(cache_path=cache_path),
            open_browser=False,
        )
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
        # lock to prevent overlapping syncs and token cache corruption
        self._sync_lock = asyncio.Lock()

        # threshold for filtering out duplicate/ghost logs
        self.duplicate_threshold = float(SYNC_DUPLICATE_THRESHOLD)

    def get_auth_url(self):
        return self.auth_manager.get_authorize_url()

    def complete_auth(self, redirected_url):
        code = self.auth_manager.parse_response_code(redirected_url)
        if code:
            self.auth_manager.get_access_token(code)
            return True
        return False

    def is_authenticated(self):
        # non blocking check for cached token
        return self.auth_manager.cache_handler.get_cached_token() is not None

    async def validate_auth(self):
        try:
            await asyncio.to_thread(self.sp.current_user)
            return True
        except Exception:
            return False

    async def sync_recently_played(self):
        async with self._sync_lock:
            # prevent spotipy from blocking the terminal on a fresh start
            if not self.is_authenticated():
                raise Exception(STRINGS.MESSAGES.AUTH_REQUIRED_KEY)

            async with AsyncSessionLocal() as db:
                try:
                    # Phase 1: parallelize spotify network call and initial db lookups
                    # we also fetch currently playing to help validate the last track in the batch
                    results, g_stat_result, current_playing = await asyncio.gather(
                        asyncio.to_thread(
                            self.sp.current_user_recently_played, limit=50
                        ),
                        db.execute(select(GlobalStat)),
                        asyncio.to_thread(self.sp.current_user_playing_track),
                    )

                    items = results.get("items", [])
                    if not items:
                        return 0

                    # sort items chronologically (oldest first) to properly calculate time deltas
                    items.sort(key=lambda x: x["played_at"])

                    # prepare identifiers for bulk lookups
                    incoming_track_ids = {item["track"]["id"] for item in items}
                    incoming_artist_ids = {
                        item["track"]["artists"][0]["id"] for item in items
                    }

                    # calculate start times immediately for all incoming items
                    processed_items = []
                    for i, item in enumerate(items):
                        end_ts = datetime.strptime(
                            item["played_at"][:19], "%Y-%m-%dT%H:%M:%S"
                        )
                        duration_ms = item["track"]["duration_ms"]

                        # subtract duration and truncate microseconds for stable duplicate checking
                        start_ts = end_ts - timedelta(milliseconds=duration_ms)
                        start_ts = start_ts.replace(microsecond=0)

                        # Look-ahead skip detection:
                        is_skipped = False
                        if i < len(items) - 1:
                            # compare to the next track in the batch
                            next_end_ts = datetime.strptime(
                                items[i + 1]["played_at"][:19], "%Y-%m-%dT%H:%M:%S"
                            )
                            next_duration_ms = items[i + 1]["track"]["duration_ms"]
                            next_start_ts = next_end_ts - timedelta(
                                milliseconds=next_duration_ms
                            )

                            gap_seconds = (next_start_ts - start_ts).total_seconds()
                            if gap_seconds < (duration_ms / 1000.0) * SKIP_THRESHOLD:
                                is_skipped = True
                        elif current_playing and current_playing.get("item"):
                            # for the last track, compare to what is playing right now
                            # if the gap is too small, the user likely skipped the last track to play the current one
                            curr_item = current_playing["item"]
                            if curr_item["id"] != item["track"]["id"]:
                                now_ts = datetime.now(timezone.utc).replace(tzinfo=None)
                                gap_to_now = (now_ts - start_ts).total_seconds()
                                if gap_to_now < (duration_ms / 1000.0) * SKIP_THRESHOLD:
                                    is_skipped = True

                        if not is_skipped:
                            processed_items.append(
                                {
                                    "raw": item,
                                    "start_ts": start_ts,
                                    "track_id": item["track"]["id"],
                                    "duration_ms": duration_ms,
                                }
                            )

                    if not processed_items:
                        return 0

                    incoming_timestamps = [i["start_ts"] for i in processed_items]
                    min_ts, max_ts = min(incoming_timestamps), max(incoming_timestamps)
                    daily_dates = {ts.date() for ts in incoming_timestamps}

                    # Phase 2: parallelize artist metadata fetch and all bulk db checks
                    # optimization: only fetch artists that don't have genres in our Track table yet
                    tracks_task = db.execute(
                        select(Track).filter(Track.id.in_(incoming_track_ids))
                    )

                    history_task = db.execute(
                        select(
                            ListeningHistory.played_at, ListeningHistory.track_id
                        ).filter(
                            ListeningHistory.played_at.between(
                                min_ts - timedelta(minutes=10),
                                max_ts + timedelta(minutes=10),
                            )
                        )
                    )

                    daily_task = db.execute(
                        select(DailyTrackStat).filter(
                            and_(
                                DailyTrackStat.date.between(
                                    min(daily_dates), max(daily_dates)
                                ),
                                DailyTrackStat.track_id.in_(incoming_track_ids),
                            )
                        )
                    )

                    existing_tracks_res, existing_records_res, existing_daily_res = (
                        await asyncio.gather(tracks_task, history_task, daily_task)
                    )

                    # map results for O(1) access in the loop
                    track_map = {t.id: t for t in existing_tracks_res.scalars().all()}

                    # optimization: identify artists needing genre info
                    missing_genre_artist_ids = set()
                    for p_item in processed_items:
                        t_id = p_item["track_id"]
                        if t_id not in track_map or not track_map[t_id].genres:
                            missing_genre_artist_ids.add(
                                p_item["raw"]["track"]["artists"][0]["id"]
                            )

                    artist_genres_map = {}
                    if missing_genre_artist_ids:
                        artists_data = await asyncio.to_thread(
                            self.sp.artists, list(missing_genre_artist_ids)[:50]
                        )
                        artist_genres_map = {
                            a["id"]: a.get("genres", [])
                            for a in artists_data["artists"]
                            if a
                        }

                    # fetch all history in the window to perform fuzzy duplicate detection
                    existing_history = existing_records_res.fetchall()
                    daily_stat_map = {
                        (ds.date, ds.track_id): ds
                        for ds in existing_daily_res.scalars().all()
                    }

                    # fetch or create global stats
                    g_stat = g_stat_result.scalars().first()
                    if not g_stat:
                        g_stat = GlobalStat(total_tracks=0, total_ms=0)
                        db.add(g_stat)

                    new_entries_count = 0
                    added_ms = 0
                    daily_stats_batch = {}  # (date, track_id) -> count
                    unique_genres_to_merge = set()
                    history_entries_to_add = []
                    batch_added_pairs = set()

                    for p_item in processed_items:
                        played_at = p_item["start_ts"]
                        t_id = p_item["track_id"]
                        duration_ms = p_item["duration_ms"]

                        # 1. Bulletproof Duplicate Check (Fuzzy Match)
                        is_duplicate = False
                        for ex_ts, ex_tid in existing_history:
                            if ex_tid == t_id:
                                if (
                                    abs((ex_ts - played_at).total_seconds())
                                    < (duration_ms / 1000.0) * 0.9
                                ):
                                    is_duplicate = True
                                    break

                        for ba_ts, ba_tid in batch_added_pairs:
                            if (
                                ba_tid == t_id
                                and abs((ba_ts - played_at).total_seconds())
                                < (duration_ms / 1000.0) * 0.9
                            ):
                                is_duplicate = True
                                break

                        if is_duplicate:
                            continue

                        # --- ALL UPDATES HAPPEN BELOW THIS LINE ---
                        track_data = p_item["raw"]["track"]
                        artist_id = track_data["artists"][0]["id"]
                        p_date = played_at.date()

                        # update daily stats batch
                        key = (p_date, t_id)
                        daily_stats_batch[key] = daily_stats_batch.get(key, 0) + 1

                        # update or create track
                        db_track = track_map.get(t_id)
                        if not db_track:
                            genres_list = artist_genres_map.get(artist_id, [])
                            db_track = Track(
                                id=t_id,
                                name=track_data["name"],
                                artist_name=track_data["artists"][0]["name"],
                                artist_id=artist_id,
                                album_name=track_data["album"]["name"],
                                image_url=(
                                    track_data["album"]["images"][0]["url"]
                                    if track_data["album"]["images"]
                                    else None
                                ),
                                duration_ms=duration_ms,
                                release_date=track_data["album"]["release_date"],
                                genres=",".join(genres_list),
                                play_count=1,
                                last_played_at=played_at,
                            )
                            db.add(db_track)
                            track_map[t_id] = db_track

                            # queue genres for merging if it's a brand new track
                            for g_name in genres_list[:GENRES_NO]:
                                unique_genres_to_merge.add((t_id, g_name))
                        else:
                            db_track.play_count += 1
                            if (
                                not db_track.last_played_at
                                or played_at > db_track.last_played_at
                            ):
                                db_track.last_played_at = played_at

                        # refined music source categorization
                        context = p_item["raw"].get("context")
                        uri = (context or {}).get("uri", "")
                        ctype = (context or {}).get("type")

                        if not context:
                            final_source = "Direct"
                        elif "radio" in uri or "station" in uri:
                            final_source = "Radio & Autoplay"
                        elif ctype == "collection":
                            final_source = "Liked Songs"
                        elif ctype == "artist":
                            final_source = "Artist Profile"
                        elif ctype == "album":
                            final_source = "Album"
                        elif ctype == "playlist":
                            if "37i9dQZF" in uri:
                                final_source = "Spotify Playlists"
                            else:
                                final_source = "User Playlists"
                        else:
                            final_source = ctype.capitalize() if ctype else "Direct"

                        history_entry = ListeningHistory(
                            played_at=played_at,
                            track_id=t_id,
                            context_type=final_source,
                            context_uri=uri,
                        )

                        history_entries_to_add.append(history_entry)
                        batch_added_pairs.add((played_at, t_id))
                        added_ms += duration_ms
                        new_entries_count += 1

                    if unique_genres_to_merge:
                        conds = [
                            and_(TrackGenre.track_id == t, TrackGenre.genre == g)
                            for t, g in unique_genres_to_merge
                        ]
                        existing_genres_res = await db.execute(
                            select(TrackGenre.track_id, TrackGenre.genre).filter(
                                or_(*conds)
                            )
                        )
                        existing_genres = set(existing_genres_res.fetchall())
                        new_genres = [
                            TrackGenre(track_id=t, genre=g)
                            for t, g in unique_genres_to_merge
                            if (t, g) not in existing_genres
                        ]
                        if new_genres:
                            db.add_all(new_genres)

                    # batch add history entries
                    if history_entries_to_add:
                        db.add_all(history_entries_to_add)

                    # update global stats once
                    g_stat.total_tracks += new_entries_count
                    g_stat.total_ms += added_ms

                    # update daily stats using the pre-fetched map (no more N+1 queries)
                    for (d, tid), count in daily_stats_batch.items():
                        ds_obj = daily_stat_map.get((d, tid))
                        if ds_obj:
                            ds_obj.play_count += count
                        else:
                            db.add(
                                DailyTrackStat(date=d, track_id=tid, play_count=count)
                            )

                    # perform a single batch commit for all new entries
                    if new_entries_count > 0:
                        await db.commit()

                    return new_entries_count

                except Exception as e:
                    await db.rollback()
                    if "token" in str(e).lower() or "auth" in str(e).lower():
                        # trigger re-auth flow
                        raise Exception(STRINGS.MESSAGES.AUTH_REQUIRED_KEY)
                    print(STRINGS.MESSAGES.SYNC_ERROR_PREFIX.format(error=e))
                    return 0

    async def get_current_track(self):
        if not self.is_authenticated():
            return None

        try:
            return await asyncio.to_thread(self.sp.current_user_playing_track)
        except Exception as e:
            print(f"Error fetching current track: {e}")
            return None
