# PLAN: AI Metadata Generation Module

This plan outlines the implementation of a new feature that uses AI (Gemini) to automatically generate essential metadata files (`style_profile.json`, `glossary.csv`, `character_relations.csv`) before the translation process starts.

## Phase 0: Socratic Gate (User Review Required)

Before proceeding with the implementation, please clarify the following points:

1. **Extraction Strategy (Token Limits)**: Modern novels can exceed millions of tokens. How should the AI read the "entire" work?
    - **Option A**: Single pass using a large context model (e.g., Gemini 1.5 Pro).
    - **Option B**: Incremental extraction (analyze chapters in sequence and merge results).
    - **Option C**: Sampling (analyze the beginning, middle, and end).
2. **Language Handling**: Is the source text always in a single language (e.g., Chinese)? Should the generator detect the source language automatically?
3. **Existing Files**: If metadata files already exist, should the AI **overwrite** them or **update/merge** the new findings with existing data?
4. **Target Directory**: Where should the generated files be stored? (Current default is the novel's root directory or a specific `config/` subfolder).

---

## Phase 1: Architecture & Design

### 1.1 Module Structure
- Create `src/preprocessing/metadata_generator.py`.
- Define `MetadataGenerator` class to handle:
    - Content reading and chunking (for long novels).
    - AI interaction for extraction.
    - Result merging and normalization.
    - File writing in standard formats.

### 1.2 Prompt Engineering
- Design system prompts for each metadata type:
    - **Style**: Genre, tone, writing style, and translation rules.
    - **Glossary**: Extracting key names, places, and concepts.
    - **Relations**: Mapping character interactions and pronouns.

---

## Phase 2: Menu Integration

### 2.1 UI Update
- Modify `main.py` (main entry point) to display a selection menu after configuration loading:
    1. **Proceed to Translation**
    2. **Generate Metadata using AI**
- Handle the choice and route to the appropriate service.

---

## Phase 3: Extraction Logic

### 3.1 Advanced Analysis
- Implement logic to handle PDF/TXT/EPUB reading.
- Implement a "Global Merger" to reconcile terms found in different parts of the novel (e.g., ensuring "Li Feng" and "Feng-er" are mapped correctly).

---

## Phase 4: Verification Plan

### Automated Tests
- Create unit tests for `MetadataGenerator` formatting logic.
- Verify CSV header compliance.

### Manual Verification
- Run the generator on a sample short novel and inspect the outputs.
- Verify that the selection menu works correctly in the terminal.
