#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify-recovery.py —— TB331FC 的 OrangeFox recovery.img 出厂体检（只读，纯 stdlib）

用法：
    python3 ci/verify-recovery.py out/recovery_fox.img
    python3 ci/verify-recovery.py out/recovery_fox.img --max-ramdisk 31707004 --expect-size 104857600
    python3 ci/verify-recovery.py out/recovery_fox.img --inspect      # 额外列 ramdisk 内容（需 lz4+cpio）

判据（任一 FAIL ⇒ 退出码 1）：
  1  Android Boot Header 魔数 "ANDROID!"
  2  header_version == 4
  3  header_size == 1584
  4  kernel_size == 0（ramdisk-only；内核在 boot.img 里）
  5  cmdline 全零（Lenovo ABL 对非空 cmdline 有缺陷）
  6  ramdisk 压缩魔数 == 02 21 4c 18（legacy LZ4；内核 CONFIG_RD_LZ4=y）
  7  ramdisk_size ≤ --max-ramdisk（默认 31,707,004 = ABL 单项上限，K=0x29C0000 口径）
  8  文件长度 ≤ 104,857,600（recovery 分区物理大小）；给了 --expect-size 则要求相等

预算口径（**不要**再减 vendor/init_boot —— 那是总量口径，不是单项口径）：
    ABL 单项上限 31,707,004 B（K = 现役 KSU 内核 0x29C0000 = 43,778,048）
    已实测能启动的参考镜像：recovery_hx_fw.img，ramdisk 21,618,637 B
"""
import argparse
import struct
import subprocess
import sys

LZ4_LEGACY = bytes.fromhex("02214c18")
ABL_RAMDISK_LIMIT = 31707004       # 单项上限（K = 0x29C0000）
PROVEN_BOOTABLE = 21618637         # recovery_hx_fw.img 的 ramdisk：真机启动 + himax 触摸注册
PARTITION_SIZE = 104857600         # recovery 分区物理大小
HDR_SIZE_EXPECT = 1584

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("  PASS  " if ok else "  FAIL  ") + name + ("  — " + detail if detail else ""))
    return ok


def inspect_ramdisk(rd):
    """用系统 lz4/cpio 列出 ramdisk 内容（缺工具就跳过）"""
    import os
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as d:
            rdp = os.path.join(d, "rd.lz4")
            cpp = os.path.join(d, "rd.cpio")
            open(rdp, "wb").write(rd)
            with open(cpp, "wb") as f:
                subprocess.run(["lz4", "-dc", rdp], stdout=f, check=True,
                               stderr=subprocess.DEVNULL)
            out = subprocess.run(["cpio", "-it", "--quiet"], stdin=open(cpp, "rb"),
                                 capture_output=True, text=True).stdout
            names = [n for n in out.splitlines() if n.strip()]
    except Exception as e:                                    # noqa: BLE001
        print("  (跳过 ramdisk 内容体检：%s)" % e)
        return
    print("  ramdisk 条目数 = %d" % len(names))
    want = ["hxchipset.ko", "Himax_firmware.bin", "nvt36523_spi.ko", "novatek_ts_fw.bin",
            "languages/zh_CN.xml", "DroidSansFallback.ttf", "init.recovery.qcom.rc",
            "bin/recovery", "recovery.fstab", "twres/ui.xml"]
    for w in want:
        hit = [n for n in names if w in n]
        check("ramdisk 含 %s" % w, bool(hit), str(hit[:2]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--max-ramdisk", type=int, default=ABL_RAMDISK_LIMIT)
    ap.add_argument("--expect-size", type=int, default=0)
    ap.add_argument("--inspect", action="store_true")
    args = ap.parse_args()

    blob = open(args.image, "rb").read()
    size = len(blob)
    hdr = blob[:4096]
    print("== verify %s (%d B) ==" % (args.image, size))
    if len(hdr) < 64:
        print("文件太小，不是 boot image")
        return 2

    check("Android boot header 魔数", hdr[:8] == b"ANDROID!", repr(hdr[:8]))

    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from("<4I", hdr, 8)
    hv = struct.unpack_from("<I", hdr, 40)[0]
    check("header_version == 4", hv == 4, "hv=%d" % hv)
    check("header_size == %d" % HDR_SIZE_EXPECT, header_size == HDR_SIZE_EXPECT,
          "header_size=%d" % header_size)
    check("kernel_size == 0（ramdisk-only）", kernel_size == 0, "kernel_size=%d" % kernel_size)

    cmdline = hdr[44:44 + 1536].split(b"\x00", 1)[0]
    check("cmdline 为空", cmdline == b"", "cmdline=%r" % cmdline)

    rd_off = ((header_size + 4095) // 4096) * 4096
    rd = blob[rd_off:rd_off + ramdisk_size]
    check("ramdisk 压缩 = legacy LZ4", rd[:4] == LZ4_LEGACY,
          "magic=%s" % (rd[:4].hex() if rd[:4] else "(空)"))

    if ramdisk_size > args.max_ramdisk:
        check("ramdisk_size ≤ 预算", False,
              "ramdisk=%d  预算=%d  超=%d B" % (ramdisk_size, args.max_ramdisk,
                                                ramdisk_size - args.max_ramdisk))
    else:
        check("ramdisk_size ≤ 预算", True,
              "ramdisk=%d  预算=%d  余=%d B" % (ramdisk_size, args.max_ramdisk,
                                                args.max_ramdisk - ramdisk_size))

    if ramdisk_size > PROVEN_BOOTABLE:
        print("  NOTE  已越过 21,618,637 B（recovery_hx_fw.img 实测启动值）——"
              "过 ABL 没问题，但用户态能否起来要真机验")

    if args.expect_size:
        check("文件长度 == %d" % args.expect_size, size == args.expect_size, "size=%d" % size)
    else:
        check("镜像文件 ≤ %d" % PARTITION_SIZE, size <= PARTITION_SIZE, "size=%d" % size)

    if args.inspect:
        inspect_ramdisk(rd)

    bad = [r for r in results if not r[1]]
    print("== %s（%d 项，%d 失败）==" % ("OK" if not bad else "FAILED", len(results), len(bad)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
