"""Tests for CLI argument parsing."""

import os

import pytest

from sqlalchemy_mcp_server.__main__ import parse_args


class TestCLI:
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
        config = parse_args(["--db-url", "sqlite://"])
        assert config.mode == "readonly"

    def test_readwrite_mode(self):
        config = parse_args(["--db-url", "sqlite://", "--mode", "readwrite"])
        assert config.mode == "readwrite"

    def test_env_var_db_url(self, monkeypatch):
        monkeypatch.setenv("SQLALCHEMY_MCP_DB_URL", "sqlite:///from_env.db")
        config = parse_args([])
        assert config.db_url == "sqlite:///from_env.db"

    def test_cli_overrides_env_var(self, monkeypatch):
        monkeypatch.setenv("SQLALCHEMY_MCP_DB_URL", "sqlite:///from_env.db")
        config = parse_args(["--db-url", "sqlite:///from_cli.db"])
        assert config.db_url == "sqlite:///from_cli.db"

    def test_default_transport(self):
        config = parse_args(["--db-url", "sqlite://"])
        assert config.transport == "stdio"

    def test_default_pool_settings(self):
        config = parse_args(["--db-url", "sqlite://"])
        assert config.pool_size == 5
        assert config.pool_pre_ping is True

    def test_no_pool_pre_ping(self):
        config = parse_args(["--db-url", "sqlite://", "--no-pool-pre-ping"])
        assert config.pool_pre_ping is False
