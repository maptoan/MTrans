# -*- coding: utf-8 -*-
"""
Tests cho APIKeyManager: RPD-block (quota/ngày), get_quota_status_summary, handle_exception.
TDD: hợp nhất trạng thái key và xử lý RPD-block chuẩn.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.services.api_key_manager import APIKeyManager, APIKeyStatus


@pytest.fixture
def manager_two_keys():
    """APIKeyManager với 2 keys, bật quota tracking."""
    return APIKeyManager(
        ["KEY_A", "KEY_B"],
        config={"enable_quota_tracking": True},
    )


@pytest.fixture
def manager_one_key():
    return APIKeyManager(
        ["KEY_A"],
        config={"enable_quota_tracking": True},
    )


# --- RPD-block (rpd_blocked_until) ---


@pytest.mark.asyncio
async def test_mark_request_error_sets_rpd_block_for_billing_quota(manager_one_key):
    """Khi lỗi 'quota... plan and billing' thì set rpd_blocked_until sang ngày hôm sau."""
    msg = "You exceeded your current quota, please check your plan and billing details."
    key = "KEY_A"

    await manager_one_key.mark_request_error(key, "quota_exceeded", msg)

    status = manager_one_key.key_statuses[key]
    assert getattr(status, "rpd_blocked_until", None) is not None
    assert status.rpd_blocked_until.date() >= datetime.now().date()


def test_is_key_available_respects_rpd_block(manager_one_key):
    """_is_key_available (qua is_key_blocked) phải return False khi key bị RPD-block."""
    key = "KEY_A"
    status = manager_one_key.key_statuses[key]
    status.rpd_blocked_until = datetime.now() + timedelta(hours=12)

    assert manager_one_key._is_key_available(status) is False
    assert manager_one_key.is_key_blocked(key) is True


def test_get_active_key_count_excludes_rpd_blocked(manager_two_keys):
    """get_active_key_count không đếm key đang rpd_blocked_until."""
    a = manager_two_keys.key_statuses["KEY_A"]
    b = manager_two_keys.key_statuses["KEY_B"]
    a.rpd_blocked_until = datetime.now() + timedelta(hours=12)
    b.rpd_blocked_until = None

    assert manager_two_keys.get_active_key_count() == 1


@pytest.mark.asyncio
async def test_wait_for_available_key_skips_rpd_blocked(manager_two_keys):
    """wait_for_available_key trả về key không bị RPD-block."""
    a = manager_two_keys.key_statuses["KEY_A"]
    b = manager_two_keys.key_statuses["KEY_B"]
    a.rpd_blocked_until = datetime.now() + timedelta(hours=12)
    b.rpd_blocked_until = None

    key = await manager_two_keys.wait_for_available_key(timeout=2)
    assert key == "KEY_B"


@pytest.mark.asyncio
async def test_all_keys_rpd_blocked_get_active_zero(manager_two_keys):
    """Khi tất cả keys đều rpd_blocked thì get_active_key_count == 0."""
    for status in manager_two_keys.key_statuses.values():
        status.rpd_blocked_until = datetime.now() + timedelta(hours=12)

    assert manager_two_keys.get_active_key_count() == 0

    key = await manager_two_keys.wait_for_available_key(timeout=1)
    assert key is None


# --- get_quota_status_summary ---


def test_get_quota_status_summary_shape(manager_two_keys):
    """get_quota_status_summary trả về dict có đủ key translator cần."""
    summary = manager_two_keys.get_quota_status_summary()

    assert "quota_blocked_ratio" in summary
    assert "available_keys" in summary
    assert "total_keys" in summary
    assert "quota_blocked_keys" in summary
    assert "earliest_reset_time" in summary
    assert summary["total_keys"] == 2


# --- handle_exception ---


@pytest.mark.asyncio
async def test_handle_exception_classifies_then_return_key_marks(manager_one_key):
    """handle_exception phân loại; return_key(is_error=True) mới cập nhật trạng thái key."""
    class QuotaError(Exception):
        pass

    exc = QuotaError("429 RESOURCE_EXHAUSTED: You exceeded your current quota, please check your plan and billing.")
    error_type = manager_one_key.handle_exception("KEY_A", exc)
    assert error_type == "quota_exceeded"

    await manager_one_key.return_key(
        999, "KEY_A", is_error=True, error_type=error_type, error_message=str(exc)
    )
    assert manager_one_key.is_key_blocked("KEY_A") is True
