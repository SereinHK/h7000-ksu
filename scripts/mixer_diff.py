#!/usr/bin/env python3
"""对比 HAL 用的 mixer_paths XML 里的控件名 与 内核实际暴露的 tinymix 控件名。"""
import re
import sys


def mixer_names(path):
    names = set()
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.search(r'name="([^"]+)"', line)
        if m:
            names.add(m.group(1).strip())
    return names


def tinymix_names(path):
    names = set()
    for line in open(path, encoding="utf-8", errors="replace"):
        parts = line.split("\t")
        if len(parts) >= 4 and parts[0].strip().isdigit():
            names.add(parts[3].strip())
    return names


def main():
    tm = tinymix_names(sys.argv[1])
    print(f"tinymix 控件: {len(tm)}")
    for xml in sys.argv[2:]:
        want = mixer_names(xml)
        missing = sorted(want - tm)
        print(f"\n=== {xml.split('/')[-1]}: XML 里 {len(want)} 个控件，缺失 {len(missing)} 个 ===")
        for n in missing[:15]:
            print("  缺:", n)


if __name__ == "__main__":
    main()
