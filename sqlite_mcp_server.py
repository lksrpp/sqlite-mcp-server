#!/usr/bin/env python3
"""
SQLite MCP Server (Async)

An MCP (Model Context Protocol) server that enables LLMs to interact with
SQLite databases through a set of read-only tools.

Uses aiosqlite for non-blocking async database operations.

Database:
- crm.db (must exist in the same directory as this script)
- Update SCRIPT_DIR and DB_PATH to point to the correct database file

Usage:
    Development (MCP Inspector):
        uv run mcp dev sqlite_mcp_server.py
    
    Production (stdio mode):
        uv run python sqlite_mcp_server.py

Tools:
    - list_tables: Get all table names in the database
    - describe_table: Get column details for a specific table
    - get_schema: Get full database schema as CREATE TABLE statements
    - query: Execute read-only SQL queries (SELECT only)
"""

import sys
import json
import os
import re
import aiosqlite
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
# Note: FastMCP always advertises tools, resources, and prompts capabilities by design.
# Clients will receive empty lists for resources/prompts since we only implement tools.
mcp = FastMCP("SQLite MCP Server")

# Database path - hardcoded to crm.db in the same directory as this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "crm.db")


async def get_connection() -> aiosqlite.Connection:
    """Get an async database connection."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Run 'uv run python seed_database.py' to create and seed the database."
        )
    
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


@mcp.tool()
async def list_tables() -> str:
    """
    List all tables in the database.
    
    Returns a JSON array of table names that exist in the SQLite database.
    Use this to discover what data is available before querying.
    """
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ) as cursor:
            rows = await cursor.fetchall()
            tables = [row["name"] for row in rows]
        return json.dumps({"tables": tables}, indent=2)
    finally:
        await conn.close()


@mcp.tool()
async def describe_table(table_name: str) -> str:
    """
    Get detailed information about a specific table's structure.
    
    Args:
        table_name: The name of the table to describe
    
    Returns a JSON object with:
    - columns: Array of column definitions (name, type, nullable, default, primary_key)
    - foreign_keys: Array of foreign key relationships
    - indexes: Array of index definitions
    
    Use this to understand the schema before writing queries.
    """
    conn = await get_connection()
    try:
        # Verify table exists
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table_name,)
        ) as cursor:
            if not await cursor.fetchone():
                return json.dumps({"error": f"Table '{table_name}' not found"}, indent=2)
        
        # Get column information
        async with conn.execute(f"PRAGMA table_info({table_name})") as cursor:
            columns = []
            async for row in cursor:
                columns.append({
                    "name": row["name"],
                    "type": row["type"],
                    "nullable": not row["notnull"],
                    "default": row["dflt_value"],
                    "primary_key": bool(row["pk"])
                })
        
        # Get foreign keys
        async with conn.execute(f"PRAGMA foreign_key_list({table_name})") as cursor:
            foreign_keys = []
            async for row in cursor:
                foreign_keys.append({
                    "column": row["from"],
                    "references_table": row["table"],
                    "references_column": row["to"]
                })
        
        # Get indexes
        async with conn.execute(f"PRAGMA index_list({table_name})") as cursor:
            indexes = []
            async for row in cursor:
                index_name = row["name"]
                # Get columns in this index
                async with conn.execute(f"PRAGMA index_info({index_name})") as idx_cursor:
                    idx_columns = [idx_row["name"] async for idx_row in idx_cursor]
                indexes.append({
                    "name": index_name,
                    "unique": bool(row["unique"]),
                    "columns": idx_columns
                })
        
        return json.dumps({
            "table": table_name,
            "columns": columns,
            "foreign_keys": foreign_keys,
            "indexes": indexes
        }, indent=2)
    finally:
        await conn.close()


@mcp.tool()
async def get_schema() -> str:
    """
    Get the complete database schema as CREATE TABLE statements.
    
    Returns the SQL CREATE statements for all tables in the database.
    This provides full context about the database structure including
    column definitions, constraints, and relationships.
    
    Use this when you need comprehensive schema information for complex queries.
    """
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ) as cursor:
            schema = {}
            async for row in cursor:
                schema[row["name"]] = row["sql"]
        
        return json.dumps({"schema": schema}, indent=2)
    finally:
        await conn.close()


@mcp.tool()
async def query(sql: str) -> str:
    """
    Execute a read-only SQL query against the database.
    
    Args:
        sql: A SELECT SQL statement to execute. Only SELECT queries are allowed
             for safety - INSERT, UPDATE, DELETE, DROP, and other modifying
             statements will be rejected.
    
    Returns a JSON object with:
    - columns: Array of column names
    - rows: Array of row data (each row is an array of values)
    - row_count: Number of rows returned
    
    Examples:
    - "SELECT * FROM users LIMIT 10"
    - "SELECT name, email FROM contacts WHERE company_id = 1"
    - "SELECT c.name, COUNT(d.id) as deal_count FROM companies c LEFT JOIN deals d ON d.contact_id IN (SELECT id FROM contacts WHERE company_id = c.id) GROUP BY c.id"
    """
    # Validate query is read-only
    sql_upper = sql.strip().upper()
    
    # List of forbidden keywords that indicate write operations
    # These must match as whole words to avoid false positives like "created_at" matching "CREATE"
    forbidden_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", 
        "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "VACUUM", 
        "REINDEX", "PRAGMA"
    ]
    
    # Check if query starts with SELECT or WITH (for CTEs)
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return json.dumps({
            "error": "Only SELECT queries are allowed. Query must start with SELECT or WITH."
        }, indent=2)
    
    # Additional safety check for forbidden keywords using word boundaries
    # This ensures "created_at" doesn't match "CREATE", but "CREATE TABLE" does
    for keyword in forbidden_keywords:
        # Use word boundary \b to match whole words only
        if re.search(rf'\b{keyword}\b', sql_upper):
            return json.dumps({
                "error": f"Query contains forbidden keyword: {keyword}. Only read-only queries are allowed."
            }, indent=2)
    
    conn = await get_connection()
    try:
        async with conn.execute(sql) as cursor:
            # Get column names
            columns = [description[0] for description in cursor.description] if cursor.description else []
            
            # Fetch all rows
            rows = await cursor.fetchall()
            
            # Convert rows to lists (from aiosqlite.Row objects)
            row_data = [list(row) for row in rows]
        
        return json.dumps({
            "columns": columns,
            "rows": row_data,
            "row_count": len(row_data)
        }, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"SQL error: {str(e)}"
        }, indent=2)
    finally:
        await conn.close()


def main():
    """Main entry point."""
    # Verify database exists at startup
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found: {DB_PATH}", file=sys.stderr)
        print("Run 'uv run python seed_database.py' to create and seed the database.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Starting SQLite MCP Server with database: {DB_PATH}", file=sys.stderr)
    
    # Run the MCP server
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
