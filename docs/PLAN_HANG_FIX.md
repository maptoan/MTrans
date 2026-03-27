# Kế hoạch xử lý lỗi chương trình kẹt sau "hết thời gian chờ Phân đoạn"

**Ngày:** 2026-03-14  
**Tình huống:** Sau log `Worker 7 hết thời gian chờ Phân đoạn 73. Sử dụng context tốt nhất có thể.`, chương trình đứng im ~3 giờ không có log thêm cho đến khi user Ctrl+C.

---

## 1. Rà soát luồng (sau khi timeout chờ segment)

1. **execution_manager.py** – `_context_aware_worker`:
   - Worker 7 đang xử lý một chunk (gọi là **chunk X**) thuộc segment có `context_lag_window`.
   - Chunk X phụ thuộc ngữ cảnh vào chunk **73** (`dep_id = 73`).
   - `await asyncio.wait_for(self._chunk_events[dep_id].wait(), timeout=600)` → sau **600 giây** ném `TimeoutError`.
   - Log cảnh báo, rồi chạy tiếp:
     - `if not self.progress_manager.is_chunk_completed(chunk_id): await translate_chunk(api_key)`.
   - **Không có timeout** bao ngoài `translate_chunk(api_key)`. Nếu bên trong treo thì worker treo vô hạn.

2. **translate_chunk (closure trong worker)**:
   - Gọi `translator_instance._translate_one_chunk_worker(...)`.
   - Có thể gọi `_wait_for_available_key(worker_id)` nếu key bị block (có `max_wait=3600` và log định kỳ mỗi ~60s).
   - Nếu treo ở đây, lẽ ra vẫn có log "Worker X waiting >...s. Pool Health: ..." mỗi phút. User không thấy log nào → khả năng cao **không** treo ở đây.

3. **_translate_one_chunk_worker_internal (translator.py)**:
   - Vòng `while attempt < max_retries` gọi `model_router.translate_chunk_async(...)`.
   - Không có `asyncio.wait_for` bao ngoài toàn bộ lần dịch. Nếu một lần gọi API treo thì cả worker treo.

4. **model_router / GenAIClient**:
   - `_generate_async` tính `timeout` (adaptive) nhưng **không truyền** vào `client.generate_content_async(...)`.
   - `genai_adapter.py`: comment ghi "Do NOT pass timeout in http_options" và `self.client = new_genai.Client(api_key=api_key)` — **không có tham số timeout**.
   - → Gọi API Gemini **không có giới hạn thời gian** từ phía ta; phụ thuộc hoàn toàn vào SDK. Nếu SDK không enforce (hoặc có đường dẫn treo), request có thể treo vô hạn.

**Kết luận nguyên nhân chính:**

- **Nguyên nhân trực tiếp:** Sau khi hết 600s chờ segment 73, worker gọi `await translate_chunk(api_key)`. Toàn bộ lần dịch **không có timeout** ở tầng execution. Nếu bên trong có bất kỳ thao tác nào treo (thực tế nhiều khả năng là **gọi API Gemini** không trả về), worker sẽ treo vô hạn.
- **Nguyên nhân phụ:** API client (GenAI) không áp timeout cho từng request; SDK có thể không cắt được một số trường hợp treo (ví dụ kết nối treo không phản hồi).

---

## 2. Kế hoạch xử lý

### 2.1. Timeout toàn bộ lần dịch một chunk (Execution Manager) — **BẮT BUỘC**

- **Mục tiêu:** Tránh treo vô hạn khi một chunk dịch không bao giờ hoàn thành.
- **Cách làm:**
  - Trong `execution_manager._context_aware_worker`, bọc **mọi** `await translate_chunk(api_key)` bằng `asyncio.wait_for(translate_chunk(api_key), timeout=T)`.
  - `T` lấy từ config: `performance.translation_task_timeout` (mặc định đề xuất: **900** giây = 15 phút).
  - Khi `TimeoutError`:
    - Log cảnh báo (worker_id, chunk_id, timeout T).
    - Đưa chunk vào `failed_chunks`.
    - Set `_chunk_events[chunk_id].set()`, `pbar.update(1)`, `queue.task_done()`.
    - `return False` (chunk sẽ được retry sau / trong đợt retry failed).
  - Áp dụng cho **cả hai nhánh**: có segment (sau khi chờ dependency) và không segment.

### 2.2. Giảm timeout chờ dependency (segment)

- **Mục tiêu:** Giảm thời gian “chết” trước khi bước dịch bắt đầu; nếu chunk dependency thực sự chậm, vẫn tiến hành dịch với context tốt nhất có thể (đã có sẵn logic).
  - Giữ nguyên hành vi: timeout xong vẫn gọi `translate_chunk(api_key)`.
- **Cách làm:**
  - Đọc timeout từ config: `performance.segment_wait_timeout` (mặc định đề xuất: **300** giây = 5 phút), thay cho hằng số 600 hiện tại.
  - Chỉ thay giá trị dùng trong `asyncio.wait_for(self._chunk_events[dep_id].wait(), timeout=...)`.

### 2.3. Cấu hình mẫu (config)

- Trong `config/config.yaml`, dưới `performance:` thêm (hoặc cập nhật):

```yaml
performance:
  # ... existing keys ...
  translation_task_timeout: 900   # Giây; timeout toàn bộ 1 lần dịch 1 chunk, tránh treo vô hạn
  segment_wait_timeout: 300      # Giây; timeout chờ chunk dependency trong segment
```

- Execution manager đọc:
  - `translation_task_timeout` từ `self.performance_config` (fallback 900).
  - `segment_wait_timeout` từ `self.performance_config` (fallback 300).

### 2.4. (Tùy chọn sau) Timeout tầng API

- Để tránh treo ở tầng HTTP/SDK: sau khi 2.1–2.3 ổn định, có thể cân nhắc:
  - Truyền timeout vào GenAI client hoặc vào từng lần gọi `generate_content_async` nếu SDK hỗ trợ (per-request timeout).
  - Hoặc bọc riêng lời gọi API trong `model_router` bằng `asyncio.wait_for(..., timeout=adaptive_timeout)` nếu không phá logic retry/fallback hiện tại.

---

## 3. Kiểm tra sau khi sửa

- Chạy lại job dịch (resume) và theo dõi:
  - Nếu có chunk bị timeout: log cảnh báo rõ worker_id, chunk_id, timeout; chunk vào failed và vẫn được retry sau.
  - Không còn hiện tượng đứng im hàng giờ không log (tối đa ~translation_task_timeout giây cho một chunk).
- (Tùy chọn) Giả lập treo: tạm thời mock/sleep dài trong translator để xác nhận sau 900s có TimeoutError và xử lý failed đúng.

---

## 4. Tóm tắt thay đổi file

| File | Thay đổi |
|------|----------|
| `config/config.yaml` | Thêm `translation_task_timeout`, `segment_wait_timeout` dưới `performance`. |
| `src/translation/execution_manager.py` | Đọc 2 config trên; bọc `translate_chunk(api_key)` bằng `asyncio.wait_for(..., timeout)`; xử lý TimeoutError (failed_chunks, event, pbar, task_done); dùng `segment_wait_timeout` cho `wait_for(_chunk_events[dep_id].wait(), ...)`. |

---

**Kết luận:** Nguyên nhân chính gây kẹt là **không có timeout** cho toàn bộ lần dịch một chunk ở execution manager, kết hợp với khả năng gọi API (Gemini) có thể treo. Sửa bằng timeout cấu hình được cho “một task dịch một chunk” và giảm timeout chờ segment; chunk timeout sẽ được coi là failed và retry sau, không treo chương trình.
