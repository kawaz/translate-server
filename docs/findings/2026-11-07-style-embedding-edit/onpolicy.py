"""最小二乗法 (a) 用の「場面」を、モデル自身の既定の訳 (Δ=0、greedy) から作る。

学習データの英文 (例文 7 対 + data/sources.json の 45 文 + それらを連結した 30 文) を既定のまま訳し、文末の約物の
直前に文体の語尾を差し込んだ訳文を作る (例: お嬢様は polite の「〜ます。」→「〜ますわ。」)。差し込んだ語尾と、
その直後の約物を「選ばせたい場面」、それ以外の位置を「今の選び方を保つ場面」にする。語尾の置換 (〜だ → 〜や) や
語彙の置換はしない (差し込みだけで表せる範囲に限る)。

usage: python onpolicy.py <style>   # data/onpolicy_<style>.json を書く
"""
import json, re, sys

import common as c

# (直前の文字列の正規表現, 差し込む語尾)。文末の約物 。！？ の直前に差し込む
RULES = {
    "ojousama": [(r"(ます|ました|ません|です|でした)$", "わ"), (r"ください$", "まし"), (r"(ですか|ますか)$", None)],
    "zundamon": [(r"(る|た|ない|かった|しい|ごい|きい|さい|たい)$", "のだ"), (r"んだ$", None), (r"だ$", ("なの", -1)), (r"の$", "だ")],
    "samurai": [(r"(る|た|ない|かった|たい)$", "でござる")],
    "kansai": [(r"る$", "ねん"), (r"た$", "んや")],
}
FORM = {"ojousama": "polite"}


def stylize(text, rules):
    """文末ごとに規則を当て、(差し込み後の文, 選ばせたい範囲 [(start, end)]) を返す"""
    out, spans, i = "", [], 0
    for mm in re.finditer(r"[。！？]", text):
        body = text[i:mm.start()]
        ins, at = None, len(body)
        for pat, val in rules:
            if re.search(pat, body):
                if isinstance(val, tuple):
                    ins, at = val[0], len(body) + val[1]
                else:
                    ins = val
                break
        if ins:
            body = body[:at] + ins + body[at:]
            s = len(out) + at
            spans.append([s, s + len(ins)])
            spans.append([len(out) + len(body), len(out) + len(body) + 1])  # 差し込みの直後の約物
        out += body + mm.group()
        i = mm.end()
    return out + text[i:], spans


def main():
    style = sys.argv[1]
    tok, model = c.load()
    pairs = c.load_pairs(style)
    pairs += c.concat_pairs(pairs, 30)
    form = FORM.get(style, "plain")
    rows = []
    for en, _ in pairs:
        base = c.generate(model, tok, en, form)
        ja, spans = stylize(base, RULES[style])
        rows.append({"en": en, "form": form, "base": base, "ja": ja, "lift": spans})
    (c.HERE / "data" / f"onpolicy_{style}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    print(f"{style}: {len(rows)} 文、差し込み {sum(len(r['lift']) // 2 for r in rows)} 箇所", file=sys.stderr)


if __name__ == "__main__":
    main()
