"""results.jsonl から findings 用の markdown 表 (テスト文ごとの全訳文、条件ごとの目印語の出現率) を出す。

usage: python tables.py > tables.md
"""
import collections, json
from pathlib import Path

import common as c

rs = [json.loads(l) for l in (Path(__file__).parent / "results.jsonl").read_text().splitlines()]
label = lambda r: f"{r['label']} / {r['lang']}" + (f" form={r['form']}" if r["form"] != "-" else "") + (" (/completion)" if r["lang"] != "ja" and r["form"] != "-" else "")

print("### 条件ごとの目印語の出現 (4 本合計、文単位)\n")
print("| GGUF / 訳先 | 文体の目印 | 出現 |\n|---|---|---|")
agg = collections.OrderedDict()
for r in rs:
    a = agg.setdefault((label(r), r["style"]), [0, 0])
    a[0] += r["hits"]; a[1] += r["sentences"]
for (lab, st), (h, n) in agg.items():
    print(f"| {lab} | {st} | {h}/{n} |")

for t in c.styles()["tests"]:
    print(f"\n### {t['label']}\n\n原文: {t['text']}\n")
    print("| GGUF / 訳先 | 訳文 | 目印 |\n|---|---|---|")
    seen = set()
    for r in rs:
        if r["test"] != t["id"]:
            continue
        k = (label(r), r["text"])
        if r["label"] == "base" and k in seen:
            continue
        seen.add(k)
        print(f"| {label(r)} | {r['text']} | {r['hits']}/{r['sentences']} |")
