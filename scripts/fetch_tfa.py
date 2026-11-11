#!/usr/bin/env python3
"""从 GitHub 拉取 NXP tfa98xx 驱动源码到 vendor/tfa98xx/。"""
import base64
import json
import os
import subprocess
import sys
import urllib.request

REPO = "LineageOS/android_kernel_google_marlin"
REF = "lineage-15.1"
SRC_DIR = "sound/soc/codecs"
DST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor", "tfa98xx")


def token():
    out = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line[9:]
    raise SystemExit("no github credential")


TOK = token()


def api(url):
    req = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + TOK,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "dsh"},
    )
    return json.load(urllib.request.urlopen(req, timeout=60))


def main():
    items = api(f"https://api.github.com/repos/{REPO}/contents/{SRC_DIR}?ref={REF}")
    files = [e for e in items if e["type"] == "file" and e["name"].startswith("tfa")]
    os.makedirs(DST, exist_ok=True)
    total = 0
    for e in files:
        blob = api(f"https://api.github.com/repos/{REPO}/git/blobs/{e['sha']}")
        data = base64.b64decode(blob["content"])
        open(os.path.join(DST, e["name"]), "wb").write(data)
        total += len(data)
    print(f"下载 {len(files)} 个文件, {total:,} B")

    for name in ("Makefile", "Kconfig"):
        entry = next((x for x in items if x["name"] == name), None)
        if not entry:
            continue
        blob = api(f"https://api.github.com/repos/{REPO}/git/blobs/{entry['sha']}")
        txt = base64.b64decode(blob["content"]).decode("utf-8", "replace")
        print(f"--- {name} 里的 tfa 行 ---")
        for line in txt.splitlines():
            if "tfa" in line.lower():
                print("   ", line.strip())


if __name__ == "__main__":
    main()
