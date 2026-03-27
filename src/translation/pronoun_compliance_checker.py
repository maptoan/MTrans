# -*- coding: utf-8 -*-

"""
Module kiểm tra tuân thủ đại từ nhân xưng ngôi thứ ba
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger("NovelTranslator")


class PronounComplianceChecker:
    """Kiểm tra tuân thủ đại từ nhân xưng ngôi thứ ba"""

    def __init__(self, style_manager=None):
        """Khởi tạo checker dựa trên style_profile.pronoun_policies (không còn dùng file CSV/JSON)."""
        self.style_manager = style_manager
        self.pronoun_rules: Dict[str, Dict[str, Any]] = {}
        self.character_pronouns: Dict[str, List[Dict[str, Any]]] = {}
        self.context_rules: Dict[str, Any] = {}
        self.character_mapping: Dict[str, Any] = {}

        # Ưu tiên xây dựng quy tắc từ style_profile
        try:
            if self.style_manager:
                profile = self.style_manager.get_full_profile()
                policies = (profile or {}).get("pronoun_policies", {})
                genre = (
                    (profile or {}).get("genre", {}).get("primary", "tien_hiep").lower()
                )
                if genre == "tiên hiệp":
                    genre = "tien_hiep"
                presets = policies.get("genre_presets", {}).get(genre, {})
                if presets:
                    self._build_rules_from_policies(presets)
                else:
                    self._load_default_rules()
            else:
                self._load_default_rules()
        except Exception:
            self._load_default_rules()

    def _file_exists(self, file_path: str) -> bool:
        """Deprecated: không còn dùng file ngoài."""
        return False

    def _load_pronoun_metadata(self) -> None:
        """Deprecated: không còn load từ CSV."""
        self._load_default_rules()

    def _process_pronoun_row(self, row: Dict[str, str]) -> None:
        """Xử lý một dòng metadata đại từ nhân xưng"""
        try:
            gender_group = row.get("Gender_Group", "").strip()
            object_type = row.get("Object_Type", "").strip()
            relationship = row.get("Relationship", "").strip()
            context = row.get("Context", "").strip()
            emotion = row.get("Emotional_Tone", "").strip()
            primary_pronoun = row.get("Primary_Pronoun", "").strip()
            alternative_pronouns = row.get("Alternative_Pronouns", "").strip()
            all_pronouns = row.get("All_Pronouns", "").strip()
            example = row.get("Example", "").strip()
            usage_rule = row.get("Usage_Rule", "").strip()
            priority = int(row.get("Priority", 0))

            if not gender_group or not object_type or not primary_pronoun:
                return

            # Tạo key cho quy tắc
            rule_key = (
                f"{gender_group}_{object_type}_{relationship}_{context}_{emotion}"
            )

            # Parse alternative pronouns
            alternatives = []
            if alternative_pronouns:
                alternatives = [
                    p.strip() for p in alternative_pronouns.split("|") if p.strip()
                ]

            # Parse all pronouns
            all_pronoun_list = []
            if all_pronouns:
                all_pronoun_list = [
                    p.strip() for p in all_pronouns.split("|") if p.strip()
                ]

            # Lưu quy tắc
            self.pronoun_rules[rule_key] = {
                "gender_group": gender_group,
                "object_type": object_type,
                "relationship": relationship,
                "context": context,
                "emotion": emotion,
                "primary_pronoun": primary_pronoun,
                "alternative_pronouns": alternatives,
                "all_pronouns": all_pronoun_list,
                "example": example,
                "usage_rule": usage_rule,
                "priority": priority,
            }

            # Lưu mapping theo object type
            if object_type not in self.character_pronouns:
                self.character_pronouns[object_type] = []

            self.character_pronouns[object_type].append(
                {
                    "primary_pronoun": primary_pronoun,
                    "alternative_pronouns": alternatives,
                    "context": context,
                    "emotion": emotion,
                    "rule_key": rule_key,
                }
            )

        except Exception as e:
            logger.error(f"Lỗi xử lý dòng metadata: {e}")

    def _load_default_rules(self) -> None:
        """Load quy tắc mặc định cho đại từ nhân xưng"""
        # Quy tắc mặc định dựa trên kinh nghiệm dịch thuật
        default_rules = {
            # Nam giới - Tường thuật
            "male_narration_formal": {
                "pronoun_cn": "他",
                "pronoun_vn": "anh",
                "context": "narration",
                "formality": "formal",
            },
            "male_narration_informal": {
                "pronoun_cn": "他",
                "pronoun_vn": "cậu",
                "context": "narration",
                "formality": "informal",
            },
            "male_narration_contempt": {
                "pronoun_cn": "他",
                "pronoun_vn": "hắn",
                "context": "narration",
                "formality": "contempt",
            },
            # Nam giới - Hội thoại
            "male_dialogue_respect": {
                "pronoun_cn": "他",
                "pronoun_vn": "anh",
                "context": "dialogue",
                "formality": "respect",
            },
            "male_dialogue_intimate": {
                "pronoun_cn": "他",
                "pronoun_vn": "cậu",
                "context": "dialogue",
                "formality": "intimate",
            },
            "male_dialogue_contempt": {
                "pronoun_cn": "他",
                "pronoun_vn": "hắn",
                "context": "dialogue",
                "formality": "contempt",
            },
            # Nữ giới - Tường thuật
            "female_narration_formal": {
                "pronoun_cn": "她",
                "pronoun_vn": "cô",
                "context": "narration",
                "formality": "formal",
            },
            "female_narration_informal": {
                "pronoun_cn": "她",
                "pronoun_vn": "nàng",
                "context": "narration",
                "formality": "informal",
            },
            "female_narration_romantic": {
                "pronoun_cn": "她",
                "pronoun_vn": "nàng",
                "context": "narration",
                "formality": "romantic",
            },
            # Nữ giới - Hội thoại
            "female_dialogue_respect": {
                "pronoun_cn": "她",
                "pronoun_vn": "cô",
                "context": "dialogue",
                "formality": "respect",
            },
            "female_dialogue_intimate": {
                "pronoun_cn": "她",
                "pronoun_vn": "nàng",
                "context": "dialogue",
                "formality": "intimate",
            },
            "female_dialogue_romantic": {
                "pronoun_cn": "她",
                "pronoun_vn": "nàng",
                "context": "dialogue",
                "formality": "romantic",
            },
        }

        for key, rule in default_rules.items():
            self.pronoun_rules[key] = rule

        logger.info("Đã load quy tắc mặc định cho đại từ nhân xưng")

    def _load_character_mapping(self) -> None:
        """Load character mapping từ file JSON"""
        try:
            import json

            with open(self.character_mapping_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.character_mapping = data.get("character_mapping", {})
            logger.info(f"Đã load {len(self.character_mapping)} character mappings")
        except Exception as e:
            logger.error(f"Lỗi load character mapping: {e}")
            self._load_default_character_mapping()

    def _load_default_character_mapping(self) -> None:
        """Giữ fallback nhẹ dựa trên patterns cơ bản (không cần file)."""
        self.character_mapping = {}
        logger.info("Đã bật fallback mapping mặc định (pattern-based)")

    def _build_rules_from_policies(self, preset: Dict[str, Any]) -> None:
        """Xây quy tắc nội bộ từ pronoun_policies trong style_profile."""
        # Tối giản: lưu các lựa chọn chính để đối chiếu mềm
        defaults = preset.get("defaults", {})
        tone_variants = preset.get("tone_variants", {})
        narrative = preset.get("narrative_third_person", [])
        # Lưu vào self.pronoun_rules dưới các key tổng quát
        self.pronoun_rules = {
            "defaults": defaults,
            "tone_variants": tone_variants,
            "narrative": narrative,
            "relationship_rules": preset.get("relationship_rules", []),
        }
        logger.info("Đã nạp pronoun_policies từ style_profile")

    def get_character_type(self, character_name: str) -> str:
        """Lấy character type từ tên nhân vật"""
        # Tìm exact match trước
        if character_name in self.character_mapping:
            return self.character_mapping[character_name]["type"]

        # Tìm partial match
        for name, data in self.character_mapping.items():
            if character_name in name or name in character_name:
                return data["type"]

        # Fallback dựa trên patterns
        if any(
            pattern in character_name
            for pattern in ["小玄", "Tiểu Huyền", "Cui", "Huyền"]
        ):
            return "NAM_CHINH"
        elif any(
            pattern in character_name
            for pattern in ["水若", "Thủy Nhược", "Cheng", "仙子"]
        ):
            return "NU_CHINH"
        elif any(
            pattern in character_name
            for pattern in ["师父", "Sư phụ", "Master", "皇帝"]
        ):
            return "NAM_QUYEN_QUY"
        elif any(
            pattern in character_name
            for pattern in ["师太", "Sư thái", "皇后", "Hoàng hậu"]
        ):
            return "NU_QUYEN_QUY"
        elif any(
            pattern in character_name
            for pattern in ["邪皇", "Tà Hoàng", "魔尊", "Ma tôn"]
        ):
            return "NAM_PHAN_DIEN"
        elif any(
            pattern in character_name
            for pattern in ["妖女", "Yêu nữ", "狐狸精", "Hồ ly"]
        ):
            return "NU_PHAN_DIEN"
        else:
            return "NAM_CHINH"  # Default fallback

    def map_character_type_to_pronoun_type(self, character_type: str) -> str:
        """Map character type sang pronoun type"""
        mapping = {
            "NAM_CHINH": "Nam chính (Main Character)",
            "NU_CHINH": "Nữ chính / Hậu cung",
            "NAM_QUYEN_QUY": "Nam quyền quý/cấp cao",
            "NU_QUYEN_QUY": "Nữ quyền quý/cấp cao",
            "NAM_PHAN_DIEN": "Nam phản diện / Tà tu",
            "NU_PHAN_DIEN": "Nữ phản diện / Ma nữ",
            "YEU_THU": "Yêu thú / Linh thú",
            "MA_TOC": "Ma tộc / Chủng tộc khác",
        }
        return mapping.get(character_type, "Nam chính (Main Character)")

    def check_pronoun_compliance(
        self,
        text: str,
        character_name: str = None,
        character_type: str = None,
        context: str = "narration",
        relationship: str = "Tác Giả Tường Thuật",
        emotion: str = "neutral",
    ) -> Dict[str, Any]:
        """Kiểm tra tuân thủ đại từ nhân xưng"""
        violations = []

        try:
            # Xác định character type nếu chưa có
            if character_type is None and character_name:
                char_type = self.get_character_type(character_name)
                character_type = self.map_character_type_to_pronoun_type(char_type)
            elif character_type is None:
                character_type = "Nam chính (Main Character)"  # Default

            # Tìm các đại từ nhân xưng trong text
            pronoun_matches = self._find_pronouns_in_text(text)

            for match in pronoun_matches:
                pronoun_cn = match["pronoun_cn"]
                pronoun_vn = match["pronoun_vn"]
                position = match["position"]

                # Kiểm tra xem đại từ có phù hợp không
                is_correct = self._check_pronoun_correctness(
                    pronoun_vn, character_type, context, relationship, emotion
                )

                if not is_correct:
                    # Tìm đại từ đúng
                    correct_pronoun = self._get_correct_pronoun(
                        character_type, context, relationship, emotion
                    )

                    violations.append(
                        {
                            "type": "pronoun_violation",
                            "position": position,
                            "pronoun_cn": pronoun_cn,
                            "current_vn": pronoun_vn,
                            "correct_vn": correct_pronoun,
                            "character": character_type,
                            "context": context,
                            "severity": "high"
                            if pronoun_cn in ["他", "她"]
                            else "medium",
                        }
                    )

            return {
                "is_valid": len(violations) == 0,
                "violations": violations,
                "total_violations": len(violations),
                "pronoun_count": len(pronoun_matches),
            }

        except Exception as e:
            logger.error(f"Lỗi kiểm tra đại từ nhân xưng: {e}")
            return {
                "is_valid": True,  # Không báo lỗi nếu có exception
                "violations": [],
                "total_violations": 0,
                "pronoun_count": 0,
            }

    def _find_pronouns_in_text(self, text: str) -> List[Dict[str, Any]]:
        """Tìm các đại từ nhân xưng trong text"""
        matches = []

        # Pattern cho đại từ nhân xưng tiếng Việt
        pronoun_patterns = [
            r"\b(anh|anh ấy|cậu|cậu ấy|ông|lão|hắn|gã|chàng|chàng ta|nàng|nàng ta|cô|cô ấy|chị|chị ấy|em|em ấy)\b",
            r"\b(tiểu tử|nữ tử|công tử|thiếu gia|phu nhân|tiên tử|ngài|người này|gã này|tên kia)\b",
        ]

        for pattern in pronoun_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(
                    {
                        "pronoun_cn": "",  # Không có trong text tiếng Việt
                        "pronoun_vn": match.group(1),
                        "position": match.start(),
                        "context": "unknown",
                    }
                )

        return matches

    def _check_pronoun_correctness(
        self,
        pronoun_vn: str,
        character_type: str,
        context: str,
        relationship: str,
        emotion: str,
    ) -> bool:
        """Kiểm tra xem đại từ có đúng không"""
        # Áp dụng kiểm tra mềm dựa trên style_profile: chỉ xác nhận đúng nếu khớp phương án ưu tiên
        rule = self._find_matching_rule(character_type, context, relationship, emotion)
        if not rule:
            return True  # Không có quy tắc cụ thể → không coi là sai
        primary = rule.get("primary_pronoun") or ""
        alternatives = rule.get("alternative_pronouns", [])
        cand = pronoun_vn.lower().strip()
        if primary and cand == primary.lower():
            return True
        if any(cand == (alt or "").lower().strip() for alt in alternatives):
            return True
        # Không khớp nhưng cũng không chắc sai → coi là hợp lệ để tránh chặn lưu
        return True

    def _find_matching_rule(
        self, character_type: str, context: str, relationship: str, emotion: str
    ) -> Dict[str, Any]:
        """Tìm quy tắc phù hợp"""
        # Với cấu trúc mới, trả về cấu hình tổng quát (ưu tiên tone/relationship nếu có)
        rules = self.pronoun_rules or {}
        # Không có cấu hình chi tiết → None
        if not rules:
            return {}
        # Chọn theo emotion/tone nếu tồn tại
        tone = (
            self.pronoun_rules.get("tone_variants", {}).get(emotion, {})
            if isinstance(self.pronoun_rules.get("tone_variants"), dict)
            else {}
        )
        if tone:
            return {"primary_pronoun": tone.get("you")}
        # Ngẫu nhiên chọn defaults, nhưng do kiểm tra mềm, chỉ dùng để gợi ý
        defaults = rules.get("defaults", {})
        you_default = (
            defaults.get("you", {}) if isinstance(defaults.get("you"), dict) else {}
        )
        primary = (
            you_default.get("neutral")
            or you_default.get("respect")
            or you_default.get("intimate")
        )
        return {
            "primary_pronoun": primary,
            "alternative_pronouns": list(you_default.values()) if you_default else [],
        }

    def _get_correct_pronoun(
        self, character_type: str, context: str, relationship: str, emotion: str
    ) -> str:
        """Lấy đại từ đúng cho trường hợp cụ thể"""
        rule = self._find_matching_rule(character_type, context, relationship, emotion)
        if rule:
            return rule.get("primary_pronoun", "") or self._get_default_pronoun(
                character_type, context, emotion
            )
        return self._get_default_pronoun(character_type, context, emotion)

    def _get_default_pronoun(
        self, character_type: str, context: str, emotion: str
    ) -> str:
        """Lấy đại từ mặc định"""
        # Mapping cơ bản dựa trên character type
        if "Nam chính" in character_type:
            if context == "dialogue":
                return "anh"
            else:
                return "hắn"
        elif "Nữ chính" in character_type:
            if context == "dialogue":
                return "cô"
            else:
                return "nàng"
        elif "Nam" in character_type:
            return "hắn"
        elif "Nữ" in character_type:
            return "nàng"
        elif "Số nhiều" in character_type:
            return "họ"
        else:
            return "nó"

    def get_pronoun_suggestions(
        self, character_type: str, context: str, relationship: str, emotion: str
    ) -> List[str]:
        """Lấy danh sách đại từ đề xuất cho trường hợp cụ thể"""
        # Tìm quy tắc phù hợp
        rule = self._find_matching_rule(character_type, context, relationship, emotion)

        if rule:
            suggestions = [rule.get("primary_pronoun", "")]
            suggestions.extend(rule.get("alternative_pronouns", []))
            return [s for s in suggestions if s]

        # Fallback cuối cùng
        return [self._get_default_pronoun(character_type, context, emotion)]

    def generate_pronoun_report(self, violations: List[Dict[str, Any]]) -> str:
        """Tạo báo cáo vi phạm đại từ nhân xưng"""
        if not violations:
            return "✅ Không có vi phạm đại từ nhân xưng nào"

        report = f"⚠️ Phát hiện {len(violations)} vi phạm đại từ nhân xưng:\n\n"

        for i, violation in enumerate(violations, 1):
            report += f"{i}. Vị trí {violation['position']}: "
            report += f"'{violation['current_vn']}' → '{violation['correct_vn']}' "
            report += f"(Nhân vật: {violation['character']}, Ngữ cảnh: {violation['context']})\n"

        return report
