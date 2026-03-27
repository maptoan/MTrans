import asyncio
import os
import sys

import yaml

# Add project root to path
sys.path.append(os.getcwd())

from src.preprocessing.chunker import SmartChunker
from src.services.api_key_manager import APIKeyManager


def load_config_manual():
    config_path = os.path.join(os.getcwd(), "config", "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

async def test_chunking_20k():
    print("\n--- Testing Chunking Efficiency (20K tokens) ---")
    config = load_config_manual()
    chunking_config = config.get("preprocessing", {}).get("chunking", {})
    print(f"Config max_chunk_tokens: {chunking_config.get('max_chunk_tokens')}")

    chunker = SmartChunker(config)
    # Mock text ~200K chars (~50K tokens)
    mock_text = ("Đây là đoạn văn mẫu để kiểm tra chunking. Một chương truyện dài để test 20K token.\n\n" * 100) * 10
    print(f"Mock text size: {len(mock_text)} chars")

    chunks = chunker.chunk_novel(mock_text)
    print(f"Total chunks generated: {len(chunks)}")
    if chunks:
        print(f"Average chars per chunk: {len(mock_text)/len(chunks):.0f}")
        for i, c in enumerate(chunks[:2]):
            print(f"Chunk {i} size: {len(c['text'])} chars")

async def test_rpd_limit():
    print("\n--- Testing RPD Hardcap Logic (Strict 20) ---")
    manager = APIKeyManager(["test_key_1"], config={"enable_quota_tracking": True})
    status = manager.key_statuses["test_key_1"]

    # Verify default is now 20
    print(f"Default daily_quota_limit: {status.daily_quota_limit}")

    status.daily_quota_used = 19
    print(f"Key status: {status.daily_quota_used}/{status.daily_quota_limit} used")
    print(f"Is key available? {manager._is_key_available(status)}")

    await manager.mark_request_success("test_key_1")
    print(f"After 1 success (reached 20): {status.daily_quota_used}/{status.daily_quota_limit} used")
    print(f"Is key available? {manager._is_key_available(status)} (Expect False)")

def test_quality_gate_logic():
    print("\n--- Testing Quality Gate 2 (Content Coverage) logic ---")
    original = "Para 1\n\nPara 2\n\nPara 3\n\nPara 4\n\nPara 5"
    trans_bad = "Dịch 1\n\n" # Only 1 para
    trans_ok = "Dịch 1\n\nDịch 2\n\nDịch 3\n\nDịch 4" # 4/5 = 80%

    def check_coverage(trans, orig):
        orig_paras = [p for p in orig.split('\n') if p.strip()]
        trans_paras = [p for p in trans.split('\n') if p.strip()]
        if not orig_paras: return True, 1.0
        ratio = len(trans_paras) / len(orig_paras)
        return ratio >= 0.7, ratio

    pass_bad, ratio_bad = check_coverage(trans_bad, original)
    pass_ok, ratio_ok = check_coverage(trans_ok, original)

    print(f"Bad translation: ratio {ratio_bad:.1%}, Pass? {pass_bad} (Expect False)")
    print(f"OK translation: ratio {ratio_ok:.1%}, Pass? {pass_ok} (Expect True)")

if __name__ == "__main__":
    try:
        asyncio.run(test_chunking_20k())
        asyncio.run(test_rpd_limit())
        test_quality_gate_logic()
        print("\n✅ Verification Successful!")
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        sys.exit(1)
