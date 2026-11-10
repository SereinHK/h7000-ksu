#!/usr/bin/env python3
"""转储 DTB 中与背光相关的属性。"""
import struct
import sys

FDT_BEGIN_NODE, FDT_END_NODE, FDT_PROP, FDT_NOP, FDT_END = 1, 2, 3, 4, 9


def parse(path):
    d = open(path, "rb").read()
    magic, totalsize, off_struct, off_strings = struct.unpack(">IIII", d[:16])
    assert magic == 0xD00DFEED, "not a FDT"
    strs = d[off_strings:]
    nodes = []

    def walk(off, path_parts):
        while True:
            (token,) = struct.unpack(">I", d[off:off + 4])
            off += 4
            if token == FDT_BEGIN_NODE:
                end = d.index(b"\x00", off)
                name = d[off:end].decode("latin1")
                off = (end + 4) & ~3
                off = walk(off, path_parts + [name])
            elif token == FDT_END_NODE:
                return off
            elif token == FDT_PROP:
                ln, nameoff = struct.unpack(">II", d[off:off + 8])
                off += 8
                pname = strs[nameoff:].split(b"\x00")[0].decode("latin1")
                val = d[off:off + ln]
                off = (off + ln + 3) & ~3
                nodes.append(("/" + "/".join(p for p in path_parts if p), pname, val))
            elif token == FDT_NOP:
                continue
            else:
                return off

    walk(off_struct, [])
    return nodes


def main():
    needles = ("bl-", "pwm", "panel-height", "panel-width", "panel-name")
    for path in sys.argv[1:]:
        print("====", path)
        seen = set()
        for node, pname, val in parse(path):
            if not any(n in pname for n in needles):
                continue
            key = (node, pname)
            if key in seen:
                continue
            seen.add(key)
            if len(val) == 4:
                shown = str(struct.unpack(">I", val)[0])
            else:
                try:
                    shown = val.rstrip(b"\x00").decode("latin1")
                    if not shown.isprintable():
                        shown = repr(val)
                except Exception:
                    shown = repr(val)
            print(f"  {node:60s} {pname} = {shown}")
        if not seen:
            print("  (没有匹配的属性)")


if __name__ == "__main__":
    main()
