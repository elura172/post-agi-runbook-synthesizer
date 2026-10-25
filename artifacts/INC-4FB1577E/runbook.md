# Operational SRE Runbook: INC-4FB1577E
> **Failure Domain:** `PROXY_BUFFER_BLOAT` | **Severity:** `SEV-3 (Moderate / Latency Spike)` | **Target Model:** `gpt-4o`
> **Theoretical Grounding:** MIT 6.033 (Computer System Engineering: Network Buffering & The End-to-End Argument)

## 1. Incident Overview & Blast Radius
- **Summary:** Severe token inter-arrival jitter detected. Chunks are generated nominally by OpenAI clusters but are buffered by an intermediate enterprise firewall or reverse proxy before delivering in bursty TCP frames.
- **Primary Fault Node:** `edge_proxy`
- **Impacted Layer:** `Enterprise Edge / WAF Proxy`
- **Blast Radius:** `edge_proxy`, `client_app`
- **Invariant Violated:** *End-to-End Streaming Invariant: Proxy must deliver SSE byte chunks immediately without HTTP response-body buffering (X-Accel-Buffering: no).*

## 2. Telemetry & SLI Degradation Profile
| SLI Metric | Target SLO | Observed Value | 1h Burn Rate | Budget Exhaustion | Status |
|---|---|---|---|---|---|
| `streaming_ttft_p95_ms` | `600.0` | `262.1` | `1.0x` | `N/A` | **NOMINAL** |
| `streaming_chunk_jitter_p95_ms` | `30.0` | `125.4` | `10.45x` | `4.6h` | **CRITICAL BREACH** |
| `streaming_http_5xx_error_rate` | `0.01` | `0.0` | `1.0x` | `N/A` | **NOMINAL** |

## 3. Circuit Breaker & Adaptive Damping Policy
- **Failure Trip Threshold:** `5 consecutive errors`
- **Recovery Timeout Window:** `30.0s`
- **Half-Open Concurrency:** `3 probe requests`
- **Backoff Strategy:** `decorrelated_full_jitter`
- **Sample Retry Backoff Progression (ms):** `[307.8, 521.7, 772.4, 1039.7, 706.1]`

## 4. Executable Remediation Procedures
### Step 1: Audit Ingress & Reverse Proxy Response Buffering Headers
```bash
curl -s -D - -o /dev/null -N https://api.openai.com/v1/models -H 'Authorization: Bearer $OPENAI_API_KEY' | grep -iE '(x-accel-buffering|transfer-encoding)'
```
- **Expected Output:** `transfer-encoding: chunked`
- **Verification Check:** Verify that chunked transfer encoding is preserved end-to-end without buffering headers.

### Step 2: Apply Dynamic Nginx / Envoy Streaming Configuration Patch
```bash
cat << 'EOF' > /tmp/stream_proxy_patch.conf
location /v1/chat/completions {
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_set_header X-Accel-Buffering 'no';
}
EOF
sudo cp /tmp/stream_proxy_patch.conf /etc/nginx/conf.d/streaming.conf
```
- **Expected Output:** `Config written to /etc/nginx/conf.d/streaming.conf`
- **Verification Check:** Run `nginx -t` to validate syntax prior to live reload.
- **Rollback Command:**
```bash
sudo rm -f /etc/nginx/conf.d/streaming.conf && sudo nginx -s reload
```

### Step 3: Gracefully Reload Reverse Proxy Configuration
```bash
sudo nginx -s reload || curl -X POST http://127.0.0.1:9901/drain_listeners
```
- **Expected Output:** `nginx: configuration file /etc/nginx/nginx.conf test is successful`
- **Verification Check:** Verify 0 dropped TCP connections in edge proxy active connection counter.

### Step 4: Verify Chunk Cadence Recovery via Sentinel Streaming Probe
```bash
sentinel diagnose --model gpt-4o --samples 15 || python -m post_agi_runbook_synthesizer.cli verify ./test_canary_probe.py
```
- **Expected Output:** `STREAM_HEALTHY / P95 jitter < 30ms`
- **Verification Check:** Assert TTFT < 600ms and inter-chunk jitter P95 < 30ms.

## 5. Adversarial Canary Verification
Execute the companion synthetic canary probe to verify system recovery prior to closing the incident:
```bash
pytest -v test_canary_probe.py
```

## 6. Historical Context & Anti-Recurrence
- **Recurrence Fingerprint:** `baf9b33c1a3d85c7`
- No identical prior incidents indexed in local ledger. Baseline record initialized.
