
import asyncio
import builtins
import cProfile
import os
import pstats
import sys
from unittest.mock import patch

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import main functions
from main import main_async, main_sync


def mock_input(prompt):
    """Auto-answer inputs for profiling automation."""
    print(f"[MOCKE_INPUT] {prompt} -> '1'")
    return "1"  # Always select option 1 (Translate)

def profile_run():
    # 1. Run sync setup first (outside profiler to reduce noise)
    print(">> Running setup...")
    result = main_sync()
    if not result:
        return
    config, valid_keys = result

    # 2. Patch input to avoid blocking
    with patch('builtins.input', side_effect=mock_input):
        print("🚀 Starting cProfile on main_async...")
        profiler = cProfile.Profile()
        try:
            profiler.enable()
            # Run the main async loop
            asyncio.run(main_async(config, valid_keys))
        except SystemExit:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            profiler.disable()
            
            # 3. Save and print stats
            output_file = 'profile.out'
            print(f"\n✅ Profiling finished. Saving stats to '{output_file}'...")
            stats = pstats.Stats(profiler)
            stats.strip_dirs().sort_stats('cumtime').dump_stats(output_file)
            
            print("\n📊 TOP 20 FUNCTIONS BY CUMULATIVE TIME:")
            stats.print_stats(20)

if __name__ == "__main__":
    profile_run()
