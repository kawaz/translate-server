# DR-0003: 常駐せず caddy-app-proxy のオンデマンド起動に乗せる

- Status: Accepted
- Date: 2026-11-05

## Context

`llama-server` は常駐すると約 1.3 GB (0.8B、Q4_K_M) を占有する。翻訳は会話中にまとまって来て、それ以外は来ない。caddy-app-proxy には、`reverse_proxy` の 502 を `handle_errors` で拾って冪等な起動スクリプトを `exec` し、302 で同じ URL に戻す仕組み (caddy-exec) がある。

## Decision

常駐させない。`ondemand/translate-server-ensure.sh` を caddy-app-proxy の規約 (listen 済みなら何もしない、`mkdir` lock で 1 本だけ起動、受け付け可能になるまで待って返す) で書き、Caddyfile から絶対パスで指す。受け付け可能の判定は TCP の listen でなく `/health` が `"ok"` を返すことで行う (`llama-server` は listen 後にモデルを読み込む)。

## 不採用案と理由

| 案 | 不採用理由 |
|---|---|
| launchd で常駐 | 使っていない間も 1.3 GB を占有する。cold start は約 7 秒で、会話の最初の 1 回だけ待てば済む |
| kawaz 製 CLI 共通の `daemon` / `service` サブコマンドを持つ専用デーモン | `llama-server` 自体がポート指定でフォアグラウンド起動する 1 バイナリで、監督・状態表示・再起動の責務はすべて caddy-app-proxy と `llama-server` に既にある。足すものが無い |

## Consequences

- アイドルで落とされた後の最初のリクエストは起動を待つ (Caddy の exec timeout 内)。llama-server は自分からは終了しないので、落とす判断は caddy-app-proxy 側か手動
- 起動の観測 (ログ、pid) は `${XDG_STATE_HOME:-~/.local/state}/translate-server/` と caddy-app-proxy の一覧ページ

## 関連

- caddy-app-proxy の README「バックエンドをアクセス時に起動する」
- [DR-0004](./DR-0004-model-in-xdg-cache.md)
