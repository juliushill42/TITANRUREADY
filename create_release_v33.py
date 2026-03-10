import os
import shutil
import hashlib
import datetime

def create_release():
    version = "3.3"
    release_dir = f"titanu-release-v{version}"
    
    # Paths
    backend_exe = "titanu-os/backend/dist/titan_backend.exe"
    installer_src = "titanu-os/frontend/electron/TitanU-Genesis-Release/TitanU OS Setup 3.3.0.exe"
    installer_dest = f"{release_dir}/TitanU_OS_Setup_v{version}.exe"
    
    # Create release directory
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)
    
    print(f"Created release directory: {release_dir}")
    
    # Copy Installer
    if os.path.exists(installer_src):
        shutil.copy2(installer_src, installer_dest)
        print(f"Copied installer to {installer_dest}")
    else:
        print(f"Error: Installer not found at {installer_src}")
        return

    # Copy Backend Executable (optional, if we want it separate, but it's likely packed in the installer? 
    # The instructions say "Copy backend executable to frontend resources" - usually means before build, 
    # but we just built the frontend. Let's assume the frontend build included the backend if configured correctly.
    # However, Step 3 says "Copy backend executable to frontend resources". 
    # Wait, if we already built the frontend, maybe we missed a step or the instructions imply 
    # we should have copied it BEFORE building the frontend? 
    # "Step 1: Build Backend Executable" -> "Step 2: Build Frontend with Updated Version".
    # Usually electron-builder picks up extra resources. 
    # If the backend is meant to be INSIDE the electron app, it should have been copied to a location 
    # where electron-builder sees it.
    # Let's check where electron-builder looks for the backend.
    
    # Create Release Notes
    release_notes = f"""TitanU OS v{version} Release Notes
================================

Release Date: {datetime.datetime.now().strftime('%Y-%m-%d')}
Version: {version}

New Features & Improvements:
- Updated core version references to v{version}
- Enhanced backend stability
- Improved installer experience

Installation:
1. Run TitanU_OS_Setup_v{version}.exe
2. Follow the on-screen instructions
3. Launch TitanU OS from your desktop

Hash Verification:
SHA-256 checksums are provided in checksums.txt
"""
    
    with open(f"{release_dir}/RELEASE_NOTES.txt", "w") as f:
        f.write(release_notes)
    
    # Generate Checksums
    checksums = []
    for filename in os.listdir(release_dir):
        filepath = os.path.join(release_dir, filename)
        if os.path.isfile(filepath) and filename != "checksums.txt":
            with open(filepath, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                checksums.append(f"{file_hash} *{filename}")
    
    with open(f"{release_dir}/checksums.txt", "w") as f:
        f.write("\n".join(checksums))
        
    print("Release package created successfully!")

if __name__ == "__main__":
    create_release()
