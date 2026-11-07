"""加工した GGUF を llama-server (bin/translate-server と同じオプション) で起動し、styles.json の tests 4 本を訳して JSON Lines で出す。
起動完了は llama-server のログ行 ("listening on http://...") を読んで待ち、終わったら起動したプロセスだけを止める。

usage: python server_eval.py <model.gguf> <label> --port 18087 --template <chat_template.jinja> \
         [--case target_lang:form[:style] ...] >> results.jsonl
  --case の例: ja:plain:zundamon  ja:polite:ojousama  ko:-:zundamon  ja:plain:-
  ja 以外の訳先に form を付けた case (ko:plain:...) は PFML を直に組んで /completion に送る
  style は目印語の数え方 (styles.json の markers) に使う。- なら数えない
"""
import argparse, io, json, os, pty, re, subprocess, threading, urllib.request

import common as c


def translate(port, text, kwargs):
    body = {"model": "plamo-3-translate", "messages": [{"role": "user", "content": text}], "chat_template_kwargs": kwargs, "temperature": 0, "max_tokens": 1024}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    return res["choices"][0]["message"]["content"], res["choices"][0]["finish_reason"]


def complete_raw(port, text, lang, form):
    """chat template は form に target_lang="ja" を要求するので、ja 以外 + form は PFML を直に組んで /completion に送る (BOS は server が付ける)"""
    body = {"prompt": c.prompt(text, form, lang), "temperature": 0, "n_predict": 1024, "stop": ["<|plamo:tag|>"]}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/completion", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    return res["content"], res.get("stop_type", "")


def hits(text, markers):
    ss = [s for s in re.split(r"(?<=[。！？!?])", text) if s.strip()]
    return sum(1 for s in ss if any(m in s for m in markers)), len(ss)


def drain(out, log):
    try:
        for x in out:
            log.write(x)
    except OSError:  # 子が終わると疑似端末の読み出しは EIO になる
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gguf")
    ap.add_argument("label")
    ap.add_argument("--port", type=int, default=18087)
    ap.add_argument("--template", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--case", action="append", required=True)
    a = ap.parse_args()
    d = c.styles()
    markers = {s["id"]: s["markers"] for s in d["styles"]}
    cmd = ["llama-server", "-m", a.gguf, "-c", "4096", "--host", "127.0.0.1", "--port", str(a.port), "--alias", "plamo-3-translate",
           "--chat-template-file", a.template, "--no-prefill-assistant", "--parallel", "1"]
    log = open(a.log, "a")
    # ログを行単位で受け取るため疑似端末につなぐ
    master, slave = pty.openpty()
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=slave, stderr=slave)
    os.close(slave)
    out = io.TextIOWrapper(os.fdopen(master, "rb", buffering=0), errors="replace")
    try:
        ready = False
        try:
            for line in out:  # 起動完了の行が出るまで読む
                log.write(line)
                if "listening on http" in line:
                    ready = True
                    break
        except OSError:  # 起動前に子が終わった
            pass
        if not ready:
            raise SystemExit(f"llama-server exited before listening (see {a.log})")
        # 以降のログも読み続ける (読まないと疑似端末が詰まって llama-server が止まる)
        threading.Thread(target=lambda: drain(out, log), daemon=True).start()
        for case in a.case:
            lang, form, style = (case.split(":") + ["-"])[:3]
            kw = {"target_lang": lang}
            if form != "-":
                kw["form"] = form
            for t in d["tests"]:
                if lang != "ja" and form != "-":
                    text, fin = complete_raw(a.port, t["text"], lang, form)
                else:
                    text, fin = translate(a.port, t["text"], kw)
                h, n = hits(text, markers[style]) if style != "-" else (None, None)
                print(json.dumps({"label": a.label, "lang": lang, "form": form, "style": style, "test": t["id"], "hits": h, "sentences": n, "finish": fin, "text": text}, ensure_ascii=False), flush=True)
    finally:
        proc.terminate()
        proc.wait()
        log.close()


if __name__ == "__main__":
    main()
