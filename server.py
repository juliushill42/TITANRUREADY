"""
TitanU OS MCP Client - Interface for Calling MCP Tools
=======================================================

The MCPClient provides a clean, async interface for invoking tools through
the TitanU OS MCP Server. It handles error management, timeouts, and provides
convenient wrapper methods for common operations.

Features:
---------
- Simple async interface for tool invocation
- Robust error handling with MCPError exception
- Configurable timeouts per operation
- Batched operations for multiple tool calls
- Synchronous wrappers for non-async contexts
- Convenience methods for common operations

Usage Example:
--------------
    from mcp import MCPClient, MCPServer

    # Create server and client
    server = MCPServer(sandbox_root="./workspace")
    client = MCPClient(server)

    # Call tools
    content = await client.read_file("config.json")
    result = await client.exec_command("python --version")
    files = await client.list_files(".", pattern="*.py")

    # Batch operations
    results = await client.batch_call([
        ("file.read", {"path": "a.txt"}),
        ("file.read", {"path": "b.txt"}),
        ("system.info", {"detailed": True})
    ])

    # Synchronous call
    result = client.call_sync("system.info", {})

Copyright (c) 2025 TitanU OS Project
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

# Import MCPServer from same package
from .server import MCPServer

# Configure logging for TitanU OS MCP Client
logger = logging.getLogger("titanu.mcp.client")


class MCPError(Exception):
    """
    TitanU OS MCP Client Error.
    
    Raised when MCP operations fail. Provides structured error information
    including the tool name and error code for debugging.
    
    Attributes:
        message: Human-readable error description
        tool: Name of the tool that caused the error (if applicable)
        code: Error code for programmatic handling
        
    Example:
        >>> try:
        ...     result = await client.read_file("nonexistent.txt")
        ... except MCPError as e:
        ...     print(f"Tool {e.tool} failed: {e.message}")
        ...     if e.code == "TOOL_NOT_FOUND":
        ...         # Handle missing tool
        ...         pass
    """
    
    # Standard error codes
    SERVER_NOT_INITIALIZED = "SERVER_NOT_INITIALIZED"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TIMEOUT_EXCEEDED = "TIMEOUT_EXCEEDED"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    
    def __init__(
        self,
        message: str,
        tool: Optional[str] = None,
        code: Optional[str] = None
    ):
        """
        Initialize MCPError.
        
        Args:
            message: Error description
            tool: Name of the tool that caused the error
            code: Error code (one of the class constants)
        """
        self.message = message
        self.tool = tool
        self.code = code or self.EXECUTION_ERROR
        super().__init__(message)
    
    def __str__(self) -> str:
        """Format error message with tool and code info."""
        parts = []
        if self.code:
            parts.append(f"[{self.code}]")
        if self.tool:
            parts.append(f"({self.tool})")
        parts.append(self.message)
        return " ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            "error": True,
            "message": self.message,
            "tool": self.tool,
            "code": self.code
        }


class MCPClient:
    """
    TitanU OS MCP Client - Interface for calling MCP tools.
    
    Provides a high-level interface for invoking MCP tools with proper
    error handling, timeouts, and structured responses. The client can
    operate with an embedded MCPServer instance or connect to a remote
    server (future capability).
    
    Attributes:
        server: The connected MCPServer instance
        default_timeout: Default timeout for operations (seconds)
        
    Example:
        >>> from mcp import MCPClient, MCPServer
        >>> 
        >>> # Create with embedded server
        >>> server = MCPServer(sandbox_root="./workspace")
        >>> client = MCPClient(server)
        >>> 
        >>> # Read a file
        >>> content = await client.read_file("config.json")
        >>> print(content)
        >>> 
        >>> # Execute a command
        >>> result = await client.exec_command("python --version")
        >>> print(result["stdout"])
        >>> 
        >>> # List Python files
        >>> files = await client.list_files(".", pattern="*.py")
        >>> print(files)
    """
    
    # Default configuration
    DEFAULT_TIMEOUT = 30.0
    
    def __init__(
        self,
        server: Optional[MCPServer] = None,
        default_timeout: float = DEFAULT_TIMEOUT
    ):
        """
        Initialize the TitanU OS MCP Client.
        
        Args:
            server: MCPServer instance to use. If None, a default server
                   will be created when first needed.
            default_timeout: Default timeout for operations in seconds.
                           Can be overridden per-call.
        """
        self._server = server
        self.default_timeout = default_timeout
        self._initialized = server is not None
        
        logger.info(
            f"TitanU OS MCP Client initialized "
            f"(server: {'connected' if server else 'not connected'})"
        )
    
    @property
    def server(self) -> MCPServer:
        """
        Get the connected MCPServer instance.
        
        Returns:
            MCPServer instance
            
        Raises:
            MCPError: If no server is connected
        """
        if self._server is None:
            raise MCPError(
                "MCP Server not initialized. Create client with a server instance.",
                code=MCPError.SERVER_NOT_INITIALIZED
            )
        return self._server
    
    def connect(self, server: MCPServer) -> None:
        """
        Connect to an MCPServer instance.
        
        Args:
            server: MCPServer instance to connect to
        """
        self._server = server
        self._initialized = True
        logger.info("MCP Client connected to server")
    
    def disconnect(self) -> None:
        """Disconnect from the current server."""
        self._server = None
        self._initialized = False
        logger.info("MCP Client disconnected from server")
    
    def is_connected(self) -> bool:
        """Check if client is connected to a server."""
        return self._server is not None
    
    # =========================================================================
    # Core Tool Calling Methods
    # =========================================================================
    
    async def call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Call an MCP tool and return the result.
        
        This is the primary method for invoking tools through the MCP
        protocol. It handles timeout management and error wrapping.
        
        Args:
            tool_name: Name of the tool (e.g., "file.read", "process.exec")
            params: Parameters for the tool (tool-specific)
            timeout: Optional timeout override in seconds
            
        Returns:
            Dict with {success, result, error, tool, timestamp}
            
        Raises:
            MCPError: If server is not connected or call fails critically
            
        Example:
            >>> result = await client.call("file.read", {"path": "config.json"})
            >>> if result["success"]:
            ...     print(result["result"]["content"])
            ... else:
            ...     print(f"Error: {result['error']}")
        """
        # Ensure server is connected
        server = self.server
        
        # Determine timeout
        effective_timeout = timeout or self.default_timeout
        
        logger.debug(f"Calling tool: {tool_name} with params: {params}")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                server.call(tool_name, params),
                timeout=effective_timeout
            )
            
            # Log the result
            if result.get("success"):
                logger.debug(f"Tool {tool_name} completed successfully")
            else:
                logger.warning(f"Tool {tool_name} failed: {result.get('error')}")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout calling tool {tool_name} after {effective_timeout}s")
            return {
                "success": False,
                "result": None,
                "error": f"Operation timed out after {effective_timeout} seconds",
                "tool": tool_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.exception(f"Unexpected error calling tool {tool_name}: {e}")
            return {
                "success": False,
                "result": None,
                "error": str(e),
                "tool": tool_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def batch_call(
        self,
        calls: List[Tuple[str, Dict[str, Any]]],
        stop_on_error: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tool calls in sequence.
        
        Processes each call in order, collecting results. Can optionally
        stop on the first error encountered.
        
        Args:
            calls: List of (tool_name, params) tuples
            stop_on_error: If True, stop execution on first error
            
        Returns:
            List of result dictionaries (same format as call())
            
        Example:
            >>> results = await client.batch_call([
            ...     ("file.read", {"path": "a.txt"}),
            ...     ("file.read", {"path": "b.txt"}),
            ...     ("system.info", {"detailed": True})
            ... ])
            >>> for result in results:
            ...     if result["success"]:
            ...         print(f"{result['tool']}: OK")
        """
        results = []
        
        for tool_name, params in calls:
            result = await self.call(tool_name, params)
            results.append(result)
            
            if stop_on_error and not result.get("success"):
                logger.warning(
                    f"Batch call stopped at {tool_name} due to error: "
                    f"{result.get('error')}"
                )
                break
        
        return results
    
    async def batch_call_parallel(
        self,
        calls: List[Tuple[str, Dict[str, Any]]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tool calls in parallel with concurrency limit.
        
        Uses asyncio.Semaphore to limit concurrent executions.
        
        Args:
            calls: List of (tool_name, params) tuples
            max_concurrent: Maximum number of concurrent calls
            
        Returns:
            List of result dictionaries (in same order as input)
            
        Example:
            >>> results = await client.batch_call_parallel([
            ...     ("http.get", {"url": "https://api1.example.com"}),
            ...     ("http.get", {"url": "https://api2.example.com"}),
            ...     ("http.get", {"url": "https://api3.example.com"})
            ... ], max_concurrent=3)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_call(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.call(tool_name, params)
        
        tasks = [
            limited_call(tool_name, params)
            for tool_name, params in calls
        ]
        
        return await asyncio.gather(*tasks)
    
    def call_sync(
        self,
        tool_name: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for call().
        
        Useful for testing, scripts, or non-async contexts.
        
        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool
            timeout: Optional timeout override
            
        Returns:
            Dict with {success, result, error, tool, timestamp}
            
        Example:
            >>> result = client.call_sync("system.info", {"detailed": False})
            >>> print(result["result"]["platform"])
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # We're in an async context, need to use run_coroutine_threadsafe
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(
                self.call(tool_name, params, timeout),
                loop
            )
            return future.result(timeout=timeout or self.default_timeout)
        else:
            # No running loop, safe to use asyncio.run
            return asyncio.run(self.call(tool_name, params, timeout))
    
    # =========================================================================
    # Tool Discovery Methods
    # =========================================================================
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        List all available MCP tools with their schemas.
        
        Returns:
            List of tool schema dictionaries with:
            - type: "function"
            - function: {name, description, parameters}
            
        Example:
            >>> tools = client.get_available_tools()
            >>> for tool in tools:
            ...     print(f"{tool['function']['name']}: "
            ...           f"{tool['function']['description']}")
        """
        return self.server.get_tool_schemas()
    
    def list_tool_names(self) -> List[str]:
        """
        Get a simple list of available tool names.
        
        Returns:
            List of tool name strings
            
        Example:
            >>> names = client.list_tool_names()
            >>> print(names)
            ['file.read', 'file.write', 'file.list', ...]
        """
        return self.server.list_tools()
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool info dictionary or None if not found
            
        Example:
            >>> info = client.get_tool_info("file.read")
            >>> print(info["description"])
            >>> print(info["parameters"])
        """
        return self.server.get_tool_info(tool_name)
    
    def can_execute(self, tool_name: str) -> bool:
        """
        Check if a tool is available and can be executed.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if tool exists and is executable
            
        Example:
            >>> if client.can_execute("file.read"):
            ...     result = await client.read_file("config.json")
        """
        return tool_name in self.server.list_tools()
    
    # =========================================================================
    # Convenience Methods - File Operations
    # =========================================================================
    
    async def read_file(
        self,
        path: str,
        encoding: str = "utf-8"
    ) -> str:
        """
        Read file contents.
        
        Args:
            path: File path relative to sandbox root
            encoding: File encoding (default: utf-8)
            
        Returns:
            File contents as string
            
        Raises:
            MCPError: If file cannot be read
            
        Example:
            >>> content = await client.read_file("config.json")
            >>> data = json.loads(content)
        """
        result = await self.call("file.read", {
            "path": path,
            "encoding": encoding
        })
        
        if not result.get("success"):
            raise MCPError(
                result.get("error", "Failed to read file"),
                tool="file.read",
                code=MCPError.EXECUTION_ERROR
            )
        
        return result["result"]["content"]
    
    async def write_file(
        self,
        path: str,
        content: str,
        confirm: bool = False,
        append: bool = False,
        encoding: str = "utf-8"
    ) -> bool:
        """
        Write content to a file.
        
        Args:
            path: File path relative to sandbox root
            content: Content to write
            confirm: Set to True to confirm destructive operation
            append: If True, append instead of overwrite
            encoding: File encoding (default: utf-8)
            
        Returns:
            True if write was successful
            
        Raises:
            MCPError: If write fails or confirmation needed
            
        Example:
            >>> await client.write_file("output.txt", "Hello World", confirm=True)
            >>> await client.write_file("log.txt", "Entry\\n", append=True, confirm=True)
        """
        result = await self.call("file.write", {
            "path": path,
            "content": content,
            "confirmed": confirm,
            "append": append,
            "encoding": encoding
        })
        
        if not result.get("success"):
            error = result.get("error", "Failed to write file")
            
            # Check if confirmation is needed
            if result.get("result", {}).get("confirmation_required"):
                raise MCPError(
                    "Write operation requires confirmation. Set confirm=True.",
                    tool="file.write",
                    code=MCPError.CONFIRMATION_REQUIRED
                )
            
            raise MCPError(error, tool="file.write", code=MCPError.EXECUTION_ERROR)
        
        return True
    
    async def list_files(
        self,
        path: str = ".",
        pattern: Optional[str] = None,
        recursive: bool = False
    ) -> List[str]:
        """
        List files in a directory.
        
        Args:
            path: Directory path relative to sandbox root
            pattern: Glob pattern to filter files (e.g., "*.py")
            recursive: If True, list files recursively
            
        Returns:
            List of file paths
            
        Example:
            >>> py_files = await client.list_files(".", pattern="*.py")
            >>> all_files = await client.list_files("src", recursive=True)
        """
        params = {
            "path": path,
            "recursive": recursive
        }
        if pattern:
            params["pattern"] = pattern
        
        result = await self.call("file.list", params)
        
        if not result.get("success"):
            raise MCPError(
                result.get("error", "Failed to list files"),
                tool="file.list",
                code=MCPError.EXECUTION_ERROR
            )
        
        # Return just the file paths
        return [f["path"] for f in result["result"].get("files", [])]
    
    async def list_directory(
        self,
        path: str = ".",
        pattern: Optional[str] = None,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """
        List directory contents with full metadata.
        
        Args:
            path: Directory path relative to sandbox root
            pattern: Glob pattern to filter
            recursive: If True, list recursively
            
        Returns:
            Dict with files, directories, and counts
            
        Example:
            >>> listing = await client.list_directory(".")
            >>> print(f"Found {listing['total_files']} files")
        """
        params = {
            "path": path,
            "recursive": recursive
        }
        if pattern:
            params["pattern"] = pattern
        
        result = await self.call("file.list", params)
        
        if not result.get("success"):
            raise MCPError(
                result.get("error", "Failed to list directory"),
                tool="file.list",
                code=MCPError.EXECUTION_ERROR
            )
        
        return result["result"]
    
    # =========================================================================
    # Convenience Methods - Process Operations
    # =========================================================================
    
    async def exec_command(
        self,
        command: str,
        args: Optional[List[str]] = None,
        timeout: float = 60,
        shell: bool = False,
        cwd: str = "."
    ) -> Dict[str, Any]:
        """
        Execute a command and return output.
        
        Args:
            command: Command to execute
            args: Command arguments
            timeout: Execution timeout in seconds
            shell: If True, execute through shell
            cwd: Working directory relative to sandbox
            
        Returns:
            Dict with stdout, stderr, exit_code
            
        Example:
            >>> result = await client.exec_command("python", ["--version"])
            >>> print(result["stdout"])
            >>> 
            >>> result = await client.exec_command("git status", shell=True)
        """
        result = await self.call("process.exec", {
            "command": command,
            "args": args or [],
            "timeout": timeout,
            "shell": shell,
            "cwd": cwd
        }, timeout=timeout + 5)  # Add buffer to let process timeout first
        
        if not result.get("success"):
            raise MCPError(
                result.get("error", "Command execution failed"),
                tool="process.exec",
                code=MCPError.EXECUTION_ERROR
            )
        
        return result["result"]
    
    async def spawn_process(
        self,
        command: str,
        args: Optional[List[str]] = None,
        cwd: str = ".",
        background: bool = True
    ) -> Dict[str, Any]:
        """
        Spawn a background process.
        
        Args:
            command: Command to execute
            args: Command arguments
            cwd: Working directory relative to sandbox
            background: Always True for spawn (parameter for API consistency)
            
        Returns:
            Dict with process_id, pid, status
            
        Example:
            >>> proc = await client.spawn_process("python", ["-m", "http.server"])
            >>> print(f"Started with PID {proc['pid']}")
        """
        result = await self.call("process.spawn", {
            "command": command,
            "args": args or [],
            "cwd": cwd
        })
        
        if not result.get("success"):
            raise MCPError(
                result.get("error", "Failed to spawn process"),
                tool="process.spawn",
                code=MCPError.EXECUTION_ERROR
            )
        
        return result["result"]
    
    # =========================================================================
    # Convenience Methods - HTTP Operations
    # =========================================================================
    
    async def http_get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30
    ) -> Dict[str, Any]:
        """
        Perform HTTP GET request.
        
        Args:
            url: URL to request
            headers: Optional HTTP headers
            timeout: Request timeout in seconds
            
        Returns:
            Dict with status, headers, body
            
        Example:
            >>> response = await client.http_get("https://api.example.com/data")
            >>> if response["status"] == 200:
            ...     data = response["body"]
        """
        result = await self.call("http.get", {
            "url": url,
            "headers": headers or {},
            "timeout": timeout
        }, timeout=timeout + 5)
        
        if not result.get("success"):
            raise MCPError(
                result.get("error", "HTTP GET request failed"),
                tool="http.get",
                code=MCPError.EXECUTION_ERROR
            )
        
        return result["result"]
    
    async def http_post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30
    ) -> Dict[str, Any]:
        """
        Perform HTTP POST request.
        
        Args:
            url: URL to request
            data: Data to send (will be JSON encoded)
            headers: Optional HTTP headers
            timeout: Request timeout in seconds
            
        Returns:
            Dict with status, headers, body
            
        Example:
            >>> response = await client.http_post(
            ...     "https://api.example.com/submit",
            ...     data={"name": "TitanU"}
            ... )
        """
        result = await self.call("http.post", {
            "url": url,
            "data": data or {},
            "headers": headers or {},
            "timeout": timeout
        }, timeout=timeout + 5)
        
        if not result.get("success"):
            raise MCPError(
                result.get("error", "HTTP POST request failed"),
                tool="http.post",
                code=MCPError.EXECUTION_ERROR
            )
        
        return result["result"]
    
    # =========================================================================
    # Convenience Methods - System Operations
    # =========================================================================
    
    async def get_system_info(self, detailed: bool = False) -> Dict[str, Any]:
        """
        Get system information.
        
        Args:
            detailed: If True, include CPU/memory/disk stats (requires psutil)
            
        Returns:
            Dict with system information
            
        Example:
            >>> info = await client.get_system_info()
            >>> print(f"Platform: {info['platform']}")
            >>> print(f"Python: {info['python_version']}")
            >>>
            >>> # Detailed info
            >>> info = await client.get_system_info(detailed=True)
            >>> print(f"CPU Usage: {info['cpu_percent']}%")
        """
        result = await self.call("system.info", {"detailed": detailed})
        
        if not result.get("success"):
            raise MCPError(
                result.get("error", "Failed to get system info"),
                tool="system.info",
                code=MCPError.EXECUTION_ERROR
            )
        
        return result["result"]
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics and status.
        
        Returns:
            Dict with client status information
        """
        return {
            "connected": self.is_connected(),
            "available_tools": len(self.list_tool_names()) if self.is_connected() else 0,
            "default_timeout": self.default_timeout,
            "server_sandbox": str(self.server.sandbox_root) if self.is_connected() else None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the MCP connection.
        
        Returns:
            Dict with health status
            
        Example:
            >>> health = await client.health_check()
            >>> if health["healthy"]:
            ...     print("MCP is operational")
        """
        try:
            # Try to get system info as a health check
            result = await self.call("system.info", {}, timeout=5)
            
            return {
                "healthy": result.get("success", False),
                "server_connected": self.is_connected(),
                "tools_available": len(self.list_tool_names()),
                "mcp_version": result.get("result", {}).get("titanu_mcp_version", "unknown"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "server_connected": self.is_connected(),
                "tools_available": 0,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# =============================================================================
# Factory Functions
# =============================================================================

def create_mcp_client(
    sandbox_root: str = ".",
    default_timeout: float = MCPClient.DEFAULT_TIMEOUT,
    **server_kwargs
) -> MCPClient:
    """
    Create a fully configured TitanU OS MCP Client with embedded server.
    
    This is a convenience function that creates both the server and client
    with sensible defaults.
    
    Args:
        sandbox_root: Root directory for sandboxed operations
        default_timeout: Default timeout for client operations
        **server_kwargs: Additional arguments for MCPServer
        
    Returns:
        Configured MCPClient instance with connected server
        
    Example:
        >>> client = create_mcp_client("./workspace")
        >>> content = await client.read_file("config.json")
    """
    server = MCPServer(sandbox_root=sandbox_root, **server_kwargs)
    return MCPClient(server=server, default_timeout=default_timeout)


def create_client_only(
    default_timeout: float = MCPClient.DEFAULT_TIMEOUT
) -> MCPClient:
    """
    Create an MCP Client without a server connection.
    
    The client can be connected to a server later using connect().
    
    Args:
        default_timeout: Default timeout for operations
        
    Returns:
        MCPClient instance (not connected)
        
    Example:
        >>> client = create_client_only()
        >>> # ... later ...
        >>> client.connect(server)
    """
    return MCPClient(server=None, default_timeout=default_timeout)