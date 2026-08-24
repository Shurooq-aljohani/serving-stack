import requests
import json

BASE_URL = "http://localhost:8000"

def verify_stack():
    try:
        # 1. Check health
        health_res = requests.get(f"{BASE_URL}/health")
        if health_res.status_code != 200:
            print(f"GREEN CHECK: FAIL (Health endpoint returned status {health_res.status_code})")
            return

        # 2. Check models
        models_res = requests.get(f"{BASE_URL}/v1/models")
        if models_res.status_code != 200:
            print(f"GREEN CHECK: FAIL (Models endpoint returned status {models_res.status_code})")
            return
        
        models_data = models_res.json()
        if not models_data.get("data"):
            print("GREEN CHECK: FAIL (No models listed in /v1/models)")
            return

        # 3. Check chat completions
        payload = {
            "model": models_data["data"][0]["id"],
            "messages": [{"role": "user", "content": "Say one, two, three"}]
        }
        chat_res = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload)
        if chat_res.status_code != 200:
            print(f"GREEN CHECK: FAIL (Chat completions returned status {chat_res.status_code})")
            return
        
        chat_data = chat_res.json()
        choices = chat_data.get("choices", [])
        if not choices or not choices[0].get("message", {}).get("content"):
            print("GREEN CHECK: FAIL (Chat completion content is empty)")
            return

        print("GREEN CHECK: PASS")

    except Exception as e:
        print(f"GREEN CHECK: FAIL (Exception: {str(e)})")

if __name__ == "__main__":
    verify_stack()
