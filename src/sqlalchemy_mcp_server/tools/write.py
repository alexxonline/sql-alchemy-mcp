"""Write MCP tools for modifying database data and schema."""

from __future__ import annotations

import json
import re
from typing import Any

from fastmcp import FastMCP
from sqlalchemy import Column, Index, MetaData, Table, text, types
from sqlalchemy.exc import SQLAlchemyError

from ..engine import get_db

# Blocked SQL patterns even in readwrite mode
_BLOCKED_PATTERNS = re.compile(
    r"^\s*(DROP\s+DATABASE|DROP\s+SCHEMA)\b",
    re.IGNORECASE,
)

# Map of SQL type names to SQLAlchemy type classes
_TYPE_MAP: dict[str, type[types.TypeEngine]] = {
    "INTEGER": types.Integer,
    "INT": types.Integer,
    "BIGINT": types.BigInteger,
    "SMALLINT": types.SmallInteger,
    "VARCHAR": types.String,
    "CHAR": types.String,
    "TEXT": types.Text,
    "FLOAT": types.Float,
    "REAL": types.Float,
    "NUMERIC": types.Numeric,
    "DECIMAL": types.Numeric,
    "BOOLEAN": types.Boolean,
    "BOOL": types.Boolean,
    "DATE": types.Date,
    "DATETIME": types.DateTime,
    "TIMESTAMP": types.DateTime,
    "BLOB": types.LargeBinary,
    "BINARY": types.LargeBinary,
    "JSON": types.JSON,
}

# Regex to parse types like VARCHAR(255) or NUMERIC(10,2)
_TYPE_PATTERN = re.compile(r"^(\w+)(?:\((\d+)(?:,\s*(\d+))?\))?$", re.IGNORECASE)


def parse_sql_type(type_str: str) -> types.TypeEngine:
    """Parse a SQL type string like 'VARCHAR(255)' into a SQLAlchemy type."""
    m = _TYPE_PATTERN.match(type_str.strip())
    if not m:
        raise ValueError(f"Cannot parse SQL type: {type_str}")

    name = m.group(1).upper()
    arg1 = int(m.group(2)) if m.group(2) else None
    arg2 = int(m.group(3)) if m.group(3) else None

    cls = _TYPE_MAP.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown SQL type: {name}. Supported types: "
            f"{', '.join(sorted(_TYPE_MAP))}"
        )

    if arg1 is not None and arg2 is not None:
        return cls(arg1, arg2)
    elif arg1 is not None:
        return cls(arg1)
    else:
        return cls()


def register_write_tools(mcp: FastMCP) -> None:
    """Register all write tools on the given FastMCP server."""

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
        }
    )
    def execute(sql: str, params: dict[str, Any] | None = None) -> str:
        """Execute a SQL statement (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, etc.).

        Args:
            sql: The SQL statement to execute.
            params: Optional dictionary of named bind parameters.
        """
        if _BLOCKED_PATTERNS.match(sql):
            return json.dumps(
                {"error": "This operation is blocked for safety reasons."}
            )

        db = get_db()
        try:
            with db.connect() as conn:
                result = conn.execute(text(sql), params or {})

                response: dict[str, Any] = {
                    "status": "success",
                    "rows_affected": result.rowcount,
                }

                # Include returned rows if the statement produces them
                if result.returns_rows:
                    rows = [dict(r) for r in result.mappings().all()]
                    response["rows"] = rows

                conn.commit()
                return json.dumps(response)
        except SQLAlchemyError as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": False})
    def execute_many(sql: str, params_list: list[dict[str, Any]]) -> str:
        """Execute a SQL statement multiple times with different parameters.

        Args:
            sql: The SQL statement with named bind parameters.
            params_list: List of parameter dictionaries, one per execution.
        """
        if _BLOCKED_PATTERNS.match(sql):
            return json.dumps(
                {"error": "This operation is blocked for safety reasons."}
            )

        db = get_db()
        try:
            with db.connect() as conn:
                result = conn.execute(text(sql), params_list)
                conn.commit()
                return json.dumps(
                    {
                        "status": "success",
                        "rows_affected": result.rowcount,
                        "executions": len(params_list),
                    }
                )
        except SQLAlchemyError as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
    def create_table(
        table_name: str,
        columns: list[dict[str, Any]],
        schema: str | None = None,
    ) -> str:
        """Create a new table.

        Args:
            table_name: Name for the new table.
            columns: List of column definitions. Each dict should have:
                - name (str): Column name
                - type (str): Column type (e.g., "INTEGER", "VARCHAR(255)", "TEXT")
                - primary_key (bool, optional): Whether this is a primary key
                - nullable (bool, optional): Whether NULL is allowed (default True)
                - default (str, optional): Default value expression
            schema: Optional schema name.
        """
        db = get_db()
        try:
            sa_columns = []
            for col_def in columns:
                col_type = parse_sql_type(col_def["type"])
                sa_columns.append(
                    Column(
                        col_def["name"],
                        col_type,
                        primary_key=col_def.get("primary_key", False),
                        nullable=col_def.get("nullable", True),
                        server_default=text(col_def["default"])
                        if col_def.get("default")
                        else None,
                    )
                )

            metadata = MetaData()
            table = Table(table_name, metadata, *sa_columns, schema=schema)
            table.create(db.get_engine())
            return json.dumps(
                {"status": "success", "table": table_name, "schema": schema}
            )
        except (SQLAlchemyError, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True})
    def drop_table(table_name: str, schema: str | None = None) -> str:
        """Drop a table from the database.

        Args:
            table_name: Name of the table to drop.
            schema: Optional schema name.
        """
        db = get_db()
        try:
            engine = db.get_engine()
            metadata = MetaData()
            table = Table(table_name, metadata, autoload_with=engine, schema=schema)
            table.drop(engine)
            return json.dumps(
                {"status": "success", "dropped": table_name, "schema": schema}
            )
        except SQLAlchemyError as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
    def add_column(
        table_name: str,
        column_name: str,
        column_type: str,
        nullable: bool = True,
        default: str | None = None,
        schema: str | None = None,
    ) -> str:
        """Add a new column to an existing table.

        Args:
            table_name: Target table name.
            column_name: Name for the new column.
            column_type: SQL type (e.g., "VARCHAR(100)", "INTEGER").
            nullable: Whether NULL values are allowed.
            default: Optional default value expression.
            schema: Optional schema name.
        """
        db = get_db()
        try:
            col_type = parse_sql_type(column_type)
            col = Column(column_name, col_type, nullable=nullable)

            # Build dialect-aware ALTER TABLE DDL
            full_table = f"{schema}.{table_name}" if schema else table_name
            col_sql = f"{column_name} {col_type.compile(db.get_engine().dialect)}"
            if not nullable:
                col_sql += " NOT NULL"
            if default is not None:
                col_sql += f" DEFAULT {default}"

            ddl = f"ALTER TABLE {full_table} ADD COLUMN {col_sql}"
            with db.connect() as conn:
                conn.execute(text(ddl))
                conn.commit()

            return json.dumps(
                {
                    "status": "success",
                    "table": table_name,
                    "column": column_name,
                    "type": str(col_type),
                }
            )
        except (SQLAlchemyError, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
    def create_index(
        index_name: str,
        table_name: str,
        columns: list[str],
        unique: bool = False,
        schema: str | None = None,
    ) -> str:
        """Create an index on a table.

        Args:
            index_name: Name for the index.
            table_name: Table to index.
            columns: List of column names to include in the index.
            unique: Whether to create a unique index.
            schema: Optional schema name.
        """
        db = get_db()
        try:
            engine = db.get_engine()
            metadata = MetaData()
            table = Table(table_name, metadata, autoload_with=engine, schema=schema)

            idx = Index(
                index_name,
                *[table.c[col] for col in columns],
                unique=unique,
            )
            idx.create(engine)
            return json.dumps(
                {
                    "status": "success",
                    "index": index_name,
                    "table": table_name,
                    "columns": columns,
                    "unique": unique,
                }
            )
        except (SQLAlchemyError, KeyError) as exc:
            return json.dumps({"error": str(exc)})
