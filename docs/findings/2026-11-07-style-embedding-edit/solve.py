"""`ja` (token 1385) の入力埋め込みの差分 Δ を求める。

usage:
  python solve.py jac   <style> <jac.npz> [--concat 30 | --onpolicy]               # 最小二乗の材料 (ヤコビアン) を作る
  python solve.py lsq   <jac.npz> <out.npz> [--margin 2] [--keep 0.3] [--lams 1,3,10,30] [--cap 3] [--reach -6]
  python solve.py train <style> <out.npy> [--epochs 8] [--lr 0.05] [--l2 1e-4] [--concat 30] [--holdout 10]

(a) 最小二乗法 1 回 (jac + lsq):
  学習データの訳文を teacher forcing で流し、訳文の各トークン位置を「場面」とする。場面ごとに
  margin = (正解トークンのロジット) - (正解以外で今いちばん高いトークンのロジット) と、その Δ についての勾配を取る。
  data/lift.json の範囲 (文体の語尾・語彙) に当たる場面は margin を --margin まで上げたい (足りていれば保つ)、
  それ以外の場面は今の margin を保ちたい (重み --keep) として、1 次近似の連立式 J Δ = b を
  リッジ最小二乗で 1 回だけ解く (反復しない)。λ ごとの解を npz に保存する
(b) 部分的な学習 (train):
  Δ だけを学習可能にし、訳文トークン (+ 終端) のクロスエントロピーを Adam で下げる (soft prompt tuning)
"""
import argparse, json, re, sys, time

import numpy as np
import torch

import common as c


def token_flags(tok, t, hit):
    """文字単位の「選ばせたい範囲」hit をトークン単位にする (+ 終端の分)。範囲に重なるトークンに加え、範囲の直前で
    終わるトークンも上げる対象にする。「終了する。」は ['終了', 'する。'] と約物ごと 1 トークンになるので、
    「終了するのだ。」(['終了', 'する', 'の', 'だ。']) を出すには「する。」でなく「する」を選ぶ場面も上げる必要がある"""
    flags, pos = [], 0
    for k in range(len(t)):
        end = len(tok.decode(t[: k + 1]))
        flags.append(bool(hit[pos:end].any()) or (end < len(hit) and hit[end] and (end == 0 or not hit[end - 1])))
        pos = end
    return flags + [False]


def sequences(tok, style, concat=0, holdout=0):
    """学習列 (prompt の id 列, 訳文 + 終端の id 列, 各訳文トークンが文体の範囲に当たるか) の (学習用, 検証用) を返す。
    holdout > 0 なら学習データの末尾 holdout 対を検証用に外す。concat > 0 なら、残りの対を連結した複数文の対
    (common.concat_pairs) を concat 個足す。form ごとに全部を作る"""
    pats = [re.compile(p) for p in json.loads((c.HERE / "data" / "lift.json").read_text())[style]]
    pairs = c.load_pairs(style)
    held_pairs = pairs[len(pairs) - holdout:] if holdout else []
    pairs = pairs[: len(pairs) - holdout]
    pairs += c.concat_pairs(pairs, concat)

    def enc(en, ja, form):
        p = c.encode(tok, c.prompt(en, form))
        t = tok(ja, add_special_tokens=False)["input_ids"]
        assert tok.decode(t) == ja, (ja, tok.decode(t))
        hit = np.zeros(len(ja), bool)
        for pat in pats:
            for mm in pat.finditer(ja):
                hit[mm.start():mm.end()] = True
        return p, t + [c.TAG_ID], token_flags(tok, t, hit)

    forms = c.train_forms(style)
    return [enc(en, ja, f) for f in forms for en, ja in pairs], [enc(en, ja, f) for f in forms for en, ja in held_pairs]


def onpolicy_sequences(tok, style):
    """onpolicy.py が作った「既定の訳 + 語尾の差し込み」を学習列にする (差し込みとその直後の約物が上げる場面)"""
    rows = json.loads((c.HERE / "data" / f"onpolicy_{style}.json").read_text())
    return [enc_row(tok, r) for r in rows]


def enc_row(tok, r):
    p = c.encode(tok, c.prompt(r["en"], r["form"]))
    t = tok(r["ja"], add_special_tokens=False)["input_ids"]
    hit = np.zeros(len(r["ja"]), bool)
    for a, b in r["lift"]:
        hit[a:b] = True
    return p, t + [c.TAG_ID], token_flags(tok, t, hit)


def jac(model, tok, style, path, concat=0, onpolicy=False):
    seqs = onpolicy_sequences(tok, style) if onpolicy else sequences(tok, style, concat)[0]
    base = model.model.embed_tokens.weight[c.JA_ID].detach().clone()
    rows, now, lift = [], [], []
    t0 = time.time()
    for p, t, flags in seqs:
        delta = torch.zeros_like(base, requires_grad=True)
        ids = p + t
        x = c.embed_with(model, ids[:-1], {c.JA_ID: base + delta})
        logits = model(inputs_embeds=x).logits[0]
        for k, y in enumerate(t):
            z = logits[len(p) - 1 + k]
            zz = z.detach().clone()
            zz[y] = -float("inf")
            m = z[y] - z[int(zz.argmax())]
            (g,) = torch.autograd.grad(m, delta, retain_graph=True)
            rows.append(g.cpu().numpy()); now.append(float(m.detach())); lift.append(flags[k])
    sec = time.time() - t0
    np.savez(path, J=np.stack(rows), now=np.array(now), lift=np.array(lift), sec=sec)
    print(f"style={style} 文={len(seqs)} 場面={len(now)} 文体の場面={sum(lift)} (うち今 margin<0: {sum(1 for a, b in zip(now, lift) if b and a < 0)}) ヤコビアン所要={sec:.1f}s", file=sys.stderr)


def lsq(jac_path, out, margin, keep, lams, cap=None, reach=None):
    """cap: 1 場面で上げる量の上限。reach: 今の margin がこれより低い (届きそうにない) 文体の場面は上げる対象から外す"""
    t0 = time.time()
    d = np.load(jac_path)
    J, now, lift = d["J"].astype(np.float64), d["now"], d["lift"]
    if reach is not None:
        lift = lift & (now >= reach)
    b = np.where(lift, np.maximum(margin - now, 0.0), 0.0)
    if cap is not None:
        b = np.minimum(b, cap)
    w = np.sqrt(np.where(lift, 1.0, keep))
    U, S, Vt = np.linalg.svd(J * w[:, None], full_matrices=False)
    print(f"場面={len(b)} 上げる場面={int((b > 0).sum())} 特異値 max={S[0]:.3g} min={S[-1]:.3g}", file=sys.stderr)
    sols = {}
    for lam in lams:
        x = Vt.T @ (S / (S ** 2 + lam) * (U.T @ (b * w)))
        pred = now + J @ x
        up = b > 0
        print(f"  λ={lam:g} |Δ|={np.linalg.norm(x):.2f}  上げる場面で margin>0 になる率(線形)={np.mean(pred[up] > 0):.2f}  保つ場面で margin が負に転じる率(線形)={np.mean((pred < 0) & (now >= 0) & ~lift) / max(np.mean((now >= 0) & ~lift), 1e-9):.3f}", file=sys.stderr)
        sols[f"lam{lam:g}"] = x.astype(np.float32)
    np.savez(out, **sols)
    print(f"  解く所要={time.time() - t0:.2f}s (ヤコビアン {float(d['sec']):.1f}s は別)", file=sys.stderr)


def ce(model, base, delta, p, t):
    x = c.embed_with(model, (p + t)[:-1], {c.JA_ID: base + delta})
    logits = model(inputs_embeds=x).logits[0, len(p) - 1:]
    return torch.nn.functional.cross_entropy(logits.float(), torch.tensor(t, device=logits.device), reduction="sum")


def train(model, tok, style, epochs, lr, l2, out, holdout=0, concat=0):
    """holdout > 0 なら学習データの末尾 holdout 対を外し、その CE を毎 epoch 出す"""
    seqs, held = sequences(tok, style, concat, holdout)
    base = model.model.embed_tokens.weight[c.JA_ID].detach().clone()
    delta = torch.zeros_like(base, requires_grad=True)
    opt = torch.optim.Adam([delta], lr=lr)
    t0 = time.time()
    rng = np.random.default_rng(0)
    for ep in range(epochs):
        tot, ntok = 0.0, 0
        for i in rng.permutation(len(seqs)):
            p, t, _ = seqs[i]
            loss = ce(model, base, delta, p, t)
            (loss / len(t) + l2 * delta.pow(2).sum()).backward()
            opt.step(); opt.zero_grad()
            tot += float(loss.detach()); ntok += len(t)
        msg = f"  epoch {ep + 1}: 平均 CE={tot / ntok:.3f} |Δ|={float(delta.norm()):.2f} 経過={time.time() - t0:.0f}s"
        if held:
            with torch.no_grad():
                hc = sum(float(ce(model, base, delta, p, t)) for p, t, _ in held) / sum(len(t) for _, t, _ in held)
            msg += f" 外した {len(held)} 文の CE={hc:.3f}"
        print(msg, file=sys.stderr)
        np.save(out.replace(".npy", f".ep{ep + 1}.npy"), delta.detach().cpu().numpy().astype(np.float32))
    print(f"style={style} 学習所要={time.time() - t0:.1f}s", file=sys.stderr)
    np.save(out, delta.detach().cpu().numpy().astype(np.float32))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("method", choices=["jac", "lsq", "train"])
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--margin", type=float, default=2.0)
    ap.add_argument("--keep", type=float, default=0.3)
    ap.add_argument("--cap", type=float)
    ap.add_argument("--reach", type=float)
    ap.add_argument("--lams", default="0.3,1,3,10,30")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--l2", type=float, default=1e-4)
    ap.add_argument("--holdout", type=int, default=0)
    ap.add_argument("--concat", type=int, default=0)
    ap.add_argument("--onpolicy", action="store_true", help="jac: onpolicy.py の場面を使う")
    a = ap.parse_args()
    if a.method == "lsq":
        return lsq(a.a, a.b, a.margin, a.keep, [float(x) for x in a.lams.split(",")], a.cap, a.reach)
    tok, model = c.load()
    if a.method == "jac":
        jac(model, tok, a.a, a.b, a.concat, a.onpolicy)
    else:
        train(model, tok, a.a, a.epochs, a.lr, a.l2, a.b, a.holdout, a.concat)


if __name__ == "__main__":
    main()
