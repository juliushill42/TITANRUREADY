
import json
import sys
import time

def send_chat_request():
    request = {
        "id": "test-missing-info",
        "type": "chat",
        "payload": {
            "model": "phi3:mini", 
            "message": {
                "role": "user",
                "content": "What is the secret code in the unmounted drive?"
            }
        }
    }
    
    print(json.dumps(request))
    sys.stdout.flush()

if __name__ == "__main__":
    send_chat_request()
