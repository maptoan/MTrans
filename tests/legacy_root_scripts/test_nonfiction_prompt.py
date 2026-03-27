import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.translation.prompt_builder import PromptBuilder

# Mock Non-Fiction Profile
mock_profile = {
    "doc_info": {
        "title": "Python for Beginners",
        "field": "Programming",
        "difficulty": "Basic"
    },
    "technical_style": {
        "terminology_strictness": "Absolute",
        "sentence_structure": "Imperative"
    }
}

# Create a dummy StyleManager
class MockStyleManager:
    def __init__(self, profile):
        self.profile = profile
        self.style_profile_path = "mock.json"

    def is_loaded(self): return True
    def get_style_summary(self): return "Mock Summary"
    def build_style_instructions(self): return "Mock Instructions"

# Mock other managers
class MockManager:
    def __init__(self): pass

glossary_manager = MockManager()
relation_manager = MockManager()

print("--- TESTING NON-FICTION DETECTION ---")
style_manager = MockStyleManager(mock_profile)
builder = PromptBuilder(style_manager=style_manager, glossary_manager=glossary_manager, relation_manager=relation_manager)


# Access private method to test detection logic
is_nf = builder._is_nonfiction()
print(f"Is Non-Fiction: {is_nf} (Expected: True)")

# Test Guideline Builder
# Access private method directly for testing
guidelines = builder._build_literary_guidelines()

print("\n--- GENERATED GUIDELINES ---")
print(guidelines[:200] + "...")

if "[NGUYÊN TẮC DỊCH NON-FICTION]" in guidelines:
    print("\n✅ SUCCESS: Non-Fiction guidelines generated.")
else:
    print("\n❌ FAILURE: Fiction guidelines generated instead.")


