
import os
import zipfile

import yaml
from google import genai
from google.genai import types

# Path setup
CONFIG_PATH = "config/config.yaml"
SOURCE_FILE = "tests/TOKEN_OPTIMIZATION_PLAN.md"
ZIP_FILE = "tests/payload.zip"
PROMPT_FILE = "tests/prompt.txt"


def load_api_keys():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            keys = config.get("api_keys", [])
            return keys
    except Exception as e:
        print(f"Error loading config: {e}")
    return []

def create_payload():
    # 1. Create prompt.txt
    instruction = "Nhiệm vụ: Dịch toàn bộ nội dung file TOKEN_OPTIMIZATION_PLAN.md sang tiếng Việt. Giữ nguyên định dạng Markdown."
    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write(instruction)

    # 2. Extract TOKEN_OPTIMIZATION_PLAN.md content if needed, or assume it exists
    if not os.path.exists(SOURCE_FILE):
        print(f"Error: {SOURCE_FILE} not found!")
        return False

    # 3. Create Zip
    with zipfile.ZipFile(ZIP_FILE, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(PROMPT_FILE)
        zipf.write(SOURCE_FILE)

    print(f"Created {ZIP_FILE} containing {PROMPT_FILE} and {SOURCE_FILE}")
    return True


def run_test():
    api_keys = load_api_keys()
    if not api_keys:
        print("No API Keys found.")
        return

    if not create_payload():
        return

    for i, api_key in enumerate(api_keys):
        print(f"\n--- Attempt {i+1}/{len(api_keys)} with key ending in ...{api_key[-4:]} ---")
        try:
            print("Initializing Gemini Client...")
            client = genai.Client(api_key=api_key)

            # Method 2: File API (Safer for archives)
            print("Uploading file via File API...")
            file_upload = client.files.upload(file=ZIP_FILE)
            print(f"File uploaded: {file_upload.name}")

            prompt = "Hãy giải nén file zip này (trong bộ nhớ), đọc file prompt.txt bên trong và thực hiện nhiệm vụ dịch file TOKEN_OPTIMIZATION_PLAN.md cũng nằm bên trong file zip đó."

            print("Sending generate_content request...")
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    prompt,
                    types.Content(
                        parts=[
                            types.Part.from_uri(
                                file_uri=file_upload.uri,
                                mime_type="application/zip"
                            )
                        ]
                    )
                ]
            )

            print("\n--- GEMINI RESPONSE ---\n")
            print(response.text)
            print("\n-----------------------\n")

            # Write success output and BREAK the loop
            with open("tests/test_result.txt", "w", encoding="utf-8") as f:
                f.write(response.text)
            return

        except Exception as e:
            error_msg = f"Attempt {i+1} Failed: {e}"
            print(error_msg)
            # Log error to file but continue loop
            with open("tests/test_result.txt", "a", encoding="utf-8") as f:
                f.write(f"\n{error_msg}\n")

            # If it's the last key, print final failure
            if i == len(api_keys) - 1:
                print("All API keys failed.")


if __name__ == "__main__":
    run_test()
