import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.services.smart_key_distributor import SmartKeyDistributor

# Configure mock config (flat structure as passed by initialization_service)
mock_config = {
    'ratios': {'translation': 0.7, 'editor': 0.2, 'reserve': 0.1},
    'cooldowns': {'rate_limit': 1, 'quota_exceeded': 2, 'server_error': 1},
    'rpd_cooldown_hours': 1,
    'key_rotation_mode': 'zero_wait'
}

async def test_allocation():
    print("\n--- Test 1: Allocation ---")
    keys = [f"key_{i}" for i in range(10)]
    distributor = SmartKeyDistributor(keys, num_chunks=100, config=mock_config)

    # Force allocation (usually done in init or update_allocation)
    # update_allocation calls _calculate_optimal_workers
    await distributor.update_allocation(100)

    counts = distributor.get_key_distribution_status()
    print(f"Distribution: {counts}")

    # 10 keys -> 7 trans, 2 editor, 1 reserve
    assert counts['translation'] == 7, f"Expected 7 translation keys, got {counts['translation']}"
    assert counts['editor'] == 2, f"Expected 2 editor keys, got {counts['editor']}"
    assert counts['reserve'] == 1, f"Expected 1 reserve key, got {counts['reserve']}"
    print("✅ Allocation Correct")

async def test_replacement():
    print("\n--- Test 2: Replacement ---")
    keys = ["key_A", "key_B", "key_C", "key_D", "key_E"]
    # 5 keys: 70% of 5 = 3.5 -> 3 trans? 20% -> 1 editor? 10% -> 0.5 -> 1 reserve?
    # Let's see actual math in SmartKeyDistributor

    distributor = SmartKeyDistributor(keys, num_chunks=100, config=mock_config)
    await distributor.update_allocation(100)

    counts = distributor.get_key_distribution_status()
    print(f"Distribution: {counts}")

    # Get key for worker 1 (Translation)
    key = distributor.get_key_for_worker(1)
    print(f"Worker 1 key: {key}")

    if key is None:
        print("❌ Failed to get key for worker 1")
        return

    # Report error
    print("Reporting 429 error...")
    # This moves key to pool (mark_request_error is sync)
    distributor.mark_request_error(key, "rate_limit", "429 Too Many Requests")

    # Replace (robust async check)
    res = distributor.replace_worker_key(1, key, "rate_limit")
    if asyncio.iscoroutine(res):
        new_key = await res
    else:
        new_key = res
    print(f"New key: {new_key}")

    assert new_key != key, "New key should be different"
    assert new_key is not None, "New key should not be None"

    # Verify worker map updated
    current_worker_key = distributor.get_key_for_worker(1)
    assert current_worker_key == new_key, "Worker key mapping not updated"

    print("✅ Replacement Correct")

async def main():
    await test_allocation()
    await test_replacement()

if __name__ == "__main__":
    asyncio.run(main())
