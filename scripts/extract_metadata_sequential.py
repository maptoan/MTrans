#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI: Trích xuất Metadata độc lập (Style → Glossary → Character Relations)
- Đọc cấu hình từ config/config.yaml
- Dùng SequentialMetadataExtractor và GeminiAPIService
- Lưu kết quả vào data/metadata theo đường dẫn trong config
"""

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

import yaml

# Add project root
sys.path.append(str(Path(__file__).parent.parent))

from src.metadata.sequential_metadata_extractor import SequentialMetadataExtractor

from src.services.gemini_api_service import GeminiAPIService
from src.utils.path_manager import resolve_path


def load_config(path: str) -> dict:
    cfg_path = resolve_path(path, "config/config.yaml")
    with open(cfg_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def ensure_parent_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


async def run_extraction(config_path: str) -> int:
    config = load_config(config_path)

    api_keys = config.get('api_keys', [])
    if not api_keys:
        print("[ERROR] Không tìm thấy API keys trong config.yaml")
        return 1

    meta_cfg = config.get('metadata', {})
    style_path = resolve_path(meta_cfg.get('style_profile_path'), 'data/metadata/style_profile.json')
    glossary_path = resolve_path(meta_cfg.get('glossary_path'), 'data/metadata/glossary.csv')
    relations_path = resolve_path(meta_cfg.get('character_relations_path'), 'data/metadata/character_relations.csv')

    # Prepare services
    api_service = GeminiAPIService(api_keys, meta_cfg.get('api_config', {}))
    extractor = SequentialMetadataExtractor(api_keys)

    # Load input text via AdvancedFileParser.parse(...)
    input_path = resolve_path(config['input']['novel_path'], config['input']['novel_path'])
    if not input_path.exists():
        print(f"[ERROR] Không tìm thấy tệp đầu vào: {input_path}")
        return 1

    try:
        from src.preprocessing.file_parser import AdvancedFileParser
        parser = AdvancedFileParser(config)
        parsed = parser.parse(str(input_path))
        text = parsed['text']
        # Upload file gốc lên Gemini để tái sử dụng qua cache
        api_service.get_or_upload_file(str(input_path))
    except Exception as e:
        print(f"[ERROR] Lỗi khi đọc nội dung tác phẩm: {e}")
        return 1

    print("🚀 Bắt đầu quy trình trích xuất Metadata (Sequential)")

    try:
        results = await extractor.extract_metadata_sequential(text, api_service)
    except Exception as e:
        print(f"[ERROR] Quy trình trích xuất thất bại: {e}")
        return 1

    # Save outputs
    ensure_parent_dir(style_path)
    style_json = results.get('style_profile', {})
    with open(style_path, 'w', encoding='utf-8') as f:
        json.dump(style_json, f, ensure_ascii=False, indent=2)

    ensure_parent_dir(glossary_path)
    glossary = results.get('glossary', [])
    # Normalize header order and fill missing columns
    glossary_headers = ['Type', 'Original_Term_Pinyin', 'Original_Term_CN', 'Translated_Term_VI', 'Alternative_Translations', 'Translation_Rule', 'Context_Usage', 'Frequency', 'Notes']
    if glossary:
        normalized_glossary = []
        for row in glossary:
            norm = {h: '' for h in glossary_headers}
            for k, v in row.items():
                if k in norm:
                    norm[k] = v
            normalized_glossary.append(norm)
        with open(glossary_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=glossary_headers)
            writer.writeheader()
            writer.writerows(normalized_glossary)
    else:
        with open(glossary_path, 'w', encoding='utf-8', newline='') as f:
            f.write('Type,Original_Term_Pinyin,Original_Term_CN,Translated_Term_VI,Alternative_Translations,Translation_Rule,Context_Usage,Frequency,Notes\n')

    ensure_parent_dir(relations_path)
    relations = results.get('character_relations', [])
    # Normalize header order and fill missing columns
    relations_headers = ['Character_A', 'Character_B', 'Relationship_Type', 'Pronoun_Rule', 'Context', 'Emotional_State', 'Usage_Example', 'Notes']
    if relations:
        normalized_relations = []
        for row in relations:
            norm = {h: '' for h in relations_headers}
            for k, v in row.items():
                if k in norm:
                    norm[k] = v
            normalized_relations.append(norm)
        with open(relations_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=relations_headers)
            writer.writeheader()
            writer.writerows(normalized_relations)
    else:
        with open(relations_path, 'w', encoding='utf-8', newline='') as f:
            f.write('Character_A,Character_B,Relationship_Type,Pronoun_Rule,Context,Emotional_State,Usage_Example,Notes\n')

    print("✅ Đã tạo 3 tệp metadata:")
    print(f"  - {style_path}")
    print(f"  - {glossary_path}")
    print(f"  - {relations_path}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Trích xuất Metadata (Style → Glossary → Relations)")
    parser.add_argument('--config', type=str, default='config/config.yaml', help='Đường dẫn đến tệp cấu hình YAML.')
    args = parser.parse_args()

    exit_code = asyncio.run(run_extraction(args.config))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
