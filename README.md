# Agentic Conversational Analytics App
A conversational analytics system that transforms natural language queries into SQL using Claude AI, LangGraph agents, and RAG (Retrieval Augmented Generation) with MCP (Model Context Protocol) integration.

## What it does?
This project enables users to ask business questions in natural language, and the system automatically:

1. **Retrieves relevant database schemas** using RAG (semantic search via ChromaDB)
2. **Generates SQL queries** using Claude AI
3. **Validates the SQL** before execution
4. **Executes the query** against the database
5. **Returns results** in a user-friendly format

## Architecture
```
User Query (Natural Language)
    ↓
[LangGraph Agent] ← Claude AI with tools
    ↓
[MCP Server] (Schema Retrieval, SQL Validation, Execution)
    ↓
[ChromaDB] (RAG - Semantic Schema Search)
    ↓
[Database] (SQL Execution)
    ↓
Results (Tabular Format)


### Key Components

- **`agent_lgs.py`** - Main LangGraph agent orchestrating the entire workflow
- **`mcp_server.py`** - MCP server exposing tools for schema retrieval, SQL validation, and execution
- **`claude_api.py`** - Claude API initialization and configuration
- **`mcp_client.py`** - MCP client for tool registration
- **`build_rag.py`** - RAG setup with ChromaDB for semantic schema search
- **`retail_schema_documentation.txt`** - Database schema definitions
- **`chroma_db/`** - Persistent ChromaDB vector store
