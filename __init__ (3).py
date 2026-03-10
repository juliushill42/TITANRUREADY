"""
TitanU OS MCP Router - Intelligent Tool Routing and Orchestration
==================================================================

The MCPRouter sits between the LLM and the MCP tools, detecting when
a user request requires tool usage and orchestrating the appropriate
tool calls. It provides:

- Intent detection from natural language
- Tool selection and parameter extraction
- LLM response parsing for tool calls
- Multi-tool workflow orchestration
- Response formatting for the UI

Features:
---------
- Pattern-based intent detection
- Multiple LLM output format support (JSON, function calls, markdown)
- Configurable routing rules
- System prompt generation for tool awareness
- Structured result formatting

Usage Example:
--------------
    from mcp import MCPClient, MCPServer, MCPRouter
    
    # Create server, client, and router
    server = MCPServer(sandbox_root="./workspace")
    client = MCPClient(server)
    router = MCPRouter(client)
    
    # Analyze user input
    analysis = router.analyze_request("read the config.json file")
    if analysis["needs_tools"]:
        results = await router.route_and_execute(
            "read the config.json file",
            llm_response='{"tool": "file.read", "params": {"path": "config.json"}}'
        )

Copyright (c) 2025 TitanU OS Project
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Import MCPClient from same package
from .client import MCPClient

# Configure logging for TitanU OS MCP Router
logger = logging.getLogger("titanu.mcp.router")


# =============================================================================
# Intent Detection Patterns
# =============================================================================

INTENT_PATTERNS: Dict[str, List[str]] = {
    "file_read": [
        r"read\s+(?:the\s+)?(?:file\s+)?['\"]?(\S+)['\"]?",
        r"show\s+(?:me\s+)?(?:contents?\s+of\s+)?['\"]?(\S+)['\"]?",
        r"what(?:'s|\s+is)\s+in\s+['\"]?(\S+)['\"]?",
        r"open\s+['\"]?(\S+)['\"]?",
        r"cat\s+['\"]?(\S+)['\"]?",
        r"view\s+(?:the\s+)?(?:file\s+)?['\"]?(\S+)['\"]?",
        r"display\s+(?:contents?\s+of\s+)?['\"]?(\S+)['\"]?",
        r"get\s+(?:contents?\s+of\s+)?['\"]?(\S+)['\"]?"
    ],
    "file_write": [
        r"write\s+(?:to\s+)?['\"]?(\S+)['\"]?",
        r"create\s+(?:a\s+)?(?:file\s+)?['\"]?(\S+)['\"]?",
        r"save\s+(?:to\s+)?['\"]?(\S+)['\"]?",
        r"make\s+(?:a\s+)?(?:file\s+)?['\"]?(\S+)['\"]?",
        r"update\s+(?:the\s+)?(?:file\s+)?['\"]?(\S+)['\"]?",
        r"modify\s+(?:the\s+)?(?:file\s+)?['\"]?(\S+)['\"]?"
    ],
    "file_list": [
        r"list\s+(?:files?\s+)?(?:in\s+)?['\"]?(\S*)['\"]?",
        r"show\s+(?:files?\s+)?(?:in\s+)?['\"]?(\S*)['\"]?",
        r"what\s+files?\s+(?:are\s+)?(?:in\s+)?['\"]?(\S*)['\"]?",
        r"ls(?:\s+['\"]?(\S*)['\"]?)?",
        r"dir(?:\s+['\"]?(\S*)['\"]?)?",
        r"browse\s+(?:the\s+)?(?:directory\s+)?['\"]?(\S*)['\"]?"
    ],
    "file_append": [
        r"append\s+(?:to\s+)?['\"]?(\S+)['\"]?",
        r"add\s+(?:to\s+)?(?:file\s+)?['\"]?(\S+)['\"]?"
    ],
    "command_exec": [
        r"run\s+(?:the\s+)?(?:command\s+)?['\"`](.+?)['\"`]",
        r"execute\s+['\"`]?(.+?)['\"`]?$",
        r"shell\s+['\"`]?(.+?)['\"`]?$",
        r"terminal\s+['\"`]?(.+?)['\"`]?$",
        r"\$\s*(.+)",
        r"cmd\s+['\"`]?(.+?)['\"`]?$"
    ],
    "http_fetch": [
        r"fetch\s+(?:from\s+)?['\"]?(https?://\S+)['\"]?",
        r"get\s+(?:from\s+)?['\"]?(https?://\S+)['\"]?",
        r"download\s+['\"]?(https?://\S+)['\"]?",
        r"request\s+['\"]?(https?://\S+)['\"]?",
        r"call\s+(?:api\s+)?['\"]?(https?://\S+)['\"]?",
        r"api\s+['\"]?(https?://\S+)['\"]?"
    ],
    "http_post": [
        r"post\s+(?:to\s+)?['\"]?(https?://\S+)['\"]?",
        r"send\s+(?:to\s+)?['\"]?(https?://\S+)['\"]?"
    ],
    "system_info": [
        r"system\s+info(?:rmation)?",
        r"cpu\s+(?:usage|info|status)",
        r"memory\s+(?:usage|info|status)",
        r"disk\s+(?:usage|info|status|space)",
        r"ram\s+(?:usage|info|status)",
        r"hardware\s+info",
        r"resource(?:s)?\s+(?:usage|status)",
        r"show\s+system",
        r"what(?:'s|\s+is)\s+(?:my\s+)?(?:cpu|memory|disk|ram)"
    ],
    "env_info": [
        r"env(?:ironment)?\s+(?:var(?:iable)?s?|info)",
        r"show\s+env",
        r"get\s+env",
        r"what\s+(?:is|are)\s+(?:the\s+)?env",
        r"list\s+env"
    ]
}

# Mapping from intents to MCP tools
INTENT_TO_TOOL: Dict[str, str] = {
    "file_read": "file.read",
    "file_write": "file.write",
    "file_list": "file.list",
    "file_append": "file.append",
    "command_exec": "process.exec",
    "http_fetch": "http.get",
    "http_post": "http.post",
    "system_info": "system.info",
    "env_info": "env.get"
}


# =============================================================================
# Routing Rule
# =============================================================================

@dataclass
class RoutingRule:
    """
    Rule for tool routing.
    
    Defines how to map a pattern match to a specific tool with
    parameter extraction.
    
    Attributes:
        pattern: Regex pattern to match
        tool: Target MCP tool name
        param_mapping: Dictionary mapping capture groups to parameters
        priority: Priority level (higher = processed first)
        description: Human-readable description of the rule
        
    Example:
        >>> rule = RoutingRule(
        ...     pattern=r"read\s+file\s+(\S+)",
        ...     tool="file.read",
        ...     param_mapping={"1": "path"},
        ...     priority=10,
        ...     description="Read file by name"
        ... )
    """
    pattern: str
    tool: str
    param_mapping: Dict[str, str] = field(default_factory=dict)
    priority: int = 0
    description: str = ""
    
    def __post_init__(self):
        """Compile the pattern for efficiency."""
        self._compiled = re.compile(self.pattern, re.IGNORECASE)
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to match the text against this rule.
        
        Args:
            text: Input text to match
            
        Returns:
            Dict with tool and params if matched, None otherwise
        """
        match = self._compiled.search(text)
        if match:
            params = {}
            for group_idx, param_name in self.param_mapping.items():
                try:
                    idx = int(group_idx)
                    if idx <= len(match.groups()):
                        value = match.group(idx)
                        if value:
                            params[param_name] = value.strip("'\"")
                except (ValueError, IndexError):
                    continue
            return {"tool": self.tool, "params": params}
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary format."""
        return {
            "pattern": self.pattern,
            "tool": self.tool,
            "param_mapping": self.param_mapping,
            "priority": self.priority,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoutingRule":
        """Create rule from dictionary."""
        return cls(
            pattern=data["pattern"],
            tool=data["tool"],
            param_mapping=data.get("param_mapping", {}),
            priority=data.get("priority", 0),
            description=data.get("description", "")
        )


# =============================================================================
# MCP Router
# =============================================================================

class MCPRouter:
    """
    TitanU OS MCP Router - Intelligent tool routing and orchestration.
    
    The router sits between the LLM and the MCP tools, detecting when
    a user request requires tool usage and orchestrating the appropriate
    tool calls.
    
    Attributes:
        client: The connected MCPClient instance
        routing_rules: List of custom routing rules
        
    Example:
        >>> from mcp import MCPClient, MCPServer, MCPRouter
        >>> 
        >>> server = MCPServer(sandbox_root="./workspace")
        >>> client = MCPClient(server)
        >>> router = MCPRouter(client)
        >>> 
        >>> # Analyze request
        >>> analysis = router.analyze_request("read config.json")
        >>> print(analysis["detected_intents"])  # ['file_read']
        >>> 
        >>> # Full routing pipeline
        >>> result = await router.route_and_execute("read config.json")
    """
    
    # Tool call regex patterns for parsing LLM output
    TOOL_CALL_PATTERNS = [
        # JSON block format: ```tool:file.read\n{"path": "..."}\n```
        r"```tool:(\w+\.?\w*)\n([\s\S]*?)```",
        # Function call format: <tool_call>file.read(path="...")</tool_call>
        r"<tool_call>(\w+\.?\w*)\((.*?)\)</tool_call>",
        # Inline tool call: [[file.read(path="...")]]
        r"\[\[(\w+\.?\w*)\((.*?)\)\]\]",
        # JSON object: {"tool": "file.read", "params": {...}}
        r'\{\s*"tool"\s*:\s*"(\w+\.?\w*)"\s*,\s*"params"\s*:\s*(\{[^}]+\})\s*\}',
        # Tool calls array: {"tool_calls": [...]}
        r'\{\s*"tool_calls"\s*:\s*(\[[\s\S]*?\])\s*\}'
    ]
    
    def __init__(
        self,
        client: Optional[MCPClient] = None,
        auto_execute: bool = False
    ):
        """
        Initialize the TitanU OS MCP Router.
        
        Args:
            client: MCPClient instance to use for tool execution.
                   If None, routing analysis still works but execution fails.
            auto_execute: If True, automatically execute detected tools
                         (use with caution)
        """
        self._client = client
        self.auto_execute = auto_execute
        self._routing_rules: List[RoutingRule] = []
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        
        # Compile intent patterns
        self._compile_patterns()
        
        # Initialize default routing rules
        self._init_default_rules()
        
        logger.info(
            f"TitanU OS MCP Router initialized "
            f"(client: {'connected' if client else 'not connected'})"
        )
    
    @property
    def client(self) -> MCPClient:
        """Get the connected MCPClient instance."""
        if self._client is None:
            raise RuntimeError(
                "MCP Client not connected. Initialize router with a client."
            )
        return self._client
    
    def connect(self, client: MCPClient) -> None:
        """
        Connect to an MCPClient instance.
        
        Args:
            client: MCPClient instance to connect to
        """
        self._client = client
        logger.info("MCP Router connected to client")
    
    def is_connected(self) -> bool:
        """Check if router has a connected client."""
        return self._client is not None
    
    def _compile_patterns(self) -> None:
        """Compile all intent patterns for efficiency."""
        for intent, patterns in INTENT_PATTERNS.items():
            self._compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def _init_default_rules(self) -> None:
        """Initialize default routing rules."""
        # File read rules
        self.add_routing_rule(RoutingRule(
            pattern=r"read\s+(?:the\s+)?(?:file\s+)?['\"]?(\S+)['\"]?",
            tool="file.read",
            param_mapping={"1": "path"},
            priority=10,
            description="Read file by path"
        ))
        
        # File write rules
        self.add_routing_rule(RoutingRule(
            pattern=r"(?:write|save)\s+(?:to\s+)?['\"]?(\S+)['\"]?\s+(?:content|with)\s+(.+)",
            tool="file.write",
            param_mapping={"1": "path", "2": "content"},
            priority=10,
            description="Write content to file"
        ))
        
        # File list rules
        self.add_routing_rule(RoutingRule(
            pattern=r"(?:list|ls|dir)\s+(?:files?\s+)?(?:in\s+)?['\"]?(\S*)['\"]?",
            tool="file.list",
            param_mapping={"1": "directory"},
            priority=10,
            description="List files in directory"
        ))
        
        # Command execution rules
        self.add_routing_rule(RoutingRule(
            pattern=r"(?:run|execute|shell)\s+['\"`](.+?)['\"`]",
            tool="process.exec",
            param_mapping={"1": "command"},
            priority=10,
            description="Execute shell command"
        ))
        
        # HTTP GET rules
        self.add_routing_rule(RoutingRule(
            pattern=r"(?:fetch|get|download)\s+(?:from\s+)?['\"]?(https?://\S+)['\"]?",
            tool="http.get",
            param_mapping={"1": "url"},
            priority=10,
            description="HTTP GET request"
        ))
        
        # System info rules
        self.add_routing_rule(RoutingRule(
            pattern=r"(?:show\s+)?system\s+info(?:rmation)?",
            tool="system.info",
            param_mapping={},
            priority=10,
            description="Get system information"
        ))
    
    # =========================================================================
    # Request Analysis
    # =========================================================================
    
    def analyze_request(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze user input to determine if MCP tools are needed.
        
        Examines the input text for patterns that suggest tool usage
        and extracts relevant parameters like file paths, URLs, and commands.
        
        Args:
            user_input: The user's natural language input
            
        Returns:
            Analysis dictionary with:
            - needs_tools: Whether tools appear to be needed
            - detected_intents: List of detected intent types
            - suggested_tools: List of suggested MCP tool names
            - confidence: Confidence score (0.0-1.0)
            - extraction: Extracted parameters (paths, urls, commands)
            
        Example:
            >>> router.analyze_request("read the config.json file")
            {
                "needs_tools": True,
                "detected_intents": ["file_read"],
                "suggested_tools": ["file.read"],
                "confidence": 0.85,
                "extraction": {"paths": ["config.json"], "urls": [], "commands": []}
            }
        """
        detected_intents = []
        suggested_tools = []
        extraction = {
            "paths": [],
            "urls": [],
            "commands": [],
            "patterns_matched": []
        }
        confidence = 0.0
        
        # Check each intent pattern
        for intent, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(user_input)
                if match:
                    if intent not in detected_intents:
                        detected_intents.append(intent)
                        tool = INTENT_TO_TOOL.get(intent)
                        if tool and tool not in suggested_tools:
                            suggested_tools.append(tool)
                    
                    # Extract captured values
                    if match.groups():
                        value = match.group(1)
                        if value:
                            value = value.strip("'\"")
                            extraction["patterns_matched"].append({
                                "intent": intent,
                                "value": value
                            })
                            
                            # Categorize the extracted value
                            if intent in ["file_read", "file_write", "file_list", "file_append"]:
                                if value and value not in extraction["paths"]:
                                    extraction["paths"].append(value)
                            elif intent in ["http_fetch", "http_post"]:
                                if value and value not in extraction["urls"]:
                                    extraction["urls"].append(value)
                            elif intent == "command_exec":
                                if value and value not in extraction["commands"]:
                                    extraction["commands"].append(value)
        
        # Calculate confidence based on matches
        if detected_intents:
            # Base confidence from having matches
            confidence = 0.5
            # Increase confidence for multiple matches to same intent
            confidence += min(0.3, len(extraction["patterns_matched"]) * 0.1)
            # Increase confidence for extracted parameters
            if extraction["paths"] or extraction["urls"] or extraction["commands"]:
                confidence += 0.2
        
        # Check custom routing rules for additional matches
        for rule in self._routing_rules:
            result = rule.match(user_input)
            if result:
                if result["tool"] not in suggested_tools:
                    suggested_tools.append(result["tool"])
                confidence = max(confidence, 0.7)  # High confidence for rule match
        
        needs_tools = confidence > 0.3
        
        return {
            "needs_tools": needs_tools,
            "detected_intents": detected_intents,
            "suggested_tools": suggested_tools,
            "confidence": min(1.0, confidence),
            "extraction": extraction,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # =========================================================================
    # Tool Schema Generation
    # =========================================================================
    
    def generate_tool_schema(
        self,
        tools: Optional[List[str]] = None,
        format: str = "openai"
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Generate JSON schema for LLM tool calling.
        
        Returns OpenAI-style function calling schema that can be
        passed to the LLM to enable structured tool invocation.
        
        Args:
            tools: List of tool names to include. If None, includes all.
            format: Schema format ("openai", "anthropic", or "simple")
            
        Returns:
            List of tool schemas for the specified format
            
        Example:
            >>> schema = router.generate_tool_schema(["file.read", "file.write"])
            >>> # Returns OpenAI function calling format
        """
        if not self.is_connected():
            logger.warning("No client connected, returning empty schema")
            return [] if format != "simple" else {}
        
        available_tools = self.client.get_available_tools()
        
        # Filter to requested tools
        if tools:
            available_tools = [
                t for t in available_tools
                if t.get("function", {}).get("name") in tools
            ]
        
        if format == "openai":
            return available_tools
        
        elif format == "anthropic":
            # Convert to Anthropic tool format
            anthropic_tools = []
            for tool in available_tools:
                func = tool.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name"),
                    "description": func.get("description"),
                    "input_schema": func.get("parameters", {})
                })
            return anthropic_tools
        
        elif format == "simple":
            # Simple dictionary format
            simple = {}
            for tool in available_tools:
                func = tool.get("function", {})
                simple[func.get("name")] = {
                    "description": func.get("description"),
                    "parameters": func.get("parameters", {}).get("properties", {})
                }
            return simple
        
        else:
            return available_tools
    
    def get_tool_descriptions(self) -> str:
        """
        Get human-readable tool descriptions for system prompts.
        
        Returns:
            Formatted string listing all available tools
        """
        if not self.is_connected():
            return "No tools available (client not connected)"
        
        lines = ["Available MCP Tools:"]
        lines.append("-" * 40)
        
        for tool in self.client.get_available_tools():
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "No description")
            params = func.get("parameters", {}).get("properties", {})
            
            lines.append(f"\n• {name}")
            lines.append(f"  {desc}")
            if params:
                lines.append("  Parameters:")
                for param_name, param_info in params.items():
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    lines.append(f"    - {param_name} ({param_type}): {param_desc}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # LLM Response Parsing
    # =========================================================================
    
    def parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response to extract tool calls.
        
        Supports multiple formats:
        - JSON tool calls: {"tool": "file.read", "params": {...}}
        - Function calls: file.read(path="...")
        - Markdown blocks: ```tool:file.read\\n{"path": "..."}\\n```
        - Tool call tags: <tool_call>file.read(path="...")</tool_call>
        - Tool calls array: {"tool_calls": [...]}
        
        Args:
            response: The LLM's response text
            
        Returns:
            List of {"tool": str, "params": dict} dictionaries
            
        Example:
            >>> response = '''I'll read that file.
            ... ```tool:file.read
            ... {"path": "config.json"}
            ... ```'''
            >>> router.parse_llm_response(response)
            [{"tool": "file.read", "params": {"path": "config.json"}}]
        """
        tool_calls = []
        
        # Try markdown code block format: ```tool:name\n{...}\n```
        block_pattern = r"```tool:(\w+\.?\w*)\n([\s\S]*?)```"
        for match in re.finditer(block_pattern, response):
            tool_name = match.group(1)
            params_str = match.group(2).strip()
            try:
                params = json.loads(params_str) if params_str else {}
                tool_calls.append({"tool": tool_name, "params": params})
            except json.JSONDecodeError:
                # Try to parse as key=value pairs
                params = self._parse_key_value_params(params_str)
                tool_calls.append({"tool": tool_name, "params": params})
        
        # Try <tool_call> tag format
        tag_pattern = r"<tool_call>(\w+\.?\w*)\((.*?)\)</tool_call>"
        for match in re.finditer(tag_pattern, response, re.DOTALL):
            tool_name = match.group(1)
            params_str = match.group(2)
            params = self._parse_function_params(params_str)
            tool_calls.append({"tool": tool_name, "params": params})
        
        # Try [[tool(params)]] format
        bracket_pattern = r"\[\[(\w+\.?\w*)\((.*?)\)\]\]"
        for match in re.finditer(bracket_pattern, response):
            tool_name = match.group(1)
            params_str = match.group(2)
            params = self._parse_function_params(params_str)
            tool_calls.append({"tool": tool_name, "params": params})
        
        # Try inline JSON: {"tool": "...", "params": {...}}
        json_pattern = r'\{\s*"tool"\s*:\s*"(\w+\.?\w*)"\s*,\s*"params"\s*:\s*(\{[^}]*\})\s*\}'
        for match in re.finditer(json_pattern, response):
            tool_name = match.group(1)
            params_str = match.group(2)
            try:
                params = json.loads(params_str)
                tool_calls.append({"tool": tool_name, "params": params})
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON params: {params_str}")
        
        # Try tool_calls array: {"tool_calls": [...]}
        array_pattern = r'\{\s*"tool_calls"\s*:\s*(\[[\s\S]*?\])\s*\}'
        for match in re.finditer(array_pattern, response):
            try:
                calls_array = json.loads(match.group(1))
                for call in calls_array:
                    if isinstance(call, dict) and "tool" in call:
                        tool_calls.append({
                            "tool": call.get("tool"),
                            "params": call.get("params", call.get("parameters", {}))
                        })
            except json.JSONDecodeError:
                logger.warning("Failed to parse tool_calls array")
        
        # Try to find a full JSON object with tool and params
        try:
            # Look for JSON objects in the response
            json_objects = re.findall(r'\{[^{}]*\}', response)
            for obj_str in json_objects:
                try:
                    obj = json.loads(obj_str)
                    if "tool" in obj and ("params" in obj or "parameters" in obj):
                        # Avoid duplicates
                        new_call = {
                            "tool": obj["tool"],
                            "params": obj.get("params", obj.get("parameters", {}))
                        }
                        if not any(c["tool"] == new_call["tool"] and c["params"] == new_call["params"] for c in tool_calls):
                            tool_calls.append(new_call)
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        
        return tool_calls
    
    def _parse_function_params(self, params_str: str) -> Dict[str, Any]:
        """
        Parse function-style parameters: key="value", key2=123
        
        Args:
            params_str: Parameter string like 'path="config.json", encoding="utf-8"'
            
        Returns:
            Dictionary of parameters
        """
        params = {}
        # Match key=value patterns
        pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\d+(?:\.\d+)?)|(\w+))'
        for match in re.finditer(pattern, params_str):
            key = match.group(1)
            # Get the first non-None value group
            value = next((g for g in match.groups()[1:] if g is not None), None)
            if value is not None:
                # Try to convert to number if possible
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except (ValueError, TypeError):
                    pass
                params[key] = value
        return params
    
    def _parse_key_value_params(self, params_str: str) -> Dict[str, Any]:
        """
        Parse key: value style parameters from text.
        
        Args:
            params_str: Parameter string with key: value lines
            
        Returns:
            Dictionary of parameters
        """
        params = {}
        for line in params_str.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().strip('"\'')
                value = value.strip().strip('"\'')
                # Try to parse as JSON value
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    pass
                params[key] = value
        return params
    
    # =========================================================================
    # Tool Execution
    # =========================================================================
    
    async def execute_tools(
        self,
        tool_calls: List[Dict[str, Any]],
        stop_on_error: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute parsed tool calls through the MCP client.
        
        Args:

            tool_calls: List of {"tool": str, "params": dict}
            stop_on_error: If True, stop on first error
            
        Returns:
            List of result dictionaries from each tool call
        """
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool", "")
            params = tool_call.get("params", {})
            
            if not tool_name:
                logger.warning("Skipping tool call with empty tool name")
                continue
            
            logger.info(f"Executing tool: {tool_name} with params: {params}")
            
            try:
                result = await self.client.call(str(tool_name), params)
                results.append(result)
                
                if stop_on_error and not result.get("success"):
                    logger.warning(f"Stopping execution due to error in {tool_name}")
                    break
                    
            except Exception as e:
                logger.exception(f"Error executing tool {tool_name}: {e}")
                results.append({
                    "success": False,
                    "result": None,
                    "error": str(e),
                    "tool": tool_name,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                if stop_on_error:
                    break
        
        return results
    
    # =========================================================================
    # Full Routing Pipeline
    # =========================================================================
    
    async def route_and_execute(
        self,
        user_input: str,
        llm_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full routing pipeline:
        1. Analyze input
        2. If LLM response provided, parse it for tool calls
        3. Otherwise, auto-detect and suggest tools
        4. Execute tools
        5. Return results
        
        Args:
            user_input: The original user request
            llm_response: Optional LLM response to parse for tool calls
            
        Returns:
            Dictionary with:
            - analysis: Request analysis results
            - tool_calls: Parsed tool calls
            - results: Execution results
            - formatted: Formatted output for display
        """
        # Step 1: Analyze the request
        analysis = self.analyze_request(user_input)
        
        tool_calls = []
        results = []
        
        # Step 2: Get tool calls from LLM response or auto-detect
        if llm_response:
            tool_calls = self.parse_llm_response(llm_response)
        elif analysis["needs_tools"] and self.auto_execute:
            # Auto-generate tool calls from extraction
            tool_calls = self._generate_tool_calls_from_analysis(analysis)
        
        # Step 3: Execute tools if we have calls
        if tool_calls and self.is_connected():
            results = await self.execute_tools(tool_calls)
        
        # Step 4: Format results
        formatted = self.format_results(tool_calls, results)
        
        return {
            "analysis": analysis,
            "tool_calls": tool_calls,
            "results": results,
            "formatted": formatted,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_tool_calls_from_analysis(
        self,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate tool calls from analysis extraction.
        
        Args:
            analysis: Result from analyze_request()
            
        Returns:
            List of tool calls
        """
        tool_calls = []
        extraction = analysis.get("extraction", {})
        
        # Generate file read calls
        if "file_read" in analysis["detected_intents"]:
            for path in extraction.get("paths", []):
                tool_calls.append({
                    "tool": "file.read",
                    "params": {"path": path}
                })
        
        # Generate file list calls
        elif "file_list" in analysis["detected_intents"]:
            paths = extraction.get("paths", [])
            if paths:
                for path in paths:
                    tool_calls.append({
                        "tool": "file.list",
                        "params": {"directory": path or "."}
                    })
            else:
                tool_calls.append({
                    "tool": "file.list",
                    "params": {"directory": "."}
                })
        
        # Generate HTTP GET calls
        elif "http_fetch" in analysis["detected_intents"]:
            for url in extraction.get("urls", []):
                tool_calls.append({
                    "tool": "http.get",
                    "params": {"url": url}
                })
        
        # Generate command exec calls
        elif "command_exec" in analysis["detected_intents"]:
            for cmd in extraction.get("commands", []):
                tool_calls.append({
                    "tool": "process.exec",
                    "params": {"command": cmd}
                })
        
        # Generate system info call
        elif "system_info" in analysis["detected_intents"]:
            tool_calls.append({
                "tool": "system.info",
                "params": {"detailed": True}
            })
        
        return tool_calls
    
    # =========================================================================
    # Routing Rules Management
    # =========================================================================
    
    def add_routing_rule(self, rule: RoutingRule) -> None:
        """
        Add a custom routing rule.
        
        Args:
            rule: RoutingRule instance to add
        """
        self._routing_rules.append(rule)
        # Sort by priority (highest first)
        self._routing_rules.sort(key=lambda r: r.priority, reverse=True)
        logger.debug(f"Added routing rule: {rule.description or rule.pattern}")
    
    def remove_routing_rule(self, pattern: str) -> bool:
        """
        Remove a routing rule by pattern.
        
        Args:
            pattern: The pattern string of the rule to remove
            
        Returns:
            True if rule was found and removed
        """
        for i, rule in enumerate(self._routing_rules):
            if rule.pattern == pattern:
                del self._routing_rules[i]
                return True
        return False
    
    def get_routing_rules(self) -> List[RoutingRule]:
        """Get all routing rules."""
        return list(self._routing_rules)
    
    def clear_routing_rules(self) -> None:
        """Clear all custom routing rules and reinitialize defaults."""
        self._routing_rules.clear()
        self._init_default_rules()
    
    def load_routing_rules(self, path: str) -> int:
        """
        Load routing rules from a JSON file.
        
        Args:
            path: Path to JSON file containing rules
            
        Returns:
            Number of rules loaded
            
        File format:
            {
                "rules": [
                    {
                        "pattern": "...",
                        "tool": "...",
                        "param_mapping": {...},
                        "priority": 10,
                        "description": "..."
                    }
                ]
            }
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            rules = data.get("rules", [])
            count = 0
            for rule_data in rules:
                try:
                    rule = RoutingRule.from_dict(rule_data)
                    self.add_routing_rule(rule)
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to load rule: {e}")
            
            logger.info(f"Loaded {count} routing rules from {path}")
            return count
        except Exception as e:
            logger.error(f"Failed to load routing rules from {path}: {e}")
            return 0
    
    def save_routing_rules(self, path: str) -> bool:
        """
        Save current routing rules to a JSON file.
        
        Args:
            path: Path to save the rules
            
        Returns:
            True if saved successfully
        """
        try:
            data = {
                "rules": [rule.to_dict() for rule in self._routing_rules]
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self._routing_rules)} routing rules to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save routing rules to {path}: {e}")
            return False
    
    # =========================================================================
    # Result Formatting
    # =========================================================================
    
    def format_tool_result(self, tool: str, result: Dict[str, Any]) -> str:
        """
        Format a single tool result for display.
        
        Args:
            tool: Tool name
            result: Result dictionary from tool execution
            
        Returns:
            Formatted string for UI display
        """
        success = result.get("success", False)
        status = "✓" if success else "✗"
        status_word = "Success" if success else "Error"
        
        lines = [f"[TOOL:{tool}] {status} {status_word}"]
        
        if success:
            tool_result = result.get("result", {})
            
            # Format based on tool type
            if tool == "file.read":
                content = tool_result.get("content", "")
                size = len(content.encode('utf-8'))
                lines.append(f"  File read successfully ({size} bytes)")
                if content:
                    preview = content[:200] + "..." if len(content) > 200 else content
                    lines.append(f"  Preview: {preview}")
                    
            elif tool == "file.list":
                files = tool_result.get("files", [])
                lines.append(f"  Found {len(files)} items")
                for f in files[:10]:
                    lines.append(f"    - {f}")
                if len(files) > 10:
                    lines.append(f"    ... and {len(files) - 10} more")
                    
            elif tool == "file.write":
                path = tool_result.get("path", "unknown")
                lines.append(f"  Written to: {path}")
                
            elif tool == "process.exec":
                stdout = tool_result.get("stdout", "")
                stderr = tool_result.get("stderr", "")
                exit_code = tool_result.get("exit_code", 0)
                lines.append(f"  Exit code: {exit_code}")
                if stdout:
                    lines.append(f"  Output: {stdout[:200]}")
                if stderr:
                    lines.append(f"  Stderr: {stderr[:200]}")
                    
            elif tool == "http.get":
                status_code = tool_result.get("status_code", 0)
                content_type = tool_result.get("content_type", "unknown")
                lines.append(f"  Status: {status_code}, Type: {content_type}")
                
            elif tool == "system.info":
                platform_info = tool_result.get("platform", "unknown")
                lines.append(f"  Platform: {platform_info}")
                
            else:
                # Generic formatting
                lines.append(f"  Result: {str(tool_result)[:200]}")
        else:
            error = result.get("error", "Unknown error")
            lines.append(f"  {error}")
        
        return "\n".join(lines)
    
    def format_results(
        self,
        tool_calls: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Format all results for display.
        
        Args:
            tool_calls: List of executed tool calls
            results: List of results from execution
            
        Returns:
            Formatted string with all results
        """
        if not results:
            return "No tools were executed."
        
        lines = ["=" * 50]
        lines.append("MCP Tool Execution Results")
        lines.append("=" * 50)
        
        for i, (call, result) in enumerate(zip(tool_calls, results)):
            tool = call.get("tool", "unknown")
            lines.append(f"\n[{i + 1}] {self.format_tool_result(tool, result)}")
        
        lines.append("\n" + "=" * 50)
        
        # Summary
        total = len(results)
        success = sum(1 for r in results if r.get("success"))
        failed = total - success
        lines.append(f"Summary: {success}/{total} succeeded, {failed} failed")
        
        return "\n".join(lines)
    
    # =========================================================================
    # System Prompt Integration
    # =========================================================================
    
    def get_tool_system_prompt(self) -> str:
        """
        Return system prompt addition for MCP awareness.
        
        This text should be added to the LLM's system prompt to enable
        tool calling capabilities.
        
        Returns:
            System prompt text describing tool usage
        """
        prompt_parts = [
            "## MCP Tool Integration",
            "",
            "You have access to the following tools via the Model Context Protocol (MCP).",
            "When you need to perform actions like reading files, executing commands,",
            "or fetching data, use the appropriate tool.",
            "",
            self.get_tool_descriptions(),
            "",
            "## How to Use Tools",
            "",
            "To invoke a tool, include a tool call in one of these formats:",
            "",
            "### Format 1: Markdown Block",
            "```tool:file.read",
            '{"path": "example.txt"}',
            "```",
            "",
            "### Format 2: Tool Call Tag",
            '<tool_call>file.read(path="example.txt")</tool_call>',
            "",
            "### Format 3: JSON Object",
            '{"tool": "file.read", "params": {"path": "example.txt"}}',
            "",
            "## Important Notes",
            "",
            "- Always explain what you're doing before making a tool call",
            "- Wait for tool results before continuing",
            "- Handle errors gracefully and explain them to the user",
            "- Use the appropriate tool for each task",
            ""
        ]
        
        return "\n".join(prompt_parts)
    
    def get_tool_context(self, analysis: Dict[str, Any]) -> str:
        """
        Generate context string based on request analysis.
        
        Provides hints to the LLM about which tools might be relevant.
        
        Args:
            analysis: Result from analyze_request()
            
        Returns:
            Context string for the LLM
        """
        if not analysis.get("needs_tools"):
            return ""
        
        lines = ["[MCP Context]"]
        lines.append(f"Detected intents: {', '.join(analysis['detected_intents'])}")
        lines.append(f"Suggested tools: {', '.join(analysis['suggested_tools'])}")
        
        extraction = analysis.get("extraction", {})
        if extraction.get("paths"):
            lines.append(f"Detected paths: {', '.join(extraction['paths'])}")
        if extraction.get("urls"):
            lines.append(f"Detected URLs: {', '.join(extraction['urls'])}")
        if extraction.get("commands"):
            lines.append(f"Detected commands: {', '.join(extraction['commands'])}")
        
        lines.append(f"Confidence: {analysis['confidence']:.2f}")
        
        return "\n".join(lines)


# =============================================================================
# Convenience Functions
# =============================================================================

def create_router(
    sandbox_root: str = ".",
    auto_execute: bool = False
) -> MCPRouter:
    """
    Create a fully configured MCP Router with server and client.
    
    Convenience function that sets up the complete MCP stack.
    
    Args:
        sandbox_root: Root directory for sandboxed operations
        auto_execute: If True, automatically execute detected tools
        
    Returns:
        Configured MCPRouter instance
        
    Example:
        >>> router = create_router(sandbox_root="./workspace")
        >>> analysis = router.analyze_request("read config.json")
    """
    from .server import MCPServer
    
    server = MCPServer(sandbox_root=sandbox_root)
    client = MCPClient(server)
    router = MCPRouter(client, auto_execute=auto_execute)
    
    return router


# Export public API
__all__ = [
    "MCPRouter",
    "RoutingRule",
    "INTENT_PATTERNS",
    "INTENT_TO_TOOL",
    "create_router"
]
