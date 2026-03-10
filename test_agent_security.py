
import asyncio
import os
import sys
import json
import base64
from pathlib import Path

# Fix import paths
backend_path = os.path.abspath("titanu-os/backend")
sys.path.append(backend_path)

# Mock core.utils.DATA_DIR since we are running outside main app
import types
utils_mock = types.ModuleType("core.utils")
utils_mock.DATA_DIR = Path("titan_data")
utils_mock.DATA_DIR.mkdir(parents=True, exist_ok=True)
utils_mock.get_user_data_dir = lambda: Path("titan_data")
utils_mock.safe_path_join = lambda base, *args: base.joinpath(*args)
utils_mock.ensure_directory = lambda p: p.mkdir(parents=True, exist_ok=True)
utils_mock.detect_titan_drive = lambda: None

sys.modules["core.utils"] = utils_mock

# Mock prompts.loader
prompts_mock = types.ModuleType("prompts")
loader_mock = types.ModuleType("prompts.loader")
loader_mock.prompt_loader = lambda: None
sys.modules["prompts"] = prompts_mock
sys.modules["prompts.loader"] = loader_mock

# Mock core.features
features_mock = types.ModuleType("core.features")
features_mock.check_feature_access = lambda x: True
features_mock.is_agent_creation_enabled = lambda: True
features_mock.are_conversational_agents_enabled = lambda: True
sys.modules["core.features"] = features_mock


# Import handlers
# We need to manually add handlers/ to path to resolve 'core.utils' from inside handlers if they don't use absolute imports correctly
# But `handlers/agents.py` does `from core.utils import DATA_DIR`.
# We mocked `core.utils` in sys.modules, so it should work.

from handlers.files import handle_files, MANAGED_FILES_DIR
from handlers.agents import handle_agents

async def test_unauthorized_state_mutation():
    """
    Test attempting to perform a state-mutating action via an agent command WITHOUT granting write permissions.
    """
    print("\n--- Testing Unauthorized State Mutation ---\n")
    
    # Define a test file path
    test_filename = "persistence_test.txt"
    test_content = "This is a test write from test_agent_security.py."
    encoded_content = base64.b64encode(test_content.encode()).decode()
    
    target_path = MANAGED_FILES_DIR / test_filename
    
    # Clean up before test
    if target_path.exists():
        target_path.unlink()
    
    # 1. Simulate an Agent attempting to write a file via the Agent Handler
    # The agent handler (`handle_agents`) exposes agent management capabilities.
    # If an agent tries to use this handler to write a file, it should fail.
    
    print("Attempting to invoke 'save_file' action on Agent Handler...")
    
    # We call `handle_agents` with an action it DOES NOT support ("save_file")
    # This simulates an agent executing a tool call routed to the wrong handler, 
    # or trying to "jailbreak" the agent handler to do file ops.
    
    result = handle_agents("save_file", {
        "filename": test_filename, 
        "content": encoded_content
    })
    
    print(f"Agent Handler Response: {result}")
    
    if result.get("success") is False and "Unknown action" in result.get("error", ""):
        print("PASS: Agent Handler rejected file operation (Unknown Action).")
    else:
        print("FAIL: Agent Handler allowed file operation or gave unexpected error.")
        
    # 2. Simulate an Agent attempting to use 'invoke' to trigger a write
    # The `invoke` action runs `invoke_agent`, which returns a prompt.
    # It does NOT execute tools.
    
    print("Attempting to invoke agent with write command...")
    invoke_result = handle_agents("invoke", {
        "agent_id": "researcher", # Using a template ID
        "message": "Write a file to persistence_test.txt"
    })
    
    print(f"Invoke Result: {invoke_result}")
    
    if invoke_result.get("success") is False and "Agent not found" in invoke_result.get("error", ""):
        # We need to create it first or use a valid ID. 
        # But 'researcher' is a template. Let's create one.
        pass
    elif invoke_result.get("success") is True:
        # Check if file exists (it shouldn't, because invoke just returns text)
        if target_path.exists():
             print("FAIL: File was created solely by invoking the agent (Unexpected).")
        else:
             print("PASS: Invoking agent did NOT create file (System is safe by default).")

    # 3. Direct File Write (Control Case)
    # This simulates what happens if the FRONTEND calls the file handler directly (User Action).
    # This SHOULD work.
    print("Control: Attempting direct write via File Handler (User Action)...")
    file_result = handle_files("upload", {
        "filename": test_filename,
        "content": encoded_content
    })
    print(f"Direct Write Result: {file_result}")
    
    if file_result.get("success"):
        print("Control PASS: Direct write succeeded.")
        # Cleanup
        if target_path.exists():
            target_path.unlink()
    else:
        print("Control FAIL: Direct write failed.")

if __name__ == "__main__":
    asyncio.run(test_unauthorized_state_mutation())
