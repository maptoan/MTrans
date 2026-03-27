import urllib.request
import json
import os
import sys

def list_models_direct(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    print(f"Calling: https://generativelanguage.googleapis.com/v1beta/models?key=XXX")
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            models = data.get('models', [])
            
            print(f"{'Model Name':<45} | {'Description'}")
            print("-" * 100)
            
            supported_count = 0
            for m in models:
                name = m.get('name', '').replace('models/', '')
                # Filter for generateContent
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    desc = m.get('description', '')[:50]
                    print(f"{name:<45} | {desc}...")
                    supported_count += 1
            
            print("-" * 100)
            print(f"Total supported models found: {supported_count}")
            
    except Exception as e:
        print(f"Error fetching models: {e}")

if __name__ == "__main__":
    KEY = os.getenv("GEMINI_API_KEY", "").strip()
    if len(sys.argv) > 1:
        KEY = sys.argv[1]
    if not KEY:
        print("Usage: python scripts/list_all_models.py <API_KEY>")
        print("Hoặc set biến môi trường GEMINI_API_KEY.")
        sys.exit(1)
    list_models_direct(KEY)
