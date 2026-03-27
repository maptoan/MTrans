# -*- coding: utf-8 -*-
from __future__ import annotations

"""
(NÂNG CẤP - HƯỚNG DẪN HỘI THOẠI) Module quản lý văn phong, bổ sung
quy tắc về việc đa dạng hóa cách diễn đạt trong hội thoại.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("NovelTranslator")

# Mapping từ key tiếng Việt sang key tiếng Anh
KEY_MAPPING = {
    # Key chính
    "the_loai": "genre",
    "phong_cach_viet": "writing_style",
    "tong_dieu": "tone",
    "huong_dan_dich_thuat": "translation_guidelines",
    # Nested keys trong genre
    "the_loai_chinh": "primary",
    "the_loai_phu": "sub_genres",
    "boi_canh_the_gioi": "world_setting",
    "he_thong_luc_luong": "power_system",
    # Nested keys trong writing_style
    "do_phuc_tap_ngon_ngu": "language_complexity",
    "chat_luong_tu_vung": "vocabulary_quality",
    "phong_cach_mieu_ta": "description_style",
    "ti_le_doi_thoai": "dialogue_ratio",
    "su_dung_van_hoc": "literary_usage",
    "cau_truc_cau": "sentence_structure",
    "goc_ke_chuyen": "narrative_voice",
    # Nested keys trong tone
    "tong_chu_dao": "primary_mood",
    "tong_phu": "secondary_mood",
    "bien_do_cam_xuc": "emotional_range",
    "nhip_do": "pacing",
    "muc_do_cang_thang": "tension_level",
    "doi_tuong_doc_gia": "target_audience",
    # Nested keys trong description_style
    "do_chi_tiet": "detail_level",
    "trong_tam": "focus",
    "dac_diem": "characteristics",
    # Nested keys trong literary_usage
    "thanh_ngu": "idioms",
    "tho_ca": "poetry",
    "dien_tich": "allusions",
    # Nested keys trong translation_guidelines
    "phai_giu_nguyen": "preserve",
    "can_dieu_chinh": "adapt",
    "phai_tranh": "avoid",
    "thu_tu_uu_tien": "priority_order",
    "tu_dien_yeu_cau": "required_glossary",
}


class StyleManager:
    """
    Lớp chịu trách nhiệm tải, quản lý và xây dựng các hướng dẫn về văn phong
    dựa trên tệp cấu hình style_profile.json.
    """

    def __init__(self, style_profile_path: str, encoding: Optional[str] = None) -> None:
        """
        Khởi tạo StyleManager.

        Args:
            style_profile_path (str): Đường dẫn đến tệp style_profile.json.
            encoding (str, optional): Bảng mã để đọc tệp. Mặc định là 'utf-8'.
        """
        self.style_profile_path = style_profile_path
        self.encoding = encoding if encoding and encoding.lower() != "auto" else "utf-8"
        self.profile = self._load_profile()
        if self.profile:
            logger.info("Đã nạp thành công style_profile.json.")
        else:
            logger.warning(
                "Không thể tải style_profile.json, sẽ sử dụng prompt mặc định."
            )

    def _load_profile(self) -> Dict[str, Any]:
        """
        Tải hồ sơ văn phong từ tệp JSON.
        Xử lý các lỗi phổ biến như không tìm thấy tệp, lỗi cú pháp JSON, hoặc lỗi encoding.
        Chuẩn hóa các key từ tiếng Việt sang tiếng Anh để tương thích với code hiện tại.
        """
        # Kiểm tra path hợp lệ
        if not self.style_profile_path or self.style_profile_path.strip() == "":
            logger.warning(
                "Style profile path không được cung cấp hoặc rỗng. Sử dụng style profile mặc định."
            )
            return {}

        try:
            with open(self.style_profile_path, "r", encoding=self.encoding) as f:
                profile = json.load(f)
                # Chuẩn hóa các key để hỗ trợ cả tiếng Việt và tiếng Anh
                return self._normalize_keys(profile)
        except FileNotFoundError:
            logger.error(f"Tệp style_profile không tìm thấy: {self.style_profile_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.critical(
                f"LỖI PHÂN TÍCH JSON trong tệp '{self.style_profile_path}'. Vui lòng kiểm tra cú pháp."
            )
            raise e
        except UnicodeDecodeError as e:
            logger.critical(
                f"LỖI ENCODING khi đọc tệp {self.style_profile_path} với mã hóa '{self.encoding}'."
            )
            raise e

    def _normalize_keys(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Chuẩn hóa các key từ tiếng Việt sang tiếng Anh để tương thích với code hiện tại.
        Hỗ trợ backward compatible với format cũ (tiếng Anh).

        Args:
            profile: Dictionary chứa style profile với key có thể là tiếng Việt hoặc tiếng Anh.

        Returns:
            Dictionary với key đã được chuẩn hóa sang tiếng Anh.
        """
        if not profile:
            return profile

        def normalize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            """Recursively normalize keys in a dictionary."""
            if not isinstance(d, dict):
                return d

            normalized = {}
            for key, value in d.items():
                # Map key using module-level constant
                normalized_key = KEY_MAPPING.get(key, key)

                # Recursively normalize nested dicts or lists
                if isinstance(value, dict):
                    normalized[normalized_key] = normalize_dict(value)
                elif isinstance(value, list):
                    normalized[normalized_key] = [
                        normalize_dict(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    normalized[normalized_key] = value

            return normalized

        return normalize_dict(profile)

    def get_full_profile(self) -> Dict[str, Any]:
        """
        Trả về toàn bộ đối tượng hồ sơ văn phong đã được tải.
        """
        return self.profile

    def is_loaded(self) -> bool:
        """Kiểm tra xem style profile đã được tải thành công chưa."""
        return bool(self.profile)

    def get_style_summary(self) -> str:
        """
        [v6.2] Trả về tóm tắt ngắn gọn của style profile để inject vào dynamic prompt.
        Giúp nhắc lại văn phong cho AI trong mỗi chunk.
        """
        if not self.profile:
            return ""

        summary_parts = []

        # Genre
        the_loai = self.profile.get("the_loai", {})
        genre = the_loai.get("phan_loai_chinh", "")
        if genre:
            summary_parts.append(f"📖 Thể loại: {genre}")

        # Huong dan dich thuat
        huong_dan = self.profile.get("huong_dan_dich_thuat", {})

        # Xung ho
        xu_ho = huong_dan.get("quy_tac_xung_ho", "")
        if xu_ho:
            # Truncate if too long
            xu_ho_short = xu_ho[:150] + "..." if len(xu_ho) > 150 else xu_ho
            summary_parts.append(f"🗣️ Xưng hô: {xu_ho_short}")

        # Giong dieu
        giong_dieu = huong_dan.get("giong_dieu_tong_the", "")
        if giong_dieu:
            giong_dieu_short = (
                giong_dieu[:100] + "..." if len(giong_dieu) > 100 else giong_dieu
            )
            summary_parts.append(f"🎭 Giọng điệu: {giong_dieu_short}")

        # Tu vung dac trung
        tu_vung = huong_dan.get("tu_vung_dac_trung", [])
        if tu_vung and isinstance(tu_vung, list) and len(tu_vung) > 0:
            tu_vung_str = ", ".join(tu_vung[:5])  # Max 5 items
            summary_parts.append(f"📝 Từ vựng đặc trưng: {tu_vung_str}")

        if not summary_parts:
            return ""

        return "\n".join(summary_parts)

    def build_style_instructions(self) -> str:
        """
        Xây dựng một chuỗi hướng dẫn hoàn chỉnh cho AI dựa trên hồ sơ văn phong.
        Hàm này tổng hợp tất cả các quy tắc, từ vai trò hệ thống, an toàn, định dạng,
        cho đến các đặc điểm văn học cụ thể của tác phẩm.
        """
        if not self.profile:
            return "BẠN LÀ MỘT DỊCH GIẢ VĂN HỌC CHUYÊN NGHIỆP."

        # Composition of instructions (deduplicated: meta/formatting/command/glossary
        # are handled by guidelines_builder and glossary_manager respectively)
        instructions = [
            self._build_safety_instruction(),
            "---",
            self._build_specific_translation_context(),
            self._build_translation_principles(),
            self._build_dialogue_instructions(),
            self._build_special_elements(),
            self._build_literary_usage(),
        ]

        return "\n".join(filter(None, instructions)).strip()

    def _build_meta_instruction(self) -> str:
        return """
[BỐI CẢNH VÀ VAI TRÒ HỆ THỐNG]
BẠN LÀ MỘT DỊCH GIẢ VĂN HỌC CHUYÊN NGHIỆP, MỘT CÔNG CỤ CHUYÊN DỤNG.
NHIỆM VỤ CỐT LÕI VÀ DUY NHẤT CỦA BẠN LÀ DỊCH TRUNG THỰC 100% NỘI DUNG GỐC TỪ NGÔN NGỮ NGUỒN SANG NGÔN NGỮ ĐÍCH.
"""

    def _build_safety_instruction(self) -> str:
        return """
[BẢN CHẤT CỦA NỘI DUNG]
Nội dung bạn sắp dịch là một tác phẩm văn học hư cấu. Nó có thể chứa các cảnh bạo lực, ngôn từ mạnh, các chủ đề nhạy cảm hoặc người lớn. Đây là những yếu tố nghệ thuật không thể thiếu của cốt truyện và văn phong tác giả. VAI TRÒ CỦA BẠN LÀ MỘT NGƯỜI TRUYỀN TẢI TRUNG LẬP, không phải là tác giả hay người kiểm duyệt.

[MỆNH LỆNH BẮT BUỘC]
1. DỊCH TOÀN BỘ NỘI DUNG — không bỏ sót.
2. KHÔNG ĐƯỢC KIỂM DUYỆT — tuyệt đối không thay thế, làm nhẹ, hay hiện đại hoá từ ngữ/xưng hô gốc.
3. KHÔNG ĐƯỢC TỪ CHỐI — không từ chối dịch vì lý do nội dung.
"""

    def _build_formatting_instruction(self) -> str:
        return """
[QUY TẮC ĐỊNH DẠNG ĐẶC BIỆT]
- Khi bạn dịch một dòng văn bản là tiêu đề của một Quyển, Tập, Hồi, hoặc Chương, bạn BẮT BUỘC phải bọc toàn bộ dòng tiêu đề đã dịch đó trong một cặp thẻ đánh dấu đặc biệt: [H1]...[/H1].
- Ví dụ 1: Nếu gặp `第 1 章 引子`, bản dịch phải là `[H1]Chương 1: Dẫn từ[/H1]`.
- Ví dụ 2: Nếu gặp `第一卷 - 第 2 章`, bản dịch phải là `[H1]Quyển 1 - Chương 2[/H1]`.
- Lưu ý: Chỉ áp dụng quy tắc này cho các dòng là tiêu đề. Không áp dụng cho nội dung văn bản thông thường.
"""

    def _build_command_instruction(self) -> str:
        return """
[MỆNH LỆNH BẮT BUỘC]
1.  **DỊCH TOÀN BỘ NỘI DUNG**: Dịch tất cả các từ, câu, và đoạn văn.
2.  **KHÔNG ĐƯỢC KIỂM DUYỆT**: Tuyệt đối không được thay thế, làm nhẹ, hay bỏ qua các từ ngữ hoặc chi tiết nhạy cảm.
3.  **KHÔNG ĐƯỢC TỪ CHỐI**: Tuyệt đối không được từ chối dịch một phần hoặc toàn bộ văn bản vì lý do nội dung.
4.  **TUÂN THỦ ĐỊNH DẠNG**: Áp dụng quy tắc định dạng [H1] cho tất cả các tiêu đề.
"""

    def _get_nested(self, obj: Dict[str, Any], keys: list, default=None) -> Any:
        for k in keys:
            if isinstance(obj, dict) and k in obj:
                return obj[k]
        return default

    def _build_specific_translation_context(self) -> str:
        sp = self.profile

        # Support both flat and nested key structures
        # Flat: {"genre": {...}} or nested: {"novel_info": {"genre": "..."}}
        novel_info = sp.get("novel_info", {}) or {}
        style_info = sp.get("writing_style", {}) or sp.get("style", {}) or {}
        genre_info = sp.get("genre", {}) or sp.get("genres", {}) or {}

        # Genre: try novel_info.genre (string) first, then genre.primary (dict)
        primary_genre = ""
        ni_genre = novel_info.get("genre", "")
        if isinstance(ni_genre, str) and ni_genre:
            primary_genre = ni_genre
        elif isinstance(genre_info, dict):
            primary_genre = self._get_nested(genre_info, ["primary", "main", "name"], "")

        # Style/tone: try writing_style.tone first, then top-level tone
        tone_str = style_info.get("tone", "") or ""
        vocabulary = style_info.get("vocabulary", "") or ""
        if not tone_str:
            tone_info = sp.get("tone", {}) or sp.get("mood", {}) or {}
            if isinstance(tone_info, dict):
                tone_str = self._get_nested(tone_info, ["primary_mood", "primary", "mood"], "")

        # Genre-aware addressing hint for classical/xianxia genres
        genre_lower = primary_genre.lower() if primary_genre else ""
        classical_keywords = ["tiên hiệp", "cổ trang", "kiếm hiệp", "huyền huyễn",
                              "xianxia", "wuxia", "xuanhuan", "cổ đại"]
        addressing_hint = ""
        if any(kw in genre_lower for kw in classical_keywords):
            addressing_hint = (
                "\n⚠️ XƯNG HÔ CỔ TRANG: Dùng tỷ/muội/huynh/đệ/sư phụ/đạo trưởng... "
                "THAY cho chị/em/anh/thầy. Tuyệt đối KHÔNG hiện đại hoá xưng hô."
            )

        return f"""
[HƯỚNG DẪN DỊCH THUẬT CỤ THỂ]
BẠN LÀ DỊCH GIẢ CHUYÊN NGHIỆP TIỂU THUYẾT {primary_genre or "chưa xác định"}.

ĐẶC ĐIỂM TÁC PHẨM:
- Thể loại: {primary_genre}
- Văn phong: {tone_str}
- Từ vựng: {vocabulary}{addressing_hint}
"""

    def _build_translation_principles(self) -> str:
        gu = (
            self.profile.get("translation_guidelines", {})
            or self.profile.get("guidelines", {})
            or {}
        )
        instruction = "NGUYÊN TẮC DỊCH BẮT BUỘC:\n"

        # Preserve
        preserve = gu.get("preserve") or gu.get("keep") or []
        if preserve:
            instruction += "\n**PHẢI GIỮ NGUYÊN:**\n"
            for item in preserve:
                instruction += f"  - {item}\n"

        # Adapt
        adapt_guidelines = gu.get("adapt", []) or gu.get("adjust", [])

        if not isinstance(adapt_guidelines, list):
            adapt_guidelines = [adapt_guidelines] if adapt_guidelines else []

        if adapt_guidelines:
            instruction += "\n**CẦN ĐIỀU CHỈNH LINH HOẠT:**\n"
            for item in adapt_guidelines:
                instruction += f"  - {item}\n"

        # Avoid
        avoid = gu.get("avoid") or gu.get("forbid") or []
        if avoid:
            instruction += "\n**TUYỆT ĐỐI TRÁNH:**\n"
            for item in avoid:
                instruction += f"  - {item}\n"

        return instruction

    def _build_dialogue_instructions(self) -> str:
        sp = self.profile
        dialogue_info = sp.get("dialogue_features", {}) or sp.get(
            "dac_diem_doi_thoai", {}
        )
        if not dialogue_info:
            return ""

        instruction = "\n\n[ĐẶC ĐIỂM ĐỐI THOẠI CỦA TÁC PHẨM]\n"

        formality = dialogue_info.get("formality_level") or dialogue_info.get(
            "muc_do_trang_trong_chung", ""
        )
        if formality:
            instruction += f"- Mức độ trang trọng: {formality}\n"

        era_language = dialogue_info.get("era_language") or dialogue_info.get(
            "ngon_ngu_thoi_dai", ""
        )
        if era_language:
            instruction += f"- Ngôn ngữ thời đại: {era_language}\n"

        # Addressing
        addressing = dialogue_info.get("addressing") or dialogue_info.get(
            "cach_xung_ho", {}
        )
        if addressing:
            instruction += "\n**QUY TẮC XƯNG HÔ BẮT BUỘC:**\n"

            self_names = addressing.get("self_names") or addressing.get(
                "nhan_vat_xuong_minh", []
            )
            if self_names:
                names_str = (
                    ", ".join(self_names)
                    if isinstance(self_names, list)
                    else self_names
                )
                instruction += (
                    f"  - Ngôi thứ nhất: {names_str} (KHÔNG dùng 'tôi', 'mình')\n"
                )

            other_names = addressing.get("other_names") or addressing.get(
                "xung_nguoi_doi_dien", []
            )
            if other_names:
                names_str = (
                    ", ".join(other_names)
                    if isinstance(other_names, list)
                    else other_names
                )
                instruction += (
                    f"  - Ngôi thứ hai: {names_str} (KHÔNG dùng 'bạn', 'cậu')\n"
                )

            third_names = addressing.get("third_names") or addressing.get(
                "xung_nguoi_thu_ba", []
            )
            if third_names:
                names_str = (
                    ", ".join(third_names)
                    if isinstance(third_names, list)
                    else third_names
                )
                instruction += (
                    f"  - Ngôi thứ ba: {names_str} (KHÔNG dùng 'anh ấy', 'cô ấy')\n"
                )

        notable = dialogue_info.get("notable_features") or dialogue_info.get(
            "dac_diem_noi_bat", ""
        )
        if notable:
            instruction += f"\n- Đặc điểm nổi bật: {notable}\n"

        return instruction

    def _build_special_elements(self) -> str:
        sp = self.profile
        special = sp.get("special_elements", {}) or sp.get("yeu_to_dac_biet", {})
        if not special:
            return ""

        instruction = "\n\n[YẾU TỐ ĐẶC BIỆT]\n"

        cultivation_terms = special.get("cultivation_terms") or special.get(
            "thuat_ngu_tu_luyen", []
        )
        if cultivation_terms:
            terms_str = (
                ", ".join(cultivation_terms)
                if isinstance(cultivation_terms, list)
                else cultivation_terms
            )
            instruction += f"- Thuật ngữ tu luyện cần lưu ý: {terms_str}\n"

        cultural_refs = special.get("cultural_references") or special.get(
            "tham_chieu_van_hoa", []
        )
        if cultural_refs:
            refs_str = (
                ", ".join(cultural_refs)
                if isinstance(cultural_refs, list)
                else cultural_refs
            )
            instruction += f"- Tham chiếu văn hóa: {refs_str}\n"

        return instruction

    def _build_literary_usage(self) -> str:
        sp = self.profile
        style_info = sp.get("writing_style", {}) or sp.get("style", {}) or {}
        lit_usage = self._get_nested(style_info, ["literary_usage", "literary"], {})

        if not lit_usage:
            return ""

        instruction = "\n\n[SỬ DỤNG VĂN CỔ]\n"

        idioms = lit_usage.get("idioms") or lit_usage.get("thanh_ngu", "")
        if idioms:
            instruction += f"- Thành ngữ: {idioms}\n"

        poetry = lit_usage.get("poetry") or lit_usage.get("thi_phu", "")
        if poetry:
            instruction += f"- Thơ phú: {poetry}\n"

        allusions = lit_usage.get("allusions") or lit_usage.get("dien_tich", "")
        if allusions:
            instruction += f"- Điển tích: {allusions}\n"

        return instruction

    def _build_required_glossary(self) -> str:
        gu = (
            self.profile.get("translation_guidelines", {})
            or self.profile.get("guidelines", {})
            or {}
        )
        required_glossary = gu.get("required_glossary") or gu.get("tu_dien_yeu_cau", [])

        if not required_glossary:
            return ""

        instruction = "\n\n[TỪ ĐIỂN YÊU CẦU BẮT BUỘC - STRICT MAPPING]\n"
        instruction += "Các thuật ngữ dưới đây CÓ Ý NGHĨA QUAN TRỌNG, bạn PHẢI dịch chính xác theo yêu cầu:\n"

        for item in required_glossary:
            src = item.get("goc", "")
            tgt = item.get("dich", "")
            note = item.get("ghi_chu", "")
            if src and tgt:
                line = f'  - "{src}" => "{tgt}"'
                if note:
                    line += f" ({note})"
                instruction += line + "\n"

        return instruction
