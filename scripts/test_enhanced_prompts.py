#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script test các enhanced prompts cho metadata extraction
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import csv
import json

import yaml

from src.services.api_key_manager import APIKeyManager
from src.services.gemini_api_service import GeminiAPIService


def load_config():
    """Load configuration"""
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_prompt(prompt_file):
    """Load prompt from file"""
    with open(f'prompts/notebooklm/{prompt_file}', 'r', encoding='utf-8') as f:
        return f.read()

async def test_style_analysis_prompt():
    """Test style analysis prompt"""
    print("🧪 Testing Style Analysis Prompt...")
    
    config = load_config()
    api_keys = config['api_keys']
    
    # Initialize API service
    api_service = GeminiAPIService(api_keys, config.get('metadata', {}).get('api_config', {}))
    
    # Load prompt
    prompt = load_prompt('1_prompt_style_analysis_enhanced.txt')
    
    # Add sample text (you can replace with actual novel content)
    sample_text = """
    小玄可怜巴巴地央道："三师姐，为了明天的伟大发明，我已经整整准备了五个月，眼下就只差火魅之发这一样东西了，师姐您仁侠高义神通广大，在四位师姐里边，又唯有您能克制火魅，所以今晚请您一定要帮帮忙啊！"
    
    程水若冷冷地看了他一眼，道："你这小混蛋，又想耍什么花招？"
    
    小玄连忙摆手："师姐，我这次是认真的！您看，这是我设计的图纸..."
    """
    
    full_prompt = f"{prompt}\n\nTiểu thuyết cần phân tích:\n{sample_text}"
    
    try:
        result = await api_service.generate_content_async(full_prompt, model_name="gemini-2.5-flash")
        
        # Try to parse as JSON
        try:
            # Remove markdown wrapper if present
            json_text = result.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:]  # Remove ```json
            if json_text.endswith('```'):
                json_text = json_text[:-3]  # Remove ```
            json_text = json_text.strip()
            
            json_data = json.loads(json_text)
            print("✅ Style analysis prompt works!")
            print(f"📊 Generated {len(json_data)} main sections")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"Raw output: {result[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

async def test_glossary_extraction_prompt():
    """Test glossary extraction prompt"""
    print("🧪 Testing Glossary Extraction Prompt...")
    
    config = load_config()
    api_keys = config['api_keys']
    
    # Initialize API service
    api_service = GeminiAPIService(api_keys, config.get('metadata', {}).get('api_config', {}))
    
    # Load prompt
    prompt = load_prompt('2_prompt_glossary_extraction_enhanced.txt')
    
    # Add sample text
    sample_text = """
    崔小玄是玄教弟子，擅长发明法宝。他的师父是如意仙娘崔采婷。
    
    在千翠山上，小玄遇到了火魅，需要三师姐程水若的帮助。
    
    小玄使用的法宝是八爪炎龙鞭，修炼的是离火诀。
    """
    
    full_prompt = f"{prompt}\n\nTiểu thuyết cần trích xuất thuật ngữ:\n{sample_text}"
    
    try:
        result = await api_service.generate_content_async(full_prompt, model_name="gemini-2.5-flash")
        
        # Try to parse as CSV
        try:
            lines = result.strip().split('\n')
            if len(lines) < 2:
                print("❌ CSV too short")
                return False
                
            # Check header
            header = lines[0].split(',')
            expected_header = ['Type', 'Original_Term_Pinyin', 'Original_Term_CN', 'Translated_Term_VI', 'Alternative_Translations', 'Translation_Rule', 'Context_Usage', 'Frequency', 'Notes']
            
            if header != expected_header:
                print(f"❌ Header mismatch. Expected: {expected_header}, Got: {header}")
                return False
            
            # Check data rows
            data_rows = lines[1:]
            if len(data_rows) < 10:
                print(f"❌ Too few data rows: {len(data_rows)}")
                return False
            
            print("✅ Glossary extraction prompt works!")
            print(f"📊 Generated {len(data_rows)} glossary entries")
            return True
            
        except Exception as e:
            print(f"❌ CSV parsing failed: {e}")
            print(f"Raw output: {result[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

async def test_character_relations_prompt():
    """Test character relations prompt"""
    print("🧪 Testing Character Relations Prompt...")
    
    config = load_config()
    api_keys = config['api_keys']
    
    # Initialize API service
    api_service = GeminiAPIService(api_keys, config.get('metadata', {}).get('api_config', {}))
    
    # Load prompt
    prompt = load_prompt('3_prompt_character_relations_enhanced.txt')
    
    # Add sample text
    sample_text = """
    小玄对三师姐说："三师姐，您就帮帮我吧！"
    
    程水若冷冷地回答："你这小混蛋，又想耍什么花招？"
    
    小玄连忙摆手："师姐，我这次是认真的！"
    """
    
    full_prompt = f"{prompt}\n\nTiểu thuyết cần phân tích quan hệ nhân vật:\n{sample_text}"
    
    try:
        result = await api_service.generate_content_async(full_prompt, model_name="gemini-2.5-flash")
        
        # Try to parse as CSV
        try:
            lines = result.strip().split('\n')
            if len(lines) < 2:
                print("❌ CSV too short")
                return False
                
            # Check header
            header = lines[0].split(',')
            expected_header = ['Speaker_ID', 'Listener_ID', 'Relationship_Type', 'Context', 'Environment', 'Power_Dynamic', 'Emotional_State', 'Speaker_Pronoun', 'Listener_Term', 'Listener_Pronoun', 'Speaker_Term', 'Notes']
            
            if header != expected_header:
                print(f"❌ Header mismatch. Expected: {expected_header}, Got: {header}")
                return False
            
            # Check data rows
            data_rows = lines[1:]
            if len(data_rows) < 5:
                print(f"❌ Too few data rows: {len(data_rows)}")
                return False
            
            print("✅ Character relations prompt works!")
            print(f"📊 Generated {len(data_rows)} character relations")
            return True
            
        except Exception as e:
            print(f"❌ CSV parsing failed: {e}")
            print(f"Raw output: {result[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Testing Enhanced Prompts for Metadata Extraction")
    print("=" * 60)
    
    # Test all prompts
    results = []
    
    results.append(await test_style_analysis_prompt())
    print()
    
    results.append(await test_glossary_extraction_prompt())
    print()
    
    results.append(await test_character_relations_prompt())
    print()
    
    # Summary
    print("=" * 60)
    print("📊 Test Results Summary:")
    print(f"✅ Passed: {sum(results)}/3")
    print(f"❌ Failed: {3 - sum(results)}/3")
    
    if all(results):
        print("🎉 All enhanced prompts are working correctly!")
    else:
        print("⚠️ Some prompts need attention. Check the errors above.")
    
    return all(results)

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
