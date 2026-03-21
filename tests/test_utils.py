# MIT License
# Copyright (c) 2025

from utils import format_duration, get_utc_date_range, get_data_dir, get_env_path
from datetime import datetime, timezone
import os
import sys
from unittest.mock import patch


def test_format_duration():
    # test zero and none
    assert format_duration(0) == "0h 0m"
    assert format_duration(None) == "0h 0m"

    # test exact minutes
    assert format_duration(60000) == "0h 1m"

    # test hours and minutes
    assert format_duration(3660000) == "1h 1m"


def test_get_utc_date_range_days():
    # test last n days logic
    start, end = get_utc_date_range(days=7)

    assert start is not None
    assert end is None

    # verify it returns naive utc datetime
    assert start.tzinfo is None


def test_get_data_dir_normal():
    # test path resolution when running as a normal script
    with patch.object(sys, "frozen", False, create=True):
        data_dir = get_data_dir()
        assert data_dir.endswith("data")
        # verify it's an absolute path
        assert os.path.isabs(data_dir)


def test_get_data_dir_frozen(tmp_path):
    # test path resolution when running as a bundled exe
    mock_exe = str(tmp_path / "app.exe")
    with patch.object(sys, "frozen", True, create=True), patch.object(
        sys, "executable", mock_exe
    ):
        data_dir = get_data_dir()
        # in frozen mode, data should be next to the exe
        assert data_dir == str(tmp_path / "data")


def test_get_env_path_normal():
    with patch.object(sys, "frozen", False, create=True):
        env_path = get_env_path()
        assert env_path.endswith(".env")
        assert os.path.isabs(env_path)
