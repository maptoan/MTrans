
import logging

from src.preprocessing.chunker import SmartChunker

# Configure logger to see output
logging.basicConfig(level=logging.INFO)

def verify_fix():
    print("Initializing SmartChunker...")
    config = {
        'preprocessing': {
            'chunking': {
                'adaptive_mode': False,
                'counter_mode': 'cjk_weighted' # Test explicit config
            }
        },
        'translation': {}
    }

    try:
        chunker = SmartChunker(config)
        print("SmartChunker initialized successfully.")

        text = "Hello World. Xin chào."
        count = chunker._count_tokens(text)
        print(f"Token count: {count}")

        if count > 0:
            print("SUCCESS: _count_tokens worked.")
        else:
            print("WARNING: count is 0.")

    except AttributeError as e:
        print(f"FAILED: AttributeError: {e}")
    except Exception as e:
        print(f"FAILED: Exception: {e}")

if __name__ == "__main__":
    verify_fix()
