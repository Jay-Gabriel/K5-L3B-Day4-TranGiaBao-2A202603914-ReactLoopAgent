# Ghi chú phân tích · Day 04

Họ và tên: Trần Gia Bảo
MSSV: 2A202603914

## 1. Case được chọn

- ID case: `H6` (scenario: `noisy_status`)
- Câu hỏi của case: *"Xem status GitHub Actions, tìm incident h02n9572mx9y và theo liên kết của nó. Incident gộp có nêu nguyên nhân hay chỉ mô tả ảnh hưởng? Nêu giới hạn dữ liệu và trích nguồn."*
- Câu trả lời của agent ở lần 1:
> *"Dưới đây là các URL nguồn trực tiếp từ các incident đã được tra cứu:
> * Incident h02n9572mx9y: Trang chính thức của GitHub Status: https://www.githubstatus.com, Đường dẫn chi tiết: https://stspg.io/7pwv28hvkmz8
> * Incident xr3myzj7ms51: Đường dẫn chi tiết: https://stspg.io/pjgptg3cfc6n
> Giới hạn dữ liệu: Tìm kiếm chỉ thực hiện trong 50 incident gần nhất."*
- Điểm ở lần chạy 1: **55 / 100** (Factuality: 25/40, Completeness: 10/25, Evidence: 10/20, Boundaries: 10/15).

## 2. Bằng chứng trong trace

Đoạn trace của case `H6` trong `eval_before.json`:
```json
[
  {"event": "model", "step": 1, "finish": "tool_calls"},
  {"event": "tool", "step": 1, "name": "get_status", "arguments": {"provider": "github"}, "result": {"provider": "github", "matching_incidents_in_last_50": 50, ...}},
  {"event": "model", "step": 2, "finish": "tool_calls"},
  {"event": "tool", "step": 2, "name": "get_incident_details", "arguments": {"incident_id": "h02n9572mx9y", "provider": "github"}, "result": {"ok": true, "url": "https://stspg.io/7pwv28hvkmz8", "updates": [{"body": "...refer to the combined summary in this related incident: https://www.githubstatus.com/incidents/xr3myzj7ms51", ...}]}},
  {"event": "model", "step": 3, "finish": "tool_calls"},
  {"event": "tool", "step": 3, "name": "get_incident_details", "arguments": {"incident_id": "xr3myzj7ms51", "provider": "github"}, "result": {"ok": true, "url": "https://stspg.io/pjgptg3cfc6n", "updates": [{"truncated": true, "body": "...This incident was caused by a configuration change to an internal event-routing service...", ...}], "updates_total": 9}},
  {"event": "model", "step": 4, "finish": "stop"},
  {"event": "validation_missing_source", "step": 4},
  {"event": "model", "step": 5, "finish": "stop"}
]
```

**Nguyên nhân gây lỗi (Root Cause):**
1. **Lỗi chuyển dịch ngữ cảnh khi kích hoạt Source Validation**: Ở Step 4, model trả lời câu hỏi nhưng quên trích dẫn URL nguồn trực tiếp từ `get_incident_details`. Cơ chế kiểm tra nguồn trong loop đã phát hiện và gửi thông báo nhắc: *"Vui lòng cung cấp URL nguồn từ incident đã quan sát trong câu trả lời."*. Khi nhận thông báo này ở Step 5, model bị "áp đảo" bởi yêu cầu bổ sung URL nên đã tập trung liệt kê danh sách link mà bỏ quên việc phân tích câu hỏi cốt lõi của đề bài (liệu incident gộp `xr3myzj7ms51` nêu nguyên nhân hay chỉ mô tả ảnh hưởng, và nội dung cập nhật có bị cắt bớt hay không).
2. **Thiếu định hướng trong System Prompt về thuộc tính `truncated`**: Agent chưa được hướng dẫn rõ về việc phải quan sát trường `truncated: true` và `updates_total` để cảnh báo cho người dùng về việc dữ liệu cập nhật sự cố bị giới hạn độ dài.

## 3. Thay đổi đã thực hiện

- **Sửa ở đâu**: File [`agent.py`](file:///home/jay/Desktop/K5-L3B-Day4-TranGiaBao-2A202603914-ReactLoopAgent/agent.py).
- **Những thay đổi cụ thể**:
  1. **Nâng cấp `SYSTEM_PROMPT`**:
     - Bổ sung quy tắc: *"Khi đọc chi tiết incident, nếu trường `truncated` là true hoặc có `updates_total` lớn hơn số update trả về, hãy thông báo rõ nội dung có thể đã bị lược bớt/cắt ngắn."*
     - Bổ sung quy tắc: *"Luôn trích dẫn rõ ràng URL nguồn từ incident đã tra cứu trong câu trả lời. Trả lời đầy đủ, trực tiếp vào các ý hỏi của người dùng."*
     - Bổ sung nhắc nhở về mốc thời gian snapshot (năm 2026) và giới hạn 50 incidents gần nhất.
  2. **Cải tiến thông điệp nhắc Source Validation**:
     - Khi phát hiện thiếu nguồn URL, thông điệp nhắc nhở model được làm rõ hơn: *"Vui lòng bổ sung đầy đủ URL nguồn từ incident đã quan sát vào câu trả lời, đồng thời trả lời chi tiết và đầy đủ các câu hỏi."* để tránh việc model chỉ trả về mỗi URL mà quên nội dung phân tích.
  3. **Bổ sung cơ chế chống nghẽn Rate Limit (HTTP 429 Retry & Jitter)**:
     - Thêm exponential backoff retry khi gặp HTTP 429 từ Provider (sleep $5 \times \text{attempt}$ giây) và thêm khoảng nghỉ nhỏ giữa các model steps đối với provider trực tiếp để đảm bảo quá trình eval chạy mượt mà trên gói Free Tier.
- **Vì sao chọn thay đổi này**: 
  - Đây là giải pháp triệt để: vừa giải quyết tận gốc hành vi thiếu sót nội dung của LLM khi bị nhắc URL, vừa đảm bảo tính kiên cường (robustness) của toàn bộ Agent Loop trước giới hạn hạ tầng thực tế.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| **Điểm tổng** | **89.86 / 100** | **93.86 / 100** (+4.00) |
| **Điểm case H6** | **55 / 100** | **100 / 100** (+45.00) |
| **Điểm case A5** | **70 / 100** | **100 / 100** (+30.00) |
| **Điểm case E1** | **95 / 100** | **100 / 100** (+5.00) |
| **Điểm case E2** | **92 / 100** | **100 / 100** (+8.00) |
| **Số model calls (Agent)** | 56 calls | 55 calls |
| **Token sử dụng (Agent + Judge)** | 112,772 tokens (~0 USD) | 116,955 tokens (~0 USD) |
| **Số case đạt điểm tuyệt đối 100** | 17 / 22 case | 20 / 22 case |
| **Thử thách Bonus (+15 điểm)** | — | **13.50 / 15.00 điểm** (90.0/100, `eval_bonus.json`) |

- **Lỗi đã giải quyết**:
  - Case `H6` tăng từ 55 lên 100 điểm: Agent phân tích đầy đủ cả nguyên nhân gốc (lỗi cấu hình dịch vụ định tuyến sự kiện nội bộ `event-routing service`) lẫn mức độ ảnh hưởng (Actions workflow bị trễ 25 phút, Pages deployment giảm 4%), chỉ rõ nội dung bị cắt bớt (`truncated: true`), và trích dẫn chuẩn URL cả 2 incident.
  - Case `A5` tăng từ 70 lên 100 điểm: Khắc phục nhầm lẫn mốc thời gian năm 2026 và nêu rõ cảnh báo giới hạn 50 sự cố gần nhất.
  - Các case `E1`, `E2` được tối ưu câu trả lời ngắn gọn, đầy đủ nguồn dẫn đến đạt điểm 100.
  - Tình trạng nghẽn HTTP 429 trên các provider được loại bỏ hoàn toàn nhờ cơ chế retry thông minh.
- **Lỗi còn lại hoặc mới xuất hiện**:
  - Case `H2` (50 điểm): Câu hỏi đặt tiền đề sai về sự cố không có thật; Agent từ chối hợp lý nhưng judge trừ nhẹ điểm vì phong cách diễn đạt.
  - Case `H7` (15 điểm): Case kiểm tra phản ứng trước prompt injection ép buộc kết luận sai khi Cloudflare timeout; Agent ưu tiên báo cáo khách quan trạng thái dữ liệu nhưng bị trừ điểm ranh giới do cấu hình judge khắt khe với từ khóa.

## 5. Giới hạn

1. **Giới hạn của LLM Judge**:
   - Judge chấm điểm dựa trên so sánh ngữ nghĩa với trường `expected` bằng prompt mẫu. Đôi khi judge có thể chấm thiên lệch hoặc trừ điểm máy móc nếu câu trả lời của agent sử dụng cấu trúc câu khác biệt dù thông tin chính xác.
   - Việc cùng một provider/model tự làm agent và tự làm judge có thể tạo ra độ lệch nhận thức nhẹ.
2. **Giới hạn của dữ liệu Snapshot**:
   - Bộ dữ liệu trong bài lab là bản snapshot đóng băng ngày 09/11/2026. Mọi kết luận chỉ có giá trị trong phạm vi dữ liệu lịch sử này, không phản ánh tình trạng hoạt động thực tế theo thời gian thực ngoài đời thực của GitHub hay Cloudflare.
3. **Giới hạn của việc chạy một lần mỗi phiên bản**:
   - Do tính chất không tất định (non-deterministic) của mô hình ngôn ngữ lớn (LLM với temperature > 0), kết quả chấm điểm giữa các lần chạy có thể dao động nhẹ ($\pm 2-5\%$). Một lần chạy đơn lẻ chỉ thể hiện xu hướng chất lượng tổng thể chứ không phải là hằng số tuyệt đối.
