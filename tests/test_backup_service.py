import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backup_service import BackupService
from models import Base


# helper to mock AsyncSessionLocal
class MockSessionLocal:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
async def temp_backup_env(tmp_path):
    # setup temporary paths for testing
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    # create a real sqlite file database for the source
    db_file = data_dir / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    engine = create_async_engine(db_url)

    # initialize schema so it's a valid sqlite db
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # mock environment variables to override the new get_data_dir defaults
    env_vars = {
        "BACKUP_ENABLED": "true",
        "DB_TYPE": "sqlite",
        "DB_PATH": str(db_file),
        "BACKUP_DIR": str(backup_dir),
        "BACKUP_COUNT": "2",
        "BACKUP_INTERVAL_HOURS": "0",
        "BACKUP_ON_MANUAL_SYNC": "true",
        "BACKUP_ON_AUTO_SYNC": "true",
    }

    with patch.dict(os.environ, env_vars):
        yield {
            "db_file": db_file,
            "backup_dir": backup_dir,
            "session_factory": session_factory,
            "engine": engine,
        }

    await engine.dispose()


@pytest.mark.asyncio
async def test_backup_creation(temp_backup_env):
    service = BackupService()

    # patch AsyncSessionLocal and ensure the background task runs
    async with temp_backup_env["session_factory"]() as session:
        with patch(
            "backup_service.AsyncSessionLocal", return_value=MockSessionLocal(session)
        ):
            await service.run_backup(reason="test")
            # give the background task time to complete
            await asyncio.sleep(0.5)

    # verify file exists in backup directory
    backups = [
        f for f in os.listdir(temp_backup_env["backup_dir"]) if f.endswith(".db")
    ]
    assert len(backups) == 1
    assert backups[0].startswith("backup_test_")


@pytest.mark.asyncio
async def test_backup_rotation(temp_backup_env):
    service = BackupService()
    backup_dir = temp_backup_env["backup_dir"]

    # run 3 backups (limit is 2)
    async with temp_backup_env["session_factory"]() as session:
        with patch(
            "backup_service.AsyncSessionLocal", return_value=MockSessionLocal(session)
        ):
            # we sleep between backups to ensure unique mtimes for sorting
            await service.run_backup(reason="one")
            await asyncio.sleep(1.1)
            await service.run_backup(reason="two")
            await asyncio.sleep(1.1)
            await service.run_backup(reason="three")
            await asyncio.sleep(0.5)

    # verify only 2 files remain
    backups = [f for f in os.listdir(backup_dir) if f.endswith(".db")]
    assert len(backups) == 2

    # verify the oldest one ("one") was removed
    filenames = "".join(backups)
    assert "one" not in filenames
    assert "two" in filenames
    assert "three" in filenames


@pytest.mark.asyncio
async def test_backup_disabled(temp_backup_env):
    with patch.dict(os.environ, {"BACKUP_ENABLED": "false"}):
        service = BackupService()
        await service.run_backup()

        # verify no files created
        assert len(os.listdir(temp_backup_env["backup_dir"])) == 0


@pytest.mark.asyncio
async def test_backup_non_sqlite(temp_backup_env):
    with patch.dict(os.environ, {"DB_TYPE": "postgres"}):
        service = BackupService()
        await service.run_backup()

        # verify no files created for postgres
        assert len(os.listdir(temp_backup_env["backup_dir"])) == 0
