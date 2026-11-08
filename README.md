# h7000-ksu

步步高家教机 S5（H7000，SDM660）的内核编译仓库：用 GitHub Actions 云编译 `kernel_h7000_bbk`，
并打包成可直接刷入的 `boot.img`。

## 第一步：编译原样内核（验证源码可用）

1. 打开仓库的 **Actions** 页面 → 左侧 `build-h7000-kernel` → 右侧 **Run workflow** → 运行；
2. 等约 10~20 分钟，下载 artifact `boot-img`；
3. 里面的 `boot.img` 就是成品，用 TWRP 刷：

   ```
   TWRP → Install → Install Image → 选择 boot.img → 勾选 Boot → 刷入
   ```

4. 重启看能不能过 logo：
   - **能开机** → 说明这份源码就是能用的那份，可以进入第二步（加 KernelSU）；
   - **不能开机** → 说明它不是当年编 MIUI 内核的那棵树，需要找 ROM 作者要正确的内核源码。

刷回官方：把 `1\boot.img`（20,653,352 B，SHA-256 `0736127…fef9`）同样用 TWRP 刷回 Boot 即可。

## 目录

```
.github/workflows/build.yml   云编译流程
scripts/repack.py             把 Image 打包成 boot.img
assets/boot_hdr.bin           官方 boot header（4 KB，运行时只改 kernel_size）
assets/verity_cert.bin        官方尾部 1,320 B verity 证书
assets/dtbs/*.dtb             从官方镜像提取的 31 个 DTB（sdm660，保持原样最稳）
```

## 说明

- 内核用 `h7000_defconfig`，工具链为 AOSP/LineageOS 的 `aarch64-linux-android-4.9`（与官方内核的 GCC 4.9 一致）；
- 这棵树的 `arch/arm64/boot/dts/qcom/` 是空的、`arch/arm/boot/dts/Makefile` 里也没有 sdm660 的条目，
  所以 **DTB 不自己编**，直接复用官方镜像里的 31 个（DTB 是纯数据，和内核补丁无关）；
- 打包布局与官方逐字节同构：`[header][gzip][DTB…][4K 对齐][verity 证书]`，`kernel_size` 动态计算。

## 第二步（待办）：KernelSU

确认内核能开机后再做：

- 版本只能用 **KernelSU v0.9.5**（1.0 之后官方不再支持非 GKI）；
- 本内核 `CONFIG_KPROBES` 未开 → 走**手动集成**：`fs/exec.c`、`fs/open.c`、`fs/read_write.c`、`fs/stat.c`、`drivers/input/input.c`、`fs/devpts/inode.c`；
- defconfig 追加 `CONFIG_KSU=y`。
