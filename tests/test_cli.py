"""Tests for CLI argument parsing and CLI mode execution."""

import json
import os

import pytest

from sqlalchemy_mcp_server.__main__ import parse_args


class TestParseArgs:
    def test_help_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "sqlalchemy-mcp-server" in captured.out

    def test_missing_db_url(self):
        with pytest.raises(SystemExit) as exc_info:
            parse_args([])
        assert exc_info.value.code == 2

    def test_invalid_mode(self):
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--db-url", "sqlite://", "--mode", "invalid"])
        assert exc_info.value.code == 2

    def test_default_mode(self):
        config, cli_args = parse_args(["--db-url", "sqlite://"])
        assert config.mode == "readonly"
        assert cli_args is None

    def test_readwrite_mode(self):
        config, _ = parse_args(["--db-url", "sqlite://", "--mode", "readwrite"])
        assert config.mode == "readwrite"

    def test_env_var_db_url(self, monkeypatch):
        monkeypatch.setenv("SQLALCHEMY_MCP_DB_URL", "sqlite:///from_env.db")
        config, _ = parse_args([])
        assert config.db_url == "sqlite:///from_env.db"

    def test_cli_overrides_env_var(self, monkeypatch):
        monkeypatch.setenv("SQLALCHEMY_MCP_DB_URL", "sqlite:///from_env.db")
        config, _ = parse_args(["--db-url", "sqlite:///from_cli.db"])
        assert config.db_url == "sqlite:///from_cli.db"

    def test_default_transport(self):
        config, _ = parse_args(["--db-url", "sqlite://"])
        assert config.transport == "stdio"

    def test_default_pool_settings(self):
        config, _ = parse_args(["--db-url", "sqlite://"])
        assert config.pool_size == 5
        assert config.pool_pre_ping is True

    def test_no_pool_pre_ping(self):
        config, _ = parse_args(["--db-url", "sqlite://", "--no-pool-pre-ping"])
        assert config.pool_pre_ping is False

    def test_cli_flag_returns_cli_args(self):
        config, cli_args = parse_args(["--db-url", "sqlite://", "--cli", "query", "--sql", "SELECT 1"])
        assert cli_args == ["query", "--sql", "SELECT 1"]

    def test_cli_flag_empty(self):
        config, cli_args = parse_args(["--db-url", "sqlite://", "--cli"])
        assert cli_args == []


class TestCLITools:
    """Test CLI tool dispatch."""

    def test_query(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["query", "--sql", "SELECT * FROM users"], mode="readonly")
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["count"] == 2
        assert len(output["rows"]) == 2

    def test_query_with_limit(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["query", "--sql", "SELECT * FROM users", "--limit", "1"], mode="readonly")
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["count"] == 1

    def test_query_compact(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["query", "--sql", "SELECT * FROM users", "--compact"], mode="readonly")
        assert exc_info.value.code == 0
        out = capsys.readouterr().out.strip()
        # Compact JSON has no spaces after separators
        assert "  " not in out
        assert json.loads(out)["count"] == 2

    def test_query_table_format(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["query", "--sql", "SELECT * FROM users", "--format", "table"], mode="readonly")
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "Alice" in out
        assert "Bob" in out
        # Table format has header separator
        assert "---" in out

    def test_list_tables(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["list_tables"], mode="readonly")
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        names = [t["name"] for t in output]
        assert "users" in names
        assert "orders" in names

    def test_describe_table(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["describe_table", "--table-name", "users"], mode="readonly")
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["table_name"] == "users"
        col_names = [c["name"] for c in output["columns"]]
        assert "id" in col_names
        assert "name" in col_names

    def test_list_schemas(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["list_schemas"], mode="readonly")
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert "main" in output

    def test_get_table_ddl(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["get_table_ddl", "--table-name", "users"], mode="readonly")
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "CREATE TABLE" in out

    def test_explain_query(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["explain_query", "--sql", "SELECT * FROM users"], mode="readonly")
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert out.strip()  # Non-empty

    def test_no_command_exits_2(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, [], mode="readonly")
        assert exc_info.value.code == 2


class TestCLIWriteTools:
    """Test CLI write tool dispatch."""

    def test_write_tools_hidden_in_readonly(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["execute", "--sql", "INSERT INTO users (name) VALUES ('test')"], mode="readonly")
        # argparse error: unrecognized command
        assert exc_info.value.code == 2

    def test_execute(self, readwrite_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(
                readwrite_server,
                ["execute", "--sql", "INSERT INTO users (name, email) VALUES ('Charlie', 'charlie@test.com')"],
                mode="readwrite",
            )
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"

    def test_create_table(self, readwrite_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        columns = json.dumps([
            {"name": "id", "type": "INTEGER", "primary_key": True},
            {"name": "title", "type": "TEXT"},
        ])
        with pytest.raises(SystemExit) as exc_info:
            run_cli(
                readwrite_server,
                ["create_table", "--table-name", "events", "--columns", columns],
                mode="readwrite",
            )
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["table"] == "events"


class TestCLIResources:
    """Test CLI resource dispatch."""

    def test_resource_schema(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["resource", "schema"], mode="readonly")
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["dialect"] == "sqlite"

    def test_resource_tables(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["resource", "tables"], mode="readonly")
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        names = [t["name"] for t in output]
        assert "users" in names

    def test_resource_table_details(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["resource", "table", "--table-name", "users"], mode="readonly")
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["table_name"] == "users"

    def test_resource_table_ddl(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["resource", "table-ddl", "--table-name", "users"], mode="readonly")
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "CREATE TABLE" in out

    def test_resource_table_sample(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["resource", "table-sample", "--table-name", "users", "--limit", "1"], mode="readonly")
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["count"] == 1

    def test_resource_no_subcommand(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["resource"], mode="readonly")
        assert exc_info.value.code == 1


class TestCLIPrompts:
    """Test CLI prompt dispatch."""

    def test_prompt_explain_schema(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["prompt", "explain_schema"], mode="readonly")
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "users" in out
        assert "sqlite" in out

    def test_prompt_sql_query(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["prompt", "sql_query", "--table-names", "users", "--task", "list all"], mode="readonly")
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "users" in out
        assert "list all" in out

    def test_prompt_no_subcommand(self, readonly_server, capsys):
        from sqlalchemy_mcp_server.cli import run_cli

        with pytest.raises(SystemExit) as exc_info:
            run_cli(readonly_server, ["prompt"], mode="readonly")
        assert exc_info.value.code == 1
