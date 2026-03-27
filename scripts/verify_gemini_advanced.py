#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Gemini API Verification Script
=======================================
This script performs a deep-dive diagnosis of your Gemini API keys to resolve
"Unknown Error", "Quota Exceeded", and "Model Not Found" issues.

Features:
1.  **Dual SDK Testing**: Tests both `google-generativeai` (Legacy) and `google-genai` (New).
2.  **Model Scanning**: Probes multiple models to find active ones.
3.  **Latency Measurement**: Checks response time.
4.  **Error Classification**: Distinguishes between 404, 429, and 403.
5.  **Config Recommendation**: Suggests the optimal `config.yaml` settings.

Usage:
    python scripts/verify_gemini_advanced.py
"""

import logging
import os
import sys
import time
from typing import Any, Dict, List

import yaml

# Force UTF-8 for Windows console
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# --- Configuration ---
MODELS_TO_SCAN = [
    'gemini-3-flash',          # Target model
    'gemini-2.5-flash',        # Potential alternative
    'gemini-2.5-flash-lite',   # Higher RPM alternative
    'gemini-2.0-flash-exp',    # Experimental
    'gemini-1.5-flash',        # Fallback stable
    'gemini-1.5-pro'           # Legacy Pro
]

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("GeminiVerifier")

# --- SDK Check ---
HAS_LEGACY_SDK = False
HAS_NEW_SDK = False

try:
    import google.generativeai as genai_legacy
    HAS_LEGACY_SDK = True
    logger.info("[OK] Legacy SDK (google-generativeai) detected.")
except ImportError:
    logger.warning("[WARN] Legacy SDK not found.")

try:
    from google import genai as genai_new
    HAS_NEW_SDK = True
    logger.info("[OK] New SDK (google-genai) detected.")
except ImportError:
    logger.warning("[WARN] New SDK not found.")

# --- Test Functions ---

def test_key_legacy(api_key: str, model_name: str) -> Dict[str, Any]:
    """Test using the old `google-generativeai` SDK."""
    if not HAS_LEGACY_SDK:
        return {"status": "SKIPPED", "sdk": "Legacy", "error": "SDK Missing"}

    start_t = time.time()
    try:
        genai_legacy.configure(api_key=api_key)
        model = genai_legacy.GenerativeModel(model_name)
        
        # Minimal payload
        response = model.generate_content("Hello", request_options={"timeout": 10})
        
        latency = time.time() - start_t
        if response and response.text:
            return {
                "status": "OK",
                "sdk": "Legacy",
                "latency": latency,
                "model": model_name
            }
        else:
             return {"status": "EMPTY", "sdk": "Legacy", "latency": latency, "error": "Empty response"}

    except Exception as e:
        latency = time.time() - start_t
        err = str(e)
        status = "ERROR"
        if "404" in err or "not found" in err.lower():
            status = "NOT_FOUND"
        elif "429" in err or "quota" in err.lower() or "exhausted" in err.lower():
            status = "QUOTA"
        elif "403" in err or "permission" in err.lower() or "API_KEY_INVALID" in err:
            status = "AUTH_FAIL"
        
        return {"status": status, "sdk": "Legacy", "latency": latency, "error": err}

def test_key_new(api_key: str, model_name: str) -> Dict[str, Any]:
    """Test using the new `google-genai` SDK."""
    if not HAS_NEW_SDK:
        return {"status": "SKIPPED", "sdk": "New", "error": "SDK Missing"}

    start_t = time.time()
    try:
        # The new SDK client initialization
        client = genai_new.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model=model_name,
            contents="Hello"
        )
        
        latency = time.time() - start_t
        if response and response.text:
            return {
                "status": "OK",
                "sdk": "New",
                "latency": latency,
                "model": model_name
            }
        else:
            return {"status": "EMPTY", "sdk": "New", "latency": latency, "error": "Empty response"}

    except Exception as e:
        latency = time.time() - start_t
        err = str(e)
        status = "ERROR"
        if "404" in err or "not found" in err.lower():
            status = "NOT_FOUND"
        elif "429" in err or "quota" in err.lower() or "exhausted" in err.lower():
            status = "QUOTA"
        elif "403" in err or "permission" in err.lower():
            status = "AUTH_FAIL"
            
        return {"status": status, "sdk": "New", "latency": latency, "error": err}

def load_keys() -> List[str]:
    """Load keys from config.yaml"""
    config_path = os.path.join(os.getcwd(), 'config', 'config.yaml')
    if not os.path.exists(config_path):
        logger.error(f"Config not found at {config_path}")
        return []
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    raw_keys = config.get('api_keys', [])
    # Filter dummy keys
    valid_keys = [k for k in raw_keys if k and "YOUR_GOOGLE" not in k and len(k) > 20]
    return valid_keys

# --- Main Runner ---

def verify_single_key(index: int, key: str) -> Dict[str, Any]:
    """Scan a single key against models until one works or all fail."""
    masked = f"{key[:6]}...{key[-4:]}"
    results = {}
    
    print(f"\n[KEY] Key {index} ({masked}): Scanning models...")
    
    best_result = None
    
    for model in MODELS_TO_SCAN:
        print(f"   -> Testing {model}...", end="", flush=True)
        
        # Test New SDK
        res_new = test_key_new(key, model)
        print(f" [New: {res_new['status']}]", end="", flush=True)
        
        # Test Legacy SDK if New SDK didn't work perfectly
        res_legacy = {"status": "SKIPPED"}
        if res_new['status'] != 'OK':
             res_legacy = test_key_legacy(key, model)
             print(f" [Legacy: {res_legacy['status']}]", end="", flush=True)
        
        print("") # newline

        # Logic to pick a "winner"
        current_status = res_new['status'] if res_new['status'] != 'ERROR' else res_legacy.get('status', 'ERROR')
        
        if current_status == 'OK':
            best_result = {
                "key_idx": index,
                "masked": masked,
                "model": model,
                "status": "ALIVE",
                "latency": res_new.get('latency', 0) if res_new['status'] == 'OK' else res_legacy.get('latency', 0),
                "sdk_used": "New" if res_new['status'] == 'OK' else "Legacy"
            }
            break 
        
        if current_status == 'QUOTA':
            if best_result is None or best_result['status'] == 'DEAD':
                best_result = {
                    "key_idx": index,
                    "masked": masked,
                    "model": model,
                    "status": "QUOTA_LIMITED",
                    "latency": 0,
                    "sdk_used": "N/A"
                }
    
    if not best_result:
        best_result = {
            "key_idx": index,
            "masked": masked,
            "model": "NONE",
            "status": "DEAD",
            "latency": 0,
            "sdk_used": "N/A"
        }
        
    return best_result

def main():
    keys = load_keys()
    if not keys:
        logger.error("No keys found!")
        return

    logger.info(f"Loaded {len(keys)} keys. Starting scan...")
    
    final_report = []
    
    for i, key in enumerate(keys, 1):
        report = verify_single_key(i, key)
        final_report.append(report)
        time.sleep(1) 
        
    # --- Analysis & Report ---
    print("\n" + "="*70)
    print(f"{'KEY':<15} | {'STATUS':<15} | {'MODEL':<22} | {'LATENCY':<8}")
    print("-" * 70)
    
    working_keys = []
    quota_keys = []
    model_counts = {}
    
    for r in final_report:
        status_txt = "[OK]" if r['status'] == "ALIVE" else "[QUOTA]" if r['status'] == "QUOTA_LIMITED" else "[DEAD]"
        lat_str = f"{r['latency']:.2f}s" if r['latency'] > 0 else "-"
        print(f"{r['masked']:<15} | {status_txt:<15} | {r['model']:<22} | {lat_str}")
        
        if r['status'] == 'ALIVE':
            working_keys.append(r)
            m = r['model']
            model_counts[m] = model_counts.get(m, 0) + 1
        elif r['status'] == 'QUOTA_LIMITED':
            quota_keys.append(r)

    print("="*70)
    
    # --- Recommendations ---
    print("\n[INFO] CONFIGURATION RECOMMENDATIONS:")
    
    if working_keys:
        best_model = max(model_counts, key=model_counts.get)
        print(f"1. Recommended Model: '{best_model}' (Worked for {model_counts[best_model]} keys)")
        print(f"2. Working Keys: {len(working_keys)}/{len(keys)}")
        
        if "gemini-3" not in best_model and "gemini-3" in str(MODELS_TO_SCAN):
             print("   [WARN] 'gemini-3-flash' validation failed for most keys.")
             
        print("\n[INFO] Recommended config.yaml snippet:")
        print("models:")
        print(f"  default: \"{best_model}\"")
        print(f"  flash: \"{best_model}\"")
        print("  pro: \"gemini-1.5-pro\" # Fallback")
    else:
        print("[CRITICAL] No keys are currently working. Global Quota Exceeded or API Outage.")
        if quota_keys:
             print(f"   Found {len(quota_keys)} keys with Quota Exceeded. Wait for cooldown.")

if __name__ == "__main__":
    main()
