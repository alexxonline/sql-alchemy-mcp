# Iteration 8: CLI Mode

## Goal

Expose every MCP tool, resource, and prompt as a synchronous command-line interface. When invoked in CLI mode the program executes a single operation, prints the result to stdout, and exits. No server is started; no long-running process is kept alive.

## Motivation

Users should be able to interact with the database directly from a terminal without needing an MCP client. This is useful for scripting, debugging, quick one-off queries, and integrating with shell pipelines.

## CLI Activation

A new top-level flag `--cli` switches the program from MCP-server mode to CLI mode.

```
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli <command> [args...]
```

If `--cli` is not provided, the program behaves as it does today (starts the MCP server). The existing `--mode readonly|readwrite` flag still applies — write commands are rejected in readonly mode.

## Command Mapping

Every registered MCP tool, resource, and prompt maps 1:1 to a CLI subcommand. The subcommand name matches the tool/resource/prompt name.

### Tools as subcommands

Each tool parameter becomes a CLI argument. Required parameters are positional or required flags; optional parameters are optional flags with defaults.

```bash
# query tool
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli query --sql "SELECT * FROM users" --params '{"id": 1}'

# list_tables tool
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli list_tables --schema public

# describe_table tool
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli describe_table --table-name users

# execute tool (requires --mode readwrite)
sqlalchemy-mcp-server --db-url sqlite:///my.db --mode readwrite --cli execute --sql "INSERT INTO users (name) VALUES ('alice')"

# create_table tool (requires --mode readwrite)
sqlalchemy-mcp-server --db-url sqlite:///my.db --mode readwrite --cli create_table --table-name events --columns '[{"name": "id", "type": "INTEGER", "primary_key": true}, {"name": "title", "type": "TEXT"}]'

# All other tools follow the same pattern: subcommand name = tool name, flags = tool parameters
```

### Resources as subcommands

Resource URIs become subcommands under a `resource` namespace. Template parameters become CLI flags.

```bash
# db://schema
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli resource schema

# db://tables
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli resource tables

# db://tables/{table_name}
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli resource table --table-name users

# db://tables/{table_name}/ddl
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli resource table-ddl --table-name users

# db://tables/{table_name}/sample
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli resource table-sample --table-name users --limit 10
```

### Prompts as subcommands

Prompts become subcommands under a `prompt` namespace. Prompt arguments become CLI flags. The output is the rendered prompt text (not sent to an LLM — just printed).

```bash
# sql_query prompt
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli prompt sql_query --table-names "users,orders" --task "find all users with no orders"

# explain_schema prompt
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli prompt explain_schema

# optimize_query prompt
sqlalchemy-mcp-server --db-url sqlite:///my.db --cli prompt optimize_query --sql "SELECT * FROM users WHERE name = 'alice'"
```

## Implementation

### Entry point changes (`__main__.py`)

Add `--cli` flag to the argument parser. When present, instead of calling `mcp.run()`:

1. Parse the subcommand and its arguments.
2. Initialize the engine (same as server mode).
3. Call the corresponding tool/resource/prompt function directly.
4. Print the result to stdout.
5. Dispose the engine.
6. Exit with code 0 on success, 1 on error.

```python
# Pseudocode
def main():
    args = parse_args()

    if args.cli:
        run_cli(args)
    else:
        run_server(args)


def run_cli(args):
    engine = create_engine(args.db_url)
    try:
        result = dispatch_command(args.command, args.command_args)
        print(result)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        engine.dispose()
```

### CLI module (`cli.py`)

A new module that handles:

1. **Subcommand registration** — Introspect the registered MCP tools, resources, and prompts from the server instance and build an `argparse` subparser for each one. Tool parameter types and defaults map to argparse argument types and defaults.
2. **Dispatch** — Given a parsed subcommand, call the underlying function with the parsed arguments.
3. **Output formatting** — JSON output is pretty-printed by default. A `--compact` flag outputs minified JSON (useful for piping). A `--format` flag supports `json` (default) and `table` for human-readable tabular output.

```python
def build_cli_parser(server: FastMCP) -> argparse.ArgumentParser:
    """Build argparse parser from registered MCP tools, resources, and prompts."""
    ...

def dispatch_command(server: FastMCP, namespace: str, command: str, args: dict) -> str:
    """Call the underlying tool/resource/prompt function and return its result."""
    ...
```

### Argument type mapping

| Tool parameter type | argparse type |
|---------------------|---------------|
| `str`               | `str`         |
| `int`               | `int`         |
| `float`             | `float`       |
| `bool`              | `store_true`  |
| `dict` / `list`     | `str` (parsed as JSON) |
| `Optional[T]`       | same as T, not required |

### Output formatting flags

```bash
# Pretty-printed JSON (default)
sqlalchemy-mcp-server --db-url ... --cli query --sql "SELECT 1"

# Compact JSON
sqlalchemy-mcp-server --db-url ... --cli query --sql "SELECT 1" --compact

# Table format
sqlalchemy-mcp-server --db-url ... --cli query --sql "SELECT * FROM users" --format table
```

Table format uses simple column-aligned plain text — no external dependency needed.

### Error handling

- Database errors: print the error message to stderr, exit 1.
- Unknown subcommand: print usage help, exit 2.
- Missing required arguments: argparse handles this automatically.
- Write commands in readonly mode: print a clear error message ("command 'execute' requires --mode readwrite"), exit 1.

## Execution Model

- **Synchronous:** All CLI operations are synchronous. If the underlying tool is async, it is run via `asyncio.run()`.
- **One-shot:** The program connects, executes, prints, disconnects, exits. No REPL, no interactive mode.
- **Composable:** Output goes to stdout, errors to stderr, making it pipeable:

```bash
# Pipe query results to jq
sqlalchemy-mcp-server --db-url ... --cli query --sql "SELECT * FROM users" --compact | jq '.[].name'

# Use in a shell script
TABLES=$(sqlalchemy-mcp-server --db-url ... --cli list_tables --compact)
```

## Help integration

```bash
# Top-level help
sqlalchemy-mcp-server --cli --help

# Subcommand help (shows parameters derived from tool docstrings)
sqlalchemy-mcp-server --cli query --help
sqlalchemy-mcp-server --cli resource table --help
```

Tool/resource/prompt docstrings are reused as argparse help text.

## Acceptance Criteria

- [ ] `--cli` flag switches from MCP server mode to CLI mode
- [ ] Every registered tool is available as a CLI subcommand
- [ ] Every registered resource is available under `resource` namespace
- [ ] Every registered prompt is available under `prompt` namespace
- [ ] Tool parameters correctly map to CLI arguments with proper types
- [ ] Write commands are rejected when `--mode readonly` (default)
- [ ] JSON output is pretty-printed by default
- [ ] `--compact` flag outputs minified JSON
- [ ] `--format table` outputs human-readable tabular output
- [ ] Errors print to stderr and exit with non-zero code
- [ ] `--help` works at every level (top, subcommand, resource, prompt)
- [ ] CLI is composable with shell pipes (stdout/stderr separation)
- [ ] Engine is properly disposed after every invocation
- [ ] No new external dependencies are introduced
