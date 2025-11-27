# SQLite MCP Server

An MCP (Model Context Protocol) server that enables LLMs to interact with SQLite databases. This server provides read-only access to any SQLite database through a set of tools for schema inspection and SQL query execution.

Built with **async/await** patterns using `aiosqlite` for non-blocking database operations.


## Features

- **list_tables** - Get all table names in the database
- **describe_table** - Get column details, types, and relationships for a specific table
- **get_schema** - Get complete database schema as CREATE TABLE statements
- **query** - Execute read-only SQL queries (SELECT only)


## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager


## Installation

1. Clone this repository
2. Install dependencies:

```bash
uv sync
```


## Quick Start with Sample Data

This project includes a CRM sample database for demonstration purposes.

### 1. Create and seed the database

```bash
uv run seed_database.py
```

This creates `crm.db` with sample CRM data:
- 5 users (sales team)
- 20 companies
- 40 contacts
- 25 deals
- 30 activities

### 2. Run the MCP server

See [Running the Server](#running-the-server) below.


## Running the Server

The server uses `crm.db` in the same directory as the script (hardcoded).

### Development Mode (MCP Inspector)

```bash
uv run mcp dev sqlite_mcp_server.py
```

This launches the **MCP Inspector** - a web-based debugging UI at `http://localhost:5173` where you can:

- See all registered tools
- Test each tool interactively with custom inputs
- Inspect JSON responses
- Debug issues before connecting an LLM

### Production Mode (LLM Integration)

```bash
uv run sqlite_mcp_server.py
```

This starts the server in **stdio mode**, ready for LLM clients to connect.


## Client Configuration

### Example: Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/sqlite-mcp-server",
        "run",
        "sqlite_mcp_server.py"
      ]
    }
  }
}
```


## Tool Reference

### list_tables

Returns all table names in the database.

**Example response:**
```json
{
  "tables": ["activities", "companies", "contacts", "deals", "users"]
}
```

### describe_table

Get detailed information about a table's structure.

**Parameters:**
- `table_name` (string): Name of the table to describe

**Example response:**
```json
{
  "table": "contacts",
  "columns": [
    {"name": "id", "type": "INTEGER", "nullable": false, "primary_key": true},
    {"name": "first_name", "type": "TEXT", "nullable": false, "primary_key": false},
    {"name": "email", "type": "TEXT", "nullable": true, "primary_key": false}
  ],
  "foreign_keys": [
    {"column": "company_id", "references_table": "companies", "references_column": "id"}
  ],
  "indexes": []
}
```

### get_schema

Returns complete database schema as CREATE TABLE statements.

**Example response:**
```json
{
  "schema": {
    "users": "CREATE TABLE users (...)",
    "companies": "CREATE TABLE companies (...)"
  }
}
```

### query

Execute a read-only SQL query. Only SELECT statements are allowed.

**Parameters:**
- `sql` (string): A SELECT SQL statement

**Example response:**
```json
{
  "columns": ["name", "email"],
  "rows": [
    ["John Doe", "john@example.com"],
    ["Jane Smith", "jane@example.com"]
  ],
  "row_count": 2
}
```

**Security:** The server validates that queries are read-only by:
1. Ensuring queries start with SELECT or WITH
2. Blocking keywords like INSERT, UPDATE, DELETE, DROP, etc.

## Using Your Own Database

The server is hardcoded to use `crm.db` in the script directory. To use a different database:

1. Replace `crm.db` with your database file (keep the same name), or
2. Modify the `DB_PATH` constant in `sqlite_mcp_server.py`
