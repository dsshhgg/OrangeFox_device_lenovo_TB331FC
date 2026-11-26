#
# of_size.mk —— OrangeFox 体积/裁剪预算（TB331FC）
# SPDX-License-Identifier: Apache-2.0
#
# 本机 ABL 的 ramdisk 额度是「三段求和」的一条不等式，不是一个常数：
#
#   total_max    = floor((89,120,768 − K) / 4096) × 4096
#   recovery_max = total_max − 13,635,716        # 原厂 init_boot(2,007,040)+vendor_boot(11,628,676)
#
#   K = boot.img 里内核的 image_size；每少 1 MB 内核，recovery ramdisk 额度就多 1 MB（1:1，无折扣）。
#
# 代入三档（来源：work\abl-limit\REPORT.md §4，地址级反汇编 + 三点实测互证）：
#   现役 KSU 内核 K=0x29C0000(43,778,048) → 安全 30,000,000 已实测通过 / 理论极限 31,707,004
#   原厂 A14 内核 K=0x2D50000(47,513,600) → 安全 26,000,000 / 理论极限 27,971,452
#   自编 Linux 内核 K=0x25F0000(39,780,352) → 安全 33,000,000 / 理论极限 35,704,700
#
# 本树口径：**按最保守的"原厂 A14 内核"档做预算 = 26 MB 安全线 / 27.97 MB 硬顶**，
# 同时留出 1 MB 给 recovery 二进制重编后的 ±100~300 KB 抖动。
#
# ⚠️ 另一条独立铁证不能忽略：**原厂 recovery ramdisk = 14,572,954 B 是唯一"已在真机上证明能启动"的值**
#    （同盘 of-rebuild/PLAN.md 全篇按它做预算）。≈31.7 MB 只是 ABL 装载层的派生口径，
#    13.99 MB 的 gzip 与 13.26 MB 的 zstd 版本都**卡在 logo**（ABL 放行、用户态没起来），
#    所以「过了尺寸」不等于「能进 recovery」。两级红线：
#      ✅ 13.0 MB 以下           → 建立完整函数的最安全区
#      ⚠️ 13.0 ~ 14.57 MB        → 可过 ABL；但已越过"实测能启动"的边界，必须真机验
#      ⛔ > 26 MB（原厂内核）    → ABL 直接拒绝
#
# 用法：`export OF_TB331FC_SLIM=1`（含 `SMALL`/`MINI`）或 `make OF_TB331FC_SLIM=1` 切档。
#

# ---------------------------------------------------------------------------
# 默认档（full）：与 TWRP 基线等价 —— 加密/解密 + MTP 全保，靠"压缩后实测"守线
# ---------------------------------------------------------------------------
TW_EXCLUDE_TWRPAPP := true
TW_EXCLUDE_BASH := true
TW_EXCLUDE_NANO := true
TW_EXCLUDE_PYTHON := true
TW_EXCLUDE_APEX := true
TW_EXTRA_LANGUAGES := true        # 修复项 #2：中文界面（与 BoardConfig.mk 同值）
# ✓ 基线原样：不设 TW_INCLUDE_PYTHON（照抄 topaz 会白吃 ~6.59 MB 未压缩 / ~2.86 MB lz4）
# ✓ 基线原样：不设 TW_EXCLUDE_ENCRYPTED_BACKUPS
#   —— 该变量在 TWRP 12.1 里判断是**反的**（Android.mk L400-404）：
#      非空 → 反而 `LOCAL_SHARED_LIBRARIES += libopenaes` 把库加回来；
#      留空 → 才真的 `-DTW_EXCLUDE_ENCRYPTED_BACKUPS` 排除代码。
#      要省这块就什么都别写。

# ---------------------------------------------------------------------------
# SLIM 档：越过 14.57 MB 那条线时的四刀（按收益排序，数字全部来自实测量）
# ---------------------------------------------------------------------------
OF_TB331FC_SLIM ?= 0
ifneq ($(filter 1 true yes SMALL MINI,$(OF_TB331FC_SLIM)),)

    # 刀 1：−4,485,464 B（lz4）占总收益 85%。代价：读不到已加密 /data（格式化仍可）。
    #       ICU 三件 4.60 MB / libchrome 1.31 MB / libsqlite / binder / keystore2 整链都从这里进来
    #       （bootable/recovery/Android.mk L335-356、libtar/Android.mk L16-56）。
    TW_INCLUDE_CRYPTO := false
    TW_INCLUDE_CRYPTO_FBE := false
    TW_INCLUDE_FBE_METADATA_DECRYPT := false
    BOARD_USES_QCOM_FBE_DECRYPTION := false

    # 刀 2：−739,520 B。二进制在 device.mk，开关在 Android.mk L456-458
    TW_INCLUDE_FASTBOOTD := false

    # 刀 3：−124,141 B（libtwrpmtp-ffs）；adb push/pull 不受影响
    TW_EXCLUDE_MTP := true

    # 刀 4：同档一起砍的零碎（Python 已关；官方日志降级只省 ~420 KB，先不动）
    TW_INCLUDE_REPACKTOOLS := false          # −~540,000（magiskboot）
    FOX_DELETE_AROMAFM := 1                  # OF 专有：−~650,000（AromaFM）
    FOX_DISABLE_APP_MANAGER := 1             # OF 专有：OF 应用管理器
    OF_ENABLE_ALL_PARTITION_TOOLS := 0       # lp 工具整组；并且**不要** lpdumpd
    #   ↑ lpdumpd 本体只 31,424 B，却拖进 liblpdump.so → libprotobuf-cpp-full.so 2.25 MB = 2.41 MB

endif
