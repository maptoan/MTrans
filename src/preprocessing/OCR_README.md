# OCR Reader Module (v1.8.stable)

Module nhận dạng văn bản từ file scan (PDF hoặc ảnh) bằng Tesseract OCR, hỗ trợ tiếng Việt, Tiếng Anh và Tiếng Trung. Module đã được tích hợp với AI cleanup và spell check để đảm bảo chất lượng văn bản đầu ra.

## Tính năng

- ✅ **Hỗ trợ nhiều định dạng**: PDF, JPG, PNG, WEBP, BMP, TIFF
- ✅ **Đa ngôn ngữ**: Tiếng Việt (VN), Tiếng Anh (EN), Tiếng Trung (CN) với auto-detect Simplified/Traditional Chinese
- ✅ **AI Cleanup**: Tự động dọn dẹp văn bản OCR (loại bỏ header/footer lặp, ký tự rác, số trang)
- ✅ **AI Spell Check**: Soát lỗi chính tả và phục hồi cấu trúc paragraph thông minh
- ✅ **Chia chunk thông minh**: Tự động chia văn bản ở ranh giới câu để tránh cắt giữa câu
- ✅ **Check & Resume**: Tự động phát hiện và resume từ các bước đã hoàn tất (OCR, cleanup, spell check)
- ✅ **Auto-retry**: Tự động retry các chunks failed sau khi hoàn tất toàn bộ pipeline
- ✅ **Progress tracking**: Hiển thị tiến trình, thời gian trung bình và ETA cho PDF nhiều trang
- ✅ **Memory optimization**: Batch rendering và JPEG caching để giảm RAM/disk usage
- ✅ **Auto-install dependencies**: Tự động cài đặt các thư viện Python thiếu
- ✅ **Cấu hình linh hoạt**: Đọc từ YAML config với nhiều tùy chọn

## Cài đặt

### Yêu cầu hệ thống

1. **Tesseract OCR** (bắt buộc)
   - Tải về: https://github.com/tesseract-ocr/tesseract
   - Cài đặt và ghi nhớ đường dẫn, ví dụ: `C:\Program Files\Tesseract-OCR\tesseract.exe`
   - Cài đặt language packs cho `vie` và `eng` nếu cần

2. **Poppler** (bắt buộc cho PDF)
   - Tải về: https://github.com/oschwartz10612/poppler-windows/releases/
   - Giải nén và ghi nhớ đường dẫn `bin`, ví dụ: `C:\Program Files\poppler-24.08.0\Library\bin`

### Cài đặt Python packages

```bash
pip install -r requirements-ocr.txt
```

Hoặc cài thủ công:
```bash
pip install pytesseract pdf2image Pillow PyYAML tqdm
```

## Cấu hình

Thêm section `ocr` vào `config/config.yaml`:

```yaml
ocr:
  enabled: true
  # Đường dẫn tới tesseract.exe (Windows)
  tesseract_cmd: "C:/Program Files/Tesseract-OCR/tesseract.exe"
  
  # Đường dẫn tới thư mục bin của Poppler (Windows)
  poppler_path: "C:/Program Files/poppler-24.08.0/Library/bin"
  
  # Ngôn ngữ OCR: "VN", "EN", "CN", hoặc kết hợp "VN+EN"
  # Với "CN" sẽ tự động detect Simplified/Traditional Chinese
  lang: "VN"
  
  # Page Segmentation Mode (3: tự động, 6: một khối văn bản đồng nhất)
  psm: 3
  
  # DPI khi chuyển PDF sang ảnh (khuyến nghị: 300)
  dpi: 300
  
  # Hiển thị thanh tiến trình cho PDF nhiều trang
  show_progress: true
```

## Sử dụng

### 1. Từ command line

```bash
python src/preprocessing/ocr_reader.py "path/to/file.pdf" --output result.txt
python src/preprocessing/ocr_reader.py "path/to/image.jpg" --output result.txt
```

### 2. Từ Python code

```python
from src.preprocessing.ocr_reader import ocr_file

# Đọc text từ PDF
text = ocr_file("input.pdf", config_path="config/config.yaml")

# Lưu kết quả
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(text)
```

### 3. Tích hợp vào pipeline dịch thuật

Module này có thể được tích hợp vào quy trình preprocessing của novel translator:

```python
from src.preprocessing.ocr_reader import ocr_file

# Nếu file input là scan PDF
if file_path.endswith('.pdf'):
    raw_text = ocr_file(file_path, config_path="config/config.yaml")
    # Tiếp tục xử lý như văn bản thông thường
    cleaned_text = clean_text(raw_text)
    chunks = chunker.chunk_novel(cleaned_text)
```

## Tham số cấu hình chi tiết

### `tesseract_cmd`
- **Mô tả**: Đường dẫn đầy đủ tới `tesseract.exe`
- **Mặc định**: Bỏ trống (sẽ tìm trong PATH)
- **Ví dụ**: `"C:/Program Files/Tesseract-OCR/tesseract.exe"`

### `poppler_path`
- **Mô tả**: Đường dẫn tới thư mục `bin` của Poppler
- **Mặc định**: Bỏ trống (sẽ tìm trong PATH)
- **Ví dụ**: `"C:/Program Files/poppler-24.08.0/Library/bin"`

### `lang`
- **Mô tả**: Ngôn ngữ OCR (phải cài language pack tương ứng)
- **Giá trị**: `"VN"` (Tiếng Việt), `"EN"` (Tiếng Anh), `"CN"` (Tiếng Trung), hoặc kết hợp `"VN+EN"`
- **Đặc biệt**: Với `"CN"`, module sẽ tự động detect Simplified (`chi_sim`) hoặc Traditional (`chi_tra`) Chinese dựa trên nội dung
- **Mặc định**: `"VN"`

### `psm` (Page Segmentation Mode)
- **Mô tả**: Chế độ phân đoạn trang của Tesseract
- **Giá trị thường dùng**:
  - `3`: Tự động phân đoạn (khuyến nghị cho tài liệu phức tạp)
  - `6`: Giả định một khối văn bản đồng nhất (nhanh hơn cho văn bản đơn giản)
- **Mặc định**: `3`

### `dpi`
- **Mô tả**: Độ phân giải khi chuyển PDF sang ảnh
- **Giá trị**: 150-600 (mặc định: 250, khuyến nghị: 300)
- **Ảnh hưởng**: DPI cao = chất lượng tốt hơn nhưng chậm hơn và tốn bộ nhớ

### `show_progress`
- **Mô tả**: Hiển thị thanh tiến trình cho PDF nhiều trang
- **Giá trị**: `true` hoặc `false`
- **Yêu cầu**: Cần cài `tqdm`

### `safety_level`
- **Mô tả**: Mức độ chặn nội dung của Google Gemini API (cho AI cleanup và spell check)
- **Giá trị**: `"BLOCK_NONE"`, `"BLOCK_ONLY_HIGH"`, `"BLOCK_MEDIUM_AND_ABOVE"`, `"BLOCK_LOW_AND_ABOVE"`
- **Mặc định**: `"BLOCK_ONLY_HIGH"`
- **Ghi chú**: Đặt `"BLOCK_NONE"` để bỏ qua tất cả safety filters (hữu ích cho văn bản có thể bị nhầm là nội dung nhạy cảm)

### `ai_cleanup` và `ai_spell_check`
- **Mô tả**: Cấu hình cho AI cleanup và spell check
- **Chia chunk thông minh**: Tự động chia ở ranh giới câu (`.`, `!`, `?`, `。`, `！`, `？`) để tránh cắt giữa câu
- **Auto-retry**: Tự động retry các chunks failed sau khi hoàn tất toàn bộ pipeline
- **Memory optimization**: Batch rendering (mặc định 10-20 trang/batch) và JPEG caching để giảm RAM/disk usage

## Xử lý lỗi thường gặp

### 1. `RuntimeError: pytesseract not installed`
**Giải pháp**: Module sẽ tự động cài đặt. Nếu thất bại, chạy thủ công:
```bash
pip install pytesseract
```

### 2. `RuntimeError: pdf2image not installed`
**Giải pháp**: Module sẽ tự động cài đặt. Nếu thất bại, chạy thủ công:
```bash
pip install pdf2image
```

### 3. `pdf2image.exceptions.PDFInfoNotInstalledError`
**Nguyên nhân**: Poppler chưa được cài hoặc chưa có trong PATH
**Giải pháp**: 
- Cài Poppler và đặt `poppler_path` trong config
- Hoặc thêm Poppler `bin` vào PATH hệ thống

### 4. `RuntimeError: pytesseract not installed. Please install pytesseract and system Tesseract.`
**Nguyên nhân**: Tesseract OCR chưa được cài hoặc chưa đúng đường dẫn
**Giải pháp**: 
- Cài Tesseract OCR và đặt `tesseract_cmd` trong config
- Đảm bảo đã cài language packs cho ngôn ngữ bạn cần

### 5. OCR kết quả kém chất lượng
**Giải pháp**:
- Tăng `dpi` lên 400-600 (chậm hơn nhưng chất lượng tốt hơn)
- Thử các `psm` khác nhau (6 cho văn bản đơn giản, 3 cho phức tạp)
- Đảm bảo file scan có độ phân giải đủ cao

## Hiệu năng

### Thời gian xử lý ước tính
- **PDF 1 trang (300 DPI)**: ~5-10 giây
- **PDF 100 trang (300 DPI)**: ~10-15 phút
- **PDF 500 trang (300 DPI)**: ~50-60 phút

### Tối ưu hóa tốc độ và bộ nhớ
- Giảm `dpi` xuống 200-250 (chất lượng giảm nhẹ, nhanh hơn ~30%)
- Sử dụng `psm: 6` cho văn bản đơn giản (nhanh hơn ~20%)
- Batch rendering: Giảm `render_batch_size` xuống 10-15 cho file rất lớn
- JPEG caching: Sử dụng `image_format: "jpeg"` và `jpeg_quality: 85` để giảm disk usage

## Tính năng mới (v1.8.stable)

### Check & Resume
Module tự động phát hiện các file từ phiên làm việc trước:
- `filename_ocred.txt`: Kết quả sau OCR
- `filename_cleanup.txt`: Kết quả sau cleanup
- `filename.txt`: File output cuối cùng

Khi phát hiện các file này, bạn có thể:
1. **Resume từ Cleanup/Spell Check**: Tiếp tục từ bước cleanup hoặc spell check (bỏ qua OCR)
2. **Rerun toàn bộ**: Chạy lại từ đầu (OCR + Cleanup + Spell Check)
3. **Exit**: Thoát không làm gì

### Chia chunk thông minh
Module tự động chia văn bản ở ranh giới câu để đảm bảo:
- Không cắt giữa câu → Tránh lỗi ở đầu/cuối chunk
- Cleanup và spell check hoạt động với câu hoàn chỉnh → Kết quả chính xác hơn

### Auto-retry failed chunks
Sau khi hoàn tất toàn bộ pipeline, module tự động retry các chunks failed trong cleanup và spell check để tối đa hóa tỷ lệ thành công.

## Ghi chú

- Module tự động cài đặt các thư viện Python thiếu khi chạy lần đầu
- File tạm được lưu trong thư mục temp của hệ điều hành (Windows: `%TEMP%`)
- Progress bar chỉ hiển thị cho PDF có > 1 trang
- Kết quả OCR có thể chứa lỗi, đặc biệt với scan chất lượng thấp hoặc chữ viết tay
- File intermediate (`_ocred.txt`, `_cleanup.txt`) được lưu tự động để hỗ trợ resume

