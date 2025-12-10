# LLM integration plan (local Apple + native Swift sidecar + remote GPU)

- Goal: run multiple LLM backends and route per request: (1) on-device Apple Foundation Model via Swift sidecar; (2) on-device MLX/Apple model from Python; (3) remote Llama/Qwen served from Spark GPU nodes (vLLM/Triton). A duplex AFM bridge is available over WebSocket for Vision clients.
- Routing: expose a tiny dispatcher (e.g., header or config `native|local|remote|auto`) over a common `LLMClient` interface so FastAPI callers don’t care about the backend.
- Native backend: Swift FoundationModels sidecar listening on `http://localhost:8081/generate` (or `NATIVE_LLM_URL`), accepting `{model, prompt, maxTokens, temperature, stop?}` and returning `{text, usage}`; Python calls this via `NativeSidecarClient`.
- Local backend: use MLX/MLX-LM to load an Apple-compatible model from disk; keep prompts local for privacy; quantize (int4/int8) to stay within RAM.
- Remote backend: stand up vLLM for Llama/Qwen on Spark GPUs; expose `/generate` over HTTP with auth; prefer fp8/int8 and continuous batching for throughput.
- AFM WebSocket bridge: `/afm/bridge` for Vision/Swift clients to register and receive `afm_request` messages, replying with `afm_result`; REST `/afm/request` publishes requests and waits for replies.
- Health/fallback: `/afm/request` caps concurrent native requests, checks recent client health (fps/thermal/busy) and, if unavailable/unhealthy, falls back to remote LLM (if configured).
- Dev steps:
  1) `services/llm/base.py` with request/response dataclasses and `LLMClient` protocol.
  2) `services/llm/native_sidecar.py` for Swift FoundationModels sidecar (`NATIVE_LLM_URL`, `NATIVE_LLM_MODEL`, `NATIVE_LLM_TOKEN`).
  3) `services/llm/local_apple.py` for MLX-based local models (`APPLE_LLM_MODEL`, dtype/max tokens config).
  4) `services/llm/remote_vllm.py` for Spark-hosted Llama/Qwen (`REMOTE_LLM_URL`, `REMOTE_LLM_MODEL`, `REMOTE_LLM_TOKEN`).
  5) Dispatcher + API wiring (console summary) to pick backend via header/body/config.
  6) Duplex bridge: `api/afm_bridge.py` exposes `/afm/request` (REST) and `/afm/bridge` (WS) so backend can send AFM requests to Vision clients and receive results.
