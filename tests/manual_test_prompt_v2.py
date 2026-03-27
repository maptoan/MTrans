import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.translation.prompt_builder import PromptBuilder


# Mock Managers
class MockGlossaryManager:
    def build_prompt_section(self, terms):
        return "GLOSSARY_SECTION_PLACEHOLDER"
    def build_compact_prompt_section(self, terms):
        return "COMPACT_GLOSSARY_PLACEHOLDER"

class MockStyleManager:
    def __init__(self):
        self.profile = {"tone": "Epic"}
    def build_style_instructions(self):
        return "STYLE_INSTRUCTION_PLACEHOLDER"
    def is_loaded(self):
        return True
    def get_style_summary(self):
        return "STYLE_SUMMARY_PLACEHOLDER"

class MockRelationManager:
    def build_prompt_section(self, chars):
        return "RELATION_SECTION_PLACEHOLDER"

def test_prompt_generation():
    output_path = "test_prompt_output_v2.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== TESTING PROMPT BUILDER V1.3 (REFACTORED) ===\n\n")

        # Initialize
        style_mgr = MockStyleManager()
        glossary_mgr = MockGlossaryManager()
        relation_mgr = MockRelationManager()

        builder = PromptBuilder(
            style_manager=style_mgr,
            glossary_manager=glossary_mgr,
            relation_manager=relation_mgr,
            document_type="novel",
            config={'translation': {'prompt_compact_format': True, 'remove_redundant_instructions': True}}
        )

        # Fake Data
        chunk_text = "Nàng bước vào phòng. Ánh mắt nhìn hắn lạnh lùng. 'Ngươi đi đi.' Hắn không nói gì, chỉ lặng lẽ rời khỏi."

        f.write(">>> 1. CHECKING LITERARY GUIDELINES (EXAMPLE MATRIX) <<<\n")
        guidelines = builder._build_literary_guidelines()
        f.write(guidelines + "\n")
        f.write("\n" + "="*50 + "\n\n")

        f.write(">>> 2. CHECKING EDITING COMMANDS (GOLDEN RULES) <<<\n")
        commands = builder._build_novel_editing_commands_optimized(contains_potential_title=True)
        f.write(commands + "\n")
        f.write("\n" + "="*50 + "\n\n")

        f.write(">>> 3. FULL PROMPT PREVIEW (USER MESSAGE ONLY) <<<\n")
        # Simulate build
        messages = builder.build_main_messages(
            chunk_text=chunk_text,
            original_context_chunks=[],
            translated_context_chunks=[],
            relevant_terms=[],
            active_characters=['Nàng', 'Hắn'],
            contains_potential_title=False
        )

        if messages:
            f.write(messages[0]['parts'][0]['text'] + "\n")

    print(f"Output generated at {output_path}")

if __name__ == "__main__":
    test_prompt_generation()
