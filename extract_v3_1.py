import zipfile
import os

zip_filename = 'TitanU-Genesis-v3.zip'
extract_to = 'temp_v3_1'

try:
    with zipfile.ZipFile(zip_filename, 'r') as z:
        z.extractall(extract_to)
        print(f"Extracted {zip_filename} to {extract_to}")
except Exception as e:
    print(f"Error extracting: {e}")
