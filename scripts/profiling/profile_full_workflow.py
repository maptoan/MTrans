
import asyncio
import os
import random
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, PROJECT_ROOT)

import src.utils.logger  # Patches logging.Logger
from src.translation.translator import NovelTranslator

DUMMY_NOVEL = "data/profiling_dummy/dummy_novel.txt"
DUMMY_GLOSSARY = "data/profiling_dummy/dummy_glossary.csv"

# Centralized Model Name
MODEL_NAME = "gemini-3-flash-preview"

# Mock config
MOCK_CONFIG = {
    "input": {"novel_path": DUMMY_NOVEL},
    "output": {"output_dir": "data/profiling_out"},
    "api_keys": ["KEY1", "KEY2", "KEY3"], # Mock keys
    "translation": {
        "model": MODEL_NAME,
        "glossary_path": DUMMY_GLOSSARY,
        "qa_editor": {"enabled": True}, 
        "context_caching": {"enabled": False}
    },
    "performance": {
        "max_workers": 10,  
        "delay_between_requests": 0.0,
        "max_requests_per_minute": 1000,
        "min_delay_between_requests": 0.0
    },
    "logging": {"suppress_grpc_logs": True},
    "models": {
        "flash": MODEL_NAME,
        "pro": MODEL_NAME
    }
}

class MockGenAIClient:
    """Mock for src.services.genai_adapter.GenAIClient"""
    def __init__(self, api_key, **kwargs):
        self.api_key = api_key
        self.use_new_sdk = True
        self.client = MagicMock()

    async def generate_content_async(self, *args, **kwargs):
        """Simulate API call with latency."""
        await asyncio.sleep(random.uniform(0.01, 0.05)) # Very low latency
        if random.random() < 0.02: # 2% failure
            raise Exception("429 Resource exhausted (Mock)")
            
        # Use a simple class instead of MagicMock for attribute access
        class MockUsage:
            def __init__(self):
                self.total_token_count = 100
                self.prompt_token_count = 50
                self.candidates_token_count = 50

        class MockCandidate:
            def __init__(self):
                self.text = "Mocked text"

        class MockResponse:
            def __init__(self):
                self.text = "This is a mocked translation result."
                self.usage_metadata = MockUsage()
                self.candidates = [MockCandidate()]
        
        return MockResponse()

    async def count_tokens_async(self, *args, **kwargs):
        return 1234
        
    async def aclose(self):
        pass
    
    def close(self):
        pass

async def run_profiling():
    print(f"\n--- Profiling Full Workflow with Mocked API ({MODEL_NAME}) ---")
    
    # 1. Patch create_client to inject MockGenAIClient
    # 2. Patch GlobalRateLimiter.acquire to bypass pauses during profiling
    with patch('src.services.genai_adapter.create_client', side_effect=lambda **kwargs: MockGenAIClient(**kwargs)), \
         patch('src.services.smart_key_distributor.GlobalRateLimiter.acquire', new_callable=AsyncMock):
        
        # Init Translator
        translator = NovelTranslator(MOCK_CONFIG, MOCK_CONFIG["api_keys"])
        
        # Run setup (this will now use mocked clients)
        await translator.setup_resources_async()
        
        # Check data
        if not os.path.exists(DUMMY_NOVEL):
             print(f"Error: {DUMMY_NOVEL} not found. Run generate_dummy_data.py first.")
             return

        with open(DUMMY_NOVEL, "r", encoding="utf-8") as f:
            text = f.read()
        
        # Create dummy chunks
        # Process 20 chunks to see if it handles concurrency/scaling
        chunks = [{"global_id": i, "text": text[:500]} for i in range(20)]
        
        print(f"Processing {len(chunks)} chunks concurrently...")
        start_time = time.time()
        
        tasks = []
        for chunk in chunks:
            task = translator._translate_one_chunk_worker(
                chunk=chunk,
                original_context_chunks=[],
                translated_context_chunks=[],
                worker_id=0,
                api_key="KEY1",
                cache_name=None
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        print(f"Processed {len(results)} chunks in {end_time - start_time:.4f}s")
        
        success_count = sum(1 for r in results if r.get('status') != 'failed')
        print(f"Success/Total: {success_count}/{len(results)}")

if __name__ == "__main__":
    asyncio.run(run_profiling())
