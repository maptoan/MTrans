#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chẩn đoán API Key (New SDK Mode).
Mục đích: Test bằng thư viện `google-genai` (mới).
"""

import logging
import os
import sys
import time

import yaml
from google import genai
from google.genai import types

# Setup simple logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("NewSDKDiagnoser")

def test_key_new_sdk(api_key: str, index: int):
    """Test key bằng New SDK (google-genai)."""
    masked_key = f"{api_key[:8]}...{api_key[-4:]}"
    logger.info(f"🔍 Checking key {index}: {masked_key}")
    
    start_time = time.time()
    try:
        # Configure New SDK
        client = genai.Client(api_key=api_key)
        
        # Use gemini-2.0-flash (New Stable/Experimental model often used with new SDK)
        # Or stick to gemini-3-flash if that's the target.
        # Let's try gemini-2.0-flash first as it was working for some users on new SDK?
        # No, let's try gemini-2.0-flash-exp or similar if standard fails.
        # But wait, config has gemini-3-flash. Let's try that.
        target_model = 'gemini-3-flash' 
        
        # Generate generic text
        response = client.models.generate_content(
            model=target_model,
            contents="Hello"
        )
        
        duration = time.time() - start_time
        
        if response and response.text:
            logger.info(f"✅ Key {masked_key}: SUCCESS ({duration:.2f}s) - '{response.text.strip()[:20]}...'")
            return "SUCCESS"
        else:
            logger.warning(f"⚠️ Key {masked_key}: Empty response")
            return "EMPTY"
            
    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        
        if "429" in error_msg or "quota" in error_msg.lower() or "resource_exhausted" in error_msg.lower():
            logger.warning(f"⛔ Key {masked_key}: Quota Exceeded (429)")
            return "QUOTA_EXCEEDED"
        elif "not found" in error_msg.lower():
             logger.error(f"❌ Key {masked_key}: Model Not Found ({target_model})")
             return "MODEL_ERROR"
        else:
            logger.error(f"❌ Key {masked_key}: Error - {error_msg[:100]}")
            return "ERROR"

def run_diagnosis():
    # Load Config
    config_path = 'config/config.yaml'
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    api_keys = config.get('api_keys', [])
    valid_keys = [k for k in api_keys if k and "YOUR_GOOGLE_API_KEY" not in k]
    
    if not valid_keys:
        logger.error("No valid API keys found in config.")
        return

    logger.info(f"\n--- TESTING {len(valid_keys)} KEYS (NEW SDK: google-genai) ---")
    
    results = []
    for i, key in enumerate(valid_keys, 1):
        res = test_key_new_sdk(key, i)
        results.append(res)
        # Delay nhẹ
        time.sleep(2) 
        
    success_count = results.count("SUCCESS")
    logger.info("\n" + "=" * 40)
    logger.info(f"SUMMARY: {success_count}/{len(valid_keys)} keys working.")
    logger.info("=" * 40)

if __name__ == "__main__":
    run_diagnosis()
