"""HuggingFace'dagi o'zbekcha ASR modellarini qidiradi va litsenziyasi bo'yicha saralaydi.

  python3 bench/find_models.py            -> bench/out/candidates.md
Tijoriy ishga mos: apache-2.0 / mit / bsd. CC-BY-NC va litsenziyasizlar alohida ko'rsatiladi (ishlatilmaydi).
Modelni plaginga O'ZIMIZ almashtirmaymiz - faqat o'lchab tavsiya qilamiz (Lochin hal qiladi).
"""
import os

from huggingface_hub import HfApi

HERE = os.path.dirname(os.path.abspath(__file__))
OK = {"apache-2.0", "mit", "bsd", "bsd-2-clause", "bsd-3-clause"}


def main():
    api = HfApi()
    seen, rows = set(), []
    queries = [dict(language="uz", pipeline_tag="automatic-speech-recognition"),
               dict(search="uzbek", pipeline_tag="automatic-speech-recognition"),
               dict(search="whisper uz")]
    for q in queries:
        for m in api.list_models(limit=300, sort="downloads", cardData=True, **q):
            if m.id in seen:
                continue
            seen.add(m.id)
            card = m.card_data.to_dict() if getattr(m, "card_data", None) else {}
            lic = str(card.get("license") or "").lower()
            tags = set(m.tags or [])
            if not any("whisper" in t for t in tags | {m.id.lower()}):
                continue
            base = card.get("base_model")
            rows.append((lic in OK, m.downloads or 0, m.id, lic or "?", str(base or "?")[:60],
                         "turbo" if "turbo" in m.id.lower() or "turbo" in str(base).lower() else ""))
    rows.sort(key=lambda r: (not r[0], -r[1]))
    lines = ["| tijoriy | yuklashlar | model | litsenziya | asos | |", "|---|---:|---|---|---|---|"]
    lines += ["| %s | %d | %s | %s | %s | %s |" % ("ha" if ok else "YO'Q", d, i, l, b, t) for ok, d, i, l, b, t in rows]
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    path = os.path.join(HERE, "out", "candidates.md")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:40]))
    print("\n->", path)


if __name__ == "__main__":
    main()
