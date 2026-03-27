import re


def reproduce_quote_issue():
    # Simulated translated text with some punctuation and quotes
    text = '"Where are you going?" he asked. "I don\'t know." - she replied.'
    
    # Logic from translator.py _find_sentences_with_missed_terms
    # 940: sentences = re.split(r'[.!?。！？\n\r]+', text)
    sentences = re.split(r'[.!?\n\r]+', text)
    
    print(f"Original text: {text}")
    print(f"Split results: {sentences}")
    
    # Example of what happens if AI returns a translation without quotes
    # because it was asked to "dịch lại CÁC CÂU GỐC" and it might strip them
    # OR because the split logic itself breaks the sentence at the question mark.
    
    # If the first 'sentence' is '"Where are you going', it is missing its closing ?"
    # If the AI translates it to 'Ban di dau', and we replace:
    
    # The actual code in translator.py does:
    # 1060: cleaned_text = cleaned_text.replace(original, translation)
    
    # In reality, if text is: "Where are you going?"
    # sentences = ['"Where are you going', '"', '']
    
    # If original = '"Where are you going' (from sentences[0])
    # AND translation = 'Ban di dau'
    # text.replace('"Where are you going', 'Ban di dau') -> 'Ban di dau?"'
    
    # Wait, if the second quote survives, it's not "missing all quotes".
    # BUT if the AI's translation ALSO includes the quote but it doesn't match?
    
    # Let's try another scenario: TheAI DECIDES to use different quotes or no quotes.
    
    print("\n--- Testing literal replacement ---")
    original = '"Where are you going'
    translation = 'Ban di dau' # Missing leading quote
    result = text.replace(original, translation)
    print(f"Result: {result}")

if __name__ == "__main__":
    reproduce_quote_issue()
