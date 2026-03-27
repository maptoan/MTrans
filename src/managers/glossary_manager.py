# -*- coding: utf-8 -*-
from __future__ import annotations

"""
(NÂNG CẤP - ENHANCED TERM MATCHING) Module quản lý glossary với:
- Regex-based term matching (chính xác hơn)
- LRU cache cho term lookups
- Optimized search với trie structure
"""

import logging
import re
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Pattern, Set

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger("NovelTranslator")


class GlossaryManager:
    """
    Quản lý glossary với enhanced term matching.
    """

    def __init__(
        self,
        glossary_path: str,
        encoding: Optional[str] = None,
        api_keys: Optional[List[str]] = None,
        key_manager: Any = None,
    ):
        self.glossary_path: str = glossary_path
        self.encoding: Optional[str] = (
            encoding if encoding and encoding.lower() != "auto" else None
        )
        self.api_keys: List[str] = api_keys or []
        self.key_manager: Any = key_manager
        self.glossary_df: pd.DataFrame = self._load_glossary()

        self.term_lookup: Dict[str, Dict[str, Any]]
        self.all_original_terms: Set[str]
        self.term_patterns: Dict[str, Pattern]

        if not self.glossary_df.empty:
            self.term_lookup = self._build_lookup()
            self.all_original_terms = self._get_all_original_terms()

            # Build regex patterns cho precise matching
            self.term_patterns = self._build_term_patterns()

            logger.info(f"Đã nạp {len(self.glossary_df)} mục từ glossary.")
        else:
            self.term_lookup = {}
            self.all_original_terms = set()
            self.term_patterns = {}
            logger.warning("Glossary rỗng hoặc không thể tải.")

    def _load_glossary(self) -> pd.DataFrame:
        """Load glossary với error handling và chuẩn hóa tên cột (backward-compatible)."""
        import csv

        import pandas as pd

        # Kiểm tra path hợp lệ
        if not self.glossary_path or self.glossary_path.strip() == "":
            logger.warning(
                "Glossary path không được cung cấp hoặc rỗng. Sử dụng glossary trống."
            )
            return pd.DataFrame()

        try:
            # Try fast path (C-engine) với quoting để xử lý dấu phẩy trong giá trị
            df = pd.read_csv(
                self.glossary_path,
                encoding=self.encoding,
                dtype=str,
                keep_default_na=False,
                engine="c",
                quoting=csv.QUOTE_MINIMAL,
            )
        except FileNotFoundError:
            logger.error(f"Tệp glossary không tìm thấy: {self.glossary_path}")
            return pd.DataFrame()
        except UnicodeDecodeError as e:
            logger.critical(
                f"LỖI ENCODING: {self.glossary_path} với mã hóa '{self.encoding}'"
            )
            raise e
        except pd.errors.ParserError as e:
            error_message = str(e)

            # Thử sửa bằng AI nếu có API keys
            if self.api_keys:
                logger.warning(f"⚠️ Phát hiện lỗi parsing CSV: {error_message}")
                logger.info("🤖 Đang thử sửa lỗi tự động bằng AI...")

                try:
                    from src.utils.csv_ai_fixer import CSVAIFixer

                    fixer = CSVAIFixer(self.api_keys, key_manager=self.key_manager)
                    fixed = fixer.fix_csv_file_sync(
                        self.glossary_path,
                        file_type="glossary",
                        encoding=self.encoding or "utf-8",
                        error_message=error_message,
                        backup=True,
                    )

                    if fixed:
                        # fixed=True nghĩa là đã verify thành công trong csv_ai_fixer
                        # File đã được sửa và lưu đè vào file gốc
                        logger.info(
                            "✅ Đã sửa file CSV bằng AI và verify thành công, đang đọc lại..."
                        )
                        try:
                            df = pd.read_csv(
                                self.glossary_path,
                                encoding=self.encoding,
                                dtype=str,
                                keep_default_na=False,
                                engine="c",
                                quoting=csv.QUOTE_MINIMAL,
                            )
                            logger.info(
                                "✅ Đọc file đã sửa thành công! Tiếp tục quy trình dịch..."
                            )
                            # Tiếp tục với column normalization (bỏ qua fallback)
                            ai_fixed = True
                        except pd.errors.ParserError:
                            # Trường hợp hiếm: verify trong fixer pass nhưng đọc lại vẫn lỗi
                            logger.warning(
                                "⚠️ File vẫn còn lỗi sau khi sửa (verify mismatch), fallback sang Python engine..."
                            )
                            ai_fixed = False
                    else:
                        logger.warning(
                            "⚠️ Không thể sửa file bằng AI, fallback sang Python engine..."
                        )
                        ai_fixed = False
                except Exception as fix_error:
                    logger.warning(
                        f"⚠️ Lỗi khi gọi AI fixer: {fix_error}, fallback sang Python engine..."
                    )
                    ai_fixed = False
            else:
                ai_fixed = False

            # Fallback: Retry with Python engine, auto-detected delimiter, skip bad lines
            if not ai_fixed:
                try:
                    with open(
                        self.glossary_path, "r", encoding=self.encoding or "utf-8"
                    ) as f:
                        sample = f.read(4096)
                        try:
                            sniffer = csv.Sniffer()
                            dialect = sniffer.sniff(sample)
                            delim = dialect.delimiter
                        except Exception:
                            delim = ","
                    df = pd.read_csv(
                        self.glossary_path,
                        encoding=self.encoding,
                        dtype=str,
                        keep_default_na=False,
                        engine="python",
                        sep=delim,
                        on_bad_lines="skip",
                        quoting=csv.QUOTE_MINIMAL,
                        doublequote=True,
                    )
                    logger.warning(
                        "ParserError khi đọc glossary: đã fallback engine='python', on_bad_lines='skip'. Một số dòng có thể bị bỏ qua hoặc bị lệch cột."
                    )
                    logger.warning(
                        "⚠️ CẢNH BÁO: File CSV có thể có lỗi format (dấu phẩy không được bọc quotes)."
                    )
                    # Hỏi người dùng có tiếp tục với dữ liệu có thể lệch hay dừng để sửa thủ công
                    try:
                        choice = (
                            input(
                                "Tiếp tục chạy với dữ liệu có thể lệch (y) hay dừng để sửa thủ công (n)? "
                            )
                            .strip()
                            .lower()
                        )
                        if choice not in ["y", "yes", "có"]:
                            raise ValueError(
                                "Người dùng chọn dừng để sửa thủ công file glossary.csv trước khi tiếp tục."
                            )
                        logger.info(
                            "✅ Tiếp tục chạy với dữ liệu fallback (có thể lệch cột)."
                        )
                    except EOFError:
                        # Không có stdin: mặc định tiếp tục để tránh treo
                        logger.warning(
                            "Không có tương tác đầu vào. Tiếp tục với dữ liệu fallback."
                        )
                except Exception:
                    try:
                        line_number = error_message.split("line ")[1].split(",")[0]
                        raise ValueError(
                            f"Lỗi định dạng tại dòng {line_number}. File CSV có thể có dấu phẩy trong giá trị không được bọc quotes. Vui lòng kiểm tra và sửa file."
                        )
                    except IndexError:
                        raise ValueError(
                            f"Lỗi định dạng: {error_message}. File CSV có thể có dấu phẩy trong giá trị không được bọc quotes."
                        )

        # Chuẩn hóa tên cột để tương thích EN/CN và thay đổi tùy chỉnh
        col_map_candidates = {
            "Original_Term_Pinyin": ["Original_Term_Pinyin", "Pinyin", "Source_Pinyin"],
            "Original_Term_CN": ["Original_Term_CN", "Chinese", "Source_CN", "Term_CN"],
            "Original_Term_EN": [
                "Original_Term_EN",
                "English",
                "Source_EN",
                "Term_EN",
                "Original",
                "Term",
                "Original_Term",
            ],  # Added Original_Term
            "Translated_Term_VI": [
                "Translated_Term_VI",
                "Vi",
                "Vietnamese",
                "Target_VI",
                "Translated_VI",
                "Vietnamese_Translation",
            ],
            "Translated_Term_EN": [
                "Translated_Term_EN",
                "Target_EN",
                "English_Translated",
            ],
            "Type": ["Type", "Category", "Class"],
            "Notes": ["Notes", "Comment", "Annotation", "Remark"],
        }

        # Xây map cột hiện có → tên chuẩn
        rename_map = {}
        for std_name, candidates in col_map_candidates.items():
            for c in candidates:
                if c in df.columns:
                    rename_map[c] = std_name
                    break
            # Nếu không có, tạo cột rỗng để tránh KeyError
            if std_name not in rename_map.values() and std_name not in df.columns:
                df[std_name] = ""

        if rename_map:
            df = df.rename(columns=rename_map)

        # Fill NA cho các cột chính
        for col in [
            "Original_Term_Pinyin",
            "Original_Term_CN",
            "Original_Term_EN",
            "Translated_Term_VI",
            "Translated_Term_EN",
            "Type",
            "Notes",
        ]:
            if col in df.columns:
                df[col] = df[col].fillna("")

        return df

    def _build_lookup(self) -> Dict[str, Dict[str, Any]]:
        """Build fast lookup dictionary."""
        lookup = {}
        for _, row in self.glossary_df.iterrows():
            # Ưu tiên khóa tra cứu: Pinyin → CN → EN
            key = (row.get("Original_Term_Pinyin") or "").strip()
            if not key:
                key = (row.get("Original_Term_CN") or "").strip()
            if not key:
                key = (row.get("Original_Term_EN") or "").strip()
            if key:
                lookup[key] = row.to_dict()
        return lookup

    def _get_all_original_terms(self) -> Set[str]:
        """Get all original terms."""
        terms = set()
        for col in ["Original_Term_Pinyin", "Original_Term_CN", "Original_Term_EN"]:
            if col in self.glossary_df.columns:
                # Lấy tất cả giá trị, loại bỏ NaN và empty strings
                col_values = self.glossary_df[col].dropna()
                for val in col_values:
                    if isinstance(val, str) and val.strip():
                        term = val.strip()
                        terms.add(term)

        # Log warning nếu có quá nhiều terms giống nhau (có thể là dấu hiệu parsing sai)
        if (
            len(terms) < len(self.glossary_df) * 0.5
        ):  # Nếu số unique terms < 50% số dòng
            logger.warning(
                f"⚠️ CẢNH BÁO: Số lượng terms duy nhất ({len(terms)}) ít hơn nhiều so với số dòng glossary ({len(self.glossary_df)}). "
                f"Có thể file CSV bị parse sai do format không đúng. Vui lòng kiểm tra file CSV."
            )

        return terms

    def _build_term_patterns(self) -> Dict[str, re.Pattern]:
        """
        Build optimized regex unions for single-pass term matching.
        Categorizes terms into CJK and Non-CJK for appropriate boundary handling.
        """
        cjk_terms = []
        non_cjk_terms = []

        # Sort terms by length descending to ensure longest match wins in union
        sorted_terms = sorted(self.all_original_terms, key=len, reverse=True)

        for term in sorted_terms:
            if not term:
                continue

            escaped_term = re.escape(term)

            # CJK terms (no word boundaries needed)
            if re.search(r"[\u4e00-\u9fff]", term):
                cjk_terms.append(escaped_term)
            else:
                # Non-CJK terms (word boundaries required)
                non_cjk_terms.append(escaped_term)

        # Build Unions
        self.cjk_union_regex = (
            re.compile(f"({'|'.join(cjk_terms)})", re.IGNORECASE) if cjk_terms else None
        )
        self.non_cjk_union_regex = (
            re.compile(f"(?<![\\w])({'|'.join(non_cjk_terms)})(?![\\w])", re.IGNORECASE)
            if non_cjk_terms
            else None
        )

        # Pre-map terms to row indices for O(1) row retrieval
        self.term_to_rows = {}
        for idx, row in self.glossary_df.iterrows():
            for col in ["Original_Term_Pinyin", "Original_Term_CN", "Original_Term_EN"]:
                term = (row.get(col) or "").strip()
                if term:
                    if term not in self.term_to_rows:
                        self.term_to_rows[term] = []
                    self.term_to_rows[term].append(idx)

        logger.info(
            f"Built optimized regex unions for {len(self.all_original_terms)} glossary terms"
        )
        return {}  # Backward compatibility if needed, but we use the new union regexes

    @lru_cache(maxsize=1000)
    def find_terms_in_chunk(self, chunk_text: str) -> List[Dict[str, Any]]:
        """
        Tìm terms trong chunk bằng single-pass regex unions.
        CẢI TIẾN v7.6: Hỗ trợ tìm kiếm xuyên khoảng trắng cho CJK.
        """
        if self.glossary_df.empty:
            return []

        found_terms = set()

        # 1. CJK Matching (Standard)
        if self.cjk_union_regex:
            for match in self.cjk_union_regex.finditer(chunk_text):
                found_terms.add(match.group(0))

        # 2. Non-CJK Matching
        if self.non_cjk_union_regex:
            for match in self.non_cjk_union_regex.finditer(chunk_text):
                found_terms.add(match.group(0))

        # 3. [NEW v7.6] CJK Fuzzy Matching (Handle erratic spaces in Chinese text)
        # Create a version of the text without any spaces for matching
        if self.cjk_union_regex:
            compact_text = re.sub(r"\s+", "", chunk_text)
            for match in self.cjk_union_regex.finditer(compact_text):
                found_terms.add(match.group(0))

        if not found_terms:
            return []

        # 4. Map back to rows
        matched_row_indices = set()
        for term in found_terms:
            # First, try exact lookup
            indices = self.term_to_rows.get(term)
            
            if not indices:
                # Try normalized lookup (ignore case and whitespace for matching key)
                term_norm = re.sub(r"\s+", "", term.lower())
                for original_term, idxs in self.term_to_rows.items():
                    orig_norm = re.sub(r"\s+", "", original_term.lower())
                    if orig_norm == term_norm:
                        indices = idxs
                        break

            if indices:
                matched_row_indices.update(indices)

        # Build results
        results = [
            self.glossary_df.iloc[idx].to_dict() for idx in sorted(matched_row_indices)
        ]

        # Log summary
        if results:
            term_names = [
                r.get("Original_Term_Pinyin")
                or r.get("Original_Term_CN")
                or r.get("Original_Term_EN")
                for r in results
            ]
            logger.info(f"Found {len(results)} glossary terms in chunk (including fuzzy CJK): {term_names}")

        return results

    def build_prompt_section(self, relevant_terms: List[Dict[str, Any]]) -> str:
        """Build glossary section cho prompt."""
        if not relevant_terms:
            return ""

        # Group by type
        by_type = {}
        for term in relevant_terms:
            term_type = term.get("Type", "Khác")
            if term_type not in by_type:
                by_type[term_type] = []
            by_type[term_type].append(term)

        type_display_names = {
            "Character": "TÊN NHÂN VẬT",
            "Place": "ĐỊA DANH",
            "Skill": "CHIÊU THỨC",
            "Item": "VẬT PHẨM",
            "Title": "DANH HIỆU",
            "Organization": "TỔ CHỨC",
            "Creature": "SINH VẬT",
            "Concept": "KHÁI NIỆM",
        }

        prompt_section = "⚠️ BẢNG THUẬT NGỮ (BẮT BUỘC - KHÔNG ĐƯỢC THAY ĐỔI) ⚠️\n🔴 PHẢI dịch CHÍNH XÁC như đã cho. KHÔNG dùng pinyin.\n"

        for term_type, terms in sorted(by_type.items()):
            display_name = type_display_names.get(term_type, term_type.upper())
            prompt_section += f"\n**{display_name}:**\n"

            for t in terms:
                original = (
                    t.get("Original_Term_CN")
                    or t.get("Original_Term_Pinyin")
                    or t.get("Original_Term_EN")
                    or ""
                ).strip()
                pinyin = (t.get("Original_Term_Pinyin") or "").strip()
                translated = (
                    t.get("Translated_Term_VI")
                    or t.get("Translated_Term_EN")
                    or t.get("Translated")
                    or ""
                ).strip()
                notes_val = t.get("Notes") if isinstance(t, dict) else None
                notes = f" // {notes_val}" if notes_val else ""
                pinyin_hint = f" ({pinyin})" if pinyin else ""
                prompt_section += (
                    f"- {original}{pinyin_hint} → **{translated}**{notes}\n"
                )

        return prompt_section.strip()

    def build_compact_prompt_section(self, relevant_terms: List[Dict[str, Any]]) -> str:
        """
        Build compact glossary section using TokenOptimizer.
        Format: "TERM_TYPE: Original(Pinyin)->VI[Note]; ..."
        """
        if not relevant_terms:
            return ""

        # Group by type
        by_type = {}
        for term in relevant_terms:
            term_type = term.get("Type", "Khác")
            if term_type not in by_type:
                by_type[term_type] = []
            by_type[term_type].append(term)

        type_display_names = {
            "Character": "NHÂN VẬT",
            "Place": "ĐỊA DANH",
            "Skill": "CHIÊU THỨC",
            "Item": "VẬT PHẨM",
            "Title": "DANH HIỆU",
            "Organization": "TỔ CHỨC",
            "Creature": "SINH VẬT",
            "Concept": "KHÁI NIỆM",
        }

        prompt_section = "⚠️ GLOSSARY (COMPACT - STRICT COMPLIANCE) ⚠️\n🔴 MUST USE PROVIDED TRANSLATIONS ONLY.\n"

        for term_type, terms in sorted(by_type.items()):
            display_name = type_display_names.get(term_type, term_type.upper())
            from src.utils.token_optimizer import TokenOptimizer

            compact_list = TokenOptimizer.compact_glossary_terms(terms)
            prompt_section += f"{display_name}: {compact_list}\n"

        return prompt_section.strip()

    def clear_cache(self):
        """Clear LRU cache manually if needed."""
        self.find_terms_in_chunk.cache_clear()

    def get_full_glossary_dict(self) -> Dict[str, str]:
        """
        Get all glossary terms as a dictionary for Context Caching.
        Format: {Original: Translated}
        """
        if self.glossary_df.empty:
            return {}

        full_dict = {}
        for _, row in self.glossary_df.iterrows():
            # Get original
            original = (
                row.get("Original_Term_CN")
                or row.get("Original_Term_Pinyin")
                or row.get("Original_Term_EN")
                or ""
            ).strip()
            # Get translated
            translated = (
                row.get("Translated_Term_VI") or row.get("Translated_Term_EN") or ""
            ).strip()

            if original and translated:
                full_dict[original] = translated

        return full_dict

    def is_loaded(self) -> bool:
        """Kiểm tra xem glossary đã được tải thành công chưa."""
        return self.glossary_df is not None and not self.glossary_df.empty
