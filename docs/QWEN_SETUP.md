# Qwen configuration

Use the AILT9019 Group 19 sponsored Alibaba Cloud Bailian access with `qwen3.6-flash`.
The shared course allocation is 25,000 credits and this key expires on
19 November 2026. Keep the key within the group and use it only for course work.
Read the teaching team's Ed announcement for the full budget and tool guidance.
The sponsored endpoint lists `qwen3.6-flash`; the older `qwen-flash` identifier
returns `model_not_found` on this endpoint. Historical evaluations used the old
model and do not establish accuracy for the new model.

Copy `.env.example` to ignored `.env` for local use. On Render set:

- `LLM_API_KEY`: the private Group 19 key supplied by the teaching team
- `LLM_BASE_URL=https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`
- `LLM_MODEL=qwen3.6-flash`
- `LLM_PROVIDER=Qwen`
- `LLM_TIMEOUT_SECONDS=30`
- `LLM_REQUESTS_PER_MINUTE=10`

Use the OpenAI-compatible endpoint above; this application does not use the
Anthropic endpoint. Do not append `/chat/completions`; the adapter adds it.
Use the sponsored key with its matching endpoint. The key must permit the exact model `qwen3.6-flash`. If an
IP allowlist is enabled, allow the deployment's outbound IPs as well.

The adapter disables thinking and requests JSON Object output. Quote capitalization
is restored to the exact source; altered wording and unknown IDs are rejected. An HTTP 403
with “Access denied by API-Key restrictions” indicates key permissions or
restrictions, not a matching failure. Never commit the exported credential CSV,
`.env`, or deployment secrets.

Avoid high concurrency: the quota is shared by the group and excessive
concurrency can suspend the key. Keep the existing 10 requests/minute limit;
coordinate usage across group tools. Contact the teaching team for a top-up or
replacement if the key is exhausted, expired, or exposed.

After saving settings, deploy/restart the application, choose **AI matching**,
and try `dark insulated flask with a silver screw top`. With the initial
fictional catalogue, LF-001 should be returned with quotations from its record.
Try `purple telescope` for a no-match example. These are demonstration probes,
not independent evidence of general accuracy.

Run `python -m evaluation.run --mode ai` for the synthetic benchmark.
The benchmark makes real API requests and uses the configured rate limit.
It does not mutate the inventory or send photos or staff credentials.

Sources: [First API call](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen),
[Structured output](https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output).
