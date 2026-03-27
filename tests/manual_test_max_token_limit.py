
import asyncio
import logging
import os
import random
import sys
import time

import yaml

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.genai_adapter import GenAIClient

# from src.utils.token_counter import TokenCounter # Removed
# Mock simple counter if needed
pass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TokenLimitTest")

async def test_token_limit():
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    api_keys = config.get('api_keys', [])
    if not api_keys:
        logger.error("No API keys found in config")
        return

    # Use a random key to avoid rate limits on first one
    api_key = random.choice(api_keys)
    logger.info(f"Using API Key: {api_key[:10]}...")

    # Initialize Client
    try:
        client = GenAIClient(api_key=api_key, use_new_sdk=True)
    except Exception as e:
        logger.error(f"Failed to init client: {e}")
        return

    model_name = "gemini-3-pro-preview" # Target model

    # Test cases: increasing token counts (Small for availability check)
    test_sizes = [100, 500, 1000]

    # Simple multiplier to estimate tokens -> chars (approx 4 chars / token)
    # 25000 tokens ~ 100000 chars

    base_text = "Đây là một đoạn văn bản mẫu để kiểm tra giới hạn token của mô hình AI. " * 10

    logger.info(f"🚀 Starting Token Limit Stress Test on {model_name}")
    logger.info("==================================================")

    for target_tokens in test_sizes:
        estimated_chars = target_tokens * 4 # Rough estimate for English/Vietnamese mix

        # Construct payload
        current_text = ""
        while len(current_text) < estimated_chars:
            current_text += base_text

        current_text = current_text[:estimated_chars]
        real_len = len(current_text)

        logger.info(f"\n🧪 Testing ~{target_tokens} tokens (Length: {real_len} chars)...")

        prompt = f"Hãy dịch đoạn văn sau sang tiếng Việt (giữ nguyên độ dài tương ứng):\n\n{current_text}"

        start_time = time.time()
        try:
            # Call API
            # Note: generate_content_async expects 'prompt' argument
            response = await client.client.aio.models.generate_content(
                model=model_name,
                contents=prompt
            )

            elapsed = time.time() - start_time

            if response and response.text:
                output_len = len(response.text)
                logger.info(f"✅ SUCCESS: ~{target_tokens} tokens | Time: {elapsed:.2f}s | Output Len: {output_len}")

                # Verify completeness (rough check)
                ratio = output_len / real_len
                if ratio < 0.5:
                    logger.warning(f"⚠️  Potential Truncation? Output ratio: {ratio:.2f}")
                else:
                    logger.info(f"   Completeness looks good (Ratio: {ratio:.2f})")
            else:
                 logger.error(f"❌ FAILED: No output text returned for {target_tokens} tokens")

        except Exception as e:
            logger.error(f"❌ CRASH: ~{target_tokens} tokens | Error: {str(e)[:200]}")
            # If 503, maybe wait and retry? NO, this is stress test.
            if "503" in str(e):
                logger.warning("   (Server Overload - 503)")

        # Cooldown to avoid 429 affecting next test
        await asyncio.sleep(5)

    await client.client.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_token_limit())
