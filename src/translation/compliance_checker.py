# -*- coding: utf-8 -*-

"""
Module kiểm tra tuân thủ metadata trong quá trình dịch
"""

import logging
import re
from typing import Any, Dict, List

from .pronoun_compliance_checker import PronounComplianceChecker

logger = logging.getLogger("NovelTranslator")


class ComplianceChecker:
    """Kiểm tra tuân thủ metadata trong bản dịch"""

    def __init__(self, style_manager, glossary_manager, config: Dict[str, Any] = None):
        self.style_manager = style_manager
        self.glossary_manager = glossary_manager
        self.config = config or {}

        # Compliance settings từ config
        self.compliance_config = self.config.get("translation", {}).get(
            "compliance", {}
        )
        self.enable_compliance = self.config.get("translation", {}).get(
            "enable_compliance_check", True
        )

        # Individual check settings
        self.enable_glossary_check = self.compliance_config.get(
            "enable_glossary_check", True
        )
        self.enable_pronoun_check = self.compliance_config.get(
            "enable_pronoun_check", True
        )
        self.enable_cjk_check = self.compliance_config.get("enable_cjk_check", True)
        self.enable_style_check = self.compliance_config.get("enable_style_check", True)

        # Retry settings
        self.retry_threshold = self.compliance_config.get("retry_threshold", 60)
        self.max_compliance_retries = self.compliance_config.get(
            "max_compliance_retries", 2
        )

        # Weight settings
        self.critical_weight = self.compliance_config.get("critical_weight", 50)
        self.high_weight = self.compliance_config.get("high_weight", 20)
        self.medium_weight = self.compliance_config.get("medium_weight", 5)

        # Compile patterns for efficiency - mở rộng để bắt tất cả ký tự không phải tiếng Việt
        self.cjk_pattern = re.compile(r"[\u4e00-\u9fff]+")  # Tiếng Trung
        self.thai_pattern = re.compile(r"[\u0e00-\u0e7f]+")  # Tiếng Thái
        self.korean_pattern = re.compile(r"[\uac00-\ud7af]+")  # Tiếng Hàn
        self.japanese_pattern = re.compile(
            r"[\u3040-\u309f\u30a0-\u30ff]+"
        )  # Tiếng Nhật
        # Thêm các ký tự đặc biệt khác
        self.special_chars_pattern = re.compile(
            r"[^\u0000-\u007F\u00C0-\u017F\u1EA0-\u1EF9\u0102\u0103\u00C2\u00E2\u00CA\u00EA\u00D4\u00F4\u01A0\u01A1\u01AF\u01B0\u00C3\u00E3\u00D5\u00F5\u00C8\u00E8\u00C9\u00E9\u00CC\u00EC\u00CD\u00ED\u00D2\u00F2\u00D3\u00F3\u00D9\u00F9\u00DA\u00FA\u00DD\u00FD\u00C1\u00E1\u00C4\u00E4\u00C5\u00E5\u00C6\u00E6\u00C7\u00E7\u00D0\u00F0\u00D6\u00F6\u00D8\u00F8\u00DE\u00FE\u00DF\u00C0\u00E0\u00C3\u00E3\u00C4\u00E4\u00C5\u00E5\u00C6\u00E6\u00C7\u00E7\u00C8\u00E8\u00C9\u00E9\u00CA\u00EA\u00CB\u00EB\u00CC\u00EC\u00CD\u00ED\u00CE\u00EE\u00CF\u00EF\u00D0\u00F0\u00D1\u00F1\u00D2\u00F2\u00D3\u00F3\u00D4\u00F4\u00D5\u00F5\u00D6\u00F6\u00D8\u00F8\u00D9\u00F9\u00DA\u00FA\u00DB\u00FB\u00DC\u00FC\u00DD\u00FD\u00DE\u00FE\u00DF]+"
        )
        # Mở rộng pattern để bắt tất cả ký tự không phải tiếng Việt
        self.foreign_pattern = re.compile(
            r"[\u4e00-\u9fff\u0e00-\u0e7f\uac00-\ud7af\u3040-\u309f\u30a0-\u30ff\u2000-\u206F\u2E00-\u2E7F\u3000-\u303F\uFF00-\uFFEF\u3400-\u4DBF\u20000-\u2A6DF\u2A700-\u2B73F\u2B740-\u2B81F\u2B820-\u2CEAF\uF900-\uFAFF\u2F800-\u2FA1F]+"
        )
        self.pronoun_patterns = {}

        logger.info(
            f"ComplianceChecker khởi tạo: enable={self.enable_compliance}, "
            f"glossary={self.enable_glossary_check}, pronoun={self.enable_pronoun_check}, "
            f"cjk={self.enable_cjk_check}, style={self.enable_style_check}"
        )

    def _build_pronoun_patterns(self) -> Dict[str, List[str]]:
        """Không còn sử dụng character_relations; trả về rỗng"""
        return {}

    def check_glossary_compliance(
        self, translated_text: str, relevant_terms: List[Dict]
    ) -> List[Dict]:
        """Kiểm tra tuân thủ glossary"""
        violations = []
        missed_terms_count = 0
        wrong_terms_count = 0

        for term in relevant_terms:
            original_cn = term.get("Original_Term_CN", "")
            term.get("Original_Term_Pinyin", "")
            translated_vi = term.get("Translated_Term_VI", "")
            translation_rule = term.get("Translation_Rule", "")

            # Kiểm tra xem có sử dụng đúng thuật ngữ không
            if original_cn and translated_vi:
                # Tìm thuật ngữ gốc trong bản dịch (không nên có)
                if original_cn in translated_text:
                    wrong_terms_count += 1
                    violations.append(
                        {
                            "type": "glossary_violation",
                            "original": original_cn,
                            "expected": translated_vi,
                            "found": original_cn,
                            "rule": translation_rule,
                            "severity": "high",
                        }
                    )

                # Kiểm tra xem có sử dụng thuật ngữ đã dịch không
                if (
                    translated_vi not in translated_text
                    and original_cn in translated_text
                ):
                    missed_terms_count += 1
                    violations.append(
                        {
                            "type": "glossary_missing",
                            "original": original_cn,
                            "expected": translated_vi,
                            "found": "not_found",
                            "rule": translation_rule,
                            "severity": "high",
                        }
                    )

        # Thêm thống kê tổng quan
        if violations:
            violations.append(
                {
                    "type": "glossary_summary",
                    "missed_terms_count": missed_terms_count,
                    "wrong_terms_count": wrong_terms_count,
                    "total_terms": len(relevant_terms),
                    "severity": "info",
                }
            )

        return violations

    def check_pronoun_compliance(
        self, translated_text: str, active_characters: List[str]
    ) -> List[Dict]:
        """Kiểm tra tuân thủ cách xưng hô sử dụng hệ thống mới"""
        violations = []

        # Khởi tạo PronounComplianceChecker nếu chưa có
        if not hasattr(self, "pronoun_checker"):
            self.pronoun_checker = PronounComplianceChecker(
                style_manager=self.style_manager
            )

        # Xác định character type dựa trên active_characters
        character_type = self._determine_character_type(active_characters)

        # Kiểm tra compliance cho các ngữ cảnh khác nhau
        contexts = ["narration", "dialogue", "internal_monologue"]
        emotions = [
            "neutral",
            "respectful",
            "affectionate",
            "contemptuous",
            "angry",
            "playful",
        ]

        for context in contexts:
            for emotion in emotions:
                # Kiểm tra compliance
                result = self.pronoun_checker.check_pronoun_compliance(
                    text=translated_text,
                    character_type=character_type,
                    context=context,
                    relationship="Tác Giả Tường Thuật",  # Default relationship
                    emotion=emotion,
                )

                # Thêm violations nếu có
                if not result["is_valid"] and result["violations"]:
                    for violation in result["violations"]:
                        violations.append(
                            {
                                "type": "pronoun_violation",
                                "character": character_type,
                                "context": context,
                                "emotion": emotion,
                                "violation": violation,
                                "severity": "high"
                                if "critical" in str(violation).lower()
                                else "medium",
                            }
                        )

        return violations

    def _determine_character_type(self, active_characters: List[str]) -> str:
        """Xác định character type dựa trên active characters"""
        if not active_characters:
            return "Nam chính (Main Character)"  # Default

        # Sử dụng PronounComplianceChecker để xác định character type
        if hasattr(self, "pronoun_checker"):
            character = active_characters[0]  # Lấy character đầu tiên
            char_type = self.pronoun_checker.get_character_type(character)
            return self.pronoun_checker.map_character_type_to_pronoun_type(char_type)
        else:
            # Fallback cũ
            character = active_characters[0]
            if any(name in character for name in ["小玄", "Tiểu Huyền", "Thôi"]):
                return "Nam chính (Main Character)"
            elif any(name in character for name in ["水若", "Thủy Nhược", "Cheng"]):
                return "Nữ chính / Hậu cung"
            elif any(name in character for name in ["师父", "Sư phụ", "Master"]):
                return "Nam quyền quý/cấp cao"
            elif any(name in character for name in ["师姐", "Sư tỷ", "Sister"]):
                return "Nữ chính / Hậu cung"
            else:
                return "Nam chính (Main Character)"  # Default fallback

    def check_foreign_compliance(self, translated_text: str) -> List[Dict]:
        """Kiểm tra còn ký tự nước ngoài (CJK, Thái, Hàn, Nhật) không"""
        violations = []
        foreign_matches = self.foreign_pattern.findall(translated_text)
        if foreign_matches:
            cjk_matches = self.cjk_pattern.findall(translated_text)
            thai_matches = self.thai_pattern.findall(translated_text)
            korean_matches = self.korean_pattern.findall(translated_text)
            japanese_matches = self.japanese_pattern.findall(translated_text)

            violation_details = []
            if cjk_matches:
                violation_details.append(f"Tiếng Trung: {cjk_matches}")
            if thai_matches:
                violation_details.append(f"Tiếng Thái: {thai_matches}")
            if korean_matches:
                violation_details.append(f"Tiếng Hàn: {korean_matches}")
            if japanese_matches:
                violation_details.append(f"Tiếng Nhật: {japanese_matches}")

            violations.append(
                {
                    "type": "foreign_characters_remaining",
                    "foreign_characters": foreign_matches,
                    "details": violation_details,
                    "severity": "critical",
                }
            )
        return violations

    def check_style_compliance(self, translated_text: str) -> List[Dict]:
        """Kiểm tra tuân thủ văn phong"""
        violations = []

        # Lấy style profile
        style_profile = self.style_manager.get_full_profile()
        if not style_profile:
            return violations

        # Kiểm tra các quy tắc preserve
        preserve_rules = style_profile.get("translation_guidelines", {}).get(
            "preserve", []
        )
        for rule in preserve_rules:
            if "cổ điển" in rule.lower() and "hiện đại" in translated_text.lower():
                violations.append(
                    {"type": "style_violation", "rule": rule, "severity": "medium"}
                )

        return violations

    def check_compliance(
        self,
        translated_text: str,
        relevant_terms: List[Dict],
        active_characters: List[str],
    ) -> Dict[str, Any]:
        """Kiểm tra tổng thể tuân thủ metadata"""

        # Kiểm tra xem có bật compliance checking không
        if not self.enable_compliance:
            return {
                "compliance_score": 100,
                "needs_retry": False,
                "total_violations": 0,
                "critical_violations": [],
                "high_violations": [],
                "medium_violations": [],
                "all_violations": [],
            }

        all_violations = []

        # Kiểm tra các loại tuân thủ (chỉ khi được bật)
        if self.enable_glossary_check:
            all_violations.extend(
                self.check_glossary_compliance(translated_text, relevant_terms)
            )
        if self.enable_pronoun_check:
            all_violations.extend(
                self.check_pronoun_compliance(translated_text, active_characters)
            )
        if self.enable_cjk_check:
            all_violations.extend(self.check_foreign_compliance(translated_text))
        if self.enable_style_check:
            all_violations.extend(self.check_style_compliance(translated_text))

        # Phân loại theo mức độ nghiêm trọng
        critical_violations = [v for v in all_violations if v["severity"] == "critical"]
        high_violations = [v for v in all_violations if v["severity"] == "high"]
        medium_violations = [v for v in all_violations if v["severity"] == "medium"]

        # Tính điểm tuân thủ
        total_violations = len(all_violations)
        critical_count = len(critical_violations)
        high_count = len(high_violations)
        medium_count = len(medium_violations)

        # Điểm tuân thủ (0-100) - sử dụng weights từ config
        compliance_score = max(
            0,
            100
            - (
                critical_count * self.critical_weight
                + high_count * self.high_weight
                + medium_count * self.medium_weight
            ),
        )

        # Quyết định có cần dịch lại không - sử dụng threshold từ config
        needs_retry = compliance_score < self.retry_threshold and total_violations > 0

        return {
            "is_valid": total_violations == 0,
            "compliance_score": compliance_score,
            "needs_retry": needs_retry,
            "total_violations": total_violations,
            "critical_violations": critical_violations,
            "high_violations": high_violations,
            "medium_violations": medium_violations,
            "all_violations": all_violations,
        }

    def generate_compliance_report(self, compliance_result: Dict[str, Any]) -> str:
        """Tạo báo cáo tuân thủ"""
        if compliance_result["total_violations"] == 0:
            return "✅ Tuân thủ hoàn hảo metadata"

        report = f"⚠️ Điểm tuân thủ: {compliance_result['compliance_score']}/100\n"
        report += f"Tổng vi phạm: {compliance_result['total_violations']}\n"

        if compliance_result["critical_violations"]:
            report += "\n🚨 VI PHẠM NGHIÊM TRỌNG:\n"
            for v in compliance_result["critical_violations"]:
                report += f"- {v['type']}: {v}\n"

        if compliance_result["high_violations"]:
            report += "\n⚠️ VI PHẠM CAO:\n"
            for v in compliance_result["high_violations"]:
                report += f"- {v['type']}: {v}\n"

        if compliance_result["medium_violations"]:
            report += "\n📝 VI PHẠM TRUNG BÌNH:\n"
            for v in compliance_result["medium_violations"]:
                report += f"- {v['type']}: {v}\n"

        return report
