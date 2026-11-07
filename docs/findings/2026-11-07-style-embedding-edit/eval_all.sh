#!/bin/bash
# 加工 GGUF を 1 つずつ作り、llama-server で tests 4 本を訳して results.jsonl に足し、GGUF を消す (ディスク節約)。
# usage: eval_all.sh <work-dir> <delta-dir>   (PY, PYTHONPATH は env で渡す。work-dir に gguf/ と server.log を作る)
set -euo pipefail
work="$1"; dl="$2"
here="$(cd "$(dirname "$0")" && pwd)"
models="${XDG_CACHE_HOME:-$HOME/.cache}/translate-server/models/plamo-3-translate-0.8b-GGUF"
src="$models/plamo-3-translate-0.8b-Q4_K_M.gguf"
tmpl="$models/chat_template.jinja"
out="$here/results.jsonl"
mkdir -p "$work/gguf"

run() {  # run <label> <case,...> <--row spec>...
	local label="$1" cases="$2"; shift 2
	local g="$work/gguf/$label.gguf" args=()
	for r in "$@"; do args+=(--row "$r"); done
	"$PY" "$here/make_gguf.py" "$src" "$g" "${args[@]}" 2>>"$work/make.log"
	local cargs=()
	IFS=, read -ra cs <<<"$cases"
	for c in "${cs[@]}"; do cargs+=(--case "$c"); done
	"$PY" "$here/server_eval.py" "$g" "$label" --template "$tmpl" --log "$work/server.log" "${cargs[@]}" >>"$out"
	rm -f "$g"
}

: >"$out"
JA=1385; KO=1464; RU=2086
# 既定 (公式 GGUF と同一の訳になることを別途確認済みの Δ=0 加工)
run base "ja:plain:ojousama,ja:polite:ojousama,ja:plain:zundamon,ja:plain:samurai,ja:plain:kansai" "$JA:$JA:-:1.0"
# (a) 最小二乗法 1 回 (既定の訳 + 語尾の差し込みを場面にした解)
for lam in 1 0.3; do
	run "ojousama-lsq-lam$lam" "ja:plain:ojousama,ja:polite:ojousama" "$JA:$JA:$dl/ojousama_lsqop.npz:lam$lam:1.0"
	run "zundamon-lsq-lam$lam" "ja:plain:zundamon" "$JA:$JA:$dl/zundamon_lsqop.npz:lam$lam:1.0"
done
# (b) 部分的な学習。スケール 0.5 / 1.0 / 1.5
for sc in 0.5 1.0 1.5; do
	run "ojousama-train-x$sc" "ja:plain:ojousama,ja:polite:ojousama" "$JA:$JA:$dl/ojousama_train16.npy:$sc"
	run "zundamon-train-x$sc" "ja:plain:zundamon" "$JA:$JA:$dl/zundamon_train_c30.npy:$sc"
	run "samurai-train-x$sc" "ja:plain:samurai" "$JA:$JA:$dl/samurai_train.npy:$sc"
	run "kansai-train-x$sc" "ja:plain:kansai" "$JA:$JA:$dl/kansai_train.npy:$sc"
done
# 派生: ja 行は元のまま、ko 行 = ja 行 + Δ(ずんだもん)、ru 行 = ja 行 + Δ(お嬢様)。ko:plain / ru:polite は PFML 直組み (/completion)
run "ko-zundamon-ru-ojousama" "ja:plain:zundamon,ja:polite:ojousama,ko:-:zundamon,ko:plain:zundamon,ru:-:ojousama,ru:polite:ojousama" \
	"$KO:$JA:$dl/zundamon_train_c30.npy:1.0" "$RU:$JA:$dl/ojousama_train16.npy:1.0"
