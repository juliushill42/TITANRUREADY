import os
import sys
import shutil
import hashlib
from pathlib import Path

RELEASE_DIR = Path("titanu-release")
BACKEND_EXE = "titan_backend.exe"
FRONTEND_EXE = "TitanU_OS_Genesis_Setup.exe"

def verify_file(filename):
    file_path = RELEASE_DIR / filename
    if not file_path.exists():
        print(f"FAIL: {filename} not found in {RELEASE_DIR}")
        return False
    
    size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"PASS: {filename} exists ({size_mb:.2f} MB)")
    
    # Simple check for empty files
    if size_mb < 0.0001:
        print(f"FAIL: {filename} is too small ({size_mb:.4f} MB)")
        return False
        
    return True

def main():
    print("Verifying Release Package...")
    
    if not RELEASE_DIR.exists():
        print(f"FAIL: Release directory {RELEASE_DIR} not found")
        sys.exit(1)
        
    checks = [
        verify_file(BACKEND_EXE),
        verify_file(FRONTEND_EXE),
        verify_file("checksums.csv"),
        verify_file("RELEASE_NOTES.md")
    ]
    
    if all(checks):
        print("\nAll release files verified successfully.")
    else:
        print("\nRelease verification FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
