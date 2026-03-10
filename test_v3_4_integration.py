import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = str(Path(__file__).parent / "titanu-os" / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

async def test_v3_4_memory():
    print("--- TitanU v3.4 Memory Integration Test ---")
    
    try:
        from core.memory_v4 import memory_manager
        print("[1] MemoryManager imported successfully.")
    except ImportError as e:
        print(f"[FAIL] Could not import MemoryManager: {e}")
        return

    # 1. Log memories
    print("[2] Logging test memories...")
    memory_manager.log("The secret lab code is 4242.", tags=["security", "lab"])
    memory_manager.log("TitanU OS was launched on a Tuesday.", tags=["history"])
    memory_manager.log("My favorite color is deep space blue.", tags=["personal"])
    
    # 2. Test Deterministic Retrieval
    print("[3] Testing deterministic retrieval (recent first)...")
    recent = memory_manager.retrieve(limit=2, strategy="deterministic")
    for r in recent:
        print(f"  - {r['content']} (Strategy: {r.get('retrieval_strategy', 'none')})")

    # 3. Test Keyword/Semantic Fallback
    print("[4] Testing retrieval with query 'what is the lab code?'...")
    results = memory_manager.retrieve("what is the lab code?", limit=3, strategy="hybrid")
    found = False
    for r in results:
        print(f"  - Found: {r['content']} (Score indicator: {r.get('retrieval_strategy')})")
        if "4242" in r["content"]:
            found = True
    
    if found:
        print("[SUCCESS] RAG correctly retrieved relevant memory.")
    else:
        print("[FAIL] RAG failed to find relevant memory.")

    # 4. Test LLM Integration (Mocking)
    print("[5] Verifying LLM integration state...")
    try:
        import titan_llm
        if titan_llm.HAS_MEMORY_V4:
            print("[SUCCESS] titan_llm.py recognized MemoryManager v4.")
        else:
            print("[FAIL] titan_llm.py did not initialize MemoryManager.")
    except Exception as e:
        print(f"[ERROR] LLM integration check failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_v3_4_memory())
