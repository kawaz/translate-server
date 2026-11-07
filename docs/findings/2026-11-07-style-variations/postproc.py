"""常体 (form=plain) の訳文に、文末だけを置換する後処理をかけるデモ。形態素解析なしの正規表現だけ。

usage: python3 postproc.py results.json
"""
import json, re, sys

# 文ごとに、終助詞 (よ / ね / なあ) を落としてから、上から最初に当たった規則で文末を置き換える
RULES = {
    "zundamon": [(r"(ん|た)だ$", r"\1だのだ"), (r"だ$", "なのだ"), (r"の$", "のだ"), (r"(しよう|こう|ろう|よう)$", r"\1なのだ"), (r"て$", "てほしいのだ"), (r"$", "のだ")],
    "neko": [(r"(ん|た)だ$", r"\1だにゃ"), (r"だ$", "だにゃ"), (r"$", "にゃ")],
    "samurai": [(r"(ん|た)だ$", r"\1だのでござる"), (r"だ$", "でござる"), (r"の$", "のでござるか"), (r"(た|る|ない|う|く|す|つ|む|ぬ|ぶ|ぐ)$", r"\1のでござる"), (r"$", "でござる")],
}


def convert(text, rules):
    out = []
    for s in re.split(r"(?<=[。！？])", text):
        body, punct = re.match(r"^(.*?)([。！？]*)$", s, re.S).groups()
        if not body:
            continue
        body = re.sub(r"(よ|ね|なあ)$", "", body)
        for pat, rep in rules:
            if re.search(pat, body):
                body = re.sub(pat, rep, body, count=1)
                break
        out.append(body + punct)
    return "".join(out)


if __name__ == "__main__":
    plain = json.load(open(sys.argv[1]))["baselines"]["plain"]
    for sid, rules in RULES.items():
        for tid, text in plain.items():
            print(f"| {sid} | {tid} | {convert(text, rules)} |")
