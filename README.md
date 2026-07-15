# SQLAlchemy MCP Server and CLI

An [MCP](https://modelcontextprotocol.io/) server that provides SQL database access through [SQLAlchemy](https://www.sqlalchemy.org/). Built with [FastMCP](https://gofastmcp.com/), it supports any database that SQLAlchemy supports and operates in **read-only** or **read-write** mode.

## Motivation

As AI agents become more common in development workflows, database access presents an unexpected problem: SQL is verbose.

When an agent needs to interact with a database, it often has to generate full SQL queries, which increases:

- prompt size

- token usage

- chances of syntax errors across dialects

This tool provides an MCP Server and a compact CLI abstraction over SQLAlchemy, allowing agents (or humans) to interact with multiple databases using short commands instead of full SQL statements.

### Benefits:

- unified interface for different database engines

- SQLAlchemy handles dialect differences

- significantly shorter commands for AI-driven workflows

## Features

- **Universal database support** -- SQLite, PostgreSQL, MySQL, Oracle, MSSQL, and [60+ other databases](https://docs.sqlalchemy.org/en/20/dialects/) via SQLAlchemy
- **Read-only and read-write modes** -- control access with a command-line flag
- **MCP tools** -- query, introspect, and modify databases
- **MCP resources** -- browse database schema, tables, DDL, and sample data
- **MCP prompts** -- get help writing, explaining, and optimizing SQL queries

## Installation

```bash
pip install sqlalchemy-mcp-server
```

With database-specific drivers:

```bash
pip install "sqlalchemy-mcp-server[postgresql]"   # PostgreSQL (psycopg2)
pip install "sqlalchemy-mcp-server[mysql]"         # MySQL (PyMySQL)
pip install "sqlalchemy-mcp-server[oracle]"        # Oracle (oracledb)
pip install "sqlalchemy-mcp-server[mssql]"         # MSSQL (pyodbc)
pip install "sqlalchemy-mcp-server[all]"           # All drivers
```

### Install from a local checkout

If you'd rather clone the repository and install from source (for example, to run an unreleased version or make your own changes):

```bash
git clone https://github.com/alexxonline/sql-alchemy-mcp.git
cd sql-alchemy-mcp

# (recommended) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# install the package from the current directory
pip install .

# ...or with database-specific drivers
pip install ".[postgresql]"      # or [mysql], [oracle], [mssql], [all]

# ...or as an editable install, so code changes take effect without reinstalling
pip install -e .
```

Once installed this way, the `sqlalchemy-mcp-server` command is available exactly as with the PyPI install (see [Quick Start](#quick-start) below).

### Run from source without installing

You can also run directly from the cloned repository without installing the package. After installing the dependencies (`pip install fastmcp sqlalchemy`, plus any driver you need), invoke it as a module from the repo root:

```bash
python -m sqlalchemy_mcp_server --db-url "sqlite:///mydb.db"
```

`python -m sqlalchemy_mcp_server ...` accepts the same arguments as the `sqlalchemy-mcp-server` command shown throughout this README, including `--cli` mode.

With [uv](https://docs.astral.sh/uv/), you can run from the checkout without managing a virtual environment yourself:

```bash
uv run sqlalchemy-mcp-server --db-url "sqlite:///mydb.db"
```

When pointing an MCP client at a local checkout, use the module form as the command:

```json
{
  "mcpServers": {
    "my-database": {
      "command": "python",
      "args": [
        "-m", "sqlalchemy_mcp_server",
        "--db-url", "sqlite:///path/to/mydb.db",
        "--mode", "readonly"
      ],
      "cwd": "/path/to/sql-alchemy-mcp"
    }
  }
}
```

## Quick Start

```bash
# Read-only access to a SQLite database
sqlalchemy-mcp-server --db-url "sqlite:///mydb.db"

# Read-write access to PostgreSQL
sqlalchemy-mcp-server --db-url "postgresql://user:pass@localhost/mydb" --mode readwrite

# HTTP transport on a custom port
sqlalchemy-mcp-server --db-url "sqlite:///mydb.db" --transport http --port 9000
```

## Server Options

```
sqlalchemy-mcp-server [OPTIONS]
```

| Argument           | Default     | Description                                              |
|--------------------|-------------|----------------------------------------------------------|
| `--db-url`         | (required)  | SQLAlchemy connection URL (or `SQLALCHEMY_MCP_DB_URL` env var) |
| `--mode`           | `readonly`  | `readonly` or `readwrite`                                |
| `--transport`      | `stdio`     | MCP transport: `stdio` or `http`                         |
| `--port`           | `8000`      | Port for HTTP transport                                  |
| `--pool-size`      | `5`         | Connection pool size                                     |
| `--no-pool-pre-ping` | (off)    | Disable connection pre-ping                              |
| `--cli`            | (off)       | Run in CLI mode (one-shot command execution, then exit)  |

## CLI Mode

Add `--cli` to run any tool, resource, or prompt as a one-shot command. The program connects, executes, prints the result to stdout, and exits — no MCP server is started.

### Running tools

```bash
# Query a table
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli query --sql "SELECT * FROM users"

# List tables
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli list_tables

# Describe a table
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli describe_table --table-name users

# Get CREATE TABLE DDL
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli get_table_ddl --table-name users

# Execute a write statement (requires --mode readwrite)
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --mode readwrite --cli execute \
  --sql "INSERT INTO users (name, email) VALUES ('alice', 'alice@example.com')"

# Create a table (requires --mode readwrite)
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --mode readwrite --cli create_table \
  --table-name events \
  --columns '[{"name": "id", "type": "INTEGER", "primary_key": true}, {"name": "title", "type": "TEXT"}]'
```

### Reading resources

```bash
# Database overview
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli resource schema

# List all tables
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli resource tables

# Table details
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli resource table --table-name users

# Table DDL
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli resource table-ddl --table-name users

# Sample rows
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli resource table-sample --table-name users --limit 10
```

### Rendering prompts

```bash
# Schema overview prompt
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli prompt explain_schema

# SQL query help
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli prompt sql_query \
  --table-names "users,orders" --task "find users with no orders"

# Query optimization
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli prompt optimize_query \
  --sql "SELECT * FROM users WHERE name = 'alice'"
```

### Output formatting

```bash
# Pretty-printed JSON (default)
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli query --sql "SELECT * FROM users"

# Compact JSON (for piping)
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli query --sql "SELECT * FROM users" --compact

# Plain text table
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli query --sql "SELECT * FROM users" --format table
```

Output goes to stdout, errors to stderr, so CLI mode is composable with shell pipelines:

```bash
# Pipe to jq
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli query \
  --sql "SELECT * FROM users" --compact | jq '.[].name'

# Use in a script
TABLES=$(sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli list_tables --compact)
```

### Getting help

```bash
# List all CLI commands
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli --help

# Help for a specific command
sqlalchemy-mcp-server --db-url sqlite:///mydb.db --cli query --help
```

## Supported Databases

| Database   | Driver Package   | URL Format                                       | Install Extra  |
|------------|------------------|--------------------------------------------------|----------------|
| SQLite     | (built-in)       | `sqlite:///path/to/db.db`                        | (none)         |
| PostgreSQL | psycopg2-binary  | `postgresql://user:pass@host/dbname`             | `[postgresql]` |
| MySQL      | PyMySQL          | `mysql+pymysql://user:pass@host/dbname`          | `[mysql]`      |
| Oracle     | oracledb         | `oracle+oracledb://user:pass@host:1521/?service_name=svc` | `[oracle]` |
| MSSQL      | pyodbc           | `mssql+pyodbc://user:pass@dsn`                   | `[mssql]`      |
| Any other  | (user-installed) | Per [SQLAlchemy docs](https://docs.sqlalchemy.org/en/20/dialects/) | Manual |

## MCP Client Configuration

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-database": {
      "command": "sqlalchemy-mcp-server",
      "args": [
        "--db-url", "sqlite:///path/to/mydb.db",
        "--mode", "readonly"
      ]
    }
  }
}
```

### Claude Desktop with uvx (no install needed)

```json
{
  "mcpServers": {
    "my-database": {
      "command": "uvx",
      "args": [
        "sqlalchemy-mcp-server",
        "--db-url", "postgresql://user:pass@localhost/mydb",
        "--mode", "readwrite"
      ]
    }
  }
}
```

## Available Tools

### Read-only tools (always available)

| Tool             | Description                                         |
|------------------|-----------------------------------------------------|
| `query`          | Execute a read-only SQL query (SELECT/WITH/EXPLAIN)  |
| `list_tables`    | List all tables and views                            |
| `describe_table` | Get columns, PKs, FKs, indexes for a table          |
| `list_schemas`   | List all database schemas                            |
| `get_table_ddl`  | Get the CREATE TABLE DDL for a table                 |
| `explain_query`  | Get the execution plan for a SELECT query            |

### Write tools (readwrite mode only)

| Tool             | Description                                         |
|------------------|-----------------------------------------------------|
| `execute`        | Execute a SQL statement (INSERT, UPDATE, DELETE, etc.) |
| `execute_many`   | Execute a statement with multiple parameter sets     |
| `create_table`   | Create a table from column definitions               |
| `drop_table`     | Drop a table                                         |
| `add_column`     | Add a column to an existing table                    |
| `create_index`   | Create an index (regular or unique)                  |

## Available Resources

| URI                                | Description                          |
|------------------------------------|--------------------------------------|
| `db://schema`                      | Database overview (dialect, mode, table count) |
| `db://tables`                      | List of all tables and views         |
| `db://tables/{table_name}`         | Detailed schema for a specific table |
| `db://tables/{table_name}/ddl`     | CREATE TABLE DDL statement           |
| `db://tables/{table_name}/sample`  | Sample rows from a table             |

## Available Prompts

| Prompt            | Description                                        |
|-------------------|----------------------------------------------------|
| `sql_query`       | Help write a SQL query for specified tables and task |
| `explain_schema`  | Comprehensive overview of the database schema       |
| `optimize_query`  | Analyze and optimize a SQL query with EXPLAIN output |

## Development

```bash
# Clone and install in development mode
git clone https://github.com/alexxonline/sql-alchemy-mcp.git
cd sql-alchemy-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```
