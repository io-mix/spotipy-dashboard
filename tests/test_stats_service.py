import pytest
from unittest.mock import patch, MagicMock
import stats_service
from tests.conftest import MockSessionLocal


@pytest.mark.asyncio
async def test_get_dashboard_stats_empty(db_session):
    # patch the session factory to use our test db
    with patch(
        "stats_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ):
        stats = await stats_service.get_dashboard_stats()

        # verify empty state defaults
        assert stats["total_tracks"] == 0
        assert stats["total_ms"] == 0
        assert len(stats["recent"]) == 0
        assert stats["all_time"]["song"] == "N/A"


@pytest.mark.asyncio
async def test_get_time_machine_count_empty(db_session):
    with patch(
        "stats_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ):
        # mock the engine object to control the 'name' property
        mock_engine = MagicMock()
        mock_engine.name = "sqlite"

        with patch("stats_service.engine", mock_engine):
            count = await stats_service.get_time_machine_count(days=7)
            assert count == 0
