# -*- coding: utf-8 -*-
from __future__ import annotations

"""
GuidelinesBuilder - Xây dựng các guidelines theo document type.

Extracted from PromptBuilder to improve modularity and maintainability.
"""

from typing import Any, Dict


class GuidelinesBuilder:
    """
    Xây dựng các nguyên tắc dịch thuật theo loại tài liệu.
    """

    def __init__(self, document_type: str, config: Dict[str, Any] = None, style_manager=None):
        self.document_type = document_type.lower()
        self.config = config or {}
        self.style_manager = style_manager

    def build_guidelines(self) -> str:
        """
        Xây dựng các nguyên tắc phù hợp với loại tài liệu.
        """
        if self.document_type == "novel":
            return self._build_literary_guidelines()
        elif self.document_type == "technical_doc":
            return self._build_technical_guidelines()
        elif self.document_type == "academic_paper":
            return self._build_academic_guidelines()
        elif self.document_type == "manual":
            return self._build_manual_guidelines()
        elif self.document_type == "medical":
            return self._build_medical_guidelines()
        else:  # general
            return self._build_general_guidelines()

    def _is_nonfiction(self) -> bool:
        """Detect if the current task is Non-Fiction based on Style Profile."""
        if not self.style_manager or not self.style_manager.is_loaded():
            return False
        p = self.style_manager.profile
        # Check for unique Non-Fiction keys
        if "technical_style" in p or "narrative_style" in p or "core_message" in p:
            return True
        # Check doc_info field
        info = p.get("doc_info", {}) or p.get("novel_info", {})
        genre = info.get("genre", "") or info.get("field", "")
        if any(
            k in str(genre).lower()
            for k in [
                "technical",
                "manual",
                "doc",
                "hồi ký",
                "non-fiction",
                "kinh tế",
                "y học",
                "lập trình",
                "giáo trình",
            ]
        ):
            return True
        return False

    def _build_nonfiction_guidelines(self) -> str:
        """
        Guidelines tối ưu cho Non-Fiction (Show, Don't Tell version).
        Phân biệt rõ Technical vs Narrative.
        """
        guidelines = """
[NGUYÊN TẮC DỊCH NON-FICTION]

1. ĐỘ CHÍNH XÁC (Accuracy):
❌ Vague: "Hệ thống chạy nhanh hơn."
✅ Precise: "Hệ thống đạt hiệu suất cao hơn 20%." (Nếu source có số liệu)
✅ Precise: "Hệ thống vận hành tối ưu hơn." (Nếu context là technical)

2. THUẬT NGỮ (Terminology):
❌ Mixed: "Sử dụng API interface để kết nối."
✅ Technical: "Sử dụng giao diện API để kết nối." (Hoặc giữ nguyên API nếu là chuẩn chung)
-> Ưu tiên tuân thủ Glossary. Nếu không có trong Glossary, hãy dùng thuật ngữ chuyên ngành chuẩn tiếng Việt.

3. CẤU TRÚC (Clarity):
❌ Run-on: "Python là ngôn ngữ tốt mà dễ học và nó có nhiều thư viện."
✅ Clear: "Python là ngôn ngữ mạnh mẽ, dễ học và sở hữu hệ sinh thái thư viện phong phú."

4. PHONG CÁCH (Tone):
- Narrative (Hồi ký/Business): Giữ giọng điệu kể chuyện, truyền cảm hứng nhưng không sến súa.
- Technical (Manual/Docs): Khách quan, súc tích, trực diện (Imperative mood cho hướng dẫn).
"""
        return guidelines.strip()

    def _build_literary_guidelines(self) -> str:
        """
        Xây dựng các nguyên tắc nền tảng về tính văn học theo phong cách "Show, Don't Tell".
        OPTIMIZED: Thay thế lý thuyết dài dòng bằng Example Matrix để AI học pattern.
        """
        if self._is_nonfiction():
            return self._build_nonfiction_guidelines()
        guidelines = """
[PHONG CÁCH VĂN HỌC MẪU - HÃY BẮT CHƯỚC]

1. NHỊP ĐIỆU & CẤU TRÚC (Rhythm):
❌ Monotone: "Cô dừng lại và thấy ánh nến lập lòe trong căn phòng tối, bóng người anh in rõ trên đường, nhưng chẳng ai lên tiếng."
✅ Dynamic: "Cô dừng lại. Ánh nến lập lòe trong phòng tối. Bóng anh in rõ trên tường. Chẳng ai lên tiếng."

2. TỐI ƯU HÀNH ĐỘNG (Action):
❌ Clumsy: "Anh bèn quay người, rồi liền bước ra ngoài, vẻ mặt tỏ ra khó chịu."
✅ Sharp: "Anh quay người, bước ra ngoài. Vẻ mặt khó chịu."

3. HỘI THOẠI (Dialogue Attributes):
❌ Repetitive: 
   "Ngươi định làm gì?" Phượng Lăng nói.
   "Từ chối." La Bích nói.
   "Được." Anh nói.
✅ Vivid: 
   "Ngươi định làm gì?" Phượng Lăng nhíu mày.
   "Từ chối."
   Anh gật đầu: "Được."

4. TRÁNH LẶP TỪ (Redundancy):
❌ Repetitive: "La Bích không muốn đi. La Bích thà ở nhà còn hơn."
✅ Natural: "La Bích không muốn đi. Cô thà ở nhà còn hơn."

5. XƯNG HÔ (Addressing):
❌ Thô sơ/Hiện đại: "Tôi không sao. Anh đi đi."
✅ Phù hợp bối cảnh: "Ta không sao. Huynh đi đi."
🚨 QUY TẮC CỨNG: Cấm dùng xưng hô "anh-em" cho các quan hệ xã giao, quan trường hoặc người lạ. Chỉ dùng "anh-em" khi thực sự là cặp đôi/vợ chồng tình cảm hiện đại. Đối với truyện quan trường/cổ đại, ưu tiên: Ta-Ngươi, Huynh-Muội, Bản quan-Hạ quan.
"""
        # Append Genre & Formatting Guidelines
        guidelines += "\n" + self._build_genre_guidelines()
        guidelines += "\n" + self._build_formatting_guidelines()

        return guidelines.strip()

    def _build_technical_guidelines(self) -> str:
        """
        Xây dựng các nguyên tắc cho tài liệu kỹ thuật.
        """
        guidelines = """
[NGUYÊN TẮC DỊCH TÀI LIỆU KỸ THUẬT]

1. CHÍNH XÁC VỀ THUẬT NGỮ:
   - TUYỆT ĐỐI tuân thủ glossary - không được tự ý thay đổi thuật ngữ.
   - Giữ nguyên thuật ngữ kỹ thuật chính xác, không "dịch sáng tạo".
   - Nếu có thuật ngữ mới chưa có trong glossary, dịch theo nghĩa kỹ thuật chuẩn.

2. RÕ RÀNG VÀ DỄ HIỂU:
   - Câu văn rõ ràng, tránh câu quá dài (>30 từ).
   - Sử dụng cấu trúc câu đơn giản, dễ hiểu.
   - Tránh từ ngữ mơ hồ, ưu tiên từ ngữ cụ thể.

3. GIỮ NGUYÊN CẤU TRÚC:
   - Giữ nguyên cấu trúc danh sách, bảng biểu, số liệu.
   - Bảo toàn định dạng kỹ thuật (mã lệnh, tên biến, số phiên bản).
   - Giữ nguyên thứ tự các bước trong quy trình.

4. TRÁNH VĂN PHONG VĂN HỌC:
   - KHÔNG sử dụng từ ngữ hoa mỹ, ẩn dụ, so sánh không cần thiết.
   - Ưu tiên văn phong khách quan, trung tính.
   - Tránh câu văn quá ngắn gọn kiểu văn học (trừ khi cần nhấn mạnh).

5. NHẤT QUÁN:
   - Sử dụng cùng một thuật ngữ cho cùng một khái niệm xuyên suốt tài liệu.
   - Giữ nguyên cách viết tên riêng, tên sản phẩm, tên công ty.
"""
        return guidelines.strip()

    def _build_academic_guidelines(self) -> str:
        """
        Xây dựng các nguyên tắc cho bài báo khoa học.
        """
        guidelines = """
[NGUYÊN TẮC DỊCH BÀI BÁO KHOA HỌC]

1. VĂN PHONG HỌC THUẬT:
   - Sử dụng văn phong formal, khách quan, chuyên nghiệp.
   - Tránh ngôn ngữ đời thường, tiếng lóng, từ ngữ không trang trọng.
   - Ưu tiên câu văn hoàn chỉnh, có cấu trúc rõ ràng.

2. CHÍNH XÁC VỀ THUẬT NGỮ KHOA HỌC:
   - TUYỆT ĐỐI tuân thủ glossary và thuật ngữ khoa học chuẩn.
   - Giữ nguyên tên khoa học (Latin), công thức, ký hiệu.
   - Dịch thuật ngữ theo từ điển chuyên ngành, không tự sáng tạo.

3. BẢO TOÀN THÔNG TIN:
   - Giữ nguyên số liệu, đơn vị đo lường, công thức.
   - Bảo toàn cấu trúc bảng biểu, biểu đồ, hình ảnh mô tả.
   - Giữ nguyên cách trích dẫn tài liệu tham khảo.

4. CẤU TRÚC CÂU HỌC THUẬT:
   - Câu văn có thể dài hơn (20-40 từ) nhưng phải rõ ràng về logic.
   - Sử dụng mệnh đề quan hệ, mệnh đề phụ để thể hiện mối quan hệ phức tạp.
   - Tránh câu quá ngắn gọn, thiếu thông tin.

5. TRÁNH DIỄN ĐẠT CÁ NHÂN:
   - KHÔNG thêm ý kiến cá nhân, cảm xúc vào bản dịch.
   - Giữ nguyên giọng điệu khách quan của tác giả gốc.
   - Tránh từ ngữ mang tính cảm xúc, chủ quan.
"""
        return guidelines.strip()

    def _build_manual_guidelines(self) -> str:
        """
        Xây dựng các nguyên tắc cho sách hướng dẫn.
        """
        guidelines = """
[NGUYÊN TẮC DỊCH SÁCH HƯỚNG DẪN]

1. RÕ RÀNG VÀ DỄ HIỂU:
   - Câu văn ngắn gọn, rõ ràng, dễ hiểu cho người dùng phổ thông.
   - Tránh câu quá dài (>25 từ) - chia nhỏ nếu cần.
   - Sử dụng từ ngữ thông dụng, tránh thuật ngữ quá chuyên sâu (trừ khi bắt buộc).

2. HƯỚNG DẪN TỪNG BƯỚC:
   - Giữ nguyên thứ tự các bước trong quy trình.
   - Sử dụng từ ngữ chỉ thị rõ ràng: "Bước 1:", "Tiếp theo:", "Cuối cùng:".
   - Đảm bảo mỗi bước có thể thực hiện độc lập.

3. NHẤN MẠNH THÔNG TIN QUAN TRỌNG:
   - Giữ nguyên các cảnh báo, lưu ý, mẹo.
   - Sử dụng từ ngữ nhấn mạnh phù hợp: "QUAN TRỌNG:", "LƯU Ý:", "CẢNH BÁO:".
   - Tránh làm mất đi tính nhấn mạnh của thông tin quan trọng.

4. THÂN THIỆN VỚI NGƯỜI DÙNG:
   - Sử dụng đại từ "bạn", "bạn có thể" thay vì "người dùng", "người đọc".
   - Văn phong thân thiện nhưng vẫn chuyên nghiệp.
   - Tránh ngôn ngữ quá formal hoặc quá informal.

5. BẢO TOÀN ĐỊNH DẠNG:
   - Giữ nguyên cấu trúc danh sách, bảng, hình ảnh mô tả.
   - Bảo toàn mã lệnh, tên file, đường dẫn, số phiên bản.
   - Giữ nguyên cách đánh số bước, mục, tiểu mục.
"""
        return guidelines.strip()

    def _build_medical_guidelines(self) -> str:
        """
        Xây dựng các nguyên tắc cho tài liệu y học.
        """
        guidelines = """
[NGUYÊN TẮC DỊCH TÀI LIỆU Y HỌC]

1. CHÍNH XÁC TUYỆT ĐỐI VỀ THUẬT NGỮ Y HỌC:
   - TUYỆT ĐỐI tuân thủ glossary - không được tự ý thay đổi thuật ngữ y học.
   - Sử dụng thuật ngữ y học chuẩn theo từ điển y học Việt Nam.
   - Tên bệnh: Dịch theo tên bệnh chuẩn (ví dụ: "hypertension" → "tăng huyết áp", không phải "cao huyết áp").
   - Tên cơ quan: Dịch theo tên giải phẫu chuẩn (ví dụ: "heart" → "tim", "liver" → "gan").
   - Tên thuốc: 
     * Tên thương mại: Giữ nguyên (ví dụ: "Aspirin", "Paracetamol")
     * Tên hoạt chất: Dịch theo tên gốc hoặc giữ nguyên nếu là tên quốc tế
     * Tên Latin: Giữ nguyên (ví dụ: "E. coli", "Staphylococcus aureus")

2. BẢO TOÀN SỐ LIỆU Y HỌC:
   - TUYỆT ĐỐI giữ nguyên tất cả số liệu: liều lượng, nồng độ, thời gian, tỷ lệ phần trăm.
   - Giữ nguyên đơn vị đo lường: mg, ml, g, %, mmol/L, IU, v.v.
   - Giữ nguyên các ký hiệu y học: >, <, ≥, ≤, ±, v.v.
   - Ví dụ: "500 mg twice daily" → "500 mg hai lần mỗi ngày" (KHÔNG đổi "500 mg" thành "năm trăm miligam")

3. VĂN PHONG PHÙ HỢP:
   - Với bài báo y học: Văn phong formal, khách quan, học thuật.
   - Với hướng dẫn bệnh nhân: Văn phong rõ ràng, dễ hiểu, thân thiện nhưng vẫn chính xác.
   - Tránh từ ngữ mơ hồ, ưu tiên từ ngữ cụ thể, chính xác.
   - Câu văn rõ ràng, tránh câu quá dài (>30 từ).

4. BẢO TOÀN CẤU TRÚC Y HỌC:
   - Giữ nguyên cấu trúc danh sách triệu chứng, chẩn đoán, điều trị.
   - Bảo toàn định dạng bảng biểu (bảng thuốc, bảng xét nghiệm).
   - Giữ nguyên cách trích dẫn tài liệu y học (tên tạp chí, năm, volume, page).
   - Bảo toàn các ký hiệu và công thức y học.

5. XỬ LÝ TÊN RIÊNG Y HỌC:
   - Tên bác sĩ, nhà nghiên cứu: Giữ nguyên hoặc dịch âm theo chuẩn.
   - Tên bệnh viện, tổ chức y tế: Giữ nguyên hoặc dịch theo tên chính thức.
   - Tên hội chứng, phương pháp: Dịch theo tên chuẩn (ví dụ: "Down syndrome" → "Hội chứng Down").
   - Tên xét nghiệm: Dịch theo tên chuẩn hoặc giữ nguyên nếu là tên viết tắt quốc tế (ví dụ: "CT scan" → "chụp CT").

6. TRÁNH DIỄN ĐẠT CÁ NHÂN:
   - KHÔNG thêm ý kiến cá nhân, cảm xúc vào bản dịch.
   - Giữ nguyên giọng điệu khách quan, khoa học của tác giả gốc.
   - Tránh từ ngữ mang tính cảm xúc, chủ quan (trừ khi là hướng dẫn bệnh nhân cần thân thiện).

7. NHẤT QUÁN:
   - Sử dụng cùng một thuật ngữ cho cùng một khái niệm xuyên suốt tài liệu.
   - Ví dụ: Nếu đã dịch "diabetes" là "đái tháo đường" thì phải dùng nhất quán, không đổi thành "tiểu đường" ở chỗ khác.
   - Tuân thủ glossary một cách tuyệt đối.

8. XỬ LÝ ĐẶC BIỆT:
   - Cảnh báo, chống chỉ định: Giữ nguyên tính nhấn mạnh và rõ ràng.
   - Hướng dẫn sử dụng thuốc: Rõ ràng, dễ hiểu, không gây nhầm lẫn.
   - Thông tin an toàn: Nhấn mạnh đúng mức, không làm mất đi tính quan trọng.
"""
        return guidelines.strip()

    def _build_general_guidelines(self) -> str:
        """
        Xây dựng các nguyên tắc cho tài liệu tổng quát.
        """
        guidelines = """
[NGUYÊN TẮC DỊCH TÀI LIỆU TỔNG QUÁT]

1. CÂN BẰNG TỰ NHIÊN VÀ CHÍNH XÁC:
   - Văn phong tự nhiên, dễ đọc nhưng vẫn chính xác về nội dung.
   - Câu văn rõ ràng, tránh câu quá dài (>30 từ) hoặc quá ngắn (<5 từ).
   - Sử dụng từ ngữ phù hợp với ngữ cảnh.

2. TUÂN THỦ THUẬT NGỮ:
   - Tuân thủ glossary nếu có.
   - Sử dụng thuật ngữ nhất quán xuyên suốt tài liệu.
   - Dịch thuật ngữ theo nghĩa chuẩn, không tự sáng tạo.

3. BẢO TOÀN CẤU TRÚC:
   - Giữ nguyên cấu trúc đoạn văn, danh sách, bảng biểu.
   - Bảo toàn định dạng đặc biệt (in đậm, in nghiêng, số liệu).
   - Giữ nguyên thứ tự thông tin.

4. TRÁNH LẶP TỪ:
   - Tránh lặp lại từ/cụm từ quá nhiều trong cùng đoạn (>2 lần).
   - Sử dụng từ đồng nghĩa hoặc đại từ khi phù hợp.
   - Ưu tiên sự đa dạng trong cách diễn đạt.

5. PHÙ HỢP VỚI NGỮ CẢNH:
   - Điều chỉnh văn phong theo từng phần của tài liệu (phần giới thiệu, phần kỹ thuật, phần kết luận).
   - Giữ nguyên giọng điệu của tác giả gốc (formal/informal, khách quan/cá nhân).
   - Đảm bảo tính nhất quán về văn phong trong toàn bộ tài liệu.
"""
        return guidelines.strip()

    def _build_genre_guidelines(self) -> str:
        """
        Xây dựng hướng dẫn theo thể loại (Genre).
        """
        genre = self.config.get("translation", {}).get("novel_genre", "general").lower()
        if genre in ["xianxia", "tienhiep", "cultivation", "huyenhuyen"]:
            return """
[HƯỚNG DẪN THỂ LOẠI: TIÊN HIỆP / HUYỀN HUYỄN]

1. THUẬT NGỮ TU TIÊN:
   - Giữ nguyên Hán-Việt cho các cõi tu vi, pháp bảo, đan dược (Trúc Cơ, Nguyên Anh, Linh thạch).
   - KHÔNG dịch nghĩa đen các chiêu thức (Vd: "Liệt Hỏa Chưởng" giữ nguyên, không dịch "Bàn tay lửa").
   - Giữ chất "cổ phong" trong từ ngữ mô tả.

2. KHÔNG KHÍ & SẮC THÁI:
   - Duy trì giọng văn hùng tráng, cổ kính.
   - Tránh từ ngữ quá hiện đại/đời thường (Vd: không dùng "OK", "tạm biệt", "xin chào" -> dùng "Hảo", "cáo từ", "hội ngộ").
   - Quan trọng: Dùng từ "đạo hữu", "tiền bối", "vãn bối" thay cho "anh/chị/em" khi phù hợp ngữ cảnh tu tiên.
"""
        return ""

    def _build_formatting_guidelines(self) -> str:
        """
        Xây dựng hướng dẫn định dạng bắt buộc (Formatting).
        Chỉ giữ rules unique — CJK/dialogue/title đã covered ở guardrail/editing commands.
        """
        return """
[QUY TẮC ĐỊNH DẠNG VĂN BẢN]

1. KHOẢNG CÁCH ĐOẠN (SPACING):
   - Giữ nguyên các dòng trống ngăn cách giữa các đoạn văn.
   - Mỗi đoạn văn cách nhau 1 dòng trống (double newline \\n\\n).
   - KHÔNG viết dính liền các đoạn văn lại với nhau.
"""

    def _build_verb_variation_guide(self) -> str:
        """
        Hướng dẫn đa dạng hóa động từ thường gặp.
        """
        guide = """
[BỘ TỪ ĐIỂN THAY THẾ ĐỘNG TỪ]

Để tránh lặp động từ, sử dụng các từ đồng nghĩa phù hợp:

THAY CHO "nói": đáp, giải thích, buột miệng, thì thầm, gằn giọng, trả lời, lên tiếng, bật ra
THAY CHO "đi": bước, tiến, lướt, sải, rảo, di chuyển, bước đi, tiến lên
THAY CHO "nhìn": liếc, ngắm, nhìn chằm chằm, dán mắt, ngó, lướt mắt, đảo mắt, nheo mắt
THAY CHO "nghĩ": suy ngẫm, trầm ngâm, trăn trở, cân nhắc, băn khoăn, suy nghĩ
THAY CHO "cầm": nắm, túm, vịn, giữ, ôm, bưng
THAY CHO "ngồi": vào chỗ, ngồi xuống, ngồi phịch, ngồi thụp

LƯU Ý QUAN TRỌNG: 
- Chỉ thay thế khi phù hợp ngữ cảnh và sắc thái cảm xúc.
- KHÔNG thay thế máy móc hoặc làm mất đi ý nghĩa gốc.
- Ưu tiên giữ nguyên nếu từ gốc đã phù hợp nhất.
"""
        return guide.strip()
