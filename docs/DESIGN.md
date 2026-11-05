# translate-server design

## Domain

A shared service for apps inside the tailnet (for example the thinking view of claude-ccmsg) to translate English into Japanese without using the cloud. Quality and speed are determined by the model (PLaMo 3 Translate) and the engine (llama.cpp); this repository is only responsible for keeping that reachable at one stable URL.

### Goals

- Translate technical text (code identifiers, paths, mixed Japanese, line breaks) without breaking it, at about 0.2 s per paragraph
- Callers need neither cloud API keys nor a Python environment. One HTTPS URL is enough

### Things we do not add

- A custom API or wrapper. The engine's OpenAI-compatible API is passed through as is (a wrapper adds code to maintain and one more thing for callers to learn)
- A resident process. 1.3 GB must not stay allocated while unused
- Configuration files. Startup options are the defaults in `bin/translate-server` plus environment variables

### Out of scope

- Reachability and TLS: caddy-app-proxy's responsibility (tailnet only, HTTPS termination)
- Sentence splitting, placeholders, spacing post-processing, result caching: the caller's responsibility. The API translates the string it is given

## Architecture

```
caller ── https://translate.kawaz-mbp.kawaz.jp/v1/chat/completions
          │ caddy-app-proxy (TLS termination, tailnet_only)
          │  on 502: exec ondemand/translate-server-ensure.sh, then 302 to the same URL
          ▼
      bin/translate-server (foreground) = exec llama-server -m <gguf> --port 8087 ...
          │ fetches the model and chat_template.jinja from Hugging Face when missing
          ▼
      ${XDG_CACHE_HOME:-~/.cache}/translate-server/models/plamo-3-translate-0.8b-GGUF/
```

| Component | Responsibility |
|---|---|
| `bin/translate-server` | Fetch the model when missing and start `llama-server`. Arguments are only port and host; the rest comes from environment variables |
| `ondemand/translate-server-ensure.sh` | Idempotent start script following caddy-app-proxy's convention. Returns once `/health` reports `"ok"` |
| `llama-server` | Inference and the OpenAI-compatible API. Homebrew's `llama.cpp` |
| Model | `Q4_K_M` from `pfnet/plamo-3-translate-0.8b-GGUF` with its bundled `chat_template.jinja`. Translation options (`target_lang` / `form` / `glossary` / `context`) are interpreted by this template from `chat_template_kwargs` |

### File placement

- Model: cache (`${XDG_CACHE_HOME:-~/.cache}/translate-server/`). It can be re-fetched, so it may be deleted
- Logs: state (`${XDG_STATE_HOME:-~/.local/state}/translate-server/server.log`)
- Configuration and data: none

### Startup

`llama-server` listens on TCP first and loads the model afterwards; it accepts requests once `/health` returns `{"status":"ok"}`. The ensure script therefore waits on `/health`, not on the TCP listen (returning on listen leads to 503 or 400 after Caddy's 302). Cold start is about 7 s on an M1 Max with the model already fetched.

## Key decisions

- Engine: llama.cpp with the official GGUF ([DR-0001](decisions/DR-0001-engine-llama-cpp.md))
- API: pass the engine's API through ([DR-0002](decisions/DR-0002-passthrough-api.md))
- No resident process; on-demand start through caddy-app-proxy ([DR-0003](decisions/DR-0003-on-demand-via-caddy.md))
- Model in the XDG cache ([DR-0004](decisions/DR-0004-model-in-xdg-cache.md))

## Related documents

- [Measurements](findings/2026-11-05-engine-benchmark.md)
- caddy-app-proxy's on-demand convention (README of that repository)
