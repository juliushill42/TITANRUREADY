import subprocess
import os
import time

key_path = "C:\\Users\\juliu\\.ssh\\titan_vast_key_new"
host = "154.42.3.37"
port = "20114"

def run_ssh(cmd):
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-p", port,
        "-i", key_path,
        f"root@{host}",
        cmd
    ]
    return subprocess.run(ssh_cmd, capture_output=True, text=True)

print("Starting vLLM with v0.x entrypoint...")
# Using the standard v0.x entrypoint and ensuring we use both GPUs
start_cmd = "nohup python3 -m vllm.entrypoints.openai.api_server --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 --host 0.0.0.0 --port 8000 --tensor-parallel-size 2 --enforce-eager > vllm_v0.log 2>&1 &"
run_ssh(start_cmd)
print("vLLM start command sent. Waiting for it to initialize...")

for i in range(15):
    time.sleep(10)
    print(f"Check {i+1}/15...")
    test_res = run_ssh("curl -s http://localhost:8000/v1/models")
    if test_res.stdout.strip() and "model" in test_res.stdout:
        print("vLLM is now responding!")
        print("Remote local test result:", test_res.stdout)
        break
else:
    print("vLLM did not start in time. Check vllm_v0.log on remote.")
