#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fox-postprocess.py —— 对 OrangeFox 编出来的 recovery.img 做出厂后处理 + 硬闸门

做四件事（顺序固定）：
  1) 清 cmdline（OF/TWRP builder 会塞 buildvariant=eng；Lenovo ABL 对非空 cmdline 有缺陷）
  2) 只保留 [头 4096 B] + [ramdisk]，丢掉任何 AVB footer（真机实测能启动的
     recovery_hx_fw.img 就是这种形态：104,857,600 B 定长、无 footer）
  3) 体检 ramdisk 内容：hxchipset.ko / Himax_firmware.bin / nvt36523_spi.ko /
     novatek_ts_fw.bin / languages/zh_CN.xml / DroidSansFallback.ttf / init.recovery.qcom.rc /
     bin/recovery / recovery.fstab / twres/ui.xml
  4) 断言：header_version=4、kernel_size=0、ramdisk 头 = 02 21 4c 18（legacy LZ4）、
     ramdisk_size ≤ ABL 单项上限（默认 31,707,004）
  5) 产出 recovery_fox.img（补零到 104,857,600）与 recovery_fox_unpadded.img

解 ramdisk 时优先用系统 lz4/cpio，缺工具则退回纯 python（lz4.block 模块 + 自带 cpio 解析）。

用法：
    python3 ci/fox-postprocess.py out/target/product/TB331FC/recovery.img \
        --outdir out/target/product/TB331FC [--max-ramdisk 31707004] [--target-size 104857600]
退出码：0 全通过；1 有 FAIL；2 输入不是 boot image
"""
import argparse
import hashlib
import os
import struct
import subprocess
import sys

LZ4_LEGACY = bytes.fromhex("02214c18")
HDR_SIZE_EXPECT = 1584

REQUIRED = [
    ("#1 触摸: hxchipset.ko", "hxchipset.ko"),
    ("#1 触摸: Himax_firmware.bin", "Himax_firmware.bin"),
    ("#1 触摸: nvt36523_spi.ko", "nvt36523_spi.ko"),
    ("#1 触摸: novatek_ts_fw.bin", "novatek_ts_fw.bin"),
    ("#2 中文: languages/zh_CN.xml", "languages/zh_CN.xml"),
    ("#3 字体: DroidSansFallback.ttf", "DroidSansFallback.ttf"),
    ("init.recovery.qcom.rc", "init.recovery.qcom.rc"),
    ("system/bin/recovery", "bin/recovery"),
    ("system/etc/recovery.fstab", "recovery.fstab"),
    ("twres/ui.xml", "twres/ui.xml"),
]


# --------------------------------------------------------------------------- #
# ramdisk 解码
# --------------------------------------------------------------------------- #
def decode_lz4_legacy_py(rd):
    """纯 python 解 lz4 legacy（02 21 4c 18）—— 需要 lz4.block 模块"""
    import lz4.block
    off, out, nblk = 4, bytearray(), 0
    while off + 4 <= len(rd):
        comp = struct.unpack_from("<I", rd, off)[0]
        off += 4
        if comp == 0:
            break
        blk = rd[off:off + comp]
        off += comp
        out += lz4.block.decompress(blk, uncompressed_size=8 * 1024 * 1024)
        nblk += 1
    return bytes(out), nblk


def decode_ramdisk_to_cpio(rd, workdir):
    """返回 (cpio_bytes, method)"""
    rd_p = os.path.join(workdir, "rd.lz4")
    cpio_p = os.path.join(workdir, "rd.cpio")
    open(rd_p, "wb").write(rd)
    # 1) 系统 lz4
    try:
        with open(cpio_p, "wb") as f:
            subprocess.run(["lz4", "-dc", rd_p], stdout=f, check=True,
                           stderr=subprocess.DEVNULL)
        return open(cpio_p, "rb").read(), "lz4-cli"
    except Exception:                                        # noqa: BLE001
        pass
    # 2) python lz4
    data, n = decode_lz4_legacy_py(rd)
    open(cpio_p, "wb").write(data)
    return data, "lz4-py(%d blocks)" % n


def list_cpio_names(buf):
    """解析 newc cpio，返回 (names, {name: size})"""
    names, sizes, o = [], {}, 0
    while o + 110 <= len(buf):
        if buf[o:o + 6] != b"070701":
            break
        def h(i):
            return int(buf[o + 6 + i * 8:o + 6 + i * 8 + 8], 16)
        fsize, namesize = h(6), h(11)
        name = buf[o + 110:o + 110 + namesize - 1].decode("utf-8", "replace")
        p = (o + 110 + namesize + 3) & ~3
        sizes[name] = fsize
        names.append(name)
        o = (p + fsize + 3) & ~3
        if name == "TRAILER!!!":
            break
    return names, sizes


def list_cpio_cli(cpio_path):
    out = subprocess.run(["cpio", "-it", "--quiet"], stdin=open(cpio_path, "rb"),
                         capture_output=True, text=True).stdout
    return [n for n in out.splitlines() if n.strip()]


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--outdir", default="")
    ap.add_argument("--max-ramdisk", type=int,
                    default=int(os.environ.get("RAMDISK_LIMIT", "31707004")))
    ap.add_argument("--target-size", type=int,
                    default=int(os.environ.get("IMG_TARGET_SIZE", "104857600")))
    args = ap.parse_args()

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.image))
    os.makedirs(outdir, exist_ok=True)
    blob = open(args.image, "rb").read()
    hdr = bytearray(blob[:4096])
    if hdr[:8] != b"ANDROID!":
        print("::error::不是 ANDROID! 头: %r" % bytes(hdr[:8]))
        return 2

    ksize, rsize, osver, hsize = struct.unpack_from("<4I", hdr, 8)
    hv = struct.unpack_from("<I", hdr, 40)[0]
    cmd = bytes(hdr[44:44 + 1536]).split(b"\x00", 1)[0]
    print("[built ] magic=ANDROID! hv=%d kernel_size=%d ramdisk_size=%d "
          "os_version=%#x header_size=%d file=%d cmdline=%r"
          % (hv, ksize, rsize, osver, hsize, len(blob), cmd))

    # 1) 清 cmdline
    hdr[44:44 + 1536] = b"\x00" * 1536

    # 2) 只取 头 + ramdisk
    rd_off = ((hsize + 4095) // 4096) * 4096 if hsize else 4096
    rd = blob[rd_off:rd_off + rsize]
    print("[rd    ] offset=%d size=%d head=%s" % (rd_off, len(rd), rd[:4].hex()))

    # 3) 内容体检
    fails = []
    work = os.path.join(os.environ.get("TMPDIR", "/tmp"), "ofpost")
    os.makedirs(work, exist_ok=True)
    names, sizes = [], {}
    try:
        cpio_bytes, method = decode_ramdisk_to_cpio(rd, work)
        print("[decode] method=%s cpio=%d B" % (method, len(cpio_bytes)))
        names, sizes = list_cpio_names(cpio_bytes)
        print("[cpio  ] entries=%d file_bytes=%d" % (len(names), sum(sizes.values())))
        open(os.path.join(work, "ramdisk_listing.txt"), "w",
             encoding="utf-8").write("\n".join(names))
        try:
            os.replace(os.path.join(work, "ramdisk_listing.txt"), "/tmp/ramdisk_listing.txt")
        except Exception:                                    # noqa: BLE001
            pass
    except Exception as e:                                   # noqa: BLE001
        fails.append("ramdisk 无法解压: %s" % e)
        print("::error::ramdisk 无法解压: %s" % e)

    if names:
        for label, pattern in REQUIRED:
            hit = [n for n in names if pattern in n]
            ok = bool(hit)
            print("  %s %-34s -> %s" % ("PASS" if ok else "FAIL", label,
                                        (hit[:2] if hit else "缺失")))
            if not ok:
                fails.append("ramdisk 缺 %s (%s)" % (label, pattern))
        # 顺带打印关键文件大小
        for key in ("hxchipset.ko", "Himax_firmware.bin", "DroidSansFallback.ttf",
                    "languages/zh_CN.xml"):
            for n, s in sizes.items():
                if n.endswith(key):
                    print("        %-52s %9d B" % (n, s))

    # 4) 硬闸门
    if hv != 4:
        fails.append("header_version=%d != 4" % hv)
    if ksize != 0:
        fails.append("kernel_size=%d != 0" % ksize)
    if rd[:4] != LZ4_LEGACY:
        fails.append("ramdisk 压缩不是 legacy LZ4（头=%s，必须是 02214c18）" % rd[:4].hex())
    if rsize > args.max_ramdisk:
        fails.append("ramdisk_size=%d > 预算 %d（超 %d B）"
                     % (rsize, args.max_ramdisk, rsize - args.max_ramdisk))

    # 5) 产出
    body = bytes(hdr) + rd
    body += b"\x00" * ((4096 - len(body) % 4096) % 4096)
    if len(body) > args.target_size:
        fails.append("头+ramdisk=%d > 目标 %d" % (len(body), args.target_size))
    body += b"\x00" * max(0, args.target_size - len(body))

    final = os.path.join(outdir, "recovery_fox.img")
    raw = os.path.join(outdir, "recovery_fox_unpadded.img")
    open(final, "wb").write(body)
    open(raw, "wb").write(bytes(hdr) + rd)

    print("[final ] %s = %d B" % (final, len(body)))
    print("[final ] %s = %d B" % (raw, len(hdr) + len(rd)))
    print("[final ] sha256(recovery_fox.img) = %s" % hashlib.sha256(body).hexdigest())
    rd2 = struct.unpack_from("<I", body, 12)[0]
    cmd2 = bytes(body[44:44 + 1536]).split(b"\x00", 1)[0]
    print("[final ] 回读 magic=%s hv=%d kernel=%d ramdisk=%d cmdline=%r ramdisk@4096=%s"
          % (body[:8], struct.unpack_from("<I", body, 40)[0],
             struct.unpack_from("<I", body, 8)[0], rd2, cmd2, body[4096:4100].hex()))
    print("[budget] ramdisk=%d / 上限=%d / 余=%d B" % (rsize, args.max_ramdisk,
                                                       args.max_ramdisk - rsize))

    if fails:
        for f in fails:
            print("::error::" + f)
        print("== GATE FAILED（%d 项）==" % len(fails))
        return 1
    print("== GATE OK ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
