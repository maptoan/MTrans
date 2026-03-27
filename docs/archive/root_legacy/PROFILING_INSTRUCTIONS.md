
# Profiling Instructions - Novel Translator

Use these scripts to identify performance bottlenecks.

## 1. Setup Data
First, generate dummy data (Text, Glossary, Image):
```bash
python scripts/profiling/generate_dummy_data.py
```

## 2. Profile Core Logic (CPU/Regex)
Profiles Glossary matching, Prompt building, and Chunking.
```bash
python scripts/profiling/profile_core_logic.py
```
*Look for high cumulative time in `re.findall` or `build_main_prompt`.*

## 3. Profile OCR (Tesseract)
Profiles image-to-text conversion.
```bash
python scripts/profiling/profile_ocr.py
```
*Note the time difference between PSM 3 and fallback.*

## 4. Profile Workflow (Async/IO)
Profiles the `Translator` pipeline with mocked API calls (using `gemini-3-flash-preview` as standard).
```bash
python scripts/profiling/profile_full_workflow.py
```

## 5. Advanced Profiling (Py-Spy & Scalene)

### Flame Graph (Whole Project)
Visualize where time is spent during execution.
```bash
# Install py-spy
pip install py-spy

# Record flame graph (requires dummy data)
py-spy record -o profile.svg -- python scripts/profiling/profile_core_logic.py
```
*Open `profile.svg` in a browser.*

### Line-Level Profiling (Memory/CPU)
See exactly which lines consume the most resources.
```bash
# Install scalene
pip install scalene

# Run line-level profile
scalene run --cli --outfile profile.html scripts/profiling/profile_core_logic.py
```
*Open `profile.html` in a browser.*

## 6. Real API Profiling (Optional)
To profile real API calls, run the main translator with a small input file:
```bash
scalene run --cli src/translation/translator.py
```
*(Requires configuring `config/config.yaml` with valid keys)*
