# translate-server

A local English-to-Japanese translation server. It runs PFN's translation-specialized LLM [PLaMo 3 Translate 0.8B](https://huggingface.co/pfnet/plamo-3-translate-0.8b-GGUF) (official GGUF) on [llama.cpp](https://github.com/ggml-org/llama.cpp)'s `llama-server` and exposes its OpenAI-compatible API as is. It is not a resident daemon; caddy-app-proxy starts it on the first request.

- 16 technical paragraphs (code identifiers, mixed Japanese) in 1.4 s with 4 concurrent requests, 0.18 s per paragraph. Measured on an Apple M1 Max
- Code (backquoted spans, paths, commands) and Japanese paragraphs are preserved. Existing Japanese sentences may be slightly rephrased
- No Python. Only Homebrew's `llama.cpp` and a 0.57 GB GGUF file

Design: [docs/DESIGN.md](docs/DESIGN.md). Decisions: [docs/decisions/](docs/decisions/INDEX.md). Measurements: [docs/findings/](docs/findings/2026-11-05-engine-benchmark.md).

## Setup

```sh
just setup   # brew install llama.cpp, fetch the model into ${XDG_CACHE_HOME:-~/.cache}/translate-server/models/
just run     # serve on 127.0.0.1:8087 in the foreground
just smoke   # translate one sentence to check the API
```

Through caddy-app-proxy the server is at `https://translate.kawaz-mbp.kawaz.jp/`; if it is not running, the first request runs `ondemand/translate-server-ensure.sh` (the first request waits a few seconds for the model to load).

## API

The OpenAI-compatible API of llama-server is used directly. Translation options go in `chat_template_kwargs`, which the model's chat template interprets.

```sh
curl -s https://translate.kawaz-mbp.kawaz.jp/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "plamo-3-translate",
  "messages": [{"role": "user", "content": "The helper reads stdin line by line. ここで問題になるのは EOF の扱い。"}],
  "chat_template_kwargs": {"target_lang": "ja", "form": "plain"},
  "temperature": 0, "max_tokens": 1024
}'
```

| `chat_template_kwargs` | Meaning |
|---|---|
| `target_lang` | Target language (`ja`). `source_lang` is auto-detected when omitted |
| `form` | `plain` (だ / である) or `polite` (です / ます). Japanese output only |
| `glossary` | Array of `{"source": "serial", "target": "直列"}`. To keep a term in English, set `source` and `target` to the same value |
| `context` | Hints for understanding the text (surrounding text, domain). It does not control style |

Push previous source/translation pairs into `messages` as `user` / `assistant` turns to get a consistent continuation (history).

- One paragraph per request allows parallelism and incremental display. Blank-line-separated paragraphs are enough; sentence-level requests additionally give a 1:1 mapping between source and translation
- Up to a few thousand tokens, a whole document in one request did not drop or merge paragraphs. The limit is 32,768 tokens for input and output combined. Nothing is returned until the whole translation is done
- `temperature: 0` makes the output deterministic, so results can be cached
- No spaces are inserted between Latin and Japanese characters; post-process on the caller side if needed

## License

This repository is under the MIT License. The model is under the [PLaMo Community License](https://plamo.preferredai.jp/info/plamo-community-license-en) (personal and non-commercial use without registration; commercial use has conditions).
