import requests
import json
import time
import subprocess
import os
import signal
import sys

# Configuration
BACKEND_URL = "http://localhost:5000"
BACKEND_SCRIPT = "titanu-os/backend/core/main.py"
VENV_PYTHON = "venv/Scripts/python" # Adjust based on environment

def start_backend():
    """Start the backend server"""
    print("[Test] Starting backend...")
    # Using python directly assuming environment is set up or use venv path
    try:
        process = subprocess.Popen([sys.executable, BACKEND_SCRIPT], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  cwd="titanu-os/backend")
        time.sleep(5)  # Wait for startup
        return process
    except Exception as e:
        print(f"[Test] Failed to start backend: {e}")
        return None

def test_models_endpoint():
    """Test the /api/models endpoint"""
    print("[Test] Testing /api/models endpoint...")
    
    url = f"{BACKEND_URL}/api/models"
    headers = {"Content-Type": "application/json"}
    payload = {"action": "list"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            print(f"[Test] FAILED: Status code {response.status_code}")
            print(response.text)
            return False
            
        data = response.json()
        print(f"[Test] Response received: {json.dumps(data, indent=2)}")
        
        # Validation checks
        if data.get("type") != "control":
            print("[Test] FAILED: Response type is not 'control'")
            return False
            
        if "message" in data:
            print("[Test] FAILED: Response contains leaked 'message' field")
            return False
            
        if "data" not in data:
             print("[Test] FAILED: Response missing 'data' field")
             return False
             
        print("[Test] SUCCESS: /api/models returned correct control format without leakage")
        return True
        
    except Exception as e:
        print(f"[Test] Error during request: {e}")
        return False

def main():
    # Check if backend is running, if not start it? 
    # For now assuming backend is running or user can run it.
    # Actually, let's try to hit it first.
    
    try:
        requests.get(f"{BACKEND_URL}/health", timeout=2)
        print("[Test] Backend appears to be running.")
    except:
        print("[Test] Backend not reachable. Please start the backend manually or in another terminal.")
        # We won't auto-start here to avoid conflict with existing terminals
        # return
    
    success = test_models_endpoint()
    
    if success:
        print("\n[Test] VERIFICATION SUCCESSFUL: Control plane leakage fixed.")
    else:
        print("\n[Test] VERIFICATION FAILED.")

if __name__ == "__main__":
    main()
