import sys
sys.path.append('titanu-os/backend')
from ssh_client import ssh
import time

def manual_startup():
    print("Connecting...")
    if not ssh.connect():
        print("Failed to connect")
        return

    print("Uploading script...")
    ssh.upload_file('titanu-os/backend/start_vllm.sh', 'start_vllm.sh')
    
    print("Making executable...")
    ssh.execute_command('chmod +x start_vllm.sh')
    
    print("Starting vLLM...")
    ssh.execute_command('nohup ./start_vllm.sh > vllm.log 2>&1 &')
    
    print("Tailing logs...")
    for i in range(20):
        _, stdout, _ = ssh.execute_command('tail -n 10 vllm.log', stream_output=False)
        print(f"--- Log Check {i+1} ---")
        print(stdout)
        if "Uvicorn running on" in stdout:
            print("SUCCESS: vLLM started!")
            break
        time.sleep(5)
    
    ssh.close()

if __name__ == "__main__":
    manual_startup()
