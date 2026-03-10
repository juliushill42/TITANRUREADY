# TitanU OS Prompt Architecture v1.0 Plan

## 1. Overview
The goal is to centralize and standardize prompt management in `titanu-os/backend`. Currently, prompts are scattered between `personality.py` and `prompts/core_brain.py`. The new architecture will use a **PromptLoader** class to handle dynamic loading, versioning, inheritance, and mode switching (Fast vs. Reasoning).

## 2. Directory Structure
We will create a new directory `titanu-os/backend/prompts/` to house the loader and prompt definitions. We will use **JSON** for prompt definitions to ensure standard library compatibility (no new dependencies) while separating data from code.

```text
titanu-os/backend/prompts/
├── __init__.py
├── loader.py                 # Core PromptLoader class implementation
└── definitions/              # JSON prompt definitions
    ├── core.json             # Main Titan system prompt (personality)
    ├── agents/
    │   ├── analyzer.json
    │   ├── executor.json
    │   ├── researcher.json
    │   └── optimizer.json
    └── common/               # Shared prompt fragments/mixins
        ├── safety.json
        └── identity.json
```

## 3. Prompt Definition Format (JSON)
Each prompt file will support inheritance and mode-specific overrides.

**Example `definitions/core.json`:**
```json
{
  "id": "core_titan",
  "version": "1.0",
  "base_prompt": "You are TITAN, a local AI operating system.",
  "modes": {
    "default": {
      "system": "{base_prompt} Be direct and concise."
    },
    "reasoning": {
      "system": "{base_prompt} Think step-by-step. Analyze constraints before answering."
    },
    "fast": {
      "system": "{base_prompt} Answer immediately. No fluff."
    }
  },
  "variables": ["memory_context"]
}
```

## 4. PromptLoader Class Design (`loader.py`)

### Responsibilities
1.  **Loading**: Read JSON files from `definitions/`.
2.  **Caching**: Cache loaded prompts to minimize disk I/O.
3.  **Inheritance**: Allow prompts to extend others (optional, for future expansion).
4.  **Mode Switching**: Select the correct text based on `mode` (default, reasoning, fast).
5.  **Formatting**: Inject dynamic variables (e.g., `memory_context`).

### Class Interface
```python
class PromptLoader:
    def __init__(self, prompts_dir: str):
        self.prompts_dir = prompts_dir
        self.cache = {}

    def get_prompt(self, prompt_id: str, mode: str = "default", **kwargs) -> str:
        """
        Retrieves a formatted prompt string.
        
        Args:
            prompt_id: The ID of the prompt (e.g., 'core', 'agents/analyzer')
            mode: 'default', 'fast', or 'reasoning'
            **kwargs: Variables to inject into the prompt (e.g., memory_context)
        """
        pass
    
    def _load_file(self, prompt_id: str) -> dict:
        """Internal method to load and parse JSON."""
        pass
```

## 5. Integration Plan

### Step 1: Create Structure
- Create `titanu-os/backend/prompts/` and subdirectories.
- Create `loader.py`.

### Step 2: Migrate Core Prompts
- Convert `TITAN_SYSTEM_PROMPT` from `titanu-os/backend/core/personality.py` into `titanu-os/backend/prompts/definitions/core.json`.
- Ensure personality traits and memory injection are preserved.

### Step 3: Migrate Agent Prompts
- Convert `AGENT_PROMPTS` from `prompts/core_brain.py` into individual JSON files in `titanu-os/backend/prompts/definitions/agents/`.

### Step 4: Integrate with Backend
- Modify `titanu-os/backend/core/personality.py` to use `PromptLoader` instead of hardcoded strings.
- Modify `titan_llm.py` or the agent handlers to request prompts via the loader.

### Step 5: Testing
- Create `titanu-os/backend/prompts/test_loader.py` to verify loading, mode switching, and formatting.

