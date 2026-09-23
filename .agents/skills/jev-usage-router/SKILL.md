---
name: jev-usage-router
description: Router using JEV ultrafast System-1 decisions before initiating browser automation, research, retries, or invoking subagents (calling extra bots). Enforces shadow mode logging, kill switch bypass, active route execution, and human-in-the-loop safety for irreversible actions.
---

# JEV Usage Router

Skill điều phối và định tuyến trước khi thực hiện các tác vụ nặng: **browser**, **research**, **retry**, và **gọi subagent (bot thêm)** trong DeepSeek Harness bằng cách tích hợp **JEV** ([browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast)).

```text
                           [Yêu cầu tác vụ từ Agent]
                                       │
                ┌──────────────────────┴──────────────────────┐
                │                                             │
      [Kiểm tra Kill Switch]                     [Chạy Router JEV]
   (bypass: true / enabled: false)         python3 route.py --intent ...
                │                                             │
      Bỏ qua Router (Default)                   Phân tích & Đánh giá route
                                                              │
                                            ┌─────────────────┴─────────────────┐
                                            │                                   │
                                      [Shadow Mode]                       [Active Mode]
                                            │                                   │
                                    Ghi log giám sát               DeepSeek Harness nghe route
                                   (.jev/logs/router.jsonl)         JEV ra quyết định hành động
                                            │                                   │
                                   Harness chạy baseline                        │
                                   Đọc log & thẩm định                          ▼
                                                             [Hành động Irreversible?]
                                                                    │         │
                                                                   Có         Không
                                                                    │         │
                                                                    ▼         ▼
                                                             DỪNG LẠI HỎI    DeepSeek
                                                             NGƯỜI DÙNG      Harness
                                                             (Giữ nút)       thực thi
```

---

## 1. Quick Setup JEV

Để cài đặt nhanh `jev-ultrafast`:

```bash
# Chạy script setup tự động
bash .agents/skills/jev-usage-router/scripts/setup_jev.sh
```

Hoặc thực hiện thủ công:
```bash
git clone https://github.com/browser-use/jev-ultrafast.git external/jev-ultrafast
cd external/jev-ultrafast
uv sync
cp .env.example .env
# Thêm TYPESAFE_API_KEY và TEXT_MODEL_API_KEY vào .env
uv run browser-harness --doctor
```

---

## 2. Quy Tắc Bắt Buộc: Hỏi Router Trước Khi Hành Động

Bất cứ khi nào chuẩn bị thực hiện một trong bốn hành vi sau, Agent **BẮT BUỘC** phải gọi Router trước:

1. **Browser**: Chuẩn bị tương tác web, mở trình duyệt, điều hướng form, click/type/scroll trên web.
2. **Research**: Chuẩn bị tìm kiếm web sâu, tra cứu tài liệu diện rộng, khảo sát nhiều nguồn.
3. **Retry**: Chuẩn bị lặp lại một lệnh hoặc tác vụ vừa thất bại, thử lại vòng lặp.
4. **Gọi bot thêm (Subagent)**: Chuẩn bị gọi `invoke_subagent` để chia nhánh công việc.

### Lệnh hỏi Router:

```bash
python3 .agents/skills/jev-usage-router/scripts/route.py \
  --intent <browser | research | retry | subagent> \
  --context "<Mô tả ngắn gọn mục tiêu, URL, truy vấn hoặc lỗi gặp phải>"
```

Đầu ra trả về cấu trúc JSON chuẩn:
```json
{
  "bypassed": false,
  "mode": "shadow",
  "route": "browser_fast_jev",
  "recommended_tool": "jev_ultrafast_agent",
  "action": "Engage JEV ultrafast System-1 loop",
  "confidence": 0.92,
  "is_irreversible": false,
  "require_human_confirmation": false,
  "execution_instruction": "SHADOW_OBSERVATION_ONLY_PROCEED_WITH_HARNESS_BASELINE"
}
```

---

## 3. Giai Đoạn 1: Chạy Shadow, Đọc Logs, Thẩm Định Trước Khi Bật Active

Hệ thống được khởi tạo ở chế độ **`shadow`** theo mặc định:
- Router tiếp nhận ý định, phân tích hành vi tối ưu, đo đạc độ trễ sub-50ms và ghi bản ghi vào file log:
  `.jev/logs/router.jsonl`
- Trong chế độ shadow, DeepSeek Harness tiếp tục vận hành luồng mặc định, cho phép theo dõi song song các quyết định mà JEV đề xuất so với thực tế.

### Đọc logs và đánh giá độ tin cậy:

```bash
# Xem báo cáo thống kê & mức độ tin cậy (Readiness)
python3 .agents/skills/jev-usage-router/scripts/inspect_logs.py

# Xem chi tiết N sự kiện router gần nhất
python3 .agents/skills/jev-usage-router/scripts/inspect_logs.py --tail 20
```

Khi độ tin cậy đạt mức cao và các quyết định phân luồng chính xác, bạn có thể tự tin chuyển sang chế độ `active`.

---

## 4. Kill Switch (Tắt hoặc Bypass Ngay Lập Tức)

Khi cần bỏ qua JEV ngay lập tức mà không làm gián đoạn luồng làm việc của Harness:

1. **Bật bypass qua CLI script**:
   ```bash
   python3 .agents/skills/jev-usage-router/scripts/flip_mode.py bypass on
   ```
2. **Hoặc truyền biến môi trường**:
   ```bash
   export JEV_BYPASS=true
   ```
3. **Hoặc sửa cấu hình trong `.jev/config.json`**:
   ```json
   {
     "enabled": false
   }
   ```
4. **Hoặc truyền cờ `--bypass` trực tiếp**:
   ```bash
   python3 .agents/skills/jev-usage-router/scripts/route.py --bypass --intent browser --context "..."
   ```

Khi kill switch kích hoạt, Router lập tức trả về `bypassed: true` và Harness tiếp tục chạy bình thường với zero overhead. Để tắt bypass:
```bash
python3 .agents/skills/jev-usage-router/scripts/flip_mode.py bypass off
```

---

## 5. Giai Đoạn 2: Flip Active (DeepSeek Harness Nghe Route · JEV Quyết · DeepSeek Harness Execute)

Khi đã kiểm tra log và tin cậy vào router, chuyển sang chế độ `active`:

```bash
python3 .agents/skills/jev-usage-router/scripts/flip_mode.py active
```

Ở chế độ `active`:
- **DeepSeek Harness lắng nghe route**: Gửi câu hỏi vào router trước mỗi tác vụ.
- **JEV quyết định**: Phân tích ngữ cảnh, lựa chọn công cụ nhanh nhất và tiết kiệm nhất (`targeted_read` vs `browser_fast_jev`, `search_direct` vs `subagent_delegate`, `in_turn_retry` vs `reground_state`).
- **DeepSeek Harness thực thi**: Gọi đúng công cụ và hành động được chỉ định.

### BẢO VỆ TUYỆT ĐỐI CHO VIỆC IRREVERSIBLE ("NGƯỜI VẪN GIỮ NÚT")

> [!CAUTION]
> **Quy tắc an toàn bất biến:**
> Nếu hành động mang tính chất không thể hoàn tác (`is_irreversible: true` / `require_human_confirmation: true`), ví dụ:
> - Thao tác git mang tính phá hủy (`git push --force`, `git reset --hard`)
> - Xóa file diện rộng hoặc dữ liệu (`rm -rf`, `drop table`, `delete from`)
> - Giao dịch tài chính, thanh toán, đặt vé chuyến bay (`payment`, `checkout`, `book flight`)
> - Xuất bản hoặc triển khai production (`publish`, `deploy production`)
>
> ➔ **DeepSeek Harness KHÔNG ĐƯỢC TỰ Ý THỰC THI**. Agent bắt buộc phải dừng lại và yêu cầu người dùng xác nhận (`ask_question` hoặc chờ phản hồi trực tiếp từ người dùng). **Người dùng luôn giữ nút.**

---

## 6. Bảng Tra Cứu Tuyến Điển Hình (Routing Table)

| Ý định | Ngữ cảnh | Route khuyến nghị | Hành động thực hiện |
| :--- | :--- | :--- | :--- |
| **browser** | Trang tĩnh, đọc bài báo, trích xuất text | `targeted_read` | Dùng `read_url_content` (nhanh, không mở browser) |
| **browser** | Form vé máy bay, login, click interactive | `browser_fast_jev` | Dùng JEV ultrafast System-1 loop (sub-100ms) |
| **browser** | Debugging sâu, network inspection | `browser_harness_playwright` | Dùng Playwright / Chrome DevTools |
| **research** | Tra cứu từ khóa đơn, error code, factoid | `search_direct` | Dùng `search_web` trực tiếp trong turn |
| **research** | Khảo sát sâu, đọc đa tài liệu, nhiều nhánh | `subagent_delegate` | Ủy quyền cho `research` subagent |
| **retry** | Lỗi mạng tạm thời, 503, timeout ngắn | `in_turn_retry` | Thử lại ngay với backoff 200-500ms |
| **retry** | DOM stale, element detached, snapshot cũ | `reground_state` | Tái lập snapshot mới trước khi thử lại |
| **retry** | Lỗi cú pháp, sai logic lặp lại | `abort_or_escalate` | Dừng thử lại vô ích, báo cáo vấn đề |
| **subagent** | Việc nhỏ, chỉnh sửa đơn, đọc 1 file | `reject_subagent_run_in_main`| Chạy trực tiếp trong turn chính |
| **subagent** | Tác vụ dài, độc lập, cần nhiều bước | `approve_subagent` | Cho phép gọi `invoke_subagent` |
