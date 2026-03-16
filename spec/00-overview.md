# SQLAlchemy MCP Server - Project Overview

## Vision

A Model Context Protocol (MCP) server built with [FastMCP](https://gofastmcp.com) that exposes SQLAlchemy-powered database operations as MCP tools and resources. It supports **any database engine supported by SQLAlchemy** (SQLite, PostgreSQL, MySQL, Oracle, MSSQL, and 60+ external dialects) and operates in either **read-only** or **read-write** mode controlled via a command-line argument.

## Architecture

```
┌──────────────────────────────────────────────┐
│              MCP Client (LLM)                │
└──────────────┬───────────────────────────────┘
               │ MCP Protocol (stdio / http)
┌──────────────▼───────────────────────────────┐
│         FastMCP Server Layer                 │
│  ┌─────────┐ ┌───────────┐ ┌──────────────┐ │
│  │  Tools  │ │ Resources │ │   Prompts    │ │
│  └────┬────┘ └─────┬─────┘ └──────┬───────┘ │
│       └─────────┬──┘              │          │
│          ┌──────▼──────┐          │          │
│          │  DB Engine  │◄─────────┘          │
│          │  (service)  │                     │
│          └──────┬──────┘                     │
│          ┌──────▼──────┐                     │
│          │ SQLAlchemy  │                     │
│          │   Engine    │                     │
│          └──────┬──────┘                     │
└─────────────────┼────────────────────────────┘
                  │
       ┌──────────▼──────────┐
       │   Any SQL Database  │
       │  (SQLite, PG, etc.) │
       └─────────────────────┘
```

## Key Design Decisions

1. **SQLAlchemy Core only** - No ORM. We use `text()` for raw SQL and `inspect()` / `MetaData.reflect()` for introspection. This keeps it simple and universal across all dialects.
2. **Mode enforcement** - A `--mode readonly|readwrite` CLI flag controls which tools are exposed. In read-only mode, write tools are not registered at all (not just disabled).
3. **Generic dialect support** - The connection URL is the only required config. Any valid SQLAlchemy URL works. Dialect-specific drivers are the user's responsibility to install.
4. **FastMCP framework** - Uses decorators for tool/resource/prompt registration, async support, and built-in MCP protocol handling.

## Technology Stack

| Component       | Technology         | Version   |
|-----------------|--------------------|-----------|
| Runtime         | Python             | >= 3.10   |
| MCP Framework   | FastMCP            | >= 2.0    |
| DB Toolkit      | SQLAlchemy         | >= 2.0    |
| Packaging       | uv / pip           | latest    |

## Project Structure (Target)

```
sqlalchemy-mcp-server/
├── pyproject.toml
├── README.md
├── src/
│   └── sqlalchemy_mcp_server/
│       ├── __init__.py
│       ├── __main__.py          # Entry point with CLI arg parsing
│       ├── server.py            # FastMCP server setup & tool registration
│       ├── engine.py            # SQLAlchemy engine creation & management
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── read.py          # Read-only tools (query, inspect, etc.)
│       │   └── write.py         # Write tools (execute, insert, etc.)
│       ├── resources.py         # MCP resources (schema info, etc.)
│       └── prompts.py           # MCP prompts (SQL help, etc.)
├── tests/
│   ├── conftest.py
│   ├── test_engine.py
│   ├── test_read_tools.py
│   ├── test_write_tools.py
│   └── test_resources.py
└── spec/                        # This planning directory
```

## Implementation Iterations

| Iteration | Spec File                        | Description                                      |
|-----------|----------------------------------|--------------------------------------------------|
| 1         | [01-project-setup.md](01-project-setup.md)             | Project scaffolding, packaging, CLI entry point   |
| 2         | [02-engine-management.md](02-engine-management.md)     | SQLAlchemy engine creation and connection management |
| 3         | [03-read-tools.md](03-read-tools.md)                   | Read-only MCP tools (query, introspection)        |
| 4         | [04-write-tools.md](04-write-tools.md)                 | Write MCP tools (execute, DDL, DML)               |
| 5         | [05-resources-and-prompts.md](05-resources-and-prompts.md) | MCP resources and prompts                     |
| 6         | [06-testing.md](06-testing.md)                         | Testing strategy and test implementation          |
| 7         | [07-packaging-and-distribution.md](07-packaging-and-distribution.md) | Packaging, README, and distribution   |
| 8         | [08-cli-mode.md](08-cli-mode.md)                                     | CLI mode for one-shot command execution |
