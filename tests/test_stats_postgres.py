import pytest
from unittest.mock import patch, MagicMock
import stats_service
from tests.conftest import MockSessionLocal


@pytest.mark.asyncio
async def test_postgres_query_path_smoke_test(db_session):
    # verify postgres-specific query generation doesn't crash
    # we use sqlite db but force the service to use postgres logic
    mock_engine = MagicMock()
    mock_engine.name = "postgresql"

    with patch(
        "stats_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ), patch("stats_service.engine", mock_engine):

        # this triggers the postgres branch in _build_time_machine_query
        # even if it fails to execute on sqlite, we check it doesn't raise python errors
        try:
            await stats_service.get_time_machine_results(dow=1, hour=12)
        except Exception as e:
            # if it fails because of sqlite vs postgres syntax, that's fine
            # we just want to ensure the python logic for building the query is sound
            assert (
                "no such function: timezone" in str(e).lower()
                or "to_char" in str(e).lower()
            )
