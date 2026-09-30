from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from . import logging_config
from .metrics import percentile


def _parse_ts(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def compute_dashboard_data(time_range_minutes: int = 60) -> dict[str, Any]:
    log_path: Path = logging_config.LOG_PATH
    records: list[dict[str, Any]] = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    now = datetime.now(timezone.utc)
    timestamps = [_parse_ts(r.get("ts")) for r in records]
    valid_ts = [t for t in timestamps if t is not None]
    anchor = max(valid_ts) if valid_ts else now
    cutoff = anchor - timedelta(minutes=time_range_minutes)

    window_records = []
    for r in records:
        dt = _parse_ts(r.get("ts"))
        if dt is None or dt >= cutoff:
            window_records.append((dt, r))

    latencies: list[int] = []
    ttfts: list[int] = []
    costs: list[float] = []
    tokens_in_list: list[int] = []
    tokens_out_list: list[int] = []
    qualities: list[float] = []

    req_received_count = 0
    req_failed_count = 0
    error_types: Counter[str] = Counter()
    tool_total = 0
    tool_ok = 0

    traffic_by_min: dict[str, int] = defaultdict(int)
    cost_by_min: dict[str, float] = defaultdict(float)

    for dt, r in window_records:
        ev = r.get("event")
        minute_key = dt.strftime("%H:%M") if dt else "unknown"

        if ev == "request_received":
            req_received_count += 1
            traffic_by_min[minute_key] += 1
        elif ev == "response_sent":
            if isinstance(r.get("latency_ms"), (int, float)):
                latencies.append(int(r["latency_ms"]))
            if isinstance(r.get("ttft_ms"), (int, float)):
                ttfts.append(int(r["ttft_ms"]))
            if isinstance(r.get("cost_usd"), (int, float)):
                c = float(r["cost_usd"])
                costs.append(c)
                cost_by_min[minute_key] = round(cost_by_min[minute_key] + c, 6)
            if isinstance(r.get("tokens_in"), (int, float)):
                tokens_in_list.append(int(r["tokens_in"]))
            if isinstance(r.get("tokens_out"), (int, float)):
                tokens_out_list.append(int(r["tokens_out"]))
            if isinstance(r.get("quality_score"), (int, float)):
                qualities.append(float(r["quality_score"]))
        elif ev == "request_failed":
            req_failed_count += 1
            err_t = r.get("error_type") or "UnknownError"
            error_types[str(err_t)] += 1

        # Retrieval success = tỉ lệ tool_success == true trên mọi event có field tool_success
        if r.get("tool_success") is not None:
            tool_total += 1
            if r.get("tool_success") is True:
                tool_ok += 1

    active_minutes = max(1, len(traffic_by_min))
    rate_per_minute = round(req_received_count / active_minutes, 2) if req_received_count else 0.0
    error_rate_pct = (
        round((req_failed_count / req_received_count) * 100, 2)
        if req_received_count > 0
        else 0.0
    )
    tool_success_rate_pct = (
        round((tool_ok / tool_total) * 100, 2) if tool_total > 0 else 100.0
    )

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    ttft_p95 = percentile(ttfts, 95)

    total_cost = round(sum(costs), 6)
    sum_tokens_in = sum(tokens_in_list)
    sum_tokens_out = sum(tokens_out_list)
    quality_mean = round(mean(qualities), 3) if qualities else 0.0

    return {
        "title": "K4-L3B Day 13 Monitoring & LLMOps",
        "source": str(log_path),
        "time_range_minutes": time_range_minutes,
        "refresh_seconds": 30,
        "window_start_utc": cutoff.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "window_end_utc": anchor.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_records": len(window_records),
        "panels": {
            "latency": {
                "id": "latency",
                "title": "Latency percentiles and TTFT",
                "unit": "ms",
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "ttft_p95": ttft_p95,
                "threshold_val": 3000,
                "threshold": "p95 <= 3000 ms",
                "threshold_ok": p95 <= 3000,
            },
            "traffic": {
                "id": "traffic",
                "title": "Request traffic",
                "unit": "requests_per_minute",
                "count": req_received_count,
                "rate_per_minute": rate_per_minute,
                "by_minute": dict(sorted(traffic_by_min.items())[-10:]),
                "threshold_val": 1,
                "threshold": "rate_per_minute >= 1 requests_per_minute",
                "threshold_ok": rate_per_minute >= 1,
            },
            "errors": {
                "id": "errors",
                "title": "Error rate and retrieval success",
                "unit": "percent",
                "error_rate_pct": error_rate_pct,
                "failed_count": req_failed_count,
                "count_by_value": dict(error_types),
                "tool_success_rate_pct": tool_success_rate_pct,
                "threshold_val": 2,
                "threshold": "error_rate_pct <= 2 %",
                "threshold_ok": error_rate_pct <= 2.0,
            },
            "cost": {
                "id": "cost",
                "title": "Cost over time",
                "unit": "usd",
                "total": total_cost,
                "sum_by_minute": dict(sorted(cost_by_min.items())[-10:]),
                "threshold_val": 2.5,
                "threshold": "total <= 2.5 usd",
                "threshold_ok": total_cost <= 2.5,
            },
            "tokens": {
                "id": "tokens",
                "title": "Input and output tokens",
                "unit": "tokens",
                "tokens_in": sum_tokens_in,
                "tokens_out": sum_tokens_out,
                "total_tokens": sum_tokens_in + sum_tokens_out,
                "threshold_val": 50000,
                "threshold": "sum_by_field <= 50000 tokens",
                "threshold_ok": max(sum_tokens_in, sum_tokens_out) <= 50000,
            },
            "quality": {
                "id": "quality",
                "title": "Quality proxy",
                "unit": "score_0_to_1",
                "mean": quality_mean,
                "series": qualities[-15:],
                "threshold_val": 0.75,
                "threshold": "mean >= 0.75 score_0_to_1",
                "threshold_ok": quality_mean >= 0.75,
            },
        },
    }


def _svg_bar_chart_with_threshold(
    items: list[tuple[str, float]],
    threshold_val: float,
    max_domain: float,
    threshold_label: str,
    bar_color: str = "#38bdf8",
) -> str:
    w, h = 360, 115
    pad_l, pad_r, pad_t, pad_b = 38, 14, 16, 22
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b
    top_val = max([max_domain, threshold_val * 1.15] + [v for _, v in items]) or 1.0

    def y_pos(val: float) -> float:
        ratio = max(0.0, min(1.0, val / top_val))
        return pad_t + plot_h * (1.0 - ratio)

    th_y = y_pos(threshold_val)
    n = max(1, len(items))
    slot_w = plot_w / n
    bar_w = min(38.0, slot_w * 0.62)

    bars_svg = []
    for idx, (label, val) in enumerate(items):
        cx = pad_l + idx * slot_w + slot_w / 2
        bx = cx - bar_w / 2
        by = y_pos(val)
        bh = max(2.0, (pad_t + plot_h) - by)
        bars_svg.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="3" fill="{bar_color}" opacity="0.88" />'
            f'<text x="{cx:.1f}" y="{by - 3:.1f}" text-anchor="middle" fill="#e2e8f0" font-size="9.5" font-weight="600">{val}</text>'
            f'<text x="{cx:.1f}" y="{h - 6}" text-anchor="middle" fill="#94a3b8" font-size="9.5">{label}</text>'
        )

    return f"""
    <svg viewBox="0 0 {w} {h}" width="100%" height="115" style="background:#0f172a;border-radius:6px;border:1px solid #1e293b;margin-top:6px;">
      <!-- Axes -->
      <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="#475569" stroke-width="1"/>
      <line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{w - pad_r}" y2="{pad_t + plot_h}" stroke="#475569" stroke-width="1"/>
      <!-- Bars -->
      {''.join(bars_svg)}
      <!-- Threshold Line (axhline / mark_rule) -->
      <line x1="{pad_l}" y1="{th_y:.1f}" x2="{w - pad_r}" y2="{th_y:.1f}" stroke="#ef4444" stroke-width="1.8" stroke-dasharray="5,3"/>
      <rect x="{w - pad_r - 135}" y="{max(2.0, th_y - 13):.1f}" width="133" height="12" rx="2" fill="#0f172a" opacity="0.85"/>
      <text x="{w - pad_r - 3}" y="{max(11.0, th_y - 4):.1f}" text-anchor="end" fill="#fca5a5" font-size="9.5" font-weight="700">{threshold_label}</text>
    </svg>
    """


def render_dashboard_html(data: dict[str, Any]) -> str:
    p = data["panels"]
    lat = p["latency"]
    trf = p["traffic"]
    err = p["errors"]
    cst = p["cost"]
    tok = p["tokens"]
    qlt = p["quality"]

    def badge(ok: bool) -> str:
        color = "#16a34a" if ok else "#dc2626"
        label = "OK (Within SLO)" if ok else "BREACH (Alert)"
        return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">{label}</span>'

    lat_svg = _svg_bar_chart_with_threshold(
        [("P50", lat["p50"]), ("P95", lat["p95"]), ("P99", lat["p99"]), ("TTFT P95", lat["ttft_p95"])],
        threshold_val=3000.0,
        max_domain=3500.0,
        threshold_label="Threshold: p95 <= 3000 ms",
        bar_color="#38bdf8",
    )

    trf_items = list(trf["by_minute"].items()) or [("now", trf["rate_per_minute"])]
    trf_svg = _svg_bar_chart_with_threshold(
        [(k, float(v)) for k, v in trf_items[-6:]],
        threshold_val=1.0,
        max_domain=5.0,
        threshold_label="Threshold: >= 1 req/min",
        bar_color="#22c55e",
    )

    err_svg = _svg_bar_chart_with_threshold(
        [("Error Rate %", err["error_rate_pct"]), ("Retrieval OK %", err["tool_success_rate_pct"])],
        threshold_val=2.0,
        max_domain=105.0,
        threshold_label="Threshold: err <= 2%",
        bar_color="#f59e0b",
    )

    cst_items = list(cst["sum_by_minute"].items()) or [("total", cst["total"])]
    cst_svg = _svg_bar_chart_with_threshold(
        [(k, round(float(v), 4)) for k, v in cst_items[-5:]] + [("Total", round(cst["total"], 4))],
        threshold_val=2.5,
        max_domain=2.8,
        threshold_label="Threshold: total <= 2.5 USD",
        bar_color="#a855f7",
    )

    tok_svg = _svg_bar_chart_with_threshold(
        [("tokens_in", float(tok["tokens_in"])), ("tokens_out", float(tok["tokens_out"]))],
        threshold_val=50000.0,
        max_domain=55000.0,
        threshold_label="Threshold: <= 50000 tokens",
        bar_color="#06b6d4",
    )

    qlt_svg = _svg_bar_chart_with_threshold(
        [("mean(quality)", qlt["mean"])] + [(f"q{i+1}", v) for i, v in enumerate(qlt["series"][-4:])],
        threshold_val=0.75,
        max_domain=1.05,
        threshold_label="Threshold: mean >= 0.75",
        bar_color="#10b981",
    )

    err_breakdown = (
        ", ".join(f"{k}: {v}" for k, v in err["count_by_value"].items())
        if err["count_by_value"]
        else "None (0 errors)"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta http-equiv="refresh" content="{data['refresh_seconds']}" />
  <title>{data['title']} — Runtime Dashboard</title>
  <style>
    * {{ box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    body {{ margin: 0; padding: 14px 20px; background: #0f172a; color: #f8fafc; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 12px; }}
    .header h1 {{ margin: 0; font-size: 19px; color: #38bdf8; }}
    .meta {{ font-size: 11.5px; color: #cbd5e1; display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; }}
    .meta span {{ background: #1e293b; padding: 3px 8px; border-radius: 5px; border: 1px solid #334155; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px; display: flex; flex-direction: column; justify-content: space-between; }}
    .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }}
    .card-title {{ font-size: 13.5px; font-weight: 700; color: #e2e8f0; margin: 0; }}
    .unit {{ font-size: 10.5px; color: #94a3b8; margin-top: 2px; }}
    .metrics-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin: 4px 0; }}
    .metric-box {{ background: #0f172a; padding: 5px 7px; border-radius: 5px; border: 1px solid #1e293b; }}
    .metric-label {{ font-size: 10px; color: #94a3b8; }}
    .metric-val {{ font-size: 13.5px; font-weight: 700; color: #f8fafc; margin-top: 1px; }}
    .threshold {{ margin-top: 6px; padding-top: 6px; border-top: 1px solid #334155; font-size: 11px; color: #fde047; display: flex; justify-content: space-between; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>{data['title']}</h1>
      <div class="meta">
        <span><b>Source:</b> {data['source']}</span>
        <span><b>Time Range:</b> 60 minutes ({data['window_start_utc']} → {data['window_end_utc']})</span>
        <span><b>Auto-Refresh:</b> {data['refresh_seconds']}s</span>
        <span><b>Records in Window:</b> {data['total_records']}</span>
      </div>
    </div>
  </div>

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="card">
      <div>
        <div class="card-header">
          <div>
            <div class="card-title">1. {lat['title']}</div>
            <div class="unit">ID: <code>latency</code> | Unit: <b>{lat['unit']}</b> | Window: <b>60m</b> | Refresh: <b>30s</b></div>
          </div>
          {badge(lat['threshold_ok'])}
        </div>
        <div class="metrics-row">
          <div class="metric-box"><div class="metric-label">P50</div><div class="metric-val">{lat['p50']} ms</div></div>
          <div class="metric-box"><div class="metric-label">P95</div><div class="metric-val">{lat['p95']} ms</div></div>
          <div class="metric-box"><div class="metric-label">P99</div><div class="metric-val">{lat['p99']} ms</div></div>
          <div class="metric-box"><div class="metric-label">TTFT P95</div><div class="metric-val">{lat['ttft_p95']} ms</div></div>
        </div>
        {lat_svg}
      </div>
      <div class="threshold"><span>Threshold Line:</span><b>{lat['threshold']}</b></div>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="card">
      <div>
        <div class="card-header">
          <div>
            <div class="card-title">2. {trf['title']}</div>
            <div class="unit">ID: <code>traffic</code> | Unit: <b>{trf['unit']}</b> | Window: <b>60m</b> | Refresh: <b>30s</b></div>
          </div>
          {badge(trf['threshold_ok'])}
        </div>
        <div class="metrics-row" style="grid-template-columns: repeat(2, 1fr);">
          <div class="metric-box"><div class="metric-label">Total Requests (count)</div><div class="metric-val">{trf['count']} reqs</div></div>
          <div class="metric-box"><div class="metric-label">Rate per Minute</div><div class="metric-val">{trf['rate_per_minute']} req/min</div></div>
        </div>
        {trf_svg}
      </div>
      <div class="threshold"><span>Threshold Line:</span><b>{trf['threshold']}</b></div>
    </div>

    <!-- Panel 3: Errors -->
    <div class="card">
      <div>
        <div class="card-header">
          <div>
            <div class="card-title">3. {err['title']}</div>
            <div class="unit">ID: <code>errors</code> | Unit: <b>{err['unit']}</b> | Window: <b>60m</b> | Refresh: <b>30s</b></div>
          </div>
          {badge(err['threshold_ok'])}
        </div>
        <div class="metrics-row" style="grid-template-columns: repeat(3, 1fr);">
          <div class="metric-box"><div class="metric-label">Error Rate</div><div class="metric-val">{err['error_rate_pct']}%</div></div>
          <div class="metric-box"><div class="metric-label">Retrieval Success</div><div class="metric-val">{err['tool_success_rate_pct']}%</div></div>
          <div class="metric-box"><div class="metric-label">Breakdown</div><div class="metric-val" style="font-size:11px;">{err_breakdown}</div></div>
        </div>
        {err_svg}
      </div>
      <div class="threshold"><span>Threshold Line:</span><b>{err['threshold']}</b></div>
    </div>

    <!-- Panel 4: Cost -->
    <div class="card">
      <div>
        <div class="card-header">
          <div>
            <div class="card-title">4. {cst['title']}</div>
            <div class="unit">ID: <code>cost</code> | Unit: <b>{cst['unit']}</b> | Window: <b>60m</b> | Refresh: <b>30s</b></div>
          </div>
          {badge(cst['threshold_ok'])}
        </div>
        <div class="metrics-row" style="grid-template-columns: repeat(2, 1fr);">
          <div class="metric-box"><div class="metric-label">Total Cost (60m)</div><div class="metric-val">${cst['total']:.5f}</div></div>
          <div class="metric-box"><div class="metric-label">Unit</div><div class="metric-val">usd</div></div>
        </div>
        {cst_svg}
      </div>
      <div class="threshold"><span>Threshold Line:</span><b>{cst['threshold']}</b></div>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="card">
      <div>
        <div class="card-header">
          <div>
            <div class="card-title">5. {tok['title']}</div>
            <div class="unit">ID: <code>tokens</code> | Unit: <b>{tok['unit']}</b> | Window: <b>60m</b> | Refresh: <b>30s</b></div>
          </div>
          {badge(tok['threshold_ok'])}
        </div>
        <div class="metrics-row" style="grid-template-columns: repeat(3, 1fr);">
          <div class="metric-box"><div class="metric-label">sum(tokens_in)</div><div class="metric-val">{tok['tokens_in']}</div></div>
          <div class="metric-box"><div class="metric-label">sum(tokens_out)</div><div class="metric-val">{tok['tokens_out']}</div></div>
          <div class="metric-box"><div class="metric-label">Total</div><div class="metric-val">{tok['total_tokens']}</div></div>
        </div>
        {tok_svg}
      </div>
      <div class="threshold"><span>Threshold Line:</span><b>{tok['threshold']}</b></div>
    </div>

    <!-- Panel 6: Quality -->
    <div class="card">
      <div>
        <div class="card-header">
          <div>
            <div class="card-title">6. {qlt['title']}</div>
            <div class="unit">ID: <code>quality</code> | Unit: <b>{qlt['unit']}</b> | Window: <b>60m</b> | Refresh: <b>30s</b></div>
          </div>
          {badge(qlt['threshold_ok'])}
        </div>
        <div class="metrics-row" style="grid-template-columns: repeat(2, 1fr);">
          <div class="metric-box"><div class="metric-label">mean(quality_score)</div><div class="metric-val">{qlt['mean']}</div></div>
          <div class="metric-box"><div class="metric-label">Unit</div><div class="metric-val">score_0_to_1</div></div>
        </div>
        {qlt_svg}
      </div>
      <div class="threshold"><span>Threshold Line:</span><b>{qlt['threshold']}</b></div>
    </div>
  </div>
</body>
</html>
"""
