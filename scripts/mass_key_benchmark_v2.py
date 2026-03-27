#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
import time
import json
from pathlib import Path

# Thêm thư mục gốc vào path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.genai_adapter import create_client
from src.utils.helpers import load_config
from src.utils.path_manager import resolve_path


def _load_api_keys() -> list[str]:
    env_keys = os.getenv("GEMINI_API_KEYS", "").strip()
    if env_keys:
        return [k.strip() for k in env_keys.split(",") if k.strip()]
    cfg = load_config(str(resolve_path("config/config.yaml", "config/config.yaml")))
    return cfg.get("api_keys", []) or []

# Tập trung vào Gemini 3+
MODELS = ["gemini-3-flash-preview", "gemini-3-pro-preview"]

async def test_key(key, model):
    # Disable internal retries as much as possible by using a low timeout
    # Or just catching the exception immediately
    client = create_client(api_key=key, use_new_sdk=True)
    try:
        # Use a very simple prompt
        response = await asyncio.wait_for(
            client.generate_content_async(prompt="1", model_name=model),
            timeout=15 # Don't wait too long
        )
        return "OK", None
    except asyncio.TimeoutError:
        return "TIMEOUT", "Request took too long"
    except Exception as e:
        err = str(e).lower()
        if "429" in err: return "RPD_OR_RPM_LIMIT", "429 Exhausted"
        if "503" in err: return "SERVICE_UNAVAILABLE", "503 High Demand"
        if "404" in err: return "NOT_FOUND", "404 Unsupported"
        return "ERROR", err[:50]

async def mass_benchmark():
    api_keys = _load_api_keys()
    if not api_keys:
        print("❌ Không tìm thấy API keys. Set GEMINI_API_KEYS hoặc cấu hình local config/config.yaml.")
        return

    results = []
    print(f"{'Key (Mask)':<20} | {'Model':<25} | {'Status':<15} | {'Detail'}")
    print("-" * 80)
    
    for key in api_keys:
        masked = f"{key[:8]}...{key[-5:]}"
        for model in MODELS:
            # Respectful delay to avoid IP-based blocking
            await asyncio.sleep(1)
            status, detail = await test_key(key, model)
            print(f"{masked:<20} | {model:<25} | {status:<15} | {detail or ''}")
            results.append({"key": masked, "model": model, "status": status, "detail": detail})
    
    # Save results
    report_path = resolve_path("data/reports/mass_key_benchmark.json", "data/reports/mass_key_benchmark.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(mass_benchmark())
