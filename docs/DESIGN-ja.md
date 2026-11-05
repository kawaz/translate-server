# translate-server の設計

## ドメイン

tailnet 内の各アプリ (claude-ccmsg の thinking 表示など) が、クラウドを使わずに英文を日本語に訳すための共有サービス。翻訳の品質と速度はモデル (PLaMo 3 Translate) とエンジン (llama.cpp) が決め、このリポは「それをいつでも同じ URL で叩ける状態にする」ことだけを担う。

### 目的

- 技術文 (コード識別子・パス・日英混在・改行) を壊さずに、1 段落 0.2 秒程度で訳す
- 利用側はクラウド API 鍵も Python 環境も持たない。HTTPS の URL 1 つで足りる

### 増やさないもの

- 独自の API やラッパ。エンジンの OpenAI 互換 API を素通しする (ラッパを足すと維持するコードと利用側の学習対象が増える)
- 常駐プロセス。使っていない間に 1.3 GB を占有させない
- 設定ファイル。起動オプションは `bin/translate-server` の既定値と環境変数だけ

### 扱わないもの

- 到達制限と TLS: caddy-app-proxy の責務 (tailnet 内のみ、HTTPS 終端)
- 文の分割、プレースホルダ、空白の後処理、結果キャッシュ: 利用側の責務。API は与えた文字列をそのまま訳す

## アーキテクチャ

```
利用側 ── https://translate.kawaz-mbp.kawaz.jp/v1/chat/completions
          │ caddy-app-proxy (TLS 終端、tailnet_only)
          │  502 なら ondemand/translate-server-ensure.sh を exec → 302 で同じ URL へ
          ▼
      bin/translate-server (フォアグラウンド) = exec llama-server -m <gguf> --port 8087 ...
          │ モデルと chat_template.jinja が無ければ Hugging Face から取得
          ▼
      ${XDG_CACHE_HOME:-~/.cache}/translate-server/models/plamo-3-translate-0.8b-GGUF/
```

| コンポーネント | 責務 |
|---|---|
| `bin/translate-server` | モデルの取得 (無ければ) と `llama-server` の起動。引数はポートとホストだけ、残りは環境変数 |
| `ondemand/translate-server-ensure.sh` | caddy-app-proxy の規約に従う冪等な起動スクリプト。`/health` が `"ok"` になるまで待って返す |
| `llama-server` | 推論と OpenAI 互換 API。Homebrew の `llama.cpp` |
| モデル | `pfnet/plamo-3-translate-0.8b-GGUF` の `Q4_K_M` と同梱の `chat_template.jinja`。翻訳オプション (`target_lang` / `form` / `glossary` / `context`) はこの template が `chat_template_kwargs` から解釈する |

### 置き場

- モデル: cache (`${XDG_CACHE_HOME:-~/.cache}/translate-server/`)。再取得できるものなので消えてよい
- ログ: state (`${XDG_STATE_HOME:-~/.local/state}/translate-server/server.log`)
- 設定・データ: 持たない

### 起動

`llama-server` は TCP で listen した後にモデルを読み込み、`/health` が `{"status":"ok"}` を返した時点でリクエストを受け付ける。ensure スクリプトは listen でなく `/health` で待つ (listen で返すと Caddy の 302 の後に 503 や 400 になる)。cold start は約 7 秒 (M1 Max、モデル取得済み)。

## 主要な設計判断

- エンジンは llama.cpp + 公式 GGUF ([DR-0001](decisions/DR-0001-engine-llama-cpp.md))
- API はエンジンのものを素通し ([DR-0002](decisions/DR-0002-passthrough-api.md))
- 常駐せず caddy-app-proxy のオンデマンド起動 ([DR-0003](decisions/DR-0003-on-demand-via-caddy.md))
- モデルは XDG cache ([DR-0004](decisions/DR-0004-model-in-xdg-cache.md))

## 関連ドキュメント

- [計測](findings/2026-11-05-engine-benchmark.md)
- caddy-app-proxy の on-demand の規約 (同リポ README)
