"""Read-only MCP tools for querying and introspecting databases."""

from __future__ import annotations

import json
import re
from typing import Any

from fastmcp import FastMCP
from sqlalchemy import MetaData, Table, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateTable

from ..engine import get_db

# Allowed statement prefixes for the query tool
_ALLOWED_PREFIXES = re.compile(
    r"^\s*(SELECT|WITH|EXPLAIN|SHOW|DESCRIBE|PRAGMA)\b",
    re.IGNORECASE,
)


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert row values to JSON-serializable types."""
    out = {}
    for k, v in row.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def register_read_tools(mcp: FastMCP) -> None:
    """Register all read-only tools on the given FastMCP server."""

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        }
    )
    def query(
        sql: str,
        params: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> str:
        """Execute a read-only SQL query and return results as JSON.

        Args:
            sql: A SELECT SQL statement to execute.
            params: Optional dictionary of named bind parameters.
            limit: Maximum number of rows to return (default 1000).
        """
        if not _ALLOWED_PREFIXES.match(sql):
            return json.dumps(
                {
                    "error": "Only SELECT, WITH, EXPLAIN, SHOW, DESCRIBE, "
                    "and PRAGMA statements are allowed."
                }
            )

        db = get_db()
        try:
            with db.connect() as conn:
                result = conn.execute(text(sql), params or {})
                rows = [
                    _serialize_row(dict(r)) for r in result.mappings().fetchmany(limit)
                ]
                # Always rollback — read-only
                conn.rollback()
                return json.dumps({"rows": rows, "count": len(rows)})
        except SQLAlchemyError as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": True})
    def list_tables(schema: str | None = None) -> str:
        """List all tables and views in the database.

        Args:
            schema: Optional schema name to filter by.
        """
        db = get_db()
        try:
            insp = db.get_inspector()
            items = [
                {"name": t, "type": "table"}
                for t in insp.get_table_names(schema=schema)
            ]
            items.extend(
                {"name": v, "type": "view"}
                for v in insp.get_view_names(schema=schema)
            )
            return json.dumps(items)
        except SQLAlchemyError as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": True})
    def describe_table(table_name: str, schema: str | None = None) -> str:
        """Describe a table's columns, primary keys, foreign keys, and indexes.

        Args:
            table_name: Name of the table to describe.
            schema: Optional schema name.
        """
        db = get_db()
        try:
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
            foreign_keys = []
            for fk in insp.get_foreign_keys(table_name, schema=schema):
                foreign_keys.append(
                    {
                        "name": fk.get("name"),
                        "constrained_columns": fk["constrained_columns"],
                        "referred_schema": fk.get("referred_schema"),
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"],
                    }
                )

            indexes = []
            for idx in insp.get_indexes(table_name, schema=schema):
                indexes.append(
                    {
                        "name": idx["name"],
                        "columns": idx["column_names"],
                        "unique": idx.get("unique", False),
                    }
                )

            unique_constraints = []
            for uc in insp.get_unique_constraints(table_name, schema=schema):
                unique_constraints.append(
                    {
                        "name": uc.get("name"),
                        "columns": uc["column_names"],
                    }
                )

            return json.dumps(
                {
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
            )
        except SQLAlchemyError as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": True})
    def list_schemas() -> str:
        """List all schemas in the database."""
        db = get_db()
        try:
            insp = db.get_inspector()
            return json.dumps(insp.get_schema_names())
        except SQLAlchemyError as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": True})
    def get_table_ddl(table_name: str, schema: str | None = None) -> str:
        """Get the DDL (CREATE TABLE statement) for a table.

        Args:
            table_name: Name of the table.
            schema: Optional schema name.
        """
        db = get_db()
        try:
            engine = db.get_engine()
            metadata = MetaData()
            table = Table(
                table_name, metadata, autoload_with=engine, schema=schema
            )
            return str(CreateTable(table).compile(engine))
        except SQLAlchemyError as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": True})
    def explain_query(sql: str) -> str:
        """Get the execution plan for a SQL query.

        Args:
            sql: The SQL query to explain (must be a SELECT statement).
        """
        if not re.match(r"^\s*(SELECT|WITH)\b", sql, re.IGNORECASE):
            return json.dumps(
                {"error": "Only SELECT and WITH statements can be explained."}
            )

        db = get_db()
        try:
            explain_sql = f"EXPLAIN {sql}"
            with db.connect() as conn:
                result = conn.execute(text(explain_sql))
                plan_rows = result.fetchall()
                conn.rollback()
                plan = "\n".join(str(row) for row in plan_rows)
                return plan
        except SQLAlchemyError as exc:
            return json.dumps({"error": str(exc)})
