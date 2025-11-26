# SQLITE MCP Server - Project Overview

## Objective

This projects implements a MCP Server to enable LLMs to interact with a sqlite database. The MCP server will be used locally on macOS to demonstrate LLM <> database interaction capabilities.

### Use Cases (Implemented)

The MCP server provides 4 tools for database interaction:

- **list_tables**: Returns all table names in the database. Useful for discovering available data before querying.
- **get_schema**: Returns full database schema as CREATE TABLE statements. Provides comprehensive context for complex queries.
- **describe_table**: Returns column details (name, type, nullable, default, primary_key), foreign keys, and indexes for a specific table.
- **query**: Executes read-only SQL queries (SELECT/WITH only). Validates queries to block INSERT, UPDATE, DELETE, DROP, and other write operations.

### Notes & Limitations

- The LLM output will only work well, if the database table names make sense and fit a use case description
- Sqlite dbs don't support column or table comments or database descriptions


## References

- General documentation on MCP servers: https://modelcontextprotocol.io/docs/develop/build-server
- Repository of the MCP Python SDK used for development: https://github.com/modelcontextprotocol/python-sdk
- Reference implementation of an MCP server: https://github.com/modelcontextprotocol/servers-archived/tree/main/src/sqlite
