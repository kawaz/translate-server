#!/bin/bash
# translate-server が port で listen していなければ起動する (冪等)。
# caddy-app-proxy の exec handler から 502 のたびに呼ばれる前提: 多重起動を lock で抑止し、
# 何度呼ばれても副作用は「必要なら 1 回起動」だけ。lock 待ちの側も listen を待ってから返す
# (即 exit すると Caddy が 302 → 502 → 302 を繰り返す)。
# llama-server は TCP の listen 後にモデルを読み込み、/health が "ok" を返した時点で受け付けるので、
# listen の判定は nc でなく /health で行う。Caddy は launchd 配下で PATH が最小なので絶対パスで引く。
set -eu -o pipefail

repo_dir="$(cd "$(dirname "$(realpath "$0")")/.." && pwd)"
bin="$repo_dir/bin/translate-server"
PORT="${TRANSLATE_SERVER_PORT:-8087}"
export PATH="/opt/homebrew/bin:/usr/bin:/bin"

state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/translate-server"
mkdir -p "$state_dir"
log="$state_dir/server.log"
lock="$state_dir/start.lock"

ready() { curl -s --max-time 1 "http://127.0.0.1:$PORT/health" 2>/dev/null | grep -q '"ok"'; }

if ready; then
	echo "already serving on $PORT"
	exit 0
fi

# モデルのロードは数秒、初回はダウンロードが乗る。Caddy 側の exec timeout に収まる範囲で待つ。
wait_ready() {
	for _ in $(seq 1 60); do
		ready && return 0
		sleep 0.5
	done
	return 1
}

# mkdir は atomic なので lock に使う。古い lock (起動失敗で残った物) は 2 分で無効化する。
if ! mkdir "$lock" 2>/dev/null; then
	if [ -n "$(find "$lock" -maxdepth 0 -mmin +2 2>/dev/null)" ]; then
		rmdir "$lock" 2>/dev/null || true
	fi
	if ! mkdir "$lock" 2>/dev/null; then
		echo "another start in progress, waiting"
		wait_ready && { echo "started by another"; exit 0; }
		echo "still not ready after 30s" >&2
		exit 1
	fi
fi

# 子は nohup + & で切り離し、Caddy の reload / 本スクリプトの終了に巻き込まれないようにする。
# 到達制限は Caddy の tailnet_only が担うので loopback にだけ bind する。
echo "starting translate-server on $PORT (log: $log)"
nohup "$bin" --port "$PORT" >>"$log" 2>&1 </dev/null &

if wait_ready; then
	rmdir "$lock"
	echo "started"
	exit 0
fi
rmdir "$lock"
echo "failed to become ready within 30s (see $log)" >&2
exit 1
