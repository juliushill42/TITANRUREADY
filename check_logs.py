from titanu_os.backend.ssh_client import ssh
import time

if __name__ == "__main__":
    if ssh.connect():
        print("--- vllm.log tail ---")
        code, stdout, stderr = ssh.execute_command("tail -n 20 vllm.log")
        print(stdout)
        print(stderr)
        ssh.close()
