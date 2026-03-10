# Plan to Resolve Backend Spawning Conflict

## Analysis
The core issue is a conflict between how the development script (`dev.bat`) and the Electron main process (`main.js`) manage the backend.

1.  **Duplicate Spawning**:
    *   `dev.bat` runs `npm run dev`, which concurrently runs Vite and Electron.
    *   `main.js` (Electron) *always* attempts to spawn the Python backend on startup.
    *   `boot_sequence.py` (Python) uses a lockfile (`titan_backend.lock`) to enforce a single instance.
    *   **Result**: When `main.js` starts the backend, if there is *already* a backend running (e.g., if the user manually started one or a previous zombie process exists), the new backend detects the lockfile and aborts. However, `main.js` expects to control the backend via stdin/stdout. If the backend aborts, `main.js` loses its connection, resulting in "Backend not available".

2.  **IPC vs. HTTP**:
    *   The current architecture in `main.js` relies heavily on **stdio (stdin/stdout)** for IPC. It sends JSON commands to the Python process's stdin and listens for JSON responses on stdout.
    *   `main.py` is capable of running a FastAPI app (lines 151-158), but the main loop (lines 965-988) is designed for `sys.stdin` reading.
    *   **Conclusion**: We must preserve the stdio-based IPC because rewriting the entire Electron frontend to use HTTP/WebSockets is a larger scope than fixing the spawning issue, and stdio is more robust for a local embedded backend.

3.  **The Fix Strategy**:
    *   **Goal**: Ensure `main.js` is the *sole* owner of the backend process during normal operation.
    *   **Mechanism**:
        *   Modify `boot_sequence.py` to allow a "force" override or better stale lock handling, but primarily trust `main.js`.
        *   CRITICAL: `main.js` is *already* trying to spawn it. The error is likely that a *previous* instance didn't clean up the lock file, or the user is running a separate backend instance manually which conflicts.
        *   **Refined Goal**: Make `main.js` smarter. It should check if the lockfile exists. If it does, check if that process is actually running.
            *   If running: Decide whether to kill it (to take ownership) or connect to it (hard with stdio). **Decision: Kill it.** Electron should be the master. If a user runs a manual backend, Electron should probably warn or take over. But for `dev.bat`, we want to ensure *clean* startups.
            *   If not running (stale lock): Delete lock and proceed.
        *   **Python Side**: The `boot_sequence.py` already checks for stale locks (lines 33-53). It checks if PID exists.
            *   *Issue*: If `main.js` spawns a NEW python process, that new process checks the lock. If an *old* python process is still running (zombie), the new one dies.
    *   **Solution**:
        *   Update `main.js` to *pre-check* and *kill* any existing backend process *before* spawning a new one. This ensures it starts with a clean slate.
        *   Use the lockfile to identify the PID of the potential zombie.

## Detailed Plan

### 1. Modify `main.js` (Electron)
*   **Action**: Add a `cleanupExistingBackend()` function before `startPython()`.
*   **Logic**:
    *   Read `titan_backend.lock` from the user data directory.
    *   If it exists, read the PID.
    *   Check if that PID is running.
    *   If running, `process.kill(pid)`. Log this action ("Killing zombie backend...").
    *   Delete the lockfile to be sure.
*   **Benefit**: Guarantees `startPython()` spawns into a clean environment.

### 2. Verify `boot_sequence.py` (Python)
*   **Action**: Review the `check_and_create_lock` function.
*   **Current State**: It checks for a lock, checks if PID is running, and if so, aborts. This is correct behavior for the *backend*, but `main.js` needs to be the enforcer to prevent this abort.
*   **Improvement**: Ensure `remove_lock` is robustly called on all exit paths (already in `signal_handler`, but double-check `atexit`).

### 3. Dev Script vs. Main.js
*   `dev.bat` runs `npm run dev`.
*   `npm run dev` runs `electron .`.
*   `main.js` runs `startPython()`.
*   **Conflict Source**: If the developer *manually* runs `python main.py` in another terminal, `main.js` will fail.
*   **Resolution**: The `cleanupExistingBackend` in `main.js` will kill the manual instance. This is acceptable for a "Commander Edition" where the app is the OS.

### 4. Implementation Steps (Code Mode)

1.  **Edit `titanu-os/frontend/electron/main.js`**:
    *   Import `fs` and `path` (already there).
    *   Implement `cleanupExistingBackend()`:
        *   Path: `path.join(app.getPath("userData"), "titan_backend.lock")`.
        *   Read PID.
        *   `try { process.kill(pid); } catch (e) { ... }`
        *   `fs.unlinkSync(lockPath)`.
    *   Call this inside `app.whenReady()` *before* `startPython()`.

2.  **Verify `titanu-os/backend/core/boot_sequence.py`**:
    *   Ensure `LOCK_FILE_NAME` matches what `main.js` looks for.
    *   (It is currently "titan_backend.lock").

3.  **Testing**:
    *   Simulate a "zombie" backend (run python manually).
    *   Start Electron.
    *   Verify zombie is killed and new backend starts successfully.

## Todo List
*   [ ] Create `cleanup_backend.js` utility in `titanu-os/frontend/electron/resources/` (or inline in main.js if simple) to handle lockfile cleanup. -> Inline is better for simplicity.
*   [ ] Modify `titanu-os/frontend/electron/main.js` to implement `cleanupExistingBackend`.
*   [ ] Verify the lockfile path aligns with `titanu-os/backend/core/boot_sequence.py` (`titan_backend.lock`).
*   [ ] Add logging to `main.js` to confirm when it cleans up a zombie process.
