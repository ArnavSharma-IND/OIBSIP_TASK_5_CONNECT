"""
Pytest configuration and shared fixtures.
"""

import os
import tempfile
import pytest
from server.config import ServerConfig
from server.database import DatabaseManager


@pytest.fixture
def temp_db_path():
    """Provides a temporary path for an isolated test database."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_connect_")
    os.close(fd)
    yield path
    # Cleanup after test
    for ext in ("", "-wal", "-shm"):
        p = path + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


@pytest.fixture
def db(temp_db_path):
    """Initializes and returns a DatabaseManager instance with an isolated database."""
    manager = DatabaseManager(db_path=temp_db_path, default_room="general")
    return manager


@pytest.fixture
def test_server_config(temp_db_path):
    """Provides an isolated ServerConfig with low iteration count for fast tests."""
    return ServerConfig(
        host="127.0.0.1",
        port=0,  # Will bind dynamically to free port in tests
        db_path=temp_db_path,
        default_room="general",
        pbkdf2_iterations=1_000,  # Reduced iterations for fast test execution
        client_timeout=5.0
    )
