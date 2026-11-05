# translate-server justfile
#
# shell script と docs だけのリポ (VERSION / release / CI なし)。VCS gate は bump-semver vcs に委ねる。

set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments

port := env("TRANSLATE_SERVER_PORT", "8087")

# default behaviour: alias for `list`
default: list

# show the recipe list
list:
    @just --list --unsorted

# ---------- setup / run ----------

# install llama.cpp (Homebrew) and fetch the model into the XDG cache
setup:
    command -v llama-server >/dev/null || brew install llama.cpp
    bin/translate-server --fetch-only

# run llama-server in the foreground on $TRANSLATE_SERVER_PORT (default 8087)
run:
    bin/translate-server --port {{ port }}

# translate one sentence through the running server (checks the API end to end)
smoke:
    curl -s http://127.0.0.1:{{ port }}/v1/chat/completions -H 'Content-Type: application/json' \
      -d '{"model":"plamo-3-translate","messages":[{"role":"user","content":"The helper reads stdin line by line."}],"chat_template_kwargs":{"target_lang":"ja","form":"plain"},"temperature":0,"max_tokens":256}' \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["choices"][0]["message"]["content"])'

# ---------- lint ----------

# just --fmt (justfile self-format check)
[private]
lint-just:
    just --unstable --fmt --check

# shell syntax check
[private]
lint-sh:
    bash -n bin/translate-server ondemand/translate-server-ensure.sh

# all lints
lint: lint-just lint-sh

# ---------- gates (used by `just push`) ----------

# working copy is clean
[private]
ensure-clean:
    bump-semver vcs is clean

# fail if the current bookmark / branch is not the default
[private]
check-on-default-branch:
    bump-semver vcs is on-default-branch

# README-ja → README, DESIGN-ja → DESIGN translation pair freshness
[private]
check-outdated-translations: ensure-clean
    bump-semver vcs outdated 'glob:**/*-ja.md' '$1/$2.md'

# ---------- push ----------

# push the default branch to origin (clean + lint + translation freshness)
push: check-on-default-branch ensure-clean lint check-outdated-translations
    bump-semver vcs push --branch "$(bump-semver vcs get default-branch)" --jj-bookmark-auto-advance
