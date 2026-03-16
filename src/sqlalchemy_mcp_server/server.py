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

    from .tools.read import register_read_tools

    register_read_tools(mcp)

    if config.mode == "readwrite":
        from .tools.write import register_write_tools

        register_write_tools(mcp)

    from .resources import register_resources

    register_resources(mcp, mode=config.mode)

    from .prompts import register_prompts

    register_prompts(mcp)

    return mcp
