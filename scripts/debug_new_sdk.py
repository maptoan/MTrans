#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug New SDK to find why it times out immediately.
"""

import asyncio
import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

async def debug_new_sdk():
    """Debug New SDK to find root cause of TimeoutError."""
    
    import yaml
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    api_keys = config.get("api_keys", [])
    api_key = api_keys[0]
    print(f"Testing with API key: {api_key[:15]}...")
    
    from google import genai
    
    # Test 1: Default client
    print("\n=== TEST 1: Default Client (no http_options) ===")
    try:
        client = genai.Client(api_key=api_key)
        print(f"Client created: {type(client)}")
        
        response = await client.aio.models.generate_content(
            model="gemini-3-flash-preview",
            contents="Say 'hi'"
        )
        print(f"SUCCESS: {response.text[:50]}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: With explicit timeout (longer)
    print("\n=== TEST 2: With 120s timeout ===")
    try:
        client = genai.Client(api_key=api_key, http_options={"timeout": 120})
        print(f"Client created: {type(client)}")
        
        response = await client.aio.models.generate_content(
            model="gemini-3-flash-preview",
            contents="Say 'hi'"
        )
        print(f"SUCCESS: {response.text[:50]}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Synchronous call
    print("\n=== TEST 3: Synchronous call ===")
    try:
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents="Say 'hi'"
        )
        print(f"SUCCESS: {response.text[:50]}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_new_sdk())
