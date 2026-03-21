import os
import pytest
from main import write_health_status, HEALTH_FILE


def test_write_health_status():
    # test docker health check file utility
    test_status = "TEST_OK"

    # ensure directory exists for the test
    os.makedirs(os.path.dirname(HEALTH_FILE), exist_ok=True)

    try:
        write_health_status(test_status)

        assert os.path.exists(HEALTH_FILE)
        with open(HEALTH_FILE, "r") as f:
            assert f.read() == test_status
    finally:
        # cleanup
        if os.path.exists(HEALTH_FILE):
            os.remove(HEALTH_FILE)
