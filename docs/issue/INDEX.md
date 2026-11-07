# Issue INDEX

active な issue の一覧。close 済みは archive/ にあり、ここには載せない。

| date | category | status | slug | 概要 |
|---|---|---|---|---|
| 2026-11-07 | bug | open | [temp0-output-not-fully-deterministic](./2026-11-07-temp0-output-not-fully-deterministic.md) | temperature 0 でも同じ入力の訳が稀に揺れる (README の「決定的なのでキャッシュできる」と食い違う)。 |
| 2026-11-06 | bug | open | [context-limit-is-4096-per-slot](./2026-11-06-context-limit-is-4096-per-slot.md) | 起動オプションが `-c 16384 --parallel 4` なので 1 slot あたり 4,096 トークン (`server.log` の `n_ctx_slot = 4096`)。入力と出力の合計が… |
| 2026-11-06 | bug | open | [post-redirect-302-breaks-cold-start](./2026-11-06-post-redirect-302-breaks-cold-start.md) | caddy-app-proxy の on-demand 起動で最初のアクセスに 302 が返るが、curl -L も Bun の fetch も POST を GET に変える… |
