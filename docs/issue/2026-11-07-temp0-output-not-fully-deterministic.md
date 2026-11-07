---
title: temperature 0 でも同じ入力の訳が稀に揺れる
status: open
category: bug
created: 2026-11-07T10:20:52+09:00
last_read:
open_entered: 2026-11-07T10:20:52+09:00
wip_entered:
blocked_entered:
pending_entered:
discarded_entered:
resolved_entered:
discard_reason:
pending_reason:
close_reason:
blocked_by:
origin: 自リポ TODO
---

# temperature 0 でも同じ入力の訳が稀に揺れる

## 概要

temperature 0 でも同じ入力の訳が稀に揺れる (README の「決定的なのでキャッシュできる」と食い違う)。

2026-11-07 の文体実験 (docs/findings/2026-11-07-style-variations.md) で 204 リクエスト (同じ chat_template_kwargs・history・temperature 0) を 2 回通したら 1 件だけ訳が 1 語違った (江戸っ子 context のみ・長文: 「開く勇気のなかった手紙」→「開く勇気のない手紙」)。サーバは --parallel 4 で他セッションと共用中。

原因は未確認。候補:

- 他リクエストとの同時 decode でバッチ構成が変わり、浮動小数の和の順序が変わる
- prompt cache の再利用

## 背景

影響: README / reference local-translate の「temperature 0 で決定的。同じ入力は同じ訳文なのでキャッシュできる」は「ほぼ決定的」が正しい。利用側のキャッシュ自体は問題ない (どちらの訳も正しい) が、テストで訳文の完全一致を期待すると落ちる。

## 受け入れ条件

- [ ] 単独アクセスで同じリクエストを N 回、並列負荷下で N 回、cache_prompt=false で N 回の 3 通りを比べて原因を切り分ける
- [ ] README の文言を実態 (ほぼ決定的) に直す
