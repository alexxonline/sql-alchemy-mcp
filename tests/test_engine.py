"""Tests for engine creation and management."""

import pytest
from sqlalchemy.pool import StaticPool

from sqlalchemy_mcp_server.engine import DatabaseEngine, get_db, init_db


class TestDatabaseEngine:
    def test_create_engine_sqlite(self):
        db = DatabaseEngine("sqlite://")
        assert db.dialect_name == "sqlite"
        assert db.driver_name == "pysqlite"
        db.dispose()

    def test_create_engine_invalid_url(self):
        with pytest.raises(Exception):
            DatabaseEngine("not-a-valid-url://")

    def test_sqlite_pool_settings(self):
        db = DatabaseEngine("sqlite://")
        pool = db.get_engine().pool
        assert isinstance(pool, StaticPool)
        db.dispose()

    def test_test_connection_fails(self):
        with pytest.raises(RuntimeError, match="Failed to connect"):
            DatabaseEngine("sqlite:////nonexistent/path/to/db.sqlite")

    def test_get_inspector(self):
        db = DatabaseEngine("sqlite://")
        insp = db.get_inspector()
        assert insp.get_table_names() == []
        db.dispose()

    def test_dispose(self):
        db = DatabaseEngine("sqlite://")
        db.dispose()
        # Engine should still be accessible but pool is reset
        assert db.get_engine() is not None


class TestGlobalEngine:
    def test_get_db_before_init(self):
        with pytest.raises(RuntimeError, match="not initialized"):
            get_db()

    def test_init_and_get_db(self):
        db = init_db("sqlite://")
        assert get_db() is db
        assert db.dialect_name == "sqlite"
