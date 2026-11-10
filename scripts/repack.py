#!/usr/bin/env python3
"""把编译出来的 ARM64 Image 打包成 H7000 可刷的 boot.img。

布局（有 ramdisk 时）：
  [1 页 boot header][gzip(Image)+DTB][补齐 4K][ramdisk][补齐 4K][1,320 B verity 证书]

没有 assets/ramdisk.cpio.gz 时退回原布局（内核+DTB 后面直接接证书）。

用法: python3 repack.py <Image> <assets 目录> <输出目录>
"""
import os
import struct
import sys
import zlib

PAGE = 4096


def gzip_kernel(payload: bytes) -> bytes:
    """按官方镜像的 gzip 头打包（mtime=0, XFL=2, OS=3）"""
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    body = co.compress(payload) + co.flush()
    hdr = b"\x1f\x8b\x08\x00" + b"\x00\x00\x00\x00" + bytes([2, 3])
    trailer = struct.pack("<II", zlib.crc32(payload) & 0xFFFFFFFF, len(payload) & 0xFFFFFFFF)
    return hdr + body + trailer


def main() -> int:
    image_path, assets, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    img = open(image_path, "rb").read()
    print(f"Image: {len(img):,} B")

    if img[0x38:0x3C] != b"ARMd":
        print("WARNING: 这不是标准的 ARM64 Image（0x38 处没有 ARM\\x64 magic）", file=sys.stderr)

    hdr = bytearray(open(os.path.join(assets, "boot_hdr.bin"), "rb").read())
    cert = open(os.path.join(assets, "verity_cert.bin"), "rb").read()

    dtb_dir = os.path.join(assets, "dtbs")
    dtbs = []
    for name in sorted(os.listdir(dtb_dir)):
        if name.endswith(".dtb"):
            blob = open(os.path.join(dtb_dir, name), "rb").read()
            if blob[:4] != b"\xd0\x0d\xfe\xed":
                print(f"WARNING: {name} 不是 FDT", file=sys.stderr)
            dtbs.append(blob)
    print(f"DTB: {len(dtbs)} 个, 共 {sum(map(len, dtbs)):,} B")

    rd_path = os.path.join(assets, "ramdisk.cpio.gz")
    ramdisk = open(rd_path, "rb").read() if os.path.exists(rd_path) else b""
    if ramdisk:
        print(f"ramdisk: {len(ramdisk):,} B")

    gz = gzip_kernel(img)
    kernel_size = len(gz) + sum(map(len, dtbs))
    print(f"gzip: {len(gz):,} B  -> kernel_size={kernel_size:#x}")
    struct.pack_into("<I", hdr, 8, kernel_size)
    struct.pack_into("<I", hdr, 16, len(ramdisk))

    body = bytes(hdr) + gz + b"".join(dtbs)
    if ramdisk:
        body += b"\x00" * ((-len(body)) % PAGE)
        body += ramdisk
        body += b"\x00" * ((-len(body)) % PAGE)
    boot = body + cert

    os.makedirs(outdir, exist_ok=True)
    dst = os.path.join(outdir, "boot.img")
    with open(dst, "wb") as f:
        f.write(boot)
    print(f"boot.img: {len(boot):,} B ({len(boot):#x})  -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
