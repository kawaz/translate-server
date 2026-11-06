---
title: cold start の 302 でクライアントが POST を GET に変えて 404 になる
status: open
category: bug
created: 2026-11-06T12:30:55+09:00
last_read:
open_entered: 2026-11-06T12:30:55+09:00
wip_entered:
blocked_entered:
pending_entered:
discarded_entered:
resolved_entered:
discard_reason:
pending_reason:
close_reason:
blocked_by:
origin: kawaz/claude-ccmsg
---

# cold start の 302 でクライアントが POST を GET に変えて 404 になる

## 概要

caddy-app-proxy の on-demand 起動で最初のアクセスに 302 が返るが、curl `-L` も Bun の `fetch` も 302 を辿る時に POST を GET に変える (HTTP 仕様どおり)。GET `/v1/chat/completions` に llama-server は `404 File Not Found` を返すので、cold start の最初の 1 回は失敗する見込み。手元の 302 を返す試験サーバで POST→GET の変換を確認した (実サーバの cold start は、評価中にサーバを止めない制約で未確認)。

## 背景

- 一次資料: claude-rules-personal の reference `local-translate.md` は「`curl -L` か 1 回リトライで吸収する」と書いているが、`-L` では吸収できない
- 利用側: ccmsg (kawaz/claude-ccmsg) の findings `docs/findings/2026-11-06-plamo-translate-eval.md` (2026-11-06)
- 以下の対処候補は部外者としてのフラグ。裏取りして採否を決めてほしい

## 対処の候補

- (a) caddy 側で 302 でなく 307 (method を保つ) を返す
- (b) クライアント側で `redirect: "manual"` で 302 を受けて同じ POST を送り直す (reference にその旨を書く)

## 受け入れ条件

- [ ] cold start の最初の POST が 404 にならない、または reference が正しい回避手順を示している
