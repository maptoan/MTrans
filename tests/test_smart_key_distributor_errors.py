from __future__ import annotations

from typing import Dict, List

import pytest

from src.services.smart_key_distributor import SmartKeyDistributor


class DummyError(Exception):
    pass


def _create_distributor(api_keys: List[str], config: Dict | None = None) -> SmartKeyDistributor:
    # num_chunks chỉ cần >0 để allocation hoạt động, không quan trọng giá trị chính xác
    return SmartKeyDistributor(api_keys, num_chunks=10, config=config or {})


@pytest.mark.asyncio
async def test_handle_exception_moves_key_to_correct_pool_quota():
    """Sau handle_exception + return_key, key bị block (trạng thái ở _state)."""
    dist = _create_distributor(["k1", "k2"])
    exc = DummyError("429 RESOURCE_EXHAUSTED: Quota exceeded for project")
    error_type = dist.handle_exception("k1", exc)
    assert error_type == "quota_exceeded"

    await dist.return_key(999, "k1", is_error=True, error_type=error_type, error_message=str(exc))
    assert dist.is_key_blocked("k1")


@pytest.mark.asyncio
async def test_handle_exception_marks_invalid_key():
    """Sau handle_exception + return_key với lỗi invalid, key bị deactivate và vào invalid_keys."""
    dist = _create_distributor(["k1"])
    exc = DummyError("403 PERMISSION_DENIED: invalid API key")
    error_type = dist.handle_exception("k1", exc)
    assert error_type == "invalid_key"

    await dist.return_key(999, "k1", is_error=True, error_type=error_type, error_message=str(exc))
    assert "k1" in dist.invalid_keys
    assert dist.key_statuses["k1"].is_active is False


@pytest.mark.asyncio
async def test_replace_worker_key_uses_reserve_after_error():
    # 1 key đang dùng, 1 key trong reserve
    api_keys = ["k1", "k2"]
    dist = _create_distributor(api_keys)

    # Giả lập: worker 1 đang dùng k1
    with dist._lock:
        dist.worker_keys[1] = "k1"
        # Cho k2 vào reserve để có thể thay thế
        dist.reserve_queue.put_nowait("k2")

    exc = DummyError("429 RESOURCE_EXHAUSTED: Quota exceeded for project")
    error_type = dist.handle_exception("k1", exc)

    # Thay key cho worker 1
    new_key = await dist.replace_worker_key(
        worker_id=1, failed_key="k1", error_type=error_type, error_message=str(exc)
    )

    # Key mới phải khác với failed_key và thuộc tập api_keys
    assert new_key is not None
    assert new_key != "k1"
    assert new_key in api_keys
    assert dist.worker_keys[1] == new_key
