"""CLI entry point for the SQLAlchemy MCP Server."""

import argparse
import os
import sys

from .server import ServerConfig, create_server


def parse_args(argv: list[str] | None = None) -> tuple[ServerConfig, list[str] | None]:
    """Parse arguments, returning (config, cli_args).

    cli_args is None when running in server mode, or the remaining
    arguments after --cli when running in CLI mode.
    """
    parser = argparse.ArgumentParser(
        prog="sqlalchemy-mcp-server",
        description="MCP server providing SQL database access through SQLAlchemy",
    )
    parser.add_argument(
        "--db-url",
        default=os.environ.get("SQLALCHEMY_MCP_DB_URL"),
        help=(
            "SQLAlchemy database connection URL "
            "(or set SQLALCHEMY_MCP_DB_URL env var)"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["readonly", "readwrite"],
        default="readonly",
        help="Server mode: readonly (default) or readwrite",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="MCP transport: stdio (default) or http",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)",
    )
    parser.add_argument(
        "--pool-size",
        type=int,
        default=5,
        help="Connection pool size (default: 5)",
    )
    parser.add_argument(
        "--no-pool-pre-ping",
        action="store_true",
        help="Disable connection pre-ping (enabled by default)",
    )
    parser.add_argument(
        "--cli",
        nargs=argparse.REMAINDER,
        default=None,
        help="Run in CLI mode: execute a single command and exit",
    )

    args = parser.parse_args(argv)

    if not args.db_url:
        parser.error(
            "A database URL is required. Use --db-url or set "
            "the SQLALCHEMY_MCP_DB_URL environment variable."
        )

    config = ServerConfig(
        db_url=args.db_url,
        mode=args.mode,
        transport=args.transport,
        port=args.port,
        pool_size=args.pool_size,
        pool_pre_ping=not args.no_pool_pre_ping,
    )

    return config, args.cli


def main(argv: list[str] | None = None) -> None:
    config, cli_args = parse_args(argv)
    mcp = create_server(config)

    if cli_args is not None:
        from .cli import run_cli
        from .engine import get_db

        try:
            run_cli(mcp, cli_args, mode=config.mode)
        finally:
            get_db().dispose()
    else:
        transport_kwargs = {}
        if config.transport == "http":
            transport_kwargs["port"] = config.port

        mcp.run(transport=config.transport, **transport_kwargs)


if __name__ == "__main__":
    main()
