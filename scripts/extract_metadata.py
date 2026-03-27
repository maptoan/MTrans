#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tích hợp để extract metadata từ novel sử dụng các prompt đã tối ưu hóa.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

import logging

from src.metadata.metadata_extractor import MetadataExtractor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("MetadataExtractor")


async def extract_metadata_from_novel(novel_file: str, api_key: str, output_dir: str = "data/metadata"):
    """
    Extract metadata từ novel file.
    
    Args:
        novel_file: Đường dẫn đến file novel
        api_key: Gemini API key
        output_dir: Thư mục output
    """
    try:
        # Load novel content
        with open(novel_file, 'r', encoding='utf-8') as f:
            novel_content = f.read()
        
        logger.info(f"Loaded novel content from: {novel_file}")
        logger.info(f"Content length: {len(novel_content)} characters")
        
        # Initialize extractor
        extractor = MetadataExtractor(
            prompts_dir="prompts/notebooklm",
            output_dir=output_dir,
            api_key=api_key
        )
        
        # Extract all metadata
        logger.info("Starting comprehensive metadata extraction...")
        results = await extractor.extract_all_metadata(novel_content)
        
        # Print results
        print("\n" + "="*60)
        print("🎉 METADATA EXTRACTION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"📊 Style Profile: {results['_summary']['style_profile_keys']} keys")
        print(f"📚 Glossary: {results['_summary']['glossary_terms']} terms")
        print(f"👥 Character Relations: {results['_summary']['character_relations']} relations")
        print("\n📁 Output Files:")
        for file_type, file_path in results['_summary']['output_files'].items():
            print(f"  - {file_type}: {file_path}")
        
        # Validate extracted metadata
        logger.info("Validating extracted metadata...")
        validation_results = extractor.validate_extracted_metadata()
        
        print("\n🔍 Validation Results:")
        all_valid = True
        for file_type, result in validation_results.items():
            if file_type != '_summary':
                status = "✅ Valid" if result['valid'] else "❌ Invalid"
                print(f"  {file_type}: {status}")
                if result['errors']:
                    print(f"    Errors: {', '.join(result['errors'])}")
                    all_valid = False
        
        if all_valid:
            print("\n🎯 All metadata files are valid and ready for use!")
        else:
            print("\n⚠️  Some metadata files have validation errors. Please check the logs.")
        
        return results
        
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        print(f"❌ Error: {e}")
        return None


def main():
    """
    Main function với CLI interface.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract metadata from novel using enhanced prompts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all metadata
  python extract_metadata.py --novel-file "data/input/novel.txt" --api-key "your_api_key"
  
  # Extract with custom output directory
  python extract_metadata.py --novel-file "data/input/novel.txt" --api-key "your_api_key" --output-dir "custom_metadata"
  
  # Extract specific metadata only
  python extract_metadata.py --novel-file "data/input/novel.txt" --api-key "your_api_key" --extract-style
  python extract_metadata.py --novel-file "data/input/novel.txt" --api-key "your_api_key" --extract-glossary
  python extract_metadata.py --novel-file "data/input/novel.txt" --api-key "your_api_key" --extract-relations
        """
    )
    
    parser.add_argument('--novel-file', type=str, required=True, 
                       help='Path to novel file (txt, epub, etc.)')
    parser.add_argument('--api-key', type=str, required=True,
                       help='Gemini API key')
    parser.add_argument('--output-dir', type=str, default='data/metadata',
                       help='Output directory for metadata files (default: data/metadata)')
    parser.add_argument('--extract-style', action='store_true',
                       help='Extract style profile only')
    parser.add_argument('--extract-glossary', action='store_true',
                       help='Extract glossary only')
    parser.add_argument('--extract-relations', action='store_true',
                       help='Extract character relations only')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate existing metadata files')
    
    args = parser.parse_args()
    
    # Check if novel file exists
    if not os.path.exists(args.novel_file):
        print(f"❌ Novel file not found: {args.novel_file}")
        return
    
    # Check if API key is provided
    if not args.api_key:
        print("❌ API key is required")
        return
    
    # Run extraction
    if args.validate_only:
        # Only validate existing files
        extractor = MetadataExtractor(output_dir=args.output_dir)
        validation_results = extractor.validate_extracted_metadata()
        
        print("🔍 Validation Results:")
        all_valid = True
        for file_type, result in validation_results.items():
            if file_type != '_summary':
                status = "✅ Valid" if result['valid'] else "❌ Invalid"
                print(f"  {file_type}: {status}")
                if result['errors']:
                    print(f"    Errors: {', '.join(result['errors'])}")
                    all_valid = False
        
        if all_valid:
            print("\n🎯 All metadata files are valid!")
        else:
            print("\n⚠️  Some metadata files have validation errors.")
    else:
        # Extract metadata
        asyncio.run(extract_metadata_from_novel(
            novel_file=args.novel_file,
            api_key=args.api_key,
            output_dir=args.output_dir
        ))


if __name__ == "__main__":
    main()
