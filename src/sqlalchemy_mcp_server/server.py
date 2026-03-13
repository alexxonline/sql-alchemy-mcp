"""FastMCP server creation and configuration."""

from dataclasses import dataclass

from fastmcp import FastMCP


@dataclass
class ServerConfig:
    """Configuration for the SQLAlchemy MCP Server."""

    db_url: str
    mode: str = "readonly"
    transport: str = "stdio"
    port: int = 8000
    pool_size: int = 5
    pool_pre_ping: bool = True


def create_server(config: ServerConfig) -> FastMCP:
    """Create and configure a FastMCP server instance.

    Args:
        config: Server configuration from CLI arguments.

    Returns:
        A configured FastMCP server instance.
    """
    from .engine import init_db

    init_db(
        db_url=config.db_url,
        pool_size=config.pool_size,
        pool_pre_ping=config.pool_pre_ping,
    )

    mcp = FastMCP("SQLAlchemy MCP Server")

    # Read tools will be registered in iteration 3
    # Write tools will be registered in iteration 4 (readwrite mode only)
    # Resources and prompts will be added in iteration 5

    return mcp
