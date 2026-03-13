# Iteration 1: Project Setup

## Goal

Create the project scaffolding with proper Python packaging, CLI entry point, and dependency management.

## Tasks

### 1.1 Initialize the project with `pyproject.toml`

Create a `pyproject.toml` with:

```toml
[project]
name = "sqlalchemy-mcp-server"
version = "0.1.0"
description = "An MCP server providing SQL database access through SQLAlchemy"
requires-python = ">=3.10"
dependencies = [
    "fastmcp>=2.0",
    "sqlalchemy>=2.0",
]

[project.optional-dependencies]
postgresql = ["psycopg2-binary"]
mysql = ["pymysql"]
oracle = ["oracledb"]
mssql = ["pyodbc"]
all = [
    "psycopg2-binary",
    "pymysql",
    "oracledb",
    "pyodbc",
]
dev = [
    "pytest>=7.0",
    "pytest-asyncio",
]

[project.scripts]
sqlalchemy-mcp-server = "sqlalchemy_mcp_server.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 1.2 Create package structure

Create the directory layout:

```
src/sqlalchemy_mcp_server/
├── __init__.py       # Package version and metadata
├── __main__.py       # CLI entry point
├── server.py         # FastMCP server creation (stub)
├── engine.py         # Engine management (stub)
├── tools/
│   ├── __init__.py
│   ├── read.py       # (stub)
│   └── write.py      # (stub)
├── resources.py      # (stub)
└── prompts.py        # (stub)
```

### 1.3 Implement CLI entry point (`__main__.py`)

The entry point parses arguments and starts the server.

**CLI arguments:**

| Argument           | Required | Default     | Description                                |
|--------------------|----------|-------------|--------------------------------------------|
| `--db-url`         | Yes      | -           | SQLAlchemy database connection URL          |
| `--mode`           | No       | `readonly`  | `readonly` or `readwrite`                   |
| `--transport`      | No       | `stdio`     | MCP transport: `stdio` or `http`            |
| `--port`           | No       | `8000`      | Port for HTTP transport                     |
| `--pool-size`      | No       | `5`         | Connection pool size                        |
| `--pool-pre-ping`  | No       | `True`      | Test connections before use                 |

**Implementation notes:**

- Use `argparse` for CLI parsing (no extra dependency).
- The `--db-url` can also be read from `SQLALCHEMY_MCP_DB_URL` environment variable.
- Validate that the mode is one of `readonly` or `readwrite`.
- Pass parsed config to `server.create_server()` which returns the FastMCP instance.
- Call `mcp.run(transport=transport)` to start.

**Example usage:**

```bash
# Read-only SQLite
sqlalchemy-mcp-server --db-url "sqlite:///mydb.db"

# Read-write PostgreSQL
sqlalchemy-mcp-server --db-url "postgresql://user:pass@localhost/mydb" --mode readwrite

# HTTP transport
sqlalchemy-mcp-server --db-url "sqlite:///mydb.db" --transport http --port 9000
```

### 1.4 Stub out `server.py`

Create a `create_server()` function that:

1. Accepts a config dataclass/dict with all CLI arguments.
2. Creates a `FastMCP("SQLAlchemy MCP Server")` instance.
3. Returns it (tools will be registered in later iterations).

```python
from dataclasses import dataclass

@dataclass
class ServerConfig:
    db_url: str
    mode: str = "readonly"       # "readonly" | "readwrite"
    transport: str = "stdio"
    port: int = 8000
    pool_size: int = 5
    pool_pre_ping: bool = True
```

## Acceptance Criteria

- [ ] `pyproject.toml` is valid and installable via `pip install -e .`
- [ ] Running `python -m sqlalchemy_mcp_server --help` prints usage info
- [ ] Running without `--db-url` (and without env var) prints an error
- [ ] `--mode` only accepts `readonly` or `readwrite`
- [ ] The server starts (even if it has no tools yet) when given a valid `--db-url`
