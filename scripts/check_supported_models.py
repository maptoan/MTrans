#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
import os
from pathlib import Path

# Thêm thư mục gốc vào path để import các module của project
sys.path.append(str(Path(__file__).parent.parent))

from src.services.genai_adapter import create_client

async def check_supported_models(api_key: str):
    print(f"Fetch all available models for API Key: {api_key[:10]}...{api_key[-5:]}")
    print("=" * 60)
    
    client = create_client(api_key=api_key, use_new_sdk=True)
    
    try:
        # Lấy danh sách model chính thức từ Google API
        print("Listing all models from Google API...")
        print("-" * 70)
        
        # Với new SDK: client.models.list()
        raw_client = client.client
        
        all_models = []
        if client.use_new_sdk and raw_client:
            models_iter = raw_client.models.list()
            for m in models_iter:
                all_models.append(m)
        else:
            # Fallback to old SDK if needed
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            for m in genai.list_models():
                all_models.append(m)
        
        print(f"{'Model Name':<45} | {'Supported Methods'}")
        print("-" * 80)
        for m in all_models:
            methods = ", ".join(m.supported_generation_methods) if hasattr(m, 'supported_generation_methods') else "N/A"
            # Chỉ hiển thị các model hỗ trợ generateContent
            if "generateContent" in methods or "generate_content" in methods.lower():
                name = m.name if hasattr(m, 'name') else str(m)
                print(f"{name:<45} | {methods}")
        
    except Exception as e:
        print(f"Error listing models: {e}")

    print("\n" + "=" * 60)
    print("Running availability test for key candidates...")
    print("=" * 60)
    
    candidate_models = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
    ]
    
    supported = []
    failed = []
    
    print(f"{'Model Name':<45} | {'Status':<10} | {'Note'}")
    print("-" * 70)
    
    for model in candidate_models:
        try:
            # Chờ để tránh Rate Limit của Free Tier khi test dồn dập
            await asyncio.sleep(2)
            
            # Thử gửi một request cực ngắn để check
            response = await client.generate_content_async(
                prompt="Hi",
                model_name=model
            )
            
            if response:
                print(f"{model:<45} | [OK ]     | Supported")
                supported.append(model)
            else:
                print(f"{model:<45} | [WAIT]    | Empty response")
        except Exception as e:
            err_msg = str(e).split('\n')[0] # First line of error
            print(f"{model:<45} | [FAIL]    | {err_msg[:40]}")
            failed.append((model, err_msg))
            
    print("=" * 60)
    print(f"Summary: {len(supported)} supported, {len(failed)} not supported.")
    if supported:
        print(f"Recommended models: {', '.join(supported)}")

if __name__ == "__main__":
    # Ưu tiên đọc từ biến môi trường để tránh hard-code secrets
    TEST_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    
    if len(sys.argv) > 1:
        TEST_KEY = sys.argv[1]

    if not TEST_KEY:
        print("Usage: python scripts/check_supported_models.py <API_KEY>")
        print("Hoặc set biến môi trường GEMINI_API_KEY.")
        sys.exit(1)
        
    asyncio.run(check_supported_models(TEST_KEY))
