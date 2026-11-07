"""HF 版 PLaMo 3 Translate 0.8B を読み、PFML プロンプトの組み立てと `ja` 行の差し替えを行う共通部品。

環境変数 PLAMO_HF にモデルのディレクトリ (snapshot_download の戻り値) を入れて使う。
"""
import json, os
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = Path(__file__).parent
JA_ID = 1385
TAG_ID = 16  # <|plamo:tag|>。生成の終端 (eos_token_id の 1 つ)


def device():
    return "mps" if torch.backends.mps.is_available() else "cpu"


def load(dtype=torch.float32):
    path = os.environ["PLAMO_HF"]
    tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True, dtype=dtype).to(device())
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    return tok, model


def prompt(src, form="plain", lang="ja"):
    """chat_template.jinja と同じ PFML (history / context / glossary なし)。bos は tokenizer が付ける"""
    s = "<|plamo:tag|>dataset<|plamo:msg|>translation<|plamo:tag|>input<|plamo:msg|>" + src
    s += "<|plamo:tag|>output<|plamo:key|>lang<|plamo:val|>" + lang
    if form:
        s += "<|plamo:key|>form<|plamo:val|>" + form
    return s + "<|plamo:msg|>"


def encode(tok, text):
    return tok(text, add_special_tokens=True)["input_ids"]


def embed_with(model, ids, row_overrides):
    """ids の埋め込みを作り、row_overrides {token_id: 行ベクトル (未スケール)} の行を差し替える。

    config の scale_embedding が true なら Plamo3Embedding が sqrt(hidden) を掛けるので合わせる (この
    モデルは false で、素の nn.Embedding)。差し替え行は勾配を通す
    """
    emb = model.model.embed_tokens
    scale = emb.embedding_dim ** 0.5 if model.config.scale_embedding else 1.0
    t = torch.tensor([ids], device=emb.weight.device)
    x = torch.nn.functional.embedding(t, emb.weight) * scale
    if row_overrides:
        x = x.clone()
        for tid, row in row_overrides.items():
            mask = (t == tid).unsqueeze(-1)
            x = torch.where(mask, (row * scale).to(x.dtype).view(1, 1, -1), x)
    return x


@torch.no_grad()
def generate(model, tok, src, form="plain", lang="ja", row_overrides=None, max_new=200):
    """greedy (temperature 0 相当)。KV cache を使わず毎回全系列を流す (短文なので十分速い)"""
    ids = encode(tok, prompt(src, form, lang))
    out = []
    for _ in range(max_new):
        x = embed_with(model, ids + out, row_overrides)
        logits = model(inputs_embeds=x).logits[0, -1]
        nxt = int(logits.argmax())
        if nxt in (1, TAG_ID):
            break
        out.append(nxt)
    return tok.decode(out)


STYLES_JSON = HERE.parent / "2026-11-07-style-variations" / "styles.json"


def styles():
    return json.loads(STYLES_JSON.read_text())


def load_pairs(style):
    """学習データ: styles.json の例文 7 対 + data/<style>.json の 45 対 (英文は data/sources.json)"""
    d = styles()
    s = next(x for x in d["styles"] if x["id"] == style)
    pairs = list(zip(d["shot_sources"], s["shots"]))
    src = json.loads((HERE / "data" / "sources.json").read_text())
    ja = json.loads((HERE / "data" / f"{style}.json").read_text())
    assert len(src) == len(ja), (style, len(src), len(ja))
    pairs += [(a["en"], b) for a, b in zip(src, ja)]
    return pairs


def concat_pairs(pairs, n, seed=0):
    """複数文の訳でも文体が続くよう、学習データの対を 2〜4 個ずつ連結した対を n 個作る (内容は無関係な文の並び)"""
    import random
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        k = rng.randint(2, 4)
        ps = rng.sample(pairs, k)
        out.append((" ".join(a for a, _ in ps), "".join(b for _, b in ps)))
    return out


def train_forms(style):
    """学習に使う form。お嬢様は評価で polite も見るので両方で学習する"""
    return ["plain", "polite"] if style == "ojousama" else ["plain"]
