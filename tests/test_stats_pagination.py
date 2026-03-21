import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from models import Track, ListeningHistory
import stats_service
from tests.conftest import MockSessionLocal


@pytest.mark.asyncio
async def test_time_machine_pagination(db_session):
    # test offset and limit logic
    mock_engine = MagicMock()
    mock_engine.name = "sqlite"

    with patch(
        "stats_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ), patch("stats_service.engine", mock_engine):

        # insert 15 plays
        t1 = Track(id="t1", name="song", artist_name="art", artist_id="a1")
        db_session.add(t1)

        base_time = datetime(2025, 1, 1, 12, 0, 0)
        for i in range(15):
            db_session.add(
                ListeningHistory(
                    track_id="t1", played_at=base_time - timedelta(minutes=i)
                )
            )
        await db_session.commit()

        # page 1: limit 10
        page1 = await stats_service.get_time_machine_results(limit=10, offset=0)
        assert len(page1) == 10

        # page 2: limit 10 (should get remaining 5)
        page2 = await stats_service.get_time_machine_results(limit=10, offset=10)
        assert len(page2) == 5

        # verify total count
        total = await stats_service.get_time_machine_count()
        assert total == 15
