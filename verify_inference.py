import sys
sys.path.append('titanu-os/backend')
from ssh_client import ssh
from remote_config import config

def verify_inference():
    print("Connecting...")
    if not ssh.connect():
        print("Failed to connect")
        return

    print("Sending inference request...")
    # Using local curl on the remote machine to test connectivity on localhost first
    # This proves the service is listening inside the container
    check_cmd = f"""curl -X POST http://localhost:{config.api_port}/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{{"model": "{config.model}", "messages": [{{"role": "user", "content": "Hello! What is your name?"}}], "max_tokens": 50}}'"""
    
    exit_code, stdout, stderr = ssh.execute_command(check_cmd)
    
    print("\n--- Inference Result ---")
    print(stdout)
    
    if '"content":' in stdout:
        print("\nSUCCESS: Inference response received!")
    else:
        print("\nFAILURE: Invalid or no response.")
        print("STDERR:", stderr)
    
    ssh.close()

if __name__ == "__main__":
    verify_inference()
