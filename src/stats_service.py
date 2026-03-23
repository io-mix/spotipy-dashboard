from sqlalchemy import func, or_, String, and_, cast, Integer, select, case, delete
from sqlalchemy.orm import joinedload
import asyncio
import json
from datetime import datetime, timedelta, timezone
from database import AsyncSessionLocal, engine
from models import (
    Track,
    ListeningHistory,
    TrackGenre,
    GlobalStat,
    DailyTrackStat,
    DashboardCache,
    DashboardSummary,
)
from utils import get_utc_date_range
from strings import STRINGS

TOP_ITEMS_LIMIT = 10

RECENT_TRACKS_LIMIT = 15

REDISCOVER_NO = 10
REDISCOVER_DAYS_AGO = 30
REDISCOVER_LIMIT = 20


# filter query by UTC date range
def _apply_date_filter(query, start_utc, end_utc):
    if start_utc and end_utc:
        query = query.filter(ListeningHistory.played_at >= start_utc)
        query = query.filter(ListeningHistory.played_at <= end_utc)
    elif start_utc:
        query = query.filter(ListeningHistory.played_at >= start_utc)
    return query


# query with timezone-aware date and search options
def _build_time_machine_query(
    start_utc, end_utc, search_query, dow=None, hour=None, specific_date=None
):
    q = select(ListeningHistory).join(Track)

    # abstract date formatting based on dialect for postgress.
    if engine.name == "postgresql":
        local_played_at = func.timezone("localtime", ListeningHistory.played_at)

        if specific_date:
            q = q.filter(func.to_char(local_played_at, "YYYY-MM-DD") == specific_date)
        else:
            # filter query by UTC date range
            q = _apply_date_filter(q, start_utc, end_utc)

        if dow is not None:
            # postgres EXTRACT(DOW) returns 0-6 (Sun-Sat)
            q = q.filter(
                cast(func.extract("dow", local_played_at), Integer) == int(dow)
            )
        if hour is not None:
            q = q.filter(func.to_char(local_played_at, "HH24") == f"{hour:02d}")

    else:
        # SQLite logic
        local_played_at = func.datetime(ListeningHistory.played_at, "localtime")

        if specific_date:
            q = q.filter(func.strftime("%Y-%m-%d", local_played_at) == specific_date)
        else:
            # filter query by UTC date range
            q = _apply_date_filter(q, start_utc, end_utc)

        if dow is not None:
            q = q.filter(func.strftime("%w", local_played_at) == str(dow))
        if hour is not None:
            q = q.filter(func.strftime("%H", local_played_at) == f"{hour:02d}")

    if search_query:
        search = f"%{search_query}%"
        q = q.filter(
            or_(
                Track.name.ilike(search),
                Track.artist_name.ilike(search),
                Track.album_name.ilike(search),
            )
        )

    return q


# fetch paginated listening history with filters
async def get_time_machine_results(
    days=0,
    start_date=None,
    end_date=None,
    search_query=None,
    offset=0,
    limit=1000,
    dow=None,
    hour=None,
    specific_date=None,
):

    start_utc, end_utc = get_utc_date_range(days, start_date, end_date)
    async with AsyncSessionLocal() as db:
        tm_query = _build_time_machine_query(
            start_utc,
            end_utc,
            search_query,
            dow=dow,
            hour=hour,
            specific_date=specific_date,
        )
        tm_query = tm_query.options(joinedload(ListeningHistory.track))

        result = await db.execute(
            tm_query.order_by(ListeningHistory.played_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()


# count filtered listening history entries
async def get_time_machine_count(
    days=0,
    start_date=None,
    end_date=None,
    search_query=None,
    dow=None,
    hour=None,
    specific_date=None,
):
    start_utc, end_utc = get_utc_date_range(days, start_date, end_date)
    async with AsyncSessionLocal() as db:
        q = _build_time_machine_query(
            start_utc,
            end_utc,
            search_query,
            dow=dow,
            hour=hour,
            specific_date=specific_date,
        )
        q = q.with_only_columns(func.count(ListeningHistory.id))

        res = await db.execute(q)
        return res.scalar() or 0


# query top items by type with grouping and date filtering
async def _get_raw_top_items(
    db, item_type, days=0, start_date=None, end_date=None, limit=TOP_ITEMS_LIMIT
):
    start_utc, end_utc = get_utc_date_range(days, start_date, end_date)

    if item_type == "genres":
        base_q = (
            select(TrackGenre.genre, func.sum(DailyTrackStat.play_count))
            .join(Track, Track.id == TrackGenre.track_id)
            .join(DailyTrackStat, DailyTrackStat.track_id == Track.id)
        )
        group_cols = [TrackGenre.genre]
        order_col = func.sum(DailyTrackStat.play_count).desc()
    elif item_type == "artists":
        base_q = select(Track.artist_name, func.sum(DailyTrackStat.play_count)).join(
            DailyTrackStat, DailyTrackStat.track_id == Track.id
        )
        group_cols = [Track.artist_id, Track.artist_name]
        order_col = func.sum(DailyTrackStat.play_count).desc()
    elif item_type == "albums":
        base_q = select(Track.album_name, func.sum(DailyTrackStat.play_count)).join(
            DailyTrackStat, DailyTrackStat.track_id == Track.id
        )
        group_cols = [Track.album_name, Track.artist_name]
        order_col = func.sum(DailyTrackStat.play_count).desc()
    elif item_type == "songs":
        base_q = select(Track.name, func.sum(DailyTrackStat.play_count)).join(
            DailyTrackStat, DailyTrackStat.track_id == Track.id
        )
        group_cols = [Track.id, Track.name]
        order_col = func.sum(DailyTrackStat.play_count).desc()
    else:
        return []

    if start_utc and end_utc:
        base_q = base_q.filter(DailyTrackStat.date >= start_utc.date())
        base_q = base_q.filter(DailyTrackStat.date <= end_utc.date())
    elif start_utc:
        base_q = base_q.filter(DailyTrackStat.date >= start_utc.date())

    result = await db.execute(
        base_q.group_by(*group_cols).order_by(order_col).limit(limit)
    )
    return result.all()


# get top items and compute ranking trends vs previous period
async def get_top_items_with_trends(
    item_type, days=0, start_date=None, end_date=None, limit=TOP_ITEMS_LIMIT
):
    async with AsyncSessionLocal() as db:
        days_int = int(days or 0)
        if (start_date or end_date) or days_int == 0:
            curr = await _get_raw_top_items(
                db, item_type, days_int, start_date, end_date, limit=limit
            )
            return [(name, count, None) for name, count in curr]

        now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        curr_start = now_utc_naive - timedelta(days=days_int)
        prev_start = now_utc_naive - timedelta(days=days_int * 2)

        curr = await _get_raw_top_items(
            db, item_type, start_date=curr_start, end_date=now_utc_naive, limit=limit
        )
        prev = await _get_raw_top_items(
            db, item_type, start_date=prev_start, end_date=curr_start, limit=limit * 10
        )

        prev_ranks = {name: rank for rank, (name, _) in enumerate(prev)}
        results = []
        for rank, (name, count) in enumerate(curr):
            trend = (
                "NEW"
                if name not in prev_ranks
                else (
                    "UP"
                    if prev_ranks[name] > rank
                    else ("DOWN" if prev_ranks[name] < rank else "SAME")
                )
            )
            results.append((name, count, trend))

        return results


# aggregate listening history by source type and top decades
async def get_music_source_stats(days=0, start_date=None, end_date=None):
    start_utc, end_utc = get_utc_date_range(days, start_date, end_date)
    async with AsyncSessionLocal() as db:
        # use the migrated context_type directly, fallback to Direct for safety
        source_expr = func.coalesce(ListeningHistory.context_type, "Direct")

        base_q = select(source_expr, func.count(ListeningHistory.id)).join(
            Track, Track.id == ListeningHistory.track_id
        )
        # filter query by UTC date range
        base_q = _apply_date_filter(base_q, start_utc, end_utc)
        # sort by count descending to show most used sources first
        context_data = (
            await db.execute(
                base_q.group_by(source_expr).order_by(
                    func.count(ListeningHistory.id).desc()
                )
            )
        ).all()

        # ensure integer division for decades by casting to int before multiplication
        decade_expr = (
            cast((cast(func.substr(Track.release_date, 1, 4), Integer) / 10), Integer)
            * 10
        ).cast(String) + "s"

        base_q2 = (
            select(decade_expr, func.count(ListeningHistory.id))
            .join(ListeningHistory, ListeningHistory.track_id == Track.id)
            .filter(
                and_(Track.release_date != None, func.length(Track.release_date) >= 4)
            )
        )
        # filter query by UTC date range
        base_q2 = _apply_date_filter(base_q2, start_utc, end_utc)
        decade_data = (
            await db.execute(
                base_q2.group_by(decade_expr)
                .order_by(func.count(ListeningHistory.id).desc())
                .limit(5)
            )
        ).all()

        return context_data, decade_data


async def update_dashboard_summary():
    async with AsyncSessionLocal() as db:

        async def get_true_favs(session, start_date=None):
            cutoff = start_date.date() if start_date else None

            # top song
            song_q = select(Track.name).join(DailyTrackStat)
            if cutoff:
                song_q = song_q.filter(DailyTrackStat.date >= cutoff)
            song_q = (
                song_q.group_by(Track.name, Track.artist_name)
                .order_by(func.sum(DailyTrackStat.play_count).desc())
                .limit(1)
            )

            # top artist
            artist_q = select(Track.artist_name).join(DailyTrackStat)
            if cutoff:
                artist_q = artist_q.filter(DailyTrackStat.date >= cutoff)
            artist_q = (
                artist_q.group_by(Track.artist_name)
                .order_by(func.sum(DailyTrackStat.play_count).desc())
                .limit(1)
            )

            # top album
            album_q = select(Track.album_name).join(DailyTrackStat)
            if cutoff:
                album_q = album_q.filter(DailyTrackStat.date >= cutoff)
            album_q = (
                album_q.group_by(Track.album_name, Track.artist_name)
                .order_by(func.sum(DailyTrackStat.play_count).desc())
                .limit(1)
            )

            s_res = await session.execute(song_q)
            ar_res = await session.execute(artist_q)
            al_res = await session.execute(album_q)

            return {
                "song": s_res.scalar() or STRINGS.COMMON.NA,
                "artist": ar_res.scalar() or STRINGS.COMMON.NA,
                "album": al_res.scalar() or STRINGS.COMMON.NA,
            }

        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        fav_all = await get_true_favs(db)
        fav_30 = await get_true_favs(db, now_naive - timedelta(days=30))

        # update all_time (ID 1)
        obj_all = await db.get(DashboardSummary, 1)
        if not obj_all:
            obj_all = DashboardSummary(id=1, time_range="all_time")
            db.add(obj_all)
        obj_all.top_song, obj_all.top_artist, obj_all.top_album = (
            fav_all["song"],
            fav_all["artist"],
            fav_all["album"],
        )
        obj_all.updated_at = datetime.utcnow()

        # update recent_30 (ID 2)
        obj_30 = await db.get(DashboardSummary, 2)
        if not obj_30:
            obj_30 = DashboardSummary(id=2, time_range="recent_30")
            db.add(obj_30)
        obj_30.top_song, obj_30.top_artist, obj_30.top_album = (
            fav_30["song"],
            fav_30["artist"],
            fav_30["album"],
        )
        obj_30.updated_at = datetime.utcnow()

        await db.commit()


# compile dashboard stats including totals, recent tracks, and top favorites
async def get_dashboard_stats():
    async with AsyncSessionLocal() as db:
        # 1. check cache first
        cache_res = await db.execute(select(DashboardCache).limit(1))
        cache_obj = cache_res.scalars().first()
        if cache_obj:
            try:
                cached_data = json.loads(cache_obj.data)
                # fetch recent tracks fresh as they change constantly
                r_res = await db.execute(
                    select(ListeningHistory)
                    .options(joinedload(ListeningHistory.track))
                    .order_by(ListeningHistory.played_at.desc())
                    .limit(RECENT_TRACKS_LIMIT)
                )
                cached_data["recent"] = r_res.scalars().all()
                return cached_data
            except:
                pass

        # 2. recalculate if no cache
        g_res = await db.execute(select(GlobalStat))
        r_res = await db.execute(
            select(ListeningHistory)
            .options(joinedload(ListeningHistory.track))
            .order_by(ListeningHistory.played_at.desc())
            .limit(RECENT_TRACKS_LIMIT)
        )

        sum_res = await db.execute(select(DashboardSummary))
        summaries = sum_res.scalars().all()

        fav_all = {
            "song": STRINGS.COMMON.NA,
            "artist": STRINGS.COMMON.NA,
            "album": STRINGS.COMMON.NA,
        }
        fav_30 = {
            "song": STRINGS.COMMON.NA,
            "artist": STRINGS.COMMON.NA,
            "album": STRINGS.COMMON.NA,
        }

        for s in summaries:
            if s.time_range == "all_time":
                fav_all = {
                    "song": s.top_song,
                    "artist": s.top_artist,
                    "album": s.top_album,
                }
            elif s.time_range == "recent_30":
                fav_30 = {
                    "song": s.top_song,
                    "artist": s.top_artist,
                    "album": s.top_album,
                }

        # if summaries are empty, calculate them
        if not summaries:
            await update_dashboard_summary()
            sum_res = await db.execute(select(DashboardSummary))
            summaries = sum_res.scalars().all()
            for s in summaries:
                if s.time_range == "all_time":
                    fav_all = {
                        "song": s.top_song,
                        "artist": s.top_artist,
                        "album": s.top_album,
                    }
                elif s.time_range == "recent_30":
                    fav_30 = {
                        "song": s.top_song,
                        "artist": s.top_artist,
                        "album": s.top_album,
                    }

        g_stat = g_res.scalars().first()
        total_tracks = g_stat.total_tracks if g_stat else 0
        total_ms = g_stat.total_ms if g_stat else 0
        recent = r_res.scalars().all()

        stats_dict = {
            "total_tracks": total_tracks,
            "total_ms": total_ms,
            "all_time": fav_all,
            "recent_30": fav_30,
        }

        # save to cache (excluding recent tracks objects)
        await db.execute(delete(DashboardCache))
        db.add(DashboardCache(data=json.dumps(stats_dict)))
        await db.commit()

        stats_dict["recent"] = recent
        return stats_dict


async def clear_dashboard_cache():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(DashboardCache))
        await db.commit()


# fetch tracks eligible for rediscovery
async def get_rediscover_tracks():
    async with AsyncSessionLocal() as db:
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        q = (
            select(
                Track,
                Track.play_count.label("play_count"),
                Track.last_played_at.label("last_played"),
            )
            .filter(Track.play_count >= REDISCOVER_NO)
            .filter(
                Track.last_played_at < (now_naive - timedelta(days=REDISCOVER_DAYS_AGO))
            )
            .order_by(Track.play_count.desc())
            .limit(REDISCOVER_LIMIT)
        )
        result = await db.execute(q)
        return result.all()


# generate listening heatmap with counts and top genre
async def get_heatmap_data(days=0, start_date=None, end_date=None, specific_date=None):
    start_utc, end_utc = get_utc_date_range(days, start_date, end_date)
    async with AsyncSessionLocal() as db:
        if engine.name == "postgresql":
            local_played_at = func.timezone("localtime", ListeningHistory.played_at)
            if specific_date:
                slice_expr = func.to_char(local_played_at, "HH24")
            else:
                slice_expr = func.to_char(local_played_at, "YYYY-MM-DD")
        else:
            local_played_at = func.datetime(ListeningHistory.played_at, "localtime")
            if specific_date:
                slice_expr = func.strftime("%H", local_played_at)
            else:
                slice_expr = func.strftime("%Y-%m-%d", local_played_at)

        # 1. fetch counts per slice
        q_counts = select(slice_expr, func.count(ListeningHistory.id))
        if specific_date:
            if engine.name == "postgresql":
                q_counts = q_counts.filter(
                    func.to_char(local_played_at, "YYYY-MM-DD") == specific_date
                )
            else:
                q_counts = q_counts.filter(
                    func.strftime("%Y-%m-%d", local_played_at) == specific_date
                )
        else:
            # filter query by UTC date range
            q_counts = _apply_date_filter(q_counts, start_utc, end_utc)

        res_counts = await db.execute(q_counts.group_by(slice_expr))
        counts = {str(row[0]): row[1] for row in res_counts.all()}

        # 2. fetch top genre per slice using a Window Function
        subq_genres = (
            select(
                slice_expr.label("slice"),
                TrackGenre.genre.label("genre"),
                func.count(ListeningHistory.id).label("cnt"),
            )
            .join(Track, Track.id == TrackGenre.track_id)
            .join(ListeningHistory, ListeningHistory.track_id == Track.id)
        )

        if specific_date:
            if engine.name == "postgresql":
                subq_genres = subq_genres.filter(
                    func.to_char(local_played_at, "YYYY-MM-DD") == specific_date
                )
            else:
                subq_genres = subq_genres.filter(
                    func.strftime("%Y-%m-%d", local_played_at) == specific_date
                )
        else:
            # filter query by UTC date range
            subq_genres = _apply_date_filter(subq_genres, start_utc, end_utc)

        subq_genres = subq_genres.group_by("slice", "genre").subquery()

        # rank genres within each slice by count
        ranked_genres = select(
            subq_genres.c.slice,
            subq_genres.c.genre,
            func.rank()
            .over(partition_by=subq_genres.c.slice, order_by=subq_genres.c.cnt.desc())
            .label("rnk"),
        ).subquery()

        # select only the top ranked genre for each slice
        q_top_genres = select(ranked_genres.c.slice, ranked_genres.c.genre).filter(
            ranked_genres.c.rnk == 1
        )
        res_genres = await db.execute(q_top_genres)

        genres = {str(row[0]): row[1] for row in res_genres.all()}

        # fill in N/A for slices with no genre data
        all_slices = [f"{h:02d}" for h in range(24)] if specific_date else counts.keys()
        for s in all_slices:
            if s not in genres:
                genres[s] = STRINGS.COMMON.NA

        return counts, genres
