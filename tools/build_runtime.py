"""Mac uchun portativ Python runtime yig'ish (Windows'da ishlaydi).

python-build-standalone tarball + macOS wheel'lar -> runtime-<arch>.tar.gz
Tar ichida ildiz papka "runtime/", symlink va ruxsatlar (0755) saqlanadi,
shuning uchun Mac'da `tar -xzf` qilingach python3 darhol ishga tushadi.
"""
import glob
import io
import os
import shutil
import subprocess
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DL = os.path.join(HERE, "dl")
OUT = os.path.join(HERE, "out")
PYVER = "3.13"
PBS = {
    "arm64": "cpython-3.13.15+20260901-aarch64-apple-darwin-install_only_stripped.tar.gz",
    "x86_64": "cpython-3.13.15+20260901-x86_64-apple-darwin-install_only_stripped.tar.gz",
}
NOW = int(time.time())


def pip_install_target(arch, target):
    if os.path.exists(target):
        shutil.rmtree(target)
    wheels = sorted(glob.glob(os.path.join(DL, f"wheels-{arch}", "*.whl")))
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
           "--no-index", "--no-deps", "--no-compile", "--only-binary=:all:",
           "--platform", f"macosx_11_0_{arch}", "--python-version", "313",
           "--implementation", "cp", "--abi", "cp313",
           "--target", target] + wheels
    subprocess.run(cmd, check=True)
    # pip Windows'da console-script .exe launcher yasaydi - Mac'ga keraksiz
    junk = os.path.join(target, "bin")
    if os.path.isdir(junk):
        shutil.rmtree(junk)
    for root, dirs, _ in os.walk(target):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d))
                dirs.remove(d)
    return len(wheels)


def add_tree(tar, src_dir, arc_prefix):
    count = 0
    for root, dirs, files in os.walk(src_dir):
        dirs.sort()
        rel_root = os.path.relpath(root, src_dir).replace("\\", "/")
        arc_root = arc_prefix if rel_root == "." else f"{arc_prefix}/{rel_root}"
        if rel_root != ".":
            ti = tarfile.TarInfo(arc_root)
            ti.type = tarfile.DIRTYPE
            ti.mode = 0o755
            ti.mtime = NOW
            tar.addfile(ti)
        for fn in sorted(files):
            full = os.path.join(root, fn)
            ti = tarfile.TarInfo(f"{arc_root}/{fn}")
            ti.size = os.path.getsize(full)
            ti.mtime = NOW
            ti.mode = 0o755 if fn.endswith((".so", ".dylib")) else 0o644
            with open(full, "rb") as fh:
                tar.addfile(ti, fh)
            count += 1
    return count


def build(arch):
    os.makedirs(OUT, exist_ok=True)
    stage = os.path.join(HERE, f"stage-{arch}")
    n_whl = pip_install_target(arch, stage)
    out_path = os.path.join(OUT, f"runtime-{arch}.tar.gz")
    src = tarfile.open(os.path.join(DL, PBS[arch]))
    n_pbs = 0
    links = []
    with tarfile.open(out_path, "w:gz", compresslevel=9, format=tarfile.PAX_FORMAT) as tar:
        for m in src.getmembers():
            if not (m.name == "python" or m.name.startswith("python/")):
                raise SystemExit(f"kutilmagan tar a'zosi: {m.name}")
            m.name = "runtime" + m.name[len("python"):]
            n_pbs += 1
            if m.issym() or m.islnk():
                # symlinklar oxirida: nishon fayl avval ochilsin (ba'zi tar'lar tartibga sezgir)
                if m.islnk():
                    m.linkname = "runtime" + m.linkname[len("python"):]
                links.append(m)
                continue
            tar.addfile(m, src.extractfile(m) if m.isfile() else None)
        sp = f"runtime/lib/python{PYVER}/site-packages"
        n_sp = add_tree(tar, stage, sp)
        for m in links:
            tar.addfile(m)
    print(f"[{arch}] {n_whl} wheel -> {n_sp} fayl; PBS {n_pbs} a'zo; "
          f"{out_path} = {os.path.getsize(out_path)/1e6:.1f} MB")


if __name__ == "__main__":
    for a in (sys.argv[1:] or ["arm64", "x86_64"]):
        build(a)
