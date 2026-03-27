import re
import sys

filepath = r"d:\My Documents\!LapTrinh\2026-0313 MTranslator\src\translation\prompt_builder.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old_code = '''    def _build_marker_preservation_instruction(self, chunk_text: str) -> str:
        """
        Xây dựng hướng dẫn bảo toàn marker cho AI.

        Args:
            chunk_text: Text của chunk (có thể chứa markers)

        Returns:
            Instruction string hoặc empty string nếu không có markers
        """
        # Kiểm tra xem chunk_text có chứa marker không
        if "[CHUNK:" in chunk_text and ":START]" in chunk_text and ":END]" in chunk_text:
            return """
⚠️ QUAN TRỌNG: BẢO TOÀN MARKER & CẤU TRÚC ĐOẠN VĂN ⚠️


1. **Bảo tồn Marker:**
   - GIỮ NGUYÊN HOÀN TOÀN các marker này. KHÔNG xóa, thay đổi, dịch, hoặc di chuyển vị trí.
   - Mỗi `[CHUNK:ID:START]` phải có một `[CHUNK:ID:END]` tương ứng.

2. **Bảo tồn Cấu trúc Đoạn văn (CỰC KỲ QUAN TRỌNG):**
   - TUYỆT ĐỐI KHÔNG gộp các đoạn văn lại với nhau.
   - PHẢI dùng 2 dấu xuống dòng (\\n\\n) để phân tách các đoạn văn rõ ràng.
   - Bản dịch PHẢI có số lượng đoạn văn tương ứng hoàn toàn với bản gốc.

🔴 QUY TẮC BẮT BUỘC:
- Nếu thấy marker dạng `[TX:id]` (ví dụ: `[TX:chapter01-0001]`), hãy GIỮ NGUYÊN HOÀN TOÀN.
- TUYỆT ĐỐI KHÔNG được chuyển đổi `[TX:id]` sang định dạng `[CHUNK:...]`.
- NHÃN `[TX:id]` là định danh đoạn văn, không phải nhãn chunk.
"""
        return ""'''

new_code = '''    def _build_marker_preservation_instruction(self, chunk_text: str) -> str:
        """
        Xây dựng hướng dẫn bảo toàn marker cho AI.
        
        Args:
            chunk_text: Text của chunk (có thể chứa markers)
            
        Returns:
            Instruction string hoặc empty string nếu không có markers
        """
        has_chunk_marker = "[CHUNK:" in chunk_text and ":START]" in chunk_text and ":END]" in chunk_text
        has_tx_marker = "[TX:" in chunk_text

        if not has_chunk_marker and not has_tx_marker:
            return ""

        instruction = "\\n⚠️ QUAN TRỌNG: BẢO TOÀN CẤU TRÚC ĐOẠN VĂN & MARKER ⚠️\\n"

        if has_chunk_marker:
            instruction += """
1. **Bảo tồn Marker CHUNK:**
   - GIỮ NGUYÊN HOÀN TOÀN các marker này. KHÔNG xóa, thay đổi, dịch, hoặc di chuyển vị trí.
   - Mỗi `[CHUNK:ID:START]` phải có một `[CHUNK:ID:END]` tương ứng.
"""

        instruction += """
2. **Bảo tồn Cấu trúc Đoạn văn (CỰC KỲ QUAN TRỌNG):**
   - TUYỆT ĐỐI KHÔNG gộp các đoạn văn lại với nhau.
   - PHẢI dùng 2 dấu xuống dòng (\\n\\n) để phân tách các đoạn văn rõ ràng.
   - Bản dịch PHẢI có số lượng đoạn văn tương ứng hoàn toàn với bản gốc.
"""

        if has_tx_marker:
            instruction += """
🔴 QUY TẮC MARKER VĂN BẢN (TEXT ID - [TX:id]):
- Nếu thấy marker dạng `[TX:id]`, hãy GIỮ NGUYÊN HOÀN TOÀN.
- Marker `[TX:id]` luôn nằm SAU đoạn văn tương đương. Hãy trả về marker y như vị trí trong bản gốc.
- TUYỆT ĐỐI KHÔNG được chuyển đổi `[TX:id]` sang định dạng `[CHUNK:...]`. KHÔNG gộp vào chunk.
"""
        return instruction'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("Replaced successfully!")
else:
    print("FAILED to replace. Original code not found.")
    
    # Try an alternative matching strategy
    print("Trying regex replacement...")
    pattern = re.compile(r'    def _build_marker_preservation_instruction\(self, chunk_text: str\) -> str:[\s\S]*?return \"\"', re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(new_code, content)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print("Regex replaced successfully!")
    else:
        print("Regex failed too.")

