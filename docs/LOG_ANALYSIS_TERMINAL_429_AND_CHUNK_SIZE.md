# Phân tích log terminal: 429 RESOURCE_EXHAUSTED và chunk quá lớn

**Nguồn:** Log chạy `python main.py` (terminal 11, đoạn 742–918).  
**Tóm tắt:** Dịch 4 chunks (1 segment), Chunk-3 có **120.901 ký tự** trong một request, lặp lại **429 RESOURCE_EXHAUSTED** với **cùng một key** sau mỗi ~46s.

---

## 1. Các vấn đề chính

### 1.1 Chunk quá lớn (120.901 ký tự / ~30k token)

**Hiện tượng:**
- Log: `Very long chunk_text: 120901 chars in build_main_messages`
- Cấu hình: `max_chunk_tokens: 25000`, nhưng balancing báo: `range 21205-31029` → có chunk **vượt 25k token** (khoảng 31k token ≈ 120k+ ký tự).
- Gửi một request ~30k token (input + output) dễ chạm giới hạn context/throughput của API và dễ bị 429 hoặc timeout.

**Nguyên nhân logic:**
- Chunk balancing cho phép chunk vượt `max_chunk_tokens` (ví dụ lên 31k).
- Không có **cap theo ký tự** hoặc **cap chặt theo token** sau balancing; prompt_builder chỉ **cảnh báo** khi > 50k ký tự, không từ chối hoặc tách nhỏ.

**Hướng cải thiện:**
- **Cap chặt sau balancing:** Đảm bảo không chunk nào vượt `max_chunk_tokens` (hoặc thêm `max_chunk_chars` nếu cần).
- **Giới hạn kích thước request:** Trong prompt_builder hoặc trước khi gọi API: nếu `len(chunk_text)` vượt ngưỡng an toàn (ví dụ 60k–80k chars), **tự động tách sub-chunk** hoặc từ chối và báo lỗi rõ ràng.
- **Cấu hình:** Thêm `max_chunk_chars` (optional) trong config để dễ bảo trì.

---

### 1.2 429 và dùng lại cùng một key

**Hiện tượng:**
- Cùng key `AIzaSyA1Yj...` bị 429 → sau ~46s log "đã phục hồi từ quota" → thử lại → vẫn 429 → lặp lại nhiều lần.
- Lỗi API: "You exceeded your current quota, please check your plan and billing" → thường là **quota theo ngày**, không phải rate limit theo phút.

**Nguyên nhân logic:**
- **SmartKeyDistributor:** Key bị 429 được đưa vào error pool với cooldown (ví dụ 46s–60s). Hết cooldown → key được đưa lại `reserve_queue` → worker có thể **lấy lại đúng key đó** (worker–key affinity hoặc thứ tự queue).
- **APIKeyManager** (nếu dùng): `get_key_for_worker(worker_id)` luôn trả cùng key cho cùng worker → sau khi key hết cooldown, worker lại dùng key vừa hết quota.
- Với **quota theo ngày**, chờ 46s rồi thử lại cùng key là vô ích.

**Hướng cải thiện:**
- **Khi 429 (quota_exceeded):** Ưu tiên **đổi key** cho lần retry thay vì chờ cooldown rồi dùng lại key cũ:
  - Trong luồng gọi API (translator/execution_manager): sau khi `return_key(..., is_error=True)` với `quota_exceeded`, lấy key mới qua **get_available_key()** (hoặc tương đương) thay vì `get_key_for_worker(worker_id)`.
- **SmartKeyDistributor:** Khi key vừa 429 (quota), có thể:
  - Tăng cooldown cho `quota_exceeded` (ví dụ 1h hoặc 24h), **hoặc**
  - Khi worker yêu cầu key sau lỗi 429, **không trả lại key vừa lỗi** cho cùng worker (trả key khác từ pool).
- **Log:** Phân biệt rõ "rate limit (RPM)" vs "quota (daily)" và ghi log cooldown tương ứng.

---

### 1.3 Segment = 1 nhưng có 4 chunks

**Hiện tượng:**
- Log: "Tài liệu được chia thành **1 segments**" và "**4 chunks**", đang dịch **Chunk-3**.

**Giải thích:**
- `_split_into_segments` gộp các chunk liền nhau thành segment theo **ContextBreakDetector** (natural break). Không có break giữa 4 chunk → 1 segment chứa cả 4 chunk.
- Worker vẫn dịch **từng chunk một** (`_translate_one_chunk_worker`), không gửi cả 4 chunk trong một request. Vì vậy **1 segment** không có nghĩa là 1 request khổng lồ; vấn đề là **bản thân một chunk (Chunk-3) đã quá lớn**.

**Kết luận:** Logic segment/chunk đúng; cần cải thiện **kích thước từng chunk** (mục 1.1) chứ không cần thay đổi cách gộp segment.

---

### 1.4 Tiến độ "0/1"

**Hiện tượng:** Progress bar: `0%| 0/1 [00:00<?, ?it/s]`.

**Giải thích:** Log có "Phát hiện 3 chunks đã hoàn thành" và tổng 4 chunks → chỉ còn **1 chunk** chưa dịch (Chunk-3). `chunks_to_translate_count = len(chunks_to_translate)` = 1, nên total=1 là đúng. Không cần sửa logic progress bar.

---

## 2. Tóm tắt hành động đề xuất

| Ưu tiên | Vấn đề | Hành động |
|--------|--------|-----------|
| P0 | Chunk > max_chunk_tokens / quá lớn | Cap chặt sau balancing; thêm max_chunk_chars (optional); có thể sub-chunk hoặc báo lỗi khi vượt ngưỡng an toàn. |
| P0 | 429 quota nhưng vẫn dùng lại cùng key | Sau 429 (quota_exceeded): ưu tiên get_available_key() (key khác) thay vì chờ cooldown rồi dùng lại get_key_for_worker. Có thể tăng cooldown cho quota_exceeded (1h/24h). |
| P1 | Cảnh báo "Very long chunk_text" | Nâng ngưỡng cảnh báo hoặc chặn request khi vượt max_chunk_chars. |

---

## 3. File liên quan (để sửa)

- **Chunk size / balancing:** `src/preprocessing/chunker.py` (hoặc nơi gọi balancing), `config/config.yaml` (`max_chunk_tokens`, thêm `max_chunk_chars` nếu cần).
- **Cảnh báo / cap kích thước request:** `src/translation/prompt_builder.py` (`build_main_messages`).
- **429 và key:** `src/translation/translator.py` (luồng retry, lấy key sau return_key), `src/translation/execution_manager.py` (`_wait_for_available_key`, `translate_chunk`), `src/services/smart_key_distributor.py` (cooldown, đưa key về queue).
- **Progress bar:** `src/translation/execution_manager.py` (biến total cho tqdm).

---

## 4. Đã triển khai (theo bàn giao)

**Bổ sung (v9.1):** Hợp nhất trạng thái key và RPD-block:
- **APIKeyManager**: `rpd_blocked_until`, nhận diện lỗi "quota... plan and billing" → block tới ngày mai; `get_quota_status_summary`, `handle_exception`, `get_earliest_reset_time`.
- **SmartKeyDistributor**: dùng `_state: APIKeyManager` làm nguồn sự thật duy nhất; `_is_key_available`/`return_key`/recovery delegate tới `_state`; `key_statuses` property trả về `_state.key_statuses`. Xem CHANGELOG v9.1.

- **429 / xoay key:** Trong `execution_manager._wait_for_available_key` đã đổi thứ tự: **ưu tiên `get_available_key()`** (lấy key từ pool) trước, fallback mới dùng `get_key_for_worker(worker_id)`. Nhờ vậy khi retry sau 429 sẽ ưu tiên dùng key khác thay vì key vừa hết cooldown.
- **Cap chunk vượt ngưỡng:** Trong `chunker.py` sau bước balancing đã gọi **`_cap_oversized_chunks`**: mọi chunk có `tokens > max_effective_tokens` được tách bằng `_chunk_by_paragraph_logic` với `hard_limit=max_effective_tokens`, đảm bảo không chunk nào vượt ngưỡng (tránh 429/context overflow). Test `test_smart_chunker_hybrid` vẫn pass.

*Tài liệu này dùng để bàn giao và triển khai các cải thiện theo TDD (test trước, implement sau).*
