import zipfile
import os

zips = ["TitanU-Genesis-v3.zip", "TitanU_OS_v3_Genesis.zip"]

for zip_path in zips:
    if os.path.exists(zip_path):
        print(f"--- Contents of {zip_path} (top 10) ---")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # List first 10 files to get an idea of structure
                for file in zip_ref.namelist()[:10]:
                    print(file)
        except Exception as e:
            print(f"Error reading {zip_path}: {e}")
    else:
        print(f"{zip_path} not found.")
