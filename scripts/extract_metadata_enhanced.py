#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Metadata Extraction CLI
Sử dụng API key rotation và quota management
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import logging

from src.integration.metadata_integration_v2 import (
    EnhancedMetadataIntegration,
    cli_extract_metadata,
    cli_show_metadata_status,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("EnhancedMetadataExtractor")


async def main():
    """
    Main CLI function
    """
    parser = argparse.ArgumentParser(
        description='Enhanced Metadata Extraction với API Key Rotation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all metadata
  python extract_metadata_enhanced.py --novel-file "data/input/novel.txt" --config "config/config.yaml"
  
  # Extract specific metadata
  python extract_metadata_enhanced.py --novel-file "data/input/novel.txt" --extract-style --extract-glossary
  
  # Show metadata status
  python extract_metadata_enhanced.py --show-status --config "config/config.yaml"
  
  # Test API keys
  python extract_metadata_enhanced.py --test-api-keys --config "config/config.yaml"
        """
    )
    
    # Required arguments
    parser.add_argument('--config', type=str, default='config/config.yaml',
                       help='Path to config.yaml file')
    
    # Novel file
    parser.add_argument('--novel-file', type=str,
                       help='Path to novel file for extraction')
    
    # Extraction options
    parser.add_argument('--extract-all', action='store_true',
                       help='Extract all metadata (default)')
    parser.add_argument('--extract-style', action='store_true',
                       help='Extract style profile only')
    parser.add_argument('--extract-glossary', action='store_true',
                       help='Extract glossary only')
    parser.add_argument('--extract-relations', action='store_true',
                       help='Extract character relations only')
    
    # Other options
    parser.add_argument('--show-status', action='store_true',
                       help='Show metadata status and API key status')
    parser.add_argument('--test-api-keys', action='store_true',
                       help='Test all API keys')
    parser.add_argument('--validate', action='store_true',
                       help='Validate existing metadata files')
    parser.add_argument('--cleanup', action='store_true',
                       help='Cleanup metadata files (with backup)')
    
    args = parser.parse_args()
    
    # Load config
    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from: {args.config}")
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return 1
    
    # Check API keys
    api_keys = config.get('api_keys', [])
    if not api_keys:
        logger.error("No API keys found in config")
        return 1
    
    logger.info(f"Found {len(api_keys)} API keys in config")
    
    # Initialize integration
    try:
        integration = EnhancedMetadataIntegration(config)
    except Exception as e:
        logger.error(f"Error initializing integration: {e}")
        return 1
    
    # Handle different commands
    try:
        if args.show_status:
            # Show metadata status
            integration.print_metadata_status()
            return 0
        
        if args.test_api_keys:
            # Test API keys
            print("🔑 Testing API keys...")
            test_results = await integration.test_api_keys()
            
            print("\n📊 API Key Test Results:")
            for i, (key, result) in enumerate(test_results.items(), 1):
                status = "✅ Active" if result else "❌ Inactive"
                print(f"  {i}. {key[:10]}...: {status}")
            
            active_count = sum(1 for result in test_results.values() if result)
            print(f"\n✅ {active_count}/{len(test_results)} API keys are active")
            
            if active_count == 0:
                print("❌ No active API keys found!")
                return 1
            
            return 0
        
        if args.validate:
            # Validate existing metadata
            print("🔍 Validating metadata files...")
            validation = integration.validate_metadata_files()
            
            print("\n📋 Validation Results:")
            for file_type, result in validation.items():
                if file_type != '_summary':
                    status = "✅ Valid" if result else "❌ Invalid"
                    print(f"  {file_type}: {status}")
            
            all_valid = all(validation.values())
            print(f"\nOverall: {'✅ All valid' if all_valid else '❌ Some invalid'}")
            
            return 0
        
        if args.cleanup:
            # Cleanup metadata files
            print("🧹 Cleaning up metadata files...")
            integration.cleanup_metadata_files(backup=True)
            print("✅ Cleanup completed with backup")
            return 0
        
        if args.novel_file:
            # Extract metadata
            if not os.path.exists(args.novel_file):
                logger.error(f"Novel file not found: {args.novel_file}")
                return 1
            
            # Determine extraction type
            if args.extract_style or args.extract_glossary or args.extract_relations:
                extract_all = False
            else:
                extract_all = True
            
            # Extract metadata
            results = await cli_extract_metadata(args.novel_file, config)
            
            if results:
                print("\n🎉 Metadata extraction completed successfully!")
                return 0
            else:
                print("\n❌ Metadata extraction failed!")
                return 1
        
        else:
            # No novel file provided, show help
            parser.print_help()
            return 0
    
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
