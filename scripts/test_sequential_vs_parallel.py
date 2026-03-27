#!/usr/bin/env python3
"""
Test script để so sánh Sequential vs Parallel approach cho metadata extraction
"""

import asyncio
import sys
import time
from pathlib import Path

import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.metadata.sequential_metadata_extractor import SequentialMetadataExtractor

from src.services.gemini_api_service import GeminiAPIService


def load_config():
    """Load configuration"""
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def create_test_text() -> str:
    """Tạo test text với dependencies rõ ràng"""
    return """
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

async def test_sequential_approach(text: str, api_service) -> dict:
    """Test Sequential approach"""
    print("🔄 Testing Sequential Approach...")
    print("-" * 40)
    
    start_time = time.time()
    
    try:
        # Initialize sequential extractor
        extractor = SequentialMetadataExtractor(api_service.api_keys)
        
        # Extract metadata sequentially
        results = await extractor.extract_metadata_sequential(text, api_service)
        
        sequential_time = time.time() - start_time
        
        print(f"✅ Sequential completed in {sequential_time:.2f}s")
        print("📊 Results:")
        print(f"  - Style sections: {len(results.get('style_profile', {}))}")
        print(f"  - Glossary terms: {len(results.get('glossary', []))}")
        print(f"  - Character relations: {len(results.get('character_relations', []))}")
        
        return {
            'success': True,
            'time': sequential_time,
            'results': results
        }
        
    except Exception as e:
        sequential_time = time.time() - start_time
        print(f"❌ Sequential failed after {sequential_time:.2f}s: {e}")
        return {
            'success': False,
            'time': sequential_time,
            'error': str(e)
        }

async def test_parallel_approach(text: str, api_service) -> dict:
    """Test Parallel approach (simulated)"""
    print("\n⚡ Testing Parallel Approach (Simulated)...")
    print("-" * 40)
    
    start_time = time.time()
    
    try:
        # Simulate parallel approach (without dependencies)
        from src.metadata.enhanced_quota_manager import EnhancedQuotaManager
        
        quota_manager = EnhancedQuotaManager(api_service.api_keys)
        results = await quota_manager.extract_metadata_optimized(text, api_service)
        
        parallel_time = time.time() - start_time
        
        print(f"✅ Parallel completed in {parallel_time:.2f}s")
        print("📊 Results:")
        print(f"  - Style sections: {len(results.get('style_profile', {}))}")
        print(f"  - Glossary terms: {len(results.get('glossary_terms', []))}")
        print(f"  - Character relations: {len(results.get('character_relations', []))}")
        
        return {
            'success': True,
            'time': parallel_time,
            'results': results
        }
        
    except Exception as e:
        parallel_time = time.time() - start_time
        print(f"❌ Parallel failed after {parallel_time:.2f}s: {e}")
        return {
            'success': False,
            'time': parallel_time,
            'error': str(e)
        }

def analyze_dependencies(sequential_results: dict, parallel_results: dict):
    """Analyze dependencies và quality differences"""
    print("\n🔍 Dependency Analysis...")
    print("-" * 40)
    
    if not sequential_results['success'] or not parallel_results['success']:
        print("❌ Cannot analyze - one or both approaches failed")
        return
    
    seq_results = sequential_results['results']
    par_results = parallel_results['results']
    
    # Analyze Style Profile
    print("📝 Style Profile Analysis:")
    seq_style = seq_results.get('style_profile', {})
    par_style = par_results.get('style_profile', {})
    
    print(f"  Sequential: {len(seq_style)} sections")
    print(f"  Parallel: {len(par_style)} sections")
    
    # Analyze Glossary
    print("\n📚 Glossary Analysis:")
    seq_glossary = seq_results.get('glossary', [])
    par_glossary = par_results.get('glossary_terms', [])
    
    print(f"  Sequential: {len(seq_glossary)} terms")
    print(f"  Parallel: {len(par_glossary)} terms")
    
    # Analyze Character Relations
    print("\n👥 Character Relations Analysis:")
    seq_relations = seq_results.get('character_relations', [])
    par_relations = par_results.get('character_relations', [])
    
    print(f"  Sequential: {len(seq_relations)} relations")
    print(f"  Parallel: {len(par_relations)} relations")
    
    # Check for missing characters
    if seq_glossary and seq_relations:
        glossary_chars = set(term['Original_Term_CN'] for term in seq_glossary if term.get('Type') == 'Character')
        relations_chars = set()
        for rel in seq_relations:
            relations_chars.add(rel.get('Character_A', ''))
            relations_chars.add(rel.get('Character_B', ''))
        
        missing_chars = glossary_chars - relations_chars
        print(f"  Missing characters in relations: {len(missing_chars)}")
        if missing_chars:
            print(f"    Missing: {list(missing_chars)[:5]}...")

def compare_quality(sequential_results: dict, parallel_results: dict):
    """Compare quality between approaches"""
    print("\n📊 Quality Comparison...")
    print("-" * 40)
    
    if not sequential_results['success'] or not parallel_results['success']:
        print("❌ Cannot compare - one or both approaches failed")
        return
    
    # Time comparison
    seq_time = sequential_results['time']
    par_time = parallel_results['time']
    
    print("⏱️ Time Comparison:")
    print(f"  Sequential: {seq_time:.2f}s")
    print(f"  Parallel: {par_time:.2f}s")
    print(f"  Difference: {abs(seq_time - par_time):.2f}s ({((seq_time - par_time) / par_time * 100):+.1f}%)")
    
    # Success rate
    print("\n✅ Success Rate:")
    print(f"  Sequential: {'✅' if sequential_results['success'] else '❌'}")
    print(f"  Parallel: {'✅' if parallel_results['success'] else '❌'}")
    
    # Data completeness
    seq_results = sequential_results['results']
    par_results = parallel_results['results']
    
    print("\n📈 Data Completeness:")
    print(f"  Style sections: {len(seq_results.get('style_profile', {}))} vs {len(par_results.get('style_profile', {}))}")
    print(f"  Glossary terms: {len(seq_results.get('glossary', []))} vs {len(par_results.get('glossary_terms', []))}")
    print(f"  Relations: {len(seq_results.get('character_relations', []))} vs {len(par_results.get('character_relations', []))}")

async def main():
    """Main test function"""
    print("🧪 Testing Sequential vs Parallel Metadata Extraction")
    print("=" * 60)
    
    # Load config
    config = load_config()
    api_keys = config['api_keys']
    api_service = GeminiAPIService(api_keys, config.get('metadata', {}).get('api_config', {}))
    
    # Create test text
    text = create_test_text()
    print(f"📝 Test text length: {len(text):,} characters")
    
    # Test Sequential approach
    sequential_results = await test_sequential_approach(text, api_service)
    
    # Test Parallel approach
    parallel_results = await test_parallel_approach(text, api_service)
    
    # Analyze dependencies
    analyze_dependencies(sequential_results, parallel_results)
    
    # Compare quality
    compare_quality(sequential_results, parallel_results)
    
    # Final recommendation
    print("\n" + "=" * 60)
    print("🎯 Final Recommendation")
    print("=" * 60)
    
    if sequential_results['success'] and parallel_results['success']:
        print("✅ Both approaches succeeded")
        print("💡 Sequential approach is recommended for:")
        print("  - Higher quality with dependencies")
        print("  - Better context awareness")
        print("  - More accurate character relations")
        print("  - Professional translation needs")
    elif sequential_results['success']:
        print("✅ Sequential approach succeeded")
        print("❌ Parallel approach failed")
        print("💡 Sequential approach is clearly better")
    elif parallel_results['success']:
        print("❌ Sequential approach failed")
        print("✅ Parallel approach succeeded")
        print("💡 Parallel approach is better in this case")
    else:
        print("❌ Both approaches failed")
        print("💡 Need to investigate issues")
    
    return sequential_results['success'] and parallel_results['success']

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
