"""Tests for mode-based tool visibility."""

import pytest

READ_TOOLS = {
    "query",
    "list_tables",
    "describe_table",
    "list_schemas",
    "get_table_ddl",
    "explain_query",
}

WRITE_TOOLS = {
    "execute",
    "execute_many",
    "create_table",
    "drop_table",
    "add_column",
    "create_index",
}


class TestModeEnforcement:
    @pytest.mark.asyncio
    async def test_readonly_has_read_tools(self, readonly_server):
        tools = await readonly_server.list_tools()
        names = {t.name for t in tools}
        assert READ_TOOLS.issubset(names)

    @pytest.mark.asyncio
    async def test_readonly_no_write_tools(self, readonly_server):
        tools = await readonly_server.list_tools()
        names = {t.name for t in tools}
        assert WRITE_TOOLS.isdisjoint(names)

    @pytest.mark.asyncio
    async def test_readwrite_has_all_tools(self, readwrite_server):
        tools = await readwrite_server.list_tools()
        names = {t.name for t in tools}
        assert READ_TOOLS.issubset(names)
        assert WRITE_TOOLS.issubset(names)
