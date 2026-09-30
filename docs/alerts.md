# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Primary SLO `fast_successful_requests` (`response_sent.latency_ms <= 3000ms` đạt 99.5% trong 28 ngày) và panel `latency` (`p95(latency_ms) <= 3000ms`).
- Điều kiện và thời gian duy trì: `p95(response_sent.latency_ms) > 3000ms` hoặc `p95(response_sent.ttft_ms) > 500ms` duy trì liên tục trong `5m`.
- Ảnh hưởng tới người dùng: Người dùng phải chờ lâu hơn 3 giây mới nhận được phản hồi từ hệ thống chat/summary, làm giảm trải nghiệm tương tác thời gian thực và tiêu hao nhanh error budget (tối đa 50 request/10,000 request).
- Ba bước kiểm tra đầu tiên (Metrics → Logs → Traces):
  1. **Metrics:** Mở Dashboard (`http://127.0.0.1:8000/dashboard`) panel `1. Latency percentiles and TTFT`, xác định khoảng thời gian `P95` / `P99` vượt đường threshold `3000 ms` và kiểm tra xem `TTFT P95` có tăng cùng lúc hay không.
  2. **Logs:** Lọc `data/logs.jsonl` trong khoảng thời gian đó với điều kiện `event == "response_sent"` và `latency_ms > 3000`, lấy ra một `correlation_id` đại diện cùng các trường `feature`, `model`, `tokens_out`.
  3. **Traces:** Mở project Langfuse cá nhân `day13-k4-l3b-2A202602970`, tìm trace theo `metadata.correlation_id`, mở waterfall của `lab-agent-run` để so sánh thời gian thực thi của child span `retrieval` và `generation` (xác định chậm do vector store/RAG hay do LLM sinh nhiều token).
- Mitigation tạm thời: Nếu span `retrieval` chiếm phần lớn thời gian (~2.5s), tắt incident/cấu hình gây nghẽn RAG (`POST /incidents/rag_slow/disable` hoặc `python scripts/inject_incident.py --scenario rag_slow --disable`), giảm top-k/timeout cho bước truy vấn tài liệu; nếu chậm ở `generation` sau khi đổi prompt, rollback label `production` của prompt `day13-chat` về version baseline (`v1`).
- Owner: `student-2A202602970`

## Alert 2

- Tên: `HighErrorRateOrRetrievalDegradation`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Primary SLO `fast_successful_requests` (tỉ lệ thành công >= 99.5%), guardrail `error_rate_pct_max <= 2%` và `retrieval_success_rate_pct_min >= 90%` trên panel `errors`.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` hoặc `tool_success_rate_pct < 90%` duy trì liên tục trong `3m`.
- Ảnh hưởng tới người dùng: Người dùng nhận lỗi HTTP 500 trực tiếp khi gửi câu hỏi hoặc hệ thống không lấy được tài liệu tham chiếu từ RAG, gây gián đoạn dịch vụ nghiêm trọng.
- Ba bước kiểm tra đầu tiên (Metrics → Logs → Traces):
  1. **Metrics:** Kiểm tra panel `3. Error rate and retrieval success` trên Dashboard để xem tỉ lệ `Error Rate (%)`, `Retrieval Success (%)` giảm xuống bao nhiêu và loại lỗi nào xuất hiện trong `Breakdown (count_by_value)` (ví dụ `RuntimeError`).
  2. **Logs:** Lọc `data/logs.jsonl` theo `event == "request_failed"` hoặc `tool_success == false` trong khung giờ phát sinh cảnh báo, trích xuất `correlation_id`, `error_type`, `tool_name` và `payload.detail` (ví dụ `"Vector store timeout"`).
  3. **Traces:** Tra cứu trace trên Langfuse theo `correlation_id` vừa lấy, kiểm tra trạng thái lỗi (`ERROR`) nằm ở span `retrieval` hay `generation` và xem `prompt_version` / `metadata` đi kèm.
- Mitigation tạm thời: Khôi phục kết nối vector store hoặc tắt chế độ giả lập lỗi công cụ (`POST /incidents/tool_fail/disable` hoặc `python scripts/inject_incident.py --scenario tool_fail --disable`), kích hoạt fallback trả lời an toàn khi retrieval timeout để không làm sập toàn bộ request `/chat`.
- Owner: `student-2A202602970`

## Alert 3

- Tên: `CostSpikeOrQualityDrop`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Guardrails `daily_cost_usd_max <= 2.5 USD`, `tokens <= 50,000` và `quality_score_avg_min >= 0.75` trên các panel `cost`, `tokens`, `quality`.
- Điều kiện và thời gian duy trì: Tổng chi phí trong cửa sổ 60 phút `sum(cost_usd) > 2.5 USD`, hoặc tổng token `sum(tokens_out) > 50,000`, hoặc điểm chất lượng trung bình `mean(quality_score) < 0.75` kéo dài trong `10m`.
- Ảnh hưởng tới người dùng: Chi phí vận hành LLM tăng đột biến vượt ngân sách (do prompt dài hoặc output token phình to gấp nhiều lần) hoặc câu trả lời bị suy giảm chất lượng, thiếu thông tin từ tài liệu.
- Ba bước kiểm tra đầu tiên (Metrics → Logs → Traces):
  1. **Metrics:** Quan sát các panel `4. Cost over time`, `5. Input and output tokens` và `6. Quality proxy` trên Dashboard để xác định thời điểm `cost_usd` / `tokens_out` tăng vọt hoặc `mean(quality_score)` tụt dưới ngưỡng `0.75`.
  2. **Logs:** Lọc các bản ghi `event == "response_sent"` trong `data/logs.jsonl` có `cost_usd` hoặc `tokens_out` cao bất thường (hoặc `quality_score < 0.75`), lấy `correlation_id`, `feature` và `model`.
  3. **Traces:** Mở trace tương ứng với `correlation_id` trên Langfuse, kiểm tra span `generation` (`usage_details.input`, `usage_details.output`, `cost_details.total`) và `lab-agent-run` metadata (`prompt_name`, `prompt_label`, `prompt_version`, `doc_count`) để xác định có phải do prompt mới hay sự cố `cost_spike`.
- Mitigation tạm thời: Nếu nguyên nhân do `cost_spike` hoặc giới hạn token chưa chặt, tắt kịch bản lỗi (`POST /incidents/cost_spike/disable` hoặc `python scripts/inject_incident.py --scenario cost_spike --disable`) và giới hạn `max_tokens`; nếu phát sinh ngay sau khi promote prompt mới lên `production`, lập tức rollback label `production` của `day13-chat` về version `1` (`baseline`).
- Owner: `student-2A202602970`

