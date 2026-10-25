# OpenAI Customer Advisory — INC-4FB1577E

**Status:** Under Investigation / Active Mitigation Applied  
**Impacted Surface:** OpenAI API Streaming & Model Inference (gpt-4o)  
**Severity:** SEV-3 (Moderate / Latency Spike)  

### Executive Summary
Severe token inter-arrival jitter detected. Chunks are generated nominally by OpenAI clusters but are buffered by an intermediate enterprise firewall or reverse proxy before delivering in bursty TCP frames.

### Immediate Actionable Workarounds for Engineering Teams
- Configure enterprise egress proxy or WAF (e.g. Nginx, Envoy, Cloudflare, Zscaler) to disable response body buffering for `api.openai.com`.
- Ensure client requests include `X-Accel-Buffering: no` and that intermediate hops preserve `Transfer-Encoding: chunked`.
- Audit TCP window scaling and MTU settings on enterprise perimeter gateways to prevent packet aggregation.

*Our Technical Support Engineering team has validated this mitigation. If you require dedicated assistance verifying proxy bypass rules or tuning SDK retry dynamics, contact support@openai.com referencing this incident ID.*
