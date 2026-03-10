
import requests
import json
import time
import os
import sys
import subprocess
import threading

def read_stdout(process, output_list):
    """Reads stdout from the process and appends to a list."""
    for line in iter(process.stdout.readline, b''):
        try:
            line_str = line.decode('utf-8').strip()
            if line_str:
                print(f"[BACKEND_OUT]: {line_str}")
                try:
                    data = json.loads(line_str)
                    output_list.append(data)
                except json.JSONDecodeError:
                    pass # Not JSON
        except Exception as e:
            print(f"Error reading stdout: {e}")

def read_stderr(process):
    """Reads stderr from the process."""
    for line in iter(process.stderr.readline, b''):
        try:
            line_str = line.decode('utf-8').strip()
            if line_str:
                print(f"[BACKEND_ERR]: {line_str}")
        except Exception as e:
            print(f"Error reading stderr: {e}")

def run_verification():
    print("--- Starting UI-Backend Integration Verification ---")
    
    # Path to main.py
    backend_path = os.path.join("titanu-os", "backend", "core", "main.py")
    if not os.path.exists(backend_path):
        print(f"Error: Backend not found at {backend_path}")
        return

    # Start the backend process
    print(f"Spawning backend: {backend_path}")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(os.path.join("titanu-os", "backend"))
    
    # Use -u for unbuffered output
    process = subprocess.Popen(
        [sys.executable, "-u", backend_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        bufsize=0 
    )

    output_list = []
    
    # Start threads for stdout and stderr
    stdout_thread = threading.Thread(target=read_stdout, args=(process, output_list))
    stdout_thread.daemon = True
    stdout_thread.start()
    
    stderr_thread = threading.Thread(target=read_stderr, args=(process,))
    stderr_thread.daemon = True
    stderr_thread.start()

    # Wait for startup
    time.sleep(5) 
    print("--- Backend initialized (assumed) ---")

    # TEST 1: Memory Persistence (Session Handling)
    test_content = f"Test Memory Entry {time.time()}"
    print(f"\n[TEST 1] Sending log_memory command: {test_content}")
    
    cmd_log = {
        "command": "log_memory",
        "params": {
            "content": test_content,
            "role": "user",
            "session_id": "default"
        }
    }
    
    process.stdin.write((json.dumps(cmd_log) + "\n").encode('utf-8'))
    process.stdin.flush()
    
    time.sleep(3) # Wait longer for FS write

    # TEST 2: Retrieve Memory
    print("\n[TEST 2] Sending get_memory command")
    cmd_get = {
        "command": "get_memory",
        "params": {
            "limit": 50
        }
    }
    process.stdin.write((json.dumps(cmd_get) + "\n").encode('utf-8'))
    process.stdin.flush()

    time.sleep(5) # Wait longer

    # Verify Results
    print("\n--- Verifying Results ---")
    
    memory_logged = False
    memory_found = False
    
    for msg in output_list:
        # Check for log success
        if msg.get("status") == "success" and msg.get("data", {}).get("message") == "Memory stored":
            memory_logged = True
            print("SUCCESS: Memory stored confirmation received.")
        
        # Check for retrieval
        data = msg.get("data", {})
        payload = msg.get("payload", {})
        
        entries = []
        if "entries" in data:
            entries = data["entries"]
        elif "entries" in payload:
            entries = payload["entries"]
        elif "entries" in msg:
            entries = msg["entries"]
            
        if entries:
            print(f"DEBUG: Found {len(entries)} entries in response.")
            for entry in entries:
                if entry.get("content") == test_content:
                    memory_found = True
                    print(f"SUCCESS: Retrieved memory entry matches: {entry.get('content')}")
                    break

    if memory_logged and memory_found:
        print("\n[CONCLUSION] UI-Backend Integration Verified: SUCCESS")
    else:
        print("\n[CONCLUSION] UI-Backend Integration Verified: FAILED")
        
        # DEBUG: Inspect the memory file directly
        try:
            app_data = os.getenv('LOCALAPPDATA')
            if app_data:
                mem_file = os.path.join(app_data, "TitanU", "memory", "memory.json")
                if os.path.exists(mem_file):
                    print(f"\nDEBUG: Memory file exists at {mem_file}")
                    try:
                        with open(mem_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if test_content in content:
                                print("DEBUG: Test content FOUND in memory.json file directly.")
                                print("       Persistence verified.")
                            else:
                                print("DEBUG: Test content NOT found in memory.json file.")
                    except Exception as e:
                        print(f"DEBUG: Error reading memory file: {e}")
                else:
                     print(f"\nDEBUG: Memory file NOT found at {mem_file}")
            else:
                print("DEBUG: LOCALAPPDATA env var not set")

        except Exception as e:
            print(f"DEBUG: Could not inspect memory file directly: {e}")

    print("\nTerminating backend...")
    process.terminate()
    process.wait()

if __name__ == "__main__":
    run_verification()
