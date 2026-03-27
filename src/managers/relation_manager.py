# -*- coding: utf-8 -*-
from __future__ import annotations

"""
(NÂNG CẤP - ENHANCED CHARACTER DETECTION) Module quản lý quan hệ với:
- Regex-based character matching
- Prompt caching
- Optimized pair processing
"""

import logging
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from .glossary_manager import GlossaryManager

logger = logging.getLogger("NovelTranslator")


class RelationManager:
    """
    Quản lý quan hệ nhân vật với enhanced detection.
    """

    def __init__(
        self,
        relations_path: str,
        glossary_manager: GlossaryManager,
        encoding: Optional[str] = None,
        api_keys: Optional[List[str]] = None,
        key_manager: Any = None,
    ):
        self.relations_path: str = relations_path
        self.encoding: Optional[str] = (
            encoding if encoding and encoding.lower() != "auto" else None
        )
        self.api_keys: List[str] = api_keys or []
        self.key_manager: Any = key_manager
        self.relations_df: pd.DataFrame = self._load_relations()
        self.glossary_manager: GlossaryManager = glossary_manager
        
        # Phase 12: Sticky Character Context
        self.active_buffer: List[str] = []
        self.max_buffer_chunks: int = 3  # Giữ nhân vật trong 3 chunks gần nhất

        if not self.relations_df.empty:
            self.character_names = self._get_character_names()
            # Build regex patterns cho character matching
            self.character_patterns = self._build_character_patterns()
            logger.info(f"Đã nạp {len(self.relations_df)} quy tắc quan hệ nhân vật.")
        else:
            self.character_names = set()
            self.character_patterns = {}
            logger.warning("File quan hệ nhân vật rỗng hoặc không thể tải.")

    def _load_relations(self) -> pd.DataFrame:
        """Load relations robustly, normalize columns, and stay backward-compatible."""
        # Kiểm tra path hợp lệ
        if not self.relations_path or self.relations_path.strip() == "":
            logger.warning(
                "Character relations path không được cung cấp hoặc rỗng. Sử dụng relations trống."
            )
            return pd.DataFrame()

        df = None

        try:
            # Try fast path (C-engine)
            df = self._read_csv_fast()
        except FileNotFoundError:
            logger.error(f"Tệp quan hệ không tìm thấy: {self.relations_path}")
            return pd.DataFrame()
        except UnicodeDecodeError as e:
            logger.critical(f"LỖI ENCODING: {self.relations_path}")
            raise e
        except pd.errors.ParserError as e:
            # Fallback flow
            df = self._handle_parser_error(str(e))

        if df is not None:
            return self._normalize_columns(df)
        return pd.DataFrame()

    def _read_csv_fast(self) -> pd.DataFrame:
        """Attempt to read CSV efficiently using C engine."""
        return pd.read_csv(
            self.relations_path,
            encoding=self.encoding,
            dtype=str,
            keep_default_na=False,
            engine="c",
        )

    def _handle_parser_error(self, error_message: str) -> Optional[pd.DataFrame]:
        """Handle CSV parsing errors via AI fix or manual fallback."""
        df = self._attempt_ai_fix(error_message)
        if df is not None:
            return df

        return self._perform_fallback_load(error_message)

    def _attempt_ai_fix(self, error_message: str) -> Optional[pd.DataFrame]:
        """Attempt to fix CSV using AI agent."""
        if not self.api_keys:
            return None

        logger.warning(f"⚠️ Phát hiện lỗi parsing CSV: {error_message}")
        logger.info("🤖 Đang thử sửa lỗi tự động bằng AI...")

        try:
            import csv as csv_module

            from src.utils.csv_ai_fixer import CSVAIFixer

            fixer = CSVAIFixer(self.api_keys, key_manager=self.key_manager)
            fixed = fixer.fix_csv_file_sync(
                self.relations_path,
                file_type="character_relations",
                encoding=self.encoding or "utf-8",
                error_message=error_message,
                backup=True,
            )

            if fixed:
                logger.info(
                    "✅ Đã sửa file CSV bằng AI và verify thành công, đang đọc lại..."
                )
                try:
                    df = pd.read_csv(
                        self.relations_path,
                        encoding=self.encoding,
                        dtype=str,
                        keep_default_na=False,
                        engine="c",
                        quoting=csv_module.QUOTE_MINIMAL,
                    )
                    logger.info(
                        "✅ Đọc file đã sửa thành công! Tiếp tục quy trình dịch..."
                    )
                    return df
                except pd.errors.ParserError:
                    logger.warning(
                        "⚠️ File vẫn còn lỗi sau khi sửa (verify mismatch), fallback sang Python engine..."
                    )
        except Exception as fix_error:
            logger.warning(
                f"⚠️ Lỗi khi gọi AI fixer: {fix_error}, fallback sang Python engine..."
            )

        return None

    def _perform_fallback_load(self, error_message: str) -> pd.DataFrame:
        """Last resort: Use Python engine with aggressive error recovery."""
        import csv as csv_module

        try:
            # Detect delimiter
            with open(self.relations_path, "r", encoding=self.encoding or "utf-8") as f:
                sample = f.read(4096)
                try:
                    sniffer = csv_module.Sniffer()
                    dialect = sniffer.sniff(sample)
                    delim = dialect.delimiter
                except Exception:
                    delim = ","

            df = pd.read_csv(
                self.relations_path,
                encoding=self.encoding,
                dtype=str,
                keep_default_na=False,
                engine="python",
                sep=delim,
                on_bad_lines="skip",
            )

            logger.warning(
                "ParserError khi đọc quan hệ: đã fallback engine='python', on_bad_lines='skip'. Một số dòng có thể bị bỏ qua."
            )

            # Interactive check
            try:
                choice = (
                    input(
                        "Tiếp tục chạy với dữ liệu relations có thể lệch (y) hay dừng để sửa thủ công (n)? "
                    )
                    .strip()
                    .lower()
                )
                if choice not in ["y", "yes", "có"]:
                    raise ValueError(
                        "Người dùng chọn dừng để sửa thủ công file character_relations.csv trước khi tiếp tục."
                    )
                logger.info(
                    "✅ Tiếp tục chạy với dữ liệu relations fallback (có thể lệch cột)."
                )
            except EOFError:
                logger.warning(
                    "Không có tương tác đầu vào. Tiếp tục với dữ liệu relations fallback."
                )

            return df

        except Exception as e2:
            self._raise_detailed_error(error_message, e2)
            return pd.DataFrame()  # unreachable but satisfies type checker

    def _raise_detailed_error(self, original_error: str, new_error: Exception) -> None:
        """Format and raise a helpful error message."""
        line_number = None
        try:
            line_number = original_error.split("line ")[1].split(",")[0]
        except Exception:
            pass

        msg = f"Lỗi định dạng CSV (relations): {original_error}"
        if line_number:
            msg = f"Lỗi định dạng tại dòng {line_number}"

        raise ValueError(msg) from new_error

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names to valid internal schema."""
        col_map_candidates = {
            "Speaker_ID": ["Speaker_ID", "Speaker", "From", "Character_A"],
            "Listener_ID": ["Listener_ID", "Listener", "To", "Character_B"],
            "Context": ["Context", "Scene", "Situation", "Context_Type", "Environment"],
            "Speaker_Pronoun": [
                "Speaker_Pronoun",
                "Speaker_Term",
                "Speaker_Address",
                "A_Dialogue_Calls_B",
                "Narrator_Refers_To_Char",
            ],
            "Listener_Term": [
                "Listener_Term",
                "Listener_Address",
                "Address",
                "B_Dialogue_Calls_A",
            ],
            "Notes": ["Notes", "Comment", "Remark"],
            "Type": ["Type"],  # Đảm bảo có cột Type
            "Chapter_Range": ["Chapter_Range", "Chapter"],  # Hỗ trợ chapter range
        }

        rename_map = {}
        for std_name, candidates in col_map_candidates.items():
            for c in candidates:
                if c in df.columns:
                    rename_map[c] = std_name
                    break

            if std_name not in rename_map.values() and std_name not in df.columns:
                df[std_name] = ""

        if rename_map:
            df = df.rename(columns=rename_map)

        return df

    def _get_character_names(self) -> Set[str]:
        """
        Lấy character names từ glossary (ưu tiên) hoặc từ relations CSV (fallback).
        """
        names: Set[str] = set()

        # Bước 1: Thử lấy từ glossary với Type='Character'
        df = self.glossary_manager.glossary_df
        if not df.empty:
            type_col = "Type" if "Type" in df.columns else None
            if type_col:
                char_df = df[df["Type"] == "Character"]
                if not char_df.empty:
                    for col in [
                        "Original_Term_Pinyin",
                        "Original_Term_CN",
                        "Original_Term_EN",
                    ]:
                        if col in char_df.columns:
                            names.update(
                                {
                                    str(x)
                                    for x in char_df[col].dropna()
                                    if str(x).strip()
                                }
                            )
                    if names:
                        logger.debug(
                            f"Lấy {len(names)} character names từ glossary (Type='Character')"
                        )
                        return names
                    else:
                        logger.debug(
                            "Glossary có Type='Character' nhưng không có character names"
                        )
            else:
                logger.debug("Glossary không có cột 'Type', không thể filter Character")

        # Bước 2: Fallback - lấy từ relations CSV (Speaker_ID, Listener_ID)
        if not self.relations_df.empty:
            for col in ["Speaker_ID", "Listener_ID"]:
                if col in self.relations_df.columns:
                    col_names = {
                        str(x)
                        for x in self.relations_df[col].dropna()
                        if str(x).strip()
                    }
                    # Normalize character names: extract phần đầu (trước underscore) nếu có
                    # Ví dụ: "Declan_Kennedy" → "Declan", "Elizabeth_Kennedy" → "Elizabeth"
                    normalized_names = set()
                    for name in col_names:
                        name = str(name).strip()
                        if not name:
                            continue
                        # Nếu có underscore, lấy phần đầu (first name)
                        if "_" in name and not re.search(r"[\u4e00-\u9fff]", name):
                            first_part = name.split("_")[0]
                            if first_part:
                                normalized_names.add(first_part)
                                # Cũng thêm full name để match cả hai trường hợp
                                normalized_names.add(name)
                        else:
                            normalized_names.add(name)
                    names.update(normalized_names)
            if names:
                logger.info(
                    f"Lấy {len(names)} character names từ relations CSV (đã normalize, fallback vì glossary không có Type='Character')"
                )
                logger.debug(f"Sample character names: {list(names)[:10]}")
                return names
            else:
                logger.warning(
                    "Relations CSV không có Speaker_ID/Listener_ID hoặc rỗng"
                )
        else:
            logger.warning("Relations CSV rỗng, không thể lấy character names")

        # Không tìm thấy character names
        if not names:
            logger.warning(
                "⚠️  Không tìm thấy character names từ glossary hoặc relations CSV."
            )
            logger.warning("💡 Để sử dụng character detection:")
            logger.warning(
                "   1. Thêm cột 'Type' vào glossary.csv và đánh dấu 'Character' cho các nhân vật"
            )
            logger.warning(
                "   2. Hoặc đảm bảo relations CSV có cột 'Speaker_ID' và 'Listener_ID' với tên nhân vật"
            )

        return names

    def _build_character_patterns(self) -> Dict[str, re.Pattern]:
        """
        Build regex patterns cho enhanced character matching.
        Cải thiện để xử lý các trường hợp edge case:
        - Tên với apostrophe: "Holly's" → match "Holly"
        - Tên với dấu câu: "Richard," "Jack." → match "Richard", "Jack"
        - Tên trong quotes: "'Holly'" → match "Holly"
        """
        patterns = {}
        for name in self.character_names:
            if not name:
                continue
            escaped_name = re.escape(name)

            # Enhanced pattern: CJK-aware matching
            if re.search(r"[\u4e00-\u9fff]", name):
                # CJK characters: more flexible matching (không cần word boundaries)
                pattern = re.compile(f"({escaped_name})", re.IGNORECASE)
            else:
                # Non-CJK: improved word boundaries với nhiều trường hợp edge case
                # Pattern linh hoạt hơn để xử lý:
                # - Tên sau dấu câu: "Hello, Richard" → match "Richard"
                # - Tên với apostrophe: "Holly's" → match "Holly" (nếu tên là "Holly")
                # - Tên trong quotes: "'Holly'" → match "Holly"
                # - Tên ở đầu câu: "Richard said" → match "Richard"
                # - Tên ở cuối câu: "said Richard." → match "Richard"
                # - Tránh match trong từ: "Richardson" không match "Richard"

                # Pattern linh hoạt: cho phép whitespace hoặc dấu câu trước/sau tên
                # Nhưng vẫn tránh match trong từ (ví dụ: "Richardson" không match "Richard")

                # Pattern chính: tên sau whitespace/dấu câu/đầu dòng, trước whitespace/dấu câu/cuối dòng
                # Sử dụng negative lookbehind để tránh match trong từ
                # Cho phép apostrophe + 's' sau tên (ví dụ: "Holly's")
                pattern = re.compile(
                    f"(?<![\\w])({escaped_name})(?=\\s|['\",.?!:;]|$|'s|'S)",
                    re.IGNORECASE | re.MULTILINE,
                )

            patterns[name] = pattern
            logger.debug(f"Created character pattern for '{name}': {pattern.pattern}")

        logger.info(f"Built {len(patterns)} character patterns for detection")
        return patterns

    def find_active_characters(self, chunk_text: str) -> List[str]:
        """
        Tìm characters trong chunk với enhanced detection và logging.
        """
        if not self.character_names:
            # Only log warning once (not repeatedly for each chunk)
            if not hasattr(self, "_character_warning_logged"):
                logger.warning("No character names available for detection")
                self._character_warning_logged = True
            return []

        found_characters = []
        match_details = []

        chunk_text_lower = chunk_text.lower()

        for name, pattern in self.character_patterns.items():
            # Optimization 1: Pre-check substring
            if name.lower() not in chunk_text_lower:
                continue

            # Optimization 2: Lazy findall (only for debug)
            if logger.isEnabledFor(logging.DEBUG):
                matches = pattern.findall(chunk_text)
                if matches:
                    found_characters.append(name)
                    match_details.append(f"'{name}' -> {len(matches)} matches")
                    logger.debug(
                        f"Character '{name}' found {len(matches)} times in chunk"
                    )
            else:
                if pattern.search(chunk_text):
                    found_characters.append(name)

        if found_characters:
            logger.info(
                f"Found {len(found_characters)} active characters in chunk: {found_characters}"
            )
            # Update sticky buffer
            for char in found_characters:
                if char not in self.active_buffer:
                    self.active_buffer.append(char)
            # Keep only unique characters, limit size if needed
            self.active_buffer = self.active_buffer[-10:] # Max 10 characters in buffer
        else:
            # [PHASE 12] If no chars found, use sticky buffer
            if self.active_buffer:
                logger.info(f"Using sticky character context: {self.active_buffer}")
                return self.active_buffer
            
            # Downgraded to DEBUG: not an error, just debug info
            logger.debug(
                f"No active characters found in chunk (searched {len(self.character_patterns)} patterns)"
            )

            # Debug details (only at DEBUG level)
            sample_names = list(self.character_names)[:10]
            logger.debug(
                f"Character names searched (sample {len(sample_names)}/{len(self.character_names)}): {sample_names}"
            )

            # All detailed pattern analysis moved to DEBUG level
            # Check for simple substring matches to debug regex failure
            simple_matches = [
                name for name in self.character_names if name in chunk_text
            ]

            if simple_matches:
                logger.debug(
                    f"Pattern mismatch: {len(simple_matches)} names found in text but not matched by regex"
                )
                for match in simple_matches[:3]:
                    logger.debug(f"   - {match}")
            else:
                logger.debug(f"Chunk preview: {chunk_text[:200]}...")

        return found_characters

    def get_pronoun_guidance(self, speaker: str, listener: str) -> List[Dict[str, Any]]:
        """Lấy quy tắc xưng hô cho đối thoại (Type == 'pattern')."""
        if self.relations_df.empty:
            return []

        # Filter theo Type == 'pattern' (hoặc không có Type nếu backward compatible)
        df = self.relations_df.copy()
        if "Type" in df.columns:
            # Lọc chỉ lấy các row có Type == 'pattern' hoặc Type rỗng/NaN (backward compatible)
            mask = df["Type"].isin(["pattern", ""]) | df["Type"].isna()
            df = df[mask]

        matches = df[(df["Speaker_ID"] == speaker) & (df["Listener_ID"] == listener)]
        return matches.to_dict("records")

    def build_prompt_section(self, active_characters) -> str:
        """
        Build prompt section. Cho phép nhận list/tuple; sẽ chuẩn hóa về tuple để cache.
        """
        if not active_characters:
            return ""
        # Chuẩn hóa về tuple để đảm bảo hashable cho cache
        if isinstance(active_characters, list):
            active_tuple = tuple(active_characters)
        elif isinstance(active_characters, tuple):
            active_tuple = active_characters
        else:
            # Fallback: ép về tuple một phần tử
            active_tuple = (active_characters,)

        return self._build_prompt_section_cached(active_tuple)

    @lru_cache(maxsize=500)
    def _build_prompt_section_cached(self, active_characters: tuple) -> str:
        """
        Bản cache-internal: nhận tuple hashable.
        """
        active_chars_list = list(active_characters)

        if not active_chars_list or len(active_chars_list) < 2:
            return ""

        prompt_section = "MỆNH LỆNH VỀ CÁCH XƯNG HÔ (TUÂN THỦ TUYỆT ĐỐI):\n"
        prompt_section += "Dựa vào ngữ cảnh đối thoại (ai đang nói, ai đang nghe), bạn BẮT BUỘC phải dịch các đại từ nhân xưng (như 他, 她, 你, 我...) theo đúng các quy tắc sau:\n"

        has_guidance = False
        processed_pairs = set()
        all_pairs = [
            (p1, p2) for p1 in active_chars_list for p2 in active_chars_list if p1 != p2
        ]

        for speaker, listener in all_pairs:
            pair_key = tuple(sorted((speaker, listener)))
            if pair_key in processed_pairs:
                continue

            guidance_s_to_l = self.get_pronoun_guidance(speaker, listener)
            guidance_l_to_s = self.get_pronoun_guidance(listener, speaker)

            if guidance_s_to_l or guidance_l_to_s:
                has_guidance = True
                prompt_section += f"\n**Giữa {speaker} và {listener}:**\n"

                if guidance_s_to_l:
                    for guidance in guidance_s_to_l:
                        context = (
                            guidance.get("Context", "Mặc định")
                            or guidance.get("Context_Type", "Mặc định")
                            or "Mặc định"
                        )
                        speaker_pronoun = guidance.get(
                            "Speaker_Pronoun", ""
                        ) or guidance.get("A_Dialogue_Calls_B", "chưa rõ")
                        listener_term = guidance.get(
                            "Listener_Term", ""
                        ) or guidance.get("B_Dialogue_Calls_A", "chưa rõ")
                        notes = (
                            f" (Lưu ý: {guidance['Notes']})"
                            if pd.notna(guidance.get("Notes")) and guidance["Notes"]
                            else ""
                        )
                        if speaker_pronoun != "chưa rõ" or listener_term != "chưa rõ":
                            prompt_section += f"- Khi {speaker} nói: xưng '{speaker_pronoun}', gọi '{listener_term}' (trong ngữ cảnh '{context}'){notes}.\n"

                if guidance_l_to_s:
                    for guidance in guidance_l_to_s:
                        context = (
                            guidance.get("Context", "Mặc định")
                            or guidance.get("Context_Type", "Mặc định")
                            or "Mặc định"
                        )
                        speaker_pronoun = guidance.get(
                            "Speaker_Pronoun", ""
                        ) or guidance.get("A_Dialogue_Calls_B", "chưa rõ")
                        listener_term = guidance.get(
                            "Listener_Term", ""
                        ) or guidance.get("B_Dialogue_Calls_A", "chưa rõ")
                        notes = (
                            f" (Lưu ý: {guidance['Notes']})"
                            if pd.notna(guidance.get("Notes")) and guidance["Notes"]
                            else ""
                        )
                        if speaker_pronoun != "chưa rõ" or listener_term != "chưa rõ":
                            prompt_section += f"- Khi {listener} nói: xưng '{speaker_pronoun}', gọi '{listener_term}' (trong ngữ cảnh '{context}'){notes}.\n"

                processed_pairs.add(pair_key)

        return prompt_section.strip() if has_guidance else ""

    def clear_cache(self):
        """Clear prompt cache."""
        self._build_prompt_section_cached.cache_clear()

    # --- Gender inference constants for narrative pronoun auto-generation ---
    _MALE_INDICATORS = {
        "chàng", "huynh", "sư huynh", "đệ", "sư đệ", "công tử",
        "bệ hạ", "hoàng thượng", "thiếu gia", "thiếu chủ", "ca ca",
        "đại ca", "nhị ca", "tam ca", "gia gia", "chủ nhân",
        "hiền đệ", "hiền huynh", "tiểu tử", "lão gia", "quốc sư",
    }
    _FEMALE_INDICATORS = {
        "nàng", "sư tỷ", "sư muội", "tỷ tỷ", "muội muội", "cô nương",
        "nương nương", "phu nhân", "tiểu thư", "nha đầu", "mỹ nhân",
        "hoàng hậu", "công chúa", "nữ hiệp", "sư nương",
    }

    def _infer_gender_from_listener_terms(self) -> Dict[str, str]:
        """
        Suy luận giới tính nhân vật từ cách người khác gọi họ (Listener_Term).
        Returns mapping: Character_ID -> 'hắn' | 'nàng'
        """
        if self.relations_df.empty:
            return {}

        df = self.relations_df
        listener_col = "Listener_ID" if "Listener_ID" in df.columns else None
        term_col = "Listener_Term" if "Listener_Term" in df.columns else None

        if not listener_col or not term_col:
            return {}

        # Collect all terms used to address each character
        char_terms: Dict[str, list] = {}
        for _, row in df.iterrows():
            char_id = str(row.get(listener_col) or "").strip()
            raw_term = str(row.get(term_col) or "").strip()
            if not char_id or not raw_term:
                continue
            if char_id not in char_terms:
                char_terms[char_id] = []
            # Split multi-value terms: "Chàng; Ngươi" or "Nàng / Thủy nhi"
            for sep in [";", "/"]:
                raw_term = raw_term.replace(sep, ";")
            parts = [p.strip().lower() for p in raw_term.split(";") if p.strip()]
            char_terms[char_id].extend(parts)

        mapping: Dict[str, str] = {}
        for char_id, terms in char_terms.items():
            male_score = 0
            female_score = 0
            for t in terms:
                # Check exact match first, then substring match
                if t in self._MALE_INDICATORS:
                    male_score += 2
                elif any(ind in t for ind in self._MALE_INDICATORS):
                    male_score += 1
                if t in self._FEMALE_INDICATORS:
                    female_score += 2
                elif any(ind in t for ind in self._FEMALE_INDICATORS):
                    female_score += 1
            if male_score > female_score:
                mapping[char_id] = "hắn"
            elif female_score > male_score:
                mapping[char_id] = "nàng"
            # If tied or zero, skip (can't determine)
        return mapping

    def get_narrative_terms_map(self) -> Dict[str, str]:
        """
        Tạo mapping cho trần thuật: Character_ID -> Narrative_Pronoun.
        Priority:
          1. Explicit Narrator_Refers_To_Char / Narrative_Term columns
          2. Auto-infer from Listener_Term gender patterns (fallback)
        """
        mapping: Dict[str, str] = {}
        if self.relations_df.empty:
            return mapping
        df = self.relations_df

        char_col = "Character_A" if "Character_A" in df.columns else "Speaker_ID"
        if char_col not in df.columns:
            return mapping

        # --- Priority 1: Explicit narrator columns ---
        col_term = None
        for col in ["Narrator_Refers_To_Char", "Narrative_Term"]:
            if col in df.columns:
                col_term = col
                break

        if col_term:
            # Filter theo Type
            filtered_df = df
            if "Type" in df.columns:
                type_filter = (
                    df["Type"].isin(["narrator_reference", "narrative_single", ""])
                    | df["Type"].isna()
                )
                filtered_df = df[type_filter]

            for _, row in filtered_df.iterrows():
                char_id = str(row.get(char_col) or "").strip()
                term = str(row.get(col_term) or "").strip()
                if not char_id or not term:
                    continue

                primary = term
                parts = [p.strip() for p in term.split("/")]
                for p in parts:
                    if p.lower() in {
                        "hắn", "nàng", "y", "cô", "anh",
                        "she", "he", "i", "me", "him", "her",
                    }:
                        primary = p.strip()
                        break
                mapping[char_id] = primary

        # --- Priority 2: Auto-infer from Listener_Term (fallback) ---
        if not mapping:
            inferred = self._infer_gender_from_listener_terms()
            if inferred:
                mapping = inferred
                logger.info(
                    f"Auto-inferred narrative pronouns for {len(inferred)} characters "
                    f"from Listener_Term patterns"
                )

        return mapping

    def build_narrative_prompt_section(self, active_characters) -> str:
        """
        Sinh đoạn quy tắc trần thuật bắt buộc cho prompt.
        Nếu có mapping → inject từng nhân vật.
        Luôn thêm quy tắc phân biệt Trần thuật vs Đối thoại.
        """
        mapping = self.get_narrative_terms_map()

        # Filter to only active characters if we have a mapping
        if mapping and active_characters:
            active_set = set(active_characters) if active_characters else set()
            filtered = {k: v for k, v in mapping.items() if k in active_set}
            # If no overlap, keep all (safety net)
            if filtered:
                mapping = filtered

        lines = ["QUY TẮC TRẦN THUẬT (BẮT BUỘC):"]
        lines.append(
            "⚠️ PHÂN BIỆT RÕ: 'Ta' trong [QUY TẮC XƯNG HÔ] CHỈ dùng khi nhân vật "
            "TỰ XƯNG trong lời thoại (ngôi thứ 1). Trong TRẦN THUẬT (ngôi thứ 3, "
            "ngoài dấu ngoặc kép), KHÔNG BAO GIỜ dùng 'Ta' để gọi nhân vật."
        )

        if mapping:
            lines.append("Đại từ trần thuật bắt buộc:")
            for char_id, pron in mapping.items():
                lines.append(f"- {char_id}: dùng '{pron}' trong trần thuật")
        else:
            lines.append(
                "Quy tắc chung: Nam → 'hắn', Nữ → 'nàng' trong trần thuật. "
                "TUYỆT ĐỐI KHÔNG dùng 'Ta' ngoài dấu ngoặc kép."
            )
        return "\n".join(lines)

    def get_full_relation_text(self) -> List[str]:
        """
        Get ALL relation rules (both dialogue and narrative) as a list of strings
        for Context Caching.
        """
        parts = []
        if not self.character_names:
            return parts

        # Convert set to sorted tuple for stability
        all_chars = tuple(sorted(list(self.character_names)))

        # 1. Dialogue Rules
        dialogue_rules = self.build_prompt_section(all_chars)
        if dialogue_rules:
            parts.append(dialogue_rules)

        # 2. Narrative Rules
        narrative_rules = self.build_narrative_prompt_section(all_chars)
        if narrative_rules:
            parts.append(narrative_rules)

        return parts

    def is_loaded(self) -> bool:
        """Kiểm tra xem character relations đã được tải thành công chưa."""
        return self.relations_df is not None and not self.relations_df.empty
