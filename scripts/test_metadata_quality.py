#!/usr/bin/env python3
"""
Test script để đánh giá chất lượng metadata được tạo ra bởi enhanced prompts
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

def load_sample_novel():
    """Load sample novel text for testing"""
    sample_text = """
    崔小玄是玄教弟子，擅长发明法宝。他的师父是如意仙娘崔采婷。
    
    在千翠山上，小玄遇到了火魅，需要三师姐程水若的帮助。
    
    小玄使用的法宝是八爪炎龙鞭，修炼的是离火诀。
    
    程水若冷冷地看了他一眼，道："你这小混蛋，又想耍什么花招？"
    
    小玄连忙摆手："师姐，我这次是认真的！您看，这是我设计的图纸..."
    
    程水若接过图纸，仔细查看，眼中闪过一丝惊讶："这...这是火魅之发的设计图？"
    
    小玄点头："正是！师姐，您看这里，火魅之发需要特殊的炼制方法，只有您能帮我。"
    
    程水若沉思片刻，道："好吧，我就帮你这一次。不过，你要答应我，不许再惹是生非。"
    
    小玄大喜："谢谢师姐！我保证，这次绝对不会有问题！"
    
    两人来到火魅洞前，程水若运起离火诀，八爪炎龙鞭在她手中舞动，发出阵阵龙吟。
    
    火魅感受到威胁，从洞中冲出，与程水若战在一处。
    
    小玄在一旁观战，心中暗暗佩服："三师姐的修为果然深不可测！"
    
    经过一番激战，程水若终于制服了火魅，取到了火魅之发。
    
    小玄接过火魅之发，激动地说："师姐，您真是太厉害了！"
    
    程水若淡淡地说："记住你的承诺。"
    
    小玄点头："是，师姐！"
    """
    return sample_text

async def test_style_analysis_quality():
    """Test quality of style analysis extraction"""
    print("🎨 Testing Style Analysis Quality...")
    
    config = load_config()
    api_keys = config['api_keys']
    api_service = GeminiAPIService(api_keys, config.get('metadata', {}).get('api_config', {}))
    
    prompt = load_prompt('1_prompt_style_analysis_enhanced.txt')
    sample_text = load_sample_novel()
    
    full_prompt = f"{prompt}\n\nTiểu thuyết cần phân tích:\n{sample_text}"
    
    try:
        result = await api_service.generate_content_async(full_prompt, model_name="gemini-2.5-flash")
        
        # Clean JSON
        json_text = result.strip()
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        if json_text.endswith('```'):
            json_text = json_text[:-3]
        json_text = json_text.strip()
        
        style_data = json.loads(json_text)
        
        # Quality checks
        quality_score = 0
        max_score = 100
        
        print("📊 Style Analysis Quality Assessment:")
        
        # Check required sections
        required_sections = [
            'novel_info', 'genre', 'writing_style', 
            'translation_guidelines', 'sample_analysis',
            'universal_style_rules', 'contextual_style_rules'
        ]
        
        sections_present = 0
        for section in required_sections:
            if section in style_data:
                sections_present += 1
                print(f"  ✅ {section}: Present")
            else:
                print(f"  ❌ {section}: Missing")
        
        quality_score += (sections_present / len(required_sections)) * 30
        print(f"  📈 Sections completeness: {sections_present}/{len(required_sections)} ({quality_score:.1f}/30)")
        
        # Check technical_jargon
        if 'writing_style' in style_data and 'technical_jargon' in style_data['writing_style']:
            jargon_count = len(style_data['writing_style']['technical_jargon'])
            if jargon_count >= 10:
                quality_score += 20
                print(f"  ✅ Technical jargon: {jargon_count} terms ({20}/20)")
            else:
                quality_score += (jargon_count / 10) * 20
                print(f"  ⚠️ Technical jargon: {jargon_count} terms (expected ≥10) ({quality_score:.1f}/20)")
        else:
            print("  ❌ Technical jargon: Missing (0/20)")
        
        # Check translation guidelines structure
        if 'translation_guidelines' in style_data:
            guidelines = style_data['translation_guidelines']
            guideline_types = ['preserve', 'adapt', 'avoid', 'priorities']
            present_types = sum(1 for t in guideline_types if t in guidelines)
            quality_score += (present_types / len(guideline_types)) * 25
            print(f"  📈 Translation guidelines: {present_types}/{len(guideline_types)} types ({quality_score:.1f}/25)")
        else:
            print("  ❌ Translation guidelines: Missing (0/25)")
        
        # Check sample analysis depth
        if 'sample_analysis' in style_data:
            sample = style_data['sample_analysis']
            if isinstance(sample, dict) and len(sample) >= 3:
                quality_score += 15
                print(f"  ✅ Sample analysis: Detailed ({15}/15)")
            else:
                quality_score += 10
                print(f"  ⚠️ Sample analysis: Basic ({10}/15)")
        else:
            print("  ❌ Sample analysis: Missing (0/15)")
        
        # Check rules count
        universal_rules = style_data.get('universal_style_rules', [])
        contextual_rules = style_data.get('contextual_style_rules', [])
        
        if len(universal_rules) >= 5:
            quality_score += 5
            print(f"  ✅ Universal rules: {len(universal_rules)} rules ({5}/5)")
        else:
            print(f"  ⚠️ Universal rules: {len(universal_rules)} rules (expected ≥5) ({0}/5)")
        
        if len(contextual_rules) >= 10:
            quality_score += 5
            print(f"  ✅ Contextual rules: {len(contextual_rules)} rules ({5}/5)")
        else:
            print(f"  ⚠️ Contextual rules: {len(contextual_rules)} rules (expected ≥10) ({0}/5)")
        
        print(f"\n🎯 Style Analysis Quality Score: {quality_score:.1f}/{max_score}")
        
        if quality_score >= 80:
            print("🌟 Excellent quality!")
            return True
        elif quality_score >= 60:
            print("✅ Good quality")
            return True
        else:
            print("⚠️ Needs improvement")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_glossary_quality():
    """Test quality of glossary extraction"""
    print("\n📚 Testing Glossary Quality...")
    
    config = load_config()
    api_keys = config['api_keys']
    api_service = GeminiAPIService(api_keys, config.get('metadata', {}).get('api_config', {}))
    
    prompt = load_prompt('2_prompt_glossary_extraction_enhanced.txt')
    sample_text = load_sample_novel()
    
    full_prompt = f"{prompt}\n\nTiểu thuyết cần trích xuất thuật ngữ:\n{sample_text}"
    
    try:
        result = await api_service.generate_content_async(full_prompt, model_name="gemini-2.5-flash")
        
        # Parse CSV
        lines = result.strip().split('\n')
        if len(lines) < 2:
            print("❌ No data found")
            return False
        
        # Parse header and data
        header = [col.strip() for col in lines[0].split(',')]
        data_rows = []
        
        for line in lines[1:]:
            if line.strip():
                row = [col.strip() for col in line.split(',')]
                if len(row) == len(header):
                    data_rows.append(dict(zip(header, row)))
        
        # Quality checks
        quality_score = 0
        max_score = 100
        
        print("📊 Glossary Quality Assessment:")
        
        # Check required columns
        required_columns = [
            'Type', 'Original_Term_Pinyin', 'Original_Term_CN', 
            'Translated_Term_VI', 'Alternative_Translations', 
            'Translation_Rule', 'Context_Usage', 'Frequency', 'Notes'
        ]
        
        columns_present = sum(1 for col in required_columns if col in header)
        quality_score += (columns_present / len(required_columns)) * 30
        print(f"  📈 Column completeness: {columns_present}/{len(required_columns)} ({quality_score:.1f}/30)")
        
        # Check data count
        if len(data_rows) >= 50:
            quality_score += 25
            print(f"  ✅ Data count: {len(data_rows)} terms ({25}/25)")
        elif len(data_rows) >= 30:
            quality_score += 20
            print(f"  ⚠️ Data count: {len(data_rows)} terms (expected ≥50) ({20}/25)")
        else:
            print(f"  ❌ Data count: {len(data_rows)} terms (expected ≥50) ({0}/25)")
        
        # Check Notes quality
        notes_with_content = sum(1 for row in data_rows if len(row.get('Notes', '')) >= 10)
        notes_quality = (notes_with_content / len(data_rows)) * 20 if data_rows else 0
        quality_score += notes_quality
        print(f"  📈 Notes quality: {notes_with_content}/{len(data_rows)} detailed notes ({notes_quality:.1f}/20)")
        
        # Check term diversity
        types = set(row.get('Type', '') for row in data_rows)
        if len(types) >= 5:
            quality_score += 10
            print(f"  ✅ Term diversity: {len(types)} types ({10}/10)")
        else:
            print(f"  ⚠️ Term diversity: {len(types)} types (expected ≥5) ({0}/10)")
        
        # Check translation rules
        rules_with_content = sum(1 for row in data_rows if len(row.get('Translation_Rule', '')) >= 5)
        rules_quality = (rules_with_content / len(data_rows)) * 15 if data_rows else 0
        quality_score += rules_quality
        print(f"  📈 Translation rules: {rules_with_content}/{len(data_rows)} detailed rules ({rules_quality:.1f}/15)")
        
        print(f"\n🎯 Glossary Quality Score: {quality_score:.1f}/{max_score}")
        
        if quality_score >= 80:
            print("🌟 Excellent quality!")
            return True
        elif quality_score >= 60:
            print("✅ Good quality")
            return True
        else:
            print("⚠️ Needs improvement")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_character_relations_quality():
    """Test quality of character relations extraction"""
    print("\n👥 Testing Character Relations Quality...")
    
    config = load_config()
    api_keys = config['api_keys']
    api_service = GeminiAPIService(api_keys, config.get('metadata', {}).get('api_config', {}))
    
    prompt = load_prompt('3_prompt_character_relations_enhanced.txt')
    sample_text = load_sample_novel()
    
    full_prompt = f"{prompt}\n\nTiểu thuyết cần phân tích:\n{sample_text}"
    
    try:
        result = await api_service.generate_content_async(full_prompt, model_name="gemini-2.5-flash")
        
        # Parse CSV
        lines = result.strip().split('\n')
        if len(lines) < 2:
            print("❌ No data found")
            return False
        
        # Parse header and data
        header = [col.strip() for col in lines[0].split(',')]
        data_rows = []
        
        for line in lines[1:]:
            if line.strip():
                row = [col.strip() for col in line.split(',')]
                if len(row) == len(header):
                    data_rows.append(dict(zip(header, row)))
        
        # Quality checks
        quality_score = 0
        max_score = 100
        
        print("📊 Character Relations Quality Assessment:")
        
        # Check required columns
        required_columns = [
            'Character_A', 'Character_B', 'Relationship_Type', 'Pronoun_Rule',
            'Context', 'Emotional_State', 'Usage_Example', 'Notes'
        ]
        
        columns_present = sum(1 for col in required_columns if col in header)
        quality_score += (columns_present / len(required_columns)) * 25
        print(f"  📈 Column completeness: {columns_present}/{len(required_columns)} ({quality_score:.1f}/25)")
        
        # Check data count
        if len(data_rows) >= 50:
            quality_score += 20
            print(f"  ✅ Data count: {len(data_rows)} relations ({20}/20)")
        elif len(data_rows) >= 30:
            quality_score += 15
            print(f"  ⚠️ Data count: {len(data_rows)} relations (expected ≥50) ({15}/20)")
        else:
            print(f"  ❌ Data count: {len(data_rows)} relations (expected ≥50) ({0}/20)")
        
        # Check Universal vs Contextual distribution
        universal_count = len([r for r in data_rows if r.get('Context', '').lower() in ['mặc định', 'chung', 'default', 'general']])
        contextual_count = len(data_rows) - universal_count
        
        if universal_count >= 20 and contextual_count >= 30:
            quality_score += 20
            print(f"  ✅ Distribution: {universal_count} universal, {contextual_count} contextual ({20}/20)")
        elif universal_count >= 10 and contextual_count >= 20:
            quality_score += 15
            print(f"  ⚠️ Distribution: {universal_count} universal, {contextual_count} contextual (expected ≥20/30) ({15}/20)")
        else:
            print(f"  ❌ Distribution: {universal_count} universal, {contextual_count} contextual (expected ≥20/30) ({0}/20)")
        
        # Check emotional states diversity
        emotions = set(row.get('Emotional_State', '') for row in data_rows)
        if len(emotions) >= 5:
            quality_score += 15
            print(f"  ✅ Emotional diversity: {len(emotions)} states ({15}/15)")
        else:
            print(f"  ⚠️ Emotional diversity: {len(emotions)} states (expected ≥5) ({0}/15)")
        
        # Check usage examples quality
        examples_with_content = sum(1 for row in data_rows if len(row.get('Usage_Example', '')) >= 10)
        examples_quality = (examples_with_content / len(data_rows)) * 20 if data_rows else 0
        quality_score += examples_quality
        print(f"  📈 Usage examples: {examples_with_content}/{len(data_rows)} detailed examples ({examples_quality:.1f}/20)")
        
        print(f"\n🎯 Character Relations Quality Score: {quality_score:.1f}/{max_score}")
        
        if quality_score >= 80:
            print("🌟 Excellent quality!")
            return True
        elif quality_score >= 60:
            print("✅ Good quality")
            return True
        else:
            print("⚠️ Needs improvement")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Main test function"""
    print("🔍 Testing Enhanced Metadata Quality")
    print("=" * 60)
    
    results = []
    
    # Test each metadata type
    results.append(await test_style_analysis_quality())
    results.append(await test_glossary_quality())
    results.append(await test_character_relations_quality())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Overall Quality Assessment:")
    passed = sum(results)
    failed = len(results) - passed
    
    print(f"✅ High Quality: {passed}/{len(results)}")
    print(f"⚠️ Needs Improvement: {failed}/{len(results)}")
    
    if all(results):
        print("🎉 All metadata types meet high quality standards!")
    else:
        print("💡 Consider reviewing the prompts for better results.")
    
    return all(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
