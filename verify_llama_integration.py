import asyncio
import os
import sys

# Ensure backend core is in path
sys.path.append(os.path.join(os.getcwd(), "titanu-os", "backend"))

async def test_llama_integration():
    print("Testing Llama.cpp Integration...")
    
    # Import here after path setup
    from core.llm_client import llm_client
    from core.model_registry import get_model
    
    model_id = "lfm-2.5-1.2b"
    model_spec = get_model(model_id)
    
    if not model_spec:
        print(f"FAILED: Model {model_id} not found in registry")
        return

    print(f"Model Spec Found: {model_spec.name}")
    print(f"Provider: {model_spec.provider}")
    
    # Mock some environment variables if needed
    # os.environ["TITAN_LLAMA_CLI_PATH"] = "..."
    # os.environ["TITAN_LLAMA_MODEL_PATH"] = "..."
    
    system_prompt = "You are a helpful assistant."
    user_prompt = "Hello, who are you?"
    
    print(f"Sending request to model: {model_id}...")
    try:
        # This will attempt to run llama-cli.exe
        # It might fail if the exe doesn't exist, but we can verify the code path
        response = await llm_client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model_id
        )
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error during chat: {e}")

if __name__ == "__main__":
    asyncio.run(test_llama_integration())
