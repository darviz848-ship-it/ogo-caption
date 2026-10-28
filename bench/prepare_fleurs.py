"""FLEURS uz_uz test to'plamini o'lchov uchun tayyorlaydi (bench/data/fleurs_uz/).

Manba (birinchisi ishlamasa ikkinchisi):
  hf  - HuggingFace google/fleurs: data/uz_uz/test.tsv + data/uz_uz/audio/test.tar.gz
  gcs - Google'ning asl FLEURS arxivi:
        https://storage.googleapis.com/xtreme_translations/FLEURS102/uz_uz.tar.gz
        (2.5 GB, train/dev/test; oqim bilan o'qiladi, faqat test qismi yoziladi)
Litsenziya: FLEURS - CC-BY-4.0. Ma'lumot repoga kirmaydi (bench/data/ - .gitignore).

Natija:
  bench/data/fleurs_uz/test.tsv          asl jadval
  bench/data/fleurs_uz/wav/<fayl>.wav    16 kHz mono
  bench/data/fleurs_uz/manifest.jsonl    {"id","wav","text","duration","gender"} - har gapdan bitta yozuv
  bench/data/fleurs_uz/long/*.wav        uzun fayllar (--long): gaplar + sukut + sintetik musiqa,
  bench/data/fleurs_uz/long.jsonl        uzun fayllar matni (gallyutsinatsiya va uzun audio sinovi)

Ishlatish:
  python3 bench/prepare_fleurs.py [--source auto|hf|gcs] [--long 10]
"""
import argparse
import csv
import io
import json
import os
import random
import shutil
import sys
import tarfile
import urllib.request
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "fleurs_uz")
GCS_URL = "https://storage.googleapis.com/xtreme_translations/FLEURS102/uz_uz.tar.gz"
SR = 16000


def _safe_name(name):
    base = os.path.basename(name)
    if not base or base.startswith(".") or "/" in base or "\\" in base:
        raise ValueError("Shubhali fayl nomi arxivda: %r" % name)
    return base


def _write_member(tf, member, dst):
    src = tf.extractfile(member)
    if src is None:
        return
    tmp = dst + ".part"
    with open(tmp, "wb") as f:
        shutil.copyfileobj(src, f, 1 << 20)
    os.replace(tmp, dst)


def from_hf():
    from huggingface_hub import hf_hub_download   # faqat bench uchun (pip install huggingface_hub)
    tsv = hf_hub_download("google/fleurs", "data/uz_uz/test.tsv", repo_type="dataset")
    tgz = hf_hub_download("google/fleurs", "data/uz_uz/audio/test.tar.gz", repo_type="dataset")
    shutil.copy(tsv, os.path.join(OUT, "test.tsv"))
    with tarfile.open(tgz, "r:gz") as tf:
        for m in tf:
            if m.isfile() and m.name.endswith(".wav"):
                _write_member(tf, m, os.path.join(OUT, "wav", _safe_name(m.name)))


def from_gcs():
    print("Yuklanmoqda:", GCS_URL, flush=True)
    resp = urllib.request.urlopen(GCS_URL)
    total = int(resp.headers.get("Content-Length") or 0)

    class Counting(io.RawIOBase):
        def __init__(self, r):
            self.r, self.n, self.last = r, 0, 0

        def readable(self):
            return True

        def readinto(self, b):
            chunk = self.r.read(len(b))
            b[:len(chunk)] = chunk
            self.n += len(chunk)
            if total and self.n - self.last > 200 << 20:
                self.last = self.n
                print("  %.0f%% (%.1f / %.1f GB)" % (100.0 * self.n / total, self.n / 1e9, total / 1e9), flush=True)
            return len(chunk)

    stream = io.BufferedReader(Counting(resp), 1 << 20)
    n = 0
    with tarfile.open(fileobj=stream, mode="r|gz") as tf:
        for m in tf:
            parts = m.name.replace("\\", "/").split("/")
            if not m.isfile():
                continue
            if parts[-1] == "test.tsv":
                _write_member(tf, m, os.path.join(OUT, "test.tsv"))
            elif len(parts) >= 2 and parts[-2] == "test" and parts[-1].endswith(".wav"):
                _write_member(tf, m, os.path.join(OUT, "wav", _safe_name(m.name)))
                n += 1
    print("test wav:", n)


def read_tsv(path):
    # FLEURS: id, file_name, raw_transcription, transcription, phonemes, num_samples, gender
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 7:
                continue
            rows.append({"id": p[0], "file": p[1], "raw": p[2], "norm": p[3],
                         "num_samples": int(p[5]), "gender": p[6]})
    return rows


def read_wav(path):
    """16 kHz mono WAV: PCM int16 yoki float32 (FLEURS - float32, wave moduli uni o'qimaydi)."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("WAV emas: " + path)
    pos, fmt, pcm = 12, None, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], int.from_bytes(data[pos + 4:pos + 8], "little")
        body = data[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            fmt = (int.from_bytes(body[0:2], "little"), int.from_bytes(body[2:4], "little"),
                   int.from_bytes(body[4:8], "little"), int.from_bytes(body[14:16], "little"))
        elif cid == b"data":
            pcm = body
        pos += 8 + size + (size & 1)
    tag, ch, sr, bits = fmt
    if ch != 1 or sr != SR:
        raise ValueError("16 kHz mono kerak: %s (%d kanal, %d Hz)" % (path, ch, sr))
    if tag == 3 and bits == 32:
        return np.frombuffer(pcm, dtype="<f4").astype(np.float32)
    if tag == 1 and bits == 16:
        return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    raise ValueError("Noma'lum WAV formati %s: tag=%d bits=%d" % (path, tag, bits))


def write_wav(path, x):
    y = np.clip(x, -1.0, 1.0)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype(np.int16).tobytes())


def synth_music(seconds, rng):
    """Nutqsiz sintetik musiqa: akkordlar + bas + zarb + shovqinli "hi-hat" (gallyutsinatsiya sinovi)."""
    t = np.arange(int(seconds * SR)) / SR
    roots = [261.63, 196.00, 220.00, 174.61]   # C G Am F
    out = np.zeros_like(t)
    beat = 0.5
    for k in range(int(seconds / beat) + 1):
        s, e = int(k * beat * SR), min(len(t), int((k + 1) * beat * SR))
        if s >= e:
            break
        root = roots[(k // 4) % len(roots)]
        tt = t[s:e] - t[s]
        env = np.exp(-tt * 3.0)
        for mul, amp in ((1.0, 0.25), (1.25, 0.18), (1.5, 0.18), (2.0, 0.08), (0.5, 0.2)):
            out[s:e] += amp * env * np.sin(2 * np.pi * root * mul * tt + rng.uniform(0, 6.28))
        out[s:e] += 0.35 * np.exp(-tt * 25.0) * np.sin(2 * np.pi * 55.0 * tt)          # zarb
        hh = min(e - s, int(0.03 * SR))
        out[s:s + hh] += 0.05 * rng.standard_normal(hh)                                  # hi-hat
    return 0.25 * out / (np.abs(out).max() + 1e-9)


def build_long(items, n_files, per_file, seed=1234):
    """Uzun fayllar: boshida musiqa (intro), gaplar orasida sukut, har 5-gapdan keyin musiqa.
    segments - har bo'lakning turi va vaqti: so'z vaqtlari va musiqa ustidagi gallyutsinatsiyani o'lchash uchun."""
    rng = np.random.default_rng(seed)
    pick = random.Random(seed)
    os.makedirs(os.path.join(OUT, "long"), exist_ok=True)
    # Oxiridagi gaplar olinadi: qisqa to'plam (run_bench --limit) boshidan oladi - kesishmasin
    pool = list(reversed(items))[:n_files * per_file]
    pick.shuffle(pool)
    recs = []
    for fi in range(n_files):
        chunk = pool[fi * per_file:(fi + 1) * per_file]
        if len(chunk) < per_file:
            break
        parts, segs, t = [], [], 0.0

        def add(x, kind, ref_id=None, text=None):
            nonlocal t
            seg = {"type": kind, "start": round(t, 3), "end": round(t + len(x) / float(SR), 3)}
            if ref_id is not None:
                seg.update({"id": ref_id, "text": text})
            segs.append(seg)
            parts.append(x.astype(np.float32))
            t += len(x) / float(SR)

        add(synth_music(6.0, rng), "music")
        for j, it in enumerate(chunk):
            add(read_wav(os.path.join(OUT, it["wav"])), "speech", it["id"], it["text"])
            if j % 5 == 4:
                add(synth_music(float(rng.uniform(4, 8)), rng), "music")
            else:
                add(np.zeros(int(rng.uniform(0.3, 2.5) * SR)), "silence")
        x = np.concatenate(parts)
        name = "long_%02d.wav" % fi
        write_wav(os.path.join(OUT, "long", name), x)
        recs.append({"id": name[:-4], "wav": "long/" + name,
                     "text": " ".join(sg["text"] for sg in segs if sg["type"] == "speech"),
                     "duration": round(len(x) / float(SR), 3), "segments": segs})
    with open(os.path.join(OUT, "long.jsonl"), "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("uzun fayllar:", len(recs), "jami %.1f daqiqa" % (sum(r["duration"] for r in recs) / 60))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="auto", choices=["auto", "hf", "gcs"])
    ap.add_argument("--long", type=int, default=10, help="uzun fayllar soni (0 - yaratilmasin)")
    ap.add_argument("--per-long", type=int, default=19, help="har uzun faylda nechta gap (150 + 10*19 <= 345 - kesishmaydi)")
    a = ap.parse_args()
    os.makedirs(os.path.join(OUT, "wav"), exist_ok=True)

    if not os.path.exists(os.path.join(OUT, "test.tsv")):
        if a.source in ("auto", "hf"):
            try:
                from_hf()
            except Exception as e:
                if a.source == "hf":
                    raise
                print("HuggingFace ishlamadi (%s) - Google arxivi ishlatiladi." % str(e)[:200])
        if not os.path.exists(os.path.join(OUT, "test.tsv")):
            from_gcs()

    rows = read_tsv(os.path.join(OUT, "test.tsv"))
    seen, items = set(), []
    for r in sorted(rows, key=lambda r: (int(r["id"]), r["file"])):
        wav = os.path.join(OUT, "wav", r["file"])
        if r["id"] in seen or not os.path.exists(wav):
            continue
        seen.add(r["id"])
        items.append({"id": r["id"], "wav": "wav/" + r["file"], "text": r["raw"],
                      "duration": r["num_samples"] / float(SR), "gender": r["gender"]})
    with open(os.path.join(OUT, "manifest.jsonl"), "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print("yozuvlar (tsv): %d, noyob gaplar: %d, jami %.1f daqiqa"
          % (len(rows), len(items), sum(i["duration"] for i in items) / 60))
    if a.long:
        build_long(items, a.long, a.per_long)


if __name__ == "__main__":
    sys.exit(main())
