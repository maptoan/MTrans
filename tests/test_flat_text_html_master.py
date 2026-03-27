from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from src.output.html_master_builder import build_html_master_from_flat_text


def test_build_html_master_from_flat_text_creates_sections_and_headings() -> None:
    """
    Phase 7: Từ TXT tổng với [H1]/[H2]/[H3] tạo master.html với section + h1/p chuẩn.
    """
    full_text = """
[H1]Chương 1: Mở đầu[/H1]
Đoạn 1.

Đoạn 2.

[H1]Chương 2[/H1]
Đoạn 3.
"""

    html = build_html_master_from_flat_text(full_text, title="Test Novel")
    soup = BeautifulSoup(html, "html.parser")

    # Kiểm tra skeleton HTML cơ bản
    assert soup.html is not None
    assert soup.head is not None
    assert soup.body is not None
    assert soup.title is not None
    assert soup.title.string == "Test Novel"

    main = soup.body.find("main", id="nt-content")
    assert main is not None

    sections = main.find_all("section")
    assert len(sections) == 2

    # Section 1
    s1 = sections[0]
    h1_1 = s1.find("h1")
    assert h1_1 is not None
    assert h1_1.get("data-role") == "chapter-title"
    assert "Chương 1" in h1_1.get_text()

    paras_1: List[str] = [p.get_text(strip=True) for p in s1.find_all("p")]
    assert paras_1 == ["Đoạn 1.", "Đoạn 2."]

    # Section 2
    s2 = sections[1]
    h1_2 = s2.find("h1")
    assert h1_2 is not None
    assert h1_2.get("data-role") == "chapter-title"
    assert "Chương 2" in h1_2.get_text()

    paras_2: List[str] = [p.get_text(strip=True) for p in s2.find_all("p")]
    assert paras_2 == ["Đoạn 3."]

