# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Tiến Đạt
- **MSSV:** 2A202602970
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/DatTienNguyenn/K4-L3-DAY13-NguyenTienDat-2A202602970-Monitoring-LLMOps
- **Commit SHA cuối:** `378e6b5`
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1` (Cohort: `K4`, Class: `K4-L3B`, Seed: `1304`)
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602970`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` (`evidence/01-pytest.txt`) |
| Log validator | `evidence/02-log-validator.png` (`evidence/02-log-validator.txt`) |
| Dashboard validator | `evidence/03-dashboard-validator.png` (`evidence/03-dashboard-validator.txt`) |
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
| `validate_logs.py` | 30/100 (21 records, 20 missing required fields & enrichment, 0 unique correlation IDs) | 100/100 (36 records, 0 missing required fields & enrichment, 19 unique correlation IDs, 0 PII leaks) | Đạt 100/100 sau khi hoàn thiện CP1 |
| `validate_dashboard.py` | HỢP LỆ: 6/6 panel có trong dashboard contract | HỢP LỆ: 6/6 panel có trong dashboard contract | Đủ 6 panel chuẩn kèm biểu đồ SVG + threshold |
| `pytest` | 22 passed in 1.00s | 24 passed in 1.36s | Bổ sung 2 test cho CCCD và thẻ thanh toán |
| Số traces hợp lệ | 10 traces (từ `load_test.py`) | > 30 traces hợp lệ có đủ cây `lab-agent-run` -> `retrieval` + `generation` | Đầy đủ metadata, prompt link, usage & cost |
| Số PII leak | 0 | 0 | `scrub_event` chạy trước khi ghi JSONL |
| Latency P95 / TTFT P95 | 153.0ms / 50.0ms (CP3 warm baseline) | 2659.0ms / 50.0ms (khi bật challenge `rag_slow`) | Tăng gấp ~17.4x ở P95/P99 trong khi TTFT P95 giữ nguyên 50ms |
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
- **SLO và lý do chọn:** Chọn SLO `fast_successful_requests` (`config/slo.yaml`): **99.5%** các request (`event == "request_received"`) phải trả về thành công (`event == "response_sent"`) và có `latency_ms <= 3000ms` trong cửa sổ 28 ngày. Lý do: ở trạng thái baseline bình thường, P50 ~ 152ms, P95 ~ 153ms–1172ms, TTFT P95 ~ 50ms, error rate = 0%; ngưỡng 3000ms tạo khoảng đệm hợp lý cho dao động mạng nhưng vẫn bắt được khi hệ thống bị suy giảm hiệu năng.
- **Cách tính error budget:** Với SLO `99.5%` trong 28 ngày, error budget là `100% - 99.5% = 0.5%`. Giả sử hệ thống phục vụ `10,000` requests trong 28 ngày thì số request tối đa được phép lỗi hoặc chậm hơn 3000ms là `10,000 × 0.5% = 50 requests`.
- **Ba alert và runbook tương ứng:** (chi tiết trong [`config/alert_rules.yaml`](../config/alert_rules.yaml) và [`docs/alerts.md`](../docs/alerts.md)):
  1. `HighLatencyP95` (`warning`, `duration: 5m`, Slack `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-1`): kích hoạt khi `p95(latency_ms) > 3000` hoặc `p95(ttft_ms) > 500`.
  2. `HighErrorRateOrRetrievalDegradation` (`critical`, `duration: 3m`, Slack `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-2`): kích hoạt khi `error_rate_pct > 2%` hoặc `tool_success_rate_pct < 90%`.
  3. `CostSpikeOrQualityDrop` (`warning`, `duration: 10m`, Slack `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-3`): kích hoạt khi `sum_60m(cost_usd) > 2.5` hoặc `sum_60m(tokens_out) > 50000` hoặc `mean(quality_score) < 0.75`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1` (Cohort: `K4`, Class: `K4-L3B`, Seed: `1304`)
- **Khoảng thời gian điều tra:** `2026-09-30 05:43:54 UTC` → `2026-09-30 05:44:08 UTC` (so sánh với baseline sạch tại `05:17:02 UTC` → `05:17:04 UTC`).
- **Triệu chứng từ metrics:**
  - Trên **Panel 1 (`latency` — Latency percentiles and TTFT)**: `Latency P95` và `Latency P99` tăng vọt từ **`153.0 ms`** (baseline lúc `05:17 UTC`) lên **`2659.0 ms`** (tăng gấp **~17.4 lần**, tăng thêm `+2506 ms`), trong khi `Latency P50` là `152.0 ms` và `TTFT P95` vẫn giữ nguyên ở **`50.0 ms`**.
  - Các panel khác vẫn bình thường: **Panel 3 (`errors`)** có `Error Rate = 0.0%`, `Retrieval Success = 100.0%`; **Panel 4 (`cost`)** có `total = $0.031965` (`<= 2.5 USD`); **Panel 5 (`tokens`)** có `tokens_in = 695`, `tokens_out = 1992`; **Panel 6 (`quality`)** có `mean = 0.867` (`>= 0.75`).
  - Việc `Latency P95/P99` tăng thêm ~2500ms nhưng `TTFT P95` của LLM vẫn 50ms và `Error Rate = 0%` cho thấy độ trễ phát sinh ở bước xử lý trước khi gọi LLM (hoặc ngoài bước sinh token).
- **Log line và correlation ID liên quan:**
  - Lọc `data/logs.jsonl` trong khoảng `05:43:54Z` – `05:44:08Z` phát hiện cả 5 request thuộc challenge (`session_id` từ `k4-l3b-challenge-s01` đến `s05`) đều có `latency_ms` từ `2652 ms` đến `2659 ms` (so với `152 ms` ở baseline).
  - Request đại diện: **`correlation_id = "req-3f4f5dda"`** (`session_id = "k4-l3b-challenge-s04"`, `user_id_hash = "c3a24a72d92a"`, `feature = "monitoring"`):
    ```json
    {"service": "api", "latency_ms": 2659, "ttft_ms": 50, "tokens_in": 48, "tokens_out": 180, "cost_usd": 0.002844, "quality_score": 0.9, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "model": "claude-sonnet-4-5", "session_id": "k4-l3b-challenge-s04", "user_id_hash": "c3a24a72d92a", "env": "dev", "feature": "monitoring", "correlation_id": "req-3f4f5dda", "level": "info", "ts": "2026-09-30T05:43:57.194248Z"}
    ```
  - (Các request cùng đợt: `req-92e7b525` — `2652ms`, `req-44e4b7e6` — `2652ms`, `req-8db90d5c` — `2652ms`, `req-5b95582f` — `2652ms`; ngay trước đó tại `05:43:54.344492Z` có log `event="incident_enabled"`, `payload={"name": "rag_slow"}`).
- **Trace ID và span gây ảnh hưởng:**
  - Tra cứu trên Langfuse theo `metadata.correlation_id = "req-3f4f5dda"` tìm thấy **Trace ID: `97e225939071bb53739a53819bf52173`** (các trace cùng đợt: `d81c14ee3eeafb5c897dc6ff91803e04` cho `req-92e7b525`, `0a41436abdd808138a40010871e82a20` cho `req-44e4b7e6`, `faa13e2266f867b9a0ffd796b4bce0d0` cho `req-8db90d5c`, `74b5964ad85b2eee37d4e933ae3efbb3` cho `req-5b95582f`).
  - So sánh waterfall các span bên trong Trace `97e225939071bb53739a53819bf52173`:
    - Root observation **`lab-agent-run`** (`AGENT`): tổng thời gian **`2.660s`** (`2660 ms`), status `DEFAULT` (OK).
    - Child span **`retrieval`** (`RETRIEVER`): chiếm **`2.508s`** (`2508 ms`, tương đương **94.3%** tổng thời gian request), trong khi ở trace baseline (`15c009efb61a4606e6f120c769f25137`) span `retrieval` chỉ mất **`0.001s` (`1 ms`)**.
    - Child span **`generation`** (`GENERATION`): chỉ mất **`0.152s`** (`152 ms`, `ttft_ms = 50 ms`, `input = 48`, `output = 180`), hoàn toàn bình thường như baseline.
- **Root cause:** Bước truy xuất tài liệu RAG (`retrieve()` trong `app/mock_rag.py`) bị nghẽn độ trễ cao (`rag_slow` incident làm mỗi lệnh gọi `retrieve()` bị chặn `time.sleep(2.5)` giây), khiến span `retrieval` tăng từ `~1 ms` lên `~2501–2508 ms` và kéo tổng `latency_ms` của mọi request tăng lên `~2652–2659 ms`.
- **Fix action:** Tắt ngay incident `rag_slow` qua control API (`python scripts/inject_incident.py --scenario rag_slow --disable` hoặc `POST /incidents/rag_slow/disable`), sau đó kiểm tra `/health` (`rag_slow: false`) và gửi lại workload để xác nhận `retrieval` span quay về `~1 ms` và `latency_ms` về `~152 ms`.
- **Preventive measure:**
  1. Thiết lập timeout cứng và cơ chế caching/circuit-breaker cho bước `retrieve()` (ví dụ nếu vector store phản hồi quá `500 ms` thì trả fallback context thay vì block 2.5s).
  2. Chuyển bước gọi RAG và I/O sang bất đồng bộ (`async/await`) để khi `--concurrency 5` các request không bị xếp hàng tuần tự trên worker đồng bộ.
  3. Bổ sung cảnh báo sớm cho độ trễ tầng retrieval (`p95(retrieval_span_latency_ms) > 1000ms` hoặc hạ ngưỡng cảnh báo `HighLatencyP95` xuống `2000ms` dựa trên baseline `153ms`) để phát hiện suy giảm RAG ngay cả khi tổng latency (`2659ms`) tiệm cận ngưỡng SLO `3000ms`.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Thiết kế dashboard runtime trực tiếp trong FastAPI (`app/dashboard.py` phục vụ tại `/dashboard` và `/api/dashboard`) bằng SVG thuần thay vì cài đặt Streamlit vào chung `.venv`. Quyết định này giúp giữ nguyên môi trường thư viện của API, tự động tính đúng `tool_success_rate_pct` trên cả `response_sent` lẫn `request_failed`, hiển thị trực quan cả 6 biểu đồ cùng đường nét đứt Threshold/SLO trong một màn hình duy nhất và tự refresh mỗi 30 giây.
- **Một lỗi/blocker đã gặp:** Khi gọi Langfuse Cloud (`cloud.langfuse.com`), một trong ba địa chỉ IPv4 trả về từ DNS (`54.154.141.85`) bị timeout kết nối TCP/SSL, khiến `client.get_prompt(..., fetch_timeout_seconds=2)` bị rơi vào `local-fallback` ở các request đầu tiên và OTLP span exporter đôi khi bị read timeout.
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra log của `uvicorn` và đo thời gian kết nối tới từng IP của `cloud.langfuse.com` bằng `curl --resolve`. Sau khi xác định IP `54.154.141.85` bị treo còn `40.180.110.56` phản hồi nhanh, tôi đã lọc bỏ IP bị treo trong `socket.getaddrinfo` tại `app/tracing.py` và tăng `OTEL_EXPORTER_OTLP_TIMEOUT`, giúp prompt resolution lấy đúng từ Langfuse (`source="langfuse"`) và 100% spans được đẩy lên Langfuse Cloud ổn định.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - **Metrics** (Dashboard) trả lời *"Hệ thống đang có triệu chứng gì và xảy ra lúc nào?"* (ví dụ: Latency P95 tăng vọt từ 153ms lên 2659ms lúc 05:43–05:44 UTC, trong khi TTFT P95 vẫn 50ms và Error rate = 0%).
  - **Logs** (`data/logs.jsonl`) trả lời *"Request cụ thể nào bị ảnh hưởng?"* bằng cách lọc trong khung giờ bất thường để lấy `correlation_id` (ví dụ `req-3f4f5dda` có `latency_ms=2659`).
  - **Traces** (Langfuse waterfall) trả lời *"Bước nào bên trong request đó là nguyên nhân gốc?"* bằng cách tra theo `correlation_id` và nhìn thấy span `retrieval` chiếm 2.508s trên tổng 2.660s, trong khi `generation` chỉ mất 0.152s.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Trong ứng dụng LLM, thay đổi prompt có thể làm tăng vọt số lượng token đầu ra, đẩy chi phí (`cost_usd`) và độ trễ tăng cao hoặc làm giảm chất lượng câu trả lời. Việc gắn `prompt_name`, `prompt_label`, `prompt_version` vào từng trace giúp biết chính xác phiên bản prompt nào gây suy giảm SLO, từ đó chỉ cần đổi label `production` trên Langfuse để rollback tức thì về version ổn định (`v1`) mà không cần sửa code hay redeploy ứng dụng.
- **Điều quan trọng nhất đã học:** Không bao giờ đoán mò root cause hoặc mở trace ngẫu nhiên khi vận hành hệ thống AI; sự kết hợp giữa `correlation_id` xuyên suốt, PII redaction trước khi ghi log/trace và chuỗi điều tra có kỷ luật **Metrics → Logs → Traces** giúp khoanh vùng sự cố chính xác và an toàn.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Đã hoàn thành toàn bộ các yêu cầu kỹ thuật, kiểm thử, dashboard, SLO/alerts, điều tra challenge và báo cáo của bài lab.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.

