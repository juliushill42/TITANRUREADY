# Llama.cpp Integration Plan - TitanU OS

## Current State
- The backend uses `Ollama` via HTTP API (`http://localhost:11434/api/chat` or `/api/generate`).
- `LLMClient` in `titanu-os/backend/core/llm_client.py` handles the HTTP requests.
- `ModelRegistry` in `titanu-os/backend/core/model_registry.py` defines model metadata and endpoints.
- `titan_llm.py` (root) also contains a similar client using the `openai` Python package pointing to Ollama.

## Objective
Modify the implementation to use `llama.cpp`'s `llama-cli.exe` for local inference with the `LFM2.5-1.2B-Instruct-Q4_K_M.gguf` model.

## Proposed Changes

### 1. New Local Inference Handler
Create `titanu-os/backend/core/llama_cpp_handler.py` to handle direct execution of `llama-cli.exe`.
- Function to build command line arguments for `llama-cli.exe`.
- Async function to run the process and capture output.
- Support for prompt templates (ChatML or similar).

### 2. Update `ModelSpec` and `ModelRegistry`
- Add a new provider type: `llama-cpp`.
- Update `TIER_0_MODELS` to include the `LFM2.5-1.2B` model with the `llama-cpp` provider.
- Store the path to `llama-cli.exe` and the `.gguf` model in environment variables or configuration.

### 3. Update `LLMClient`
- Modify `LLMClient.chat` to check the model provider.
- If provider is `llama-cpp`, route the request to `LlamaCppHandler` instead of making an HTTP request to Ollama.
- Ensure the interface remains compatible for `CentralBrain` and other agents.

### 4. Configuration
- Specified model: `LFM2.5-1.2B-Instruct-Q4_K_M.gguf`
- CLI: `llama-cli.exe`
- We need to determine the default paths for these files.
  - Recommended: `tools/llama-cli.exe` and `models/LFM2.5-1.2B-Instruct-Q4_K_M.gguf`.

## Implementation Steps
1.  **Define Paths**: Assume `tools/llama-cli.exe` and `models/LFM2.5-1.2B-Instruct-Q4_K_M.gguf`.
2.  **Create `llama_cpp_handler.py`**:
    - Implement `run_llama_cli(prompt, system_prompt, ...)`
3.  **Modify `model_registry.py`**:
    - Update `ModelSpec` to support `llama-cpp` provider.
    - Add `LFM2.5-1.2B` to `TIER_0_MODELS`.
4.  **Modify `llm_client.py`**:
    - Import `llama_cpp_handler`.
    - Logic to switch between `requests` (Ollama) and `llama_cli` (llama.cpp).
5.  **Test**:
    - Create a test script to verify `llama-cli.exe` execution.
    - Verify integration through `LLMClient`.
