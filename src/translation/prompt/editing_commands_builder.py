# -*- coding: utf-8 -*-
from __future__ import annotations

"""
EditingCommandsBuilder - Xây dựng các mệnh lệnh biên tập.

Extracted from PromptBuilder to improve modularity and maintainability.
"""


class EditingCommandsBuilder:
    """
    Xây dựng các mệnh lệnh biên tập theo document type.
    """

    def __init__(self, document_type: str, remove_redundant_instructions: bool = True):
        self.document_type = document_type.lower()
        self.remove_redundant_instructions = remove_redundant_instructions

    def build_editing_commands(self, contains_potential_title: bool) -> str:
        """
        Xây dựng các mệnh lệnh biên tập cụ thể, có cấu trúc tuần tự với ví dụ.
        Sử dụng logic tối ưu để tiết kiệm tokens.
        """
        if self.document_type == "novel":
            return self._build_novel_editing_commands_optimized(contains_potential_title)
        elif self.document_type == "medical":
            return self._build_medical_editing_commands_optimized(contains_potential_title)
        else:
            return self._build_simple_editing_commands_optimized(contains_potential_title)

    def _build_novel_editing_commands_optimized(self, contains_potential_title: bool) -> str:
        """
        Editing commands đã tối ưu - 3 Golden Rules mạnh mẽ thay vì checklist dài dòng.
        """
        commands = ["[MỆNH LỆNH BIÊN TẬP CỐT LÕI (GOLDEN RULES)]\n"]

        if contains_potential_title:
            commands.append("""1. TIÊU ĐỀ:
   - "Chương X", "Chapter X" -> [H1]Chương X...[/H1]
   - "Phần 1", "Section 1" -> [H2]...[/H2]""")
        else:
            # Fallback nếu không có title potential
            commands.append("1. CẤU TRÚC: Giữ nguyên số lượng đoạn văn (paragraph breaks).")

        commands.append("""2. HỘI THOẠI & XƯNG HÔ:
   - Các cặp quan hệ đã liệt kê -> BẮT BUỘC dùng đúng (Huynh/Muội, Ta/Nàng).
    - "X nói/hỏi/đáp" -> Chuyển thành hành động nếu lặp lại >2 lần (VD: Phượng Lăng gật đầu: "Chào đạo hữu.").

3. TINH GỌN VĂN PHONG (Anti-Redundancy):
   - Xóa các từ đệm thừa thãi: "bèn", "liền", "rồi", "thì" (trừ khi cần thiết cho mạch truyện).
   - Tách câu >40 từ thành 2 câu ngắn.
   - Không được tóm tắt nội dung.""")

        return "\n\n".join(commands)

    def _build_simple_editing_commands_optimized(self, contains_potential_title: bool) -> str:
        """
        Simple editing commands đã tối ưu.
        """
        commands = ["[MỆNH LỆNH BIÊN TẬP]\n"]

        if contains_potential_title:
            commands.append("BƯỚC 1: Tiêu đề → [H1]...[/H1]")

        commands.append("""BƯỚC 2: Kiểm tra độ dài câu (>30 từ → xem xét tách)
BƯỚC 3: Kiểm tra lặp từ (>3 lần/đoạn → thay thế)
BƯỚC 4: Kiểm tra rõ ràng (câu dễ hiểu, từ nối đúng)
BƯỚC 5: Bảo toàn định dạng (danh sách, bảng, số liệu)""")

        return "\n\n".join(commands)

    def _build_medical_editing_commands_optimized(self, contains_potential_title: bool) -> str:
        """
        Medical editing commands đã tối ưu.
        """
        commands = ["[MỆNH LỆNH BIÊN TẬP]\n"]

        if contains_potential_title:
            commands.append("BƯỚC 1: Tiêu đề → [H1]...[/H1]")

        commands.append("""BƯỚC 2: Kiểm tra thuật ngữ y học (tuân thủ glossary, tên bệnh/cơ quan/thuốc đúng chuẩn)
BƯỚC 3: Kiểm tra số liệu (giữ nguyên: liều lượng, nồng độ, đơn vị, ký hiệu)
BƯỚC 4: Kiểm tra độ dài câu (>30 từ → xem xét tách, nhưng ưu tiên rõ ràng)
BƯỚC 5: Kiểm tra rõ ràng (đặc biệt: hướng dẫn thuốc, chẩn đoán, điều trị)
BƯỚC 6: Kiểm tra cảnh báo (nhấn mạnh đúng mức, không làm mất tính quan trọng)""")

        return "\n\n".join(commands)

    def build_quality_checklist(self) -> str:
        """
        Checklist rút gọn - chỉ giữ các điểm quan trọng nhất.
        """
        if self.remove_redundant_instructions:
            # Ultra-compact version
            checklist = """[KIỂM TRA]
☑ Câu ≤35 từ, không lặp từ >2/5 câu, đoạn <150 từ
☑ Giữ paragraph breaks, không CJK/markdown
→ Chưa đạt → sửa lại"""
        else:
            # Standard compact version
            checklist = """[KIỂM TRA CHẤT LƯỢNG]
☑ Câu ≤35 từ, phân bố độ dài cân đối
☑ Không lặp từ >2 lần/5 câu, không lặp "X nói:" >2 lần/cảnh
☑ Đoạn văn <150 từ, có chuyển tiếp tự nhiên
☑ Giữ nguyên paragraph breaks như bản gốc
☑ Không còn ký tự CJK, không có định dạng markdown/chú thích
→ Nếu chưa đạt → sửa lại"""
        return checklist.strip()

    def _build_header_footer_cleanup_section_compact(self) -> str:
        """
        Cleanup section rút gọn - chỉ giữ thông tin quan trọng nhất.
        """
        return """[CLEANUP HEADER/FOOTER/PAGE NUMBER]
→ CHỈ xóa nếu CHẮC CHẮN 100%. Nếu NGHI NGỜ → GIỮ LẠI.

XÓA NẾU:
- Dòng ngắn (≤50 ký tự) + Lặp lại ≥3 lần + Ở đầu/cuối + Không có ngữ cảnh
- Số trang: "1", "Page 1", "Trang 1", "第1页" (≤20 ký tự)

KHÔNG XÓA:
- Đoạn văn dài (>50 ký tự) hoặc có ngữ cảnh
- Tiêu đề chương (pattern "Chương X", "Chapter X", "第X章")
- Đoạn văn không lặp lại hoặc có liên kết với nội dung

→ Khi NGHI NGỜ → GIỮ LẠI và DỊCH"""

    def _build_translation_command(self) -> str:
        """
        Yêu cầu dịch thuật compact — chống tóm tắt/cắt bớt.
        """
        return """
[NHIỆM VỤ DỊCH — BẮT BUỘC]
• Dịch TỪNG CÂU, ±20% độ dài gốc, giữ nguyên số đoạn văn
• Tuân thủ [QUY TẮC XƯNG HÔ] + [QUY TẮC TRẦN THUẬT]
• Hội thoại: dấu ngoặc kép "..."
• KHÔNG tóm tắt, KHÔNG ghi chú, KHÔNG giải thích
• Câu cuối phải hoàn chỉnh, có dấu câu kết thúc
"""
