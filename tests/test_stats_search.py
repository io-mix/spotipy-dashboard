import pytest
from unittest.mock import patch, MagicMock
from models import Track, ListeningHistory
import stats_service
from tests.conftest import MockSessionLocal
from datetime import datetime


@pytest.mark.asyncio
async def test_time_machine_search_filtering(db_session):
    # verify search filters by track, artist, and album
    mock_engine = MagicMock()
    mock_engine.name = "sqlite"

    with patch(
        "stats_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ), patch("stats_service.engine", mock_engine):

        # setup: 3 different tracks with required artist_id
        t1 = Track(
            id="1",
            name="unique_song",
            artist_name="a",
            artist_id="art1",
            album_name="x",
        )
        t2 = Track(
            id="2",
            name="s",
            artist_name="unique_artist",
            artist_id="art2",
            album_name="y",
        )
        t3 = Track(
            id="3",
            name="s",
            artist_name="a",
            artist_id="art3",
            album_name="unique_album",
        )
        db_session.add_all([t1, t2, t3])

        now = datetime.now()
        db_session.add(ListeningHistory(track_id="1", played_at=now))
        db_session.add(ListeningHistory(track_id="2", played_at=now))
        db_session.add(ListeningHistory(track_id="3", played_at=now))
        await db_session.commit()

        # search by song name
        res = await stats_service.get_time_machine_results(search_query="unique_song")
        assert len(res) == 1
        assert res[0].track.name == "unique_song"

        # search by artist
        res = await stats_service.get_time_machine_results(search_query="unique_artist")
        assert len(res) == 1
        assert res[0].track.artist_name == "unique_artist"

        # search by album
        res = await stats_service.get_time_machine_results(search_query="unique_album")
        assert len(res) == 1
        assert res[0].track.album_name == "unique_album"
