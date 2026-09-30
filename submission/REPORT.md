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
| Trace metadata | `evidence/08-a.png`, `evidence/08-b.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-a.png`, `evidence/10-b.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 (21 records, 20 missing required fields & enrichment, 0 unique correlation IDs) | 100/100 (82 records, 0 missing required fields & enrichment, 34 unique correlation IDs, 0 PII leaks) | Đạt 100/100 sau khi hoàn thiện CP1 |
| `validate_dashboard.py` | HỢP LỆ: 6/6 panel có trong dashboard contract | HỢP LỆ: 6/6 panel có trong dashboard contract | Đủ 6 panel chuẩn kèm biểu đồ SVG + threshold |
| `pytest` | 22 passed in 1.00s | 24 passed in 1.01s | Bổ sung 2 test cho CCCD và thẻ thanh toán |
| Số traces hợp lệ | 10 traces (từ `load_test.py`) | > 25 traces hợp lệ có đủ cây `lab-agent-run` -> `retrieval` + `generation` | Đầy đủ metadata, prompt link, usage & cost |
| Số PII leak | 0 | 0 | `scrub_event` chạy trước khi ghi JSONL |
| Latency P95 / TTFT P95 | 2126.0ms / 50.0ms | 1172.0ms / 50.0ms | Đạt trong ngưỡng SLO `<= 3000ms` |
| Retrieval success rate | 100% (10/10 requests `tool_success=True`) | 100.0% | Tính trên toàn bộ event có `tool_success` |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware` (`app/middleware.py`), đầu mỗi request gọi `clear_contextvars()` để xóa context cũ, đọc header `x-request-id` (nếu không có thì tự sinh theo format `req-<8-char-hex>` bằng `uuid.uuid4().hex[:8]`), lưu vào `request.state.correlation_id`, gọi `bind_contextvars(correlation_id=correlation_id)` để gắn tự động vào mọi log, và gắn `x-request-id` cùng `x-response-time-ms` vào response headers.
- **Các metadata được ghi vào structured log:** `ts`, `level`, `service`, `event`, `correlation_id`, kèm context enrichment được bind tại `/chat` (`user_id_hash`, `session_id`, `feature`, `model`, `env`) và các chỉ số vận hành tại `response_sent` (`latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, `payload`).
- **Cách bảo đảm PII được scrub trước khi ghi:** Đăng ký processor `scrub_event` trong `structlog.configure` (`app/logging_config.py`) đứng trước `JsonlFileProcessor()` và `structlog.processors.JSONRenderer()`, kết hợp `summarize_text()` gọi `scrub_text()` để thay thế email, số điện thoại VN, CCCD 12 số và số thẻ thanh toán 16 số bằng chuỗi `[REDACTED_<TYPE>]`. User ID được băm một chiều bằng SHA-256 (`hash_user_id`).
- **Cách kiểm chứng kết quả:** Chuyển file log cũ ra ngoài repo (`../logs-cp0-baseline.jsonl`), khởi động lại API, chạy `python scripts/load_test.py`, `python scripts/validate_logs.py` (đạt `100/100`, `Potential PII leaks detected: 0`, `Unique correlation IDs found: 10`) và chạy `python -m pytest -q` (`24 passed`).

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Kiểm tra trong project Langfuse cá nhân `day13-k4-l3b-2A202602970` (`projectId: cmunhtdw70hcxad0cz02lsbh8`), đối chiếu `correlation_id` trong `metadata` của trace với `correlation_id` trong `data/logs.jsonl` của máy local.
- **Cấu trúc root/retrieval/generation observations:**
  - Trace root: `day13-agent-request`
  - Root observation: `lab-agent-run` (type `AGENT`, gắn metadata `correlation_id`, `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`, `doc_count`, `query_preview`)
  - Child observation 1: `retrieval` (type `RETRIEVER`, gắn `query_preview`, `doc_count`, `capture_input=False`, `capture_output=False`)
  - Child observation 2: `generation` (type `GENERATION`, gắn `model="claude-sonnet-4-5"`, `prompt=managed_prompt`, `usage_details` (`input`, `output`, `total`), `cost_details` (`input`, `output`, `total`), `metadata` an toàn, `capture_input=False`, `capture_output=False`)
- **Cách nối trace với log:** Qua trường `metadata.correlation_id` (ví dụ `req-v1base01`, `req-v2cand01`) được truyền vào `propagate_attributes(metadata={"correlation_id": correlation_id, ...})` trong `LabAgent.run`, khớp 1-1 với trường `correlation_id` trong `data/logs.jsonl`.
- **Prompt name:** `day13-chat` (type: `text`, giữ 3 biến `{{feature}}`, `{{docs}}`, `{{message}}`)
- **Version/label baseline:** Version `1` — labels: `baseline`, `production`
- **Version/label candidate:** Version `2` (thêm hướng dẫn trả lời ngắn gọn, bám sát tài liệu) — label: `candidate`
- **Trace ID của mỗi version:**
  - Version 1 (`label=baseline`, `correlation_id=req-v1base01`): `ecc12109e95ee1551b6db20376450f2f` (và `9a95eed38aa7f59de2332f51eb5fd111` cho `req-v1base02`)
  - Version 2 (`label=candidate`, `correlation_id=req-v2cand01`): `3c15dee0b0939534ac424b81ce6b193f` (và `56010f34b4a0da53eeb11642c365031c` cho `req-v2cand02`)
  - Promote `production` -> Version 2 (`correlation_id=req-prom0002`): `065c7793608bc049e0585a96ad738648`
  - Rollback `production` -> Version 1 (`correlation_id=req-roll0002`): `7d5369d281610f8bb4c2c69d17f09930`
- **Cách promote và rollback `production`:** Không cần sửa code ứng dụng; chỉ chuyển label `production` từ version `1` sang version `2` trên Langfuse (promote), restart/refresh cache và gửi request kiểm tra (`prompt_label=production`, `prompt_version=2`). Khi rollback, chuyển label `production` quay về version `1` trên Langfuse, restart và gửi request kiểm tra (`prompt_label=production`, `prompt_version=1`).

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng tại endpoint `http://127.0.0.1:8000/dashboard` (`app/dashboard.py`), đọc dữ liệu trực tiếp từ `data/logs.jsonl`, cửa sổ mặc định 60 phút, tự refresh mỗi 30 giây, có biểu đồ SVG kèm đường threshold cho từng panel theo đúng `config/dashboard.yaml`:
  1. `latency` (`ms`): Latency P50, P95, P99 và TTFT P95 (threshold `p95 <= 3000 ms`).
  2. `traffic` (`requests_per_minute`): Tổng request và tốc độ request/phút (threshold `rate_per_minute >= 1`).
  3. `errors` (`percent`): Error rate (`%`), breakdown theo `error_type`, và `tool_success_rate_pct` tính trên mọi event có trường `tool_success` (threshold `error_rate_pct <= 2%`).
  4. `cost` (`usd`): Chi phí theo từng phút và tổng chi phí trong cửa sổ 60 phút (threshold `total <= 2.5 USD`).
  5. `tokens` (`tokens`): Tổng `tokens_in` và `tokens_out` (threshold `sum_by_field <= 50000 tokens`).
  6. `quality` (`score_0_to_1`): Trung bình `quality_score` (threshold `mean >= 0.75`).
- **SLO và lý do chọn:** Chọn SLO `fast_successful_requests` (`config/slo.yaml`): **99.5%** các request (`event == "request_received"`) phải trả về thành công (`event == "response_sent"`) và có `latency_ms <= 3000ms` trong cửa sổ 28 ngày. Lý do: ở trạng thái baseline bình thường, P50 ~ 152ms, P95 ~ 1172ms–2126ms, TTFT P95 ~ 50ms, error rate = 0%; ngưỡng 3000ms tạo khoảng đệm hợp lý cho dao động mạng nhưng vẫn bắt được ngay khi bước RAG bị chậm (`rag_slow` cộng thêm 2500ms làm latency vượt >2600–3000ms) hoặc khi `tool_fail` gây lỗi 500.
- **Cách tính error budget:** Với SLO `99.5%` trong 28 ngày, error budget là `100% - 99.5% = 0.5%`. Giả sử hệ thống phục vụ `10,000` requests trong 28 ngày thì số request tối đa được phép lỗi hoặc chậm hơn 3000ms là `10,000 × 0.5% = 50 requests`.
- **Ba alert và runbook tương ứng:** (chi tiết trong [`config/alert_rules.yaml`](../config/alert_rules.yaml) và [`docs/alerts.md`](../docs/alerts.md)):
  1. `HighLatencyP95` (`warning`, `duration: 5m`, Slack `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-1`): kích hoạt khi `p95(latency_ms) > 3000` hoặc `p95(ttft_ms) > 500`.
  2. `HighErrorRateOrRetrievalDegradation` (`critical`, `duration: 3m`, Slack `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-2`): kích hoạt khi `error_rate_pct > 2%` hoặc `tool_success_rate_pct < 90%`.
  3. `CostSpikeOrQualityDrop` (`warning`, `duration: 10m`, Slack `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-3`): kích hoạt khi `sum_60m(cost_usd) > 2.5` hoặc `sum_60m(tokens_out) > 50000` hoặc `mean(quality_score) < 0.75`.


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
