import sys
from pathlib import Path
import os

# Add backend to path so we can import modules
backend_path = Path(__file__).parent / "titanu-os" / "backend"
sys.path.append(str(backend_path))

try:
    from remote_config import RemoteGPUConfig
    
    print("Loading configuration...")
    config = RemoteGPUConfig.load()
    
    print("\n--- Loaded Configuration ---")
    print(f"Provider: {config.provider}")
    print(f"Host: {config.host}")
    print(f"Port: {config.port}")
    print(f"User: {config.user}")
    print(f"Key Path: {config.key_path}")
    
    print("\n--- Environment Variables ---")
    print(f"TITAN_GPU_HOST: {os.environ.get('TITAN_GPU_HOST')}")
    print(f"TITAN_GPU_PORT: {os.environ.get('TITAN_GPU_PORT')}")
    
    # Check if values match expected .env values
    expected_host = "69.30.85.29"
    expected_port = 22031
    
    if config.host == expected_host and config.port == expected_port:
        print("\nSUCCESS: Configuration loaded correctly from .env!")
    else:
        print(f"\nFAILURE: Configuration mismatch. Expected host {expected_host}, got {config.host}")

except ImportError as e:
    print(f"ImportError: {e}")
    print(f"Sys Path: {sys.path}")
except Exception as e:
    print(f"Error: {e}")
