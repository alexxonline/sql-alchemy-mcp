# SQLAlchemy MCP Server

An [MCP](https://modelcontextprotocol.io/) server that provides SQL database access through [SQLAlchemy](https://www.sqlalchemy.org/). Built with [FastMCP](https://gofastmcp.com/), it supports any database that SQLAlchemy supports and operates in **read-only** or **read-write** mode.

## Motivation

As AI agents become more common in development workflows, database access presents an unexpected problem: SQL is verbose.

When an agent needs to interact with a database, it often has to generate full SQL queries, which increases:

- prompt size

- token usage

- chances of syntax errors across dialects

This tool provides a compact CLI abstraction over SQLAlchemy, allowing agents (or humans) to interact with multiple databases using short commands instead of full SQL statements.

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

## Quick Start

```bash
# Read-only access to a SQLite database
sqlalchemy-mcp-server --db-url "sqlite:///mydb.db"

# Read-write access to PostgreSQL
sqlalchemy-mcp-server --db-url "postgresql://user:pass@localhost/mydb" --mode readwrite

# HTTP transport on a custom port
sqlalchemy-mcp-server --db-url "sqlite:///mydb.db" --transport http --port 9000
```

## CLI Usage

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
git clone https://github.com/alexsaez/sqlalchemy-mcp-server.git
cd sqlalchemy-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```
