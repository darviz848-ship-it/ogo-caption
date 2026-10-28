"""HuggingFace Whisper modelini CTranslate2 formatiga o'giradi (bench/models/ - .gitignore'da).

  python3 bench/convert_model.py Kotib/uzbek_stt_v1 bench/models/kotib_ct2_f16
  python3 bench/convert_model.py <repo> <papka> --quantization float16 --revision <commit>

Plagindagidek: model float16 saqlanadi, transcribe.py uni compute_type="int8" bilan yuklaydi.
Talab (faqat o'girish uchun, plaginga kerak emas): pip install transformers torch huggingface_hub
Litsenziya tekshiriladi: tijoriy ishga mos bo'lmasa (apache-2.0 / mit / bsd) - to'xtaydi.
Natija papkasida SOURCE.json: repo, commit, litsenziya, hajm.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_MODEL = os.path.join(os.path.dirname(HERE), "win", "payload", "Engine", "uzbek_model")
OK_LICENSES = {"apache-2.0", "mit", "bsd", "bsd-2-clause", "bsd-3-clause"}


def dir_size(path):
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(path) for f in fs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("out")
    ap.add_argument("--quantization", default="float16")
    ap.add_argument("--revision")
    ap.add_argument("--keep-heads", action="store_true",
                    help="alignment_heads ni o'zgartirmaslik (default: 24 qatlamli Medium bo'lsa asl uzbek_model nikiga tenglanadi)")
    ap.add_argument("--any-license", action="store_true", help="faqat o'lchov uchun; plaginga qo'yib bo'lmaydi")
    a = ap.parse_args()

    from huggingface_hub import HfApi, snapshot_download
    info = HfApi().model_info(a.model, revision=a.revision)
    card = info.card_data.to_dict() if info.card_data else {}
    lic = str(card.get("license") or "").lower()
    print("model: %s  commit: %s  litsenziya: %s" % (a.model, info.sha, lic or "?"))
    if lic not in OK_LICENSES and not a.any_license:
        sys.exit("Litsenziya tijoriy ishga mos emas yoki noma'lum (%s) - to'xtadim. Faqat o'lchash uchun: --any-license" % (lic or "?"))

    files = [s.rfilename for s in (info.siblings or [])]
    weights = ["*.safetensors"] if any(f.endswith(".safetensors") for f in files) else ["*.bin"]
    local = snapshot_download(a.model, revision=info.sha,
                              allow_patterns=["*.json", "*.txt", "*.model", "*.tiktoken"] + weights)

    import ctranslate2
    copy = [f for f in ("tokenizer.json", "preprocessor_config.json") if os.path.exists(os.path.join(local, f))]
    conv = ctranslate2.converters.TransformersConverter(local, copy_files=copy,
                                                        load_as_float16=a.quantization in ("float16", "int8_float16"))
    conv.convert(a.out, quantization=a.quantization, force=True)

    if not os.path.exists(os.path.join(a.out, "tokenizer.json")):
        # faster-whisper tokenizer.json siz HuggingFace'dan yuklaydi - plagin internetsiz ishlashi uchun shart
        from transformers import WhisperTokenizerFast
        WhisperTokenizerFast.from_pretrained(local).backend_tokenizer.save(os.path.join(a.out, "tokenizer.json"))
        print("tokenizer.json transformers orqali yaratildi")

    cfg_path = os.path.join(a.out, "config.json")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    ref = json.load(open(os.path.join(REPO_MODEL, "config.json"), encoding="utf-8"))
    hf_cfg = json.load(open(os.path.join(local, "config.json"), encoding="utf-8"))
    layers = hf_cfg.get("decoder_layers")
    for k in ("lang_ids", "suppress_ids", "suppress_ids_begin", "alignment_heads"):
        same = cfg.get(k) == ref.get(k)
        print("  %-18s %s" % (k, "asl uzbek_model bilan bir xil" if same else "FARQ: %s" % str(cfg.get(k))[:120]))
    if cfg.get("alignment_heads") != ref["alignment_heads"] and layers == 24 and not a.keep_heads:
        # Fine-tune'larda generation_config.alignment_heads ko'pincha yo'q - CT2 butun yarim qatlamlarni oladi,
        # so'z vaqtlari boshqacha bo'ladi. Asl uzbek_model (Whisper Medium) dagi boshlar qo'yiladi.
        cfg["alignment_heads"] = ref["alignment_heads"]
        json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), indent=2)
        print("  alignment_heads -> asl uzbek_model nikiga tenglandi (Whisper Medium)")
    vocab = json.load(open(os.path.join(a.out, "vocabulary.json"), encoding="utf-8"))
    ref_vocab = json.load(open(os.path.join(REPO_MODEL, "vocabulary.json"), encoding="utf-8"))
    print("  vocabulary.json    %s" % ("bir xil" if vocab == ref_vocab else "FARQ (%d / %d)" % (len(vocab), len(ref_vocab))))

    src = {"repo": a.model, "commit": info.sha, "license": lic, "quantization": a.quantization,
           "decoder_layers": layers, "d_model": hf_cfg.get("d_model"), "size_mb": round(dir_size(a.out) / 1e6, 1)}
    json.dump(src, open(os.path.join(a.out, "SOURCE.json"), "w", encoding="utf-8"), indent=2)
    print("tayyor: %s (%.0f MB)" % (a.out, src["size_mb"]))


if __name__ == "__main__":
    main()
