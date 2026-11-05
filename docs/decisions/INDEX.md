# Decision Records 一覧

Status は各 DR ファイルの `Status:` 行が正本。

状態は絵文字とラベルだけ。日付・裁定の内訳は各 DR 本文に書く。

- `💭 提案`: Decision がまだ裁定されていない。実装に着手しない (本文の `Status: Proposed`)
- `✅ 実装済`: Decision の全部に実装エビデンスがある
- `🟡 部分実装`: 一部のみ実装
- `⬜ 未実装`: 裁定済みで設計のみ、実装エビデンスなし (着手してよい)
- `🚧 進行中`: 実装の途中
- `N/A`: 実装対象でない (命名・思想・プロセス等)
- `❌ 撤退`: 撤退判断済

| DR | 状態 | 説明 |
|---|---|---|
| [DR-0001](DR-0001-engine-llama-cpp.md) | ✅ 実装済 | エンジンは llama.cpp + PLaMo 3 Translate 0.8B の公式 GGUF (`bin/translate-server`) |
| [DR-0002](DR-0002-passthrough-api.md) | ✅ 実装済 | API はエンジンの OpenAI 互換 API を素通し。ラッパを持たない |
| [DR-0003](DR-0003-on-demand-via-caddy.md) | 🟡 部分実装 | 常駐せず caddy-app-proxy のオンデマンド起動 (`ondemand/translate-server-ensure.sh` はあり、Caddyfile への登録は caddy-app-proxy 側) |
| [DR-0004](DR-0004-model-in-xdg-cache.md) | ✅ 実装済 | モデルは XDG cache に置き、無ければ取得する |
