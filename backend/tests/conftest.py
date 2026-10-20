"""Pytest configuration and test fixtures for backend test suite."""

import os
import sys
from pathlib import Path
import pytest

# The backend has no built-in default secrets, so the tests supply their own (set before the app is imported).
os.environ.setdefault("SECRET_KEY", "test-jwt-secret-for-unit-tests-only")
os.environ.setdefault("EDGE_API_KEY", "test-edge-api-key")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password-for-unit-tests")
# Isolate tests to a local SQLite database so test fixtures never pollute production DB
os.environ["DATABASE_URL"] = "sqlite:///./test_unit.db"
# Always set (not setdefault): the CORS tests need this exact list, even when the environment defines its own.
os.environ["CORS_ORIGINS"] = "http://localhost:3000,https://*.vercel.app"

# Ensure backend and root workspace are on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(backend_dir.parent) not in sys.path:
    sys.path.insert(0, str(backend_dir.parent))

from database import Base, engine, ensure_detection_event_id_column
import models  # Ensure all ORM models are registered with Base.metadata


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure all SQLAlchemy tables are created for the test session."""
    Base.metadata.create_all(bind=engine)
    try:
        ensure_detection_event_id_column()
    except Exception:
        pass
    yield
