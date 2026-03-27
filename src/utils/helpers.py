# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Module chứa các hàm tiện ích chung cho dự án Novel Translator.

Các chức năng chính:
- Kiểm tra và tự động cài đặt dependencies
- Lazy import và cài đặt packages
- Đếm tokens trong text
"""

import logging
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional

try:
    from importlib import metadata as importlib_metadata
except ImportError:
    import importlib_metadata

logger = logging.getLogger("NovelTranslator")

# Mapping từ package name (trong requirements.txt) → import name (thực tế)
# Một số packages có tên khác khi import
PACKAGE_IMPORT_MAPPING: Dict[str, str] = {
    "Pillow": "PIL",
    "PyYAML": "yaml",
    "beautifulsoup4": "bs4",
    "python-docx": "docx",
    "pytesseract": "pytesseract",
    "pdf2image": "pdf2image",
    "google-generativeai": "google.generativeai",  # SDK cũ (backward compatibility)
    "google-genai": "google.genai",  # SDK mới
    "pandas": "pandas",
    "chardet": "chardet",
    "tqdm": "tqdm",
    "ebooklib": "ebooklib",
    "PyPDF2": "PyPDF2",
    "pdfplumber": "pdfplumber",  # OCR module dependency
    "pypandoc": "pypandoc",
    "colorlog": "colorlog",
}


def _check_package_installed(package_name: str) -> bool:
    """
    Kiểm tra xem package đã được cài đặt chưa bằng cách thử import thực tế.

    Args:
        package_name: Tên package trong requirements.txt (ví dụ: "Pillow", "PyYAML")

    Returns:
        True nếu package đã cài đặt, False nếu chưa
    """
    # Strategy 1: Thử import với mapping (nếu có)
    import_name = PACKAGE_IMPORT_MAPPING.get(package_name)
    if import_name:
        try:
            __import__(import_name)
            return True
        except ImportError:
            pass

    # Strategy 2: Thử check version bằng importlib_metadata (chính xác cho package name)
    try:
        version = importlib_metadata.version(package_name)
        # Nếu có version, thử import với các tên phổ biến
        possible_import_names: List[str] = [
            package_name.lower().replace(
                "-", "_"
            ),  # google-generativeai -> google_generativeai
            package_name.lower().replace(
                "-", ""
            ),  # python-docx -> pythondocx (ít dùng)
            package_name,  # giữ nguyên
        ]

        for possible_name in possible_import_names:
            try:
                __import__(possible_name)
                # Có version VÀ import được → chắc chắn đã cài
                return True
            except ImportError:
                continue

        # Nếu có version nhưng không import được, kiểm tra xem có phải package cấp thấp không
        # Một số packages như 'setuptools', 'pip' có thể không cần import
        # Nhưng với các packages trong requirements.txt, chúng ta cần import được
        # Vì vậy, nếu có version nhưng không import được → coi là chưa cài đúng cách
        # (có thể là dependency conflict hoặc partial installation)
        logger.debug(
            f"Package '{package_name}' có version {version} nhưng không thể import"
        )
        # Vẫn return True vì có version → đã cài (có thể là issue khác)
        return True
    except (importlib_metadata.PackageNotFoundError, Exception) as e:
        logger.debug(f"Package '{package_name}' không tìm thấy version: {e}")
        pass

    # Strategy 3: Thử import với tên tự động generate (fallback)
    auto_import_name = package_name.lower().replace("-", "_")
    try:
        __import__(auto_import_name)
        return True
    except ImportError:
        pass

    # Không tìm thấy package
    return False


DEFAULT_REQUIREMENTS_PATH = "requirements.txt"


def parse_requirements(requirements_path: str = DEFAULT_REQUIREMENTS_PATH) -> List[str]:
    """
    Parses requirements.txt to get a list of package names.

    Args:
        requirements_path: Path to the requirements file.

    Returns:
        List of package names.
    """
    if not os.path.exists(requirements_path):
        logger.warning(
            f"Không tìm thấy tệp '{requirements_path}'. Bỏ qua việc kiểm tra thư viện."
        )
        return []

    try:
        with open(requirements_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        required_packages: List[str] = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Lấy tên package (trước dấu ==, >=, >, <, @)
            package = (
                line.split("==")[0]
                .split(">=")[0]
                .split("<=")[0]
                .split(">")[0]
                .split("<")[0]
                .split("@")[0]
                .strip()
            )
            package = package.replace("git+", "")
            if package and ".git" not in package:
                required_packages.append(package)
        return required_packages

    except FileNotFoundError:
        logger.warning(f"Không tìm thấy file '{requirements_path}'.")
        return []
    except Exception as e:
        logger.error(f"Lỗi khi đọc tệp requirements.txt: {e}", exc_info=True)
        return []


def install_packages(
    packages: List[str], requirements_path: str = DEFAULT_REQUIREMENTS_PATH
) -> bool:
    """
    Installs a list of packages using pip.

    Args:
        packages: List of package names to install.
        requirements_path: Path to requirements.txt (for fallback reference).

    Returns:
        True if installation was successful, False otherwise.
    """
    if not packages:
        return True

    logger.warning(
        f"Phát hiện {len(packages)} thư viện cần thiết chưa được cài đặt: "
        f"{', '.join(packages)}"
    )
    logger.info("Đang tự động cài đặt các thư viện từ requirements.txt...")

    try:
        # Cài đặt các packages
        # Note: We install from requirements file to respect version constraints
        # But here we are triggered by missing individual packages.
        # Installing purely from requirements.txt is safer to ensure consistency.
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_path],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            logger.info("✓ Cài đặt thành công!")
            return True
        else:
            logger.error(f"Quá trình cài đặt thất bại với mã lỗi {result.returncode}")
            logger.debug(f"STDOUT: {result.stdout}")
            logger.debug(f"STDERR: {result.stderr}")
            logger.info(
                f"Vui lòng thử chạy lệnh thủ công: pip install -r {requirements_path}"
            )
            return False

    except subprocess.SubprocessError as e:
        logger.error(f"Lỗi khi chạy subprocess cài đặt packages: {e}", exc_info=True)
        logger.info(
            f"Vui lòng thử chạy lệnh thủ công: pip install -r {requirements_path}"
        )
        return False
    except Exception as e:
        logger.error(f"Lỗi không mong đợi khi cài đặt packages: {e}", exc_info=True)
        logger.info(
            f"Vui lòng thử chạy lệnh thủ công: pip install -r {requirements_path}"
        )
        return False


def check_and_install_dependencies(
    requirements_path: str = DEFAULT_REQUIREMENTS_PATH,
) -> None:
    """
    Kiểm tra và tự động cài đặt các thư viện cần thiết.

    Đọc file requirements.txt, kiểm tra từng package đã được cài đặt chưa,
    và tự động cài đặt các package còn thiếu.

    Args:
        requirements_path: Đường dẫn đến file requirements.txt

    Returns:
        None. Hàm này có thể exit chương trình (sys.exit(0)) nếu cài đặt package mới thành công.
    """
    required_packages = parse_requirements(requirements_path)

    if not required_packages:
        logger.debug(
            "Không tìm thấy package nào trong requirements.txt (hoặc file lỗi)"
        )
        return

    missing_packages: List[str] = []
    for package in required_packages:
        if not _check_package_installed(package):
            missing_packages.append(package)
            logger.debug(f"Package thiếu: {package}")

    if missing_packages:
        success = install_packages(missing_packages, requirements_path)

        if success:
            # Kiểm tra lại xem packages đã được cài chưa
            still_missing: List[str] = []
            for package in missing_packages:
                if not _check_package_installed(package):
                    still_missing.append(package)

            if still_missing:
                logger.warning(
                    f"Một số packages vẫn chưa được cài đặt: {', '.join(still_missing)}"
                )
                logger.info(
                    f"Vui lòng chạy lệnh thủ công: pip install {' '.join(still_missing)}"
                )
                # Không exit, tiếp tục chạy (có thể packages vẫn hoạt động)
            else:
                logger.info("Tất cả packages đã được cài đặt thành công.")
                # Chỉ yêu cầu chạy lại nếu thực sự cài package mới
                logger.info("VUI LÒNG CHẠY LẠI CHƯƠNG TRÌNH để áp dụng các thay đổi.")
                sys.exit(0)
    else:
        logger.debug("Tất cả các thư viện cần thiết đã được cài đặt.")


def lazy_import_and_install(
    package: str, import_name: Optional[str] = None, version_spec: Optional[str] = None
):
    """
    Chỉ import/cài đặt package khi thực sự cần.

    Thử import module trước, nếu không thành công thì tự động cài đặt package
    và import lại. Không yêu cầu khởi động lại chương trình.

    Args:
        package: Tên package để pip install (ví dụ 'opencv-python-headless')
        import_name: Tên module để import (mặc định = tên trước dấu '-' → '_')
        version_spec: Ràng buộc phiên bản, ví dụ '>=1.0.0', '==1.26.4'

    Returns:
        Module đã import thành công.

    Raises:
        ImportError: Nếu không thể cài đặt hoặc import package.

    Example:
        >>> cv2 = lazy_import_and_install('opencv-python-headless', 'cv2')
        >>> # Module cv2 đã sẵn sàng sử dụng
    """
    import importlib
    import importlib.util

    target_import = import_name or package.replace("-", "_")

    try:
        return importlib.import_module(target_import)
    except ImportError:
        pass

    # Cài đặt tại chỗ rồi import lại
    pkg_spec = package + (version_spec or "")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg_spec],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error(f"Cài đặt '{pkg_spec}' thất bại: {result.stderr.strip()}")
            raise ImportError(f"Không thể cài đặt gói: {pkg_spec}")
        # Làm mới cache và import lại
        importlib.invalidate_caches()
        return importlib.import_module(target_import)
    except Exception as e:
        raise ImportError(f"Lazy import thất bại cho '{pkg_spec}': {e}")


def count_tokens(text: str) -> int:
    """
    Đếm số tokens trong text dựa trên heuristic.

    Sử dụng công thức:
    - CJK characters (Chinese, Japanese, Korean): 1.5 tokens/character
    - Các ký tự khác: 0.25 tokens/character (4 characters = 1 token)

    Args:
        text: Text cần đếm tokens

    Returns:
        Số tokens ước tính (làm tròn xuống số nguyên)

    Example:
        >>> count_tokens("Hello world")
        3  # 11 characters / 4 = 2.75 → 2 (rounded down)
        >>> count_tokens("你好")
        3  # 2 CJK characters * 1.5 = 3
    """
    if not text:
        return 0

    # Đếm CJK characters (Chinese, Japanese, Korean)
    cjk_pattern = r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]"
    cjk_chars = len(re.findall(cjk_pattern, text))
    other_chars = len(text) - cjk_chars

    # Tính tokens: CJK * 1.5 + other / 4
    tokens = int(cjk_chars * 1.5 + other_chars / 4)
    return tokens
