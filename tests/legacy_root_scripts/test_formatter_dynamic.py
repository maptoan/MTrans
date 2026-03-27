import os
import sys
from unittest.mock import MagicMock

from src.output.formatter import OutputFormatter

# Mock Config
config = {"output": {"output_path": "data/output_test/", "styles": {"epub_css": "data/templates/epub.css"}}}

# Mock StyleManager
mock_style_manager = MagicMock()
mock_style_manager.is_loaded.return_value = True
mock_style_manager.get_full_profile.return_value = {"writing_style": {"tone": {"pacing": "chậm (slow)"}}}

# Test
os.makedirs("data/output_test/", exist_ok=True)
formatter = OutputFormatter(config, style_manager=mock_style_manager)
css_path = formatter._generate_dynamic_css()

print(f"Dynamic CSS Path: {css_path}")

if css_path and os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        print(f"Content:\n{f.read()}")
else:
    print("Failed to generate CSS")

# Test build args
args = formatter._build_pandoc_args("TestNovel", {})
print(f"Pandoc Args: {args}")
