import os
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv
from models import Base
from utils import get_data_dir, get_env_path, resolve_path

load_dotenv(get_env_path())


def get_engine():
    db_type = os.getenv("DB_TYPE", "sqlite").lower()

    if db_type == "postgres":
        user = os.getenv("DB_USER")
        pw = os.getenv("DB_PASSWORD")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME")
        url = f"postgresql+asyncpg://{user}:{pw}@{host}:{port}/{db_name}"
        connect_args = {}
    else:
        env_db_path = os.getenv("DB_PATH")
        if env_db_path:
            db_path = resolve_path(env_db_path)
        else:
            db_path = os.path.join(get_data_dir(), "spotify_history.db")

        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        url = f"sqlite+aiosqlite:///{db_path}"
        # allow SQLite to wait for locks (e.g., during backups)
        connect_args = {"check_same_thread": False, "timeout": 15}

    engine = create_async_engine(url, connect_args=connect_args)

    if db_type == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            # reduce disk sync frequency for faster writes
            cursor.execute("PRAGMA synchronous=NORMAL")
            # increase cache size to 64mb for faster lookups
            cursor.execute("PRAGMA cache_size=-64000")
            # memory map the database for near-instant cold starts
            cursor.execute("PRAGMA mmap_size=268435456")
            cursor.close()

    return engine


engine = get_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    # perform schema creation in a way that doesn't block the main thread
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
