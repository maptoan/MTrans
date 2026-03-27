# -*- coding: utf-8 -*-
"""
Script to fix CJK regex pattern in refiners.py and cjk_cleaner.py
"""

# Correct CJK pattern (single backslash for proper Unicode)
CORRECT_PATTERN = r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+'

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Fix refiners.py (trong repo hiện tại)
refiners_path = PROJECT_ROOT / 'src' / 'translation' / 'refiners.py'
with open(refiners_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the buggy pattern
old_pattern_line = r'r"[\\u4e00-\\u9fff\\u3400-\\u4dbf\\u20000-\\u2a6df\\u2a700-\\u2b73f\\u2b740-\\u2b81f\\u2b820-\\u2ceaf\\uf900-\\ufaff\\u2f800-\\u2fa1f]+"'
new_pattern_line = f"r'{CORRECT_PATTERN}'"

content = content.replace(old_pattern_line, new_pattern_line)

with open(refiners_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"OK Fixed {refiners_path}")

# Fix cjk_cleaner.py
cleaner_path = PROJECT_ROOT / 'src' / 'translation' / 'cjk_cleaner.py'
with open(cleaner_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(old_pattern_line, new_pattern_line)

with open(cleaner_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"OK Fixed {cleaner_path}")
