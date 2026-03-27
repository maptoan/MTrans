#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A/B Testing Script cho Token Optimization Phase 2

Script này tự động test và so sánh 2 versions của prompt formatting:
- Version A (Control): Safe format (hiện tại)
- Version B (Test): Compact format (mới)

Usage:
    python scripts/ab_testing.py --config config/config.yaml --chunks 10
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.preprocessing.chunker import SmartChunker
from src.preprocessing.file_parser import parse_file
from src.translation.translator import NovelTranslator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ABTesting")


class ABTestMetrics:
    """Collect metrics cho A/B testing"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset metrics"""
        self.prompt_tokens = []
        self.response_tokens = []
        self.total_tokens = []
        self.response_times = []
        self.errors = []
        self.translations = []
    
    def add_result(
        self,
        prompt_tokens: int,
        response_tokens: int,
        response_time: float,
        translation: str,
        error: Optional[str] = None
    ):
        """Add một result"""
        self.prompt_tokens.append(prompt_tokens)
        self.response_tokens.append(response_tokens)
        self.total_tokens.append(prompt_tokens + response_tokens)
        self.response_times.append(response_time)
        self.translations.append(translation)
        if error:
            self.errors.append(error)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        if not self.total_tokens:
            return {}
        
        return {
            'prompt_tokens': {
                'total': sum(self.prompt_tokens),
                'avg': sum(self.prompt_tokens) / len(self.prompt_tokens),
                'min': min(self.prompt_tokens),
                'max': max(self.prompt_tokens)
            },
            'response_tokens': {
                'total': sum(self.response_tokens),
                'avg': sum(self.response_tokens) / len(self.response_tokens),
                'min': min(self.response_tokens),
                'max': max(self.response_tokens)
            },
            'total_tokens': {
                'total': sum(self.total_tokens),
                'avg': sum(self.total_tokens) / len(self.total_tokens),
                'min': min(self.total_tokens),
                'max': max(self.total_tokens)
            },
            'response_times': {
                'total': sum(self.response_times),
                'avg': sum(self.response_times) / len(self.response_times),
                'min': min(self.response_times),
                'max': max(self.response_times)
            },
            'error_count': len(self.errors),
            'error_rate': len(self.errors) / len(self.total_tokens) if self.total_tokens else 0,
            'sample_count': len(self.total_tokens)
        }


class ABTester:
    """A/B Testing class"""
    
    def __init__(self, config_path: str):
        """Initialize với config"""
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            self.base_config = yaml.safe_load(f)
        
        # Create config A (control - safe format)
        self.config_a = self._create_config_a()
        
        # Create config B (test - compact format)
        self.config_b = self._create_config_b()
        
        self.metrics_a = ABTestMetrics()
        self.metrics_b = ABTestMetrics()
    
    def _create_config_a(self) -> Dict[str, Any]:
        """Create config A (control - safe format)"""
        import copy
        config = copy.deepcopy(self.base_config)
        # Ensure safe format
        config['translation']['prompt_compact_format'] = False
        config['translation']['remove_redundant_instructions'] = False
        return config
    
    def _create_config_b(self) -> Dict[str, Any]:
        """Create config B (test - compact format)"""
        import copy
        config = copy.deepcopy(self.base_config)
        # Enable compact format
        config['translation']['prompt_compact_format'] = True
        config['translation']['remove_redundant_instructions'] = True
        return config
    
    def select_sample_chunks(
        self,
        all_chunks: List[Dict[str, Any]],
        count: int
    ) -> List[Dict[str, Any]]:
        """Select sample chunks đại diện"""
        total = len(all_chunks)
        if count >= total:
            return all_chunks
        
        # Select diverse chunks:
        # - First chunk
        # - Middle chunks
        # - Last chunk
        # - Random chunks
        
        selected = []
        indices = set()
        
        # First
        if total > 0:
            indices.add(0)
            selected.append(all_chunks[0])
        
        # Last
        if total > 1:
            indices.add(total - 1)
            selected.append(all_chunks[total - 1])
        
        # Middle
        if total > 2:
            mid = total // 2
            indices.add(mid)
            selected.append(all_chunks[mid])
        
        # Random (fill remaining)
        import random
        remaining = count - len(selected)
        if remaining > 0:
            available = [i for i in range(total) if i not in indices]
            random_indices = random.sample(available, min(remaining, len(available)))
            for idx in random_indices:
                selected.append(all_chunks[idx])
        
        logger.info(f"Selected {len(selected)} sample chunks from {total} total chunks")
        return selected
    
    async def translate_chunk_with_config(
        self,
        chunk: Dict[str, Any],
        config: Dict[str, Any],
        translator: NovelTranslator,
        api_keys: List[str]
    ) -> Dict[str, Any]:
        """Translate một chunk với config cụ thể, có fallback API key"""
        chunk_id = chunk.get('global_id', 0)
        chunk_text = chunk.get('text', '')
        
        start_time = time.time()
        error = None
        prompt_tokens = 0
        response_tokens = 0
        translation = ""
        
        # Get context chunks (empty for now, can be enhanced)
        original_context_chunks = []
        translated_context_chunks = []
        
        # Get relevant terms và active characters từ translator (giống workflow thực tế)
        # Sử dụng full context text để tìm terms và characters
        full_context_text = "\n".join(original_context_chunks or []) + "\n" + chunk_text
        relevant_terms = translator.glossary_manager.find_terms_in_chunk(full_context_text)
        
        # Chỉ detect characters nếu document_type là "novel"
        if translator.document_type == "novel":
            active_characters = translator.relation_manager.find_active_characters(full_context_text)
        else:
            active_characters = []
        
        # Detect potential title
        import re as re_module
        contains_potential_title = bool(re_module.search(r'^(第|Chapter|Chương)', chunk_text.strip(), re_module.IGNORECASE))
        
        # Build prompt (chỉ build một lần)
        prompt = translator.prompt_builder.build_main_prompt(
            chunk_text=chunk_text,
            original_context_chunks=original_context_chunks,
            translated_context_chunks=translated_context_chunks,
            relevant_terms=relevant_terms,
            active_characters=active_characters,
            contains_potential_title=contains_potential_title
        )
        
        # Estimate prompt tokens (rough estimate: ~4 chars per token)
        prompt_tokens = len(prompt) // 4
        
        # Calculate complexity score (simple estimation)
        complexity_score = min(100, max(0, len(chunk_text) // 50))
        
        # Retry với các API keys khác nhau nếu gặp lỗi
        last_error = None
        failed_keys = set()  # Track keys đã fail
        
        for attempt, api_key in enumerate(api_keys, 1):
            if api_key in failed_keys:
                continue  # Skip keys đã fail
            
            try:
                logger.debug(f"Chunk {chunk_id}: Attempt {attempt}/{len(api_keys)} với key {api_key[:10]}...")
                
                # Translate chunk using model router
                result = await translator.model_router.translate_chunk_async(
                    prompt=prompt,
                    complexity_score=complexity_score,
                    api_key=api_key,
                    force_model=None
                )
                
                translation = result.get('translation', '')
                # Estimate response tokens
                response_tokens = len(translation) // 4
                
                # Success - break out of retry loop
                error = None
                break
                
            except Exception as e:
                error_str = str(e)
                last_error = error_str
                
                # Check if error is quota/rate limit related
                is_quota_error = (
                    '429' in error_str or 
                    'RESOURCE_EXHAUSTED' in error_str or
                    'quota' in error_str.lower() or
                    'rate limit' in error_str.lower()
                )
                
                if is_quota_error:
                    logger.warning(f"Chunk {chunk_id}: Key {api_key[:10]}... quota/rate limit - thử key khác...")
                    failed_keys.add(api_key)
                    
                    # Nếu còn keys khác, tiếp tục thử
                    if attempt < len(api_keys):
                        # Thêm delay ngắn trước khi thử key tiếp theo để tránh rate limit
                        delay = 2.0  # 2 giây delay
                        logger.debug(f"Chunk {chunk_id}: Đợi {delay}s trước khi thử key tiếp theo...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Hết keys, return error
                        error = f"All {len(api_keys)} keys exhausted (quota/rate limit): {error_str}"
                        logger.error(f"Chunk {chunk_id}: {error}")
                else:
                    # Lỗi khác (network, invalid key, etc.) - không retry
                    error = error_str
                    logger.error(f"Chunk {chunk_id}: Error với key {api_key[:10]}...: {error_str}")
                    break
        
        # Nếu vẫn có error sau khi thử hết keys
        if error and not translation:
            error = last_error or error
        
        response_time = time.time() - start_time
        
        return {
            'chunk_id': chunk_id,
            'prompt_tokens': prompt_tokens,
            'response_tokens': response_tokens,
            'response_time': response_time,
            'translation': translation,
            'error': error
        }
    
    async def test_version_a(self, sample_chunks: List[Dict[str, Any]]) -> ABTestMetrics:
        """Test Version A (control)"""
        logger.info("=" * 60)
        logger.info("Testing Version A (Control - Safe Format)")
        logger.info("=" * 60)
        
        # Get API keys from config
        # Config structure: api_keys can be dict with 'keys' or direct list
        api_keys_config = self.config_a.get('api_keys', {})
        if isinstance(api_keys_config, dict):
            all_keys = api_keys_config.get('keys', [])
        else:
            all_keys = api_keys_config if isinstance(api_keys_config, list) else []
        valid_keys = [key for key in all_keys if key and "YOUR_GOOGLE_API_KEY" not in key]
        if not valid_keys:
            raise ValueError("No valid API keys found in config")
        
        logger.info(f"Sử dụng {len(valid_keys)} API keys với fallback mechanism")
        
        translator = NovelTranslator(self.config_a, valid_keys)
        metrics = ABTestMetrics()
        
        for i, chunk in enumerate(sample_chunks, 1):
            logger.info(f"Translating chunk {i}/{len(sample_chunks)} (ID: {chunk.get('global_id', 0)})")
            
            result = await self.translate_chunk_with_config(
                chunk=chunk,
                config=self.config_a,
                translator=translator,
                api_keys=valid_keys
            )
            
            metrics.add_result(
                prompt_tokens=result['prompt_tokens'],
                response_tokens=result['response_tokens'],
                response_time=result['response_time'],
                translation=result['translation'],
                error=result.get('error')
            )
        
        return metrics
    
    async def test_version_b(self, sample_chunks: List[Dict[str, Any]]) -> ABTestMetrics:
        """Test Version B (test)"""
        logger.info("=" * 60)
        logger.info("Testing Version B (Test - Compact Format)")
        logger.info("=" * 60)
        
        # Get API keys from config
        # Config structure: api_keys can be dict with 'keys' or direct list
        api_keys_config = self.config_b.get('api_keys', {})
        if isinstance(api_keys_config, dict):
            all_keys = api_keys_config.get('keys', [])
        else:
            all_keys = api_keys_config if isinstance(api_keys_config, list) else []
        valid_keys = [key for key in all_keys if key and "YOUR_GOOGLE_API_KEY" not in key]
        if not valid_keys:
            raise ValueError("No valid API keys found in config")
        
        logger.info(f"Sử dụng {len(valid_keys)} API keys với fallback mechanism")
        
        translator = NovelTranslator(self.config_b, valid_keys)
        metrics = ABTestMetrics()
        
        for i, chunk in enumerate(sample_chunks, 1):
            logger.info(f"Translating chunk {i}/{len(sample_chunks)} (ID: {chunk.get('global_id', 0)})")
            
            result = await self.translate_chunk_with_config(
                chunk=chunk,
                config=self.config_b,
                translator=translator,
                api_keys=valid_keys
            )
            
            metrics.add_result(
                prompt_tokens=result['prompt_tokens'],
                response_tokens=result['response_tokens'],
                response_time=result['response_time'],
                translation=result['translation'],
                error=result.get('error')
            )
        
        return metrics
    
    def compare_results(
        self,
        metrics_a: ABTestMetrics,
        metrics_b: ABTestMetrics
    ) -> Dict[str, Any]:
        """Compare results giữa A và B"""
        stats_a = metrics_a.get_stats()
        stats_b = metrics_b.get_stats()
        
        if not stats_a or not stats_b:
            return {'error': 'No data to compare'}
        
        # Calculate savings
        total_tokens_a = stats_a['total_tokens']['total']
        total_tokens_b = stats_b['total_tokens']['total']
        token_savings = total_tokens_a - total_tokens_b
        token_savings_pct = (token_savings / total_tokens_a * 100) if total_tokens_a > 0 else 0
        
        prompt_tokens_a = stats_a['prompt_tokens']['total']
        prompt_tokens_b = stats_b['prompt_tokens']['total']
        prompt_savings = prompt_tokens_a - prompt_tokens_b
        prompt_savings_pct = (prompt_savings / prompt_tokens_a * 100) if prompt_tokens_a > 0 else 0
        
        # Compare error rates
        error_rate_a = stats_a['error_rate']
        error_rate_b = stats_b['error_rate']
        error_rate_diff = error_rate_b - error_rate_a
        
        # Compare response times
        avg_time_a = stats_a['response_times']['avg']
        avg_time_b = stats_b['response_times']['avg']
        time_diff = avg_time_b - avg_time_a
        time_diff_pct = (time_diff / avg_time_a * 100) if avg_time_a > 0 else 0
        
        comparison = {
            'version_a': {
                'name': 'Control (Safe Format)',
                'stats': stats_a
            },
            'version_b': {
                'name': 'Test (Compact Format)',
                'stats': stats_b
            },
            'comparison': {
                'token_savings': {
                    'total': token_savings,
                    'percentage': token_savings_pct
                },
                'prompt_savings': {
                    'total': prompt_savings,
                    'percentage': prompt_savings_pct
                },
                'error_rate_diff': error_rate_diff,
                'response_time_diff': {
                    'seconds': time_diff,
                    'percentage': time_diff_pct
                }
            },
            'recommendation': self._get_recommendation(
                token_savings_pct,
                error_rate_diff,
                time_diff_pct
            )
        }
        
        return comparison
    
    def _get_recommendation(
        self,
        token_savings_pct: float,
        error_rate_diff: float,
        time_diff_pct: float
    ) -> str:
        """Get recommendation dựa trên results"""
        # Criteria:
        # - Token savings ≥ 5%
        # - Error rate không tăng > 5%
        # - Response time không tăng > 10%
        
        if token_savings_pct < 2:
            return "FAIL: Token savings không đáng kể (< 2%)"
        
        if error_rate_diff > 0.05:  # 5% increase
            return "FAIL: Error rate tăng quá nhiều (> 5%)"
        
        if time_diff_pct > 10:
            return "FAIL: Response time tăng quá nhiều (> 10%)"
        
        if token_savings_pct >= 5 and error_rate_diff <= 0.02:
            return "PASS: Excellent results - recommend enabling"
        elif token_savings_pct >= 3:
            return "PASS: Good results - recommend enabling"
        else:
            return "CONDITIONAL: Marginal savings - test với more samples"
    
    def generate_report(
        self,
        comparison: Dict[str, Any],
        output_file: Optional[str] = None
    ) -> str:
        """Generate report"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("A/B TESTING REPORT - Token Optimization Phase 2")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Version A stats
        report_lines.append("VERSION A (Control - Safe Format):")
        report_lines.append("-" * 80)
        stats_a = comparison['version_a']['stats']
        report_lines.append(f"  Total Tokens: {stats_a['total_tokens']['total']:,} (avg: {stats_a['total_tokens']['avg']:.1f})")
        report_lines.append(f"  Prompt Tokens: {stats_a['prompt_tokens']['total']:,} (avg: {stats_a['prompt_tokens']['avg']:.1f})")
        report_lines.append(f"  Response Tokens: {stats_a['response_tokens']['total']:,} (avg: {stats_a['response_tokens']['avg']:.1f})")
        report_lines.append(f"  Avg Response Time: {stats_a['response_times']['avg']:.2f}s")
        report_lines.append(f"  Error Rate: {stats_a['error_rate']:.2%}")
        report_lines.append(f"  Sample Count: {stats_a['sample_count']}")
        report_lines.append("")
        
        # Version B stats
        report_lines.append("VERSION B (Test - Compact Format):")
        report_lines.append("-" * 80)
        stats_b = comparison['version_b']['stats']
        report_lines.append(f"  Total Tokens: {stats_b['total_tokens']['total']:,} (avg: {stats_b['total_tokens']['avg']:.1f})")
        report_lines.append(f"  Prompt Tokens: {stats_b['prompt_tokens']['total']:,} (avg: {stats_b['prompt_tokens']['avg']:.1f})")
        report_lines.append(f"  Response Tokens: {stats_b['response_tokens']['total']:,} (avg: {stats_b['response_tokens']['avg']:.1f})")
        report_lines.append(f"  Avg Response Time: {stats_b['response_times']['avg']:.2f}s")
        report_lines.append(f"  Error Rate: {stats_b['error_rate']:.2%}")
        report_lines.append(f"  Sample Count: {stats_b['sample_count']}")
        report_lines.append("")
        
        # Comparison
        report_lines.append("COMPARISON:")
        report_lines.append("-" * 80)
        comp = comparison['comparison']
        report_lines.append(f"  Token Savings: {comp['token_savings']['total']:,} ({comp['token_savings']['percentage']:.2f}%)")
        report_lines.append(f"  Prompt Savings: {comp['prompt_savings']['total']:,} ({comp['prompt_savings']['percentage']:.2f}%)")
        report_lines.append(f"  Error Rate Difference: {comp['error_rate_diff']:.2%}")
        report_lines.append(f"  Response Time Difference: {comp['response_time_diff']['seconds']:.2f}s ({comp['response_time_diff']['percentage']:.2f}%)")
        report_lines.append("")
        
        # Recommendation
        report_lines.append("RECOMMENDATION:")
        report_lines.append("-" * 80)
        report_lines.append(f"  {comparison['recommendation']}")
        report_lines.append("")
        
        report_lines.append("=" * 80)
        
        report_text = "\n".join(report_lines)
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"Report saved to: {output_file}")
        
        return report_text


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='A/B Testing cho Token Optimization')
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Path to config file'
    )
    parser.add_argument(
        '--novel',
        type=str,
        required=True,
        help='Path to novel file để test'
    )
    parser.add_argument(
        '--chunks',
        type=int,
        default=5,
        help='Số lượng sample chunks để test (default: 5)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file cho report (optional)'
    )
    
    args = parser.parse_args()
    
    # Check files exist
    if not Path(args.config).exists():
        logger.error(f"Config file not found: {args.config}")
        return
    
    if not Path(args.novel).exists():
        logger.error(f"Novel file not found: {args.novel}")
        return
    
    # Initialize tester
    tester = ABTester(args.config)
    
    # Load và chunk novel
    logger.info(f"Loading novel: {args.novel}")
    config = tester.config_a  # Use config A để load novel
    raw_text = parse_file(args.novel, config)
    from src.preprocessing.text_cleaner import clean_text
    cleaned_text = clean_text(raw_text, config)
    
    chunker = SmartChunker(config)
    all_chunks = chunker.chunk_novel(cleaned_text)
    
    if not all_chunks:
        logger.error("No chunks found in novel")
        return
    
    # Select sample chunks
    sample_chunks = tester.select_sample_chunks(all_chunks, args.chunks)
    
    # Test Version A
    logger.info("\n" + "=" * 60)
    logger.info("Starting Version A (Control) Test")
    logger.info("=" * 60)
    metrics_a = await tester.test_version_a(sample_chunks)
    
    # Test Version B
    logger.info("\n" + "=" * 60)
    logger.info("Starting Version B (Test) Test")
    logger.info("=" * 60)
    metrics_b = await tester.test_version_b(sample_chunks)
    
    # Compare results
    logger.info("\n" + "=" * 60)
    logger.info("Comparing Results")
    logger.info("=" * 60)
    comparison = tester.compare_results(metrics_a, metrics_b)
    
    # Generate report
    output_file = args.output or f"ab_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report = tester.generate_report(comparison, output_file)
    
    # Print report (an toàn với encoding của terminal)
    try:
        print("\n" + report)
    except UnicodeEncodeError:
        # Fallback: chỉ thông báo đường dẫn report nếu terminal không hỗ trợ kí tự Unicode
        try:
            print(f"\nReport saved to: {output_file}")
        except UnicodeEncodeError:
            logger.info(f"Report saved to: {output_file}")
        logger.warning("Could not print full report due to terminal encoding limitations.")
    
    logger.info("A/B Testing completed!")


if __name__ == "__main__":
    asyncio.run(main())
