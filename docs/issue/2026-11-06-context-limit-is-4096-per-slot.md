---
title: 入出力合計の上限は 32,768 でなく slot あたり 4,096 トークンで、超えると HTTP 200 のまま途中で切れる
status: open
category: bug
created: 2026-11-06T12:31:10+09:00
last_read:
open_entered: 2026-11-06T12:31:10+09:00
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

# 入出力合計の上限は 32,768 でなく slot あたり 4,096 トークンで、超えると HTTP 200 のまま途中で切れる

## 概要

起動オプションが `-c 16384 --parallel 4` なので 1 slot あたり 4,096 トークン (`server.log` の `n_ctx_slot = 4096`)。入力と出力の合計がこれを超えると HTTP 200 のまま訳文が途中で切れ、`finish_reason: "length"` になる。12,931 字の md を 1 リクエストで送ると 29 段落中 18 段落が切れた (観測)。

## 背景

claude-rules-personal の reference `local-translate.md` は「入出力合計の上限は 32,768 トークン」「数千トークンまでなら md を丸ごと 1 リクエストでも脱落しない」と書いているが、後者もこの上限内に限られる。

利用側は ccmsg (kawaz/claude-ccmsg) の findings `docs/findings/2026-11-06-plamo-translate-eval.md` (2026-11-06)。

## 対処の候補 (裏取りして採否を決めて)

- reference の数字を実態 (4,096 / slot) に直す
- 呼び出し側は `finish_reason` を見て `length` なら分割して再送する旨を書く
- 必要なら `-c` を増やすか `--parallel` を減らす

## 受け入れ条件

- [ ] 上限の記述が実態 (slot あたり) と一致している
- [ ] 途中で切れた場合の扱い (`finish_reason` の確認) が利用側に伝わる
