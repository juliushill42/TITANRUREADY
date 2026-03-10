"""
TitanU OS MCP (Model Context Protocol) Integration
===================================================

Provides standardized tool calling for the Central Brain.

The MCP (Model Context Protocol) system enables the TitanU OS Central Brain
to invoke tools through structured JSON schema calls. This provides a safe,
sandboxed environment for executing operations locally.

Components:
-----------
- MCPServer: Local tool execution engine with built-in safety measures
- MCPClient: Client interface for connecting to MCP servers
- MCPError: Exception class for MCP errors
- MCPRouter: Routes tool calls to appropriate handlers (future)

Built-in Tools:
--------------
- file.read: Read file contents
- file.write: Write file contents (with confirmation)
- file.list: List files in directory
- process.spawn: Spawn background process
- process.exec: Execute command and wait for result
- http.get: HTTP GET request
- http.post: HTTP POST request
- system.info: Get system information

Usage:
------
    from mcp import MCPServer, MCPClient
    
    # Create server and client
    server = MCPServer(sandbox_root="./workspace")
    client = MCPClient(server)
    
    # Call tools via client
    content = await client.read_file("config.json")
    result = await client.exec_command("python --version")
    
    # Or use factory function
    from mcp import create_mcp_client
    client = create_mcp_client("./workspace")
    files = await client.list_files(".", pattern="*.py")

Copyright (c) 2025 TitanU OS Project
"""

from .server import MCPServer, create_mcp_server
from .client import MCPClient, MCPError, create_mcp_client, create_client_only
from .router import (
    MCPRouter,
    RoutingRule,
    create_router,
    INTENT_PATTERNS,
    INTENT_TO_TOOL
)

__version__ = "2.5.0"
__author__ = "TitanU OS Team"

__all__ = [
    # Server
    'MCPServer',
    'create_mcp_server',
    # Client
    'MCPClient',
    'MCPError',
    'create_mcp_client',
    'create_client_only',
    # Router
    'MCPRouter',
    'RoutingRule',
    'create_router',
    'INTENT_PATTERNS',
    'INTENT_TO_TOOL',
]