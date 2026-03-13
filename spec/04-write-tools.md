# Iteration 4: Write Tools

## Goal

Implement MCP tools for modifying database data and schema. These tools are **only available in `readwrite` mode**.

## Tools

### 4.1 `execute` - Execute a SQL statement

```python
@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
    }
)
def execute(sql: str, params: dict[str, Any] | None = None) -> str:
    """Execute a SQL statement (INSERT, UPDATE, DELETE, etc.).

    Args:
        sql: The SQL statement to execute.
        params: Optional dictionary of bind parameters.
    """
```

**Implementation details:**

- Wrap SQL in `sqlalchemy.text()`.
- Execute within `with engine.connect() as conn` and `conn.execute()`.
- Commit the transaction: `conn.commit()`.
- Return a summary: `{"rows_affected": result.rowcount, "status": "success"}`.
- For statements that return results (e.g., INSERT ... RETURNING), include the returned rows.
- **Forbidden statements:** Even in readwrite mode, block `DROP DATABASE` and other extremely destructive operations. Maintain a blocklist of patterns.

### 4.2 `execute_many` - Execute a parameterized statement with multiple parameter sets

```python
@mcp.tool(annotations={"readOnlyHint": False})
def execute_many(sql: str, params_list: list[dict[str, Any]]) -> str:
    """Execute a SQL statement multiple times with different parameters.

    Args:
        sql: The SQL statement with named bind parameters.
        params_list: List of parameter dictionaries, one per execution.
    """
```

**Implementation:**
- Use `conn.execute(text(sql), params_list)` which SQLAlchemy handles as executemany.
- Return `{"rows_affected": result.rowcount, "executions": len(params_list)}`.

### 4.3 `create_table` - Create a table from a schema definition

```python
@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
def create_table(
    table_name: str,
    columns: list[dict[str, Any]],
    schema: str | None = None,
) -> str:
    """Create a new table.

    Args:
        table_name: Name for the new table.
        columns: List of column definitions. Each dict should have:
            - name (str): Column name
            - type (str): Column type (e.g., "INTEGER", "VARCHAR(255)", "TEXT")
            - primary_key (bool, optional): Whether this is a primary key
            - nullable (bool, optional): Whether NULL is allowed (default True)
            - default (str, optional): Default value expression
        schema: Optional schema name.
    """
```

**Implementation:**
- Parse column type strings into SQLAlchemy types. Support common types:
  - `INTEGER`, `BIGINT`, `SMALLINT`
  - `VARCHAR(n)`, `TEXT`, `CHAR(n)`
  - `FLOAT`, `NUMERIC(p,s)`, `DECIMAL(p,s)`
  - `BOOLEAN`
  - `DATE`, `DATETIME`, `TIMESTAMP`
  - `BLOB`, `BINARY`
- Build a `Table` object with `Column` objects and call `table.create(engine)`.
- Return success message with table name.

### 4.4 `drop_table` - Drop a table

```python
@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True})
def drop_table(table_name: str, schema: str | None = None) -> str:
    """Drop a table from the database.

    Args:
        table_name: Name of the table to drop.
        schema: Optional schema name.
    """
```

**Implementation:**
- Reflect the table, then call `table.drop(engine)`.
- Return confirmation message.

### 4.5 `add_column` - Add a column to an existing table

```python
@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
def add_column(
    table_name: str,
    column_name: str,
    column_type: str,
    nullable: bool = True,
    default: str | None = None,
    schema: str | None = None,
) -> str:
    """Add a new column to an existing table.

    Args:
        table_name: Target table name.
        column_name: Name for the new column.
        column_type: SQL type (e.g., "VARCHAR(100)", "INTEGER").
        nullable: Whether NULL values are allowed.
        default: Optional default value.
        schema: Optional schema name.
    """
```

**Implementation:**
- Generate and execute `ALTER TABLE ... ADD COLUMN ...` SQL.
- Use dialect-aware DDL generation where possible.

### 4.6 `create_index` - Create an index

```python
@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
def create_index(
    index_name: str,
    table_name: str,
    columns: list[str],
    unique: bool = False,
    schema: str | None = None,
) -> str:
    """Create an index on a table.

    Args:
        index_name: Name for the index.
        table_name: Table to index.
        columns: List of column names to include.
        unique: Whether to create a unique index.
        schema: Optional schema name.
    """
```

## SQL Type Parsing

Create a utility function to parse SQL type strings into SQLAlchemy type objects:

```python
from sqlalchemy import types

TYPE_MAP = {
    "INTEGER": types.Integer,
    "BIGINT": types.BigInteger,
    "SMALLINT": types.SmallInteger,
    "VARCHAR": types.String,
    "TEXT": types.Text,
    "FLOAT": types.Float,
    "NUMERIC": types.Numeric,
    "DECIMAL": types.Numeric,
    "BOOLEAN": types.Boolean,
    "DATE": types.Date,
    "DATETIME": types.DateTime,
    "TIMESTAMP": types.DateTime,
    "BLOB": types.LargeBinary,
    "BINARY": types.LargeBinary,
    "JSON": types.JSON,
}

def parse_sql_type(type_str: str) -> types.TypeEngine:
    """Parse a SQL type string like 'VARCHAR(255)' into a SQLAlchemy type."""
    # Handle parameterized types: VARCHAR(255), NUMERIC(10,2)
    # Handle plain types: INTEGER, TEXT, BOOLEAN
    ...
```

## Safety Considerations

1. **Mode enforcement:** Write tools are simply not registered in readonly mode. There is no runtime check needed — the tools don't exist.
2. **Blocklist:** Reject statements matching dangerous patterns:
   - `DROP DATABASE`
   - `TRUNCATE` (unless explicitly intended — could be allowed)
   - Dialect-specific dangerous operations
3. **Transaction safety:** Each write operation runs in its own transaction. If it fails, it rolls back automatically.
4. **Parameterized queries:** Always use bind parameters for user-supplied values to prevent SQL injection.

## Acceptance Criteria

- [ ] `execute` runs INSERT/UPDATE/DELETE and reports rows affected
- [ ] `execute` blocks extremely dangerous operations (DROP DATABASE)
- [ ] `execute_many` handles batch operations efficiently
- [ ] `create_table` creates tables from column definitions
- [ ] `drop_table` drops existing tables
- [ ] `add_column` adds columns with proper types
- [ ] `create_index` creates regular and unique indexes
- [ ] All write tools are absent in readonly mode
- [ ] All write tools handle errors with clear messages
- [ ] SQL type parsing covers common types across dialects
