import zipfile
import json
import os

zip_filename = 'TitanU-Genesis-v3.zip'

try:
    with zipfile.ZipFile(zip_filename, 'r') as z:
        # List files to find package.json
        for filename in z.namelist():
            if filename.endswith('package.json') and 'frontend' in filename:
                print(f"Found: {filename}")
                with z.open(filename) as f:
                    content = json.load(f)
                    print(f"Version: {content.get('version')}")
except FileNotFoundError:
    print(f"{zip_filename} not found.")
except Exception as e:
    print(f"Error: {e}")

zip_filename_2 = 'TitanU_OS_v3_Genesis.zip'
try:
    with zipfile.ZipFile(zip_filename_2, 'r') as z:
         # List files to find package.json
        for filename in z.namelist():
            if filename.endswith('package.json') and 'frontend' in filename:
                print(f"Found in {zip_filename_2}: {filename}")
                with z.open(filename) as f:
                    content = json.load(f)
                    print(f"Version: {content.get('version')}")
except FileNotFoundError:
    print(f"{zip_filename_2} not found.")
except Exception as e:
    print(f"Error: {e}")
