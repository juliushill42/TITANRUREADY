"""
TitanU OS MCP Server - Local Tool Execution Engine
===================================================

The MCPServer provides a safe, sandboxed environment for executing tools
requested by the Central Brain. All operations are validated against
security policies before execution.

Features:
---------
- Sandbox enforcement for file operations
- Async/await patterns for I/O operations
- Configurable timeouts for HTTP and process operations
- Comprehensive logging
- Custom tool registration
- Auto-loading of tool schemas from JSON files

Copyright (c) 2025 TitanU OS Project
"""

import asyncio
import json
import logging
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field

# Optional imports with graceful fallback
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False
    aiofiles = None

# Configure logging for TitanU OS MCP
logger = logging.getLogger("titanu.mcp.server")


@dataclass
class ToolSchema:
    """Schema definition for an MCP tool."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None
    requires_confirmation: bool = False
    timeout: Optional[float] = None


@dataclass
class ToolResponse:
    """Standard response format for all MCP tool calls."""
    success: bool
    result: Any
    error: Optional[str]
    tool: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "tool": self.tool,
            "timestamp": self.timestamp
        }


class SecurityViolationError(Exception):
    """Raised when a security policy is violated."""
    pass


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not registered."""
    pass


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass


class MCPServer:
    """
    TitanU OS MCP Server - Local tool execution engine.
    
    Provides a secure, sandboxed environment for executing tools requested
    by the Central Brain through the Model Context Protocol.
    
    Attributes:
        sandbox_root: Root directory for sandboxed file operations
        tools: Dictionary of registered tools
        http_timeout: Default timeout for HTTP operations (seconds)
        process_timeout: Default timeout for process operations (seconds)
        
    Example:
        >>> server = MCPServer(sandbox_root="./workspace")
        >>> result = await server.call("file.read", {"path": "example.txt"})
        >>> print(result["result"])
    """
    
    # Default configuration
    DEFAULT_HTTP_TIMEOUT = 30.0
    DEFAULT_PROCESS_TIMEOUT = 60.0
    DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    
    def __init__(
        self,
        sandbox_root: str = ".",
        http_timeout: float = DEFAULT_HTTP_TIMEOUT,
        process_timeout: float = DEFAULT_PROCESS_TIMEOUT,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        enable_confirmations: bool = True
    ):
        """
        Initialize the TitanU OS MCP Server.
        
        Args:
            sandbox_root: Root directory for sandboxed file operations.
                          All file paths will be resolved relative to this.
            http_timeout: Default timeout for HTTP operations in seconds.
            process_timeout: Default timeout for process operations in seconds.
            max_file_size: Maximum allowed file size for read/write operations.
            enable_confirmations: If True, destructive operations require confirmation.
        """
        self.sandbox_root = Path(sandbox_root).resolve()
        self.http_timeout = http_timeout
        self.process_timeout = process_timeout
        self.max_file_size = max_file_size
        self.enable_confirmations = enable_confirmations
        
        # Storage for registered tools
        self._tools: Dict[str, ToolSchema] = {}
        
        # Pending confirmations for destructive operations
        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}
        
        # Background processes
        self._background_processes: Dict[str, subprocess.Popen] = {}
        
        # Initialize built-in tools
        self._register_builtin_tools()
        
        logger.info(
            f"TitanU OS MCP Server initialized with sandbox root: {self.sandbox_root}"
        )
    
    def _register_builtin_tools(self) -> None:
        """Register all built-in tools for TitanU OS MCP."""
        
        # File operations
        self.register_tool(
            name="file.read",
            schema={
                "description": "Read the contents of a file within the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file (relative to sandbox root)"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding (default: utf-8)",
                            "default": "utf-8"
                        }
                    },
                    "required": ["path"]
                }
            },
            handler=self._tool_file_read
        )
        
        self.register_tool(
            name="file.write",
            schema={
                "description": "Write content to a file within the sandbox. Requires confirmation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file (relative to sandbox root)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding (default: utf-8)",
                            "default": "utf-8"
                        },
                        "append": {
                            "type": "boolean",
                            "description": "If true, append to file instead of overwriting",
                            "default": False
                        },
                        "confirmed": {
                            "type": "boolean",
                            "description": "Set to true to confirm the write operation",
                            "default": False
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            handler=self._tool_file_write,
            requires_confirmation=True
        )
        
        self.register_tool(
            name="file.list",
            schema={
                "description": "List files and directories within the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path (relative to sandbox root)",
                            "default": "."
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "If true, list recursively",
                            "default": False
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern to filter files (e.g., '*.py')",
                            "default": "*"
                        }
                    }
                }
            },
            handler=self._tool_file_list
        )
        
        # Process operations
        self.register_tool(
            name="process.spawn",
            schema={
                "description": "Spawn a background process. Returns process ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute"
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Command arguments",
                            "default": []
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory (relative to sandbox)",
                            "default": "."
                        }
                    },
                    "required": ["command"]
                }
            },
            handler=self._tool_process_spawn
        )
        
        self.register_tool(
            name="process.exec",
            schema={
                "description": "Execute a command and wait for the result.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute"
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Command arguments",
                            "default": []
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory (relative to sandbox)",
                            "default": "."
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Timeout in seconds",
                            "default": None
                        },
                        "shell": {
                            "type": "boolean",
                            "description": "Execute through shell",
                            "default": False
                        }
                    },
                    "required": ["command"]
                }
            },
            handler=self._tool_process_exec
        )
        
        # HTTP operations
        self.register_tool(
            name="http.get",
            schema={
                "description": "Perform an HTTP GET request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to request"
                        },
                        "headers": {
                            "type": "object",
                            "description": "HTTP headers",
                            "default": {}
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Request timeout in seconds",
                            "default": None
                        }
                    },
                    "required": ["url"]
                }
            },
            handler=self._tool_http_get
        )
        
        self.register_tool(
            name="http.post",
            schema={
                "description": "Perform an HTTP POST request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to request"
                        },
                        "data": {
                            "type": "object",
                            "description": "Data to send (will be JSON encoded)",
                            "default": {}
                        },
                        "headers": {
                            "type": "object",
                            "description": "HTTP headers",
                            "default": {}
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Request timeout in seconds",
                            "default": None
                        }
                    },
                    "required": ["url"]
                }
            },
            handler=self._tool_http_post
        )
        
        # System operations
        self.register_tool(
            name="system.info",
            schema={
                "description": "Get system information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "detailed": {
                            "type": "boolean",
                            "description": "Include detailed information",
                            "default": False
                        }
                    }
                }
            },
            handler=self._tool_system_info
        )
        
        logger.debug(f"Registered {len(self._tools)} built-in tools")
    
    def register_tool(
        self,
        name: str,
        schema: Dict[str, Any],
        handler: Callable,
        requires_confirmation: bool = False,
        timeout: Optional[float] = None
    ) -> None:
        """
        Register a custom tool with the MCP server.
        
        Args:
            name: Unique tool name (e.g., "custom.mytool")
            schema: JSON schema describing the tool's parameters
            handler: Async callable that implements the tool
            requires_confirmation: If True, tool requires confirmation for execution
            timeout: Optional custom timeout for this tool
            
        Example:
            >>> async def my_handler(params):
            ...     return {"message": f"Hello, {params.get('name', 'World')}!"}
            >>> server.register_tool(
            ...     name="custom.greet",
            ...     schema={"description": "Greet someone", "parameters": {...}},
            ...     handler=my_handler
            ... )
        """
        tool = ToolSchema(
            name=name,
            description=schema.get("description", ""),
            parameters=schema.get("parameters", {}),
            handler=handler,
            requires_confirmation=requires_confirmation,
            timeout=timeout
        )
        self._tools[name] = tool
        logger.debug(f"Registered tool: {name}")
    
    def load_tools_from_directory(self, path: str) -> int:
        """
        Auto-load tool schemas from JSON files in a directory.
        
        Each JSON file should contain a tool definition with:
        - name: Tool name
        - description: Tool description
        - parameters: JSON schema for parameters
        - handler_module: Python module path containing the handler
        - handler_function: Name of the handler function in the module
        
        Args:
            path: Path to directory containing tool JSON files
            
        Returns:
            Number of tools loaded
            
        Example JSON file (mcp/tools/custom_tool.json):
            {
                "name": "custom.example",
                "description": "An example custom tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"}
                    },
                    "required": ["input"]
                },
                "handler_module": "mcp.handlers.custom",
                "handler_function": "handle_example"
            }
        """
        tools_path = Path(path)
        if not tools_path.exists():
            logger.warning(f"Tools directory does not exist: {path}")
            return 0
        
        loaded_count = 0
        for json_file in tools_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    tool_def = json.load(f)
                
                name = tool_def.get("name")
                if not name:
                    logger.warning(f"Tool definition missing 'name': {json_file}")
                    continue
                
                # Try to import the handler
                handler = None
                handler_module = tool_def.get("handler_module")
                handler_function = tool_def.get("handler_function")
                
                if handler_module and handler_function:
                    try:
                        import importlib
                        module = importlib.import_module(handler_module)
                        handler = getattr(module, handler_function)
                    except (ImportError, AttributeError) as e:
                        logger.warning(
                            f"Could not load handler for tool '{name}': {e}"
                        )
                        continue
                
                self.register_tool(
                    name=name,
                    schema={
                        "description": tool_def.get("description", ""),
                        "parameters": tool_def.get("parameters", {})
                    },
                    handler=handler,
                    requires_confirmation=tool_def.get("requires_confirmation", False),
                    timeout=tool_def.get("timeout")
                )
                loaded_count += 1
                logger.info(f"Loaded custom tool from {json_file.name}: {name}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in tool file {json_file}: {e}")
            except Exception as e:
                logger.error(f"Error loading tool from {json_file}: {e}")
        
        return loaded_count
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get JSON schemas for all registered tools.
        
        Returns:
            List of tool schema dictionaries suitable for LLM tool calling.
        """
        schemas = []
        for name, tool in self._tools.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        return schemas
    
    def _make_response(
        self,
        tool: str,
        success: bool,
        result: Any = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a standardized tool response."""
        response = ToolResponse(
            success=success,
            result=result,
            error=error,
            tool=tool,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        return response.to_dict()
    
    def _validate_sandbox_path(self, path: str) -> Path:
        """
        Validate and resolve a path within the sandbox.
        
        Args:
            path: Relative path to validate
            
        Returns:
            Resolved absolute path within sandbox
            
        Raises:
            SecurityViolationError: If path escapes sandbox
        """
        # Resolve the full path
        full_path = (self.sandbox_root / path).resolve()
        
        # Ensure it's within the sandbox
        try:
            full_path.relative_to(self.sandbox_root)
        except ValueError:
            raise SecurityViolationError(
                f"Path '{path}' escapes sandbox root. Access denied."
            )
        
        return full_path
    
    async def call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call.
        
        This is the main entry point for all tool invocations from the
        TitanU OS Central Brain.
        
        Args:
            tool_name: Name of the tool to execute (e.g., "file.read")
            params: Parameters for the tool call
            
        Returns:
            Standardized response dictionary with:
            - success: bool indicating success/failure
            - result: Tool return value (on success)
            - error: Error message (on failure)
            - tool: Name of the executed tool
            - timestamp: ISO format timestamp
            
        Example:
            >>> result = await server.call("file.read", {"path": "config.json"})
            >>> if result["success"]:
            ...     print(result["result"])
        """
        logger.info(f"MCP call: {tool_name} with params: {params}")
        
        # Check if tool exists
        if tool_name not in self._tools:
            return self._make_response(
                tool=tool_name,
                success=False,
                error=f"Tool '{tool_name}' not found. Available tools: {list(self._tools.keys())}"
            )
        
        tool = self._tools[tool_name]
        
        # Check for confirmation requirement
        if tool.requires_confirmation and self.enable_confirmations:
            if not params.get("confirmed", False):
                confirmation_id = f"{tool_name}_{datetime.now().timestamp()}"
                self._pending_confirmations[confirmation_id] = {
                    "tool": tool_name,
                    "params": params,
                    "created": datetime.now(timezone.utc).isoformat()
                }
                return self._make_response(
                    tool=tool_name,
                    success=False,
                    error=f"This operation requires confirmation. Set 'confirmed': true to proceed.",
                    result={"confirmation_required": True, "confirmation_id": confirmation_id}
                )
        
        # Execute the tool
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(params)
            else:
                result = tool.handler(params)
            
            return self._make_response(
                tool=tool_name,
                success=True,
                result=result
            )
            
        except SecurityViolationError as e:
            logger.warning(f"Security violation in {tool_name}: {e}")
            return self._make_response(
                tool=tool_name,
                success=False,
                error=f"Security violation: {str(e)}"
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout executing {tool_name}")
            return self._make_response(
                tool=tool_name,
                success=False,
                error="Operation timed out"
            )
        except Exception as e:
            logger.exception(f"Error executing {tool_name}: {e}")
            return self._make_response(
                tool=tool_name,
                success=False,
                error=str(e)
            )
    
    # =========================================================================
    # Built-in Tool Implementations
    # =========================================================================
    
    async def _tool_file_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents within sandbox."""
        path = params.get("path")
        encoding = params.get("encoding", "utf-8")
        
        if not path:
            raise ValueError("Parameter 'path' is required")
        
        full_path = self._validate_sandbox_path(path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if not full_path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        # Check file size
        file_size = full_path.stat().st_size
        if file_size > self.max_file_size:
            raise ValueError(
                f"File too large ({file_size} bytes). Maximum: {self.max_file_size} bytes"
            )
        
        async with aiofiles.open(full_path, 'r', encoding=encoding) as f:
            content = await f.read()
        
        return {
            "path": path,
            "content": content,
            "size": file_size,
            "encoding": encoding
        }
    
    async def _tool_file_write(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to file within sandbox."""
        path = params.get("path")
        content = params.get("content")
        encoding = params.get("encoding", "utf-8")
        append = params.get("append", False)
        
        if not path:
            raise ValueError("Parameter 'path' is required")
        if content is None:
            raise ValueError("Parameter 'content' is required")
        
        full_path = self._validate_sandbox_path(path)
        
        # Check content size
        content_size = len(content.encode(encoding))
        if content_size > self.max_file_size:
            raise ValueError(
                f"Content too large ({content_size} bytes). Maximum: {self.max_file_size} bytes"
            )
        
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = 'a' if append else 'w'
        async with aiofiles.open(full_path, mode, encoding=encoding) as f:
            await f.write(content)
        
        return {
            "path": path,
            "bytes_written": content_size,
            "encoding": encoding,
            "mode": "append" if append else "write"
        }
    
    async def _tool_file_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List files and directories within sandbox."""
        path = params.get("path", ".")
        recursive = params.get("recursive", False)
        pattern = params.get("pattern", "*")
        
        full_path = self._validate_sandbox_path(path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        
        if not full_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        files = []
        directories = []
        
        if recursive:
            for item in full_path.rglob(pattern):
                rel_path = item.relative_to(self.sandbox_root)
                if item.is_file():
                    files.append({
                        "path": str(rel_path),
                        "size": item.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            item.stat().st_mtime, tz=timezone.utc
                        ).isoformat()
                    })
                elif item.is_dir():
                    directories.append(str(rel_path))
        else:
            for item in full_path.glob(pattern):
                rel_path = item.relative_to(self.sandbox_root)
                if item.is_file():
                    files.append({
                        "path": str(rel_path),
                        "size": item.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            item.stat().st_mtime, tz=timezone.utc
                        ).isoformat()
                    })
                elif item.is_dir():
                    directories.append(str(rel_path))
        
        return {
            "path": path,
            "files": files,
            "directories": directories,
            "total_files": len(files),
            "total_directories": len(directories)
        }
    
    async def _tool_process_spawn(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn a background process."""
        command = params.get("command")
        args = params.get("args", [])
        cwd = params.get("cwd", ".")
        
        if not command:
            raise ValueError("Parameter 'command' is required")
        
        # Validate working directory is within sandbox
        work_dir = self._validate_sandbox_path(cwd)
        
        # Build full command
        full_command = [command] + args
        
        # Spawn process
        process = subprocess.Popen(
            full_command,
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Store process reference
        process_id = f"proc_{process.pid}_{datetime.now().timestamp()}"
        self._background_processes[process_id] = process
        
        return {
            "process_id": process_id,
            "pid": process.pid,
            "command": command,
            "args": args,
            "status": "running"
        }
    
    async def _tool_process_exec(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command and wait for result."""
        command = params.get("command")
        args = params.get("args", [])
        cwd = params.get("cwd", ".")
        timeout = params.get("timeout", self.process_timeout)
        shell = params.get("shell", False)
        
        if not command:
            raise ValueError("Parameter 'command' is required")
        
        # Validate working directory is within sandbox
        work_dir = self._validate_sandbox_path(cwd)
        
        # Build command
        if shell:
            full_command = command + " " + " ".join(args) if args else command
        else:
            full_command = [command] + args
        
        try:
            process = await asyncio.create_subprocess_shell(
                full_command if shell else " ".join(full_command),
                cwd=str(work_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "command": command,
                "args": args,
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "success": process.returncode == 0
            }
            
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"Process execution timed out after {timeout} seconds"
            )
    
    async def _tool_http_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform HTTP GET request."""
        url = params.get("url")
        headers = params.get("headers", {})
        timeout = params.get("timeout", self.http_timeout)
        
        if not url:
            raise ValueError("Parameter 'url' is required")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    body = await response.json()
                else:
                    body = await response.text()
                
                return {
                    "url": url,
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": body,
                    "content_type": content_type
                }
    
    async def _tool_http_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform HTTP POST request."""
        url = params.get("url")
        data = params.get("data", {})
        headers = params.get("headers", {})
        timeout = params.get("timeout", self.http_timeout)
        
        if not url:
            raise ValueError("Parameter 'url' is required")
        
        # Set default content type for JSON
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    body = await response.json()
                else:
                    body = await response.text()
                
                return {
                    "url": url,
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": body,
                    "content_type": content_type
                }
    
    async def _tool_system_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get system information."""
        detailed = params.get("detailed", False)
        
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),

            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "hostname": platform.node(),
            "titanu_mcp_version": "2.5.0"
        }
        
        if detailed:
            import psutil
            try:
                info["cpu_count"] = psutil.cpu_count()
                info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
                info["memory_total"] = psutil.virtual_memory().total
                info["memory_available"] = psutil.virtual_memory().available
                info["memory_percent"] = psutil.virtual_memory().percent
                info["disk_usage"] = {
                    str(partition.mountpoint): {
                        "total": psutil.disk_usage(partition.mountpoint).total,
                        "used": psutil.disk_usage(partition.mountpoint).used,
                        "free": psutil.disk_usage(partition.mountpoint).free
                    }
                    for partition in psutil.disk_partitions()
                    if partition.fstype
                }
            except ImportError:
                info["detailed_error"] = "psutil not installed for detailed info"
            except Exception as e:
                info["detailed_error"] = str(e)
        
        return info
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def list_tools(self) -> List[str]:
        """Return a list of all registered tool names."""
        return list(self._tools.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dictionary with tool information or None if not found
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
            "requires_confirmation": tool.requires_confirmation,
            "timeout": tool.timeout
        }
    
    def call_sync(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous wrapper for tool calls.
        
        Useful for testing or non-async contexts.
        
        Args:
            tool_name: Name of the tool to call
            params: Tool parameters
            
        Returns:
            Tool response dictionary
        """
        return asyncio.run(self.call(tool_name, params))
    
    def get_pending_confirmations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all pending confirmations.
        
        Returns:
            Dictionary of confirmation_id -> confirmation details
        """
        return self._pending_confirmations.copy()
    
    def clear_pending_confirmation(self, confirmation_id: str) -> bool:
        """
        Clear a pending confirmation.
        
        Args:
            confirmation_id: ID of the confirmation to clear
            
        Returns:
            True if cleared, False if not found
        """
        if confirmation_id in self._pending_confirmations:
            del self._pending_confirmations[confirmation_id]
            return True
        return False
    
    def get_background_processes(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all background processes.
        
        Returns:
            Dictionary of process_id -> process status
        """
        result = {}
        for proc_id, proc in self._background_processes.items():
            poll_result = proc.poll()
            result[proc_id] = {
                "pid": proc.pid,
                "running": poll_result is None,
                "exit_code": poll_result,
                "args": proc.args
            }
        return result
    
    def terminate_process(self, process_id: str) -> bool:
        """
        Terminate a background process.
        
        Args:
            process_id: ID of the process to terminate
            
        Returns:
            True if terminated, False if not found
        """
        if process_id not in self._background_processes:
            return False
        
        proc = self._background_processes[process_id]
        proc.terminate()
        proc.wait(timeout=5)
        del self._background_processes[process_id]
        return True
    
    async def cleanup(self) -> None:
        """
        Clean up server resources.
        
        Terminates all background processes and clears pending state.
        """
        for proc_id, proc in list(self._background_processes.items()):
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error terminating process {proc_id}: {e}")
        
        self._background_processes.clear()
        self._pending_confirmations.clear()
        logger.info("TitanU OS MCP Server cleanup complete")


# Convenience function for creating server instances
def create_mcp_server(
    sandbox_root: str = ".",
    **kwargs
) -> MCPServer:
    """
    Create and configure a TitanU OS MCP Server instance.
    
    This is a convenience function for creating a properly configured
    MCP server with sensible defaults.
    
    Args:
        sandbox_root: Root directory for sandboxed operations
        **kwargs: Additional arguments passed to MCPServer
        
    Returns:
        Configured MCPServer instance
        
    Example:
        >>> server = create_mcp_server("./workspace")
        >>> result = await server.call("system.info", {})
    """
    return MCPServer(sandbox_root=sandbox_root, **kwargs)
