
import cProfile
import io
import os
import pstats
import re
import sys
import time

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, PROJECT_ROOT)

import src.utils.logger  # Patches logging.Logger
from src.managers.glossary_manager import GlossaryManager
from src.managers.relation_manager import RelationManager
from src.managers.style_manager import StyleManager
from src.preprocessing.chunker import SmartChunker
from src.translation.prompt_builder import PromptBuilder

# Mock config
MOCK_CONFIG = {
    "translation": {
        "context": {"max_context_tokens": 1000},
        "use_multi_turn": True
    },
    "chunking": {
        "max_tokens": 2000,
        "min_tokens": 100
    }
}

DUMMY_NOVEL = "data/profiling_dummy/dummy_novel.txt"
DUMMY_GLOSSARY = "data/profiling_dummy/dummy_glossary.csv"

def profile_glossary(manager, text):
    print("\n--- Profiling GlossaryManager.find_terms_in_chunk ---")
    start = time.time()
    terms = manager.find_terms_in_chunk(text)
    end = time.time()
    print(f"Terms found: {len(terms)}")
    print(f"Time taken: {end - start:.4f}s")
    
def profile_prompt_builder(builder, text, glossary_terms):
    print("\n--- Profiling PromptBuilder.build_main_prompt ---")
    # Mock data
    original_context = ["Previous context chunk 1", "Previous context chunk 2"]
    translated_context = ["Dịch chunk 1", "Dịch chunk 2"]
    active_chars = ["Xiao Yan"]
    
    start = time.time()
    prompt = builder.build_main_prompt(
        chunk_text=text,
        original_context_chunks=original_context,
        translated_context_chunks=translated_context,
        relevant_terms=glossary_terms,
        active_characters=active_chars,
        contains_potential_title=False
    )
    end = time.time()
    print(f"Prompt length: {len(str(prompt))} chars")
    print(f"Time taken: {end - start:.4f}s")

def profile_chunker(chunker, text):
    print("\n--- Profiling SmartChunker.chunk_novel ---")
    start = time.time()
    chunks = chunker.chunk_novel(text)
    end = time.time()
    print(f"Chunks created: {len(chunks)}")
    print(f"Time taken: {end - start:.4f}s")

def main():
    if not os.path.exists(DUMMY_NOVEL):
        print(f"Error: {DUMMY_NOVEL} not found. Run generate_dummy_data.py first.")
        return

    # Load data
    with open(DUMMY_NOVEL, "r", encoding="utf-8") as f:
        text = f.read()

    # Init components
    glossary = GlossaryManager(DUMMY_GLOSSARY)
    
    # Initialize dependencies with dummy paths (they handle missing files gracefully)
    relation_manager = RelationManager("", glossary_manager=glossary)
    style_manager = StyleManager("")
    
    prompt_builder = PromptBuilder(
        style_manager=style_manager,
        glossary_manager=glossary, 
        relation_manager=relation_manager,
        config=MOCK_CONFIG
    )
    chunker = SmartChunker(MOCK_CONFIG)

    # cProfile Wrapper (Optional, skip if another profiler is active)
    pr = None
    if "--internal" in sys.argv:
        try:
            pr = cProfile.Profile()
            pr.enable()
        except ValueError:
            print("Warning: Could not start internal cProfile (another profiler may be active).")
            pr = None

    # Run logic
    profile_chunker(chunker, text * 10) # 10x text for load
    
    # Use first chunk for deep analysis
    first_chunk = text[:2000] 
    glossary_terms = glossary.find_terms_in_chunk(first_chunk)
    
    # Run loop for prompt builder to see cumulative impact
    for _ in range(100):
        profile_prompt_builder(prompt_builder, first_chunk, glossary_terms)

    if pr:
        pr.disable()

        # Stats
        s = io.StringIO()
        sortby = pstats.SortKey.CUMULATIVE
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats(20) # Top 20
        
        print("\n=== TOP 20 CUMULATIVE TIME ===")
        print(s.getvalue())

        # Dump stats
        pr.dump_stats("scripts/profiling/profile_core.stats")
        print("Saved stats to scripts/profiling/profile_core.stats")
    else:
        print("\nInternal cProfile skipped. Use --internal to force it, or use external profilers (Scalene/py-spy).")

if __name__ == "__main__":
    main()
