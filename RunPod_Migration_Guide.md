# Migrating from Vast.ai to RunPod for TitanU OS

Since the Vast.ai pod has stopped, we are migrating to RunPod for better stability and to avoid PTY/connection errors.

## 1. Recommended Template

When creating a new Pod on RunPod, search for and select this specific template:

**`runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04`**

### Why this template?
- **PyTorch 2.8.0**: Latest stable version with vLLM support.
- **Python 3.11**: Required for modern vLLM versions.
- **CUDA 12.8.1**: Supports newer GPUs (A40, RTX 4090, etc.).
- **Ubuntu 22.04**: Compatible base OS.

## 2. Essential Configuration (Prevent PTY Errors)

Before starting the pod, configure these settings:

1.  **Container Configuration**:
    *   Enable **"Interactive Terminal Access"**.
    *   Set **"SSH Server"** to **Enabled**.
    *   (Optional) Use "RunPod Volume" for persistence.
    *   **Port Exposure**: Ensure TCP port `8080` is exposed if you plan to access the API directly.

2.  **Post-Start Script**:
    Copy and paste this script into the "Post-Start Script" field. This script installs vLLM, configures SSH to prevent PTY errors, and starts the inference server automatically.

    ```bash
    #!/bin/bash

    # Update system packages
    apt update && apt upgrade -y

    # Install additional dependencies for vLLM
    apt install -y git curl wget build-essential

    # Install vLLM with all dependencies
    pip install vllm --upgrade

    # Configure SSH for PTY allocation (prevents connection errors)
    sed -i 's/#AllowTcpForwarding yes/AllowTcpForwarding yes/' /etc/ssh/sshd_config
    sed -i 's/#PermitTunnel yes/PermitTunnel yes/' /etc/ssh/sshd_config
    systemctl restart sshd

    # Create vLLM startup script
    cat > /root/start_vllm.sh << 'EOF'
    #!/bin/bash
    cd /root
    nohup python -m vllm.entrypoints.openai.api_server \
      --model Qwen/Qwen2.5-32B-Instruct \
      --tensor-parallel-size 2 \
      --host 0.0.0.0 \
      --port 8080 \
      --max-model-len 32768 \
      --trust-remote-code \
      --dtype auto \
      > vllm.log 2>&1 &
    echo "vLLM started with PID $!"
    EOF

    chmod +x /root/start_vllm.sh

    # Start vLLM
    /root/start_vllm.sh

    echo "RunPod setup complete!"
    echo "vLLM should be running on port 8080"
    echo "SSH is configured for PTY allocation"
    ```
    *Note: Adjust `--tensor-parallel-size` if you are using a different number of GPUs (e.g., 1 for a single RTX 4090).*

### Alternative: Custom Template with vLLM

If you want to create a custom template with vLLM pre-installed (to save startup time):

1. **Start with base template:** `runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04`
2. **Add to Container Configuration:**
   - **Container Volume:** 50GB+ (for model downloads)
   - **Expose Ports:** 8080 (for vLLM)
3. **Post-Start Script:** Use the script above (but you can skip the `pip install vllm --upgrade` line if you save the template after installation).

### Verification Steps

After RunPod starts:
1. **SSH into pod:** `ssh root@ssh.runpod.io -p YOUR_PORT`
2. **Check vLLM:** `curl http://localhost:8080/v1/models`
3. **Check logs:** `tail -f /root/vllm.log`

The vLLM installation will take 2-3 minutes during pod startup, but then it's ready to use immediately.

## 3. Connecting TitanU OS

Once your RunPod instance is running:

1.  Get the connection details from the RunPod dashboard (Connect button).
    *   **Host**: Usually `ssh.runpod.io`
    *   **Port**: A 5-digit port number (e.g., `22123`)
    *   **User**: `root`

2.  Update your local configuration:
    *   Open `titanu-os/backend/config/gpu_config.json`
    *   Update the `port` field with your new RunPod port.
    *   Ensure `host` is set to `ssh.runpod.io`.

    Example `gpu_config.json`:
    ```json
    {
      "provider": "runpod",
      "host": "ssh.runpod.io",
      "port": 22123,
      "user": "root",
      "local_port": 8080,
      "vllm_port": 8080,
      "model": "Qwen/Qwen2.5-32B-Instruct",
      "enabled": true
    }
    ```

3.  Restart TitanU OS Backend to apply changes.
