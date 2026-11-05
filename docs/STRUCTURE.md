# リポジトリの構造

```
bin/translate-server                  フォアグラウンド起動 (モデル取得 → exec llama-server)
ondemand/translate-server-ensure.sh   caddy-app-proxy から呼ばれる冪等な起動スクリプト
justfile                              setup / run / smoke / lint / push
docs/
  DESIGN{,-ja}.md                     現在の設計
  STRUCTURE.md                        このファイル
  decisions/                          判断記録 (DR) と INDEX
  findings/                           計測の記録
README{,-ja}.md                       利用者向け (API の使い方、セットアップ)
```

実行時のファイルはリポの外: モデルは `${XDG_CACHE_HOME:-~/.cache}/translate-server/`、ログは `${XDG_STATE_HOME:-~/.local/state}/translate-server/`。
