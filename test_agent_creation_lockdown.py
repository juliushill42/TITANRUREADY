#!/usr/bin/env python3
"""
Test script to verify agent creation lockdown functionality
Tests all paths where agent creation could be attempted
"""

import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'titanu-os', 'backend'))

from core.features import initialize_feature_flags, is_agent_creation_enabled
from handlers.agents import handle_agents, create_agent, create_agent_from_description

def test_feature_flag_system():
    """Test that feature flag system is working correctly"""
    print("Testing feature flag system...")
    
    # Initialize with Genesis key present (should still disable agent creation)
    initialize_feature_flags(genesis_key_present=True)
    
    # Verify agent creation is disabled
    assert not is_agent_creation_enabled(), "Agent creation should be disabled"
    print("✓ Agent creation is correctly disabled")
    
    return True

def test_backend_handler_rejection():
    """Test that backend handler rejects agent creation"""
    print("\nTesting backend handler rejection...")
    
    # Test create action
    result = handle_agents("create", {
        "name": "Test Agent",
        "role": "Test role",
        "system_prompt": "Test prompt"
    })
    
    assert result.get("success") == False, "Should return success=False"
    assert result.get("code") == "FEATURE_DISABLED", "Should return FEATURE_DISABLED code"
    assert "v3.3" in result.get("message", ""), "Should mention v3.3"
    print("✓ Backend handler correctly rejects agent creation")
    
    # Test create_from_description action
    result = handle_agents("create_from_description", {
        "description": "Create an agent that helps with testing"
    })
    
    assert result.get("success") == False, "Should return success=False"
    assert result.get("code") == "FEATURE_DISABLED", "Should return FEATURE_DISABLED code"
    print("✓ Backend handler correctly rejects agent creation from description")
    
    return True

def test_direct_function_calls():
    """Test that direct function calls are blocked"""
    print("\nTesting direct function call blocking...")
    
    # Test create_agent function
    result = create_agent("Test Agent", "Test role", "Test prompt")
    assert result.get("success") == False, "Should return success=False"
    assert result.get("code") == "FEATURE_DISABLED", "Should return FEATURE_DISABLED code"
    print("✓ create_agent function correctly blocked")
    
    # Test create_agent_from_description function
    result = create_agent_from_description("Create a test agent")
    assert result.get("success") == False, "Should return success=False"
    assert result.get("code") == "FEATURE_DISABLED", "Should return FEATURE_DISABLED code"
    print("✓ create_agent_from_description function correctly blocked")
    
    return True

def test_ipc_layer_rejection():
    """Test that IPC layer rejects agent creation commands"""
    print("\nTesting IPC layer rejection...")
    
    # Import main module components
    from core.main import agents_handler, create_agent_handler
    
    # Test agents handler with create action
    result = agents_handler({"action": "create", "name": "Test"})
    assert result.get("status") == "error", "Should return error status"
    assert result.get("type") == "feature_disabled", "Should return feature_disabled type"
    payload = result.get("payload", {})
    assert payload.get("code") == "FEATURE_DISABLED", "Should return FEATURE_DISABLED code"
    print("✓ IPC agents handler correctly rejects creation")
    
    # Test create_agent handler
    result = create_agent_handler({"description": "Test agent"})
    assert result.get("status") == "error", "Should return error status"
    assert result.get("type") == "feature_disabled", "Should return feature_disabled type"
    print("✓ IPC create_agent handler correctly rejects creation")
    
    return True

def test_no_partial_creation():
    """Test that no partial agent objects are created when flag is disabled"""
    print("\nTesting no partial creation...")
    
    from handlers.agents import AGENTS_DIR
    import tempfile
    
    # Count agents before attempt
    initial_count = len(list(AGENTS_DIR.glob("*.json")))
    
    # Try to create agent (should fail)
    result = create_agent("Test Agent", "Test role", "Test prompt")
    assert result.get("success") == False, "Should fail"
    
    # Count agents after attempt
    final_count = len(list(AGENTS_DIR.glob("*.json")))
    
    assert initial_count == final_count, "No new agent files should be created"
    print("✓ No partial agent objects created")
    
    return True

def test_error_message_quality():
    """Test that error messages are user-friendly and consistent"""
    print("\nTesting error message quality...")
    
    # Test all paths return consistent error format
    paths_to_test = [
        lambda: handle_agents("create", {}),
        lambda: handle_agents("create_from_description", {}),
        lambda: create_agent("Test", "Test", "Test"),
        lambda: create_agent_from_description("Test")
    ]
    
    for i, test_func in enumerate(paths_to_test):
        result = test_func()
        
        # Check for required fields
        assert "error" in result or "code" in result, f"Path {i} should have error or code field"
        
        if "code" in result:
            assert result["code"] == "FEATURE_DISABLED", f"Path {i} should have FEATURE_DISABLED code"
        
        if "message" in result:
            assert "v3.3" in result["message"], f"Path {i} should mention v3.3"
        
        if "payload" in result:
            payload = result["payload"]
            assert "code" in payload, f"Path {i} payload should have code"
            assert "message" in payload, f"Path {i} payload should have message"
    
    print("✓ All error messages are consistent and user-friendly")
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("AGENT CREATION LOCKDOWN TEST SUITE")
    print("=" * 60)
    
    try:
        test_feature_flag_system()
        test_backend_handler_rejection()
        test_direct_function_calls()
        test_ipc_layer_rejection()
        test_no_partial_creation()
        test_error_message_quality()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Agent creation is properly locked down")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)