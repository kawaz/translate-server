"""公式 GGUF をコピーし、token_embd だけ F32 に dequantize して指定の行を書き換えた GGUF を作る。
他のテンソルとメタデータは元のまま (量子化もそのまま) 複製する。

usage: python make_gguf.py <src.gguf> <out.gguf> [--row DST:SRC:DELTA:SCALE ...]
  DST の行を「SRC の行 (dequantize 済み) + SCALE × Δ」にする。DELTA は .npy、.npz:key、または - (Δ=0)
  例: --row 1385:1385:ojousama_train.npy:1.0     (ja 行に Δ を足す)
      --row 1464:1385:zundamon_train.npy:1.0     (ko 行を ja 行 + Δ で置き換える)
"""
import argparse, sys

import numpy as np
import gguf


def load_delta(spec):
    if spec == "-":
        return None
    if ":" in spec:
        f, k = spec.rsplit(":", 1)
        return np.load(f)[k]
    return np.load(spec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--row", action="append", default=[])
    a = ap.parse_args()

    r = gguf.GGUFReader(a.src)
    arch = r.fields[gguf.Keys.General.ARCHITECTURE].contents()
    w = gguf.GGUFWriter(a.out, arch=arch, endianess=r.endianess)
    for f in r.fields.values():
        if f.name == gguf.Keys.General.ARCHITECTURE or f.name.startswith("GGUF."):
            continue
        vt = f.types[0]
        st = f.types[-1] if vt == gguf.GGUFValueType.ARRAY else None
        w.add_key_value(f.name, f.contents(), vt, sub_type=st)

    emb = None
    for t in r.tensors:
        if t.name == "token_embd.weight":
            emb = gguf.quants.dequantize(t.data, t.tensor_type).astype(np.float32)
            orig = emb.copy()
            for spec in a.row:
                dst, src, rest = spec.split(":", 2)
                dspec, scale = rest.rsplit(":", 1)
                d = load_delta(dspec)
                emb[int(dst)] = orig[int(src)] + (0 if d is None else float(scale) * d)
                print(f"row {dst} <- row {src} + {scale} x {dspec}  |row|={np.linalg.norm(emb[int(dst)]):.2f} (元 {np.linalg.norm(orig[int(dst)]):.2f})", file=sys.stderr)
            w.add_tensor_info(t.name, emb.shape, emb.dtype, emb.nbytes, gguf.GGMLQuantizationType.F32)
        else:
            w.add_tensor_info(t.name, t.data.shape, t.data.dtype, t.data.nbytes, t.tensor_type)
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_ti_data_to_file()
    for t in r.tensors:
        w.write_tensor_data(emb if t.name == "token_embd.weight" else t.data, tensor_endianess=r.endianess)
    w.close()


if __name__ == "__main__":
    main()
