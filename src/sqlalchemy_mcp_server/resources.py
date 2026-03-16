"""MCP resources for browsable database metadata."""

from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP
from sqlalchemy import MetaData, Table, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateTable

from .engine import get_db


def _validate_table_name(table_name: str) -> str | None:
    """Check table_name exists in the database. Returns error string or None."""
    db = get_db()
    insp = db.get_inspector()
    valid = set(insp.get_table_names()) | set(insp.get_view_names())
    if table_name not in valid:
        return f"Table or view '{table_name}' not found."
    return None


def _get_table_info(table_name: str, schema: str | None = None) -> dict[str, Any]:
    """Shared introspection logic for a single table."""
    db = get_db()
    insp = db.get_inspector()

    columns = []
    for col in insp.get_columns(table_name, schema=schema):
        columns.append(
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "default": str(col["default"]) if col.get("default") else None,
                "autoincrement": col.get("autoincrement", False),
            }
        )

    pk = insp.get_pk_constraint(table_name, schema=schema)
    foreign_keys = [
        {
            "name": fk.get("name"),
            "constrained_columns": fk["constrained_columns"],
            "referred_schema": fk.get("referred_schema"),
            "referred_table": fk["referred_table"],
            "referred_columns": fk["referred_columns"],
        }
        for fk in insp.get_foreign_keys(table_name, schema=schema)
    ]
    indexes = [
        {
            "name": idx["name"],
            "columns": idx["column_names"],
            "unique": idx.get("unique", False),
        }
        for idx in insp.get_indexes(table_name, schema=schema)
    ]
    unique_constraints = [
        {"name": uc.get("name"), "columns": uc["column_names"]}
        for uc in insp.get_unique_constraints(table_name, schema=schema)
    ]

    return {
        "table_name": table_name,
        "schema": schema,
        "columns": columns,
        "primary_key": {
            "name": pk.get("name"),
            "columns": pk.get("constrained_columns", []),
        },
        "foreign_keys": foreign_keys,
        "indexes": indexes,
        "unique_constraints": unique_constraints,
    }


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in row.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def register_resources(mcp: FastMCP, mode: str) -> None:
    """Register all MCP resources on the given server."""

    @mcp.resource("db://schema")
    def get_schema_overview() -> str:
        """Overview of the database: dialect, tables, and schema names."""
        db = get_db()
        insp = db.get_inspector()
        return json.dumps(
            {
                "dialect": db.dialect_name,
                "driver": db.driver_name,
                "schemas": insp.get_schema_names(),
                "tables_count": len(insp.get_table_names()),
                "mode": mode,
            }
        )

    @mcp.resource("db://tables")
    def get_tables_list() -> str:
        """List of all tables and views in the database."""
        db = get_db()
        insp = db.get_inspector()
        items = [{"name": t, "type": "table"} for t in insp.get_table_names()]
        items.extend({"name": v, "type": "view"} for v in insp.get_view_names())
        return json.dumps(items)

    @mcp.resource("db://tables/{table_name}")
    def get_table_details(table_name: str) -> str:
        """Detailed schema information for a specific table."""
        err = _validate_table_name(table_name)
        if err:
            return json.dumps({"error": err})
        return json.dumps(_get_table_info(table_name))

    @mcp.resource("db://tables/{table_name}/ddl", mime_type="text/sql")
    def get_table_ddl_resource(table_name: str) -> str:
        """CREATE TABLE DDL statement for a specific table."""
        err = _validate_table_name(table_name)
        if err:
            return json.dumps({"error": err})
        db = get_db()
        engine = db.get_engine()
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=engine)
        return str(CreateTable(table).compile(engine))

    @mcp.resource("db://tables/{table_name}/sample{?limit}")
    def get_table_sample(table_name: str, limit: int = 5) -> str:
        """Sample rows from a table for quick data exploration."""
        err = _validate_table_name(table_name)
        if err:
            return json.dumps({"error": err})
        db = get_db()
        try:
            with db.connect() as conn:
                result = conn.execute(
                    text(f"SELECT * FROM {table_name} LIMIT :lim"), {"lim": limit}
                )
                rows = [_serialize_row(dict(r)) for r in result.mappings().all()]
                conn.rollback()
                return json.dumps({"table": table_name, "rows": rows, "count": len(rows)})
        except SQLAlchemyError as exc:
            return json.dumps({"error": str(exc)})
