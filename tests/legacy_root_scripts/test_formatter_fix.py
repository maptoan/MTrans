# -*- coding: utf-8 -*-
import io
import os
import sys

# Fix encoding cho terminal Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Thêm đường dẫn để import module
sys.path.append(os.path.abspath("."))

from src.output.formatter import OutputFormatter


def test_issues():
    config = {
        "output": {
            "formats": ["txt"],
            "preferred_chapter_term": "Hồi", # Thử nghiệm thống nhất tất cả thành "Hồi"
            "preferred_volume_term": "Tập",
            "epub_options": {
                "cover_image_path": "data/input/cover.jpg"
            }
        }
    }
    formatter = OutputFormatter(config)

    test_cases = [
        # Issue 1 & 3: Xóa mất tiêu đề và không sửa hết số thứ tự bằng chữ
        ("Hồi thứ tư: Nước ngập ma hang", "[H1]Hồi 4: Nước Ngập Ma Hang[/H1]"),

        # Issue 2: Nhận diện sai cụm từ thường là Heading 1 (False Positive)
        ("- Hồi lâu sau, mới nghe Phi La bảo: “Tiểu gia hỏa, cũng khá đấy chứ…”", "- Hồi lâu sau, mới nghe Phi La bảo: “Tiểu gia hỏa, cũng khá đấy chứ…”"),

        # Issue 4: Viết lặp "Hồi hồi", "Chương chương"
        ("Hồi 9", "[H1]Hồi 9[/H1]"),
        ("Chương 10", "[H1]Hồi 10[/H1]"), # Chương được đổi thành Hồi theo config
        ("Tập 6", "[H1]Tập 6[/H1]"),

        # Issue 5: Viết hoa toàn bộ (ALL CAPS) -> Title Case
        ("Hồi 9: BÍ ẨN DI TÍCH", "[H1]Hồi 9: Bí Ẩn Di Tích[/H1]"),
        ("Quyển 2: CÔ ĐẢO XUÂN SẮC", "[H1]Tập 2: Cô Đảo Xuân Sắc[/H1]"), # Quyển -> Tập và Title Case

        # Issue 6: Thuật ngữ không đồng nhất (Unification)
        ("Chương chương: 10", "[H1]Hồi 10[/H1]"),
        ("Hồi hồi: chín", "[H1]Hồi 9[/H1]"),

        # Issue 7: Tiêu đề bị xuống dòng (Gom dòng)
        ("[H1]Chương 1[/H1]\nMở đầu", "[H1]Hồi 1: Mở Đầu[/H1]"),
        ("Hồi thứ mười\nTrận chiến cuối cùng", "[H1]Hồi 10: Trận Chiến Cuối Cùng[/H1]"),
        ("Chương 2: \nSóng gió nổi lên", "[H1]Hồi 2: Sóng Gió Nổi Lên[/H1]"),
    ]

    print("--- TESTING OUTPUT FORMATTER ISSUES ---")
    all_passed = True
    for input_text, expected in test_cases:
        # Giả lập input là một đoạn văn bản
        result = formatter._normalize_paragraphs(input_text)
        if result != expected:
            print("FAILED:")
            print(f"  Input:    {input_text}")
            print(f"  Expected: {expected}")
            print(f"  Actual:   {result}")
            all_passed = False
        else:
            print(f"PASSED: {input_text} -> {result}")

    if all_passed:
        print("\n✅ Mọi test case đã vượt qua (hoặc lỗi đã được sửa)!")
    else:
        print("\n❌ Có lỗi cần khắc phục.")

if __name__ == "__main__":
    test_issues()
