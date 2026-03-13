# Iteration 6: Testing

## Goal

Implement a comprehensive test suite covering all tools, resources, and prompts.

## Strategy

- Use **pytest** with **pytest-asyncio** for async test support.
- Use **SQLite in-memory databases** for all unit tests (no external DB required).
- Use FastMCP's built-in test client for MCP-level integration tests.
- Test both `readonly` and `readwrite` mode configurations.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_engine.py           # Engine creation and management
├── test_read_tools.py       # All read-only tools
├── test_write_tools.py      # All write tools
├── test_resources.py        # All resources
├── test_prompts.py          # All prompts
├── test_mode_enforcement.py # Mode-based tool visibility
└── test_cli.py              # CLI argument parsing
```

## Fixtures (`conftest.py`)

```python
import pytest
from sqlalchemy import create_engine, text

@pytest.fixture
def sample_db():
    """Create an in-memory SQLite database with sample data."""
    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                amount DECIMAL(10,2),
                status TEXT DEFAULT 'pending'
            )
        """))
        conn.execute(text(
            "INSERT INTO users (id, name, email) VALUES (:id, :name, :email)"
        ), [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ])
        conn.execute(text(
            "INSERT INTO orders (id, user_id, amount, status) VALUES (:id, :uid, :amt, :st)"
        ), [
            {"id": 1, "uid": 1, "amt": 99.99, "st": "completed"},
            {"id": 2, "uid": 1, "amt": 49.50, "st": "pending"},
            {"id": 3, "uid": 2, "amt": 150.00, "st": "completed"},
        ])
        conn.commit()
    yield engine
    engine.dispose()

@pytest.fixture
def readonly_server(sample_db):
    """Create a server in readonly mode with the sample database."""
    ...

@pytest.fixture
def readwrite_server(sample_db):
    """Create a server in readwrite mode with the sample database."""
    ...
```

## Test Cases

### `test_engine.py`

| Test | Description |
|------|-------------|
| `test_create_engine_sqlite` | Engine creation with SQLite URL |
| `test_create_engine_invalid_url` | Error on malformed URL |
| `test_sqlite_pool_settings` | SQLite doesn't use QueuePool |
| `test_test_connection_fails` | Clear error when DB unreachable |
| `test_get_inspector` | Inspector is returned and functional |
| `test_dispose` | Engine is cleanly disposed |

### `test_read_tools.py`

| Test | Description |
|------|-------------|
| `test_query_select` | Basic SELECT returns correct rows |
| `test_query_with_params` | Parameterized query works |
| `test_query_limit` | Row limit is respected |
| `test_query_rejects_insert` | INSERT is rejected |
| `test_query_rejects_delete` | DELETE is rejected |
| `test_query_rejects_drop` | DROP is rejected |
| `test_query_with_cte` | WITH (CTE) queries work |
| `test_query_sql_error` | Invalid SQL returns clear error |
| `test_list_tables` | Returns all tables and views |
| `test_list_tables_with_schema` | Schema filter works |
| `test_describe_table` | Returns columns, PKs, FKs, indexes |
| `test_describe_table_not_found` | Error for nonexistent table |
| `test_list_schemas` | Returns available schemas |
| `test_get_table_ddl` | Returns valid CREATE TABLE SQL |
| `test_explain_query` | Returns execution plan |

### `test_write_tools.py`

| Test | Description |
|------|-------------|
| `test_execute_insert` | INSERT adds rows |
| `test_execute_update` | UPDATE modifies rows |
| `test_execute_delete` | DELETE removes rows |
| `test_execute_returns_rowcount` | Row count is accurate |
| `test_execute_blocks_drop_database` | DROP DATABASE is blocked |
| `test_execute_many` | Batch insert works |
| `test_create_table` | Table creation from column defs |
| `test_create_table_types` | Various column types are handled |
| `test_drop_table` | Table is dropped |
| `test_add_column` | Column is added |
| `test_create_index` | Index is created |
| `test_create_unique_index` | Unique index is created |
| `test_execute_rollback_on_error` | Failed statement rolls back |

### `test_mode_enforcement.py`

| Test | Description |
|------|-------------|
| `test_readonly_has_read_tools` | Read tools exist in readonly mode |
| `test_readonly_no_write_tools` | Write tools absent in readonly mode |
| `test_readwrite_has_all_tools` | All tools exist in readwrite mode |

### `test_resources.py`

| Test | Description |
|------|-------------|
| `test_schema_resource` | Returns dialect, table count |
| `test_tables_resource` | Lists all tables |
| `test_table_detail_resource` | Returns column info for a table |
| `test_table_ddl_resource` | Returns DDL |
| `test_table_sample_resource` | Returns sample rows |
| `test_invalid_table_resource` | Error for nonexistent table |

### `test_prompts.py`

| Test | Description |
|------|-------------|
| `test_sql_query_prompt` | Returns messages with schema context |
| `test_explain_schema_prompt` | Returns full schema overview |
| `test_optimize_query_prompt` | Includes EXPLAIN output |

### `test_cli.py`

| Test | Description |
|------|-------------|
| `test_help_flag` | `--help` prints usage |
| `test_missing_db_url` | Error without `--db-url` |
| `test_invalid_mode` | Error for bad `--mode` value |
| `test_env_var_db_url` | `SQLALCHEMY_MCP_DB_URL` env var works |
| `test_default_mode` | Default mode is readonly |

## Acceptance Criteria

- [ ] All tests pass with `pytest`
- [ ] Tests run without any external database (SQLite in-memory only)
- [ ] Both readonly and readwrite modes are covered
- [ ] Error cases are tested (invalid input, missing tables, bad SQL)
- [ ] Test suite runs in under 10 seconds
