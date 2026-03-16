"""MCP prompts for SQL assistance."""

from __future__ import annotations

import json

from fastmcp import FastMCP
from fastmcp.prompts import Message
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .engine import get_db
from .resources import _get_table_info


def register_prompts(mcp: FastMCP) -> None:
    """Register all MCP prompts on the given server."""

    @mcp.prompt
    def sql_query(table_names: str, task: str) -> list[Message]:
        """Generate a SQL query for a task using specified tables.

        Args:
            table_names: Comma-separated list of tables to work with.
            task: Description of what the query should do.
        """
        db = get_db()
        names = [n.strip() for n in table_names.split(",") if n.strip()]

        schemas = []
        for name in names:
            try:
                info = _get_table_info(name)
                schemas.append(info)
            except Exception:
                schemas.append({"table_name": name, "error": "Table not found"})

        context = (
            f"Database dialect: {db.dialect_name}\n\n"
            f"Table schemas:\n{json.dumps(schemas, indent=2)}"
        )

        return [
            Message(
                f"You are a SQL expert. Use the following database context to "
                f"write a query.\n\n{context}",
                role="assistant",
            ),
            Message(task),
        ]

    @mcp.prompt
    def explain_schema() -> str:
        """Provide a comprehensive overview of the database schema,
        including all tables, columns, relationships, and indexes.
        """
        db = get_db()
        insp = db.get_inspector()

        lines = [f"Database dialect: {db.dialect_name}\n"]

        for table_name in insp.get_table_names():
            info = _get_table_info(table_name)
            lines.append(f"## Table: {table_name}")

            # Columns
            lines.append("Columns:")
            for col in info["columns"]:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                lines.append(f"  - {col['name']} {col['type']} {nullable}")

            # Primary key
            pk_cols = info["primary_key"]["columns"]
            if pk_cols:
                lines.append(f"Primary key: {', '.join(pk_cols)}")

            # Foreign keys
            for fk in info["foreign_keys"]:
                src = ", ".join(fk["constrained_columns"])
                dst = ", ".join(fk["referred_columns"])
                lines.append(
                    f"FK: ({src}) -> {fk['referred_table']}({dst})"
                )

            # Indexes
            for idx in info["indexes"]:
                uniq = " UNIQUE" if idx["unique"] else ""
                cols = ", ".join(c for c in idx["columns"] if c)
                lines.append(f"Index{uniq}: {idx['name']} ({cols})")

            lines.append("")

        return "\n".join(lines)

    @mcp.prompt
    def optimize_query(sql: str) -> list[Message]:
        """Help optimize a SQL query by providing the execution plan and schema context.

        Args:
            sql: The SQL query to optimize.
        """
        db = get_db()

        # Get EXPLAIN output
        plan = ""
        try:
            with db.connect() as conn:
                result = conn.execute(text(f"EXPLAIN {sql}"))
                plan_rows = result.fetchall()
                conn.rollback()
                plan = "\n".join(str(row) for row in plan_rows)
        except SQLAlchemyError as exc:
            plan = f"Error running EXPLAIN: {exc}"

        # Get schemas for all tables in the database
        insp = db.get_inspector()
        schemas = []
        for table_name in insp.get_table_names():
            try:
                schemas.append(_get_table_info(table_name))
            except Exception:
                pass

        context = (
            f"Database dialect: {db.dialect_name}\n\n"
            f"Query:\n{sql}\n\n"
            f"Execution plan:\n{plan}\n\n"
            f"Database schema:\n{json.dumps(schemas, indent=2)}"
        )

        return [
            Message(
                f"You are a SQL performance expert. Analyze the following query, "
                f"its execution plan, and the database schema. Suggest "
                f"optimizations.\n\n{context}",
                role="assistant",
            ),
            Message(f"Please optimize this query:\n{sql}"),
        ]
