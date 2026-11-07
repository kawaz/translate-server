"""HF 版で Δ の候補を手早く比べる (GGUF を作る前の当たり付け)。評価文は styles.json の tests 4 本。

usage: python hf_eval.py <style> <delta.npy|delta.npz:key> [--scale 1.0] [--form plain] [--tests short,dialog]
"""
import argparse, json, re

import numpy as np
import torch

import common as c


def load_delta(spec):
    if ":" in spec:
        f, k = spec.split(":")
        return np.load(f)[k]
    return np.load(spec)


def hits(text, markers):
    ss = [s for s in re.split(r"(?<=[。！？!?])", text) if s.strip()]
    return sum(1 for s in ss if any(m in s for m in markers)), len(ss)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("style")
    ap.add_argument("deltas", nargs="+")
    ap.add_argument("--scales", default="1.0")
    ap.add_argument("--form", default="plain")
    ap.add_argument("--tests", default="short,dialog,tech,long")
    a = ap.parse_args()
    tok, model = c.load()
    d = c.styles()
    markers = next(s for s in d["styles"] if s["id"] == a.style)["markers"]
    tests = [t for t in d["tests"] if t["id"] in a.tests.split(",")]
    base = model.model.embed_tokens.weight[c.JA_ID].detach().clone()
    for spec in a.deltas:
        delta = torch.tensor(load_delta(spec), device=base.device)
        for sc in [float(x) for x in a.scales.split(",")]:
            tot = [0, 0]
            for t in tests:
                out = c.generate(model, tok, t["text"], a.form, row_overrides={c.JA_ID: base + sc * delta})
                h, n = hits(out, markers)
                tot[0] += h; tot[1] += n
                print(json.dumps({"delta": spec, "scale": sc, "test": t["id"], "hits": f"{h}/{n}", "text": out}, ensure_ascii=False), flush=True)
            print(f"# {spec} x{sc}: {tot[0]}/{tot[1]}", flush=True)


if __name__ == "__main__":
    main()
