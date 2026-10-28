"""runtime-<arch>.tar.gz ichidagi barcha Mach-O fayllarni statik tekshirish.

- arxitektura to'g'rimi (arm64 / x86_64)
- LC_CODE_SIGNATURE bormi (arm64 da imzosiz kod umuman ishlamaydi)
- har bir LC_LOAD_DYLIB tar ichida yoki macOS tizim kutubxonasida topiladimi
- minimal macOS versiyasi (LC_BUILD_VERSION / LC_VERSION_MIN_MACOSX)
"""
import posixpath
import struct
import sys
import tarfile

CPU = {"arm64": 0x0100000C, "x86_64": 0x01000007}
LC_REQ_DYLD = 0x80000000
DYLIB_CMDS = {0xC, 0x80000018, 0x8000001F, 0x20, 0x80000023}
LC_RPATH = 0x8000001C
LC_BUILD_VERSION = 0x32
LC_VERSION_MIN_MACOSX = 0x24
LC_CODE_SIGNATURE = 0x1D
SYSTEM_PREFIXES = ("/usr/lib/", "/System/Library/")


def ver(v):
    return f"{v >> 16}.{(v >> 8) & 0xff}"


def parse_slice(buf, off):
    magic = struct.unpack_from("<I", buf, off)[0]
    if magic != 0xFEEDFACF:
        return None
    cputype, _sub, _ftype, ncmds, _sz, _flags = struct.unpack_from("<iiIIII", buf, off + 4)
    p = off + 32
    info = {"cpu": cputype & 0xFFFFFFFF, "deps": [], "rpaths": [], "minos": None, "signed": False}
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", buf, p)
        if cmd in DYLIB_CMDS:
            name_off = struct.unpack_from("<I", buf, p + 8)[0]
            name = buf[p + name_off:p + cmdsize].split(b"\0", 1)[0].decode()
            info["deps"].append((name, cmd == 0x80000018))
        elif cmd == LC_RPATH:
            name_off = struct.unpack_from("<I", buf, p + 8)[0]
            info["rpaths"].append(buf[p + name_off:p + cmdsize].split(b"\0", 1)[0].decode())
        elif cmd == LC_BUILD_VERSION:
            _plat, minos = struct.unpack_from("<II", buf, p + 8)
            info["minos"] = minos
        elif cmd == LC_VERSION_MIN_MACOSX and info["minos"] is None:
            info["minos"] = struct.unpack_from("<I", buf, p + 8)[0]
        elif cmd == LC_CODE_SIGNATURE:
            info["signed"] = True
        p += cmdsize
    return info


def parse_macho(buf, want_cpu):
    if len(buf) < 32:
        return None, None
    be = struct.unpack_from(">I", buf, 0)[0]
    if be in (0xCAFEBABE, 0xCAFEBABF):  # universal (fat)
        nfat = struct.unpack_from(">I", buf, 4)[0]
        if nfat > 20:
            return None, None  # java class fayli bo'lishi mumkin
        is64 = be == 0xCAFEBABF
        archs = []
        for i in range(nfat):
            if is64:
                cpu, _s, off, _size, _al, _r = struct.unpack_from(">iiQQII", buf, 8 + i * 32)
            else:
                cpu, _s, off, _size, _al = struct.unpack_from(">iiIII", buf, 8 + i * 20)
            archs.append(cpu & 0xFFFFFFFF)
            if cpu & 0xFFFFFFFF == want_cpu:
                return parse_slice(buf, off), "fat"
        return {"cpu": None, "fat_archs": archs}, "fat"
    if struct.unpack_from("<I", buf, 0)[0] == 0xFEEDFACF:
        return parse_slice(buf, 0), "thin"
    return None, None


def main(path, arch):
    want = CPU[arch]
    tar = tarfile.open(path)
    members = {m.name: m for m in tar.getmembers()}

    def resolve(p, depth=0):
        """tar ichidagi yo'lni symlinklarni kuzatib hal qiladi."""
        p = posixpath.normpath(p)
        m = members.get(p)
        if m is None:
            # ota papkalardan birortasi symlink bo'lishi mumkin
            parts = p.split("/")
            for i in range(1, len(parts)):
                head = "/".join(parts[:i])
                hm = members.get(head)
                if hm is not None and hm.issym() and depth < 10:
                    tgt = posixpath.join(posixpath.dirname(head), hm.linkname)
                    return resolve(posixpath.join(tgt, *parts[i:]), depth + 1)
            return None
        if m.issym() and depth < 10:
            return resolve(posixpath.join(posixpath.dirname(p), m.linkname), depth + 1)
        return p

    exe = resolve("runtime/bin/python3")
    machos = {}
    for m in tar.getmembers():
        if not m.isfile() or m.size < 64:
            continue
        f = tar.extractfile(m)
        head = f.read(4)
        if head not in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
            continue
        buf = head + f.read()
        info, kind = parse_macho(buf, want)
        if info is None:
            continue
        machos[m.name] = (info, kind)

    exe_info = machos[exe][0]
    problems = []
    minos_all = {}
    unsigned = []
    sys_deps = set()
    for name, (info, kind) in sorted(machos.items()):
        if info.get("cpu") != want:
            problems.append(f"ARXITEKTURA: {name} ({kind}, {info.get('fat_archs')})")
            continue
        if not info["signed"]:
            unsigned.append(name)
        if info["minos"]:
            minos_all[name] = info["minos"]
        loader_dir = posixpath.dirname(name)
        for dep, weak in info["deps"]:
            if dep.startswith("/"):
                if dep.startswith(SYSTEM_PREFIXES):
                    sys_deps.add(dep)
                else:
                    problems.append(f"TIZIMDAN TASHQARI ABSOLYUT YO'L: {name} -> {dep}")
                continue
            cands = []
            if dep.startswith("@loader_path/"):
                cands.append(posixpath.join(loader_dir, dep[len("@loader_path/"):]))
            elif dep.startswith("@executable_path/"):
                cands.append(posixpath.join(posixpath.dirname(exe), dep[len("@executable_path/"):]))
            elif dep.startswith("@rpath/"):
                rest = dep[len("@rpath/"):]
                for rp in info["rpaths"] + exe_info["rpaths"]:
                    base = rp.replace("@loader_path", loader_dir).replace(
                        "@executable_path", posixpath.dirname(exe))
                    cands.append(posixpath.join(base, rest))
            else:
                cands.append(posixpath.join(loader_dir, dep))
            if not any(resolve(c) for c in cands):
                tag = "ZAIF (weak)" if weak else "TOPILMADI"
                problems.append(f"{tag}: {name} -> {dep}  (qidirildi: {cands})")

    top = sorted(minos_all.items(), key=lambda kv: -kv[1])[:6]
    print(f"== {path.rsplit(chr(92), 1)[-1]}  [{arch}]")
    print(f"   Mach-O fayllar: {len(machos)}   python: {exe}")
    print(f"   Eng yuqori minimal macOS talablari:")
    for n, v in top:
        print(f"      macOS {ver(v):6} {n}")
    print(f"   Imzosiz Mach-O: {len(unsigned)}" + ("" if not unsigned else f"  {unsigned[:8]}"))
    print(f"   Tizim kutubxonalari ({len(sys_deps)}): " + ", ".join(sorted(d.rsplit('/', 1)[-1] for d in sys_deps)))
    if problems:
        print(f"   MUAMMOLAR ({len(problems)}):")
        for p in problems:
            print("      " + p)
    else:
        print("   MUAMMO YO'Q: barcha bog'liqliklar hal qilindi")
    return 1 if problems or (arch == "arm64" and unsigned) else 0


if __name__ == "__main__":
    rc = 0
    for spec in sys.argv[1:]:
        p, a = spec.rsplit("=", 1)
        rc |= main(p, a)
    sys.exit(rc)
