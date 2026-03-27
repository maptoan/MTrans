#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct API test to diagnose connection issues.
Tests with gemini-2.5-flash and gemini-3-flash-preview models.
"""

import asyncio
import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_model(api_key: str, model_name: str, method: str = "rest"):
    """Test a specific model with a specific method."""
    print(f"\n=== Testing {model_name} via {method.upper()} ===")
    
    if method == "rest":
        try:
            import httpx
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            headers = {
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "contents": [
                    {"parts": [{"text": "Say 'Hello World' in Vietnamese. Just the translation, nothing else."}]}
                ]
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    print(f"✅ SUCCESS! Response: {text[:100]}")
                    return True
                else:
                    print(f"❌ ERROR: HTTP {response.status_code}")
                    error_text = response.text[:300]
                    print(f"   {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ FAILED: {type(e).__name__}: {e}")
            return False
    
    elif method == "new_sdk":
        try:
            from google import genai
            
            client = genai.Client(api_key=api_key, http_options={"timeout": 60})
            
            response = await client.aio.models.generate_content(
                model=model_name,
                contents="Say 'Hello World' in Vietnamese. Just the translation, nothing else."
            )
            
            if response.text:
                print(f"✅ SUCCESS! Response: {response.text[:100]}")
                return True
            else:
                print("⚠️ WARNING: Empty response")
                return False
                
        except Exception as e:
            print(f"❌ FAILED: {type(e).__name__}: {e}")
            return False
    
    elif method == "old_sdk":
        try:
            import google.generativeai as genai_old
            
            genai_old.configure(api_key=api_key)
            model = genai_old.GenerativeModel(model_name)
            
            response = await model.generate_content_async("Say 'Hello World' in Vietnamese. Just the translation, nothing else.")
            
            if response.text:
                print(f"✅ SUCCESS! Response: {response.text[:100]}")
                return True
            else:
                print("⚠️ WARNING: Empty response")
                return False
                
        except Exception as e:
            print(f"❌ FAILED: {type(e).__name__}: {e}")
            return False

async def test_direct_api():
    """Test direct API call without the application stack."""
    
    # Load a single API key from config
    import yaml
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    api_keys = config.get("api_keys", [])
    if not api_keys:
        print("ERROR: No API keys found in config")
        return
    
    api_key = api_keys[0]
    print(f"Testing with API key: {api_key[:15]}...")
    
    # Models to test
    models = ["gemini-2.5-flash", "gemini-3-flash-preview"]
    
    results = {}
    for model in models:
        # Test with REST API first (most reliable for error messages)
        result = await test_model(api_key, model, "rest")
        results[f"{model}_rest"] = result
        
        if result:
            # If REST works, also test SDKs
            results[f"{model}_new_sdk"] = await test_model(api_key, model, "new_sdk")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test}: {status}")

if __name__ == "__main__":
    asyncio.run(test_direct_api())
