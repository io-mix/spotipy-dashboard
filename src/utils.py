from datetime import datetime, timedelta, timezone
from strings import STRINGS
import os
import sys


def format_duration(ms):
    if not ms:
        return STRINGS.DASHBOARD.ZERO_TIME
    total_seconds = int(ms / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def get_utc_date_range(days=0, start_date=None, end_date=None):
    if start_date or end_date:
        d1_local = (
            start_date.replace(tzinfo=timezone.utc).astimezone()
            if isinstance(start_date, datetime)
            else start_date
        )
        d2_local = (
            end_date.replace(tzinfo=timezone.utc).astimezone()
            if isinstance(end_date, datetime)
            else end_date
        )
        if d1_local and not d2_local:
            d2_local = d1_local
        if d2_local and not d1_local:
            d1_local = d2_local
        if d1_local > d2_local:
            d1_local, d2_local = d2_local, d1_local

        local_start = datetime(
            d1_local.year, d1_local.month, d1_local.day, 0, 0, 0
        ).astimezone()

        local_end = datetime(
            d2_local.year, d2_local.month, d2_local.day, 23, 59, 59
        ).astimezone()

        start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = local_end.astimezone(timezone.utc).replace(tzinfo=None)
        return start_utc, end_utc

    elif int(days or 0) > 0:
        start_utc = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=int(days)
        )
        return start_utc, None

    return None, None


def get_app_root():
    # returns the absolute path to the project root or the executable directory
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # if running as script, root is one level up from src/
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def resolve_path(path_str):
    # ensures a path is absolute. if relative, resolves it against the app root.
    if os.path.isabs(path_str):
        return path_str
    return os.path.abspath(os.path.join(get_app_root(), path_str))


def get_data_dir():
    # ensures the data directory exists and returns its absolute path
    data_path = resolve_path("data")
    if not os.path.exists(data_path):
        try:
            os.makedirs(data_path, exist_ok=True)
        except Exception:
            pass
    return data_path


def get_env_path():
    return resolve_path(".env")
