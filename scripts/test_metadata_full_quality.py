#!/usr/bin/env python3
"""
Test script để đánh giá chất lượng metadata với dữ liệu lớn hơn
"""

import asyncio
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.gemini_api_service import GeminiAPIService


def load_config():
    """Load configuration"""
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_prompt(prompt_file):
    """Load prompt from file"""
    with open(f'prompts/notebooklm/{prompt_file}', 'r', encoding='utf-8') as f:
        return f.read()

def load_large_sample_novel():
    """Load larger sample novel text for testing"""
    sample_text = """
    第一章：玄教弟子
    
    崔小玄是玄教弟子，擅长发明法宝。他的师父是如意仙娘崔采婷，在千翠山上修炼。
    
    小玄使用的法宝是八爪炎龙鞭，修炼的是离火诀。他的三师姐程水若修为高深，擅长克制火魅。
    
    程水若冷冷地看了他一眼，道："你这小混蛋，又想耍什么花招？"
    
    小玄连忙摆手："师姐，我这次是认真的！您看，这是我设计的图纸..."
    
    程水若接过图纸，仔细查看，眼中闪过一丝惊讶："这...这是火魅之发的设计图？"
    
    小玄点头："正是！师姐，您看这里，火魅之发需要特殊的炼制方法，只有您能帮我。"
    
    程水若沉思片刻，道："好吧，我就帮你这一次。不过，你要答应我，不许再惹是生非。"
    
    小玄大喜："谢谢师姐！我保证，这次绝对不会有问题！"
    
    第二章：火魅洞之战
    
    两人来到火魅洞前，程水若运起离火诀，八爪炎龙鞭在她手中舞动，发出阵阵龙吟。
    
    火魅感受到威胁，从洞中冲出，与程水若战在一处。小玄在一旁观战，心中暗暗佩服："三师姐的修为果然深不可测！"
    
    经过一番激战，程水若终于制服了火魅，取到了火魅之发。
    
    小玄接过火魅之发，激动地说："师姐，您真是太厉害了！"
    
    程水若淡淡地说："记住你的承诺。"
    
    小玄点头："是，师姐！"
    
    第三章：炼制法宝
    
    回到千翠山，小玄开始炼制火魅之发。他按照图纸上的方法，将火魅之发与八爪炎龙鞭融合。
    
    程水若在一旁指导："火候要掌握好，不能太急也不能太慢。"
    
    小玄专心致志地炼制，终于成功炼制出了新的法宝。
    
    程水若满意地点头："不错，你的炼器术有进步。"
    
    小玄兴奋地说："谢谢师姐的指导！"
    
    第四章：新的挑战
    
    就在这时，山下传来消息，有强敌来犯。程水若眉头一皱："看来又有麻烦了。"
    
    小玄握紧拳头："师姐，让我也去帮忙！"
    
    程水若看了他一眼："你确定？这次的敌人可不简单。"
    
    小玄坚定地说："我确定！我要保护千翠山！"
    
    程水若点头："好，那就一起去吧。"
    
    两人下山迎敌，面对强敌，小玄毫不畏惧，运用新炼制的法宝与敌人战斗。
    
    经过激烈的战斗，他们终于击退了强敌。
    
    程水若赞许地说："小玄，你长大了。"
    
    小玄谦虚地说："都是师姐教导有方。"
    
    第五章：新的开始
    
    回到山上，小玄继续修炼。他明白，只有不断变强，才能保护自己珍视的人。
    
    程水若看着他的背影，心中欣慰："这个师弟，终于懂事了。"
    
    小玄回头，看到程水若在看他，脸上一红："师姐，您在看什么？"
    
    程水若轻笑："没什么，继续修炼吧。"
    
    小玄点头，继续专心修炼。
    
    夕阳西下，千翠山上，师兄弟二人各自修炼，画面和谐而美好。
    """
    return sample_text

async def test_comprehensive_metadata_quality():
    """Test comprehensive metadata quality with larger sample"""
    print("🔍 Testing Comprehensive Metadata Quality")
    print("=" * 60)
    
    config = load_config()
    api_keys = config['api_keys']
    api_service = GeminiAPIService(api_keys, config.get('metadata', {}).get('api_config', {}))
    
    sample_text = load_large_sample_novel()
    
    # Test all three metadata types
    results = []
    
    # 1. Style Analysis
    print("\n🎨 Testing Style Analysis with Large Sample...")
    style_prompt = load_prompt('1_prompt_style_analysis_enhanced.txt')
    style_full_prompt = f"{style_prompt}\n\nTiểu thuyết cần phân tích:\n{sample_text}"
    
    try:
        style_result = await api_service.generate_content_async(style_full_prompt, model_name="gemini-2.5-flash")
        
        # Clean and parse JSON
        json_text = style_result.strip()
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        if json_text.endswith('```'):
            json_text = json_text[:-3]
        json_text = json_text.strip()
        
        style_data = json.loads(json_text)
        
        # Save for inspection
        with open('temp_style_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(style_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Style analysis completed - {len(style_data)} sections")
        results.append(True)
        
    except Exception as e:
        print(f"❌ Style analysis failed: {e}")
        results.append(False)
    
    # 2. Glossary Extraction
    print("\n📚 Testing Glossary Extraction with Large Sample...")
    glossary_prompt = load_prompt('2_prompt_glossary_extraction_enhanced.txt')
    glossary_full_prompt = f"{glossary_prompt}\n\nTiểu thuyết cần trích xuất thuật ngữ:\n{sample_text}"
    
    try:
        glossary_result = await api_service.generate_content_async(glossary_full_prompt, model_name="gemini-2.5-flash")
        
        # Parse CSV
        lines = glossary_result.strip().split('\n')
        if len(lines) >= 2:
            header = [col.strip() for col in lines[0].split(',')]
            data_rows = []
            
            for line in lines[1:]:
                if line.strip():
                    row = [col.strip() for col in line.split(',')]
                    if len(row) == len(header):
                        data_rows.append(dict(zip(header, row)))
            
            # Save for inspection
            with open('temp_glossary.csv', 'w', encoding='utf-8', newline='') as f:
                if data_rows:
                    writer = csv.DictWriter(f, fieldnames=header)
                    writer.writeheader()
                    writer.writerows(data_rows)
            
            print(f"✅ Glossary extraction completed - {len(data_rows)} terms")
            results.append(True)
        else:
            print("❌ Glossary extraction failed - no data")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Glossary extraction failed: {e}")
        results.append(False)
    
    # 3. Character Relations
    print("\n👥 Testing Character Relations with Large Sample...")
    relations_prompt = load_prompt('3_prompt_character_relations_enhanced.txt')
    relations_full_prompt = f"{relations_prompt}\n\nTiểu thuyết cần phân tích:\n{sample_text}"
    
    try:
        relations_result = await api_service.generate_content_async(relations_full_prompt, model_name="gemini-2.5-flash")
        
        # Parse CSV
        lines = relations_result.strip().split('\n')
        if len(lines) >= 2:
            header = [col.strip() for col in lines[0].split(',')]
            data_rows = []
            
            for line in lines[1:]:
                if line.strip():
                    row = [col.strip() for col in line.split(',')]
                    if len(row) == len(header):
                        data_rows.append(dict(zip(header, row)))
            
            # Save for inspection
            with open('temp_character_relations.csv', 'w', encoding='utf-8', newline='') as f:
                if data_rows:
                    writer = csv.DictWriter(f, fieldnames=header)
                    writer.writeheader()
                    writer.writerows(data_rows)
            
            print(f"✅ Character relations completed - {len(data_rows)} relations")
            results.append(True)
        else:
            print("❌ Character relations failed - no data")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Character relations failed: {e}")
        results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Comprehensive Test Results:")
    passed = sum(results)
    failed = len(results) - passed
    
    print(f"✅ Successful: {passed}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    
    if all(results):
        print("🎉 All metadata extractions completed successfully!")
        print("\n📁 Generated files for inspection:")
        print("  - temp_style_analysis.json")
        print("  - temp_glossary.csv") 
        print("  - temp_character_relations.csv")
    else:
        print("⚠️ Some extractions failed. Check the errors above.")
    
    return all(results)

async def main():
    """Main test function"""
    success = await test_comprehensive_metadata_quality()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
