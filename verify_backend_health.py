import sys
import json
import time
import subprocess
import os
import requests
import unittest
import threading

# Add backend directory to sys.path to import modules if needed, 
# though we'll primarily test via IPC/subprocess to simulate real usage
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'titanu-os', 'backend'))
sys.path.append(BACKEND_DIR)

class TestBackendHealth(unittest.TestCase):
    def setUp(self):
        self.backend_process = None
        self.backend_ready = False
        self.output_queue = []

    def tearDown(self):
        if self.backend_process:
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()

    def start_backend(self):
        """Starts the backend process and waits for initialization."""
        cmd = [sys.executable, os.path.join(BACKEND_DIR, 'core', 'main.py')]
        
        # Set environment variables if needed
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        self.backend_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
            cwd=BACKEND_DIR # Run from backend dir as expected
        )
        
        # Read stdout in a separate thread to avoid blocking
        self.stdout_thread = threading.Thread(target=self._read_stdout)
        self.stdout_thread.daemon = True
        self.stdout_thread.start()
        
        # Also read stderr for debugging
        self.stderr_thread = threading.Thread(target=self._read_stderr)
        self.stderr_thread.daemon = True
        self.stderr_thread.start()

    def _read_stdout(self):
        """Reads stdout and prints it for debugging."""
        try:
            while self.backend_process and self.backend_process.poll() is None:
                if self.backend_process.stdout:
                    line = self.backend_process.stdout.readline()
                    if line:
                        print(f"[STDOUT] {line.strip()}")
                        self.output_queue.append(line)
                        if "PYTHON_STARTING" in line or "Backend ready" in line:
                            self.backend_ready = True
                    else:
                        time.sleep(0.01)
        except Exception as e:
            print(f"Error reading stdout: {e}")

    def _read_stderr(self):
        """Reads stderr and prints it for debugging."""
        try:
            while self.backend_process and self.backend_process.poll() is None:
                if self.backend_process.stderr:
                    line = self.backend_process.stderr.readline()
                    if line:
                        print(f"[STDERR] {line.strip()}")
                    else:
                        time.sleep(0.01)
        except Exception as e:
            print(f"Error reading stderr: {e}")

    def send_command(self, command):
        """Sends a JSON command to the backend via stdin."""
        if not self.backend_process:
            raise RuntimeError("Backend not started")
        
        try:
            json_cmd = json.dumps(command) + "\n"
            if self.backend_process.stdin:
                print(f"Sending command: {json_cmd.strip()}")
                self.backend_process.stdin.write(json_cmd)
                self.backend_process.stdin.flush()
        except Exception as e:
            print(f"Error sending command: {e}")

    def get_response(self, timeout=5):
        """Reads a JSON response from accumulated output."""
        start_time = time.time()
        start_index = 0
        
        while time.time() - start_time < timeout:
            # Check new lines in output_queue
            current_len = len(self.output_queue)
            for i in range(start_index, current_len):
                line = self.output_queue[i].strip()
                # Skip known log prefixes or debug messages if they aren't JSON
                if not line or line.startswith("DEBUG:") or line.startswith("INFO") or line.startswith("[PY]"):
                    continue
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    pass # Ignore non-JSON lines
            
            start_index = current_len
            time.sleep(0.1)
        return None

    def test_backend_startup_and_ping(self):
        """Task 1: Validate process startup and basic command response."""
        print("\nTesting Backend Startup & Ping...")
        self.start_backend()
        
        # Wait for backend to be ready
        print("Waiting for backend ready signal...")
        start_wait = time.time()
        while not self.backend_ready and time.time() - start_wait < 15:
            time.sleep(0.5)
            
        if not self.backend_ready:
            print("Warning: Backend readiness flag not set (PYTHON_STARTING not seen in stdout)")
        else:
            print("Backend reported ready.")
        
        # Try a simple command. 'models' with action 'list' is a good candidate.
        ping_cmd = {"command": "models", "data": {"action": "list"}}
        self.send_command(ping_cmd)
        
        response = self.get_response(timeout=10)
        print(f"Ping (Models) Response: {response}")
        
        if response is None:
             print("Check STDOUT/STDERR logs above for why no response was received.")
        
        self.assertIsNotNone(response, "No response received from backend")
        self.assertTrue(isinstance(response, dict))

    def test_core_commands(self):
        """Task 2: Command Validation (prompt, models)."""
        # We can reuse the backend instance if we want, but for isolation let's restart or just continue if alive.
        # unittest runs setUp/tearDown per test, so it will restart.
        
        print("\nTesting Core Commands...")
        self.start_backend()
        
        # Wait for ready
        start_wait = time.time()
        while not self.backend_ready and time.time() - start_wait < 15:
            time.sleep(0.5)

        # Test 'models' command
        models_cmd = {"command": "models", "data": {"action": "list"}}
        self.send_command(models_cmd)
        response = self.get_response(timeout=10)
        print(f"Models Response: {response}")
        self.assertIsNotNone(response)

        # Test 'prompt' command (simple)
        # Note: Previous run failed because 'text' was expected but 'prompt' was sent, or structure was slightly off.
        # Let's fix the payload to match what the backend likely expects.
        # Based on logs: "DEBUG handle_prompt: No text provided"
        # The backend expects "text" key in data probably.
        prompt_cmd = {
            "command": "prompt", 
            "data": {
                "text": "Hello", 
                "model": "titan-embed-text-v1" 
            }
        }
        self.send_command(prompt_cmd)
        response = self.get_response(timeout=15)
        print(f"Prompt Response: {response}")
        self.assertIsNotNone(response)

    def test_inference_error_handling(self):
        """Task 3: Test inference error handling (simulated failures)."""
        print("\nTesting Inference Error Handling...")
        self.start_backend()
        
        # Wait for ready
        start_wait = time.time()
        while not self.backend_ready and time.time() - start_wait < 15:
            time.sleep(0.5)

        # Simulate an error by asking for a non-existent model or invalid parameters
        # This checks if the backend crashes or returns a proper error message
        error_cmd = {
            "command": "prompt",
            "data": {
                "text": "This should fail",
                "model": "non-existent-model-xyz"
            }
        }
        self.send_command(error_cmd)
        
        response = self.get_response(timeout=15)
        print(f"Error Test Response: {response}")
        
        self.assertIsNotNone(response)
        # We expect either a success (if it falls back) or an error, but NOT a crash (timeout/None)
        # Ideally we check type="error" or similar.
        
        # Verify backend is still alive by sending another simple command
        ping_cmd = {"command": "models", "data": {"action": "list"}}
        self.send_command(ping_cmd)
        ping_response = self.get_response(timeout=5)
        self.assertIsNotNone(ping_response, "Backend died after error test")

    def test_restart_resilience(self):
        """Task 4: Verify backend restart resilience."""
        print("\nTesting Restart Resilience...")
        
        # Start first instance
        self.start_backend()
        start_wait = time.time()
        while not self.backend_ready and time.time() - start_wait < 15:
            time.sleep(0.5)
            
        # Send a command to change state (if any state persistence existed, we'd check it)
        # For now, just verify it's working
        models_cmd = {"command": "models", "data": {"action": "list"}}
        self.send_command(models_cmd)
        self.get_response(timeout=10)
        
        # Kill it (simulated by tearDown, but let's be explicit)
        if self.backend_process:
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
        self.backend_process = None
        self.backend_ready = False
        
        print("Backend stopped. Restarting...")
        time.sleep(2) # Give it a moment
        
        # Restart
        self.start_backend()
        start_wait = time.time()
        while not self.backend_ready and time.time() - start_wait < 15:
            time.sleep(0.5)
            
        if not self.backend_ready:
            print("Warning: Backend failed to restart properly")
            
        # Verify it still works
        self.send_command(models_cmd)
        response = self.get_response(timeout=10)
        print(f"Post-Restart Response: {response}")
        self.assertIsNotNone(response, "Backend failed to respond after restart")

if __name__ == '__main__':
    unittest.main(verbosity=2)
