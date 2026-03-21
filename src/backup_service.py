# MIT License
# Copyright (c) 2025

import os
import asyncio
from datetime import datetime
from sqlalchemy import text
from database import AsyncSessionLocal
from utils import get_data_dir, resolve_path
from strings import STRINGS


class BackupService:
    def __init__(self):
        self.enabled = os.getenv("BACKUP_ENABLED", "false").lower() == "true"
        self.db_type = os.getenv("DB_TYPE", "sqlite").lower()

        data_dir = get_data_dir()

        env_db_path = os.getenv("DB_PATH")
        self.db_path = (
            resolve_path(env_db_path)
            if env_db_path
            else os.path.join(data_dir, "spotify_history.db")
        )

        env_backup_dir = os.getenv("BACKUP_DIR")
        self.backup_dir = (
            resolve_path(env_backup_dir)
            if env_backup_dir
            else os.path.join(data_dir, "backups")
        )

        self.max_backups = int(os.getenv("BACKUP_COUNT", "5"))
        self.on_manual = os.getenv("BACKUP_ON_MANUAL_SYNC", "true").lower() == "true"
        self.on_auto = os.getenv("BACKUP_ON_AUTO_SYNC", "true").lower() == "true"
        self.interval_hours = float(os.getenv("BACKUP_INTERVAL_HOURS", "0"))

    async def run_backup(self, reason="sync"):
        if not self.enabled or self.db_type != "sqlite":
            return

        if not os.path.exists(self.db_path):
            return

        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{reason}_{timestamp}.db"
        dest_path = os.path.abspath(os.path.join(self.backup_dir, filename))

        try:
            # warn the user/logs that this might block db operations
            print(STRINGS.MESSAGES.BACKUP_START.format(path=dest_path))

            # offload the backup execution to a background task to prevent blocking the main event loop
            async def _do_backup():
                try:
                    async with AsyncSessionLocal() as session:
                        await session.execute(text(f"VACUUM INTO '{dest_path}'"))
                        print(STRINGS.MESSAGES.BACKUP_SUCCESS.format(filename=filename))
                    self._rotate_backups()
                except Exception as e:
                    print(STRINGS.MESSAGES.BACKUP_FAILED.format(error=e))

            asyncio.create_task(_do_backup())
        except Exception as e:
            print(STRINGS.MESSAGES.BACKUP_INIT_FAILED.format(error=e))

    def _rotate_backups(self):
        files = [
            os.path.join(self.backup_dir, f)
            for f in os.listdir(self.backup_dir)
            if f.endswith(".db")
        ]
        files.sort(key=os.path.getmtime)
        while len(files) > self.max_backups:
            oldest_file = files.pop(0)
            try:
                os.remove(oldest_file)
                print(
                    STRINGS.MESSAGES.BACKUP_ROTATE.format(
                        filename=os.path.basename(oldest_file)
                    )
                )
            except Exception as e:
                print(STRINGS.MESSAGES.BACKUP_FAILED.format(error=e))
