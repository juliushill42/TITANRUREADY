# TitanU Genesis Enforcement Plan

## 1. Machine Fingerprint Strategy

We will implement a "Minimal Enforcement" fingerprint that balances uniqueness with stability. It will generate a SHA-256 hash based on hardware identifiers that persist across simple updates but uniquely identify the hardware/OS installation.

### Python Implementation
We will utilize the `platform` and `uuid` standard libraries.

```python
import platform
import uuid
import hashlib

def get_device_fingerprint() -> str:
    """
    Generates a stable device fingerprint.
    Components:
    1. Node Name (Network name) - stable for most single-user setups.
    2. Machine Type (e.g., 'AMD64') - stable hardware architecture.
    3. MAC Address (uuid.getnode()) - unique to network interface.
    """
    components = [
        platform.node(),             # e.g., 'Desktop-Main'
        platform.machine(),          # e.g., 'AMD64'
        str(uuid.getnode())          # e.g., '2348234239' (MAC address based)
    ]
    
    # Combine with a separator to prevent boundary collision attacks
    combined = "|".join(filter(None, components))
    
    # Return first 16 chars of SHA-256 for a readable but unique ID
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]
```

## 2. `pro_license.json` Schema Definition

The existing schema will be expanded to support the Genesis binding logic.

**File Location:** `titanu-os/backend/titan_data/pro_license.json`

```json
{
  "license_key": "TITAN-GENESIS-XXXX-XXXX",
  "genesis_key_hash": "SHA256_HASH_OF_KEY_FOR_VERIFICATION",
  "activated": true,
  "tier": "genesis", 
  "features": {
    "hardware_acceleration": true,
    "enterprise_encryption": true,
    "advanced_browser": true,
    "cloud_llm": true,
    "wake_word": true,
    "analytics": true
  },
  "binding": {
    "device_fingerprint": "a1b2c3d4e5f6g7h8",
    "binding_timestamp": "2024-05-20T10:00:00Z",
    "rebind_count": 0,
    "last_verified": "2024-05-21T15:30:00Z"
  }
}
```

*   **Note:** Grouping binding fields under a `binding` object keeps the schema clean, but flat structure is also acceptable if preferred for simplicity. We will use a flat structure in implementation to match current `license.py` style if easier, but `binding` object is recommended for organization.

## 3. Enforcement Logic Flow

This logic will reside primarily in `ProLicense.validate_state()` (new method).

### A. Startup / Validation Check
Triggered when `Titan OS` starts or `check_license()` is called.

1.  **Load License:** Read `pro_license.json`. If missing or `activated: false`, return `Free Tier`.
2.  **Calculate Fingerprint:** Call `get_device_fingerprint()`.
3.  **Compare:**
    *   **Case 1: No Binding (First Run after Activation):**
        *   If `device_fingerprint` is missing/null in JSON:
            *   Write current fingerprint to `device_fingerprint`.
            *   Set `rebind_count` = 0.
            *   Set `binding_timestamp` = Now.
            *   **Result:** ALLOW (Activate).
    *   **Case 2: Fingerprint Match:**
        *   If stored `device_fingerprint` == calculated fingerprint:
            *   Update `last_verified` = Now.
            *   **Result:** ALLOW (Activate).
    *   **Case 3: Fingerprint Mismatch (Device Switch):**
        *   Check `rebind_count`.
        *   **Sub-case 3a: `rebind_count` < 1 (One Mercy Rebind):**
            *   Update `device_fingerprint` to new fingerprint.
            *   Increment `rebind_count` (+1).
            *   Log warning (internal or UI notification: "Genesis License re-bound to new device. No rebinds remaining.").
            *   **Result:** ALLOW (Activate).
        *   **Sub-case 3b: `rebind_count` >= 1:**
            *   **Result:** DENY (Deactivate).
            *   Return Error: "Genesis key bound to another device. Limit reached."

### B. Activation Logic (New Key Input)
Triggered when user enters a key in settings.

1.  **Validate Format:** Check if key matches Genesis format.
2.  **Verify Hash:** Verify `sha256(input_key) == genesis_key_hash` (if hash verification is implemented locally) or server-side mock.
3.  **Initialize Binding:**
    *   Set `device_fingerprint` = `get_device_fingerprint()`.
    *   Set `rebind_count` = 0.
    *   Save to `pro_license.json`.

## 4. Integration Points

### Backend Integration
**File:** `titanu-os/pro/licensing/license.py`

*   **Modify `ProLicense` class:**
    *   Update `__init__` to include new fields.
    *   Update `load()` and `save()` to handle new schema fields.
    *   Update `validate_key()` to include the fingerprint check logic defined above.
    *   Replace the placeholder `get_hardware_id` with the robust `get_device_fingerprint`.

**File:** `titan_os.py` (Main Backend)

*   **Import Integration:** Ensure `ProLicense` is initialized.
*   **Startup Check:** Call `check_license()` during startup sequence.
*   **API Endpoints:**
    *   **GET `/api/status`:** Piggyback here. Add a `license` object to the response.
        ```json
        {
          "online": true,
          "license": {
            "active": true,
            "tier": "genesis",
            "rebinds_remaining": 0,
             "error": null
          }
        }
        ```
    *   **POST `/api/license/activate`:** Create/Update endpoint to accept a key and trigger the Activation Logic.

### Frontend Integration
**Component:** `CommanderPane.jsx` (or Settings Modal)

*   **Status Display:** Poll `/api/status`. If `license.active` is true, show "Genesis Mode: ACTIVE".
*   **Error Handling:** If `license.error` is present (e.g., "Device Mismatch"), display a blocking or warning modal.
*   **Activation UI:** Add an input field for the License Key that POSTs to `/api/license/activate`.
