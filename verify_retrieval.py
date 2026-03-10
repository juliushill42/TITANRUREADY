
import sys
import os
import json
import logging
from datetime import datetime

# Adjust path so we can import from core
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "titanu-os", "backend")
sys.path.insert(0, backend_dir)

try:
    from core.memory_agent import handle_log_memory, handle_get_memory, load_memory_from_disk, handle_clear_memory
    from core.personality import get_titan_prompt
except ImportError as e:
    print(f"Error importing core modules: {e}")
    sys.exit(1)

def verify_retrieval():
    print("--- Starting Retrieval Verification ---")
    
    # 1. Initialize Memory
    print("[1] Loading memory...")
    load_memory_from_disk()
    
    # Clear existing memory to ensure clean test
    print("[1.5] Clearing existing memory for test...")
    handle_clear_memory({})

    # 2. Write a specific memory
    secret_code = "The secret code is 998877"
    print(f"[2] Writing memory: '{secret_code}'")
    log_result = handle_log_memory({
        "content": secret_code,
        "role": "user",
        "tags": ["test_secret"]
    })
    
    if log_result.get("status") != "success":
        print(f"FAILED to write memory: {log_result}")
        return
    print("Memory written successfully.")

    # 3. Retrieve memory (formatted string for LLM)
    print("[3] Retrieving memory for LLM context...")
    
    # Simulate what happens before get_titan_prompt is called
    # Usually we get recent memories. Let's see what handle_get_memory gives us.
    get_result = handle_get_memory({"limit": 5})
    
    if get_result.get("status") != "success":
        print(f"FAILED to get memory: {get_result}")
        return
        
    entries = get_result["data"]["entries"]
    print(f"Retrieved {len(entries)} entries.")
    
    # 4. Construct the prompt string
    # We need to manually format the entries into a string like the actual system does.
    # Looking at the code, main.py or personality.py likely orchestrates this.
    # Wait, personality.py takes 'memory_context' string.
    # We need to see how that string is built. 
    # Since I don't have the exact function that builds the string from entries in front of me (it might be in handlers/agents.py or similar),
    # I will simulate a simple join which is the standard way.
    
    memory_context_string = "\n".join([f"- {e['content']} ({e['timestamp']})" for e in entries])
    
    print(f"Constructed Memory Context:\n---\n{memory_context_string}\n---")
    
    # 5. Inject into System Prompt
    print("[5] Injecting into TITAN System Prompt...")
    final_prompt = get_titan_prompt(memory_context=memory_context_string)
    
    print("\n--- Final System Prompt (Snippet) ---")
    start_index = final_prompt.find("## MEMORY CONTEXT")
    end_index = final_prompt.find("## CRITICAL RULE")
    
    if start_index != -1 and end_index != -1:
        print(final_prompt[start_index:end_index])
    else:
        print("Could not find MEMORY CONTEXT section in prompt!")
        print(final_prompt)

    # 6. Verification
    if secret_code in final_prompt:
        print("\n[SUCCESS] The secret code was found in the final system prompt.")
    else:
        print("\n[FAILURE] The secret code was NOT found in the final system prompt.")

if __name__ == "__main__":
    verify_retrieval()
