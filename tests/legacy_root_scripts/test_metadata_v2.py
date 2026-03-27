
import sys
from typing import Dict, List


# Mock class to test methods
class MockMetadataGenerator:
    def __init__(self):
        self.glossary_path = "test_glossary.csv"
        self.relations_path = "test_relations.csv"

    # Paste the modified methods here or import them if possible.
    # For robust testing without complex imports, I will paste the logic I just wrote.

    def _merge_glossary_entries(self, entries: List[Dict]) -> List[Dict]:
        """Gộp các entry glossary, loại bỏ trùng lặp theo Term key phù hợp."""
        seen = {}
        for entry in entries:
            # [FIX] Support multiple key variants (Standard vs Prompt v2.0 vs Legacy)
            key = (entry.get('Original_Term_CN') or
                   entry.get('Original_Term_Chinese') or
                   entry.get('Original_Term_Pinyin') or
                   entry.get('Term') or
                   entry.get('Original Term') or '')

            # Normalize keys to Standard Internal Format for consistency
            if 'Original_Term_Chinese' in entry:
                entry['Original_Term_CN'] = entry.pop('Original_Term_Chinese')
            if 'Translation_Method' in entry:
                entry['Translation_Rule'] = entry.pop('Translation_Method')
            if 'Usage_Context' in entry:
                entry['Context_Usage'] = entry.pop('Usage_Context')
            if 'Frequency_Level' in entry:
                entry['Frequency'] = entry.pop('Frequency_Level')
            if 'Translation_Notes' in entry:
                entry['Notes'] = entry.pop('Translation_Notes')

            if key and key not in seen:
                # IMPORTANT: Create a copy to avoid reference issues in real usage, though here simple
                seen[key] = entry
            elif key and key in seen:
                # Merge: ưu tiên frequency cao hơn hoặc thông tin chi tiết hơn
                old_len = len(str(seen[key].get('Notes', '')))
                new_len = len(str(entry.get('Notes', '')))
                if new_len > old_len:
                    seen[key] = entry

        return list(seen.values())

    def _save_glossary_csv(self, entries: List[Dict]) -> bool:
        """Lưu glossary vào file CSV."""
        if not entries:
            return True

        # Updated Headers to support Prompt v2.0 Rich Metadata
        headers = [
            "Type",
            "Original_Term_Pinyin",
            "Original_Term_CN",
            "Translated_Term_VI",
            "Alternative_Translations",
            "Translation_Rule",
            "Context_Usage",
            "Frequency",
            "First_Appearance",   # New
            "Associated_Info",    # New
            "Notes"
        ]

        try:
            with open(self.glossary_path, 'w', encoding='utf-8-sig', newline='') as f:
                import csv
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(entries)
            print("Saved glossary successfully")
            return True
        except Exception as e:
            print(f"Error saving glossary: {e}")
            return False

# Test Data simulating Prompt v2.0 output
test_data = [
    {
        "Type": "Character",
        "Original_Term_Chinese": "崔小玄",  # New Key
        "Original_Term_Pinyin": "Cuǐ Xiāo Xuán",
        "Translated_Term_VI": "Thôi Tiểu Huyền",
        "Alternative_Translations": "Tiểu Huyền",
        "Translation_Method": "pinyin",       # New Key
        "Usage_Context": "Main char",         # New Key
        "Frequency_Level": "High",            # New Key
        "First_Appearance": "Chapter 1",      # New Key
        "Translation_Notes": "Note v2"        # New Key
    }
]

def run_test():
    gen = MockMetadataGenerator()
    merged = gen._merge_glossary_entries(test_data)
    print("Merged Entry:", merged[0])

    # Check normalization
    assert 'Original_Term_CN' in merged[0], "Failed to normalize Original_Term_Chinese"
    assert 'Translation_Rule' in merged[0], "Failed to normalize Translation_Method"
    assert merged[0]['Original_Term_CN'] == "崔小玄"

    # Save
    gen._save_glossary_csv(merged)

    # Verify file content
    with open("test_glossary.csv", "r", encoding="utf-8-sig") as f:
        content = f.read()
        print("CSV Content:\n", content)
        assert "Original_Term_CN" in content
        assert "First_Appearance" in content
        assert "Thôi Tiểu Huyền" in content

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    run_test()
