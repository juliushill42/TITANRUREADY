import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI, APIConnectionError, APIStatusError

# DEBUG: Load .env from script directory explicitly
_script_dir = Path(__file__).parent
_env_path = _script_dir / ".env"
print(f"[DEBUG titan_llm] Script dir: {_script_dir}")
print(f"[DEBUG titan_llm] Looking for .env at: {_env_path}")
print(f"[DEBUG titan_llm] .env exists: {_env_path.exists()}")

if _env_path.exists():
    load_dotenv(_env_path)
    print(f"[DEBUG titan_llm] Loaded .env from {_env_path}")
else:
    load_dotenv()  # fallback to default behavior
    print("[DEBUG titan_llm] Using default load_dotenv()")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")

# Task A: Model Presets for Ollama
# Using phi3:mini for better performance on limited RAM
MODEL_PRESETS = {
    "FAST": "phi3:mini",
    "BALANCED": "phi3:mini",
    "QUALITY": "llama2",
}

# Ollama model configuration - default to phi3:mini for memory efficiency
MASTER_MODEL = os.getenv("MASTER_MODEL", "phi3:mini")
SUB_AGENT_MODEL = os.getenv("SUB_AGENT_MODEL", "phi3:mini")

# DEBUG: Print loaded model configuration
print(f"[DEBUG titan_llm] MASTER_MODEL = {MASTER_MODEL}")
print(f"[DEBUG titan_llm] SUB_AGENT_MODEL = {SUB_AGENT_MODEL}")
print(f"[DEBUG titan_llm] LLM_BASE_URL = {LLM_BASE_URL}")

client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

async def chat(system_prompt: str, user_prompt: str, model: str = MASTER_MODEL) -> str:
    # DEBUG: Log which model is being requested
    print(f"[DEBUG titan_llm.chat] Called with model parameter: '{model}'")
    print(f"[DEBUG titan_llm.chat] MASTER_MODEL constant: '{MASTER_MODEL}'")
    
    # Task C: Backend Stability - Retry logic (max 2 retries)
    max_retries = 2
    fallback_tried = False
    
    for attempt in range(max_retries + 1):
        current_model = model
        print(f"[DEBUG titan_llm.chat] Attempt {attempt+1}: Using model '{current_model}'")
        
        try:
            response = await client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
            
        except APIConnectionError:
            # Task C: User-friendly error message when LLM server is offline
            if attempt == max_retries:
                return "LLM server is not running. Start Ollama: ollama serve"
            
        except APIStatusError as e:
            error_msg = str(e).lower()
            
            # Task C: Detect missing model errors
            if e.status_code == 404 or "not found" in error_msg:
                 return "Model not available. Pull the model with: ollama pull llama2"
            
            # Task H: Memory Protection - try phi3:mini on ANY error if not already using it
            if current_model != "phi3:mini" and not fallback_tried:
                fallback_tried = True
                try:
                    response = await client.chat.completions.create(
                        model="phi3:mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.7,
                    )
                    return response.choices[0].message.content
                except Exception:
                    pass
            
            if attempt == max_retries:
                return f"Error: {str(e)}"
                
        except Exception as e:
            # Try fallback model on any exception if not already using it
            if current_model != "phi3:mini" and not fallback_tried:
                fallback_tried = True
                try:
                    response = await client.chat.completions.create(
                        model="phi3:mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.7,
                    )
                    return response.choices[0].message.content
                except Exception:
                    pass
            
            print(f"Error communicating with LLM: {e}")
            if attempt == max_retries:
                return f"Error: {str(e)}"
        
        # Short delay before retry
        await asyncio.sleep(1)

    return "Error: Maximum retries exceeded."