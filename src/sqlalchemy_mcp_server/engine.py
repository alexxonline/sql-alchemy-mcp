"""SQLAlchemy engine creation and management."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine, Inspector, make_url


class DatabaseEngine:
    """Manages a SQLAlchemy engine and provides connection utilities."""

    def __init__(self, db_url: str, pool_size: int = 5, pool_pre_ping: bool = True):
        url = make_url(db_url)
        self.dialect_name = url.get_backend_name()
        self.driver_name = url.get_driver_name()

        kwargs: dict = {
            "pool_pre_ping": pool_pre_ping,
            "echo": False,
        }

        # SQLite doesn't support pool_size (uses StaticPool/NullPool)
        if self.dialect_name != "sqlite":
            kwargs["pool_size"] = pool_size

        self._engine: Engine = create_engine(url, **kwargs)

        # Test connectivity at startup
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            self._engine.dispose()
            raise RuntimeError(
                f"Failed to connect to database ({self.dialect_name}): {exc}"
            ) from exc

    def connect(self) -> Connection:
        """Return a context-manager connection."""
        return self._engine.connect()

    def get_engine(self) -> Engine:
        """Return the underlying engine."""
        return self._engine

    def get_inspector(self) -> Inspector:
        """Return a fresh Inspector for introspection."""
        return inspect(self._engine)

    def dispose(self) -> None:
        """Dispose of the engine and connection pool."""
        self._engine.dispose()


_db_engine: DatabaseEngine | None = None


def get_db() -> DatabaseEngine:
    """Get the active database engine. Raises if not initialized."""
    if _db_engine is None:
        raise RuntimeError("Database engine not initialized")
    return _db_engine


def init_db(db_url: str, **kwargs) -> DatabaseEngine:
    """Initialize the global database engine."""
    global _db_engine
    _db_engine = DatabaseEngine(db_url, **kwargs)
    return _db_engine
