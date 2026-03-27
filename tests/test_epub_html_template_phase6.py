from __future__ import annotations

from typing import Dict

from bs4 import BeautifulSoup

from src.output.epub_reinject import build_html_master


def test_build_html_master_uses_rich_template(tmp_path) -> None:
    """
    Phase 6: HTML master phải có:
    - <head> với <meta charset="utf-8"> và <title>
    - <body> chứa <main id="nt-content"> bao các <section>
    """
    chapters_html: Dict[str, str] = {
        "c1": "<html><body><h1>C1</h1><p>A</p></body></html>",
        "c2": "<html><body><h1>C2</h1><p>B</p></body></html>",
    }

    master_html = build_html_master(chapters_html, title="My Master")
    soup = BeautifulSoup(master_html, "html.parser")

    # head + meta + title
    assert soup.head is not None
    meta_charset = soup.head.find("meta", attrs={"charset": True})
    assert meta_charset is not None
    assert meta_charset["charset"].lower() == "utf-8"

    assert soup.title is not None
    assert soup.title.string == "My Master"

    # body + main
    assert soup.body is not None
    main = soup.body.find("main", id="nt-content")
    assert main is not None

    sections = main.find_all("section")
    assert len(sections) == 2

