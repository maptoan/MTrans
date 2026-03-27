import asyncio
import os
import sys

sys.path.append(os.getcwd())

from src.services.api_key_manager import APIKeyManager


async def test_rpd_limit():
    print("\n--- Testing RPD Hardcap Logic (Strict 20) ---")
    manager = APIKeyManager(["test_key_1"], config={"enable_quota_tracking": True})
    status = manager.key_statuses["test_key_1"]

    print(f"Default daily_quota_limit: {status.daily_quota_limit}")
    assert status.daily_quota_limit == 20, "RPD limit should be 20"

    status.daily_quota_used = 19
    print(f"Key status: {status.daily_quota_used}/{status.daily_quota_limit} used")
    assert manager._is_key_available(status) == True

    await manager.mark_request_success("test_key_1")
    print(f"After 1 success (reached 20): {status.daily_quota_used}/{status.daily_quota_limit} used")
    assert manager._is_key_available(status) == False
    print("✅ RPD Hardcap Verified!")

if __name__ == "__main__":
    asyncio.run(test_rpd_limit())
