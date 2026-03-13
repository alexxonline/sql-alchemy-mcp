# Iteration 5: Resources and Prompts

## Goal

Implement MCP resources for browsable database metadata and MCP prompts to assist LLMs with common SQL tasks.

## Resources

### 5.1 `db://schema` - Database schema overview

```python
@mcp.resource("db://schema")
def get_schema_overview() -> str:
    """Overview of the database: dialect, tables, and schema names."""
```

Returns a JSON object with:
- `dialect`: Database dialect name (e.g., "sqlite", "postgresql")
- `driver`: DBAPI driver name
- `schemas`: List of schema names
- `tables_count`: Total number of tables
- `mode`: Current server mode (readonly/readwrite)

### 5.2 `db://tables` - List of all tables

```python
@mcp.resource("db://tables")
def get_tables_list() -> str:
    """List of all tables and views in the database."""
```

Returns JSON array of `{"name": "...", "type": "table|view", "schema": "..."}`.

### 5.3 `db://tables/{table_name}` - Table details (resource template)

```python
@mcp.resource("db://tables/{table_name}")
def get_table_details(table_name: str) -> str:
    """Detailed schema information for a specific table."""
```

Returns JSON with columns, primary keys, foreign keys, indexes, and unique constraints for the specified table.

### 5.4 `db://tables/{table_name}/ddl` - Table DDL

```python
@mcp.resource("db://tables/{table_name}/ddl")
def get_table_ddl_resource(table_name: str) -> str:
    """CREATE TABLE DDL statement for a specific table."""
```

Returns the DDL as plain text with `mime_type="text/sql"`.

### 5.5 `db://tables/{table_name}/sample` - Sample data

```python
@mcp.resource("db://tables/{table_name}/sample{?limit}")
def get_table_sample(table_name: str, limit: int = 5) -> str:
    """Sample rows from a table for quick data exploration."""
```

Returns first N rows as JSON. Validates `table_name` against known tables to prevent injection.

## Prompts

### 5.6 `sql_query` - Help write a SQL query

```python
@mcp.prompt
def sql_query(table_names: str, task: str) -> list[Message]:
    """Generate a SQL query for a task using specified tables.

    Args:
        table_names: Comma-separated list of tables to work with.
        task: Description of what the query should do.
    """
```

**Implementation:**
- Fetch the schema for each specified table.
- Build a multi-message prompt that includes:
  1. System context: dialect, table schemas
  2. User request: the task description
- Return messages that the LLM can use to generate a correct query.

### 5.7 `explain_schema` - Explain database structure

```python
@mcp.prompt
def explain_schema() -> str:
    """Provide a comprehensive overview of the database schema.

    Returns a prompt that includes all tables, their columns,
    relationships (foreign keys), and indexes.
    """
```

**Implementation:**
- Reflect all tables.
- Format a human-readable schema description.
- Include foreign key relationships as a "relationships" section.

### 5.8 `optimize_query` - Help optimize a query

```python
@mcp.prompt
def optimize_query(sql: str) -> list[Message]:
    """Help optimize a SQL query.

    Args:
        sql: The SQL query to optimize.
    """
```

**Implementation:**
- Include the query.
- Run EXPLAIN on it and include the execution plan.
- Include relevant table schemas.
- Ask the LLM to suggest optimizations.

## Resource Implementation Notes

- Resources should reuse the same introspection logic as read tools (avoid duplication).
- Extract shared logic into helper functions in `engine.py` or a shared `introspection.py` module.
- Table name validation: always check `table_name` against `inspector.get_table_names()` before using it in any query, to prevent SQL injection via resource URIs.

## Acceptance Criteria

- [ ] `db://schema` returns database overview
- [ ] `db://tables` returns all tables with types
- [ ] `db://tables/{name}` returns detailed schema for a specific table
- [ ] `db://tables/{name}/ddl` returns valid DDL
- [ ] `db://tables/{name}/sample` returns sample data rows
- [ ] `sql_query` prompt includes relevant table schemas
- [ ] `explain_schema` prompt provides full schema overview
- [ ] `optimize_query` prompt includes EXPLAIN output
- [ ] Invalid table names in resource URIs return clear errors (not SQL injection)
