#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autofix-of-source.py —— 从 ninja/clang 报错里自动修掉 OrangeFox R12.1 源码自身的两类小毛病，
然后让调用方增量重编（ninja 增量，只重编受影响的目标，几十秒级）。

为什么要这个：
    这台设备的 OF 树走的是 minimal manifest，OF 自己那段代码偶尔会用 AID_* 常量却没 include
    `private/android_filesystem_config.h`。典型：

        bootable/recovery/partitionmanager.cpp:1361:74: error:
            use of undeclared identifier 'AID_MEDIA_RW'

    AID_* 就是数字 UID/GID，换算成数字即可，零依赖、零语义变化。

它修什么（只碰 bootable/recovery 之下的源码，设备树不动）：
    1) error: use of undeclared identifier 'AID_XXX'   → 换成已知数字（未知则报错不硬改）
    2) fatal error: '<some/header.h>' file not found     → 只报告，不自动改（避免猜错）

退出码：0 = 至少改了一处（值得重试）；1 = 没有可改的（放弃）
"""
import os
import re
import sys

# 常见 AID（android_filesystem_config.h 里的值，AOSP 与 Android 12 一致）
AID = {
    "AID_ROOT": 0, "AID_SYSTEM": 1000, "AID_RADIO": 1001, "AID_BLUETOOTH": 1002,
    "AID_GRAPHICS": 1003, "AID_INPUT": 1004, "AID_AUDIO": 1005, "AID_CAMERA": 1006,
    "AID_LOG": 1007, "AID_COMPASS": 1008, "AID_MOUNT": 1009, "AID_WIFI": 1010,
    "AID_ADB": 1011, "AID_INSTALL": 1012, "AID_MEDIA": 1013, "AID_DHCP": 1014,
    "AID_SDCARD_RW": 1015, "AID_VPN": 1016, "AID_KEYSTORE": 1017, "AID_USB": 1018,
    "AID_DRM": 1019, "AID_MDNSR": 1020, "AID_GPS": 1021, "AID_UNUSED1": 1022,
    "AID_MEDIA_RW": 1023, "AID_MTP": 1024, "AID_NFC": 1025, "AID_SDCARD_R": 1028,
    "AID_SHELL": 2000, "AID_CACHE": 2001, "AID_DIAG": 2002,
    "AID_SDCARD_PICS": 1033, "AID_SDCARD_AV": 1034, "AID_SDCARD_ALL": 1035,
    "AID_LOGD": 1036, "AID_SHARED_RELRO": 1037, "AID_DBUS": 1038, "AID_TLSDATE": 1039,
    "AID_MEDIA_EX": 1040, "AID_AUDIOSERVER": 1041, "AID_METRICS_COLL": 1042,
}

RE_UNDECL = re.compile(
    r"(?P<file>[A-Za-z0-9_./+-]+\.(?:cpp|cc|cxx|c|h|hpp)):(?P<line>\d+):(?P<col>\d+):\s*"
    r"error:\s*use of undeclared identifier\s*'(?P<sym>[A-Za-z_][A-Za-z0-9_]*)'")
RE_MISSING = re.compile(r"fatal error:\s*'(?P<hdr>[^']+)' file not found")

PROTECTED = ("/device/", "/vendor/", "/prebuilt/", "/out/")


def is_protected(path):
    p = path.replace("\\", "/")
    return any(k in p for k in PROTECTED)


def main():
    if len(sys.argv) < 3:
        print("usage: autofix-of-source.py <build.log> <FOX_DIR>")
        return 1
    logp, foxdir = sys.argv[1], sys.argv[2]
    if not os.path.exists(logp):
        print("日志不存在:", logp)
        return 1
    txt = open(logp, encoding="utf-8", errors="replace").read()

    patches = {}          # file -> {sym: value}
    unknown, missing = [], []
    for m in RE_UNDECL.finditer(txt):
        sym, f = m.group("sym"), m.group("file")
        if is_protected(f):
            continue
        if sym in AID:
            patches.setdefault(f, {})[sym] = AID[sym]
        elif sym.startswith("AID_"):
            unknown.append(sym)
    for m in RE_MISSING.finditer(txt):
        missing.append(m.group("hdr"))

    if not patches:
        if unknown:
            print("!! 有未知 AID 常量，不敢猜：", sorted(set(unknown)))
        if missing:
            print("!! 缺头文件（本脚本不自动处理）：", sorted(set(missing)))
        print("没有可自动修复的项")
        return 1

    changed = 0
    for rel, syms in sorted(patches.items()):
        cand = [os.path.join(foxdir, rel), os.path.join(foxdir, os.path.relpath(rel)),
                rel if os.path.isabs(rel) else None]
        path = next((c for c in cand if c and os.path.exists(c)), None)
        if not path:
            print("!! 找不到源文件:", rel)
            continue
        s = open(path, encoding="utf-8", errors="replace").read()
        orig = s
        for sym, val in syms.items():
            cnt = s.count(sym)
            if cnt:
                s = s.replace(sym, str(val))
                print("   %s : %s -> %d （%d 处）" % (rel, sym, val, cnt))
                changed += cnt
        # 在文件头加一行说明，方便以后回溯
        if s != orig:
            banner = ("// [autofix] AID_* 常量已按 android_filesystem_config.h 的数值就地展开"
                      "（源文件未 include 该头文件；OF minimal manifest 的已知毛病）\n")
            if "[autofix]" not in s.splitlines()[0]:
                s = banner + s
            open(path, "w", encoding="utf-8").write(s)

    if changed:
        print("共替换 %d 处，可以增量重试" % changed)
        return 0
    print("没有实际改动")
    return 1


if __name__ == "__main__":
    sys.exit(main())
