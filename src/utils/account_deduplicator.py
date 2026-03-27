# -*- coding: utf-8 -*-

"""
Account Deduplicator - Lọc tự động các API keys thuộc cùng tài khoản.

Tính năng:
- Detect các keys thuộc cùng 1 tài khoản Google Cloud
- Chỉ giữ lại 1 key/tài khoản (deduplicate)
- Sử dụng nhiều phương pháp để detect: quota sharing, response patterns, error patterns
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from .api_key_validator import APIKeyStatus, GeminiAPIChecker

logger = logging.getLogger("NovelTranslator")


class AccountDeduplicator:
    """
    Class để detect và deduplicate các API keys thuộc cùng tài khoản.
    """

    def __init__(self, api_keys: List[str], config: Dict[str, Any]):
        """
        Khởi tạo Account Deduplicator.

        Args:
            api_keys: Danh sách các API keys
            config: Configuration dictionary
        """
        self.api_keys = api_keys
        self.config = config
        self.checker = GeminiAPIChecker(api_keys, config)

    def detect_account_groups(
        self, test_results: Optional[List[APIKeyStatus]] = None
    ) -> Dict[str, List[str]]:
        """
        Detect các keys thuộc cùng tài khoản dựa trên test results.

        Phương pháp:
        1. Account type matching: Keys có cùng account_type → có thể cùng tài khoản
        2. Quota sharing detection: Keys cùng hết quota cùng lúc → cùng tài khoản
        3. Response pattern matching: Keys có similar response times → có thể cùng tài khoản
        4. Error pattern matching: Keys có cùng error patterns → có thể cùng tài khoản

        Args:
            test_results: Kết quả test từ GeminiAPIChecker (optional, sẽ test nếu None)

        Returns:
            Dictionary: {account_id: [list of keys]}
            account_id là "account_0", "account_1", etc.
        """
        if test_results is None:
            logger.info("🔍 Đang test các keys để detect account groups...")
            test_results = self.checker.run_checks()

        # Group 0: Keys có cùng account_type (quan trọng nhất)
        account_type_groups = self._group_by_account_type(test_results)

        # Group 1: Keys có cùng quota error pattern
        quota_groups = self._group_by_quota_pattern(test_results)

        # Group 2: Keys có cùng response pattern
        response_groups = self._group_by_response_pattern(test_results)

        # Group 3: Keys có cùng error pattern
        error_groups = self._group_by_error_pattern(test_results)

        # Merge các groups (ưu tiên account_type_groups)
        account_groups = self._merge_groups(
            account_type_groups, quota_groups, response_groups, error_groups
        )

        return account_groups

    def _group_by_account_type(
        self, test_results: List[APIKeyStatus]
    ) -> Dict[str, List[str]]:
        """
        Group keys theo account_type.

        Logic:
        - Keys có cùng account_type → có thể cùng tài khoản
        - Đây là phương pháp chính xác nhất vì account_type được detect từ API response
        """
        groups: Dict[str, List[str]] = defaultdict(list)

        for result in test_results:
            account_type = result.account_type
            if account_type and account_type != "unknown":
                groups[account_type].append(result.full_key)

        return dict(groups)

    def _group_by_quota_pattern(
        self, test_results: List[APIKeyStatus]
    ) -> Dict[str, List[str]]:
        """
        Group keys theo quota error pattern.

        Logic:
        - Keys có cùng error message về quota → có thể cùng tài khoản
        - Keys có cùng quota status → có thể cùng tài khoản
        """
        groups: Dict[str, List[str]] = defaultdict(list)

        for result in test_results:
            if not result.is_valid and result.error_message:
                error_msg = result.error_message.lower()

                # Extract quota info từ error message
                if "quota" in error_msg or "429" in error_msg:
                    # Tạo key từ error pattern
                    # Keys có cùng error pattern → có thể cùng tài khoản
                    pattern_key = self._extract_quota_pattern(error_msg)
                    groups[pattern_key].append(result.full_key)

        return dict(groups)

    def _group_by_response_pattern(
        self, test_results: List[APIKeyStatus]
    ) -> Dict[str, List[str]]:
        """
        Group keys theo response pattern (response time, success rate).

        Logic:
        - Keys từ cùng tài khoản có thể có similar response times
        - Group keys có response time tương tự nhau
        """
        groups: Dict[str, List[str]] = defaultdict(list)

        # Group valid keys theo response time ranges
        valid_results = [r for r in test_results if r.is_valid and r.response_time]

        if not valid_results:
            return {}

        # Tính response time ranges
        response_times = [r.response_time for r in valid_results if r.response_time]
        if not response_times:
            return {}

        avg_response_time = sum(response_times) / len(response_times)

        # Group keys có response time tương tự (trong khoảng ±20% của average)
        for result in valid_results:
            if result.response_time:
                # Normalize response time vào buckets
                bucket = self._bucket_response_time(
                    result.response_time, avg_response_time
                )
                groups[bucket].append(result.full_key)

        return dict(groups)

    def _group_by_error_pattern(
        self, test_results: List[APIKeyStatus]
    ) -> Dict[str, List[str]]:
        """
        Group keys theo error pattern.

        Logic:
        - Keys từ cùng tài khoản có thể có cùng error patterns
        - Ví dụ: cùng "billing required", cùng "access denied", etc.
        """
        groups: Dict[str, List[str]] = defaultdict(list)

        for result in test_results:
            if not result.is_valid and result.error_message:
                error_msg = result.error_message.lower()

                # Extract error type
                error_type = self._extract_error_type(error_msg)
                groups[error_type].append(result.full_key)

        return dict(groups)

    def _extract_quota_pattern(self, error_msg: str) -> str:
        """Extract quota pattern từ error message."""
        # Normalize error message để tạo pattern key
        if "billing" in error_msg or "payment" in error_msg:
            return "quota_billing_required"
        elif "429" in error_msg or "resource exhausted" in error_msg:
            return "quota_exceeded"
        elif "rate limit" in error_msg:
            return "quota_rate_limit"
        else:
            return "quota_unknown"

    def _bucket_response_time(self, response_time: float, avg_time: float) -> str:
        """Bucket response time vào ranges."""
        if response_time < avg_time * 0.8:
            return "response_fast"
        elif response_time < avg_time * 1.2:
            return "response_normal"
        else:
            return "response_slow"

    def _extract_error_type(self, error_msg: str) -> str:
        """Extract error type từ error message."""
        error_msg_lower = error_msg.lower()

        if "billing" in error_msg_lower or "payment" in error_msg_lower:
            return "error_billing"
        elif "access denied" in error_msg_lower or "permission" in error_msg_lower:
            return "error_permission"
        elif "invalid" in error_msg_lower:
            return "error_invalid"
        elif "quota" in error_msg_lower or "429" in error_msg_lower:
            return "error_quota"
        else:
            return "error_unknown"

    def _merge_groups(self, *group_dicts: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Merge các groups lại thành account groups.

        WARNING: Logic này có thể không chính xác vì không thể detect chính xác keys nào thuộc cùng tài khoản.
        Chỉ merge khi có nhiều indicators cùng lúc (conservative approach).

        Logic:
        - Chỉ merge keys nếu chúng xuất hiện trong NHIỀU groups cùng lúc (≥2 groups)
        - Điều này giảm false positives nhưng vẫn có thể có false negatives
        """
        # Tạo graph: key -> set of group_ids
        key_to_groups: Dict[str, Set[str]] = defaultdict(set)

        for group_dict in group_dicts:
            for group_id, keys in group_dict.items():
                for key in keys:
                    key_to_groups[key].add(group_id)

        # CONSERVATIVE: Chỉ merge keys nếu chúng có ≥2 shared groups
        # Điều này giảm false positives (nhóm nhầm keys từ tài khoản khác nhau)
        min_shared_groups = 2

        # Tìm connected components (keys có nhiều shared groups)
        visited: Set[str] = set()
        account_groups: Dict[str, List[str]] = {}
        account_counter = 0

        for key in self.api_keys:
            if key in visited:
                continue

            # Tìm keys có nhiều shared groups với key này
            account_keys = self._find_connected_keys_conservative(
                key, key_to_groups, visited, min_shared_groups
            )

            if len(account_keys) > 1:  # Chỉ tạo group nếu có >1 key
                account_id = f"account_{account_counter}"
                account_groups[account_id] = account_keys
                account_counter += 1
                visited.update(account_keys)
            else:
                # Key đơn lẻ (không có keys khác có nhiều shared groups)
                # → Có thể là tài khoản riêng, giữ lại
                visited.add(key)

        return account_groups

    def _find_connected_keys(
        self, start_key: str, key_to_groups: Dict[str, Set[str]], visited: Set[str]
    ) -> List[str]:
        """Tìm tất cả keys connected với start_key qua shared groups."""
        connected = [start_key]
        queue = [start_key]
        visited_local = {start_key}

        while queue:
            current_key = queue.pop(0)
            current_groups = key_to_groups.get(current_key, set())

            # Tìm keys có shared groups
            for other_key in self.api_keys:
                if other_key in visited_local or other_key in visited:
                    continue

                other_groups = key_to_groups.get(other_key, set())

                # Nếu có shared groups → cùng tài khoản
                if current_groups & other_groups:  # Intersection
                    connected.append(other_key)
                    queue.append(other_key)
                    visited_local.add(other_key)

        return connected

    def _find_connected_keys_conservative(
        self,
        start_key: str,
        key_to_groups: Dict[str, Set[str]],
        visited: Set[str],
        min_shared_groups: int = 2,
    ) -> List[str]:
        """
        Tìm keys connected với start_key qua NHIỀU shared groups (conservative).

        Chỉ merge keys nếu chúng có ≥min_shared_groups groups chung.
        Điều này giảm false positives (nhóm nhầm keys từ tài khoản khác nhau).
        """
        connected = [start_key]
        queue = [start_key]
        visited_local = {start_key}
        key_to_groups.get(start_key, set())

        while queue:
            current_key = queue.pop(0)
            current_groups = key_to_groups.get(current_key, set())

            # Tìm keys có NHIỀU shared groups
            for other_key in self.api_keys:
                if other_key in visited_local or other_key in visited:
                    continue

                other_groups = key_to_groups.get(other_key, set())
                shared_groups = current_groups & other_groups  # Intersection

                # Chỉ merge nếu có ≥min_shared_groups groups chung
                if len(shared_groups) >= min_shared_groups:
                    connected.append(other_key)
                    queue.append(other_key)
                    visited_local.add(other_key)

        return connected

    def deduplicate(self, strategy: str = "first") -> Tuple[List[str], Dict[str, Any]]:
        """
        Deduplicate keys: chỉ giữ lại 1 key/tài khoản.

        Args:
            strategy: Strategy để chọn key từ mỗi account
                - "first": Chọn key đầu tiên trong group
                - "fastest": Chọn key có response time nhanh nhất
                - "most_reliable": Chọn key có success rate cao nhất

        Returns:
            Tuple:
                - List các keys đã deduplicate
                - Dictionary với thông tin về deduplication
        """
        logger.info(f"🔄 Bắt đầu deduplicate {len(self.api_keys)} keys...")

        # Detect account groups
        account_groups = self.detect_account_groups()

        # Chọn 1 key từ mỗi account
        selected_keys: List[str] = []
        dedup_info: Dict[str, Any] = {
            "original_count": len(self.api_keys),
            "account_groups": {},
            "removed_keys": [],
        }

        test_results = self.checker.run_checks()
        result_map = {r.full_key: r for r in test_results}

        for account_id, keys in account_groups.items():
            if not keys:
                continue

            # Chọn key theo strategy
            selected_key = self._select_key(keys, result_map, strategy)
            selected_keys.append(selected_key)

            # Lưu thông tin
            dedup_info["account_groups"][account_id] = {
                "keys": keys,
                "selected": selected_key,
                "removed": [k for k in keys if k != selected_key],
            }
            dedup_info["removed_keys"].extend([k for k in keys if k != selected_key])

        # Keys không thuộc group nào (có thể là unique accounts)
        grouped_keys = set()
        for keys in account_groups.values():
            grouped_keys.update(keys)

        ungrouped_keys = [k for k in self.api_keys if k not in grouped_keys]
        selected_keys.extend(ungrouped_keys)

        dedup_info["final_count"] = len(selected_keys)
        dedup_info["ungrouped_keys"] = ungrouped_keys

        logger.info("✅ Deduplicate hoàn tất:")
        logger.info(f"  - Trước: {dedup_info['original_count']} keys")
        logger.info(f"  - Sau: {dedup_info['final_count']} keys")
        logger.info(f"  - Đã loại bỏ: {len(dedup_info['removed_keys'])} keys")
        logger.info(f"  - Số tài khoản: {len(account_groups)}")

        return selected_keys, dedup_info

    def _select_key(
        self, keys: List[str], result_map: Dict[str, APIKeyStatus], strategy: str
    ) -> str:
        """Chọn 1 key từ list keys theo strategy."""
        if strategy == "first":
            return keys[0]
        elif strategy == "fastest":
            # Chọn key có response time nhanh nhất
            valid_keys = [
                k for k in keys if result_map.get(k) and result_map[k].is_valid
            ]
            if valid_keys:
                fastest_key = min(
                    valid_keys,
                    key=lambda k: result_map[k].response_time or float("inf"),
                )
                return fastest_key
            return keys[0]
        elif strategy == "most_reliable":
            # Chọn key có is_valid = True
            valid_keys = [
                k for k in keys if result_map.get(k) and result_map[k].is_valid
            ]
            if valid_keys:
                return valid_keys[0]
            return keys[0]
        else:
            return keys[0]


def deduplicate_account_keys(
    api_keys: List[str],
    config: Dict[str, Any],
    strategy: str = "first",
    conservative: bool = True,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Helper function để deduplicate API keys theo tài khoản.

    WARNING: Detection không chính xác 100%. Nên sử dụng conservative mode.

    Args:
        api_keys: Danh sách các API keys
        config: Configuration dictionary
        strategy: Strategy để chọn key ("first", "fastest", "most_reliable")
        conservative: Nếu True, chỉ deduplicate khi có nhiều indicators (giảm false positives)

    Returns:
        Tuple:
            - List các keys đã deduplicate
            - Dictionary với thông tin về deduplication
    """
    deduplicator = AccountDeduplicator(api_keys, config)
    return deduplicator.deduplicate(strategy=strategy, conservative=conservative)


def get_unique_account_keys(
    api_keys: List[str], config: Dict[str, Any], conservative: bool = True
) -> List[str]:
    """
    Helper function để chỉ lấy 1 key/tài khoản (simple version).

    WARNING: Detection không chính xác 100%. Nên sử dụng conservative mode.
    Trong conservative mode, chỉ deduplicate khi có nhiều indicators chung.

    Args:
        api_keys: Danh sách các API keys
        config: Configuration dictionary
        conservative: Nếu True, chỉ deduplicate khi có nhiều indicators (giảm false positives)

    Returns:
        List các keys đã deduplicate (1 key/tài khoản, hoặc tất cả nếu không detect được)
    """
    selected_keys, _ = deduplicate_account_keys(
        api_keys, config, strategy="first", conservative=conservative
    )
    return selected_keys
