# OrangeFox Device Tree — Lenovo Xiaoxin Pad 2024 (`TB331FC` / `khaje` / `p255`)

OrangeFox R12.1（`fox_12.1`）设备树。派生自真机「已能开机」的 TWRP 12.1 基线
`LzwPluto/twrp_device_lenovo_TB331FC`，硬件参数逐条沿用，只加 OF 层。
逐项对照表见上层 `../DIFF.md`，云编译方案见上层 `../BUILD-OF.md`。

## 设备事实（不改）

| 项 | 值 |
|---|---|
| SoC | Qualcomm Snapdragon 685 4G（SM6225-AD / `bengal` / `khaje`） |
| 屏幕 | 1200×1920 IPS LCD；Himax HX83102，**KTZ8866 背光**（`/sys/class/backlight/bkl-bl/brightness`，MAX 4095） |
| 触摸 | **Himax HX83102J**（`hxchipset.ko` 607,560 B + `Himax_firmware.bin` 261,120 B，修复项 #1）；Novatek `nvt36523_spi.ko` 仍保留但真机报 `unknown panel, exit` |
| 启动 | A/B + **独立 recovery 分区**；Boot Header **v4**；recovery 是 ramdisk-only（`kernel_size=0`） |
| 压缩 | ramdisk **LZ4 legacy**（`02 21 4c 18`）；内核没有 `CONFIG_RD_XZ/LZMA` |
| 分区 | `boot`/`vendor_boot` 96 MiB、`init_boot` 8 MiB、`dtbo` 24 MiB、`recovery` 100 MiB(物理 104,857,600)、`super` 12 GiB |
| cmdline | **必须为空**（高通 ABL 对非空 cmdline 有缺陷，会不进系统） |

## 构建

```bash
# 仓库放进 device/lenovo/TB331FC 之后
source build/envsetup.sh
export ALLOW_MISSING_DEPENDENCIES=true
export FOX_USE_TWRP_RECOVERY_IMAGE_BUILDER=1
lunch fox_TB331FC-eng
mka adbd recoveryimage -j$(nproc)
```

`vendorsetup.sh` 会被自动 source（**不要**在里面写 `add_lunch_combo`，现代树里该函数已删除）。

## 体积（先看这条再动手）

```
total_max    = floor((89,120,768 − 内核 image_size) / 4096) × 4096
recovery_max = total_max − 13,635,716          # 原厂 init_boot + vendor_boot 两份 ramdisk
```

默认档（加密/MTP/fastbootd 全保）预期 `ramdisk_size ≈ 19.5 MB`（+ 中文/字体 ≈ 0.4 MB），slim 档 ≈ 13.5 MB。
两档都低于原厂内核口径的安全线 26 MB；只有 slim 档同时低于「唯一实测能启动」的 14,572,954 B。
开关与实测收益见 `of_size.mk`。

## 刷写（只碰 a 槽）

```bash
fastboot flash recovery_a recovery.img
adb reboot recovery          # 本机不支持 fastboot boot / fastboot reboot recovery
```

* **不要写 `recovery_b`**：b 槽三个分区是 ZUI17，而 `vbmeta_b` 是 ZUI16，摘要不符，动它就是把机器推离"能救回来"的那一侧。
* 回滚永远是 `fastboot flash recovery_a <原厂 recovery.img>`（100,663,296 B）。

## 目录

```
BoardConfig.mk        硬件参数 + TWRP 层（原样）+ OF 层（新增，逐行标注验证状态）
of_size.mk            体积预算公式、默认档 / SLIM 档开关（含实测字节收益）
fox_TB331FC.mk        OF 产品身份；inherit vendor/twrp/config/common.mk
AndroidProducts.mk    只留 fox_ 一个 lunch 目标
device.mk             PRODUCT_PACKAGES（解密/fastbootd 用 if-guard 包住）
vendorsetup.sh        FOX_*/OF_* 环境变量（lunch 前 source）
recovery.fstab        fs_mgr 首挂载表（原样沿用基线）
system.prop           recovery 侧属性（新增）
fox/fox.cfg           OF 设备信息（可选，未被验证一定被读取）
prebuilt/kernel       104 字节占位符（kernel_size=0，不得换成真内核）
recovery/root/        47 个文件 / 4,822,826 B = 基线 44 文件/3,693,026 B + 修复项 #1
                      （vendor/lib/modules/hxchipset.ko 607,560 B +
                       lib/firmware/Himax_firmware.bin 261,120 B +
                       lib/firmware/Himax_firmware_hx83102j.bin 261,120 B）
prebuilt/fonts/       修复项 #3：DroidSansFallback.ttf（3,939,852 B）
prebuilt/languages/   修复项 #2：zh_CN.xml（60,099 B）
```
