
# Account Deduplication Guide

> **Mục đích:** Hướng dẫn sử dụng tính năng **Account Deduplication** để tự động lọc và loại bỏ các API key trùng lặp thuộc cùng một tài khoản Google Cloud, giúp tối ưu hóa việc quản lý tài nguyên và tránh lỗi Quota Exceeded cục bộ.

---

## 🧐 Tại sao cần deduplicate?

Khi bạn tạo nhiều project trên cùng một tài khoản Google Cloud để lấy nhiều API key, các key này thực chất chia sẻ chung một hạn mức (quota) của tài khoản đó. Việc sử dụng song song các key này không làm tăng tổng throughput của bạn, mà ngược lại còn khiến bạn chạm ngưỡng giới hạn nhanh hơn và khó quản lý lỗi.

**Vấn đề:**
- 3 key từ cùng 1 tài khoản = 1 lần quota (không phải 3).
- Khi 1 key bị `429 Resource Exhausted`, các key kia cũng chết theo.
- Hệ thống switch key liên tục nhưng vẫn gặp lỗi, gây lãng phí tài nguyên CPU và network.

**Giải pháp:**
- Sử dụng **Account Deduplicator** để nhận diện các key "anh em".
- Chỉ giữ lại **1 key duy nhất** cho mỗi tài khoản vật lý.
- Đảm bảo mỗi key trong hồ chứa (pool) đều có quota độc lập.

---

## 🛠️ Cách hoạt động

Công cụ sử dụng thuật toán thông minh để phát hiện các nhóm key:

1.  **Account Type Detection:** Phân tích phản hồi từ API để xác định loại tài khoản (Free/Paid/Enterprise).
2.  **Quota Sharing Check:** Nếu một key hết quota, công cụ kiểm tra xem các key khác có bị ảnh hưởng ngay lập tức không.
3.  **Response Pattern Analysis:** Phân tích độ trễ (latency) và mẫu lỗi (error pattern) để nhóm các key có hành vi giống hệt nhau.

Sau khi phân nhóm, công cụ sẽ chọn ra **1 key đại diện** (thường là key đầu tiên hoặc key có độ trễ thấp nhất) và loại bỏ các key còn lại khỏi danh sách active.

---

## 📖 Hướng dẫn sử dụng

Tính năng này được tích hợp sẵn trong `src/utils/account_deduplicator.py` và có thể được sử dụng thông qua code hoặc script hỗ trợ.

### 1. Sử dụng trong code

```python
from src.utils.account_deduplicator import deduplicate_account_keys
from config.loader import load_config

# Load config
config = load_config()
all_keys = config['api_keys']

# Chạy deduplication
unique_keys, info = deduplicate_account_keys(
    api_keys=all_keys,
    config=config,
    strategy="first",       # Chọn key đầu tiên trong nhóm
    conservative=True       # Chế độ an toàn (giảm thiểu nhận diện nhầm)
)

print(f"Original: {len(all_keys)} -> Unique: {len(unique_keys)}")
```

### 2. Các Strategy lựa chọn key

-   `first`: Chọn key đầu tiên tìm thấy trong nhóm (Mặc định, nhanh nhất).
-   `fastest`: Test thử và chọn key có tốc độ phản hồi nhanh nhất.
-   `most_reliable`: Chọn key có tỉ lệ lỗi thấp nhất trong quá trình test.

---

## ⚠️ Lưu ý quan trọng

1.  **Conservative Mode:** Mặc định `conservative=True`. Chế độ này yêu cầu nhiều bằng chứng (indicators) trùng khớp mới kết luận 2 key là cùng tài khoản. Điều này giúp tránh việc loại nhầm các key độc lập.
2.  **Không xóa key:** Công cụ chỉ *loại bỏ khỏi danh sách active* trong phiên chạy hiện tại. Nó **KHÔNG** xóa key khỏi file `config.yaml` của bạn.
3.  **Hiệu năng:** Quá trình check có thể mất vài giây đến vài chục giây tùy số lượng key, do cần gửi request test đến API.

---

## 📊 Kết quả mong đợi

Sau khi deduplicate, bạn sẽ thấy:
- Số lượng key giảm đi (nếu bạn có nhiều key cùng acc).
- Ít lỗi `429` dây chuyền hơn.
- Hiệu suất hệ thống ổn định hơn do load balancer hoạt động chính xác trên các nguồn tài nguyên thực sự độc lập.
