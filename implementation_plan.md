# Titan OS v1.1 Upgrade Plan: Remote LLM Integration (RunPod/vLLM)

## 1. Architecture Overview

We will upgrade `titan_os.py` to replace the mock execution logic with real LLM calls. The system will connect to a remote vLLM server running on RunPod.

### Infrastructure
- **Server**: RunPod GPU Instance (e.g., A100 or H100).
- **Software**: vLLM (serving OpenAI-compatible API).
- **Models**:
    - **Master Agent (Coordinator)**: High reasoning capability (e.g., `Qwen/Qwen2.5-72B-Instruct` or `meta-llama/Llama-3.1-70B-Instruct`).
    - **Sub Agents (Workers)**: High speed/efficiency (e.g., `Qwen/Qwen2.5-7B-Instruct` or `meta-llama/Llama-3.1-8B-Instruct`).
    - *Note*: The system will support configuring different model names, but you can point both to the same model if you only load one on vLLM.

### Data Flow
1.  **User** submits a complex task via Web UI.
2.  **Master Agent** (Coordinator) receives the task.
    - Calls vLLM with a "Planning Prompt".
    - Parses the response to create specific subtasks.
3.  **Agent Manager** assigns subtasks to specific Agents (Researcher, Executor, etc.).
4.  **Sub Agents** execute their assigned tasks.
    - Call vLLM with a "Role-Specific Prompt".
    - Return results to the shared memory.
5.  **Master Agent** synthesizes the final result (optional, or just aggregates).

## 2. Technical Changes

### A. Configuration Management
We will add environment variable support for flexible configuration.

**New Config Variables:**
- `TITAN_LLM_API_BASE`: URL of the vLLM server (e.g., `https://your-pod-id-8000.proxy.runpod.net/v1`)
- `TITAN_LLM_API_KEY`: API Key (usually "EMPTY" for vLLM unless configured otherwise).
- `TITAN_MASTER_MODEL`: Model name for the coordinator (e.g., `Qwen/Qwen2.5-72B-Instruct`).
- `TITAN_SUB_MODEL`: Model name for workers.

### B. New `TitanLLM` Class
A dedicated client to handle communication with the vLLM server.

```python
class TitanLLM:
    def __init__(self, base_url, api_key, model):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    async def chat(self, messages: List[Dict], temperature=0.7) -> str:
        # Wraps the OpenAI chat completion call
        pass
```

### C. Enhanced `Agent` Class
Update the `Agent` class to hold a reference to its specific LLM client (or model config).

### D. Refactored `AgentManager`
1.  **`assign_task`**:
    - Instead of round-robin, it will first use the **Coordinator Agent** to analyze the task.
    - If the task is simple, assign directly.
    - If complex, break it down (requires a structured output from the LLM).

2.  **`execute_task`** (New Method):
    - Replaces the `asyncio.sleep(0.1)` mock logic.
    - Constructs a prompt based on the Agent's `role` and the `task_description`.
    - Calls `TitanLLM.chat`.

## 3. Implementation Steps (Code Mode)

### Step 1: Setup & Dependencies
- Add `openai` (for the async client) and `python-dotenv` to `requirements.txt`.
- Create a `.env.example` file.

### Step 2: Implement `TitanLLM`
- Create the class in `titan_os.py`.
- Implement error handling (e.g., if RunPod is down).

### Step 3: Upgrade Agent Logic
- Modify `Agent` to accept an LLM client.
- Implement the "Planning Prompt" for the Coordinator.
    - *Prompt*: "You are the Coordinator. Break down this task into steps for the following agents: [List Agents]. Return JSON."
- Implement the "Execution Prompt" for other agents.
    - *Prompt*: "You are a {role}. Your goal is {goal}. Execute this task: {task}."

### Step 4: Integration
- Wire everything together in `AgentManager`.
- Update the `create_task` endpoint to trigger the new flow.

### Step 5: Testing
- Verify connection to the user's RunPod instance.
- Test a simple task ("What is 2+2?").
- Test a complex task ("Research quantum computing and write a summary").

## 4. Questions for User
- Do you already have the RunPod instance running? If so, what is the Base URL?
- Which specific models do you plan to load? (We need the exact model strings for the config).