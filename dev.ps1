import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1] / "titanu-os"
    driver_script = repo_root / "scripts" / "build.py"

    if not driver_script.exists():
        print(f"Driver build script not found at {driver_script}")
        sys.exit(1)

    python_exe = sys.executable
    print(f"Running TitanU OS build pipeline via {driver_script}")

    try:
        subprocess.run(
            [python_exe, str(driver_script)],
            check=True,
            cwd=repo_root,
        )
    except subprocess.CalledProcessError as err:
        print("TitanU OS build pipeline failed.")
        print(err)
        sys.exit(err.returncode)


if __name__ == "__main__":
    main()
