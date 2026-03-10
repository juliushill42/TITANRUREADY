import sys
import subprocess
import json
import threading
import time
import os

def read_stderr(process):
    """Read stderr from the process and print it with a prefix"""
    for line in iter(process.stderr.readline, ''):
        print(f"[BACKEND_LOG] {line.strip()}")
    process.stderr.close()

def run_verification():
    print("Starting verification of TitanU OS Backend...")
    
    # Path to the backend script
    backend_script = os.path.join("titanu-os", "backend", "core", "main.py")
    
    if not os.path.exists(backend_script):
        print(f"Error: Backend script not found at {backend_script}")
        return

    # Start the backend process
    # We use python -u for unbuffered output to ensure we see things immediately
    print(f"Launching {backend_script}...")
    process = subprocess.Popen(
        [sys.executable, "-u", backend_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0  # Unbuffered
    )

    # Start a thread to read stderr (logs)
    stderr_thread = threading.Thread(target=read_stderr, args=(process,))
    stderr_thread.daemon = True
    stderr_thread.start()

    print("Waiting for initial boot frame...")
    
    # Give it a moment to boot
    time.sleep(2)

    try:
        # Read the first line of output which should be the boot frame
        # (Note: actual boot frame might be preceded by some debug noise if not strictly handled,
        # but main.py seems to try to suppress stdout noise)
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            
            print(f"[BACKEND_OUT] {line}")
            
            try:
                data = json.loads(line)
                if data.get("type") == "system" and data.get("payload", {}).get("state") == "ready":
                    print("✅ SUCCESS: Received Backend Ready Signal!")
                    break
            except json.JSONDecodeError:
                pass # Ignore non-JSON lines
                
        # Send a test command
        print("\nSending 'system' status check command...")
        test_command = {
            "id": "verify_1",
            "command": "system",
            "payload": {}
        }
        process.stdin.write(json.dumps(test_command) + "\n")
        process.stdin.flush()
        
        # Read response
        print("Waiting for response...")
        start_time = time.time()
        while time.time() - start_time < 5:
            line = process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
                
            print(f"[BACKEND_OUT] {line}")
            try:
                data = json.loads(line)
                if data.get("id") == "verify_1":
                    print("✅ SUCCESS: Received response to system command!")
                    print(f"Payload: {data.get('payload')}")
                    return
            except json.JSONDecodeError:
                pass
                
        print("❌ TIMEOUT: Did not receive response to test command.")

    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        print("\nTerminating backend process...")
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()

if __name__ == "__main__":
    run_verification()
