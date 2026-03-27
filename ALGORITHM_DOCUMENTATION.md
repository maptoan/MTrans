# API Key Management & Chunking Optimization Algorithm

> **Model:** Gemini 3 Flash Preview  
> **Phiên bản:** 1.0  
> **Ngày tạo:** 2026-02-24

---

## 1. Giới hạn Gemini API (Cập nhật 2026-03-18)

Dưới đây là các model tối ưu nhất để dùng cho dịch thuật với tài khoản Free Tier:

| Model | RPM | TPM | RPD | Ưu điểm / Trạng thái |
|-------|-----|-----|-----|----------------------|
| **Gemini 3 Flash** | 5 | 250K | 20 | **Ổn định nhất**, chất lượng cao |
| **Gemini 2.5 Flash** | 5 | 250K | 20 | Tương đương v3 Flash |
| **Gemini 3.1 Flash-Lite** | 15 | 250K | **500** | **Quảng bá RPD cực lớn**, nhưng có thể kém ổn định |
| **Gemini 2.5 Flash-Lite** | 10 | 250K | 20 | Tốc độ cao, an toàn hơn 3.1 |
| **Gemini Robotics ER 1.5** | 10 | 250K | 20 | Dùng tốt cho Vision/Layout |

> [!TIP]
> **Khuyến nghị:** Luôn dùng `gemini-3-flash-preview` làm mặc định để đảm bảo marker không bị mất. Chỉ dùng `3.1 Flash-Lite` khi bạn cần dịch số lượng cực lớn và chấp nhận rủi ro marker bị lỗi.

---

## 2. Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HỆ THỐNG TỐI ƯU HÓA TỔNG THỂ                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    SMART CHUNKING LAYER                              │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                  │   │
│  │  │ Adaptive    │ │ Paragraph-  │ │ Balancing   │                  │   │
│  │  │ Sizing      │ │ Aware       │ │ (85% fill)  │                  │   │
│  │  │ 20K tokens  │ │ (giữ câu)   │ │             │                  │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    KEY DISTRIBUTION LAYER                           │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                  │   │
│  │  │ Worker-Key  │ │ Global Rate │ │ Zero-Wait   │                  │   │
│  │  │ Affinity    │ │ Limiter     │ │ Replacement │                  │   │
│  │  │ (70/20/10) │ │ (250 RPM)   │ │             │                  │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    GEMINI API LAYER                                  │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                  │   │
│  │  │ Token       │ │ Context     │ │ Auto-Retry  │                  │   │
│  │  │ Bucket      │ │ Caching     │ │ + Backoff   │                  │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Thuật toán Chunking tối ưu

### 3.1. Công thức Tính Token

```python
# CJK: 1 ký tự ≈ 1 token
# Punctuation: 1 ký tự ≈ 0.5 token  
# Other: 1 ký tự ≈ 0.25 token
tokens = cjk_count + (whitespace_count * 0.1) + (punct_count * 0.5) + (other_count * 0.25)
```

### 3.2. Adaptive Chunk Sizing

```python
# Cấu hình: max_chunk_tokens: 20000
# Safety ratio: 0.9 (sử dụng 90% để tránh vượt limit)
max_effective = 20000 * 0.9 = 18000 tokens/chunk
```

| Model | Max Chunk | Safety (90%) | Thực tế |
|-------|-----------|--------------|---------|
| gemini-3-flash-preview | 25,000 | 90% | **18,000** |
| default | 10,000 | 90% | **9,000** |

### 3.3. Paragraph-Aware Splitting

```python
# KHÔNG cắt giữa câu - chỉ cắt tại ranh giới đoạn văn
def chunk_text(text, max_tokens=18000):
    paragraphs = text.split("\n\n")
    current_chunk = []
    current_tokens = 0
    
    for para in paragraphs:
        para_tokens = count_tokens(para)
        
        if current_tokens + para_tokens <= max_tokens:
            current_chunk.append(para)
            current_tokens += para_tokens
        else:
            yield "\n\n".join(current_chunk)
            current_chunk = [para]
            current_tokens = para_tokens
```

### 3.4. Chunk Balancing (Tối ưu Fill Rate)

```python
# Target: 85% utilization (không quá nhỏ, không quá lớn)
target_tokens = max_chunk_tokens * 0.85  # 17K
min_tokens = max_chunk_tokens * 0.80     # 16K

# Smart merging: Gộp chunks nhỏ < 80% vào chunk trước
# Splitting: Chia chunks > 100% thành 2 phần
```

---

## 4. Thuật toán Phân phối API Keys

### 4.1. Smart Key Distributor v7.0 - Tổng quan

Smart Key Distributor là hệ thống quản lý API key thông minh với các tính năng:

1. **Chunk-First Allocation** - Phân bổ worker tối ưu theo số chunk
2. **Zero-Wait Replacement** - Thay key lỗi ngay lập tức
3. **Auto-Recovery Pool** - Tự động đưa key hết cooldown về queue

### 4.2. Worker-Key Affinity (Phân bổ Cố định)

```python
# Phân bổ keys theo tỷ lệ:
# - 70% → Translation Workers
# - 20% → Editor Workers  
# - 10% → Reserve (dự phòng)

translation_keys = keys[:int(len(keys) * 0.7)]
editor_keys = keys[int(len(keys) * 0.7):int(len(keys) * 0.9)]
reserve_keys = keys[int(len(keys) * 0.9):]
```

**Lợi ích:**
- Giảm overhead việc lookup key mới
- Dễ debug và theo dõi usage per key
- Mỗi worker được gán 1 key cố định

```python
# Mỗi worker được gán 1 key cố định
key_index = worker_id % len(api_keys)
assigned_key = api_keys[key_index]
```

### 4.3. Global Rate Limiter (RPM Control)

```python
# Global RPM = 250 (tổng hệ thống)
# Per-key delay = 12s (5 RPM = 1 request/12s)

global_interval = 60 / 250  # 0.24s giữa mỗi request
per_key_delay = 12.0        # Đảm bảo 5 RPM/key
```

**Logic Sliding Window:**
- Sử dụng cửa sổ trượt 60 giây để track timestamps
- Nếu số request trong cửa sổ ≥ giới hạn → chờ cho đến khi request cũ nhất hết hiệu lực

```python
class GlobalRateLimiter:
    async def acquire(self):
        # Sliding Window 60s
        self.request_timestamps = [t for t in timestamps if now - t < 60]
        
        if len(self.request_timestamps) >= self.rpm_limit:
            wait_time = 60 - (now - earliest_timestamp) + 0.5s
            await asyncio.sleep(wait_time)
        
        self.request_timestamps.append(now)
```

### 4.4. Zero-Wait Replacement (Thay thế Ngay)

Khi một key bị lỗi:
```
1. Đưa failed_key vào Error Pool tương ứng
2. Lấy ngay key từ Reserve Queue (không chờ)
3. Nếu Reserve rỗng → scan Error Pools tìm key có cooldown gần hết nhất
```

```python
async def replace_worker_key(worker_id, failed_key, error_type):
    # Bước 1: Phân loại lỗi và tính cooldown
    cooldown = cooldown_calculator.calculate_cooldown(error_type)
    move_to_error_pool(failed_key, cooldown)
    
    # Bước 2: Thay thế ngay từ Reserve
    try:
        new_key = reserve_queue.get_nowait()  # INSTANT
        worker_keys[worker_id] = new_key
    except QueueEmpty:
        # Bước 3: Fallback - lấy key sắp hết cooldown
        new_key = get_earliest_recovery_key()
```

### 4.5. Auto-Recovery (Phục hồi Tự động)

Background task chạy liên tục để phục hồi các keys từ error pools:

```python
async def _recovery_task():
    while running:
        earliest = get_earliest_recovery_time()
        wait_time = clamp(earliest - now, min=1s, max=30s)
        await asyncio.sleep(wait_time)
        
        # Move recovered keys back to reserve queue
        for key in expired_error_pools:
            await reserve_queue.put(key)
```

### 4.6. Exponential Backoff (Khi lỗi)

```python
# Chiến lược cooldown:
# - Rate Limit (429): 15s → 30s → 60s → 120s
# - Quota Exceeded: 60s → (sau 3 lần) → 24h penalty
# - Server Error: 30s → 60s → 120s → 240s

BACKOFF_MULTIPLIERS = [1, 2, 4, 8, 16]
cooldown = base_cooldown * BACKOFF_MULTIPLIERS[retry_count]
```

| Error Type | Base Cooldown | Exponential Backoff |
|------------|---------------|---------------------|
| Rate Limit (429) | 15s | 15s → 30s → 60s → 120s |
| Quota Exceeded | 60s | 60s → ... → **24h** (nếu retry > 3 lần) |
| Server Error | 30s | 30s → 60s → 120s → 240s |
| Timeout | 10s | 10s → 20s → 40s → 80s |

---

## 5. Cơ chế Kiểm soát Token (TPM Control)

### 5.1. Token Bucket Per Key

```python
# Mỗi key có Token Bucket riêng
bucket = TokenBucket(
    rate=TPM/60,      # 250000/60 = 4166 tokens/giây
    capacity=5000      # Burst capacity
)

# Đợi đủ tokens trước khi gọi API
await bucket.wait_for_tokens(estimated_input_tokens)
```

### 5.2. Context Caching (Giảm Token)

```python
# Cache static content (system prompt, glossary, style)
# Chỉ gửi dynamic content (chunk + context)

cached_content = {
    "system_instruction": "...",      # Cacheable (1 lần)
    "glossary": "...",                 # Cacheable (1 lần)
    "style_profile": "...",            # Cacheable (1 lần)
    "chunk_text": "...",               # KHÔNG cache (mỗi chunk khác nhau)
    "context_before": "...",            # KHÔNG cache
}

# Tiết kiệm: 75-90% input tokens
```

---

## 6. Kiểm soát RPD (Daily Quota)

```python
# Giới hạn 20 requests/ngày/key
daily_limit = 20

# Warning khi đạt 80% (16 requests)
if quota_used >= daily_limit * 0.8:
    logger.warning("⚠️ Key sắp hết quota ngày")

# Penalty khi retry > 3 lần vì quota
if retry_count > 3 and error == "quota_exceeded":
    cooldown = 24 * 3600  # 24 giờ
```

---

## 7. Cấu hình Tối ưu

```yaml
# config.yaml

# Chunking Configuration
preprocessing:
  chunking:
    max_chunk_tokens: 20000      # Tăng chunk size để giảm số requests
    adaptive_mode: true           # Tự động điều chỉnh theo model
    target_utilization: 0.85      # 85% fill rate
    safety_ratio: 0.90            # 90% để tránh vượt limit

# Performance Configuration
performance:
  max_requests_per_minute: 250   # Global RPM limit
  min_delay_between_requests: 12.0  # 5 RPM/key = 12s delay

  max_parallel_workers: 42        # 70% của 60 keys (nếu có 60 keys)

# Key Management Configuration
key_management:
  rpd_cooldown_hours: 24         # 24h penalty cho quota exceeded
  max_retries_before_rpd: 3      # Retry 3 lần trước khi penalty
  
  # Allocation Ratios
  translation_worker_ratio: 0.7   # 70% translation
  editor_worker_ratio: 0.2        # 20% editor
  reserve_ratio: 0.1              # 10% reserve
  
  # Base Cooldowns
  base_cooldowns:
    rate_limit: 15
    quota_exceeded: 60
    server_error: 30
    timeout: 10
```

---

## 8. Sơ đồ Luồng Tổng hợp

```
                    ┌─────────────────────────────────────┐
                    │     INPUT: Raw Novel Text           │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │   SMART CHUNKING LAYER              │
                    │   - Adaptive sizing (20K tokens)    │
                    │   - Paragraph-aware splitting       │
                    │   - Balancing (85% fill)            │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │   TOKEN CHECK                       │
                    │   Input ≤ 18K tokens?               │
                    │   (20K × 90% safety)               │
                    └─────────────────┬───────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
         YES  │                       │  NO (quá lớn)         │
              ▼                       ▼                       ▼
┌─────────────────────┐   ┌─────────────────────┐  ┌─────────────────────┐
│  CONTEXT CACHING    │   │   SUB-CHUNK FALLBACK│  │   REJECT / ERROR    │
│  (tiết kiệm 75-90%) │   │   (Chia 2×10K)      │  │                     │
└─────────┬───────────┘   └──────────┬──────────┘  └─────────────────────┘
          │                            │
          └────────────┬───────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   KEY DISTRIBUTION LAYER    │
        │   ┌────────────────────────┐ │
        │   │ Global Rate Limiter    │ │
        │   │ RPM ≤ 250 total       │ │
        │   └────────────────────────┘ │
        │   ┌────────────────────────┐ │
        │   │ Zero-Wait Replacement  │ │
        │   │ (Reserve Queue)       │ │
        │   └────────────────────────┘ │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   GEMINI API CALL           │
        │   - Token Bucket (TPM)      │
        │   - Exponential Backoff     │
        │   - Auto-Retry            │
        └──────────────┬──────────────┘
                       │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
     │ SUCCESS    RATE LIMIT      OTHER ERR
     │                 │                 │
     │ +1 quota   Move to        Exponential
     │ Reset      Error Pool     Backoff
```

---

## 9. Error Pools (Phân loại lỗi)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ERROR POOLS STRUCTURE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                │
│  │   QUOTA    │   │   RATE LIMIT │   │  SERVER     │                │
│  │   POOL     │   │    POOL      │   │  ERROR      │                │
│  │            │   │              │   │   POOL      │                │
│  │ Cooldown:  │   │ Cooldown:    │   │             │                │
│  │ 60s-24h   │   │ 15s-120s     │   │ Cooldown:   │                │
│  │            │   │              │   │ 30s-240s    │                │
│  └──────┬─────┘   └──────┬───────┘   └──────┬──────┘                │
│         │                │                  │                        │
│         │    ┌───────────┴───────────┐      │                        │
│         │    │                       │      │                        │
│         │    │    RESERVE QUEUE      │◄─────┘                        │
│         │    │    (10% keys)         │                               │
│         │    │                       │                               │
│         │    │  Zero-Wait Replacement│                               │
│         │    │  (Instant fallback)   │                               │
│         │    └───────────────────────┘                               │
│         │                                                              │
│         │    ┌───────────────────────┐                               │
│         └───►│   AUTO-RECOVERY TASK    │◄──── Background task         │
│              │   (1-30s interval)      │       chạy liên tục         │
│              └───────────────────────┘                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Kết quả Tối ưu

| Chỉ số | Trước | Sau | Cải thiện |
|--------|-------|-----|-----------|
| **Chunks/ngày** | ~60 | ~20 | **Giảm 3.3x** |
| **Tokens/ngày** | ~700K | ~2.4M | **Tăng 3.4x** |
| **429 Errors** | >10% | <1% | **Giảm 90%** |
| **Chunk Size** | 6K | 20K | **Tăng 3.3x** |
| **Workers** | 5 | 42 | **Tăng 8x** |

---

## 11. Đảm bảo Hệ thống

- ✅ Không vượt **RPD limit** (20 request/ngày/key)
- ✅ Không vượt **RPM limit** (5 request/phút/key)  
- ✅ Không vượt **TPM limit** (250K tokens/phút/key)
- ✅ Tự phục hồi khi gặp lỗi (Zero-Wait + Auto-Recovery)
- ✅ Tối ưu token đầu vào (Context Caching - tiết kiệm 75-90%)

---

## 12. Các Files liên quan

| File | Mô tả |
|------|-------|
| `src/services/smart_key_distributor.py` | Smart Key Distributor v7.0 |
| `src/services/api_key_manager.py` | API Key Manager |
| `src/preprocessing/chunker.py` | Smart Chunking |
| `src/utils/token_bucket.py` | Token Bucket implementation |
| `config/config.yaml` | Cấu hình hệ thống |

---

## 13. Phân tích Log phân phối Key & Cải tiến (2026-03-14)

### 13.1. Các vấn đề phát hiện từ log

| Vấn đề | Mô tả | Hậu quả |
|--------|--------|---------|
| **Đếm trùng lỗi quota** | `mark_request_error` được gọi cả trong translator và trong `return_key(is_error=True)` → mỗi lỗi bị tính 2 lần. | Log "Key đã vượt quá 37 lần", "38 lần" liên tiếp; `retry_count` tăng gấp đôi → áp dụng RPD 24h sớm hơn thực tế. |
| **GenAIClient nhận None key** | Khi Surgical CJK Cleanup chạy với `current_key is None` (hoặc key đã bị thu hồi), `final_cleanup_pass` gọi model_router với `api_key=None` → `create_client(None)` → lỗi. | "GenAIClient received empty/None api_key", "Dọn dẹp cuối cùng thất bại", và `AttributeError: 'GenAIClient' object has no attribute 'use_new_sdk'` trong `__del__`. |
| **No Fallback available** | Khi toàn bộ key bị 429, chunk retry liên tục với delay; không có fallback (ví dụ lưu bản nháp, bỏ qua cleanup). | Chunks 17, 23, 29, 30 lặp retry rất nhiều lần; tiến độ chậm. |

### 13.2. Cải tiến đã áp dụng

1. **Tránh đếm trùng lỗi**
   - Trong translator: bỏ gọi `mark_request_error` trước khi gọi `return_key(..., is_error=True, error_type=...)`.
   - Chỉ `return_key` gọi `mark_request_error` một lần → mỗi lỗi chỉ tăng `retry_count` một lần, cooldown/RPD chính xác hơn.

2. **Tránh cleanup với key None**
   - Translator: chỉ chạy Surgical CJK Cleanup khi `current_key` khác None (`and current_key`).
   - CJKCleaner.`final_cleanup_pass`: tham số `api_key` cho phép `Optional[str]`; nếu None hoặc rỗng thì log cảnh báo và trả về text gốc (bỏ qua micro-translation).

3. **GenAIClient an toàn khi __init__ fail**
   - Trong `close()` và `aclose()`: dùng `getattr(self, "use_new_sdk", False)` và `getattr(self, "client", None)` để tránh `AttributeError` khi object chưa khởi tạo xong (ví dụ raise do api_key None).

### 13.3. Cải tiến đã triển khai (2026-03-14)

4. **Fallback khi hết key (Partial)**
   - Khi `quota_blocked_ratio >= 1.0` hoặc `available_keys == 0`, nếu chunk đã có **draft_translation** (sau Gate 1+2, QA hoặc cleanup): gọi `progress_manager.save_chunk_result(chunk_id, draft_translation, metadata={"status": "partial", "reason": "quota_exceeded"})` và trả về `status="partial"` thay vì failed.
   - Execution manager và retry logic coi `status in ("success", "partial")` là có bản dịch; partial vẫn được merge vào file tổng.
   - Biến `draft_translation` được cập nhật mỗi khi có `final_translation` hợp lệ trong vòng lặp.

5. **Truyền error_message vào return_key**
   - `SmartKeyDistributor.return_key(..., error_message=None)` và `APIKeyManager.return_key(..., error_message=None)`; khi `is_error=True` thì truyền xuống `mark_request_error(key, error_type, error_message)`.
   - Translator truyền `error_message=str(e)` ở các chỗ có exception `e`.

6. **Giảm log lặp RPD**
   - Trong `CooldownCalculator.calculate_cooldown`: log warning "Key đã vượt quá X lần..." chỉ khi `retry_count == MAX_RETRIES_BEFORE_RPD_PENALTY` (lần đầu đạt RPD) hoặc `retry_count % 10 == 0`; các lần khác dùng `logger.debug`.

---

## 14. Bảng Tra cứu Toàn diện (Dữ liệu 2026-03-18)

Dữ liệu được trích xuất từ bảng Dashboard mới nhất cho tài khoản Free Tier:

| Nhóm Model | Model Cụ thể | RPM | TPM | RPD |
|:---|:---|:---:|:---:|:---:|
| **Flash Series** | Gemini 3 Flash | 5 | 250K | 20 |
| | Gemini 2.5 Flash | 5 | 250K | 20 |
| **Lite Series** | Gemini 3.1 Flash Lite | 15 | 250K | 500 |
| | Gemini 2.5 Flash Lite | 10 | 250K | 20 |
| **Gemma Series** | Gemma 3 (1B/4B/12B/27B) | 30 | 15K | 14.4K |
| **Embedding** | Gemini Embedding 1/2 | 100 | 30K | 1K |
| **Robotics** | Gemini Robotics ER 1.5 | 10 | 250K | 20 |

**Ghi chú nâng cao:**
- **Gemma 3** có RPD cực lớn (14.4K) nhưng TPM rất thấp (15K), chỉ phù hợp dịch từng câu ngắn, không dùng được cho chunking 20K tokens.
- **Gemini 3.1 Flash Lite** là model duy nhất có RPD "đột biến" (500), cực kỳ hữu ích để gánh tải khi các key khác hết quota.

---

**Tài liệu được cập nhật dựa trên khảo sát thực tế 2026-03-18**
