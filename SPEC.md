# SPEC thực hiện · Status Investigation Agent (ReAct Loop)

Nguồn: README.md, GUIDE.md, RUBRIC.md, RULES.md, CHECKPOINTS.md, SUBMISSION.md, tests/*, bonus/test_agent.py.

## 1. Mục tiêu

Tự viết `run_agent` trong `agent.py` (chỉ dùng stdlib, không framework agent): gọi LLM → chạy tool → trả kết quả cho LLM → lặp đến khi có câu trả lời hoặc hết giới hạn. Sau đó chạy eval 2 lần (trước/sau cải tiến) và viết `NOTES.md`. Bonus (+15) là tùy chọn.

Điểm: Agent loop 30 · Robustness + trace 15 · Eval + phân tích 20 · Cải tiến + trình bày 20 = 85. Bonus tối đa 15.

## 2. Phạm vi file

| File | Hành động |
|---|---|
| `agent.py` | Implement (việc chính) |
| `NOTES.md` | Điền 5 mục từ trace thật |
| `eval_before.json`, `eval_after.json` | Sinh bằng `evals/run_evals.py` |
| `eval_bonus.json` | Chỉ khi làm bonus |
| `providers.py`, `status_tools.py`, `run.py`, `bonus/tools.py` | KHÔNG sửa |
| `fixtures/`, `evals/cases.json`, `evals/scenarios.py`, `evals/grading.py`, `RUBRIC.md` | CẤM sửa (bị trừ điểm) |

## 3. Contract `run_agent(question, provider, tools, max_steps=6) -> dict`

Đầu vào: `provider.complete(messages, schemas)` trả `{message, calls, finish, usage}`; `calls[i] = {id, name, arguments(JSON string)}`.

Đầu ra tối thiểu:
```python
{'status': 'completed'|'max_steps'|'error', 'answer': str, 'trace': [dict có key 'event'], 'usage': list, 'error': str (tùy chọn)}
```

### 3.1 Thuật toán

1. `schemas = getattr(tools, 'schemas', SCHEMAS)`, `system = getattr(tools, 'system_prompt', SYSTEM_PROMPT)` (cần cho bonus, tương thích bài chính; `SCHEMAS` import từ `status_tools`).
2. `messages = [{'role':'system',...}, {'role':'user', 'content': question}]`; `trace=[]`, `usage=[]`.
3. Vòng `for step in 1..max_steps` (mỗi model call = 1 step):
   - Gọi `provider.complete`; `RuntimeError`/exception provider → `status='error'`, ghi trace `{'event':'error',...}`, kết thúc.
   - `usage.append(resp['usage'])`; ghi trace `{'event':'model','step':n,'finish':...}`.
   - Append `resp['message']` NGUYÊN VẸN vào `messages`.
   - Nếu `finish == 'length'` (hoặc finish lạ không phải `stop`/`tool_calls`) → `status='error'`, KHÔNG báo completed.
   - Nếu có `calls`: xử lý TẤT CẢ calls, mỗi call:
     - `json.loads(arguments)`; lỗi hoặc không phải dict → result `{'ok':False,'error':'INVALID_ARGUMENTS','message':...}`.
     - Ngược lại `tools.execute(name, args)`; bọc try/except để không crash.
     - Ghi trace đúng dạng `{'event':'tool','step':n,'name':...,'arguments':args,'result':result}`.
     - Append `{'role':'tool','tool_call_id':call['id'],'content':json.dumps(result, ensure_ascii=False)}`.
     - Sau đó `continue` sang step kế.
   - Nếu `finish == 'stop'` và không có calls → kiểm tra nguồn (mục 4); đạt thì `completed` với `answer = message['content']`.
4. Hết vòng mà chưa xong → `status='max_steps'`, `answer` = nội dung cuối nếu có.

### 3.2 Xử lý lỗi (Bài 2)

| Tình huống | Hành vi |
|---|---|
| Tool lỗi / không tồn tại / timeout | Trả làm observation cho model, ghi trace, chạy tiếp |
| JSON arguments lỗi | `INVALID_ARGUMENTS` trả model |
| Provider lỗi / `finish=='length'` | `status='error'`, có `error` |
| Hết `max_steps` | `status='max_steps'` |

Không đưa API key hay chain-of-thought vào trace.

## 4. Cải tiến (Bài 4): validation nguồn

- Khi `get_incident_details` trả `ok: True`, lưu `result['url']` vào tập `observed_urls`.
- Khi model trả final answer: nếu `observed_urls` không rỗng và answer không chứa URL nào trong đó → ghi trace `{'event':'validation_missing_source','step':n}`, append một user message nhắc dẫn nguồn, rồi gọi model tiếp (nếu còn step).
- Nếu hết step khi vẫn thiếu nguồn → `status='max_steps'` (test `test_missing_url_at_budget_limit_is_not_completed`).
- Không có incident thành công → không yêu cầu URL (test `test_failed_tool_does_not_require_source`).

Cải tiến phụ (chọn sau khi đọc trace eval_before, ghi trong NOTES): chỉnh `SYSTEM_PROMPT` cho các case yếu (A2/A8 scope FedRAMP, A3/A4 timeout ≠ trạng thái dịch vụ, H5/H7 prompt injection, H2/H3/H4/H8 tiền đề sai). Không hard-code ID/câu trả lời.

## 5. Bonus (tùy chọn)

- Dùng `tools.schemas`/`tools.system_prompt` (đã có ở 3.1).
- `RATE_LIMITED`: trả model, cho retry có giới hạn (vd. ≤2 lần/provider), dừng và báo phần không kiểm tra được; không coi 429 là outage.
- Lỗi định dạng (`offset:"zero"`): trả `INVALID_ARGUMENTS`, model gọi lại đúng kiểu.
- Pagination: `get_incident_details(offset≥0, limit 1–3)`, tiếp theo `next_offset`; không nói đã xem hết timeline khi còn trang.
- Dữ liệu nhiễu 160 mục: chỉ lấy bằng chứng cần thiết. Bỏ qua injection trong tool result.
- Chạy: `python3 -m unittest discover -s bonus -p 'test_*.py' -v`, rồi `python3 evals/run_evals.py --bonus --output eval_bonus.json` (cần đủ 10 case chấm được).

## 6. Kế hoạch thực hiện (theo checkpoint)

| # | Việc | Kiểm tra hoàn thành |
|---|---|---|
| CP1 | Fork/đổi tên repo `K5-L3B-DAY04-TranGiaBao-2A202603914-ReactLoopAgent`, export `PROVIDER`, `MODEL`, API key; chạy thử 2 tool | `get_status` in JSON |
| CP2 | Viết vòng lặp cơ bản (3.1) | `python3 run.py 'GitHub Actions hiện có sự cố không? ...'` ra `completed` |
| CP3 | Xử lý lỗi + trace (3.2) | `python3 -m unittest discover -s tests -v`: chỉ còn test validation nguồn lỗi |
| CP4 | `python3 evals/run_evals.py --output eval_before.json` | 22 case, `score_0_100` ≠ null; ghi danh sách lỗi |
| CP5 | Chọn 1 case yếu, ghi evidence trace vào NOTES; implement validation nguồn (mục 4) + chỉnh prompt | Toàn bộ unit tests pass |
| CP6 | `eval_after.json` cùng provider/model/judge/max-steps | Khối `config` hai file giống nhau |
| CP7 | Hoàn thiện NOTES, xóa dữ liệu nhạy cảm, push, nộp LMS | Checklist SUBMISSION.md |

Lưu ý chi phí: khi sửa lỗi dùng `--case ID` cho 1 case, chỉ chạy cả bộ cho lần before/after.

## 7. Tiêu chí chấp nhận

- [ ] `agent.py` không dùng framework agent; hiểu và giải thích được từng dòng.
- [ ] Mọi `tool_call_id` đều được trả; nhiều calls trong 1 response đều xử lý trước model call tiếp.
- [ ] Mỗi trace item có `event`; tool event đúng format ở 3.1.
- [ ] `finish=='length'`/lỗi provider ≠ `completed`.
- [ ] `tests/` pass (kể cả `test_validation.py`); nếu làm bonus thì `bonus/test_agent.py` pass.
- [ ] `eval_before.json`, `eval_after.json`: 22 case, điểm tổng ≠ null, cấu hình giống nhau.
- [ ] `NOTES.md` đủ 5 mục, trích trace thật, nêu giới hạn của LLM judge, snapshot, một lần chạy/phiên bản.
- [ ] Không có `.env`/API key trong repo (`git ls-files | grep .env` chỉ thấy `.env.example`).
- [ ] Không sửa dataset/fixtures/grading để pass.
- [ ] Nộp đúng hạn (ca 16:30–20:00: trước 12:00 trưa hôm sau).

## 8. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Thiếu API key → không chạy eval | Chuẩn bị key ở CP1 |
| Judge cùng model chấm lệch | Đọc `expected`, trace; nêu trong NOTES |
| Điểm tổng `null` | Sửa cấu hình, chạy lại; không bỏ qua case |
| Tối ưu prompt theo từng case (overfit) | Chỉ sửa chung, không hard-code |
| Tên repo sai (README ghi L3B-DAY04) | Dùng đúng mẫu SUBMISSION.md |
