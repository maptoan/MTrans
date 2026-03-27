# Kế hoạch chi tiết: Cải tiến quản lý Key & Fallback

**Phiên bản:** 1.0  
**Ngày:** 2026-03-14  
**Trạng thái:** Kế hoạch – chưa thực thi

---

## 1. Tổng quan

Ba đề xuất cải tiến cần thực thi theo thứ tự ưu tiên, có kiểm thử và không phá vỡ hành vi hiện tại.

| # | Đề xuất | Ưu tiên | Độ phức tạp | Rủi ro |
|---|---------|---------|--------------|--------|
| 1 | Fallback khi hết key (lưu bản nháp → partial) | Cao | Trung bình | Trung bình |
| 2 | Truyền `error_message` vào `return_key` | Thấp | Thấp | Thấp |
| 3 | Giảm log lặp "Key đã vượt quá X lần..." | Thấp | Thấp | Rất thấp |

---

## 2. Đề xuất 1: Fallback khi hết key (Partial)

### 2.1. Mục tiêu

- Khi **100% key bị quota** và chunk **đã có bản dịch nháp** (draft): không retry vô hạn, **lưu bản nháp** và trả về **partial** thay vì failed.
- Merge và báo cáo vẫn dùng được bản partial; sau này có thể chạy job “resume partial” (chỉ cleanup/QA) nếu cần.

### 2.2. Điều kiện kích hoạt

- Trong `translator`: trong khối `except ResourceExhausted`, sau khi gọi `return_key`, kiểm tra `quota_blocked_ratio >= 1.0 or available_keys == 0`.
- **Và** tại thời điểm đó có **draft translation** (bản dịch đã có trong lần attempt hiện tại trước khi gặp 429).

### 2.3. Biến “draft” trong vòng lặp

- **Khái niệm:** `draft_translation` = bản dịch tốt nhất đã có được trong vòng lặp retry (dù chưa qua hết cleanup/QA).
- **Vị trí trong code:** `_translate_one_chunk_worker_internal`, vòng `while attempt < max_retries`.
- **Cách triển khai:**
  - Đầu vòng lặp (trước `try`): `draft_translation: Optional[str] = None`.
  - Mỗi khi có `final_translation` hợp lệ (sau Gate 1, sau Gate 2, sau QA, sau cleanup): gán `draft_translation = final_translation`.
  - Trong `except ResourceExhausted`, trước khi `return { status: "failed", ... }` khi `quota_blocked_ratio >= 1.0`:
    - Nếu `draft_translation` không rỗng:
      - Gọi `self.progress_manager.save_chunk_result(chunk_id, draft_translation, metadata={"status": "partial", "reason": "quota_exceeded"})`.
      - Trả về `{ "chunk_id": chunk_id, "status": "partial", "translation": draft_translation, "error": "..." }`.
    - Nếu không có draft: giữ hành vi cũ (return failed, không lưu).

### 2.4. Nơi cần sửa (đề xuất 1)

| File | Thay đổi |
|------|----------|
| `src/translation/translator.py` | (1) Thêm `draft_translation = None` đầu vòng lặp. (2) Gán `draft_translation = final_translation` tại các điểm đã có `final_translation` hợp lệ (sau validate, sau QA, sau cleanup). (3) Trong nhánh “100% quota → return failed”: nếu `draft_translation` có giá trị thì lưu qua `save_chunk_result` với metadata `status=partial`, rồi return `status="partial"` và `translation=draft_translation`. |
| `src/translation/execution_manager.py` | Nơi kiểm tra `result.get("status") == "success"`: mở rộng thành `result.get("status") in ("success", "partial")` để partial được coi là “có bản dịch”, vẫn ghi progress (đã ghi ở translator) và đưa vào merge. Có thể tách đếm: `success_count` vs `partial_count` nếu cần báo cáo. |
| `src/translation/translator.py` (chỗ gom kết quả) | Bất kỳ chỗ nào đếm success/failed (ví dụ `success_count`, `failed_count`): thêm đếm `partial_count` và log/tổng kết riêng (ví dụ: "X success, Y partial, Z failed"). |
| (Tùy chọn) `src/managers/progress_state_manager.py` | Nếu muốn truy vấn “chunk nào là partial” sau này: có thể lưu `metadata` per chunk (ví dụ `completed_meta[chunk_id] = {"status": "partial", "reason": "quota_exceeded"}`). Không bắt buộc cho phase 1. |

### 2.5. Merge và finalize

- **Merge:** `_merge_all_chunks` (và mọi nơi load bản dịch từ progress) đã dựa trên `progress_manager` / `get_chunk_translation`. Partial được lưu bằng `save_chunk_result` nên sẽ nằm trong `completed_chunks` và vẫn được merge như bình thường.
- **Báo cáo:** Trong bước finalize/report, nếu có lưu `partial_count`: hiển thị dòng kiểu “Hoàn thành: X, Partial (chưa cleanup): Y, Thất bại: Z”.

### 2.6. Tiêu chí hoàn thành (đề xuất 1)

- [ ] Khi 100% key quota và chunk đã có draft: chunk được lưu vào progress với metadata `status=partial`, và hàm worker trả về `status="partial"` với `translation=draft`.
- [ ] Merge vẫn chạy và đưa nội dung partial vào file tổng.
- [ ] Báo cáo cuối (log hoặc UI) phân biệt được success / partial / failed (ít nhất qua log).
- [ ] Test: mock 100% quota sau khi đã có `final_translation` → kỳ vọng 1 chunk partial được lưu và merge.

### 2.7. Rủi ro và giảm thiểu

- **Partial bị coi là success và không bao giờ cleanup lại:** Giảm thiểu bằng cách ghi rõ trong metadata (`reason`, `status=partial`) và (sau này) có thể thêm job “resume partial” chỉ chạy cleanup/QA cho các chunk có metadata partial.
- **Nhầm lẫn draft giữa các attempt:** Chỉ gán `draft_translation` khi `final_translation` thực sự tồn tại và đã qua validate; không gán khi exception xảy ra trước khi có bản dịch.

---

## 3. Đề xuất 2: Truyền `error_message` vào `return_key`

### 3.1. Mục tiêu

- Cho phép distributor ghi log chi tiết hơn (ví dụ nội dung lỗi API) khi đánh dấu lỗi key, mà không thay đổi hành vi hiện tại.

### 3.2. Thay đổi API

- **SmartKeyDistributor.return_key:** Thêm tham số tùy chọn `error_message: Optional[str] = None`. Khi `is_error=True`, gọi `mark_request_error(key, error_type or "unknown", error_message or "")`.
- **mark_request_error** đã có tham số `error_message`; chỉ cần truyền từ `return_key` xuống.

### 3.3. Nơi gọi `return_key(..., is_error=True)`

- `src/translation/translator.py`: Tất cả chỗ gọi `return_key(..., is_error=True, error_type=...)` có thể thêm `error_message=str(e)` (hoặc message ngắn) nếu có biến exception `e` trong scope.
- Không bắt buộc mọi nơi đều truyền; mặc định `None` để tương thích ngược.

### 3.4. Tiêu chí hoàn thành (đề xuất 2)

- [ ] Signature `return_key(..., error_message=None)` được thêm và được gọi từ translator ở ít nhất 2 chỗ có sẵn `str(e)`.
- [ ] Test hiện tại (initialization, key distributor) vẫn pass.

### 3.5. Rủi ro

- Rất thấp: chỉ mở rộng API tùy chọn.

---

## 4. Đề xuất 3: Giảm log lặp "Key đã vượt quá X lần..."

### 4.1. Mục tiêu

- Giảm spam log khi một key bị quota nhiều lần liên tiếp; vẫn log khi cần (lần đầu đạt RPD, hoặc theo bước).

### 4.2. Vị trí log

- `src/services/smart_key_distributor.py`, lớp `CooldownCalculator`, method `calculate_cooldown`: dòng gọi `logger.warning(f"Key đã vượt quá {retry_count} lần thử lại vì lỗi quota, áp dụng thời gian chờ RPD 24h")`.

### 4.3. Quy tắc log mới (đề xuất)

- Chỉ log khi **một trong hai**:
  - `retry_count == MAX_RETRIES_BEFORE_RPD_PENALTY` (lần đầu đạt ngưỡng RPD), **hoặc**
  - `retry_count % 10 == 0` (mỗi 10 lần: 10, 20, 30, ...).
- Các lần khác: bỏ log (hoặc chuyển xuống `logger.debug` nếu muốn giữ trace).

### 4.4. Tiêu chí hoàn thành (đề xuất 3)

- [ ] Log chỉ xuất hiện ở các bước đã chọn (ví dụ lần 3 và mỗi 10 lần).
- [ ] Không ảnh hưởng tới logic cooldown (vẫn trả về `RPD_COOLDOWN_SECONDS` như cũ).

### 4.5. Rủi ro

- Rất thấp: chỉ thay đổi mức độ log.

---

## 5. Thứ tự thực thi đề xuất

1. **Đề xuất 3** (giảm log) – nhanh, ít đụng chạm.
2. **Đề xuất 2** (error_message trong return_key) – API nhỏ, dễ review.
3. **Đề xuất 1** (fallback partial) – cần test kỹ (unit + tích hợp).

Sau mỗi đề xuất: chạy test hiện có, kiểm tra lint, rồi mới sang đề xuất tiếp theo.

---

## 6. Kiểm thử

### 6.1. Đề xuất 1 (Partial)

- **Unit (translator):** Mock `key_manager.get_quota_status_summary()` trả về `quota_blocked_ratio=1.0`, `available_keys=0`. Mock translation thành công một lần để có `final_translation`, sau đó lần gọi sau trả 429. Kỳ vọng: một lần return với `status="partial"` và progress đã lưu chunk với metadata partial.
- **Tích hợp (nếu có):** Chạy pipeline với 1 key, giới hạn quota rất thấp để tạo 100% quota sau vài chunk; kiểm tra có chunk partial được lưu và xuất hiện trong file merge.

### 6.2. Đề xuất 2 và 3

- Chạy bộ test hiện có (initialization, key distributor, translator cơ bản); không có test mới bắt buộc nếu không thay đổi hành vi.

---

## 7. Tài liệu cập nhật sau khi làm

- **ALGORITHM_DOCUMENTATION.md:** Cập nhật mục 13 (hoặc thêm mục mới) để ghi lại: (1) Fallback partial (điều kiện, flow, metadata), (2) Tham số `error_message` trong `return_key`, (3) Quy tắc log RPD.
- **CHANGELOG.md:** Ghi ngắn từng đề xuất đã triển khai (version/date).

---

## 8. Tóm tắt file cần sửa

| File | Đề xuất 1 | Đề xuất 2 | Đề xuất 3 |
|------|-----------|-----------|-----------|
| `src/translation/translator.py` | ✓ draft + partial return + save | ✓ truyền error_message (nếu có e) | – |
| `src/translation/execution_manager.py` | ✓ coi partial như “có bản dịch” | – | – |
| `src/services/smart_key_distributor.py` | – | ✓ return_key(error_message=...) | ✓ điều kiện log trong calculate_cooldown |
| `src/managers/progress_state_manager.py` | (tùy chọn) metadata partial | – | – |
| Tests | ✓ test partial (translator hoặc execution) | – | – |
| Docs | ✓ ALGORITHM + CHANGELOG | ✓ ALGORITHM | ✓ ALGORITHM |

---

**Kế hoạch này có thể dùng làm checklist khi triển khai từng đề xuất. Khi sẵn sàng thực thi, nên bắt đầu từ Đề xuất 3 → 2 → 1.**
