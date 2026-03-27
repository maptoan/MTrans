# -*- coding: utf-8 -*-
"""
Module tự động sửa lỗi CSV bằng AI khi phát hiện ParserError.

Sử dụng Gemini API để phân tích và sửa lỗi format CSV, đặc biệt là:
- Các giá trị có dấu phẩy không được bọc trong quotes
- Các giá trị có dấu ngoặc kép không được escape đúng
- Số cột không đúng giữa các dòng
- Các lỗi format CSV khác

Các chức năng chính:
- Tự động phát hiện và sửa lỗi CSV bằng AI
- Backup file gốc trước khi sửa
- Retry logic với nhiều vòng sửa
- Status tracking để tránh sửa lại file đã sửa thành công
- Fallback sang Python engine nếu AI không sửa được
"""

import asyncio
import csv
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")

# Import adapter
try:
    from ..services.genai_adapter import GenAIClient, create_client

    ADAPTER_AVAILABLE = True
except ImportError:
    ADAPTER_AVAILABLE = False
    GenAIClient = None  # type: ignore
    create_client = None  # type: ignore


class CSVAIFixer:
    """
    Module tự động sửa lỗi CSV bằng AI sử dụng Gemini API.

    Tự động phát hiện và sửa các lỗi format CSV như:
    - Giá trị có dấu phẩy không được bọc quotes
    - Giá trị có quotes không được escape đúng
    - Số cột không đúng
    - Các lỗi format khác
    """

    # Worker ID khi dùng key_manager chung
    _WORKER_ID_CSV_FIXER = 996

    def __init__(
        self,
        api_keys: List[str],
        config: Optional[Dict[str, Any]] = None,
        key_manager: Any = None,
    ) -> None:
        """
        Khởi tạo CSV AI Fixer.

        Args:
            api_keys: Danh sách API keys để sử dụng (rotate khi không có key_manager)
            config: Optional cấu hình (model, temperature, etc.)
            key_manager: Nếu có thì dùng chung get_available_key/return_key với quy trình chính.
        """
        self.api_keys: List[str] = api_keys or []
        self.config: Dict[str, Any] = config or {}
        self.key_manager = key_manager
        self.current_key_index: int = 0
        self.use_new_sdk: bool = config.get("use_new_sdk", True) if config else True

        # Safety settings (string-based format để tương thích với cả 2 SDKs)
        self.safety_settings: List[Dict[str, str]] = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

    def _get_client(self, model_name: str = "gemini-2.5-flash") -> GenAIClient:
        """
        Lấy GenAI Client với API key rotation (dùng khi không có key_manager).
        """
        if not ADAPTER_AVAILABLE:
            raise ImportError("GenAI adapter không khả dụng")

        if not self.api_keys:
            raise ValueError("Không có API key")

        api_key = self.api_keys[self.current_key_index % len(self.api_keys)]
        self.current_key_index += 1

        return create_client(api_key=api_key, use_new_sdk=self.use_new_sdk)

    def _read_csv_sample(
        self, file_path: str, encoding: str = "utf-8", max_lines: int = 10
    ) -> Tuple[List[str], List[str]]:
        """
        Đọc mẫu từ file CSV để phân tích.

        Args:
            file_path: Đường dẫn file CSV
            encoding: Encoding của file (mặc định: 'utf-8')
            max_lines: Số dòng tối đa để đọc (mặc định: 10)

        Returns:
            Tuple (header_list, sample_lines_list)
            - header_list: List chứa header (dòng đầu tiên)
            - sample_lines_list: List các dòng mẫu (tối đa max_lines)
        """
        with open(file_path, "r", encoding=encoding) as f:
            lines = f.readlines()

        if not lines:
            return [], []

        header = lines[0].strip()
        sample_lines = [
            line.strip() for line in lines[1 : max_lines + 1] if line.strip()
        ]

        return [header], sample_lines

    def _build_fix_prompt(
        self,
        file_path: str,
        file_type: str,
        header: str,
        sample_lines: List[str],
        error_message: str,
        encoding: str = "utf-8",
    ) -> str:
        """
        Tạo prompt cho AI để sửa lỗi CSV.

        Args:
            file_path: Đường dẫn file CSV cần sửa
            file_type: Loại file ('glossary' hoặc 'character_relations')
            header: Header của CSV (dòng đầu tiên)
            sample_lines: Các dòng mẫu có lỗi (không sử dụng trong prompt hiện tại)
            error_message: Thông báo lỗi từ pandas
            encoding: Encoding của file (mặc định: 'utf-8')

        Returns:
            Prompt string để gửi cho AI
        """
        # Đọc toàn bộ file để AI sửa tất cả các dòng
        with open(file_path, "r", encoding=encoding) as f:
            all_lines = f.readlines()

        data_lines = [line.strip() for line in all_lines[1:] if line.strip()]
        total_lines = len(data_lines)

        # Build prompt từng phần để tránh lỗi f-string với triple quotes
        # Tính expected_cols bằng CSV reader để xử lý đúng header có quotes
        try:
            import csv as csv_module
            import io

            reader = csv_module.reader(io.StringIO(header))
            expected_cols = len(next(reader))
        except Exception:
            # Fallback: dùng split nếu CSV reader thất bại
            expected_cols = len(header.split(","))

        prompt = f"""Bạn là chuyên gia sửa lỗi format CSV. Nhiệm vụ của bạn là sửa lỗi parsing trong file CSV.

**THÔNG TIN FILE:**
- File: {file_path}
- Loại: {file_type}
- Lỗi: {error_message}
- Tổng số dòng dữ liệu: {total_lines}

**HEADER (dòng đầu tiên - KHÔNG SỬA):**
{header}

**SỐ CỘT EXPECTED:** {expected_cols} cột

**TẤT CẢ CÁC DÒNG DỮ LIỆU CẦN SỬA:**
"""
        # Gửi tất cả các dòng (Gemini 2.5 Flash có thể xử lý được)
        # Nếu quá dài (>300 dòng), chỉ gửi 300 dòng đầu và hướng dẫn AI
        # Tăng từ 200 lên 300 để AI thấy nhiều mẫu hơn
        max_lines_to_show = 300 if total_lines > 300 else total_lines
        for i, line in enumerate(data_lines[:max_lines_to_show], start=2):
            prompt += f"Dòng {i}: {line}\n"

        if total_lines > max_lines_to_show:
            prompt += f"\n... (còn {total_lines - max_lines_to_show} dòng nữa, áp dụng cùng quy tắc sửa cho tất cả)\n"
            prompt += f"\n⚠️ QUAN TRỌNG: Bạn PHẢI trả về TẤT CẢ {total_lines} dòng đã sửa, không chỉ {max_lines_to_show} dòng đầu.\n"

        # Tiếp tục build prompt
        prompt += f"""
**YÊU CẦU:**
1. Phân tích lỗi: Xác định các giá trị có dấu phẩy không được bọc trong quotes
2. Sửa lỗi: Bọc tất cả giá trị có dấu phẩy, dấu ngoặc kép, hoặc ký tự đặc biệt trong quotes
3. Đảm bảo: Mỗi dòng phải có đúng {expected_cols} cột
4. Giữ nguyên: Nội dung và thứ tự của các giá trị, chỉ thêm quotes khi cần
5. Sửa TẤT CẢ các dòng: Trả về tất cả {total_lines} dòng đã sửa (nếu chỉ thấy một phần, áp dụng cùng quy tắc cho phần còn lại)

**QUY TẮC CSV:**
- Nếu giá trị chứa dấu phẩy -> BỌC trong quotes: ví dụ: giá trị có phẩy sẽ thành [QUOTE]giá trị, có phẩy[QUOTE]
- Nếu giá trị chứa dấu ngoặc kép -> DOUBLE quotes: ví dụ: giá trị có quotes sẽ thành [QUOTE]giá trị [DBL_QUOTE]có quotes[DBL_QUOTE][QUOTE]
- Nếu giá trị chứa xuống dòng -> BỌC trong quotes
- Nếu giá trị không có dấu phẩy/quotes -> KHÔNG cần quotes (trừ khi có yêu cầu khác)

Lưu ý: [QUOTE] = dấu ngoặc kép ", [DBL_QUOTE] = dấu ngoặc kép đôi ""

**OUTPUT FORMAT:**
Trả về TẤT CẢ các dòng đã sửa (không bao gồm header), mỗi dòng một dòng, format CSV đúng chuẩn.
KHÔNG giải thích, KHÔNG thêm comment, CHỈ trả về các dòng CSV đã sửa, đúng thứ tự.

**VÍ DỤ:**
Input (lỗi): 
Term,Value,Type,Category,Context,Definition,Chapter,Notes
Meggie Cleary,Meggie Cleary,character_name,family,Nhân vật nữ chính, trung tâm bi kịch,Cô con gái duy nhất trong gia đình Cleary, người phụ nữ bị giằng xé,Ch.1-7,Tên riêng cần giữ nguyên

Output (đã sửa):
Meggie Cleary,Meggie Cleary,character_name,family,"Nhân vật nữ chính, trung tâm bi kịch","Cô con gái duy nhất trong gia đình Cleary, người phụ nữ bị giằng xé",Ch.1-7,Tên riêng cần giữ nguyên

**BẮT ĐẦU SỬA TẤT CẢ {total_lines} DÒNG:**
"""
        return prompt

    async def _call_ai_fix(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Gọi AI để sửa lỗi CSV với retry logic.

        Args:
            prompt: Prompt string để gửi cho AI
            max_retries: Số lần retry tối đa (mặc định: 3)

        Returns:
            Response text từ AI (các dòng CSV đã sửa) hoặc None nếu thất bại
        """
        for attempt in range(max_retries):
            key = None
            client = None
            failed = False
            err_type, err_msg = "generation_error", ""
            try:
                if self.key_manager:
                    # [v9.1] get_available_key is now async
                    key = await self.key_manager.get_available_key()
                    if not key:
                        logger.warning("Không lấy được key cho CSV AI Fixer.")
                        await asyncio.sleep(2**attempt)
                        continue
                    client = create_client(api_key=key, use_new_sdk=self.use_new_sdk)
                else:
                    client = self._get_client("gemini-2.5-flash")

                logger.info(
                    f"🤖 Đang gọi AI để sửa lỗi CSV (attempt {attempt + 1}/{max_retries})..."
                )

                response = await client.generate_content_async(
                    prompt=prompt,
                    model_name="gemini-2.5-flash",
                    safety_settings=self.safety_settings,
                )

                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()
                else:
                    logger.warning(f"AI không trả về nội dung (attempt {attempt + 1})")

            except Exception as e:
                failed = True
                err_msg = str(e)
                err_type = (
                    self.key_manager.handle_exception(key, e)
                    if (self.key_manager and key and hasattr(self.key_manager, "handle_exception"))
                    else "generation_error"
                )
                logger.warning(
                    f"Lỗi khi gọi AI (attempt {attempt + 1}): {err_msg}",
                    exc_info=True,
                )

                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                else:
                    logger.error(f"Không thể gọi AI sau {max_retries} lần thử")
                    return None
            finally:
                if self.key_manager and key:
                    await self.key_manager.return_key(
                        self._WORKER_ID_CSV_FIXER,
                        key,
                        is_error=failed,
                        error_type=err_type,
                        error_message=err_msg,
                    )

        return None

    def _parse_ai_response(
        self, response: str, expected_columns: Optional[int] = None
    ) -> List[str]:
        """
        Parse response từ AI thành danh sách các dòng CSV đã sửa.

        Loại bỏ markdown formatting, comments, và validate số cột.

        Args:
            response: Response text từ AI
            expected_columns: Optional số cột expected (để validate)

        Returns:
            List các dòng CSV đã sửa (không bao gồm header)
        """
        lines = []
        for line in response.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Loại bỏ markdown code blocks nếu có
            if line.startswith("```"):
                continue

            # Loại bỏ comment hoặc giải thích (nhưng không bỏ dòng bắt đầu bằng ** nếu có dấu phẩy)
            if line.startswith("#") or line.startswith("//"):
                continue
            # Chỉ bỏ dòng ** nếu không có dấu phẩy (có thể là markdown formatting)
            if line.startswith("**") and "," not in line:
                continue

            # Loại bỏ các dòng không có dấu phẩy (không phải CSV)
            if "," not in line:
                continue

            # Validate: Đếm số cột
            try:
                import csv as csv_module
                import io

                reader = csv_module.reader(io.StringIO(line))
                fields = next(reader)

                # Nếu có expected_columns, kiểm tra số cột
                if expected_columns and len(fields) != expected_columns:
                    # Có thể là dòng không hợp lệ, skip
                    continue

                # Chỉ thêm các dòng có ít nhất 2 cột (hợp lý cho CSV)
                if len(fields) >= 2:
                    lines.append(line)
            except Exception:
                # Nếu không parse được, skip
                continue

        return lines

    def _merge_fixed_lines(
        self,
        original_lines: List[str],
        fixed_lines: List[str],
        header: str,
        expected_columns: int,
    ) -> List[str]:
        """
        Merge các dòng đã sửa vào file gốc.

        Nếu AI sửa đủ số dòng, dùng tất cả. Nếu thiếu, merge với dòng gốc.

        Args:
            original_lines: Tất cả các dòng gốc (bao gồm header)
            fixed_lines: Các dòng đã được AI sửa (không bao gồm header)
            header: Header của CSV
            expected_columns: Số cột expected (từ header)

        Returns:
            Danh sách các dòng đã merge (bao gồm header ở đầu)
        """
        result = [header]
        original_data_count = len(original_lines) - 1  # Trừ header

        # Nếu AI sửa đủ hoặc nhiều hơn số dòng gốc, dùng tất cả (cắt bớt nếu thừa)
        if len(fixed_lines) >= original_data_count:
            # AI đã sửa đủ số dòng, dùng tất cả (cắt bớt nếu thừa)
            result.extend(fixed_lines[:original_data_count])
            if len(fixed_lines) > original_data_count:
                logger.warning(
                    f"AI trả về {len(fixed_lines)} dòng, nhiều hơn {original_data_count} dòng gốc. Chỉ dùng {original_data_count} dòng đầu."
                )
        else:
            # AI chỉ sửa một phần, merge từng dòng
            # Sử dụng tất cả các dòng đã sửa, phần còn lại giữ nguyên dòng gốc
            logger.warning(
                f"AI chỉ trả về {len(fixed_lines)} dòng, ít hơn {original_data_count} dòng gốc. Sẽ merge với dòng gốc."
            )
            for i, original_line in enumerate(original_lines[1:], start=0):
                if i < len(fixed_lines):
                    # Dùng dòng đã sửa
                    result.append(fixed_lines[i])
                else:
                    # Dùng dòng gốc cho phần còn lại
                    result.append(original_line.strip())

        return result

    async def fix_csv_file(
        self,
        file_path: str,
        file_type: str,
        encoding: str = "utf-8",
        error_message: str = "",
        backup: bool = True,
    ) -> bool:
        """
        Tự động sửa file CSV bằng AI

        Args:
            file_path: Đường dẫn file CSV cần sửa
            file_type: 'glossary' hoặc 'character_relations'
            encoding: Encoding của file
            error_message: Thông báo lỗi từ pandas
            backup: Tự động backup file gốc

        Returns:
            True nếu sửa thành công, False nếu thất bại
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"File không tồn tại: {file_path}")
            return False

        if not self.api_keys:
            logger.error("Không có API key để gọi AI")
            return False

        logger.info(f"🔧 Bắt đầu sửa file CSV bằng AI: {file_path}")

        # Chống lặp lại không cần thiết giữa các phiên làm việc:
        # Nếu lần trước đã sửa THẤT BẠI và file chưa thay đổi (mtime), bỏ qua gọi AI và trả về False ngay
        # Nếu lần trước đã sửa THÀNH CÔNG và file chưa thay đổi (mtime), bỏ qua gọi AI và trả về True ngay
        try:
            import json
            import os

            status_path = Path(str(file_path) + ".ai_fix_status.json")
            current_mtime = os.path.getmtime(file_path)
            if status_path.exists():
                with open(status_path, "r", encoding="utf-8") as sf:
                    status = json.load(sf)
                last_status = status.get("status")
                last_mtime = status.get("file_mtime")
                # So sánh mtime với sai số nhỏ
                if (
                    isinstance(last_mtime, (int, float))
                    and abs(current_mtime - float(last_mtime)) < 1e-6
                ):
                    if last_status == "failed":
                        logger.info(
                            "⏭️ Bỏ qua AI fixer: file đã được thử sửa và thất bại ở phiên trước, file chưa thay đổi. Fallback sang Python engine."
                        )
                        return False
                    if last_status == "success":
                        logger.info(
                            "✅ Bỏ qua AI fixer: file đã được sửa thành công ở phiên trước và chưa thay đổi."
                        )
                        return True
        except Exception:
            # Không chặn quy trình nếu lỗi đọc status
            pass

        # Backup
        if backup:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = (
                file_path.parent
                / f"{file_path.stem}_ai_fix_backup_{timestamp}{file_path.suffix}"
            )
            shutil.copy2(file_path, backup_path)
            logger.info(f"💾 Đã backup file gốc: {backup_path}")

        # Đọc file gốc
        try:
            with open(file_path, "r", encoding=encoding) as f:
                original_lines = f.readlines()
        except Exception as e:
            logger.error(f"Lỗi khi đọc file: {e}")
            return False

        if not original_lines:
            logger.error("File rỗng")
            return False

        # Tổng vòng retry: 3 (lưu file mỗi vòng, kể cả khi còn lỗi)
        last_error_for_status = None
        for round_idx in range(3):
            logger.info(f"🔄 Vòng sửa {round_idx + 1}/3...")

            # Đọc lại file để lấy trạng thái mới nhất (có thể đã thay đổi ở vòng trước)
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    current_lines = f.readlines()
                if not current_lines:
                    logger.error("File rỗng, không thể tiếp tục")
                    last_error_for_status = "empty_file"
                    break
                current_header = current_lines[0].strip()
            except Exception as e:
                logger.error(f"Lỗi khi đọc file ở vòng {round_idx + 1}: {e}")
                last_error_for_status = str(e)
                break

            # Tính expected_columns từ header hiện tại
            try:
                import csv as csv_module
                import io

                reader = csv_module.reader(io.StringIO(current_header))
                current_expected_columns = len(next(reader))
            except Exception:
                # Fallback: dùng split nếu CSV reader thất bại
                current_expected_columns = len(current_header.split(","))

            # Build prompt theo trạng thái file hiện tại mỗi vòng
            prompt = self._build_fix_prompt(
                str(file_path), file_type, current_header, [], error_message, encoding
            )
            ai_response = await self._call_ai_fix(prompt)
            if not ai_response:
                logger.error("AI không trả về response")
                last_error_for_status = "no_ai_response"
                # Dừng vòng này và thử vòng tiếp theo nếu còn
                continue

            fixed_lines = self._parse_ai_response(ai_response, current_expected_columns)
            if not fixed_lines:
                logger.warning("AI không trả về dòng nào đã sửa")
                last_error_for_status = "no_fixed_lines"
                continue

            logger.info(f"✅ AI đã sửa {len(fixed_lines)} dòng")

            try:
                # Sử dụng current_lines đã đọc ở đầu vòng lặp
                merged_lines = self._merge_fixed_lines(
                    current_lines, fixed_lines, current_header, current_expected_columns
                )
                # Không cần extend thêm vì _merge_fixed_lines đã xử lý đầy đủ
                # Logic extend cũ có thể gây lỗi vì merged_lines đã bao gồm header

                with open(file_path, "w", encoding=encoding, newline="") as f:
                    for line in merged_lines:
                        f.write(line + "\n")

                logger.info(f"✅ Đã lưu đè file đã sửa vào file gốc: {file_path}")

                # Verify bằng engine='c'
                try:
                    import pandas as pd

                    verify_df = pd.read_csv(
                        file_path,
                        dtype=str,
                        keep_default_na=False,
                        engine="c",
                        quoting=csv.QUOTE_MINIMAL,
                    )
                    logger.info(
                        f"✅ File đã sửa hợp lệ: {len(verify_df)} dòng, {len(verify_df.columns)} cột"
                    )
                    logger.info(
                        "✅ File metadata đã được sửa và lưu đè. Các phiên làm việc sau sẽ không cần fix lại."
                    )
                    # Ghi status success
                    try:
                        import json
                        import os

                        status_path = Path(str(file_path) + ".ai_fix_status.json")
                        with open(status_path, "w", encoding="utf-8") as sf:
                            json.dump(
                                {
                                    "status": "success",
                                    "file_path": str(file_path),
                                    "file_mtime": os.path.getmtime(file_path),
                                    "timestamp": datetime.now().isoformat(),
                                    "file_type": file_type,
                                },
                                sf,
                                ensure_ascii=False,
                                indent=2,
                            )
                    except Exception:
                        pass
                    return True
                except Exception as verify_error:
                    logger.warning(
                        f"⚠️ File vẫn có lỗi sau khi sửa (vòng {round_idx + 1}/3): {verify_error}"
                    )
                    last_error_for_status = str(verify_error)
                    # Chuẩn hóa bằng Python engine, ghi lại, verify lại
                    try:
                        import pandas as pd

                        delim = ","
                        try:
                            with open(file_path, "r", encoding=encoding) as f:
                                sample = f.read(4096)
                            import csv as csv_module

                            sniffer = csv_module.Sniffer()
                            dialect = sniffer.sniff(sample)
                            delim = dialect.delimiter
                        except Exception:
                            pass
                        df_py = pd.read_csv(
                            file_path,
                            dtype=str,
                            keep_default_na=False,
                            engine="python",
                            sep=delim,
                            on_bad_lines="skip",
                        )
                        df_py.to_csv(file_path, index=False, quoting=csv.QUOTE_MINIMAL)
                        logger.info(
                            "✅ Đã chuẩn hóa lại CSV bằng Python engine và lưu theo chuẩn quoting."
                        )
                        # Verify lại
                        try:
                            verify_df2 = pd.read_csv(
                                file_path,
                                dtype=str,
                                keep_default_na=False,
                                engine="c",
                                quoting=csv.QUOTE_MINIMAL,
                            )
                            logger.info(
                                f"✅ File đã chuẩn hóa hợp lệ: {len(verify_df2)} dòng, {len(verify_df2.columns)} cột"
                            )
                            # Ghi status success
                            try:
                                import json
                                import os

                                status_path = Path(
                                    str(file_path) + ".ai_fix_status.json"
                                )
                                with open(status_path, "w", encoding="utf-8") as sf:
                                    json.dump(
                                        {
                                            "status": "success",
                                            "file_path": str(file_path),
                                            "file_mtime": os.path.getmtime(file_path),
                                            "timestamp": datetime.now().isoformat(),
                                            "file_type": file_type,
                                            "note": "normalized_by_python_engine",
                                        },
                                        sf,
                                        ensure_ascii=False,
                                        indent=2,
                                    )
                            except Exception:
                                pass
                            return True
                        except Exception as e4:
                            logger.warning(
                                f"⚠️ Chuẩn hóa vẫn thất bại với engine='c': {e4}"
                            )
                            # Tiếp tục vòng kế tiếp nếu còn
                            continue
                    except Exception as norm_err:
                        logger.warning(f"⚠️ Lỗi khi chuẩn hóa CSV fallback: {norm_err}")
                        continue
            except Exception as e_round:
                logger.error(f"Lỗi khi ghi/merge ở vòng {round_idx + 1}: {e_round}")
                last_error_for_status = str(e_round)
                continue

        # Hết 3 vòng mà vẫn lỗi: ghi status failed và hướng dẫn
        try:
            import json
            import os

            status_path = Path(str(file_path) + ".ai_fix_status.json")
            with open(status_path, "w", encoding="utf-8") as sf:
                json.dump(
                    {
                        "status": "failed",
                        "file_path": str(file_path),
                        "file_mtime": os.path.getmtime(file_path),
                        "timestamp": datetime.now().isoformat(),
                        "file_type": file_type,
                        "error": last_error_for_status or "unknown",
                    },
                    sf,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            pass

        logger.warning(
            '⚠️ CSV vẫn còn lỗi sau 3 vòng sửa. Gợi ý: kiểm tra các giá trị có dấu phẩy nhưng không bọc ""; đảm bảo mỗi dòng đúng số cột; dùng Excel/LibreOffice để thêm "" cho các ô chứa dấu phẩy.'
        )
        return False

    def fix_csv_file_sync(
        self,
        file_path: str,
        file_type: str,
        encoding: str = "utf-8",
        error_message: str = "",
        backup: bool = True,
    ) -> bool:
        """
        Synchronous wrapper cho fix_csv_file.

        Hỗ trợ cả sync và async context bằng cách:
        - Nếu có event loop đang chạy: chạy trong thread riêng
        - Nếu không có event loop: chạy trực tiếp

        Args:
            file_path: Đường dẫn file CSV cần sửa
            file_type: Loại file ('glossary' hoặc 'character_relations')
            encoding: Encoding của file (mặc định: 'utf-8')
            error_message: Thông báo lỗi từ pandas
            backup: Tự động backup file gốc (mặc định: True)

        Returns:
            True nếu sửa thành công, False nếu thất bại
        """
        try:
            # Kiểm tra xem có event loop đang chạy không
            loop = asyncio.get_running_loop()
            # Nếu có event loop đang chạy, không thể dùng run_until_complete
            # Sử dụng asyncio.run_coroutine_threadsafe hoặc tạo task mới
            # Nhưng trong trường hợp này, tốt nhất là tạo thread riêng
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self._fix_csv_file_in_thread,
                    file_path,
                    file_type,
                    encoding,
                    error_message,
                    backup,
                )
                return future.result(timeout=300)  # 5 phút timeout
        except RuntimeError:
            # Không có event loop đang chạy, có thể dùng run_until_complete
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(
                self.fix_csv_file(file_path, file_type, encoding, error_message, backup)
            )

    def _fix_csv_file_in_thread(
        self,
        file_path: str,
        file_type: str,
        encoding: str,
        error_message: str,
        backup: bool,
    ) -> bool:
        """
        Helper để chạy fix_csv_file trong thread riêng.

        Tạo event loop mới trong thread này để chạy async function.

        Args:
            file_path: Đường dẫn file CSV cần sửa
            file_type: Loại file ('glossary' hoặc 'character_relations')
            encoding: Encoding của file
            error_message: Thông báo lỗi từ pandas
            backup: Tự động backup file gốc

        Returns:
            True nếu sửa thành công, False nếu thất bại
        """
        # Tạo event loop mới trong thread này
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.fix_csv_file(file_path, file_type, encoding, error_message, backup)
            )
        finally:
            loop.close()
