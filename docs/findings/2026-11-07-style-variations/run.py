"""styles.json の全文体 x 全テスト文を translate-server に通し、results.json と表 (markdown) を出す。

usage: python3 run.py [--url http://127.0.0.1:8087] > tables.md
"""
import argparse, json, re, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
CONFIGS = {
    # 文体の指示を どの経路で渡すか。chat template は system を捨てるので、効く可能性があるのはこの 3 経路
    "ctx": {"context": True, "history": False, "glossary": False},
    "shots": {"context": False, "history": True, "glossary": False},
    "full": {"context": True, "history": True, "glossary": True},
}


def translate(url, text, kwargs, history=()):
    msgs = []
    for src, dst in history:
        msgs += [{"role": "user", "content": src}, {"role": "assistant", "content": dst}]
    msgs.append({"role": "user", "content": text})
    body = {"model": "plamo-3-translate", "messages": msgs, "chat_template_kwargs": kwargs, "temperature": 0, "max_tokens": 1024}
    req = urllib.request.Request(url + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.load(r)
    return res["choices"][0]["message"]["content"], res["choices"][0]["finish_reason"]


def sentences(text):
    return [s for s in re.split(r"(?<=[。！？!?])", text) if s.strip()]


def hits(text, markers):
    ss = sentences(text)
    return sum(1 for s in ss if any(m in s for m in markers)), len(ss)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8087")
    a = ap.parse_args()
    d = json.loads((HERE / "styles.json").read_text())
    out = {"baselines": {}, "styles": {}}
    for b in d["baselines"]:
        kw = {"target_lang": b.get("target_lang", "ja")}
        if "form" in b:
            kw["form"] = b["form"]
        out["baselines"][b["id"]] = {t["id"]: translate(a.url, t["text"], kw)[0] for t in d["tests"]}
    for s in d["styles"]:
        shots = list(zip(d["shot_sources"], s["shots"]))
        out["styles"][s["id"]] = {}
        for cname, c in CONFIGS.items():
            kw = {"target_lang": "ja", "form": s["form"]}
            if c["context"]:
                kw["context"] = s["context"]
            if c["glossary"] and s["glossary"]:
                kw["glossary"] = s["glossary"]
            row = {}
            for t in d["tests"]:
                text, fin = translate(a.url, t["text"], kw, shots if c["history"] else ())
                h, n = hits(text, s["markers"])
                row[t["id"]] = {"text": text, "finish": fin, "hits": h, "sentences": n}
            out["styles"][s["id"]][cname] = row
        print(f"done {s['id']}", file=sys.stderr)
    (HERE / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
