#!/usr/bin/env python3
"""把 KernelSU v0.9.5 手动集成到 4.4 内核树（无 kprobe 方案）。

用法: python3 ksu_integrate.py <kernel 目录>
"""
import os
import re
import sys

PRE_EXEC = """#ifdef CONFIG_KSU
extern bool ksu_execveat_hook __read_mostly;
extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr, void *argv,
			void *envp, int *flags);
extern int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr,
				 void *argv, void *envp, int *flags);
#endif
"""

BODY_EXEC = """
#ifdef CONFIG_KSU
	if (unlikely(ksu_execveat_hook))
		ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);
	else
		ksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);
#endif
"""

PRE_FACCESSAT = """#ifdef CONFIG_KSU
extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user, int *mode,
			 int *flags);
#endif
"""

BODY_FACCESSAT = """
#ifdef CONFIG_KSU
	ksu_handle_faccessat(&dfd, &filename, &mode, NULL);
#endif
"""

PRE_VFS_READ = """#ifdef CONFIG_KSU
extern bool ksu_vfs_read_hook __read_mostly;
extern int ksu_handle_vfs_read(struct file **file_ptr, char __user **buf_ptr,
			size_t *count_ptr, loff_t **pos);
#endif
"""

BODY_VFS_READ = """
#ifdef CONFIG_KSU
	if (unlikely(ksu_vfs_read_hook))
		ksu_handle_vfs_read(&file, &buf, &count, &pos);
#endif
"""

PRE_STAT = """#ifdef CONFIG_KSU
extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);
#endif
"""

BODY_STAT = """
#ifdef CONFIG_KSU
	ksu_handle_stat(&dfd, &filename, &flag);
#endif
"""

PRE_INPUT = """#ifdef CONFIG_KSU
extern bool ksu_input_hook __read_mostly;
extern int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code, int *value);
#endif
"""

BODY_INPUT = """
#ifdef CONFIG_KSU
	if (unlikely(ksu_input_hook))
		ksu_handle_input_handle_event(&type, &code, &value);
#endif
"""

PRE_DEVPTS = """#ifdef CONFIG_KSU
extern int ksu_handle_devpts(struct inode *);
#endif
"""

BODY_DEVPTS = """
#ifdef CONFIG_KSU
	ksu_handle_devpts(pts_inode);
#endif
"""

OPS = [
    # (文件, 函数正则, 锚点正则, 函数前的 extern, 函数体内的插入)
    ("fs/exec.c", r"^static int do_execveat_common\(", r"^\tint retval;\s*$", PRE_EXEC, BODY_EXEC),
    ("fs/open.c", r"^SYSCALL_DEFINE3\(faccessat,", r"^\tunsigned int lookup_flags = LOOKUP_FOLLOW;\s*$", PRE_FACCESSAT, BODY_FACCESSAT),
    ("fs/read_write.c", r"^ssize_t vfs_read\(", r"^\tssize_t ret;\s*$", PRE_VFS_READ, BODY_VFS_READ),
    ("fs/stat.c", r"^int vfs_fstatat\(", r"^\tunsigned int lookup_flags = 0;\s*$", PRE_STAT, BODY_STAT),
    ("drivers/input/input.c", r"^static void input_handle_event\(", r"^\tdisposition = input_get_disposition\(dev, type, code, &value\);\s*$", PRE_INPUT, BODY_INPUT),
    ("fs/devpts/inode.c", r"^void \*devpts_get_priv\(", r"^\{\s*$", PRE_DEVPTS, BODY_DEVPTS),
]


def apply(root):
    ok = True
    for rel, func_re, anchor_re, pre, body in OPS:
        path = os.path.join(root, rel)
        s = open(path, encoding="utf-8", errors="surrogateescape").read()
        if "CONFIG_KSU" in s and ("ksu_execveat_hook" in s or "ksu_handle_" in s):
            print(f"[skip] {rel} 已打过补丁")
            continue
        # 1) 先在函数前插入 extern
        m = re.search(func_re, s, re.M)
        if not m:
            print(f"[FAIL] {rel}: 找不到函数 {func_re}")
            ok = False
            continue
        s = s[: m.start()] + pre + s[m.start():]
        # 2) 重新定位函数，找锚点插入函数体
        m = re.search(func_re, s, re.M)
        a = re.compile(anchor_re, re.M).search(s, m.end())
        if not a:
            print(f"[FAIL] {rel}: 找不到锚点 {anchor_re}")
            ok = False
            continue
        s = s[: a.end()] + body + s[a.end():]
        open(path, "w", encoding="utf-8", errors="surrogateescape").write(s)
        print(f"[ok] {rel}")
    return ok


def wire(root):
    # drivers/Makefile
    mk = os.path.join(root, "drivers/Makefile")
    s = open(mk).read()
    if "kernelsu" not in s:
        if not s.endswith("\n"):
            s += "\n"
        s += "\nobj-$(CONFIG_KSU) += kernelsu/\n"
        open(mk, "w").write(s)
        print("[ok] drivers/Makefile")
    else:
        print("[skip] drivers/Makefile")
    # drivers/Kconfig
    kc = os.path.join(root, "drivers/Kconfig")
    s = open(kc).read()
    if "kernelsu/Kconfig" not in s:
        idx = s.rfind("endmenu")
        if idx < 0:
            raise SystemExit("drivers/Kconfig: 找不到 endmenu")
        s = s[:idx] + 'source "drivers/kernelsu/Kconfig"\n\n' + s[idx:]
        open(kc, "w").write(s)
        print("[ok] drivers/Kconfig")
    else:
        print("[skip] drivers/Kconfig")
    # 固定 KSU_VERSION（免去 .git 依赖）
    kmk = os.path.join(root, "drivers/kernelsu/Makefile")
    s = open(kmk).read()
    s = s.replace("-DKSU_VERSION=16", "-DKSU_VERSION=11872")
    open(kmk, "w").write(s)
    print("[ok] kernelsu/Makefile (KSU_VERSION=11872)")


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    wire(root)
    if not apply(root):
        raise SystemExit(1)
    print("KernelSU 集成完成")
