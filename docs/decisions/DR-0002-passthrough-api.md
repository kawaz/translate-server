# DR-0002: API はエンジンの OpenAI 互換 API を素通しする

- Status: Accepted
- Date: 2026-11-05

## Context

利用側 (claude-ccmsg の daemon と webui、他のローカルアプリ) は「文字列を渡して訳文を受け取る」だけでよい。`llama-server` は `/v1/chat/completions` を出し、翻訳のオプション (`target_lang` / `form` / `glossary` / `context`) はモデルの chat template が `chat_template_kwargs` から解釈する。

## Decision

このリポは API を定義しない。利用側は `llama-server` の OpenAI 互換 API をそのまま叩く。URL と `model` 名 (`plamo-3-translate`) だけがこのリポの契約。

## 不採用案と理由

| 案 | 不採用理由 |
|---|---|
| 専用の `POST /translate` (`{texts: [...], target, form}` で配列を返す) を前段に置く | 維持するコードと、利用側が覚える API が 1 つ増える。段落ごとに並列で送る方が逐次表示に向き、配列 API の利点が無い。webui から直接 fetch する時も素の API で足りる |
| 結果キャッシュをサーバ側に持つ | `temperature: 0` で決定的なので、キャッシュは利用側が自分の表示単位で持つ方が無駄が無い |
| 文の分割やプレースホルダをサーバ側で行う | 分割単位は利用側の表示設計で決まる (段落か文か)。サーバが決めると利用側ごとの要件に合わない |

## Consequences

- エンジンを差し替える時は OpenAI 互換 API を持つものに限る
- 利用側は `chat_template_kwargs` の中身 (モデル依存) を知る必要がある。README に表で示す

## 関連

- [DR-0001](./DR-0001-engine-llama-cpp.md)
