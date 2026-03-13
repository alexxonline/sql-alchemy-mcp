# Iteration 3: Read-Only Tools

## Goal

Implement MCP tools for querying and introspecting databases. These tools are available in both `readonly` and `readwrite` modes.

## Tools

### 3.1 `query` - Execute a SELECT query

**Purpose:** Run a read-only SQL query and return results.

```python
@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
def query(sql: str, params: dict[str, Any] | None = None) -> str:
    """Execute a read-only SQL query and return results as JSON.

    Args:
        sql: A SELECT SQL statement to execute.
        params: Optional dictionary of bind parameters.
    """
```

**Implementation details:**

- Wrap the SQL in `sqlalchemy.text()`.
- Execute within a connection context manager: `with engine.connect() as conn`.
- Fetch all rows using `result.mappings().all()`.
- Convert to list of dicts and serialize to JSON.
- **Safety:** In read-only mode, wrap in a transaction that is always rolled back. Additionally, validate that the statement begins with SELECT / WITH / EXPLAIN / SHOW / DESCRIBE / PRAGMA (after stripping whitespace and comments). Reject anything else.
- **Row limit:** Accept an optional `limit` parameter (default 1000) to prevent unbounded result sets. Append `LIMIT` only if the query doesn't already contain one — or better, use `result.fetchmany(limit)`.
- **Error handling:** Catch `SQLAlchemyError` and return a clear error message.

### 3.2 `list_tables` - List all tables

```python
@mcp.tool(annotations={"readOnlyHint": True})
def list_tables(schema: str | None = None) -> str:
    """List all tables in the database.

    Args:
        schema: Optional schema name to list tables from.
    """
```

**Implementation:**
- Use `inspect(engine).get_table_names(schema=schema)`.
- Also include `get_view_names(schema=schema)` with a `type` field to distinguish.
- Return as JSON array of objects: `[{"name": "users", "type": "table"}, ...]`.

### 3.3 `describe_table` - Get table schema

```python
@mcp.tool(annotations={"readOnlyHint": True})
def describe_table(table_name: str, schema: str | None = None) -> str:
    """Describe a table's columns, primary keys, foreign keys, and indexes.

    Args:
        table_name: Name of the table to describe.
        schema: Optional schema name.
    """
```

**Implementation:**
- Use `Inspector` methods:
  - `get_columns(table_name, schema=schema)` - column details
  - `get_pk_constraint(table_name, schema=schema)` - primary key
  - `get_foreign_keys(table_name, schema=schema)` - foreign keys
  - `get_indexes(table_name, schema=schema)` - indexes
  - `get_unique_constraints(table_name, schema=schema)` - unique constraints
- Serialize column types to strings (`str(col["type"])`).
- Return as a structured JSON object.

### 3.4 `list_schemas` - List database schemas

```python
@mcp.tool(annotations={"readOnlyHint": True})
def list_schemas() -> str:
    """List all schemas in the database."""
```

**Implementation:**
- Use `inspect(engine).get_schema_names()`.
- Return as JSON array.

### 3.5 `get_table_ddl` - Get CREATE TABLE statement

```python
@mcp.tool(annotations={"readOnlyHint": True})
def get_table_ddl(table_name: str, schema: str | None = None) -> str:
    """Get the DDL (CREATE TABLE statement) for a table.

    Args:
        table_name: Name of the table.
        schema: Optional schema name.
    """
```

**Implementation:**
- Reflect the table using `Table(table_name, MetaData(), autoload_with=engine, schema=schema)`.
- Use `CreateTable(table).compile(engine)` to generate the DDL string.
- Return as plain text.

### 3.6 `explain_query` - Get query execution plan

```python
@mcp.tool(annotations={"readOnlyHint": True})
def explain_query(sql: str) -> str:
    """Get the execution plan for a SQL query.

    Args:
        sql: The SQL query to explain.
    """
```

**Implementation:**
- Prepend `EXPLAIN` (or `EXPLAIN ANALYZE` depending on dialect) to the query.
- Execute and return the plan as text.
- Only allow SELECT statements.

## Tool Registration Pattern

In `server.py`, conditionally register tools based on mode:

```python
def create_server(config: ServerConfig) -> FastMCP:
    mcp = FastMCP("SQLAlchemy MCP Server")

    # Always register read tools
    from .tools.read import register_read_tools
    register_read_tools(mcp)

    # Only register write tools in readwrite mode
    if config.mode == "readwrite":
        from .tools.write import register_write_tools
        register_write_tools(mcp)

    return mcp
```

Each tool module exposes a `register_*_tools(mcp)` function that uses `mcp.tool` as a decorator or `mcp.add_tool()`.

## Acceptance Criteria

- [ ] `query` executes SELECT statements and returns JSON results
- [ ] `query` rejects non-SELECT statements in all modes
- [ ] `query` respects the row limit parameter
- [ ] `list_tables` returns tables and views with their types
- [ ] `describe_table` returns columns, PKs, FKs, indexes, and unique constraints
- [ ] `list_schemas` returns available schemas
- [ ] `get_table_ddl` returns a valid CREATE TABLE statement
- [ ] `explain_query` returns a query execution plan
- [ ] All tools handle errors gracefully with clear messages
- [ ] All tools work with SQLite (minimum viable dialect for testing)
