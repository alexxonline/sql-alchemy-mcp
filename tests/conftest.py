"""Shared test fixtures."""

import pytest
from sqlalchemy import text

import sqlalchemy_mcp_server.engine as engine_module
from sqlalchemy_mcp_server.engine import DatabaseEngine, init_db
from sqlalchemy_mcp_server.server import ServerConfig, create_server


@pytest.fixture(autouse=True)
def _reset_engine():
    """Reset the global engine before each test."""
    engine_module._db_engine = None
    yield
    if engine_module._db_engine is not None:
        engine_module._db_engine.dispose()
        engine_module._db_engine = None


@pytest.fixture
def sample_db():
    """Initialize global engine with an in-memory SQLite database with sample data."""
    db = init_db("sqlite://")
    with db.connect() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
            )
        )
        conn.execute(
            text(
                """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                amount DECIMAL(10,2),
                status TEXT DEFAULT 'pending'
            )
        """
            )
        )
        conn.execute(
            text("INSERT INTO users (id, name, email) VALUES (:id, :name, :email)"),
            [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
            ],
        )
        conn.execute(
            text(
                "INSERT INTO orders (id, user_id, amount, status) "
                "VALUES (:id, :uid, :amt, :st)"
            ),
            [
                {"id": 1, "uid": 1, "amt": 99.99, "st": "completed"},
                {"id": 2, "uid": 1, "amt": 49.50, "st": "pending"},
                {"id": 3, "uid": 2, "amt": 150.00, "st": "completed"},
            ],
        )
        conn.commit()
    return db


@pytest.fixture
def readonly_server(sample_db):
    """Create a FastMCP server in readonly mode with sample data."""
    engine_module._db_engine = sample_db
    config = ServerConfig(db_url="sqlite://", mode="readonly")
    # Skip init_db inside create_server since we already have the engine
    from fastmcp import FastMCP

    from sqlalchemy_mcp_server.prompts import register_prompts
    from sqlalchemy_mcp_server.resources import register_resources
    from sqlalchemy_mcp_server.tools.read import register_read_tools

    mcp = FastMCP("Test Server")
    register_read_tools(mcp)
    register_resources(mcp, mode="readonly")
    register_prompts(mcp)
    return mcp


@pytest.fixture
def readwrite_server(sample_db):
    """Create a FastMCP server in readwrite mode with sample data."""
    engine_module._db_engine = sample_db
    from fastmcp import FastMCP

    from sqlalchemy_mcp_server.prompts import register_prompts
    from sqlalchemy_mcp_server.resources import register_resources
    from sqlalchemy_mcp_server.tools.read import register_read_tools
    from sqlalchemy_mcp_server.tools.write import register_write_tools

    mcp = FastMCP("Test Server")
    register_read_tools(mcp)
    register_write_tools(mcp)
    register_resources(mcp, mode="readwrite")
    register_prompts(mcp)
    return mcp
