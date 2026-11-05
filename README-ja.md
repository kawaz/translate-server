# translate-server

ローカルで動く英日翻訳サーバ。PFN の翻訳特化 LLM [PLaMo 3 Translate 0.8B](https://huggingface.co/pfnet/plamo-3-translate-0.8b-GGUF) (公式 GGUF) を [llama.cpp](https://github.com/ggml-org/llama.cpp) の `llama-server` で動かし、その OpenAI 互換 API をそのまま出す。常駐はせず、caddy-app-proxy が最初のアクセスで起動する。

- 16 段落 (技術文、コード識別子・日英混在) を 1.4 秒 (4 並列)、1 段落 0.18 秒。Apple M1 Max での実測
- コード (バッククォート内・パス・コマンド) と日本語段落をそのまま保つ。既存の日本語文を軽く言い換えることがある
- Python 不要。Homebrew の `llama.cpp` と 0.57 GB の GGUF だけ

設計は [docs/DESIGN-ja.md](docs/DESIGN-ja.md)、採否の記録は [docs/decisions/](docs/decisions/INDEX.md)、計測は [docs/findings/](docs/findings/2026-11-05-engine-benchmark.md)。

## セットアップ

```sh
just setup   # brew install llama.cpp、モデルを ${XDG_CACHE_HOME:-~/.cache}/translate-server/models/ に取得
just run     # 127.0.0.1:8087 でフォアグラウンド起動
just smoke   # 1 文翻訳して API を確認
```

caddy-app-proxy 経由では `https://translate.kawaz-mbp.kawaz.jp/` で、起動していなければ最初のアクセスで `ondemand/translate-server-ensure.sh` が起動する (初回はモデルのロードで数秒待つ)。

## API

llama-server の OpenAI 互換 API がそのまま使える。翻訳のオプションは `chat_template_kwargs` で渡す (モデルの chat template が解釈する)。

```sh
curl -s https://translate.kawaz-mbp.kawaz.jp/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "plamo-3-translate",
  "messages": [{"role": "user", "content": "The helper reads stdin line by line. ここで問題になるのは EOF の扱い。"}],
  "chat_template_kwargs": {"target_lang": "ja", "form": "plain"},
  "temperature": 0, "max_tokens": 1024
}'
```

| `chat_template_kwargs` | 内容 |
|---|---|
| `target_lang` | 訳先 (`ja`)。`source_lang` は省略すると自動判定 |
| `form` | `plain` (常体、〜だ / 〜である) か `polite` (敬体、〜です / 〜ます)。日本語訳のみ |
| `glossary` | `[{"source": "serial", "target": "直列"}]` の配列。英語のまま残したい語は `source` と `target` を同じにする |
| `context` | 内容理解のためのヒント (周辺の文章、分野)。文体の指示としては効かない |

直前の原文・訳文ペアを `messages` に `user` / `assistant` で積むと、その続きとして一貫した訳になる (history)。

- 1 段落 = 1 リクエストで送ると並列が効き、段落ごとに逐次表示できる。空行区切りの段落単位で十分で、文単位にすると原文と訳文の 1:1 対応が得られる
- 数千トークンまでなら丸ごと 1 リクエストでも段落の脱落・結合は起きなかった。上限は入出力合計 32,768 トークン。全文が返るまで最初の 1 文字も出ない
- `temperature: 0` で決定的。同じ入力は同じ訳文になるので結果はキャッシュできる
- 英数字と和文の間の空白は入らない。必要なら呼び出し側で後処理する

## ライセンス

このリポジトリは MIT License。モデルは [PLaMo コミュニティライセンス](https://plamo.preferredai.jp/info/plamo-community-license) (私的利用・非商用は登録不要、商用は条件あり)。
