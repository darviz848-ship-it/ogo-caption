"""bench/out/<model>/<set>/*.json natijalaridan jadval: sozlama -> WER / CER / RTF (+ xato turlari).

  python3 bench/summarize.py [model_tag ...]      -> bench/out/<model_tag>/table.md
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def table(tag):
    out = []
    for set_name in ("short", "long"):
        files = sorted(glob.glob(os.path.join(HERE, "out", tag, set_name, "*.json")))
        if not files:
            continue
        rows = {os.path.basename(f)[:-5]: json.load(open(f, encoding="utf-8"))["summary"] for f in files}
        base = rows.get("base")
        first = next(iter(rows.values()))
        out.append("### %s - %s (%d ta yozuv, %.1f daqiqa audio)\n" % (tag, set_name, first["items"], first["audio_min"]))
        head = "| sozlama | yozuv | WER % | ΔWER | CER % | RTF | S / D / I | -ning→-ni |"
        sep = "|---|---:|---:|---:|---:|---:|---|---:|"
        if set_name == "long":
            head += " musiqa/sukutda so'z | vaqti siljigan % |"
            sep += "---:|---:|"
        out += [head, sep]
        order = sorted(rows, key=lambda k: (k != "base", rows[k]["wer"]))
        for k in order:
            r = rows[k]
            d = "" if base is None or k == "base" else "%+.2f" % (r["wer"] - base["wer"])
            line = "| %s | %d | %.2f | %s | %.2f | %.3f | %d / %d / %d | %d |" % (
                k, r["items"], r["wer"], d, r["cer"], r["rtf"], r["sub"], r["del"], r["ins"], r["ning_ni"])
            if set_name == "long":
                line += " %d | %.2f |" % (r["halluc"], r["off_sync_pct"])
            out.append(line)
        out.append("")
    return "\n".join(out)


def main():
    tags = sys.argv[1:] or sorted(d for d in os.listdir(os.path.join(HERE, "out"))
                                  if os.path.isdir(os.path.join(HERE, "out", d)))
    for tag in tags:
        md = table(tag)
        if md:
            open(os.path.join(HERE, "out", tag, "table.md"), "w", encoding="utf-8").write(md)
            print(md)


if __name__ == "__main__":
    main()
