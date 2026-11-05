# DR-0001: エンジンは llama.cpp + 公式 GGUF

- Status: Accepted
- Date: 2026-11-05

## Context

claude-ccmsg の thinking 翻訳は macOS の Translation.framework を使っていて、16 段落に 29 秒 (OS 側で直列化され並列が効かない) かかり、固有名詞 (Claude → クラウディア) やインラインコードを壊す。候補を同じ 16 段落で測った ([findings](../findings/2026-11-05-engine-benchmark.md))。

## Decision

PFN の PLaMo 3 Translate 0.8B の公式 GGUF (`Q4_K_M`) を、Homebrew の `llama.cpp` に含まれる `llama-server` で動かす。モデルカードの指定どおり `--chat-template-file chat_template.jinja --no-prefill-assistant` を付け、`--parallel 4` で同時 decode する。

## 不採用案と理由

| 案 | 不採用理由 |
|---|---|
| 同じモデルの MLX-4bit を `mlx-lm` の `serve.py` で動かす | Python の venv (約 1 GB) と依存が要る。速度は llama.cpp の半分 (16 段落 6.0 秒対 3.0 秒) で品質は同等 |
| Translation.framework を続ける | 固有名詞とインラインコードを壊し、並列化できない。20 倍遅い |
| クラウド LLM (`claude -p` 経由の sol / haiku) | 16 並列で 7 秒と 5 倍遅く、クラウド依存と定額枠の消費が付く。品質は sol が最も安定だが日本語文中の英単語を訳す |
| 2B 以上のモデル | 0.8B の 2 倍遅く、既知の 3 観点での品質差が無い。必要になれば `TRANSLATE_SERVER_MODEL_*` で差し替える |

## Consequences

- 依存は `brew install llama.cpp` と 0.57 GB の GGUF だけ。Python を持たない
- 既存の日本語文を軽く言い換える癖は残る。利用側で文単位に分け、ラテン文字を含まない文を送らなければ消せる
- llama.cpp の版が上がって `chat_template_kwargs` の扱いが変わると動かなくなりうる。`just smoke` で検知する

## 関連

- [DR-0002](./DR-0002-passthrough-api.md)
- [findings](../findings/2026-11-05-engine-benchmark.md)
