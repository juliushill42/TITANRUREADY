import asyncio
import os
from dotenv import load_dotenv
from titan_llm import chat, MASTER_MODEL

# Load environment variables
load_dotenv()

async def main():
    print("Testing LLM Connection...")
    
    llm_base_url = os.getenv("LLM_BASE_URL")
    print(f"LLM_BASE_URL: {llm_base_url}")
    print(f"MASTER_MODEL: {MASTER_MODEL}")
    
    print("\nSending request to LLM...")
    response = await chat(
        system_prompt="You are a helpful assistant.",
        user_prompt="Hello, are you working?",
        model=MASTER_MODEL
    )
    
    print("\nResponse from LLM:")
    print("-" * 20)
    print(response)
    print("-" * 20)

if __name__ == "__main__":
    asyncio.run(main())