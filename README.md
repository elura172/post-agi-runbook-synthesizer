# Post-AGI Runbook Synthesizer

[![CI](https://github.com/elura172/post-agi-runbook-synthesizer/actions/workflows/ci.yml/badge.svg)](https://github.com/elura172/post-agi-runbook-synthesizer/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Theoretical Grounding](https://img.shields.io/badge/Grounding-MIT%206.033%20%7C%206.824-lightgrey.svg)](docs/architecture-rfc.md)

> **Automated SRE incident-to-runbook compiler, synthetic canary generator, and alerting synthesizer for distributed AI infrastructure.**

Post-AGI Runbook Synthesizer transforms static post-mortems and raw streaming telemetry into **executable SRE infrastructure artifacts**. Built to support high-concurrency LLM streaming platforms, model routing meshes, and distributed inference topologies.

---

## 🚀 Key Capabilities

- **8-Stage Cognitive SRE Pipeline:** Translates raw incident reports through telemetry pressure, topology modeling, circuit breaking, deterministic remediation, adversarial falsification, customer comms, historical continuity, and multi-artifact orchestration.
- **5-Artifact Production Bundle:** Automatically generates:
  1. `runbook.md` — Executable SRE runbook with step-by-step shell commands, verification checks, and explicit rollbacks.
  2. `alerts.yaml` — Valid Prometheus Alertmanager alerting rules tuned to the incident's degradation signature.
  3. `test_canary_probe.py` — Standalone, runnable Pytest synthetic canary and chaos invariant suite.
  4. `customer_advisory.md` — Blameless, SLA-grounded enterprise customer advisory for statuspage broadcasting.
  5. `incident_ledger.json` — Structured post-mortem record indexed into a persistent SQLite ledger with anti-recurrence fingerprinting.
- **Companion to OpenAI Stream Sentinel:** Ingests markdown incident reports from [`openai-stream-sentinel`](https://github.com/elura172/openai-stream-sentinel) directly, closing the loop from client-side streaming diagnostics to production SRE remediation.
- **3-Verb CLI Workflow:**
  - `runbook synthesize`: Compile 5-artifact bundle from an incident file or built-in reference scenario.
  - `runbook verify`: Execute the synthetic canary probe suite against live endpoints or offline simulations.
  - `runbook history`: Query the historical post-mortem ledger to identify recurrence patterns and track MTTR.

---

## 🏗️ The 8-Stage Cognitive SRE Pipeline

```
┌────────────────────────────────────────────────────────┐
│               Raw Incident / RCA Report                │
│    (Sentinel Markdown, Structured JSON, or Preset)     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 1. Telemetry Pressure (TTFT, P95 Jitter, SLI Burn)    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. Topology Model (Service Graph & Blast Radius)       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. Adaptive Damping (Circuit Breaker & Backoff Jitter) │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. Remediation Synthesizer (Commands & Rollbacks)      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 5. Adversarial Falsifier (Pytest Canary & Chaos Test)  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 6. Stakeholder Comms (Customer Statuspage Advisory)   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 7. Post-Mortem Ledger (SQLite Anti-Recurrence Hash)    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 8. Unified Orchestrator (5-Artifact Compilation)      │
│  [runbook.md] [alerts.yaml] [test_canary_probe.py]    │
│       [customer_advisory.md] [incident_ledger.json]    │
└────────────────────────────────────────────────────────┘
```

For the full theoretical specification, see [RFC-001: The 8-Stage Cognitive SRE Incident Pipeline](docs/architecture-rfc.md).

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/elura172/post-agi-runbook-synthesizer.git
cd post-agi-runbook-synthesizer

# Install dependencies using uv
uv sync
```

---

## ⚡ Quickstart

### 1. Synthesize an SRE Bundle from a Built-in Preset

```bash
uv run runbook synthesize --incident proxy_buffer_bloat --output ./artifacts/INC-4FB1577E
```

Output:
```
Loaded built-in incident preset: `proxy_buffer_bloat`
╭──────────────── SRE Cognitive Pipeline Completed (8 Stages) ─────────────────╮
│ Incident Successfully Synthesized                                            │
│ ID: INC-4FB1577E  |  Domain: PROXY_BUFFER_BLOAT                              │
│ Severity: SEV-3 (Moderate / Latency Spike)  |  Target Model: gpt-4o          │
│ Theoretical Grounding: MIT 6.033 (Computer System Engineering)               │
╰──────────────────────────────────────────────────────────────────────────────╯
...
Compiled SRE Artifact Bundle:
- ./artifacts/INC-4FB1577E/runbook.md
- ./artifacts/INC-4FB1577E/alerts.yaml
- ./artifacts/INC-4FB1577E/test_canary_probe.py
- ./artifacts/INC-4FB1577E/customer_advisory.md
- ./artifacts/INC-4FB1577E/incident_ledger.json
```

### 2. Synthesize from an OpenAI Stream Sentinel RCA Report

```bash
uv run runbook synthesize --incident fixtures/sample-sentinel-incident.md
```

### 3. Verify System Invariants with the Synthesized Canary Probe

```bash
uv run runbook verify ./artifacts/INC-4FB1577E/test_canary_probe.py
```

*Note: If `OPENAI_API_KEY` is set, the canary executes a live streaming probe against `api.openai.com`. If unset, it executes deterministic offline simulation probes.*

### 4. Query Historical Incidents in the SQLite Ledger

```bash
uv run runbook history --domain proxy_buffer_bloat
```

---

## 🔬 Built-In Reference Scenarios

| Scenario Preset | Failure Domain | Impacted Layer | Primary Architectural Fault |
|---|---|---|---|
| `proxy_buffer_bloat` | `PROXY_BUFFER_BLOAT` | Enterprise Edge / WAF | Reverse proxy collects chunked SSE transfer frames into bursty TCP packets. |
| `inference_shard_stall` | `INFERENCE_SHARD_STALL` | Inference GPU Shards | Paged attention memory exhaustion spikes TTFT to >14 seconds. |
| `rate_limit_stampede` | `RATE_LIMIT_STAMPEDE` | Redis Cluster Rate Limiter | Partition split-brain causes false-positive 429 storm on enterprise accounts. |

---

## 🧪 Testing

Run the full automated test suite (13 tests including end-to-end canary execution):

```bash
uv run pytest -v
```

---

## 📜 MIT OpenCourseWare Grounding

- **MIT 6.033 (Computer System Engineering):** Modularity, fault isolation, network buffering, and Saltzer & Reed's End-to-End Argument.
- **MIT 6.824 (Distributed Systems):** Consistency models, partitioning, KV-cache thrashing, and consensus during network partitions.
- **RFC 3393:** IP Packet Delay Variation Metric.
- **RFC 5321:** Exponential backoff and retry scheduling with decorrelated jitter.

---

## 📄 License

MIT License — Copyright (c) 2026 Paul Trafford (`elura172`).
