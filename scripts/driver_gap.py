#!/usr/bin/env python3
"""找出 DT 里声明了、但内核树里没有驱动匹配的 compatible。

用法: python3 driver_gap.py <dtb 文件或目录> <kernel 裸仓库路径>
"""
import os
import re
import struct
import subprocess
import sys

FDT_BEGIN_NODE, FDT_END_NODE, FDT_PROP, FDT_NOP = 1, 2, 3, 4


def parse_compat(dtb):
    d = open(dtb, "rb").read()
    magic, _, off_struct, off_strings = struct.unpack(">IIII", d[:16])
    if magic != 0xD00DFEED:
        return []
    strs = d[off_strings:]
    out = []

    def walk(off, path):
        while True:
            (token,) = struct.unpack(">I", d[off:off + 4])
            off += 4
            if token == FDT_BEGIN_NODE:
                end = d.index(b"\x00", off)
                name = d[off:end].decode("latin1")
                off = (end + 4) & ~3
                off = walk(off, path + "/" + name)
            elif token == FDT_END_NODE:
                return off
            elif token == FDT_PROP:
                ln, nameoff = struct.unpack(">II", d[off:off + 8])
                off += 8
                pname = strs[nameoff:].split(b"\x00")[0].decode("latin1")
                val = d[off:off + ln]
                off = (off + ln + 3) & ~3
                if pname == "compatible":
                    for c in val.split(b"\x00"):
                        if c:
                            out.append((path, c.decode("latin1")))
            elif token == FDT_NOP:
                continue
            else:
                return off

    walk(off_struct, "")
    return out


def tree_compatibles(repo):
    """内核树里所有源码中出现过的 compatible 字符串"""
    res = subprocess.run(
        ["git", "--git-dir", repo, "grep", "-I", "-h", "-o", r'"[a-z0-9][a-z0-9,._+-]*,[a-z0-9,._+-]*"', "HEAD", "--",
         "drivers", "sound", "arch/arm/boot/dts", "arch/arm64/boot/dts"],
        capture_output=True, text=True, errors="replace",
    )
    s = set()
    for line in res.stdout.splitlines():
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            s.add(line[1:-1])
    return s


def main():
    dtb_or_dir, repo = sys.argv[1], sys.argv[2]
    dtbs = []
    if os.path.isdir(dtb_or_dir):
        dtbs = [os.path.join(dtb_or_dir, f) for f in sorted(os.listdir(dtb_or_dir)) if f.endswith(".dtb")]
    else:
        dtbs = [dtb_or_dir]

    known = tree_compatibles(repo)
    print(f"内核树里的 compatible 字符串: {len(known)}")

    all_compat = {}
    for f in dtbs:
        for path, c in parse_compat(f):
            all_compat.setdefault(c, path)

    missing = {c: p for c, p in all_compat.items() if c not in known}
    print(f"DT 里出现的 compatible: {len(all_compat)}，可能缺驱动的: {len(missing)}\n")
    for c in sorted(missing, key=lambda x: (missing[x], x)):
        print(f"  {c:45s}  {missing[c]}")


if __name__ == "__main__":
    main()
