#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
import time
from pathlib import Path

# Thêm thư mục gốc vào path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.genai_adapter import create_client
from src.utils.helpers import load_config


def _load_api_keys() -> list[str]:
    """
    Ưu tiên ENV để tránh hard-code secrets trong repo.
    - GEMINI_API_KEYS="key1,key2,key3"
    Fallback: đọc từ config/config.yaml local.
    """
    env_keys = os.getenv("GEMINI_API_KEYS", "").strip()
    if env_keys:
        return [k.strip() for k in env_keys.split(",") if k.strip()]
    cfg = load_config("config/config.yaml")
    return cfg.get("api_keys", []) or []

# Danh sách các model đời mới cần test
MODELS_TO_TEST = [
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview"
]

async def test_key_availability(key, model):
    """Kiểm tra một model cụ thể có sẵn và còn quota không."""
    client = create_client(api_key=key, use_new_sdk=True)
    try:
        # Gửi prompt cực ngắn để check nhanh
        start_time = time.time()
        response = await client.generate_content_async(prompt="Hi", model_name=model)
        elapsed = time.time() - start_time
        return {
            "status": "OK",
            "time": elapsed,
            "error": None
        }
    except Exception as e:
        err_msg = str(e)
        status = "FAILED"
        if "429" in err_msg:
            status = "LIMIT_REACHED"
        elif "404" in err_msg:
            status = "NOT_FOUND"
        elif "invalid" in err_msg.lower():
            status = "INVALID_KEY"
            
        return {
            "status": status,
            "time": 0,
            "error": err_msg.split('\n')[0][:50]
        }

async def benchmark_mass_keys():
    api_keys = _load_api_keys()
    if not api_keys:
        print("❌ Không tìm thấy API keys. Set GEMINI_API_KEYS hoặc cấu hình local config/config.yaml.")
        return

    print("🚀 MASS KEY BENCHMARKING - FOCUS: GEMINI 3/3.1")
    print("=" * 100)
    print(f"{'API Key (Masked)':<20} | {'Model':<30} | {'Status':<15} | {'Note'}")
    print("-" * 100)
    
    results = []
    
    for key in api_keys:
        masked_key = f"{key[:8]}...{key[-5:]}"
        
        for model in MODELS_TO_TEST:
            # Tối ưu hóa timing: Chờ 2s giữa mỗi lần test để tránh kích hoạt RPM limit
            # Của các key dùng chung IP (nếu có)
            await asyncio.sleep(2)
            
            res = await test_key_availability(key, model)
            print(f"{masked_key:<20} | {model:<30} | {res['status']:<15} | {res['error'] or 'Active'}")
            
            results.append({
                "key": masked_key,
                "model": model,
                "status": res['status']
            })
        
        print("-" * 100)
        # Chờ 5s sau khi test xong 1 key để reset quota burst
        await asyncio.sleep(5)

    # Tổng kết
    print("\n📊 TỔNG KẾT BENCHMARK")
    print("=" * 60)
    for model in MODELS_TO_TEST:
        success = sum(1 for r in results if r['model'] == model and r['status'] == "OK")
        limits = sum(1 for r in results if r['model'] == model and r['status'] == "LIMIT_REACHED")
        print(f"{model:<30}: {success} Hoạt động, {limits} Hết quota/Bị giới hạn")

if __name__ == "__main__":
    asyncio.run(benchmark_mass_keys())
