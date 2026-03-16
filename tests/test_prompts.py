"""Tests for MCP prompts."""

import pytest


class TestSqlQueryPrompt:
    @pytest.mark.asyncio
    async def test_sql_query_prompt(self, readonly_server):
        r = await readonly_server.render_prompt(
            "sql_query",
            {"table_names": "users,orders", "task": "Find users with orders over 75"},
        )
        msgs = r.messages
        assert len(msgs) == 2
        context = msgs[0].content.text
        assert "sqlite" in context
        assert "users" in context
        assert "orders" in context


class TestExplainSchemaPrompt:
    @pytest.mark.asyncio
    async def test_explain_schema_prompt(self, readonly_server):
        r = await readonly_server.render_prompt("explain_schema", {})
        text = r.messages[0].content.text
        assert "users" in text
        assert "orders" in text
        assert "FK" in text


class TestOptimizeQueryPrompt:
    @pytest.mark.asyncio
    async def test_optimize_query_prompt(self, readonly_server):
        r = await readonly_server.render_prompt(
            "optimize_query",
            {"sql": "SELECT * FROM users WHERE id = 1"},
        )
        msgs = r.messages
        assert len(msgs) == 2
        context = msgs[0].content.text
        assert "Execution plan" in context
        assert "SELECT * FROM users WHERE id = 1" in context
