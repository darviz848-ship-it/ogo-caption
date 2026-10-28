"""OgoCaption-Mac-Setup papkasini Mac uchun ZIP ga yig'ish (Windows'da).

- Unix ruxsatlari saqlanadi (create_system=3): .command/.sh -> 0755,
  shunda Mac'da Archive Utility ochgach INSTALL.command darhol ishlaydi.
- Allaqachon siqilgan fayllar (.tar.gz, .mogrt) STORED, qolgani DEFLATED.
- Arxiv 2^31 baytdan kichik bo'lishi kerak - zip64 yozuvlari chiqmasin
  (eski unzip/Archive Utility bilan muammo bo'lmasin).
"""
import os
import shutil
import sys
import zipfile

SRC = sys.argv[1]
OUT = sys.argv[2]
TOP = os.path.basename(os.path.normpath(SRC))
EXEC_EXT = (".command", ".sh")
STORED_EXT = (".tar.gz", ".mogrt", ".zip")


def order_key(rel):
    # kichik/muhim fayllar oldinda, katta payload oxirida
    return (rel.startswith("payload/"), rel)


def main():
    if os.path.exists(OUT):
        raise SystemExit(f"Allaqachon bor: {OUT}")
    files, dirs = [], []
    for root, dnames, fnames in os.walk(SRC):
        for d in dnames:
            dirs.append(os.path.relpath(os.path.join(root, d), SRC).replace("\\", "/"))
        for f in fnames:
            files.append(os.path.relpath(os.path.join(root, f), SRC).replace("\\", "/"))
    tmp = OUT + ".part"
    with zipfile.ZipFile(tmp, "w", allowZip64=True) as zf:
        zi = zipfile.ZipInfo(TOP + "/")
        zi.create_system = 3
        zi.external_attr = (0o40755 << 16) | 0x10
        zf.writestr(zi, b"")
        for d in sorted(dirs, key=order_key):
            zi = zipfile.ZipInfo(f"{TOP}/{d}/")
            zi.create_system = 3
            zi.external_attr = (0o40755 << 16) | 0x10
            zf.writestr(zi, b"")
        for rel in sorted(files, key=order_key):
            full = os.path.join(SRC, rel)
            zi = zipfile.ZipInfo.from_file(full, f"{TOP}/{rel}")
            zi.create_system = 3
            mode = 0o100755 if rel.endswith(EXEC_EXT) else 0o100644
            zi.external_attr = mode << 16
            zi.compress_type = zipfile.ZIP_STORED if rel.endswith(STORED_EXT) else zipfile.ZIP_DEFLATED
            zi._compresslevel = 6
            with open(full, "rb") as src, zf.open(zi, "w") as dst:
                shutil.copyfileobj(src, dst, 4 * 1024 * 1024)
            print(f"  + {rel}  ({os.path.getsize(full) / 1e6:.1f} MB)", flush=True)
    size = os.path.getsize(tmp)
    os.replace(tmp, OUT)
    print(f"\n{OUT}\n{size:,} bayt = {size / 1e9:.3f} GB")


if __name__ == "__main__":
    main()
