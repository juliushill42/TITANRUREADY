import subprocess
import os

key_path = os.path.expanduser("~/.ssh/titan_vast_key_new")
if os.path.exists(key_path):
    os.remove(key_path)
if os.path.exists(key_path + ".pub"):
    os.remove(key_path + ".pub")

subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", key_path, "-N", ""], check=True)
print(f"Key created at {key_path}")
with open(key_path + ".pub", "r") as f:
    print("\n--- PUBLIC KEY ---")
    print(f.read())
    print("------------------")
