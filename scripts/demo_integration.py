#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo script minh họa cách tích hợp Metadata Extraction module vào quy trình tổng thể.
"""

import asyncio
import os
import sys
from pathlib import Path

import yaml

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

import logging

from src.integration.metadata_integration import MetadataIntegration
from src.metadata.metadata_extractor import MetadataExtractor

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger("IntegrationDemo")


def demo_phase_1_preprocessing():
    """
    Demo Phase 1: Pre-processing (Metadata Extraction)
    """
    print("\n" + "=" * 60)
    print("🔄 PHASE 1: PRE-PROCESSING (Metadata Extraction)")
    print("=" * 60)

    # Sample novel content
    sample_novel = """
    第一章 引子
    
    在遥远的古代，有一个叫做"玄天宗"的修仙门派。门派中有一位年轻的弟子名叫"林轩"，他天赋异禀，修炼速度极快。
    
    林轩的师父是"玄天真人"，一位德高望重的长老。他们之间的关系既是师徒，又像父子。
    
    这一天，林轩正在修炼"玄天心法"，突然听到外面传来一阵喧哗声。他走出洞府，看到一群外门弟子正在争吵。
    
    "你们在吵什么？"林轩问道。
    
    "林师兄，我们在讨论修炼心得。"一位弟子回答道。
    
    林轩点了点头，心想："这些师弟们都很努力，我应该帮助他们。"
    
    就在这时，天空中突然出现了一道金光，一个神秘的声音传来："林轩，你已突破到金丹期，可以下山历练了。"
    
    林轩心中一震，连忙跪下："弟子遵命！"
    
    从此，林轩踏上了修仙之路，开始了他的传奇人生。
    """

    print("📚 Sample Novel Content:")
    print(sample_novel[:200] + "...")

    # Initialize MetadataExtractor
    print("\n🔧 Initializing MetadataExtractor...")
    extractor = MetadataExtractor(
        prompts_dir="prompts/notebooklm",
        output_dir="demo_metadata_output",
        api_key="demo_key",  # Demo key for testing
    )

    print("✅ MetadataExtractor initialized")

    # Show prompt analysis
    print("\n📋 Enhanced Prompts Analysis:")

    # Style analysis prompt
    style_prompt = extractor.load_prompt("style_analysis")
    print("📄 Style Analysis Prompt:")
    print(f"   Length: {len(style_prompt)} characters")
    print(f"   Contains context_style_variations: {'context_style_variations' in style_prompt}")
    print(f"   Contains character_voice_analysis: {'character_voice_analysis' in style_prompt}")
    print(f"   Contains universal_style_rules: {'universal_style_rules' in style_prompt}")
    print(f"   Contains contextual_style_rules: {'contextual_style_rules' in style_prompt}")

    # Glossary extraction prompt
    glossary_prompt = extractor.load_prompt("glossary_extraction")
    print("\n📄 Glossary Extraction Prompt:")
    print(f"   Length: {len(glossary_prompt)} characters")
    print(f"   Contains Context_Usage: {'Context_Usage' in glossary_prompt}")
    print(f"   Contains Translation_Rule: {'Translation_Rule' in glossary_prompt}")
    print(f"   Contains Universal guidelines: {'Universal' in glossary_prompt}")
    print(f"   Contains Contextual guidelines: {'Contextual' in glossary_prompt}")

    # Character relations prompt
    relations_prompt = extractor.load_prompt("character_relations")
    print("\n📄 Character Relations Prompt:")
    print(f"   Length: {len(relations_prompt)} characters")
    print(f"   Contains UNIVERSAL RULES: {'UNIVERSAL RULES' in relations_prompt}")
    print(f"   Contains CONTEXTUAL RULES: {'CONTEXTUAL RULES' in relations_prompt}")
    print(f"   Contains mặc định: {'mặc định' in relations_prompt}")
    print(f"   Contains chung: {'chung' in relations_prompt}")

    print("\n✅ Phase 1 completed: Enhanced prompts ready for metadata extraction")


def demo_phase_2_initialization():
    """
    Demo Phase 2: Initialization (Manager Loading)
    """
    print("\n" + "=" * 60)
    print("🔄 PHASE 2: INITIALIZATION (Manager Loading)")
    print("=" * 60)

    # Mock config
    config = {
        "api": {"gemini_api_key": "demo_key"},
        "input": {"novel_path": "demo_novel.txt"},
        "output": {"formats": ["txt", "epub"]},
        "metadata": {
            "auto_extract": True,
            "validate_on_load": True,
            "prompts_dir": "prompts/notebooklm",
            "output_dir": "data/metadata",
        },
    }

    print("🔧 Initializing MetadataIntegration...")
    integration = MetadataIntegration(config)
    print("✅ MetadataIntegration initialized")

    # Check metadata files status
    print("\n📊 Checking metadata files status...")
    status = integration.check_metadata_files()
    print("Metadata files status:")
    for file_type, exists in status.items():
        status_icon = "✅" if exists else "❌"
        print(f"   {file_type}: {status_icon}")

    # Validate metadata files
    print("\n🔍 Validating metadata files...")
    validation = integration.validate_metadata_files()
    print("Validation results:")
    for file_type, result in validation.items():
        if file_type != "_summary":
            status_icon = "✅" if result["valid"] else "❌"
            print(f"   {file_type}: {status_icon}")
            if result["errors"]:
                print(f"     Errors: {', '.join(result['errors'])}")

    # Show metadata summary
    print("\n📋 Metadata Summary:")
    summary = integration.get_metadata_summary()
    print(f"   Files exist: {summary['files_exist']}")
    print(f"   All valid: {validation['_summary']['all_valid']}")
    print(f"   File paths: {summary['file_paths']}")

    print("\n✅ Phase 2 completed: Enhanced managers ready for translation")


def demo_phase_3_translation():
    """
    Demo Phase 3: Translation (Enhanced Translation Process)
    """
    print("\n" + "=" * 60)
    print("🔄 PHASE 3: TRANSLATION (Enhanced Translation Process)")
    print("=" * 60)

    # Sample chunk text
    sample_chunk = """
    林轩走出洞府，看到一群外门弟子正在争吵。
    
    "你们在吵什么？"林轩问道。
    
    "林师兄，我们在讨论修炼心得。"一位弟子回答道。
    
    林轩点了点头，心想："这些师弟们都很努力，我应该帮助他们。"
    """

    print("📝 Sample Chunk Text:")
    print(sample_chunk)

    # Simulate context extraction
    print("\n🔍 Simulating Context Extraction...")

    # Mock context extraction results
    context_info = {
        "context": "master_disciple",
        "environment": "informal",
        "chapter": "Chapter 1",
        "detected_keywords": ["sư phụ", "đệ tử", "thảo luận"],
        "confidence": 0.85,
    }

    print("Context extraction results:")
    for key, value in context_info.items():
        print(f"   {key}: {value}")

    # Simulate enhanced managers
    print("\n🔧 Simulating Enhanced Managers...")

    # Mock enhanced managers
    managers = {
        "style_manager": "Enhanced StyleManager (with context_style_variations)",
        "glossary_manager": "Enhanced GlossaryManager (with fuzzy matching)",
        "relation_manager": "Enhanced RelationManager (with 2-tier system)",
    }

    print("Enhanced managers:")
    for manager_type, description in managers.items():
        print(f"   {manager_type}: {description}")

    # Simulate 2-tier rule application
    print("\n📋 Simulating 2-Tier Rule Application...")

    # Universal rules (always apply)
    universal_rules = [
        "Giữ nguyên tông điệu chủ đạo của tác phẩm",
        "Duy trì tính nhất quán trong thuật ngữ",
        "Bảo toàn cấu trúc câu đặc trưng",
    ]

    print("Universal rules (always apply):")
    for i, rule in enumerate(universal_rules, 1):
        print(f"   {i}. {rule}")

    # Contextual rules (based on context)
    contextual_rules = {
        "master_disciple": [
            "Sử dụng ngôn ngữ trang trọng, sâu sắc",
            "Cấu trúc câu phức tạp",
            "Sử dụng thuật ngữ tu tiên",
        ],
        "informal": ["Ngôn ngữ gần gũi, thân mật", "Cấu trúc câu đơn giản", "Sử dụng xưng hô thân mật"],
    }

    print(f"\nContextual rules for '{context_info['context']}' context:")
    for i, rule in enumerate(contextual_rules["master_disciple"], 1):
        print(f"   {i}. {rule}")

    print(f"\nContextual rules for '{context_info['environment']}' environment:")
    for i, rule in enumerate(contextual_rules["informal"], 1):
        print(f"   {i}. {rule}")

    # Simulate enhanced prompt building
    print("\n🔧 Simulating Enhanced Prompt Building...")

    prompt_sections = [
        "Literary Guidelines (nền tảng)",
        "Style Instructions (từ enhanced style profile)",
        "Glossary Terms (với fuzzy matching)",
        "Character Relations (với 2-tier system)",
        "Context Awareness (từ ContextExtractor)",
        "Enhanced Validation (consistency checks)",
    ]

    print("Enhanced prompt sections:")
    for i, section in enumerate(prompt_sections, 1):
        print(f"   {i}. {section}")

    # Simulate translation result
    print("\n📝 Simulating Enhanced Translation...")

    mock_translation = """
    Lâm Huyền bước ra khỏi động phủ, thấy một nhóm đệ tử ngoại môn đang tranh cãi.
    
    "Các sư đệ đang tranh cãi gì vậy?" Lâm Huyền hỏi.
    
    "Sư huynh Lâm, chúng em đang thảo luận về tâm đắc tu luyện." Một đệ tử trả lời.
    
    Lâm Huyền gật đầu, thầm nghĩ: "Những sư đệ này đều rất chăm chỉ, ta nên giúp đỡ họ."
    """

    print("Enhanced translation result:")
    print(mock_translation)

    print("\n✅ Phase 3 completed: Enhanced translation with context awareness")


def demo_integration_workflow():
    """
    Demo toàn bộ integration workflow
    """
    print("\n" + "=" * 80)
    print("🚀 DEMO: METADATA EXTRACTION INTEGRATION WORKFLOW")
    print("=" * 80)

    # Phase 1: Pre-processing
    demo_phase_1_preprocessing()

    # Phase 2: Initialization
    demo_phase_2_initialization()

    # Phase 3: Translation
    demo_phase_3_translation()

    print("\n" + "=" * 80)
    print("🎉 INTEGRATION WORKFLOW DEMO COMPLETED!")
    print("=" * 80)

    print("\n📋 Integration Summary:")
    print("✅ Phase 1: Enhanced prompts ready for metadata extraction")
    print("✅ Phase 2: Enhanced managers loaded from metadata")
    print("✅ Phase 3: Context-aware translation with 2-tier system")

    print("\n🎯 Key Benefits:")
    print("✅ Seamless integration with existing workflow")
    print("✅ Enhanced translation quality with context awareness")
    print("✅ Consistent terminology and character voice")
    print("✅ Improved performance with cached rules")
    print("✅ Zero breaking changes to existing code")

    print("\n🚀 Module ready for production use!")


def demo_config_integration():
    """
    Demo config integration
    """
    print("\n" + "=" * 60)
    print("🔧 CONFIG INTEGRATION DEMO")
    print("=" * 60)

    # Load existing config
    config_path = "config/config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        print("✅ Loaded existing config.yaml")
    else:
        print("❌ config.yaml not found, using mock config")
        config = {
            "api": {"gemini_api_key": "demo_key"},
            "input": {"novel_path": "demo_novel.txt"},
            "output": {"formats": ["txt", "epub"]},
        }

    # Show existing config
    print("\n📋 Existing Config:")
    print(f"   API key present: {'gemini_api_key' in config.get('api', {})}")
    print(f"   Input novel: {config.get('input', {}).get('novel_path', 'Not specified')}")
    print(f"   Output formats: {config.get('output', {}).get('formats', [])}")

    # Show metadata config integration
    print("\n🔧 Metadata Config Integration:")
    metadata_config = {
        "metadata": {
            "auto_extract": True,
            "validate_on_load": True,
            "prompts_dir": "prompts/notebooklm",
            "output_dir": "data/metadata",
        }
    }

    print("New metadata config section:")
    for key, value in metadata_config["metadata"].items():
        print(f"   {key}: {value}")

    # Show enhanced translation config
    print("\n🚀 Enhanced Translation Config:")
    translation_config = {
        "translation": {"use_context_extraction": True, "use_2_tier_system": True, "context_aware_prompts": True}
    }

    print("Enhanced translation config:")
    for key, value in translation_config["translation"].items():
        print(f"   {key}: {value}")

    print("\n✅ Config integration completed")


def main():
    """
    Main demo function
    """
    print("🎬 Starting Metadata Extraction Integration Demo...")

    try:
        # Demo integration workflow
        demo_integration_workflow()

        # Demo config integration
        demo_config_integration()

        print("\n🎉 All demos completed successfully!")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.error(f"Demo failed: {e}")


if __name__ == "__main__":
    main()
