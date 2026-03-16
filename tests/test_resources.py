"""Tests for MCP resources."""

import json

import pytest


@pytest.fixture
def read(readonly_server):
    async def _read(uri):
        r = await readonly_server.read_resource(uri)
        return r.contents[0].content

    return _read


class TestSchemaResource:
    @pytest.mark.asyncio
    async def test_schema_resource(self, read):
        r = json.loads(await read("db://schema"))
        assert r["dialect"] == "sqlite"
        assert r["driver"] == "pysqlite"
        assert r["tables_count"] == 2
        assert r["mode"] == "readonly"
        assert "main" in r["schemas"]


class TestTablesResource:
    @pytest.mark.asyncio
    async def test_tables_resource(self, read):
        r = json.loads(await read("db://tables"))
        names = {t["name"] for t in r}
        assert "users" in names
        assert "orders" in names


class TestTableDetailResource:
    @pytest.mark.asyncio
    async def test_table_detail_resource(self, read):
        r = json.loads(await read("db://tables/users"))
        col_names = [c["name"] for c in r["columns"]]
        assert "id" in col_names
        assert "name" in col_names
        assert len(r["primary_key"]["columns"]) > 0

    @pytest.mark.asyncio
    async def test_invalid_table_resource(self, read):
        r = json.loads(await read("db://tables/nonexistent"))
        assert "error" in r


class TestTableDDLResource:
    @pytest.mark.asyncio
    async def test_table_ddl_resource(self, read):
        r = await read("db://tables/users/ddl")
        assert "CREATE TABLE" in r
        assert "users" in r


class TestTableSampleResource:
    @pytest.mark.asyncio
    async def test_table_sample_resource(self, read):
        r = json.loads(await read("db://tables/users/sample"))
        assert r["count"] == 2
        assert r["table"] == "users"
        assert len(r["rows"]) == 2
