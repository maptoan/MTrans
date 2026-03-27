# -*- coding: utf-8 -*-
import logging
import os
import sys

# Thêm thư mục gốc vào path để import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.preprocessing.chunker import SmartChunker

# Giả lập logger
logging.basicConfig(level=logging.INFO)

def reproduce():
    config = {
        "preprocessing": {
            "chunking": {
                "max_chunk_tokens": 15,  # Giới hạn cực nhỏ để ép cắt
                "safety_ratio": 1.0,
                "enable_balancing": False 
            }
        },
        "translation": {
            "default_model": "flash"
        }
    }
    
    # Văn bản lắt léo
    text = (
        "Dòng 1: Đây là một câu có dấu ngoặc kép “Anh ấy nói: Chào bạn.” và nó chưa hết. "
        "Dòng 2: Câu này có chữ viết tắt như v.v. và vẫn tiếp tục. "
        "Dòng 3: Đang suy nghĩ... chúng ta có nên đi không? "
        "Dòng 4: Kết thúc ở đây."
    )
    
    chunker = SmartChunker(config)
    chunks = chunker.chunk_novel(text)
    
    print(f"\n--- KẾT QUẢ CHIA CHUNK (Tổng {len(chunks)} chunks) ---")
    for i, chunk in enumerate(chunks):
        content = chunk['text_original'].strip()
        print(f"\nCHUNK {i} (Tokens: {chunk['tokens']}):")
        print(f"NỘI DUNG: '{content}'")
        last_char = content[-1] if content else ""
        print(f"KẾT THÚC BẰNG: '{last_char}'")
        if last_char not in ".!?。！？”’」』》":
            print("⚠️ CẢNH BÁO: Chunk bị cắt ở ranh giới không an toàn!")

if __name__ == "__main__":
    reproduce()
