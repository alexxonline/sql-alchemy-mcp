"""Tests for read-only MCP tools."""

import json

import pytest


@pytest.fixture
def call(readonly_server):
    async def _call(name, args=None):
        r = await readonly_server.call_tool(name, args or {})
        return r.content[0].text

    return _call


class TestQuery:
    @pytest.mark.asyncio
    async def test_query_select(self, call):
        r = json.loads(await call("query", {"sql": "SELECT * FROM users ORDER BY id"}))
        assert r["count"] == 2
        assert r["rows"][0]["name"] == "Alice"
        assert r["rows"][1]["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_query_with_params(self, call):
        r = json.loads(
            await call(
                "query",
                {"sql": "SELECT * FROM users WHERE id = :id", "params": {"id": 1}},
            )
        )
        assert r["count"] == 1
        assert r["rows"][0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_query_limit(self, call):
        r = json.loads(
            await call("query", {"sql": "SELECT * FROM users", "limit": 1})
        )
        assert r["count"] == 1

    @pytest.mark.asyncio
    async def test_query_rejects_insert(self, call):
        r = json.loads(
            await call("query", {"sql": "INSERT INTO users VALUES (99, 'X', 'x@x')"})
        )
        assert "error" in r

    @pytest.mark.asyncio
    async def test_query_rejects_delete(self, call):
        r = json.loads(await call("query", {"sql": "DELETE FROM users"}))
        assert "error" in r

    @pytest.mark.asyncio
    async def test_query_rejects_drop(self, call):
        r = json.loads(await call("query", {"sql": "DROP TABLE users"}))
        assert "error" in r

    @pytest.mark.asyncio
    async def test_query_with_cte(self, call):
        r = json.loads(
            await call(
                "query",
                {"sql": "WITH u AS (SELECT * FROM users) SELECT * FROM u"},
            )
        )
        assert r["count"] == 2

    @pytest.mark.asyncio
    async def test_query_sql_error(self, call):
        r = json.loads(
            await call("query", {"sql": "SELECT * FROM nonexistent_table"})
        )
        assert "error" in r


class TestListTables:
    @pytest.mark.asyncio
    async def test_list_tables(self, call):
        r = json.loads(await call("list_tables"))
        names = {t["name"] for t in r}
        assert "users" in names
        assert "orders" in names
        assert all(t["type"] == "table" for t in r)

    @pytest.mark.asyncio
    async def test_list_tables_with_schema(self, call):
        r = json.loads(await call("list_tables", {"schema": "main"}))
        names = {t["name"] for t in r}
        assert "users" in names


class TestDescribeTable:
    @pytest.mark.asyncio
    async def test_describe_table(self, call):
        r = json.loads(await call("describe_table", {"table_name": "users"}))
        col_names = [c["name"] for c in r["columns"]]
        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names
        assert len(r["primary_key"]["columns"]) > 0

    @pytest.mark.asyncio
    async def test_describe_table_foreign_keys(self, call):
        r = json.loads(await call("describe_table", {"table_name": "orders"}))
        assert len(r["foreign_keys"]) > 0
        fk = r["foreign_keys"][0]
        assert fk["referred_table"] == "users"

    @pytest.mark.asyncio
    async def test_describe_table_not_found(self, call):
        r = json.loads(await call("describe_table", {"table_name": "nonexistent"}))
        assert "error" in r


class TestListSchemas:
    @pytest.mark.asyncio
    async def test_list_schemas(self, call):
        r = json.loads(await call("list_schemas"))
        assert "main" in r


class TestGetTableDDL:
    @pytest.mark.asyncio
    async def test_get_table_ddl(self, call):
        r = await call("get_table_ddl", {"table_name": "users"})
        assert "CREATE TABLE" in r
        assert "users" in r


class TestExplainQuery:
    @pytest.mark.asyncio
    async def test_explain_query(self, call):
        r = await call("explain_query", {"sql": "SELECT * FROM users WHERE id = 1"})
        # SQLite EXPLAIN returns opcode rows
        assert len(r) > 0

    @pytest.mark.asyncio
    async def test_explain_query_rejects_non_select(self, call):
        r = json.loads(
            await call("explain_query", {"sql": "DELETE FROM users"})
        )
        assert "error" in r
