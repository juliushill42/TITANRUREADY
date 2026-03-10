import paramiko
import os

key_dir = os.path.expanduser("~/.ssh")
keys = ["id_titanu", "id_runpod", "id_ed25519"]

print(f"Checking keys in {key_dir}...")

for key_name in keys:
    key_path = os.path.join(key_dir, key_name)
    if not os.path.exists(key_path):
        print(f"[MISSING] {key_name}")
        continue
        
    try:
        paramiko.Ed25519Key.from_private_key_file(key_path)
        print(f"[OK] {key_name} (Ed25519) - Not encrypted")
    except paramiko.PasswordRequiredException:
        print(f"[ENCRYPTED] {key_name} (Ed25519) - Password required")
    except paramiko.SSHException:
        try:
            paramiko.RSAKey.from_private_key_file(key_path)
            print(f"[OK] {key_name} (RSA) - Not encrypted")
        except paramiko.PasswordRequiredException:
            print(f"[ENCRYPTED] {key_name} (RSA) - Password required")
        except Exception as e:
            print(f"[ERROR] {key_name}: {e}")
    except Exception as e:
        print(f"[ERROR] {key_name}: {e}")
