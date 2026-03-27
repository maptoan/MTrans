#!/usr/bin/env python3
"""
Test script để kiểm tra hiệu quả của quota optimization
"""

import asyncio
import sys
import time
from pathlib import Path

import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.metadata.enhanced_quota_manager import EnhancedQuotaManager, TaskType

from src.services.gemini_api_service import GeminiAPIService


def load_config():
    """Load configuration"""
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def create_large_sample_text() -> str:
    """Tạo sample text lớn để test quota optimization"""
    base_text = """
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
    
    # Duplicate text để tạo file lớn hơn
    large_text = base_text * 5  # Tạo text ~5x lớn hơn
    return large_text

async def test_quota_optimization():
    """Test quota optimization với large file"""
    print("🚀 Testing Quota Optimization for Large Files")
    print("=" * 60)
    
    # Load config
    config = load_config()
    api_keys = config['api_keys']
    
    print(f"📊 Available API keys: {len(api_keys)}")
    for i, key in enumerate(api_keys):
        print(f"  Key {i+1}: {key[:10]}...")
    
    # Create large sample text
    large_text = create_large_sample_text()
    print(f"📝 Sample text length: {len(large_text):,} characters")
    
    # Initialize services
    api_service = GeminiAPIService(api_keys, config.get('metadata', {}).get('api_config', {}))
    quota_manager = EnhancedQuotaManager(api_keys)
    
    # Test 1: Single API key (old method)
    print("\n🔍 Test 1: Single API Key Method (Old)")
    print("-" * 40)
    
    start_time = time.time()
    try:
        # Simulate old method with single API key
        old_results = await test_old_method(large_text, api_service)
        old_time = time.time() - start_time
        old_success = True
        print(f"✅ Old method completed in {old_time:.2f}s")
    except Exception as e:
        old_time = time.time() - start_time
        old_success = False
        print(f"❌ Old method failed after {old_time:.2f}s: {e}")
    
    # Test 2: Enhanced quota optimization (new method)
    print("\n🚀 Test 2: Enhanced Quota Optimization (New)")
    print("-" * 40)
    
    start_time = time.time()
    try:
        new_results = await quota_manager.extract_metadata_optimized(large_text, api_service)
        new_time = time.time() - start_time
        new_success = True
        print(f"✅ New method completed in {new_time:.2f}s")
        
        # Show results summary
        print("📊 Results summary:")
        print(f"  - Chunks processed: {new_results.get('chunks_processed', 0)}")
        print(f"  - Glossary terms: {len(new_results.get('glossary_terms', []))}")
        print(f"  - Character relations: {len(new_results.get('character_relations', []))}")
        
    except Exception as e:
        new_time = time.time() - start_time
        new_success = False
        print(f"❌ New method failed after {new_time:.2f}s: {e}")
    
    # Test 3: Quota usage comparison
    print("\n📊 Test 3: Quota Usage Analysis")
    print("-" * 40)
    
    usage_stats = quota_manager.quota_monitor.get_usage_stats()
    print("API Key Usage Statistics:")
    for key, stats in usage_stats.items():
        print(f"  {key[:10]}...:")
        print(f"    Tokens: {stats['tokens_used']:,}/{stats['tokens_limit']:,} ({stats['tokens_percent']:.1f}%)")
        print(f"    Requests: {stats['requests_used']}/{stats['requests_limit']} ({stats['requests_percent']:.1f}%)")
        print(f"    Status: {'Blocked' if stats['is_blocked'] else 'Active'}")
        print(f"    Errors: {stats['error_count']}")
    
    # Summary comparison
    print("\n" + "=" * 60)
    print("📊 Performance Comparison Summary")
    print("=" * 60)
    
    print("Old Method (Single API):")
    print(f"  Success: {'✅' if old_success else '❌'}")
    print(f"  Time: {old_time:.2f}s")
    
    print("\nNew Method (Quota Optimization):")
    print(f"  Success: {'✅' if new_success else '❌'}")
    print(f"  Time: {new_time:.2f}s")
    
    if old_success and new_success:
        improvement = ((old_time - new_time) / old_time) * 100
        print(f"\n🚀 Performance Improvement: {improvement:.1f}%")
    
    # Quota efficiency analysis
    total_tokens_used = sum(stats['tokens_used'] for stats in usage_stats.values())
    total_requests_used = sum(stats['requests_used'] for stats in usage_stats.values())
    
    print("\n📈 Quota Efficiency:")
    print(f"  Total tokens used: {total_tokens_used:,}")
    print(f"  Total requests used: {total_requests_used}")
    print(f"  Average tokens per request: {total_tokens_used / max(total_requests_used, 1):.0f}")
    
    return {
        'old_success': old_success,
        'old_time': old_time,
        'new_success': new_success,
        'new_time': new_time,
        'usage_stats': usage_stats
    }

async def test_old_method(text: str, api_service) -> dict:
    """Simulate old method with single API key"""
    # This would be the old method that uses single API key
    # For testing, we'll just simulate with a small portion
    sample_text = text[:50000]  # Use only first 50k chars
    
    # Simulate style analysis
    style_prompt = f"Analyze style: {sample_text[:1000]}"
    await api_service.generate_content_async(style_prompt, model_name="gemini-2.5-flash")
    
    # Simulate glossary extraction
    glossary_prompt = f"Extract glossary: {sample_text[:1000]}"
    await api_service.generate_content_async(glossary_prompt, model_name="gemini-2.5-flash")
    
    # Simulate character relations
    relations_prompt = f"Extract relations: {sample_text[:1000]}"
    await api_service.generate_content_async(relations_prompt, model_name="gemini-2.5-flash")
    
    return {'simulated': True}

async def main():
    """Main test function"""
    try:
        results = await test_quota_optimization()
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
