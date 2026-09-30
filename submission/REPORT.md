# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Tiến Đạt
- **MSSV:** 2A202602970
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/DatTienNguyenn/K4-L3-DAY13-NguyenTienDat-2A202602970-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602970`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 (21 records, 20 missing required fields & enrichment, 0 unique correlation IDs) | 100/100 (21 records, 0 missing required fields & enrichment, 10 unique correlation IDs, 0 PII leaks) | Đạt 100/100 sau khi hoàn thiện CP1 |
| `validate_dashboard.py` | HỢP LỆ: 6/6 panel có trong dashboard contract | HỢP LỆ: 6/6 panel có trong dashboard contract | Đủ 6 panel chuẩn |
| `pytest` | 22 passed in 1.00s | 24 passed in 1.02s | Bổ sung 2 test cho CCCD và thẻ thanh toán |
| Số traces hợp lệ | 10 traces (từ `load_test.py`) | | |
| Số PII leak | 0 | 0 | `scrub_event` chạy trước khi ghi JSONL |
| Latency P95 / TTFT P95 | 2126.0ms / 50.0ms | | |
| Retrieval success rate | 100% (10/10 requests `tool_success=True`) | | |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware` (`app/middleware.py`), đầu mỗi request gọi `clear_contextvars()` để xóa context cũ, đọc header `x-request-id` (nếu không có thì tự sinh theo format `req-<8-char-hex>` bằng `uuid.uuid4().hex[:8]`), lưu vào `request.state.correlation_id`, gọi `bind_contextvars(correlation_id=correlation_id)` để gắn tự động vào mọi log, và gắn `x-request-id` cùng `x-response-time-ms` vào response headers.
- **Các metadata được ghi vào structured log:** `ts`, `level`, `service`, `event`, `correlation_id`, kèm context enrichment được bind tại `/chat` (`user_id_hash`, `session_id`, `feature`, `model`, `env`) và các chỉ số vận hành tại `response_sent` (`latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, `payload`).
- **Cách bảo đảm PII được scrub trước khi ghi:** Đăng ký processor `scrub_event` trong `structlog.configure` (`app/logging_config.py`) đứng trước `JsonlFileProcessor()` và `structlog.processors.JSONRenderer()`, kết hợp `summarize_text()` gọi `scrub_text()` để thay thế email, số điện thoại VN, CCCD 12 số và số thẻ thanh toán 16 số bằng chuỗi `[REDACTED_<TYPE>]`. User ID được băm một chiều bằng SHA-256 (`hash_user_id`).
- **Cách kiểm chứng kết quả:** Chuyển file log cũ ra ngoài repo (`../logs-cp0-baseline.jsonl`), khởi động lại API, chạy `python scripts/load_test.py`, `python scripts/validate_logs.py` (đạt `100/100`, `Potential PII leaks detected: 0`, `Unique correlation IDs found: 10`) và chạy `python -m pytest -q` (`24 passed`).

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
- **SLO và lý do chọn:**
- **Cách tính error budget:**
- **Ba alert và runbook tương ứng:**

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
