# DR-0004: モデルは XDG cache に置き、無ければ取得する

- Status: Accepted
- Date: 2026-11-05

## Context

モデル (GGUF 0.57 GB) と `chat_template.jinja` は Hugging Face からいつでも再取得できる。置き場の判定基準は reference の `app-file-placement` (設定 / データ / 状態 / キャッシュの区別) に従う。

## Decision

`${XDG_CACHE_HOME:-~/.cache}/translate-server/models/<repo 名>/` に置く。`bin/translate-server` は起動時に無ければ取得し (`.part` に落として rename)、消えていても次の起動で戻る。ログは `${XDG_STATE_HOME:-~/.local/state}/translate-server/`。設定ファイルとデータは持たない。

## 不採用案と理由

| 案 | 不採用理由 |
|---|---|
| `${XDG_DATA_HOME}` (data) | data は「消えたら困る自前のもの」の置き場。再取得できるモデルを置くと、cache 掃除の対象から外れて 0.5 GB が残り続ける |
| リポ内 (`models/` を gitignore) | リポの場所に依存し、複数の checkout で重複する |
| Hugging Face の既定キャッシュ (`~/.cache/huggingface/`) | `hf` CLI (Python) を要求する。curl で足りる |

## Consequences

- 初回起動はダウンロード時間 (回線次第で数十秒〜数分) が乗る。`just setup` で先に取れる
- モデルを変える時は `TRANSLATE_SERVER_MODEL_REPO` / `TRANSLATE_SERVER_MODEL_FILE` で指定し、置き場は repo 名ごとに分かれる

## 関連

- [DR-0003](./DR-0003-on-demand-via-caddy.md)
