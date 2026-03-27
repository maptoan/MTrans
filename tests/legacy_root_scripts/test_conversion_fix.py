import logging
import os

from PIL import Image

from src.output.formatter import OutputFormatter

# Mock success level for testing
logging.Logger.success = lambda self, msg, *args, **kwargs: self.info(f"[SUCCESS] {msg}", *args, **kwargs)
logging.Logger.save = lambda self, msg, *args, **kwargs: self.info(f"[SAVE] {msg}", *args, **kwargs)


# Setup dummy environment
os.makedirs("data/test_output", exist_ok=True)
dummy_cover = "data/test_output/cover.jpg"
img = Image.new('RGB', (600, 800), color = 'red')
img.save(dummy_cover)

config = {
    'output': {
        'output_path': 'data/test_output',
        'formats': ['docx', 'pdf', 'txt'],
        'epub_options': {
            'cover_image_path': os.path.abspath(dummy_cover),
            'epub_title': 'Test Novel',
            'epub_author': 'Tester'
        }
    }
}

formatter = OutputFormatter(config)
content = """[H1]Chương 1: Test Title[/H1]
Đây là nội dung chương 1.
[H2]Phần 1[/H2]
Nội dung phần 1.
"""

print("Running save...")
formatter.save(content, "Test_Novel")

print("Checking outputs...")
base = "data/test_output/Test_Novel_translated"
if os.path.exists(f"{base}.docx"):
    print("[PASS] DOCX created")
else:
    print("[FAIL] DOCX missing")

if os.path.exists(f"{base}.pdf"):
    print("[PASS] PDF created")
else:
    print("[FAIL] PDF missing")
