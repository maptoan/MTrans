#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.genai_adapter import create_client

async def test_rpm(client, model, target_count=20):
    """Test Requests Per Minute limit"""
    print(f"\n--- Testing RPM limit for {model} ---")
    start_time = time.time()
    success_count = 0
    errors = []
    
    tasks = []
    for i in range(target_count):
        tasks.append(client.generate_content_async(prompt="Say '1'", model_name=model))
    
    # Send all at once to see where it breaks
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for r in results:
        if isinstance(r, Exception):
            errors.append(str(r))
        else:
            success_count += 1
            
    elapsed = time.time() - start_time
    print(f"Results: {success_count}/{target_count} succeeded in {elapsed:.2f}s")
    if errors:
        print(f"First error: {errors[0][:100]}")
    
    return success_count, elapsed

async def test_tpm(client, model):
    """Test Tokens Per Minute limit (approximation)"""
    print(f"\n--- Testing TPM limit for {model} ---")
    # Generates a prompt with roughly 10k tokens (repeating words)
    large_prompt = "Translate this word: Apple. " * 5000 
    
    try:
        start_time = time.time()
        response = await client.generate_content_async(prompt=large_prompt, model_name=model)
        elapsed = time.time() - start_time
        print(f"TPM Test (Small Batch ~10k tokens): OK in {elapsed:.2f}s")
        return True
    except Exception as e:
        print(f"TPM Test Failed: {str(e)[:100]}")
        return False

async def benchmark_key(api_key):
    print(f"Benckmarking Technical Limits for Key: {api_key[:10]}...{api_key[-5:]}")
    print("=" * 80)
    
    client = create_client(api_key=api_key, use_new_sdk=True)
    
    # Test RPM for Flash (Target 15)
    flash_rpm, flash_time = await test_rpm(client, "gemini-2.5-flash", 20)
    
    # Wait to reset quota
    print("Waiting 60s to reset quota...")
    await asyncio.sleep(60)
    
    # Test RPM for Gemini 3 (Target 15)
    g3_rpm, g3_time = await test_rpm(client, "gemini-3-flash-preview", 20)
    
    print("\n" + "=" * 80)
    print("TECHNICAL LIMIT REPORT")
    print("-" * 80)
    print(f"{'Model':<25} | {'Effective RPM':<15} | {'Behavior'}")
    print("-" * 80)
    print(f"{'Gemini 2.5 Flash':<25} | {flash_rpm:<15} | {'Standard Free Tier' if flash_rpm >= 10 else 'Restricted'}")
    print(f"{'Gemini 3 Flash Preview':<25} | {g3_rpm:<15} | {'Standard Free Tier' if g3_rpm >= 10 else 'Restricted'}")
    print("-" * 80)
    print("Note: Requests Per Day (RPD) cannot be tested quickly without depletion.")
    print("=" * 80)

if __name__ == "__main__":
    # Ưu tiên đọc từ biến môi trường để tránh hard-code secrets
    NEW_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    
    if len(sys.argv) > 1:
        NEW_KEY = sys.argv[1]

    if not NEW_KEY:
        print("Usage: python scripts/benchmark_key_limits.py <API_KEY>")
        print("Hoặc set biến môi trường GEMINI_API_KEY.")
        sys.exit(1)
        
    asyncio.run(benchmark_key(NEW_KEY))
