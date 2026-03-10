import subprocess
import os

key_path = "C:\\Users\\juliu\\.ssh\\titan_vast_key_new"
host = "154.42.3.37"
port = "20114"

ssh_cmd = [
    "ssh", "-o", "StrictHostKeyChecking=no",
    "-p", port,
    "-i", key_path,
    f"root@{host}",
    "python3 -c 'import torch; print(\"CUDA available:\", torch.cuda.is_available()); print(\"Device count:\", torch.cuda.device_count())'"
]

result = subprocess.run(ssh_cmd, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
