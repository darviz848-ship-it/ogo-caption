"""O'zbekcha transkripsiya o'lchovi: WER / CER / RTF (+ xato turlari, so'z vaqtlari, gallyutsinatsiya).

  python3 bench/run_bench.py --model bench/models/kotib_ct2_f16 --set short --limit 150 --config base
  python3 bench/run_bench.py --model ... --set long --config base --config base+cond_off
  python3 bench/run_bench.py --model ... --set short --engine win/payload/Engine   # Engine'ning o'zi (subprocess)

--set short - FLEURS uz_uz test, har gap alohida (manifest.jsonl, boshidan --limit ta);
--set long  - 10 ta ~4.5 daqiqalik fayl: gaplar + sukut + sintetik musiqa (long.jsonl).
--config    - CONFIGS dagi nomlar, "+" bilan birlashtiriladi: base+cond_off+hst2.
Natija: bench/out/<model>/<set>/<config>.json (umumiy ko'rsatkichlar + har yozuv).
Har sozlama plagindagi zanjirdan o'tadi: Engine (kirill -> lotin, merge_number_words) -> panel mergeWords.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import bench_lib as B

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "fleurs_uz")

PROMPT_PLUGIN = u"salom, qandaysiz, привет, hello"
# To'g'ri imloli o'zbekcha jumla: oʻ, gʻ, -ning, -dagi, sh, ch, tutuq
PROMPT_UZ = (u"Assalomu alaykum! Bugun Oʻzbekistonning poytaxti Toshkentdagi yangi koʻprik va "
             u"bogʻdagi bayram haqida gaplashamiz, shuningdek, taʼlim masalasiga ham toʻxtalamiz.")
PROMPT_UZ_ASCII = PROMPT_UZ.replace(u"ʻ", "'").replace(u"ʼ", "'")

BASE = {"language": "uz", "word_timestamps": True, "initial_prompt": PROMPT_PLUGIN}   # plagin bugun

# Har biri bazadan bitta farq. "post" - Engine'dagi post-processing qadamlari (bench_lib).
CONFIGS = {
    "base": {},
    "prompt_none": {"initial_prompt": None},
    "prompt_uz": {"initial_prompt": PROMPT_UZ},
    "prompt_uz_ascii": {"initial_prompt": PROMPT_UZ_ASCII},
    "cond_off": {"condition_on_previous_text": False},
    "hst2": {"hallucination_silence_threshold": 2.0},
    "crt2.0": {"compression_ratio_threshold": 2.0},
    "nst0.4": {"no_speech_threshold": 0.4},
    "beam1": {"beam_size": 1},
    "beam3": {"beam_size": 3},
    "beam8": {"beam_size": 8},
    "temp0": {"temperature": 0.0},
    "reppen1.1": {"repetition_penalty": 1.1},
    "nrng4": {"no_repeat_ngram_size": 4},
    "vad": {"vad_filter": True},
    "vad500": {"vad_filter": True, "vad_parameters": {"min_silence_duration_ms": 500, "speech_pad_ms": 200}},
    "pp_premerge": {"post": ["premerge"]},
    "pp_dedup": {"post": ["dedup"]},
    "pp_noise": {"post": ["noise"]},
}


def make_config(name):
    kw, post = dict(BASE), []
    for part in name.split("+"):
        if part not in CONFIGS:
            raise SystemExit("Noma'lum sozlama: %s (bor: %s)" % (part, ", ".join(CONFIGS)))
        c = dict(CONFIGS[part])
        post += c.pop("post", [])
        kw.update(c)
    return kw, post


def load_set(name, limit):
    path = os.path.join(DATA, "manifest.jsonl" if name == "short" else "long.jsonl")
    items = [json.loads(l) for l in open(path, encoding="utf-8")]
    return items[:limit] if limit else items


def transcribe_items(model, items, kw, log_every=10):
    """faster-whisper bilan; har so'z: matn (bosh bo'shlig'i bilan), vaqt, segment raqami."""
    out = []
    for n, it in enumerate(items):
        wav = os.path.join(DATA, it["wav"])
        t0 = time.perf_counter()
        segments, info = model.transcribe(wav, **kw)
        raw, segs = [], []
        for si, seg in enumerate(segments):
            segs.append({"start": seg.start, "end": seg.end, "text": seg.text,
                         "no_speech_prob": seg.no_speech_prob, "avg_logprob": seg.avg_logprob,
                         "compression_ratio": seg.compression_ratio, "temperature": seg.temperature})
            for w in seg.words or []:
                raw.append({"word": w.word, "start": w.start, "end": w.end, "prob": w.probability, "seg": si})
        dt = time.perf_counter() - t0
        out.append({"id": it["id"], "raw": raw, "segments": segs, "time": dt, "duration": it["duration"]})
        if log_every and (n + 1) % log_every == 0:
            done = sum(x["time"] for x in out) / max(1e-9, sum(x["duration"] for x in out))
            print("  %d/%d  RTF %.3f" % (n + 1, len(items), done), flush=True)
    return out


def engine_subprocess(engine_dir, model_dir, items):
    """Engine'ning o'z transcribe.py si: vaqtinchalik papkada Engine nusxasi + uzbek_model -> model."""
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        eng = os.path.join(tmp, "Engine")
        shutil.copytree(engine_dir, eng, ignore=shutil.ignore_patterns("uzbek_model", "multi_model", "translate_model*", "__pycache__"))
        os.symlink(os.path.abspath(model_dir), os.path.join(eng, "uzbek_model"))
        for it in items:
            t0 = time.perf_counter()
            p = subprocess.run([sys.executable, os.path.join(eng, "transcribe.py"), os.path.join(DATA, it["wav"]), "uz"],
                               capture_output=True, text=True, encoding="utf-8", cwd=eng)
            dt = time.perf_counter() - t0
            data = json.loads(p.stdout.strip().splitlines()[-1])
            if not data.get("success"):
                raise RuntimeError("Engine xatosi: %s" % data)
            out.append({"id": it["id"], "engine_words": data["words"], "time": dt, "duration": it["duration"]})
    return out


def postprocess(eng, rec, post):
    raw = rec["raw"]
    if "noise" in post:
        raw = B.drop_noise_segments(raw)
    if "premerge" in post:
        raw = B.premerge(raw)
    words = B.engine_words(eng, raw, is_uzbek=True)
    if "dedup" in post:
        words = B.dedup_repeats(words)
    return B.panel_merge_words(words)


def evaluate(eng, set_name, items, recs, post):
    by_id = {it["id"]: it for it in items}
    per, timing = [], {"aligned": 0, "off_sync": 0, "halluc": 0, "bad_dur": 0}
    apos_split = raw_words = 0
    for rec in recs:
        it = by_id[rec["id"]]
        if "engine_words" in rec:
            words = B.panel_merge_words(rec["engine_words"])
        else:
            words = postprocess(eng, rec, post)
            raw_words += len(rec["raw"])
            apos_split += sum(1 for w in rec["raw"] if w["word"][:1] in "'" + B.APOSTROPHES)
        hyp = B.tokens(words)
        ref = B.tokens(B.ref_words(eng, it["text"]))
        sc = B.score(ref, hyp)
        sc.pop("pairs")
        row = {"id": rec["id"], "hyp": " ".join(w["word"] for w in words), "time": rec["time"],
               "duration": rec["duration"], **sc}
        if set_name == "long":
            tc = B.timing_check(it["segments"], eng, hyp)
            for k in timing:
                timing[k] += tc[k]
            row.update(tc)
        per.append(row)
    agg = B.aggregate(per)
    agg["rtf"] = sum(r["time"] for r in per) / max(1e-9, sum(r["duration"] for r in per))
    agg["audio_min"] = sum(r["duration"] for r in per) / 60.0
    agg["items"] = len(per)
    agg["apos_split_per_1k"] = 1000.0 * apos_split / raw_words if raw_words else None
    if set_name == "long":
        agg.update(timing)
        agg["off_sync_pct"] = 100.0 * timing["off_sync"] / max(1, timing["aligned"])
    return agg, per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="CT2 Whisper model papkasi")
    ap.add_argument("--set", default="short", choices=["short", "long"])
    ap.add_argument("--limit", type=int, help="nechta yozuv (default: short - 150, long - hammasi)")
    ap.add_argument("--config", action="append", default=[])
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--threads", type=int, default=0, help="0 - plagindagidek (CTranslate2 o'zi tanlaydi)")
    ap.add_argument("--engine", help="Engine papkasi: transcribe.py ni o'zini subprocess bilan ishga tushirish")
    ap.add_argument("--tag", help="natija papkasi nomi (default - model papkasi nomi)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    items = load_set(a.set, a.limit if a.limit is not None else (150 if a.set == "short" else 0))
    tag = a.tag or os.path.basename(os.path.normpath(a.model))
    outdir = os.path.join(HERE, "out", tag, a.set)
    os.makedirs(outdir, exist_ok=True)
    eng = B.load_engine()
    configs = a.config or ["base"]
    if a.engine:
        configs = ["engine"]

    model = None
    for name in configs:
        path = os.path.join(outdir, name + ".json")
        if os.path.exists(path) and not a.force:
            print("bor, o'tkazildi:", path)
            continue
        print("== %s / %s / %s (%d ta, %.1f daqiqa)" % (tag, a.set, name, len(items), sum(i["duration"] for i in items) / 60), flush=True)
        if a.engine:
            recs, post, kw = engine_subprocess(a.engine, a.model, items), [], {"engine": a.engine}
        else:
            kw, post = make_config(name)
            if model is None:
                from faster_whisper import WhisperModel
                t0 = time.perf_counter()
                model = WhisperModel(a.model, device="cpu", compute_type=a.compute_type, cpu_threads=a.threads)
                print("model yuklandi: %.1f s" % (time.perf_counter() - t0), flush=True)
            recs = transcribe_items(model, items, kw)
        agg, per = evaluate(eng, a.set, items, recs, post)
        res = {"model": a.model, "set": a.set, "config": name, "kwargs": kw, "post": post,
               "compute_type": a.compute_type, "threads": a.threads, "cpu_count": os.cpu_count(),
               "summary": agg, "items": per, "raw": recs}
        with open(path + ".part", "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False)
        os.replace(path + ".part", path)
        print("   WER %.2f%%  CER %.2f%%  RTF %.3f  (S %d / D %d / I %d, -ning->-ni %d)"
              % (agg["wer"], agg["cer"], agg["rtf"], agg["sub"], agg["del"], agg["ins"], agg["ning_ni"]), flush=True)


if __name__ == "__main__":
    main()
