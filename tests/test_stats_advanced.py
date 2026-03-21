import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from models import Track, ListeningHistory, DailyTrackStat, TrackGenre
import stats_service
from tests.conftest import MockSessionLocal


@pytest.mark.asyncio
async def test_get_top_items_with_trends_logic(db_session):
    # setup: mock session and engine
    mock_engine = MagicMock()
    mock_engine.name = "sqlite"

    with patch(
        "stats_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ), patch("stats_service.engine", mock_engine):

        # use a fixed "now" to avoid boundary issues
        now = datetime(2025, 3, 21, 12, 0, 0)

        # patch datetime.now inside the service to match our test "now"
        with patch("stats_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = now.replace(tzinfo=timezone.utc)
            mock_datetime.utcnow.return_value = now
            # ensure other datetime methods still work
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # track 1: trending up (0 plays prev, 10 plays curr)
            t1 = Track(id="t1", name="up", artist_name="a1", artist_id="art1")
            # track 2: trending down (10 plays prev, 5 plays curr)
            t2 = Track(id="t2", name="down", artist_name="a2", artist_id="art2")
            db_session.add_all([t1, t2])

            # prev period (e.g., 10 days ago)
            db_session.add(
                DailyTrackStat(
                    date=(now - timedelta(days=10)).date(), track_id="t2", play_count=10
                )
            )

            # curr period (e.g., 2 days ago)
            db_session.add(
                DailyTrackStat(
                    date=(now - timedelta(days=2)).date(), track_id="t1", play_count=10
                )
            )
            db_session.add(
                DailyTrackStat(
                    date=(now - timedelta(days=1)).date(), track_id="t2", play_count=5
                )
            )

            await db_session.commit()

            # check trends for 7 day window
            results = await stats_service.get_top_items_with_trends("songs", days=7)

            # t1 should be #1 (10 plays) and NEW (since it had 0 in prev window [now-14 to now-7])
            assert results[0][0] == "up"
            assert results[0][1] == 10
            assert results[0][2] == "NEW"

            # t2 should be #2 (5 plays) and DOWN (since it was #1 in prev window)
            assert results[1][0] == "down"
            assert results[1][1] == 5
            assert results[1][2] == "DOWN"


@pytest.mark.asyncio
async def test_get_rediscover_tracks_logic(db_session):
    with patch(
        "stats_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # track a: eligible (15 plays, 40 days ago)
        ta = Track(
            id="ta",
            name="oldie",
            artist_name="a",
            artist_id="art_a",
            play_count=15,
            last_played_at=now - timedelta(days=40),
        )
        # track b: too recent (15 plays, 5 days ago)
        tb = Track(
            id="tb",
            name="recent",
            artist_name="b",
            artist_id="art_b",
            play_count=15,
            last_played_at=now - timedelta(days=5),
        )
        # track c: not enough plays (2 plays, 40 days ago)
        tc = Track(
            id="tc",
            name="rare",
            artist_name="c",
            artist_id="art_c",
            play_count=2,
            last_played_at=now - timedelta(days=40),
        )

        db_session.add_all([ta, tb, tc])
        await db_session.commit()

        forgotten = await stats_service.get_rediscover_tracks()
        assert len(forgotten) == 1
        assert forgotten[0][0].name == "oldie"


@pytest.mark.asyncio
async def test_get_heatmap_data_logic(db_session):
    mock_engine = MagicMock()
    mock_engine.name = "sqlite"

    with patch(
        "stats_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ), patch("stats_service.engine", mock_engine):

        t1 = Track(id="t1", name="s1", artist_name="a1", artist_id="art1")
        db_session.add(t1)
        db_session.add(TrackGenre(track_id="t1", genre="rock"))

        # insert plays at 14:00 UTC
        p1 = ListeningHistory(track_id="t1", played_at=datetime(2025, 1, 1, 14, 0))
        p2 = ListeningHistory(track_id="t1", played_at=datetime(2025, 1, 1, 14, 30))
        db_session.add_all([p1, p2])
        await db_session.commit()

        counts, genres = await stats_service.get_heatmap_data(
            specific_date="2025-01-01"
        )

        # check that the count of 2 exists in the results (ignoring timezone offset)
        assert 2 in counts.values()
        # verify the genre is correctly associated with the hour that has 2 plays
        hour_with_plays = [h for h, c in counts.items() if c == 2][0]
        assert genres.get(hour_with_plays) == "rock"


@pytest.mark.asyncio
async def test_get_music_source_stats_logic(db_session):
    with patch(
        "stats_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ):
        # track from 1985
        t1 = Track(
            id="t1",
            name="80s",
            artist_name="a",
            artist_id="art",
            release_date="1985-01-01",
        )
        # track from 2023
        t2 = Track(
            id="t2",
            name="modern",
            artist_name="b",
            artist_id="art2",
            release_date="2023-05-10",
        )
        db_session.add_all([t1, t2])

        db_session.add(
            ListeningHistory(
                track_id="t1", played_at=datetime.now(), context_type="playlist"
            )
        )
        db_session.add(
            ListeningHistory(
                track_id="t2", played_at=datetime.now(), context_type="album"
            )
        )
        await db_session.commit()

        sources, decades = await stats_service.get_music_source_stats()

        # verify decades grouping (1985 -> 1980s, 2023 -> 2020s)
        decade_names = [d[0] for d in decades]
        assert "1980s" in decade_names
        assert "2020s" in decade_names
