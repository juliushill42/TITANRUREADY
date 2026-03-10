import requests
import json
import time

def test_inference():
    print("Testing CPU inference with phi3:mini via Ollama...")
    url = "http://localhost:11434/v1/chat/completions"
    payload = {
        "model": "phi3:mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'CPU Inference Active' if you can hear me."}
        ],
        "temperature": 0.7
    }
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        end_time = time.time()
        
        content = data['choices'][0]['message']['content']
        print(f"\nResponse: {content}")
        print(f"Time taken: {end_time - start_time:.2f} seconds")
        
        if "CPU Inference Active" in content:
            print("\nSUCCESS: Model is responsive on CPU.")
        else:
            print("\nPARTIAL SUCCESS: Model responded but didn't follow the exact instruction.")
            
    except Exception as e:
        print(f"\nERROR: Could not connect to Ollama or model failed: {e}")
        print("Make sure Ollama is running locally.")

if __name__ == "__main__":
    test_inference()
