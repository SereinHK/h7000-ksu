#!/usr/bin/env python3
"""检查 mixer_paths.xml 中播放路径需要的 mixer 控件在内核里是否存在。

用法: python3 mixer_paths_check.py <mixer_paths.xml> <tinymix.txt> [路径名...]
"""
import re
import sys


def parse_paths(xml_path):
    t = open(xml_path, encoding="utf-8", errors="replace").read()
    paths = {}
    for m in re.finditer(r'<path name="([^"]+)">(.*?)</path>', t, re.S):
        name, body = m.group(1), m.group(2)
        ctls = []
        for c in re.finditer(r'<ctl name="([^"]+)" value="([^"]*)"', body):
            ctls.append((c.group(1), c.group(2)))
        subs = re.findall(r'<path name="([^"]+)"', body)
        paths[name] = (ctls, subs)
    return paths


def resolve(paths, name, seen=None):
    """展开嵌套 path，返回所有 (ctl, value)"""
    if seen is None:
        seen = set()
    if name in seen or name not in paths:
        return []
    seen.add(name)
    ctls, subs = paths[name]
    out = list(ctls)
    for s in subs:
        out += resolve(paths, s, seen)
    return out


def mixer_names(tinymix_path):
    names = set()
    for line in open(tinymix_path, encoding="utf-8", errors="replace"):
        parts = line.split("\t")
        if len(parts) >= 4 and parts[0].strip().isdigit():
            names.add(re.split(r"\s{2,}", parts[3].strip())[0])
    return names


def main():
    xml_path, tm_path = sys.argv[1], sys.argv[2]
    targets = sys.argv[3:] or ["speaker", "deep-buffer-playback", "low-latency-playback", "compress-offload-playback"]
    paths = parse_paths(xml_path)
    tm = mixer_names(tm_path)
    print(f"mixer_paths 里定义 path: {len(paths)} 个；内核控件: {len(tm)} 个\n")
    for t in targets:
        if t not in paths:
            print(f"!! path 不存在: {t}")
            continue
        need = resolve(paths, t)
        missing = [(c, v) for c, v in need if c not in tm]
        print(f"=== {t}: 需要 {len(need)} 个控件，缺失 {len(missing)} ===")
        for c, v in missing[:12]:
            print(f"   缺: {c} = {v}")
        if not missing:
            print("   （全部存在）")


if __name__ == "__main__":
    main()
