# Release Repository Structure Plan

## Overview
We will create a clean, export-ready folder named `titanu-release` that serves as the root for the new private GitHub repository. This ensures we don't accidentally push build artifacts, temp files, or system-specific logs from the development environment.

## Directory Structure
```
titanu-release/
├── README.md               # Overview of the project, features, and quick links
├── SETUP.md                # Detailed installation instructions (Ollama, Keys, Installer)
├── INSTALLER/              # Directory containing the executable
│   └── TitanU OS Setup 3.1.2.exe  # The latest installer
├── SOURCE/                 # Source code snapshot (for reference/dev access)
│   ├── backend/            # Python backend source
│   ├── frontend/           # Electron/React source
│   ├── docs/               # Relevant documentation from the main repo
│   └── scripts/            # Useful dev scripts
└── .gitignore              # Git ignore file to keep the repo clean
```

## File Content Plan

### 1. README.md
*   **Title:** TitanU OS - Private Distribution
*   **Description:** Brief overview of TitanU OS (Local, Private, AI Desktop Assistant).
*   **Quick Start:**
    *   Link to `SETUP.md` for installation.
    *   Basic usage instructions.
*   **Features:** Bullet points of key capabilities (Genesis v3.3 features).
*   **Repository Structure:** Explanation of what's in `INSTALLER` and `SOURCE`.

### 2. SETUP.md
*   Based on `titanu-os/docs/GENESIS_SETUP_GUIDE.md` but simplified for the end-user (Luke).
*   **Prerequisites:** Ollama, Windows 10/11.
*   **Step-by-Step:**
    1.  Install Ollama & Pull Model (`qwen2.5-coder:3b`).
    2.  Run the Installer from `INSTALLER/` folder.
    3.  Activation process (Genesis Key).
*   **Troubleshooting:** Common issues.

### 3. Source Code
*   We will copy the `titanu-os` directory content into `SOURCE` but exclude:
    *   `node_modules`
    *   `__pycache__`
    *   `dist` / `build` folders
    *   `.git` (nested git)
    *   `venv` / `env`

## Execution Steps (Code Mode)
1.  **Create Directory:** `titanu-release` in the workspace root.
2.  **Copy Installer:** Copy `titanu-os/frontend/electron/TitanU-Genesis-Release/TitanU OS Setup 3.1.2.exe` to `titanu-release/INSTALLER/`.
3.  **Create Docs:** Write `README.md` and `SETUP.md` in `titanu-release/` based on the plan.
4.  **Copy Source:** Recursively copy `titanu-os` to `titanu-release/SOURCE/` using a script (python or shell) that respects excludes to avoid bloat.
5.  **Git Setup:** Initialize `git` in `titanu-release` (conceptually - user will run commands).
6.  **Instructions:** Output the exact sequence of commands the user needs to run to push this to their new private repo.
