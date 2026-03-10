import shutil
import os

source_dir = "titanu-os"
release_dir = "titanu-release/SOURCE"
installer_src = "titanu-os/frontend/electron/TitanU-Genesis-Release/TitanU OS Setup 3.1.2.exe"
installer_dst = "titanu-release/INSTALLER/TitanU OS Setup 3.1.2.exe"

# 1. Copy Installer
print(f"Copying installer from {installer_src} to {installer_dst}...")
try:
    shutil.copy2(installer_src, installer_dst)
    print("Installer copied successfully.")
except FileNotFoundError:
    print("Error: Installer file not found!")
except Exception as e:
    print(f"Error copying installer: {e}")

# 2. Copy Source Code (with filtering)
def ignore_patterns(path, names):
    ignore_list = [
        'node_modules', 
        '__pycache__', 
        'dist', 
        'build', 
        '.git', 
        'venv', 
        'env',
        'TitanU-Genesis-Release', # Build artifacts
        'test-package' # Heavy test artifacts
    ]
    # Filter out large files or irrelevant dirs
    return [n for n in names if n in ignore_list or n.endswith('.exe') or n.endswith('.zip')]

print(f"Copying source code from {source_dir} to {release_dir}...")
if os.path.exists(release_dir):
    shutil.rmtree(release_dir)

try:
    shutil.copytree(source_dir, release_dir, ignore=ignore_patterns)
    print("Source code copied successfully.")
except Exception as e:
    print(f"Error copying source code: {e}")

print("Release preparation complete.")
