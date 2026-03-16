"""Tests for write MCP tools."""

import json

import pytest


@pytest.fixture
def call(readwrite_server):
    async def _call(name, args=None):
        r = await readwrite_server.call_tool(name, args or {})
        return r.content[0].text

    return _call


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_insert(self, call):
        r = json.loads(
            await call(
                "execute",
                {"sql": "INSERT INTO users (id, name, email) VALUES (3, 'Charlie', 'c@example.com')"},
            )
        )
        assert r["status"] == "success"
        assert r["rows_affected"] == 1

    @pytest.mark.asyncio
    async def test_execute_update(self, call):
        r = json.loads(
            await call(
                "execute",
                {"sql": "UPDATE users SET name = 'Robert' WHERE id = 2"},
            )
        )
        assert r["status"] == "success"
        assert r["rows_affected"] == 1

    @pytest.mark.asyncio
    async def test_execute_delete(self, call):
        r = json.loads(
            await call("execute", {"sql": "DELETE FROM orders WHERE id = 3"})
        )
        assert r["status"] == "success"
        assert r["rows_affected"] == 1

    @pytest.mark.asyncio
    async def test_execute_returns_rowcount(self, call):
        r = json.loads(
            await call("execute", {"sql": "UPDATE orders SET status = 'shipped'"})
        )
        assert r["rows_affected"] == 3

    @pytest.mark.asyncio
    async def test_execute_blocks_drop_database(self, call):
        r = json.loads(await call("execute", {"sql": "DROP DATABASE mydb"}))
        assert "error" in r

    @pytest.mark.asyncio
    async def test_execute_blocks_drop_schema(self, call):
        r = json.loads(await call("execute", {"sql": "DROP SCHEMA public"}))
        assert "error" in r

    @pytest.mark.asyncio
    async def test_execute_rollback_on_error(self, call):
        # Attempt a bad insert
        r = json.loads(
            await call("execute", {"sql": "INSERT INTO nonexistent VALUES (1)"})
        )
        assert "error" in r
        # Verify existing data is intact
        q = json.loads(
            await call("query", {"sql": "SELECT count(*) as cnt FROM users"})
        )
        assert q["rows"][0]["cnt"] == 2


class TestExecuteMany:
    @pytest.mark.asyncio
    async def test_execute_many(self, call):
        r = json.loads(
            await call(
                "execute_many",
                {
                    "sql": "INSERT INTO users (id, name, email) VALUES (:id, :name, :email)",
                    "params_list": [
                        {"id": 10, "name": "X", "email": "x@x.com"},
                        {"id": 11, "name": "Y", "email": "y@y.com"},
                        {"id": 12, "name": "Z", "email": "z@z.com"},
                    ],
                },
            )
        )
        assert r["status"] == "success"
        assert r["executions"] == 3
        assert r["rows_affected"] == 3


class TestCreateTable:
    @pytest.mark.asyncio
    async def test_create_table(self, call):
        r = json.loads(
            await call(
                "create_table",
                {
                    "table_name": "products",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {"name": "name", "type": "VARCHAR(100)", "nullable": False},
                        {"name": "price", "type": "NUMERIC(10,2)"},
                    ],
                },
            )
        )
        assert r["status"] == "success"
        assert r["table"] == "products"

        # Verify table exists
        tables = json.loads(await call("list_tables"))
        assert "products" in [t["name"] for t in tables]

    @pytest.mark.asyncio
    async def test_create_table_types(self, call):
        r = json.loads(
            await call(
                "create_table",
                {
                    "table_name": "type_test",
                    "columns": [
                        {"name": "c1", "type": "INTEGER"},
                        {"name": "c2", "type": "BIGINT"},
                        {"name": "c3", "type": "TEXT"},
                        {"name": "c4", "type": "BOOLEAN"},
                        {"name": "c5", "type": "DATE"},
                        {"name": "c6", "type": "DATETIME"},
                        {"name": "c7", "type": "FLOAT"},
                        {"name": "c8", "type": "BLOB"},
                        {"name": "c9", "type": "JSON"},
                    ],
                },
            )
        )
        assert r["status"] == "success"

    @pytest.mark.asyncio
    async def test_create_table_bad_type(self, call):
        r = json.loads(
            await call(
                "create_table",
                {
                    "table_name": "bad",
                    "columns": [{"name": "x", "type": "UNKNOWNTYPE"}],
                },
            )
        )
        assert "error" in r


class TestDropTable:
    @pytest.mark.asyncio
    async def test_drop_table(self, call):
        # Create then drop
        await call(
            "create_table",
            {
                "table_name": "to_drop",
                "columns": [{"name": "id", "type": "INTEGER"}],
            },
        )
        r = json.loads(await call("drop_table", {"table_name": "to_drop"}))
        assert r["status"] == "success"

        tables = json.loads(await call("list_tables"))
        assert "to_drop" not in [t["name"] for t in tables]


class TestAddColumn:
    @pytest.mark.asyncio
    async def test_add_column(self, call):
        r = json.loads(
            await call(
                "add_column",
                {
                    "table_name": "users",
                    "column_name": "age",
                    "column_type": "INTEGER",
                },
            )
        )
        assert r["status"] == "success"
        assert r["column"] == "age"

        desc = json.loads(await call("describe_table", {"table_name": "users"}))
        col_names = [c["name"] for c in desc["columns"]]
        assert "age" in col_names


class TestCreateIndex:
    @pytest.mark.asyncio
    async def test_create_index(self, call):
        r = json.loads(
            await call(
                "create_index",
                {
                    "index_name": "idx_users_name",
                    "table_name": "users",
                    "columns": ["name"],
                },
            )
        )
        assert r["status"] == "success"
        assert r["unique"] is False

    @pytest.mark.asyncio
    async def test_create_unique_index(self, call):
        # Use user_id + status combo which is unique in sample data
        r = json.loads(
            await call(
                "create_index",
                {
                    "index_name": "idx_users_email_uniq",
                    "table_name": "users",
                    "columns": ["email"],
                    "unique": True,
                },
            )
        )
        assert r["status"] == "success"
        assert r["unique"] is True
