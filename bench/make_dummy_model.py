"""Stend kodini MODELSIZ sinash uchun kichik tasodifiy CTranslate2 Whisper modeli.

DIQQAT: og'irliklar tasodifiy - model ma'noli matn bermaydi, uning WER/CER natijasi hech narsani
anglatmaydi. Faqat run_bench.py zanjiri (audio -> faster-whisper -> so'z vaqtlari -> post-processing
-> WER/CER/RTF -> JSON) xatosiz ishlashini tekshirish uchun.
Lug'at va tokenizer - repodagi win/payload/Engine/uzbek_model dan (asl modelniki bilan bir xil).

  python3 bench/make_dummy_model.py bench/models/dummy
"""
import json
import os
import shutil
import sys

import numpy as np
from ctranslate2.specs import whisper_spec

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "win", "payload", "Engine", "uzbek_model")


def main(out, d=64, ffn=128, layers=2, heads=2, n_mels=80, seed=0):
    rng = np.random.default_rng(seed)
    vocab = json.load(open(os.path.join(SRC, "vocabulary.json"), encoding="utf-8"))
    cfg = json.load(open(os.path.join(SRC, "config.json"), encoding="utf-8"))
    V = len(vocab)
    r = lambda *s: (rng.standard_normal(s) * 0.05).astype(np.float32)
    ones, zeros = (lambda n: np.ones(n, np.float32)), (lambda n: np.zeros(n, np.float32))

    spec = whisper_spec.WhisperSpec(layers, heads, layers, heads)
    e, dec = spec.encoder, spec.decoder
    e.conv1.weight, e.conv1.bias = r(d, n_mels, 3), zeros(d)
    e.conv2.weight, e.conv2.bias = r(d, d, 3), zeros(d)
    e.position_encodings.encodings = r(1500, d)
    e.layer_norm.gamma, e.layer_norm.beta = ones(d), zeros(d)

    def ln(x):
        x.gamma, x.beta = ones(d), zeros(d)

    def lin(x, o, i):
        x.weight, x.bias = r(o, i), zeros(o)

    def ffn_(f):
        ln(f.layer_norm)
        lin(f.linear_0, ffn, d)
        lin(f.linear_1, d, ffn)

    for L in e.layer:
        ln(L.self_attention.layer_norm)
        lin(L.self_attention.linear[0], 3 * d, d)
        lin(L.self_attention.linear[1], d, d)
        ffn_(L.ffn)
    dec.embeddings.weight = r(V, d)
    dec.position_encodings.encodings = r(448, d)
    ln(dec.layer_norm)
    dec.projection.weight = dec.embeddings.weight
    for L in dec.layer:
        ln(L.self_attention.layer_norm)
        lin(L.self_attention.linear[0], 3 * d, d)
        lin(L.self_attention.linear[1], d, d)
        ln(L.attention.layer_norm)
        lin(L.attention.linear[0], d, d)
        lin(L.attention.linear[1], 2 * d, d)
        lin(L.attention.linear[2], d, d)
        ffn_(L.ffn)

    spec.register_vocabulary(vocab)
    spec.config.suppress_ids = cfg["suppress_ids"]
    spec.config.suppress_ids_begin = cfg["suppress_ids_begin"]
    spec.config.lang_ids = cfg["lang_ids"]
    spec.config.alignment_heads = [[layers - 1, h] for h in range(heads)]
    spec.validate()
    spec.optimize(quantization="float16")
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    spec.save(out)
    shutil.copy(os.path.join(SRC, "tokenizer.json"), out)
    print("tasodifiy model:", out, "(%.1f MB)" % (os.path.getsize(os.path.join(out, "model.bin")) / 1e6))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "models", "dummy"))
