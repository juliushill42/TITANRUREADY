
import subprocess, json, sys, time, os
from pathlib import Path

# Get script directory to resolve paths reliably
SCRIPT_DIR = Path("c:/Users/juliu/Desktop/Titan_OS_Launch/titanu-os/backend")
BACKEND_PATH = SCRIPT_DIR / "core" / "main.py"

BACKEND_CMD = [sys.executable, str(BACKEND_PATH)]

def send(proc, obj):
    json_str = json.dumps(obj)
    print(f"[TEST] Sending: {json_str}")
    proc.stdin.write(json_str + "\n")
    proc.stdin.flush()

def read(proc):
    line = proc.stdout.readline()
    if line:
        line = line.strip()
        print(f"[TEST] Received: {line}")
    return line

# Run from the backend directory so imports work
proc = subprocess.Popen(
    BACKEND_CMD,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=sys.stderr, # Don't hide errors!
    text=True,
    cwd=str(SCRIPT_DIR)
)

print(f"[TEST] Started backend at {BACKEND_PATH}")

# Wait for READY
start_time = time.time()
while True:
    if proc.poll() is not None:
        print("[TEST] Backend process exited prematurely")
        sys.exit(1)
        
    line = read(proc)
    if not line:
        if time.time() - start_time > 10:
             print("[TEST] Timeout waiting for ready signal")
             proc.terminate()
             sys.exit(1)
        continue
        
    try:
        data = json.loads(line)
        if data.get("type") == "system" and data["payload"]["state"] == "ready":
            print("[TEST] Ready signal received")
            break
    except json.JSONDecodeError:
        print(f"[TEST] Ignored non-JSON line: {line}")
        continue

# Send chat with missing info query
send(proc, {
    "id": "test-missing-info",
    "command": "chat",
    "payload": {
        "message": "What is the secret code in the unmounted drive?",
        "model": "qwen2.5-coder:3b"
    }
})

# Read response
start_time = time.time()
while True:
    if proc.poll() is not None:
         print("[TEST] Backend exited before response")
         break
         
    if time.time() - start_time > 30:
        print("[TEST] Timeout waiting for response")
        break

    line = read(proc)
    if not line:
        continue
        
    try:
        resp = json.loads(line)
        # Look for the response to our specific ID
        if resp.get("id") == "test-missing-info":
             content = resp.get("payload", {}).get("message", "")
             print(f"[TEST] Response content: {content}")
             
             # Check for refusal
             refusal_keywords = ["cannot", "don't have", "no access", "unmounted", "unable", "sorry"]
             if any(keyword in content.lower() for keyword in refusal_keywords):
                 print("PASS: Model correctly refused to answer.")
             else:
                 print("FAIL: Model did not refuse or refusal was unclear.")
             break
    except json.JSONDecodeError:
        pass

proc.terminate()
