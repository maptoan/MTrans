# -*- coding: utf-8 -*-

"""
Module kiểm tra và phát hiện chunk có kích thước bất thường
"""

import logging
import statistics
from typing import Any, Dict, List

logger = logging.getLogger("NovelTranslator")


class ChunkSizeValidator:
    """Kiểm tra kích thước chunk để phát hiện lỗi dịch thiếu"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.size_config = config.get("translation", {}).get(
            "chunk_size_validation", {}
        )

        # Cấu hình từ config - CHẶT CHẼ HỢP LÝ
        self.enable_validation = config.get("translation", {}).get(
            "enable_chunk_size_validation", True
        )
        self.enable_size_check = self.size_config.get("enable_size_check", True)
        self.deviation_threshold = self.size_config.get(
            "size_deviation_threshold", 0.5
        )  # Đơn giản: 50%
        self.min_absolute_size = self.size_config.get(
            "min_absolute_size", 100
        )  # Tăng lên 100
        self.max_retries = self.size_config.get("max_retries_for_size", 2)  # Tăng lên 2
        self.adaptive_threshold = self.size_config.get(
            "enable_adaptive_threshold", True
        )
        self.check_method = self.size_config.get("size_check_method", "statistical")
        self.enable_punctuation_check = self.size_config.get(
            "enable_punctuation_check", False
        )
        self.last_chunk_relaxed_threshold = self.size_config.get(
            "last_chunk_relaxed_threshold", 1.2
        )  # Giảm xuống 1.2
        self.enable_word_ratio_check = self.size_config.get(
            "enable_word_ratio_check", True
        )
        self.min_word_ratio = self.size_config.get("min_word_ratio", 1.2)  # 120%
        self.max_word_ratio = self.size_config.get("max_word_ratio", 2.0)  # 200%

        # Thêm cấu hình tối ưu hóa - CHẶT CHẼ HỢP LÝ
        self.min_size_ratio = (
            0.3  # Chunk nhỏ hơn 30% trung bình = bất thường (cân bằng)
        )
        self.max_size_ratio = (
            5.0  # Chunk lớn hơn 500% trung bình = bất thường (chặt chẽ hơn)
        )
        self.z_score_threshold = 1.5  # Z-score threshold (giảm xuống 1.5)
        self.percentile_threshold = 0.15  # 15th percentile (tăng lên 15th)

        # Lưu trữ thống kê chunk sizes
        self.chunk_sizes = []
        self.average_size = 0
        self.median_size = 0
        self.std_deviation = 0

        logger.info(
            f"ChunkSizeValidator khởi tạo: enable={self.enable_validation}, "
            f"method={self.check_method}, threshold={self.deviation_threshold}"
        )

    def add_chunk_size(
        self, chunk_id: int, original_size: int, translated_size: int
    ) -> None:
        """Thêm kích thước chunk vào thống kê"""
        if not self.enable_validation or not self.enable_size_check:
            return

        # Chỉ lưu kích thước bản dịch (không phải bản gốc)
        self.chunk_sizes.append(
            {
                "chunk_id": chunk_id,
                "original_size": original_size,
                "translated_size": translated_size,
                "size_ratio": translated_size / original_size
                if original_size > 0
                else 0,
            }
        )

        # Cập nhật thống kê
        self._update_statistics()

        logger.debug(
            f"Chunk {chunk_id}: original={original_size}, translated={translated_size}, "
            f"ratio={translated_size / original_size:.2f}"
        )

    def _update_statistics(self) -> None:
        """Cập nhật thống kê từ dữ liệu hiện có"""
        if len(self.chunk_sizes) < 2:
            return

        translated_sizes = [chunk["translated_size"] for chunk in self.chunk_sizes]

        self.average_size = statistics.mean(translated_sizes)
        self.median_size = statistics.median(translated_sizes)
        self.std_deviation = (
            statistics.stdev(translated_sizes) if len(translated_sizes) > 1 else 0
        )

        logger.debug(
            f"Thống kê cập nhật: avg={self.average_size:.0f}, "
            f"median={self.median_size:.0f}, std={self.std_deviation:.0f}"
        )

    def validate_chunk_size(
        self,
        chunk_id: int,
        original_size: int,
        translated_size: int,
        translated_text: str = "",
        is_last_chunk: bool = False,
        original_text: str = None,
    ) -> Dict[str, Any]:
        """Kiểm tra kích thước chunk có bất thường không - TỐI ƯU HÓA HOÀN TOÀN"""

        # 1. KIỂM TRA CƠ BẢN - Nhanh nhất
        if not self.enable_validation or not self.enable_size_check:
            return self._create_result(
                True, False, "validation_disabled", translated_size, original_size, 0
            )

        # 2. KIỂM TRA TUYỆT ĐỐI - Không phụ thuộc thống kê
        if translated_size < self.min_absolute_size and not is_last_chunk:
            return self._create_result(
                False,
                True,
                "below_minimum_size",
                translated_size,
                original_size,
                0,
                f"Kích thước {translated_size} < {self.min_absolute_size}",
            )

        # 3. KIỂM TRA CHUNK CUỐI CÙNG
        if is_last_chunk and translated_size < (self.min_absolute_size * 0.5):
            return self._create_result(
                False,
                True,
                "last_chunk_too_small",
                translated_size,
                original_size,
                0,
                f"Chunk cuối cùng quá nhỏ: {translated_size} < {self.min_absolute_size * 0.5}",
            )

        # 4. KIỂM TRA CHUNK CỰC NHỎ (không phải chunk cuối) - CHỈ KHI THỰC SỰ CỰC NHỎ
        if (
            not is_last_chunk
            and len(self.chunk_sizes) >= 3
            and translated_size < (self.average_size * 0.15)
        ):
            deviation = self._calculate_deviation(translated_size)
            return self._create_result(
                False,
                True,
                "extremely_small_chunk",
                translated_size,
                original_size,
                deviation,
                f"Chunk cực nhỏ: {translated_size} < {self.average_size * 0.15:.0f} (15% trung bình)",
            )

        # 5. KIỂM TRA DỮ LIỆU ĐỦ
        if len(self.chunk_sizes) < 3:
            return self._create_result(
                True, False, "insufficient_data", translated_size, original_size, 0
            )

        # 6. TÍNH TOÁN ĐỘ LỆCH
        deviation = self._calculate_deviation(translated_size)

        # 7. KIỂM TRA KÍCH THƯỚC BẤT THƯỜNG
        is_abnormal = self._check_abnormal_size(translated_size, deviation, chunk_id)

        # 8. KIỂM TRA CHUNK CUỐI CÙNG VỚI NGƯỠNG LỎNG HƠN
        if is_last_chunk and is_abnormal:
            is_abnormal = deviation > (
                self.deviation_threshold * self.last_chunk_relaxed_threshold
            )

        # 9. KIỂM TRA DẤU CÂU (nếu được bật)
        punctuation_issues = []
        if self.enable_punctuation_check and translated_text:
            punctuation_issues = self._check_punctuation_issues(translated_text)

        # 10. KIỂM TRA TỶ LỆ TỪ - ĐÃ LOẠI BỎ
        # word_ratio_issues = []
        # if self.enable_word_ratio_check and original_text and translated_text:
        #     word_ratio_issues = self._check_word_ratio(original_text, translated_text, chunk_id)

        # 11. TỔNG HỢP KẾT QUẢ
        if is_abnormal or punctuation_issues:
            reason = "size_deviation" if is_abnormal else "punctuation_issues"
            details = []

            if is_abnormal:
                details.append(
                    f"Kích thước {translated_size} lệch {deviation:.1%} so với trung bình {self.average_size:.0f}"
                )

            if punctuation_issues:
                details.extend(punctuation_issues)

            return self._create_result(
                False,
                True,
                reason,
                translated_size,
                original_size,
                deviation,
                "; ".join(details),
                punctuation_issues,
            )
        else:
            return self._create_result(
                True, False, "normal_size", translated_size, original_size, deviation
            )

    def _create_result(
        self,
        is_valid: bool,
        needs_retry: bool,
        reason: str,
        translated_size: int,
        original_size: int,
        deviation: float,
        details: str = "",
        punctuation_issues: List[str] = None,
    ) -> Dict[str, Any]:
        """Tạo kết quả validation - TỐI ƯU HÓA"""
        result = {
            "is_valid": is_valid,
            "needs_retry": needs_retry,
            "reason": reason,
            "size_ratio": translated_size / original_size if original_size > 0 else 0,
            "deviation": deviation,
        }

        if details:
            result["details"] = details

        if punctuation_issues:
            result["punctuation_issues"] = punctuation_issues

        return result

    def _calculate_deviation(self, translated_size: int) -> float:
        """Tính độ lệch của kích thước so với trung bình"""
        if self.average_size == 0:
            return 0
        # Tính độ lệch tuyệt đối (cả lớn hơn và nhỏ hơn)
        return abs(self.average_size - translated_size) / self.average_size

    def _check_abnormal_size(
        self, translated_size: int, deviation: float, chunk_id: int = None
    ) -> bool:
        """Kiểm tra xem kích thước có bất thường không - ĐƠN GIẢN HÓA"""

        # 1. KIỂM TRA TUYỆT ĐỐI - Không phụ thuộc thống kê (ưu tiên cao nhất)
        if translated_size < self.min_absolute_size:
            logger.debug(
                f"Chunk {chunk_id}: Chunk quá nhỏ tuyệt đối: {translated_size} < {self.min_absolute_size}"
            )
            return True

        # 2. KIỂM TRA ĐƠN GIẢN - Chỉ so sánh với trung bình (không tính chunk failed)
        if self.average_size > 0:
            # Tính tỷ lệ so với trung bình
            ratio = translated_size / self.average_size

            # Nếu tỷ lệ < mức tối thiểu (mặc định 20% = 0.8) thì failed
            min_ratio = 1.0 - self.deviation_threshold  # 1.0 - 0.2 = 0.8 (80%)

            # Log thông tin để debug
            logger.debug(
                f"Chunk {chunk_id}: Size check: {translated_size} vs avg {self.average_size:.0f} (ratio: {ratio:.2f}, min: {min_ratio:.2f})"
            )

            if ratio < min_ratio:
                logger.warning(
                    f"Chunk {chunk_id}: Chunk quá nhỏ so với trung bình: {translated_size} < {self.average_size * min_ratio:.0f} ({min_ratio:.0%} trung bình)"
                )
                return True

    def _check_statistical(self, translated_size: int, deviation: float) -> bool:
        """Kiểm tra theo phương pháp thống kê - CHỈ KIỂM TRA CHUNK NHỎ"""
        if self.std_deviation > 0:
            # Chỉ kiểm tra chunk nhỏ hơn trung bình
            if translated_size < self.average_size:
                z_score = abs(translated_size - self.average_size) / self.std_deviation
                return z_score > self.z_score_threshold
        else:
            # Fallback: chỉ kiểm tra chunk nhỏ
            if translated_size < self.average_size:
                return deviation > (self.deviation_threshold * 0.8)
        return False

    def _check_percentile(self, translated_size: int, deviation: float) -> bool:
        """Kiểm tra theo phương pháp percentile - TỐI ƯU HÓA"""
        if len(self.chunk_sizes) >= 10:
            sizes = sorted([chunk["translated_size"] for chunk in self.chunk_sizes])
            percentile_threshold = sizes[int(len(sizes) * self.percentile_threshold)]
            return translated_size < percentile_threshold
        else:
            # Fallback: kiểm tra độ lệch
            return deviation > (self.deviation_threshold * 0.8)

    def _check_fixed_ratio(self, translated_size: int, deviation: float) -> bool:
        """Kiểm tra theo phương pháp tỷ lệ cố định - ĐƠN GIẢN"""
        if self.average_size == 0:
            return False

        # ĐƠN GIẢN: Chunk nhỏ hơn 80% trung bình = bất thường
        min_acceptable_size = self.average_size * 0.8
        is_too_small = translated_size < min_acceptable_size

        if is_too_small:
            logger.debug(
                f"Chunk quá nhỏ: {translated_size} < {min_acceptable_size:.0f} (80% trung bình)"
            )

        return is_too_small

    def _check_word_ratio(
        self, original_text: str, translated_text: str, chunk_id: int
    ) -> List[str]:
        """Kiểm tra tỷ lệ từ để đảm bảo chất lượng bản dịch"""
        try:
            # Đếm từ trong văn bản gốc (tiếng Trung)
            original_words = self._count_words(original_text)

            # Đếm từ trong văn bản dịch (tiếng Việt)
            translated_words = self._count_words(translated_text)

            if original_words == 0:
                return []

            # Tính tỷ lệ từ
            word_ratio = translated_words / original_words

            issues = []

            # Kiểm tra tỷ lệ từ theo config - CHỈ KIỂM TRA TỶ LỆ QUÁ THẤP
            if word_ratio < self.min_word_ratio:
                issues.append(
                    f"Tỷ lệ từ quá thấp: {word_ratio:.1%} (< {self.min_word_ratio:.0%}) - {original_words}→{translated_words} từ"
                )
                logger.warning(
                    f"Chunk {chunk_id}: Tỷ lệ từ quá thấp {word_ratio:.1%} - có thể dịch thiếu"
                )
            else:
                logger.debug(
                    f"Chunk {chunk_id}: Tỷ lệ từ hợp lý {word_ratio:.1%} - {original_words}→{translated_words} từ"
                )

            return issues

        except Exception as e:
            logger.error(f"Lỗi kiểm tra tỷ lệ từ chunk {chunk_id}: {e}")
            return []

    def _count_words(self, text: str) -> int:
        """Đếm số từ trong văn bản"""
        if not text or not isinstance(text, str):
            return 0

        # Loại bỏ khoảng trắng thừa và chia thành từ
        words = text.strip().split()

        # Lọc bỏ các từ rỗng
        words = [word for word in words if word.strip()]

        return len(words)

    def get_size_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê kích thước chunk"""
        if len(self.chunk_sizes) == 0:
            return {
                "total_chunks": 0,
                "average_size": 0,
                "median_size": 0,
                "std_deviation": 0,
                "min_size": 0,
                "max_size": 0,
            }

        sizes = [chunk["translated_size"] for chunk in self.chunk_sizes]

        return {
            "total_chunks": len(self.chunk_sizes),
            "average_size": self.average_size,
            "median_size": self.median_size,
            "std_deviation": self.std_deviation,
            "min_size": min(sizes),
            "max_size": max(sizes),
            "size_ratios": [chunk["size_ratio"] for chunk in self.chunk_sizes],
        }

    def generate_size_report(self, validation_result: Dict[str, Any]) -> str:
        """Tạo báo cáo chi tiết về kích thước chunk"""
        report = "=== BÁO CÁO KIỂM TRA KÍCH THƯỚC CHUNK ===\n"
        report += f"Chunk ID: {validation_result.get('chunk_id', 'N/A')}\n"
        report += f"Trạng thái: {'HỢP LỆ' if validation_result['is_valid'] else 'BẤT THƯỜNG'}\n"
        report += f"Lý do: {validation_result['reason']}\n"
        report += f"Tỷ lệ kích thước: {validation_result['size_ratio']:.2f}\n"
        report += f"Độ lệch: {validation_result['deviation']:.1%}\n"

        if not validation_result["is_valid"] and "details" in validation_result:
            report += f"Chi tiết: {validation_result['details']}\n"

        # Thêm thống kê tổng quan
        stats = self.get_size_statistics()
        if stats["total_chunks"] > 0:
            report += "\n--- THỐNG KÊ TỔNG QUAN ---\n"
            report += f"Tổng chunks: {stats['total_chunks']}\n"
            report += f"Kích thước trung bình: {stats['average_size']:.0f}\n"
            report += f"Kích thước trung vị: {stats['median_size']:.0f}\n"
            report += f"Độ lệch chuẩn: {stats['std_deviation']:.0f}\n"
            report += f"Kích thước nhỏ nhất: {stats['min_size']}\n"
            report += f"Kích thước lớn nhất: {stats['max_size']}\n"

        return report

    def _check_punctuation_issues(self, translated_text: str) -> List[str]:
        """Kiểm tra các vấn đề về dấu câu và câu cuối không trọn vẹn"""
        issues = []

        if not translated_text or len(translated_text.strip()) == 0:
            return issues

        # Loại bỏ khoảng trắng đầu cuối
        text = translated_text.strip()

        # Kiểm tra chunk không kết thúc bằng dấu câu
        if not self._ends_with_punctuation(text):
            issues.append("Không kết thúc bằng dấu câu")

        # CHỈ KIỂM TRA CÂU CUỐI CÙNG - không check toàn bộ chunk
        last_sentence = self._get_last_sentence(text)
        if last_sentence and self._is_incomplete_sentence(last_sentence):
            issues.append("Câu cuối không trọn vẹn")

        # Kiểm tra chunk bắt đầu bằng chữ thường (có thể bị cắt)
        if text and text[0].islower():
            issues.append("Bắt đầu bằng chữ thường")

        return issues

    def _get_last_sentence(self, text: str) -> str:
        """Lấy câu cuối cùng trong text - Đơn giản hóa"""
        if not text or len(text.strip()) < 3:
            return ""

        text = text.strip()

        # Tách câu dựa trên dấu câu - Đơn giản hóa
        sentences = []
        current_sentence = ""
        in_quotes = False
        quote_chars = ['"', "'", '"', "'", "«", "»", "「", "」", "『", "』"]
        sentence_endings = {".", "!", "?", "。", "！", "？", "…", "..."}

        for i, char in enumerate(text):
            current_sentence += char

            # Toggle quote state
            if char in quote_chars:
                in_quotes = not in_quotes

            # Tách câu khi không trong dấu ngoặc kép
            elif not in_quotes and char in sentence_endings:
                # Kiểm tra không phải dấu chấm trong số
                if char == "." and i > 0 and i < len(text) - 1:
                    if text[i - 1].isdigit() and text[i + 1].isdigit():
                        continue  # Bỏ qua dấu chấm trong số

                sentences.append(current_sentence.strip())
                current_sentence = ""

        # Thêm câu cuối nếu có
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        # Trả về câu cuối cùng (loại bỏ câu rỗng)
        valid_sentences = [s for s in sentences if s and len(s.strip()) > 1]
        return valid_sentences[-1] if valid_sentences else ""

    def _ends_with_punctuation(self, text: str) -> bool:
        """Kiểm tra text có kết thúc bằng dấu câu không (đơn giản và hiệu quả)"""
        if not text:
            return False

        # Loại bỏ khoảng trắng và ký tự xuống dòng cuối
        text = text.rstrip()

        if not text:
            return False

        # Các dấu câu kết thúc câu hợp lệ (bao gồm cả dấu ngoặc kép)
        valid_ending_punctuation = {
            # Dấu câu cơ bản
            ".",
            "!",
            "?",
            "。",
            "！",
            "？",
            # Dấu ngoặc kép (coi như dấu câu kết thúc câu)
            '"',
            '"',
            "'",
            "'",  # Ca ASCII va Unicode quotes
            # Dấu ngoặc vuông và đặc biệt
            "」",
            "』",
            "》",
            "》",
            # Dấu chấm lửng và gạch ngang Unicode
            "…",
            "—",
            "–",  # Unicode ellipsis, em dash, en dash
        }

        # Kiểm tra ký tự cuối cùng
        last_char = text[-1]
        if last_char in valid_ending_punctuation:
            return True

        # Kiểm tra dấu chấm lửng và gạch ngang (có thể có nhiều ký tự)
        if text.endswith("...") or text.endswith("——"):
            return True

        return False

    def _is_incomplete_sentence(self, sentence: str) -> bool:
        """Kiểm tra một câu có trọn vẹn không - TỐI ƯU HÓA"""
        if not sentence or len(sentence.strip()) < 3:
            return True

        sentence = sentence.strip()
        words = sentence.split()

        # Kiểm tra nhanh - câu quá ngắn
        if len(words) < 2:
            return True

        # Kiểm tra các dấu hiệu câu không trọn vẹn - TỐI ƯU HÓA
        incomplete_indicators = [
            # Câu bắt đầu bằng liên từ và rất ngắn
            (
                sentence.lower().startswith(
                    (
                        "và",
                        "nhưng",
                        "tuy",
                        "mặc dù",
                        "vì",
                        "do",
                        "nếu",
                        "khi",
                        "sau khi",
                        "and",
                        "but",
                        "though",
                        "although",
                        "because",
                        "if",
                        "when",
                        "after",
                    )
                )
                and len(words) < 5
            ),
            # Câu kết thúc bằng dấu phẩy, hai chấm và rất ngắn
            (
                sentence.endswith((",", ":", ";", "，", "：", "；", "...", "…"))
                and len(words) < 4
            ),
            # Câu quá ngắn và không có động từ chính
            (
                len(words) < 3
                and not any(
                    word in sentence.lower()
                    for word in [
                        "là",
                        "có",
                        "được",
                        "bị",
                        "làm",
                        "đi",
                        "đến",
                        "về",
                        "is",
                        "are",
                        "was",
                        "were",
                        "has",
                        "have",
                        "had",
                        "do",
                        "does",
                        "did",
                        "will",
                        "would",
                        "can",
                        "could",
                        "should",
                        "must",
                    ]
                )
            ),
            # Câu bắt đầu bằng chữ thường (có thể bị cắt)
            (sentence[0].islower() and len(words) < 4),
            # Câu kết thúc bằng từ nối
            (
                sentence.lower().endswith(
                    (
                        "và",
                        "nhưng",
                        "tuy",
                        "mặc dù",
                        "vì",
                        "do",
                        "nếu",
                        "khi",
                        "sau khi",
                        "and",
                        "but",
                        "though",
                        "although",
                        "because",
                        "if",
                        "when",
                        "after",
                    )
                )
                and len(words) < 6
            ),
        ]

        return any(incomplete_indicators)
