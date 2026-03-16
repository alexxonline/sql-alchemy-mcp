"""CLI mode for one-shot command execution."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from fastmcp import FastMCP


# Write-only tools that require readwrite mode
_WRITE_TOOLS = {"execute", "execute_many", "create_table", "drop_table", "add_column", "create_index"}

# Resource subcommand -> URI pattern (use {arg_name} for template params)
_RESOURCE_MAP = {
    "schema": "db://schema",
    "tables": "db://tables",
    "table": "db://tables/{table_name}",
    "table-ddl": "db://tables/{table_name}/ddl",
    "table-sample": "db://tables/{table_name}/sample?limit={limit}",
}


def _format_output(data: str, compact: bool = False, fmt: str = "json") -> str:
    """Format output based on user preferences."""
    if fmt == "table":
        return _format_as_table(data)
    if compact:
        try:
            parsed = json.loads(data)
            return json.dumps(parsed, separators=(",", ":"))
        except (json.JSONDecodeError, TypeError):
            return data
    try:
        parsed = json.loads(data)
        return json.dumps(parsed, indent=2)
    except (json.JSONDecodeError, TypeError):
        return data


def _format_as_table(data: str) -> str:
    """Format JSON data as a plain text table."""
    try:
        parsed = json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return data

    rows = None
    if isinstance(parsed, dict) and "rows" in parsed:
        rows = parsed["rows"]
    elif isinstance(parsed, list):
        rows = parsed

    if not rows or not isinstance(rows, list) or not isinstance(rows[0], dict):
        return json.dumps(parsed, indent=2)

    headers = list(rows[0].keys())
    col_widths = {h: len(h) for h in headers}
    str_rows = []
    for row in rows:
        str_row = {h: str(row.get(h, "")) for h in headers}
        for h in headers:
            col_widths[h] = max(col_widths[h], len(str_row[h]))
        str_rows.append(str_row)

    header_line = "  ".join(h.ljust(col_widths[h]) for h in headers)
    separator = "  ".join("-" * col_widths[h] for h in headers)
    lines = [header_line, separator]
    for str_row in str_rows:
        lines.append("  ".join(str_row[h].ljust(col_widths[h]) for h in headers))

    return "\n".join(lines)


def _add_format_args(parser: argparse.ArgumentParser) -> None:
    """Add --compact and --format flags to a parser."""
    parser.add_argument(
        "--compact", action="store_true", default=False,
        help="Output minified JSON (useful for piping)",
    )
    parser.add_argument(
        "--format", dest="output_format", choices=["json", "table"],
        default="json", help="Output format (default: json)",
    )


def _parse_json_arg(value: str, name: str) -> Any:
    """Parse a JSON string argument, raising a clear error on failure."""
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid JSON for --{name}: {exc}"
        )


def build_cli_parser(server: FastMCP, mode: str) -> argparse.ArgumentParser:
    """Build an argparse parser from registered MCP tools, resources, and prompts."""
    parser = argparse.ArgumentParser(
        prog="sqlalchemy-mcp-server --cli",
        description="Execute database operations from the command line",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # --- Tools ---
    tools = asyncio.run(_list_tools(server))
    for tool in tools:
        name = tool.name
        desc = tool.description or ""
        # Mark write tools
        if name in _WRITE_TOOLS and mode != "readwrite":
            continue  # Don't register write tools in readonly mode
        sub = subparsers.add_parser(name, help=desc)
        _add_format_args(sub)
        _add_tool_args(sub, tool.parameters)

    # --- Resources ---
    resource_parser = subparsers.add_parser("resource", help="Access database resources")
    resource_subs = resource_parser.add_subparsers(dest="resource_command", help="Resource to access")

    for res_name, uri_pattern in _RESOURCE_MAP.items():
        sub = resource_subs.add_parser(res_name, help=f"Read {uri_pattern}")
        _add_format_args(sub)
        # Extract template params from URI pattern
        import re
        for param in re.findall(r"\{(\w+)\}", uri_pattern):
            if param == "limit":
                sub.add_argument(f"--{param}", type=int, default=5, help=f"{param}")
            else:
                sub.add_argument(
                    f"--{param.replace('_', '-')}",
                    dest=param, required=True, help=param,
                )

    # --- Prompts ---
    prompt_parser = subparsers.add_parser("prompt", help="Render MCP prompts")
    prompt_subs = prompt_parser.add_subparsers(dest="prompt_command", help="Prompt to render")

    prompts = asyncio.run(_list_prompts(server))
    for prompt in prompts:
        sub = prompt_subs.add_parser(prompt.name, help=prompt.description or "")
        _add_format_args(sub)
        if prompt.arguments:
            for arg in prompt.arguments:
                flag = f"--{arg.name.replace('_', '-')}"
                sub.add_argument(
                    flag, dest=arg.name,
                    required=arg.required,
                    help=arg.description or arg.name,
                )

    return parser


def _add_tool_args(sub: argparse.ArgumentParser, parameters: dict[str, Any]) -> None:
    """Add argparse arguments from a tool's JSON Schema parameters."""
    props = parameters.get("properties", {})
    required = set(parameters.get("required", []))

    for param_name, schema in props.items():
        flag = f"--{param_name.replace('_', '-')}"
        kwargs: dict[str, Any] = {"dest": param_name}

        json_type = schema.get("type", "string")
        is_required = param_name in required

        if json_type == "boolean":
            kwargs["action"] = "store_true"
            kwargs["default"] = schema.get("default", False)
        elif json_type == "integer":
            kwargs["type"] = int
            kwargs["default"] = schema.get("default")
            kwargs["required"] = is_required
        elif json_type == "number":
            kwargs["type"] = float
            kwargs["default"] = schema.get("default")
            kwargs["required"] = is_required
        elif json_type in ("object", "array"):
            # Accept as JSON string
            kwargs["type"] = str
            kwargs["default"] = schema.get("default")
            kwargs["required"] = is_required
            kwargs["metavar"] = "JSON"
        else:
            kwargs["type"] = str
            kwargs["default"] = schema.get("default")
            kwargs["required"] = is_required

        # Description from schema
        desc = schema.get("description", param_name)
        if json_type in ("object", "array"):
            desc = f"{desc} (as JSON string)"
        kwargs["help"] = desc

        sub.add_argument(flag, **kwargs)


async def _list_tools(server: FastMCP):
    return await server.list_tools()


async def _list_prompts(server: FastMCP):
    return await server.list_prompts()


async def _call_tool(server: FastMCP, name: str, arguments: dict[str, Any]) -> str:
    result = await server.call_tool(name, arguments)
    parts = []
    for content in result.content:
        parts.append(content.text)
    return "\n".join(parts)


async def _read_resource(server: FastMCP, uri: str) -> str:
    result = await server.read_resource(uri)
    parts = []
    for content in result.contents:
        parts.append(content.content)
    return "\n".join(parts)


async def _render_prompt(server: FastMCP, name: str, arguments: dict[str, Any]) -> str:
    result = await server.render_prompt(name, arguments)
    parts = []
    for msg in result.messages:
        role = msg.role
        text = msg.content.text if hasattr(msg.content, "text") else str(msg.content)
        parts.append(f"[{role}]\n{text}")
    return "\n\n".join(parts)


def _build_tool_arguments(args: argparse.Namespace, parameters: dict[str, Any]) -> dict[str, Any]:
    """Build tool arguments dict from parsed CLI args, parsing JSON strings for complex types."""
    props = parameters.get("properties", {})
    arguments = {}
    for param_name, schema in props.items():
        value = getattr(args, param_name, None)
        if value is None:
            continue
        json_type = schema.get("type", "string")
        if json_type in ("object", "array") and isinstance(value, str):
            value = _parse_json_arg(value, param_name)
        arguments[param_name] = value
    return arguments


def run_cli(server: FastMCP, cli_args: list[str], mode: str) -> None:
    """Parse CLI arguments and execute the requested command."""
    parser = build_cli_parser(server, mode)
    args = parser.parse_args(cli_args)

    if not args.command:
        parser.print_help()
        sys.exit(2)

    compact = getattr(args, "compact", False)
    output_format = getattr(args, "output_format", "json")

    try:
        if args.command == "resource":
            result = _dispatch_resource(server, args)
        elif args.command == "prompt":
            result = _dispatch_prompt(server, args)
        else:
            result = _dispatch_tool(server, args)

        print(_format_output(result, compact=compact, fmt=output_format))
        sys.exit(0)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _dispatch_tool(server: FastMCP, args: argparse.Namespace) -> str:
    """Dispatch a tool subcommand."""
    tool_name = args.command

    # Find the tool's parameter schema
    tools = asyncio.run(_list_tools(server))
    tool = next((t for t in tools if t.name == tool_name), None)
    if tool is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    arguments = _build_tool_arguments(args, tool.parameters)
    return asyncio.run(_call_tool(server, tool_name, arguments))


def _dispatch_resource(server: FastMCP, args: argparse.Namespace) -> str:
    """Dispatch a resource subcommand."""
    res_cmd = getattr(args, "resource_command", None)
    if not res_cmd:
        raise ValueError("No resource specified. Use --help for available resources.")

    uri_pattern = _RESOURCE_MAP.get(res_cmd)
    if not uri_pattern:
        raise ValueError(f"Unknown resource: {res_cmd}")

    # Build URI from pattern and args
    import re
    params = re.findall(r"\{(\w+)\}", uri_pattern)
    uri = uri_pattern
    for param in params:
        value = getattr(args, param, None)
        if value is None:
            raise ValueError(f"Missing required argument: --{param.replace('_', '-')}")
        uri = uri.replace(f"{{{param}}}", str(value))

    return asyncio.run(_read_resource(server, uri))


def _dispatch_prompt(server: FastMCP, args: argparse.Namespace) -> str:
    """Dispatch a prompt subcommand."""
    prompt_name = getattr(args, "prompt_command", None)
    if not prompt_name:
        raise ValueError("No prompt specified. Use --help for available prompts.")

    prompts = asyncio.run(_list_prompts(server))
    prompt = next((p for p in prompts if p.name == prompt_name), None)
    if prompt is None:
        raise ValueError(f"Unknown prompt: {prompt_name}")

    arguments = {}
    if prompt.arguments:
        for arg in prompt.arguments:
            value = getattr(args, arg.name, None)
            if value is not None:
                arguments[arg.name] = value

    return asyncio.run(_render_prompt(server, prompt_name, arguments))
