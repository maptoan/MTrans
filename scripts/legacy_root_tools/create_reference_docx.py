
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor


def create_reference_docx():
    base_dir = Path(__file__).resolve().parent
    path = base_dir / "data" / "templates" / "reference.docx"
    doc = docx.Document()

    # 1. Normal Style
    style_normal = doc.styles['Normal']
    font_normal = style_normal.font
    font_normal.name = 'Times New Roman'
    font_normal.size = Pt(12)
    style_normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    style_normal.paragraph_format.first_line_indent = Pt(24) # ~2 chars
    style_normal.paragraph_format.space_after = Pt(6)

    # 2. Heading 1 (Chapter Title)
    style_h1 = doc.styles['Heading 1']
    font_h1 = style_h1.font
    font_h1.name = 'Arial'
    font_h1.size = Pt(18)
    font_h1.bold = True
    font_h1.color.rgb = RGBColor(0, 0, 0) # Black
    style_h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_h1.paragraph_format.space_before = Pt(24)
    style_h1.paragraph_format.space_after = Pt(18)
    style_h1.paragraph_format.page_break_before = True

    # 3. Heading 2 (Section)
    style_h2 = doc.styles['Heading 2']
    font_h2 = style_h2.font
    font_h2.name = 'Arial'
    font_h2.size = Pt(16)
    font_h2.bold = True
    font_h2.color.rgb = RGBColor(0, 0, 0)
    style_h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    style_h2.paragraph_format.space_before = Pt(18)
    style_h2.paragraph_format.space_after = Pt(12)

    # 4. Heading 3 (Subsection)
    style_h3 = doc.styles['Heading 3']
    font_h3 = style_h3.font
    font_h3.name = 'Arial'
    font_h3.size = Pt(14)
    font_h3.bold = False
    font_h3.italic = True
    font_h3.color.rgb = RGBColor(50, 50, 50)
    style_h3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Save
    doc.save(str(path))
    print(f"Created reference.docx at {path}")

if __name__ == "__main__":
    create_reference_docx()
