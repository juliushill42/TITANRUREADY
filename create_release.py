#!/usr/bin/env python3
"""
Script to create a GitHub release for TitanU OS v3.1.0 - Genesis.
This script uses the GitHub API to create a release and upload installer assets.
"""

import os
import sys
import requests
import json
import shutil
import zipfile
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# GitHub repository configuration
REPO_OWNER = "jufa44"
REPO_NAME = "TitanU-Genesis"
TAG_NAME = "v3.1.0"
RELEASE_NAME = "TitanU OS v3.1.0 - Genesis"
RELEASE_BODY = """TitanU OS v3.1.0 - Genesis Release

This release contains a single zip file, `TitanU-Genesis-v3.zip`, which includes:
- `TitanU-Genesis-Release/` directory containing all installer files.

Genesis represents the dawn of a new era in AI-powered operating systems.
"""

def get_github_token():
    """Get GitHub token from environment or prompt user."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GitHub token not found in environment variable GITHUB_TOKEN")
        print("Please set GITHUB_TOKEN environment variable with a valid GitHub personal access token")
        print("You can create one at: https://github.com/settings/tokens")
        sys.exit(1)
    return token

def delete_existing_release(token, headers):
    """Check for and delete an existing release and its tag."""
    print(f"\nChecking for existing release with tag {TAG_NAME}...")
    
    # Get release by tag
    get_release_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{TAG_NAME}"
    response = requests.get(get_release_url, headers=headers)
    
    if response.status_code == 200:
        release = response.json()
        release_id = release['id']
        print(f"Found existing release with ID: {release_id}. Deleting it...")
        
        # Delete the release
        delete_release_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/{release_id}"
        delete_response = requests.delete(delete_release_url, headers=headers)
        
        if delete_response.status_code == 204:
            print("Successfully deleted the existing release.")
        else:
            print(f"Error deleting release: {delete_response.status_code}")
            print(delete_response.text)
            sys.exit(1)

        # Delete the git tag
        print(f"Deleting git tag {TAG_NAME}...")
        delete_tag_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/tags/{TAG_NAME}"
        delete_tag_response = requests.delete(delete_tag_url, headers=headers)

        if delete_tag_response.status_code == 204:
            print(f"Successfully deleted git tag {TAG_NAME}.")
        else:
            # It might fail if the tag is part of a release, even if we just deleted it.
            # Or if it's a lightweight tag. GitHub API for deleting tags can be tricky.
            # We'll proceed even if this fails, as the release deletion is the most critical part.
            print(f"Warning: Could not delete git tag {TAG_NAME}. Status: {delete_tag_response.status_code}")
            print(delete_tag_response.text)
            print("This may be due to the tag being associated with a commit. Continuing...")

    elif response.status_code == 404:
        print("No existing release found. Proceeding to create a new one.")
    else:
        print(f"Error checking for existing release: {response.status_code}")
        print(response.text)
        sys.exit(1)

def get_ignored_patterns(gitignore_path):
    """Read and parse .gitignore file."""
    if not os.path.exists(gitignore_path):
        return []
    with open(gitignore_path, 'r') as f:
        patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return patterns

def is_ignored(path, ignore_patterns):
    """Check if a file or directory should be ignored."""
    path = Path(path)
    for pattern in ignore_patterns:
        if path.match(pattern):
            return True
    return False

def create_zip_with_gitignore(zip_filename, root_dir, gitignore_path):
    """Create a zip archive, respecting .gitignore patterns."""
    ignore_patterns = get_ignored_patterns(gitignore_path)
    
    print(f"Creating zip archive '{zip_filename}' from directory '{root_dir}'...")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_dir):
            # Exclude ignored directories
            dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d).replace(os.sep, '/'), ignore_patterns)]
            
            for file in files:
                file_path = os.path.join(root, file)
                if not is_ignored(file_path.replace(os.sep, '/'), ignore_patterns):
                    arcname = os.path.relpath(file_path, root_dir)
                    zipf.write(file_path, arcname)
    print("Zip archive created successfully.")


def create_release():
    """Create a GitHub release and upload assets."""

    # Define paths
    source_dir = "titanu-os"
    zip_filename = "TitanU-Genesis-v3.zip"
    gitignore_path = os.path.join(source_dir, ".gitignore")

    # Check if the source directory exists
    if not os.path.isdir(source_dir):
        print(f"Error: Source directory '{source_dir}' not found.")
        sys.exit(1)

    # Create the zip archive, respecting .gitignore
    try:
        create_zip_with_gitignore(zip_filename, source_dir, gitignore_path)
    except Exception as e:
        print(f"Error creating zip archive: {e}")
        sys.exit(1)

    installer_files = [zip_filename]
    
    print("Found required installer files:")
    for f in installer_files:
        size = os.path.getsize(f) / (1024 * 1024)  # Convert to MB
        print(f"  - {f} ({size:.1f} MB)")
    
    # Get GitHub token
    token = get_github_token()
    
    # GitHub API headers
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Delete existing release and tag if they exist
    delete_existing_release(token, headers)
    
    # Create release
    release_data = {
        "tag_name": TAG_NAME,
        "name": RELEASE_NAME,
        "body": RELEASE_BODY,
        "draft": True,
        "prerelease": False
    }
    
    print(f"\nCreating GitHub release {TAG_NAME}...")
    
    try:
        # Create the release
        response = requests.post(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases",
            headers=headers,
            json=release_data
        )
        
        if response.status_code != 201:
            print(f"Error creating release: {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        release = response.json()
        release_id = release["id"]
        upload_url = release["upload_url"].replace("{?name,label}", "")
        
        print(f"Release created successfully!")
        print(f"Release URL: {release['html_url']}")
        
        # Upload assets
        print(f"\nUploading assets...")
        for file_path in installer_files:
            file_name = os.path.basename(file_path)
            print(f"Uploading {file_name}...")
            
            with open(file_path, 'rb') as f:
                upload_headers = {
                    "Authorization": f"token {token}",
                    "Content-Type": "application/octet-stream"
                }
                
                upload_response = requests.post(
                    f"{upload_url}?name={file_name}",
                    headers=upload_headers,
                    data=f.read()
                )
                
                if upload_response.status_code != 201:
                    print(f"Error uploading {file_name}: {upload_response.status_code}")
                    print(upload_response.text)
                else:
                    asset = upload_response.json()
                    print(f"  ✓ Uploaded successfully ({asset['size'] / (1024*1024):.1f} MB)")
        
        print(f"\n✅ Release completed successfully!")
        print(f"📦 Release URL: {release['html_url']}")
        
    except Exception as e:
        print(f"Error during release creation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_release()