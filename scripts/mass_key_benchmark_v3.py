import urllib.request
import json
import time
import sys
import os
from pathlib import Path

# Thêm thư mục gốc vào path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.helpers import load_config


def _load_api_keys() -> list[str]:
    env_keys = os.getenv("GEMINI_API_KEYS", "").strip()
    if env_keys:
        return [k.strip() for k in env_keys.split(",") if k.strip()]
    cfg = load_config("config/config.yaml")
    return cfg.get("api_keys", []) or []

MODELS = [
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-preview",
    "gemini-3.1-flash-lite-preview"
]

def test_key_direct(key, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": "Hi"}]}]}
    headers = {"Content-Type": "application/json"}
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    
    try:
        start_time = time.time()
        with urllib.request.urlopen(req, timeout=10) as response:
            elapsed = time.time() - start_time
            return "OK", f"{elapsed:.2f}s"
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read().decode()
        if code == 429: return "LIMIT_REACHED", "429 Quota Exhausted"
        if code == 503: return "UNAVAILABLE", "503 High Demand"
        if code == 404: return "NOT_FOUND", "404 Model Unsupported"
        return "HTTP_ERROR", f"{code}: {body[:50]}"
    except Exception as e:
        return "GENERAL_ERROR", str(e)[:50]

def mass_benchmark_v3():
    api_keys = _load_api_keys()
    if not api_keys:
        print("❌ Không tìm thấy API keys. Set GEMINI_API_KEYS hoặc cấu hình local config/config.yaml.")
        return

    print(f"{'Key (Mask)':<20} | {'Model':<25} | {'Status':<15} | {'Detail'}")
    print("-" * 80)
    
    for key in api_keys:
        masked = f"{key[:8]}...{key[-5:]}"
        for model in MODELS:
            # Short sleep to avoid being flagged as spam by the firewall
            time.sleep(0.5)
            status, detail = test_key_direct(key, model)
            print(f"{masked:<20} | {model:<25} | {status:<15} | {detail}")
            sys.stdout.flush()

if __name__ == "__main__":
    mass_benchmark_v3()
