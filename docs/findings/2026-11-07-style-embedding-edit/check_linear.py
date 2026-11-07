"""最小二乗の解で、1 次近似の予測 margin と実際の margin (Δ を入れて流し直した値) を比べる。

usage: python check_linear.py <style> <jac.npz> <lsq.npz> <key>... [--scales 0.25,0.5,1]
"""
import argparse

import numpy as np
import torch

import common as c
import solve


def margins(model, seqs, row):
    out = []
    with torch.no_grad():
        for p, t, _ in seqs:
            x = c.embed_with(model, (p + t)[:-1], {c.JA_ID: row})
            lg = model(inputs_embeds=x).logits[0]
            for k, y in enumerate(t):
                z = lg[len(p) - 1 + k].clone()
                zy = float(z[y]); z[y] = -float("inf")
                out.append(zy - float(z.max()))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("style"); ap.add_argument("jac"); ap.add_argument("lsq"); ap.add_argument("keys", nargs="+")
    ap.add_argument("--scales", default="0.25,0.5,1")
    ap.add_argument("--concat", type=int, default=30)
    a = ap.parse_args()
    tok, model = c.load()
    seqs, _ = solve.sequences(tok, a.style, a.concat)
    J = np.load(a.jac); now, lift, Jm = J["now"], J["lift"], J["J"]
    base = model.model.embed_tokens.weight[c.JA_ID].detach().clone()
    up = lift & (now < 2)
    for key in a.keys:
        d = np.load(a.lsq)[key]
        for sc in [float(x) for x in a.scales.split(",")]:
            pred = now + Jm @ (sc * d)
            real = margins(model, seqs, base + torch.tensor(sc * d, device=base.device))
            keep = ~lift & (now >= 0)
            print(f"{key} x{sc}: 上げる場面 margin>0 予測={np.mean(pred[up] > 0):.2f} 実際={np.mean(real[up] > 0):.2f} | 予測と実際の相関={np.corrcoef(pred - now, real - now)[0, 1]:.2f} | 保つ場面で負に転じる 予測={np.mean(pred[keep] < 0):.3f} 実際={np.mean(real[keep] < 0):.3f}")


if __name__ == "__main__":
    main()
