
import logging
import os
import sys
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.managers.glossary_manager import GlossaryManager
from src.managers.relation_manager import RelationManager
from src.managers.style_manager import StyleManager
from src.translation.prompt_builder import PromptBuilder

# Setup logger to avoid errors
logging.basicConfig(level=logging.INFO)

def verify_prompt():
    # Mock Managers
    style_manager = MagicMock(spec=StyleManager)
    style_manager.profile = {}
    style_manager.build_style_instructions.return_value = "Keep it simple."

    glossary_manager = MagicMock(spec=GlossaryManager)
    glossary_manager.build_prompt_section.return_value = "Some Glossary"
    # Important: The real method uses build_compact_prompt_section
    # We should let the REAL GlossaryManager method run if possible, but testing PromptBuilder calling it.
    # Since we mocked it, we must mock the compact method too IF PromptBuilder calls it directly.
    # Updated PromptBuilder calls: self.glossary_manager.build_compact_prompt_section(relevant_terms)
    glossary_manager.build_compact_prompt_section.return_value = "G:{Test->ThuNghiem}"

    relation_manager = MagicMock(spec=RelationManager)
    relation_manager.build_prompt_section.return_value = "Relations..."
    relation_manager.build_narrative_prompt_section.return_value = "Narrative..."

    # Config enabling compact format
    config = {'prompt_compact_format': True}

    # Initialize PromptBuilder
    builder = PromptBuilder(
        style_manager=style_manager,
        glossary_manager=glossary_manager,
        relation_manager=relation_manager,
        document_type="novel",
        config=config
    )
    # Ensure flag is set (constructor should read it)
    builder.prompt_compact_format = True

    # Dummy Data
    chunk_text = "This is a test chunk."
    context_chunks = ["Context 1 text.", "Context 2 text matches style."]
    relevant_terms = [{'original': 'Test', 'translation': 'ThuNghiem'}]

    # Build Prompt
    prompt = builder.build_main_prompt(
        chunk_text=chunk_text,
        original_context_chunks=[],
        translated_context_chunks=context_chunks,
        relevant_terms=relevant_terms,
        active_characters=[],
        contains_potential_title=False
    )

    print("--- Generated Prompt ---")
    print(prompt)
    print("------------------------")

    # Assertions
    if "G:{Test->ThuNghiem}" in prompt:
        print("✅ Compact Glossary found.")
    else:
        print("❌ Compact Glossary NOT found.")

    if "[PREV_CTX]" in prompt and "STYLE:" in prompt:
        print("✅ Compact Context Layout found.")
    else:
        print("❌ Compact Context Layout NOT found.")

if __name__ == "__main__":
    verify_prompt()
