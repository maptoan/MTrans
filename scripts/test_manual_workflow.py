#!/usr/bin/env python3
"""
Test script để chạy quy trình mô phỏng thủ công của user
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import yaml
from src.metadata.manual_workflow_emulator import ManualWorkflowEmulator


async def test_manual_workflow():
    """Test manual workflow emulator"""
    print("🧪 Testing Manual Workflow Emulator")
    print("=" * 50)
    
    # Load config
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Initialize emulator
    emulator = ManualWorkflowEmulator(config)
    
    # Test with sample text (since we don't have actual file)
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
    
    # Save sample text to temp file
    temp_file = Path('temp_sample.txt')
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(sample_text)
    
    try:
        # Run workflow
        results = await emulator.run_full_workflow(str(temp_file))
        
        print("\n📊 Test Results Summary:")
        print(f"✅ Text processed: {results.get('text_length', 0)} characters")
        print(f"✅ Style sections: {results.get('style_sections', 0)}")
        print(f"✅ Glossary terms: {results.get('glossary_terms', 0)}")
        print(f"✅ Character relations: {results.get('relations', 0)}")
        print(f"✅ Format valid: {'Yes' if results.get('format_valid', False) else 'No'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
        
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()

async def main():
    """Main test function"""
    success = await test_manual_workflow()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
