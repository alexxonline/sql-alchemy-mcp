# Iteration 2: Engine Management

## Goal

Implement the SQLAlchemy engine creation and connection management layer that all tools will use.

## Tasks

### 2.1 Implement `engine.py`

This module manages the SQLAlchemy engine lifecycle.

**Core class: `DatabaseEngine`**

```python
class DatabaseEngine:
    """Manages a SQLAlchemy engine and provides connection utilities."""

    def __init__(self, db_url: str, pool_size: int = 5, pool_pre_ping: bool = True):
        ...

    def connect(self) -> Connection:
        """Return a context-manager connection."""
        ...

    def get_engine(self) -> Engine:
        """Return the underlying engine."""
        ...

    def get_inspector(self) -> Inspector:
        """Return a fresh Inspector for introspection."""
        ...

    def dispose(self) -> None:
        """Dispose of the engine and connection pool."""
        ...
```

**Engine creation details:**

```python
from sqlalchemy import create_engine, inspect

engine = create_engine(
    db_url,
    pool_size=pool_size,       # ignored for SQLite (uses StaticPool/NullPool)
    pool_pre_ping=pool_pre_ping,
    echo=False,                # could be a debug flag later
)
```

**Important considerations:**

- SQLite uses `StaticPool` or `NullPool` by default; don't pass `pool_size` for SQLite URLs.
- Detect SQLite URLs (`db_url.startswith("sqlite")`) and adjust engine kwargs accordingly.
- The engine should be created lazily or at server start, not on import.

### 2.2 Connection URL validation

Before creating the engine, validate the URL:

1. Use `sqlalchemy.engine.make_url()` to parse and validate the URL format.
2. Attempt a test connection on startup (`engine.connect()`) and raise a clear error if it fails.
3. Surface the dialect name (e.g., "postgresql", "sqlite") for logging.

### 2.3 Wire engine into server

Update `server.py` to:

1. Create a `DatabaseEngine` instance from the config.
2. Store it so tools can access it (module-level or via FastMCP's dependency injection).

**Pattern for tool access:**

Tools access the engine via a module-level reference set during server creation:

```python
# engine.py
_db_engine: DatabaseEngine | None = None

def get_db() -> DatabaseEngine:
    """Get the active database engine. Raises if not initialized."""
    if _db_engine is None:
        raise RuntimeError("Database engine not initialized")
    return _db_engine

def init_db(db_url: str, **kwargs) -> DatabaseEngine:
    """Initialize the database engine."""
    global _db_engine
    _db_engine = DatabaseEngine(db_url, **kwargs)
    return _db_engine
```

## Acceptance Criteria

- [ ] `DatabaseEngine` can be instantiated with any valid SQLAlchemy URL
- [ ] SQLite URLs are detected and pool settings adjusted automatically
- [ ] Invalid URLs raise a clear error at startup (not later when a tool runs)
- [ ] A test connection is made on initialization to verify connectivity
- [ ] `get_db()` provides global access to the engine for tools
- [ ] `dispose()` cleanly shuts down the connection pool
