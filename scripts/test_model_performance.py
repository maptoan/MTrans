#!/usr/bin/env python3
"""
Test script để so sánh performance giữa gemini-2.5-flash và gemini-2.5-pro
cho metadata extraction tasks
"""

import asyncio
import sys
import time
from pathlib import Path

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

async def test_model_performance():
    """Test performance comparison between models"""
    print("🚀 Testing Model Performance Comparison")
    print("=" * 60)
    
    config = load_config()
    api_keys = config['api_keys']
    api_service = GeminiAPIService(api_keys, config.get('metadata', {}).get('api_config', {}))
    
    # Sample text for testing
    sample_text = """
    崔小玄是玄教弟子，擅长发明法宝。他的师父是如意仙娘崔采婷，在千翠山上修炼。
    
    小玄使用的法宝是八爪炎龙鞭，修炼的是离火诀。他的三师姐程水若修为高深，擅长克制火魅。
    
    程水若冷冷地看了他一眼，道："你这小混蛋，又想耍什么花招？"
    
    小玄连忙摆手："师姐，我这次是认真的！您看，这是我设计的图纸..."
    
    程水若接过图纸，仔细查看，眼中闪过一丝惊讶："这...这是火魅之发的设计图？"
    
    小玄点头："正是！师姐，您看这里，火魅之发需要特殊的炼制方法，只有您能帮我。"
    
    程水若沉思片刻，道："好吧，我就帮你这一次。不过，你要答应我，不许再惹是生非。"
    
    小玄大喜："谢谢师姐！我保证，这次绝对不会有问题！"
    """
    
    # Test prompts
    style_prompt = load_prompt('1_prompt_style_analysis_enhanced.txt')
    glossary_prompt = load_prompt('2_prompt_glossary_extraction_enhanced.txt')
    relations_prompt = load_prompt('3_prompt_character_relations_enhanced.txt')
    
    models_to_test = [
        ("gemini-2.5-flash", "⚡ Flash Model"),
        ("gemini-2.5-pro", "🧠 Pro Model")
    ]
    
    results = {}
    
    for model_name, model_display in models_to_test:
        print(f"\n{model_display} - {model_name}")
        print("-" * 40)
        
        model_results = {}
        
        # Test Style Analysis
        print("  🎨 Testing Style Analysis...")
        try:
            start_time = time.time()
            style_prompt_full = f"{style_prompt}\n\nTiểu thuyết cần phân tích:\n{sample_text}"
            style_result = await api_service.generate_content_async(style_prompt_full, model_name=model_name)
            style_time = time.time() - start_time
            
            # Try to parse JSON
            try:
                import json
                json_text = style_result.strip()
                if json_text.startswith('```json'):
                    json_text = json_text[7:]
                if json_text.endswith('```'):
                    json_text = json_text[:-3]
                json_text = json_text.strip()
                
                style_data = json.loads(json_text)
                style_success = True
                style_sections = len(style_data)
            except:
                style_success = False
                style_sections = 0
            
            print(f"    ✅ Time: {style_time:.2f}s, Success: {style_success}, Sections: {style_sections}")
            model_results['style'] = {
                'time': style_time,
                'success': style_success,
                'sections': style_sections
            }
        except Exception as e:
            print(f"    ❌ Error: {e}")
            model_results['style'] = {'time': 0, 'success': False, 'sections': 0}
        
        # Test Glossary Extraction
        print("  📚 Testing Glossary Extraction...")
        try:
            start_time = time.time()
            glossary_prompt_full = f"{glossary_prompt}\n\nTiểu thuyết cần trích xuất thuật ngữ:\n{sample_text}"
            glossary_result = await api_service.generate_content_async(glossary_prompt_full, model_name=model_name)
            glossary_time = time.time() - start_time
            
            # Parse CSV
            lines = glossary_result.strip().split('\n')
            if len(lines) >= 2:
                glossary_terms = len(lines) - 1  # Exclude header
                glossary_success = True
            else:
                glossary_terms = 0
                glossary_success = False
            
            print(f"    ✅ Time: {glossary_time:.2f}s, Success: {glossary_success}, Terms: {glossary_terms}")
            model_results['glossary'] = {
                'time': glossary_time,
                'success': glossary_success,
                'terms': glossary_terms
            }
        except Exception as e:
            print(f"    ❌ Error: {e}")
            model_results['glossary'] = {'time': 0, 'success': False, 'terms': 0}
        
        # Test Character Relations
        print("  👥 Testing Character Relations...")
        try:
            start_time = time.time()
            relations_prompt_full = f"{relations_prompt}\n\nTiểu thuyết cần phân tích:\n{sample_text}"
            relations_result = await api_service.generate_content_async(relations_prompt_full, model_name=model_name)
            relations_time = time.time() - start_time
            
            # Parse CSV
            lines = relations_result.strip().split('\n')
            if len(lines) >= 2:
                relations_count = len(lines) - 1  # Exclude header
                relations_success = True
            else:
                relations_count = 0
                relations_success = False
            
            print(f"    ✅ Time: {relations_time:.2f}s, Success: {relations_success}, Relations: {relations_count}")
            model_results['relations'] = {
                'time': relations_time,
                'success': relations_success,
                'count': relations_count
            }
        except Exception as e:
            print(f"    ❌ Error: {e}")
            model_results['relations'] = {'time': 0, 'success': False, 'count': 0}
        
        # Calculate totals
        total_time = model_results['style']['time'] + model_results['glossary']['time'] + model_results['relations']['time']
        total_success = sum(1 for task in model_results.values() if task['success'])
        
        print(f"  📊 Total Time: {total_time:.2f}s, Successful Tasks: {total_success}/3")
        
        results[model_name] = {
            'tasks': model_results,
            'total_time': total_time,
            'total_success': total_success
        }
        
        # Add delay between models to avoid rate limits
        await asyncio.sleep(2)
    
    # Summary comparison
    print("\n" + "=" * 60)
    print("📊 Performance Comparison Summary")
    print("=" * 60)
    
    flash_results = results.get('gemini-2.5-flash', {})
    pro_results = results.get('gemini-2.5-pro', {})
    
    print("⚡ Flash Model:")
    print(f"  Total Time: {flash_results.get('total_time', 0):.2f}s")
    print(f"  Success Rate: {flash_results.get('total_success', 0)}/3")
    
    print("\n🧠 Pro Model:")
    print(f"  Total Time: {pro_results.get('total_time', 0):.2f}s")
    print(f"  Success Rate: {pro_results.get('total_success', 0)}/3")
    
    # Calculate improvements
    if pro_results.get('total_time', 0) > 0:
        time_improvement = ((pro_results['total_time'] - flash_results.get('total_time', 0)) / pro_results['total_time']) * 100
        print("\n🚀 Flash vs Pro:")
        print(f"  Time Improvement: {time_improvement:.1f}%")
        print(f"  Speed Ratio: {pro_results['total_time'] / flash_results.get('total_time', 1):.2f}x")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if flash_results.get('total_success', 0) >= pro_results.get('total_success', 0):
        print("  ✅ Use gemini-2.5-flash for metadata extraction")
        print("  ✅ Better performance with same or better quality")
    else:
        print("  ⚠️ Consider using gemini-2.5-pro for better quality")
        print("  ⚠️ Trade-off between speed and quality")
    
    return results

async def main():
    """Main test function"""
    try:
        results = await test_model_performance()
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
