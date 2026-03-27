
import csv
import os
import random

from PIL import Image, ImageDraw, ImageFont

# config
OUTPUT_DIR = "data/profiling_dummy"
NOVEL_FILE = os.path.join(OUTPUT_DIR, "dummy_novel.txt")
GLOSSARY_FILE = os.path.join(OUTPUT_DIR, "dummy_glossary.csv")
IMAGE_FILE = os.path.join(OUTPUT_DIR, "dummy_page.png")

# Ensure dir
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_novel(num_chars=3000): # Approx 2000 tokens
    """Generate dummy Chinese novel text with repeating patterns and glossary terms."""
    base_text = "传说在遥远的东方，有一位名叫{name}的修仙者。他手持{weapon}，身穿{armor}，行走在{place}。"
    terms = {
        "name": ["萧炎", "林动", "牧尘", "唐三"],
        "weapon": ["玄重尺", "天妖傀", "大荒芜碑", "海神三叉戟"],
        "armor": ["帝炎甲", "祖符之铠", "灵力衣", "蓝银皇甲"],
        "place": ["乌坦城", "大荒郡", "北灵境", "斗罗大陆"]
    }
    
    content = []
    current_chars = 0
    while current_chars < num_chars:
        # Random fill
        sentence = base_text.format(
            name=random.choice(terms["name"]),
            weapon=random.choice(terms["weapon"]),
            armor=random.choice(terms["armor"]),
            place=random.choice(terms["place"])
        )
        # Add some filler
        sentence += " 天地灵気涌动，风云变色。" * 2
        content.append(sentence)
        current_chars += len(sentence)
        
    with open(NOVEL_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(content))
    print(f"Generated {NOVEL_FILE} ({os.path.getsize(NOVEL_FILE)} bytes)")

def generate_glossary(num_terms=100):
    """Generate dummy glossary csv."""
    headers = ["Original_Term_CN", "Original_Term_Pinyin", "Original_Term_EN", "Translated_Term_VI", "Type", "Notes"]
    
    with open(GLOSSARY_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        # Add core terms matching novel
        core_terms = [
            ["萧炎", "Xiao Yan", "Xiao Yan", "Tiêu Viêm", "Character", "Main char"],
            ["林动", "Lin Dong", "Lin Dong", "Lâm Động", "Character", "Main char"],
            ["玄重尺", "Xuan Zhong Chi", "Heavy Ruler", "Huyền Trọng Thước", "Item", "Weapon"],
            ["乌坦城", "Wu Tan Cheng", "Wu Tan City", "Ô Thản Thành", "Place", "City"],
        ]
        writer.writerows(core_terms)
        
        # Fill rest
        for i in range(num_terms - len(core_terms)):
            writer.writerow([
                f"术语{i}", f"Shu Yu {i}", f"Term {i}", f"Thuật ngữ {i}", "Skill", ""
            ])
            
    print(f"Generated {GLOSSARY_FILE} with {num_terms} terms")

def generate_image():
    """Generate simple image with text for OCR."""
    img = Image.new('RGB', (800, 1000), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Try to load a default font, otherwise use default
    try:
        # Check windows fonts
        font_path = "C:/Windows/Fonts/msyh.ttc" # Microsoft YaHei (Chinese)
        if os.path.exists(font_path):
             font = ImageFont.truetype(font_path, 20)
        else:
             font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
        
    text = """
    Chapter 1: The Beginning
    
    这是一个测试页面。
    This is a test page for OCR profiling.
    
    Content should be detected clearly.
    1234567890
    """
    
    d.text((50, 50), text, fill=(0, 0, 0), font=font)
    img.save(IMAGE_FILE)
    print(f"Generated {IMAGE_FILE}")

if __name__ == "__main__":
    generate_novel()
    generate_glossary()
    generate_image()
