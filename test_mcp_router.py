"""Quick test for MCP Router"""

from mcp import MCPRouter, RoutingRule, create_router, INTENT_PATTERNS
import json

def test_router():
    print("=" * 60)
    print("TitanU OS MCP Router Test")
    print("=" * 60)
    
    # Create router without client (analysis only mode)
    router = MCPRouter()
    
    print("\n1. Testing analyze_request:")
    test_cases = [
        "read the config.json file",
        "list files in ./src",
        "run command 'npm install'",
        "fetch https://api.example.com/data",
        "show system info",
        "what's in requirements.txt"
    ]
    
    for test in test_cases:
        result = router.analyze_request(test)
        print(f"\n   Input: '{test}'")
        print(f"   needs_tools: {result['needs_tools']}")
        print(f"   intents: {result['detected_intents']}")
        print(f"   tools: {result['suggested_tools']}")
        print(f"   confidence: {result['confidence']:.2f}")
    
    print("\n" + "=" * 60)
    print("2. Testing parse_llm_response:")
    
    # Test various LLM response formats
    responses = [
        # Markdown block format
        '''I'll read that file for you.
```tool:file.read
{"path": "config.json"}
```''',
        # Tool call tag format
        '''Let me check that file.
<tool_call>file.read(path="config.json")</tool_call>''',
        # JSON object format
        '''Reading file now.
{"tool": "file.read", "params": {"path": "test.txt"}}''',
        # Bracket format
        '''Executing: [[process.exec(command="ls -la")]]'''
    ]
    
    for resp in responses:
        tool_calls = router.parse_llm_response(resp)
        print(f"\n   Response format test:")
        print(f"   Found {len(tool_calls)} tool call(s)")
        for tc in tool_calls:
            print(f"     - {tc['tool']}: {tc['params']}")
    
    print("\n" + "=" * 60)
    print("3. Testing routing rules:")
    
    # Test custom rule
    custom_rule = RoutingRule(
        pattern=r"backup\s+(.+)",
        tool="file.copy",
        param_mapping={"1": "source"},
        priority=20,
        description="Backup file command"
    )
    router.add_routing_rule(custom_rule)
    
    result = router.analyze_request("backup important.txt")
    print(f"\n   Custom rule test: 'backup important.txt'")
    print(f"   suggested_tools: {result['suggested_tools']}")
    
    print("\n" + "=" * 60)
    print("4. Intent patterns coverage:")
    print(f"\n   Supported intents: {list(INTENT_PATTERNS.keys())}")
    
    print("\n" + "=" * 60)
    print("5. System prompt generation:")
    prompt = router.get_tool_system_prompt()
    print(f"\n   System prompt length: {len(prompt)} chars")
    print(f"   Preview: {prompt[:200]}...")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_router()