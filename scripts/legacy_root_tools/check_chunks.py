import os
import re
from pathlib import Path

# Thư mục chứa các file chunk cần kiểm tra (mặc định trong repo hiện tại)
directory = str(Path(__file__).resolve().parent / 'data' / 'progress' / 'TDTTT_chunks')
files = [f for f in os.listdir(directory) if f.endswith('.txt')]

missing_end = []
anh_em = []
cjk_found = []

# CJK regex
cjk_re = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')
anh_em_re = re.compile(r'\b(anh|em)\b', re.IGNORECASE)

for filename in sorted(files, key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else 0):
    path = os.path.join(directory, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

            # Check for markers
            if '[CHUNK:' in content and 'START]' in content:
                if 'END]' not in content:
                    missing_end.append(filename)

            # Check for style
            if anh_em_re.search(content):
                anh_em.append(filename)

            # Check for CJK
            if cjk_re.search(content):
                cjk_found.append(filename)
    except Exception as e:
        print(f"Error reading {filename}: {e}")

print(f"Total files checked: {len(files)}")
print(f"Missing END markers ({len(missing_end)}): {missing_end}")
print(f"Style violations (anh/em) ({len(anh_em)}): {anh_em}")
print(f"CJK found ({len(cjk_found)}): {cjk_found}")
