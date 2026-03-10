import sys
import os
import json
from pathlib import Path

# Add backend to path
backend_path = Path("titanu-os/backend").resolve()
sys.path.insert(0, str(backend_path))

try:
    from core.memory_agent import handle_get_memory, handle_log_memory
    
    # Test 1: Log a memory (to ensure we have something)
    print("Testing log_memory...")
    # We use a unique string to be sure
    test_content = "My name is Julius - VERIFICATION TEST"
    log_result = handle_log_memory({"content": test_content, "role": "user"})
    print(f"Log Result: {json.dumps(log_result)}")
    
    # Test 2: Get memory
    print("\nTesting get_memory...")
    get_result = handle_get_memory({"limit": 50})
    print(f"Get Result: {json.dumps(get_result)}")
    
    # Verify structure
    if "payload" in get_result:
        print("\nSUCCESS: Response contains 'payload' field.")
        entries = get_result["payload"].get("entries", [])
        found = any(e["content"] == test_content for e in entries)
        if found:
            print(f"SUCCESS: Found '{test_content}' in entries.")
        else:
            print(f"WARNING: Did not find '{test_content}' in entries.")
    else:
        print("\nFAILURE: Response missing 'payload' field.")
        if "data" in get_result:
            print("Found 'data' field instead - this confirms the bug.")
        print(f"Keys found: {list(get_result.keys())}")

except ImportError as e:
    print(f"ImportError: {e}")
    print(f"sys.path: {sys.path}")
except Exception as e:
    print(f"Error: {e}")
