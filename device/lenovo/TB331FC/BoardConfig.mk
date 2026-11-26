#
# OrangeFox (fox_12.1) BoardConfig — Lenovo Xiaoxin Pad 2024 / TB331FC (khaje / SM6225-AD)
# SPDX-License-Identifier: Apache-2.0
#
# 派生自 TWRP 12.1 基线：LzwPluto/twrp_device_lenovo_TB331FC（真机「已能开机」的那一版）
# 派生原则（三条）：
#   1) 所有硬件参数（屏幕 / 背光 / 触摸 / 分区尺寸 / 头版本 / LZ4 / 加密）逐字节沿用基线，
#      只在该项与 OF 有关联时另加 OF 变量，不替换原变量；
#   2) TW_* 一个都不删 —— OrangeFox 的 bootable/recovery 就是 TWRP 派生版，
#      TW_* 仍是唯一真实开关，OF_* / FOX_* 只是在其之上再加的一层；
#   3) 每条新增的 OF 变量都在行尾标注验证状态：
#        [基线]       = 与 TWRP 已开机基线完全一致（等价物或逐字沿用）
#        [OF惯例]     = 取自 fox_12.1 兄弟设备树（topaz，同 SM6225）的写法，未在本机上机验证
#        [新增]       = 本树为 OF 构建/R12.1 特性补充，附理由
#

DEVICE_PATH := device/lenovo/TB331FC

# For building with minimal manifest
ALLOW_MISSING_DEPENDENCIES := true

#
# ============================================================================
#  A/B & Virtual A/B
# ============================================================================
#
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS += \
    boot \
    dtbo \
    init_boot \
    odm \
    product \
    recovery \
    system \
    system_ext \
    vbmeta \
    vbmeta_system \
    vendor \
    vendor_boot \
    vendor_dlkm

# 本机是 A/B + **独立 recovery 分区**：下面两个必须"不设"（留空），否则
# 会把 recovery 打进 boot 分区，或把 recovery 资源搬到 vendor_boot。
BOARD_USES_RECOVERY_AS_BOOT := false
BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT :=
TARGET_NO_RECOVERY := false
BOARD_USES_GENERIC_KERNEL_IMAGE := true

# 原厂 recovery.img 是 ramdisk-only（kernel_size=0）。true 才会 kernel_size=0
# 且**不追加 buildvariant=eng 到 cmdline** —— 本机 ABL 对非空 cmdline 有缺陷会不进系统。
BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true

#
# ============================================================================
#  Architecture (bengal / SM6225-AD)
# ============================================================================
#
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := kryo300

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a-neon
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_2ND_CPU_VARIANT_RUNTIME := cortex-a9

TARGET_BOARD_PLATFORM := bengal
TARGET_BOARD_PLATFORM_GPU := qcom-adreno610   # [OF惯例] 兄弟树都写；无功能影响
# 注意：本树**不写** TARGET_BOOTLOADER_BOARD_NAME —— 基线没有，OF 源码里也无引用。

# APEX
OVERRIDE_TARGET_FLATTEN_APEX := true

# Bootloader & Platform
TARGET_NO_BOOTLOADER := true
BOARD_USES_QCOM_HARDWARE := true               # [OF惯例] 摘 QTI HAL 用

#
# ============================================================================
#  Boot image header v4 / LZ4 ramdisk / 空 cmdline
# ============================================================================
#
BOARD_BOOTIMG_HEADER_VERSION := 4              # [基线] 沿用基线原样
BOARD_BOOT_HEADER_VERSION := 4                 # [新增] 与上面同值：兄弟 OF 树都用这个名字
                                               #   （topaz: `BOARD_BOOT_HEADER_VERSION := 4`）。
                                               #   两个都写=幂等；产物头版本仍只由
                                               #   BOARD_MKBOOTIMG_ARGS 里的 --header_version 决定。
# ★ 先定义 pagesize 再拼 MKBOOTIMG_ARGS：若 BOARD_MKBOOTIMG_ARGS 已被父 makefile 以 `:=` 定义，
#   `+=` 会**立即展开**右边，此时 $(BOARD_KERNEL_PAGESIZE) 若还没定义就会拼出空值。
BOARD_KERNEL_PAGESIZE := 4096
BOARD_KERNEL_IMAGE_NAME := Image
BOARD_FLASH_BLOCK_SIZE := 262144               # (BOARD_KERNEL_PAGESIZE * 64)

BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOTIMG_HEADER_VERSION)
BOARD_MKBOOTIMG_ARGS += --pagesize $(BOARD_KERNEL_PAGESIZE)

# ★ cmdline 必须为空：高通 ABL 对非空 cmdline 有缺陷会不开机。
#   显式置空是保险；真正保证为空的是上面 BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true
#   （build/make 只在它 != true 时才追加 kernel/cmdline）。
BOARD_KERNEL_CMDLINE :=

# 104 字节占位符：满足 kernel.mk 的 "NO KERNEL" 检查，同时产物不带内核。
# 换成真内核会让 image_size 变大、把 ABL ramdisk 额度 1:1 吃掉（见 of_size.mk）。
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel

# LZ4 legacy（原厂 ramdisk 就是 02 21 4c 18；内核 CONFIG_RD_LZ4=y，IKCONFIG 实测）
BOARD_RAMDISK_USE_LZ4 := true

# 任何 ramdisk 压缩格式都走 build/make 的 COMPRESSION_COMMAND 一个变量；
# 本机内核没有 CONFIG_RD_XZ / CONFIG_RD_LZMA ⇒ 绝不要用 BOARD_RAMDISK_USE_XZ/LZMA。

#
# ============================================================================
#  Partitions（数值取自原厂 rawprogram0/4.xml）
# ============================================================================
#
BOARD_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE := 8388608
BOARD_DTBOIMG_PARTITION_SIZE := 25165824
# 沿用基线的 100,663,296（96 MiB）：它是「原厂 recovery.img 长度」这一保守口径；
# recovery 分区物理大小是 104,857,600。两者都不构成启动闸门，只决定 footer 对齐值。
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 100663296
BOARD_HAS_LARGE_FILESYSTEM := true
BOARD_SYSTEMIMAGE_PARTITION_TYPE := ext4
BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := f2fs
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_COPY_OUT_VENDOR := vendor

# Dynamic Partitions（12 GiB super；旧 OF 树写 8.5 GiB 是错的）
BOARD_SUPER_PARTITION_SIZE := 12884901888
BOARD_SUPER_PARTITION_GROUPS := qti_dynamic_partitions
BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST := system system_ext vendor vendor_dlkm odm product
BOARD_QTI_DYNAMIC_PARTITIONS_SIZE := 12880707584

#
# ============================================================================
#  Recovery
# ============================================================================
#
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
TARGET_RECOVERY_QCOM_RTC_FIX := true            # [OF惯例]
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery.fstab
RECOVERY_SDCARD_ON_DATA := true                 # [OF惯例]
TARGET_SYSTEM_PROP := $(DEVICE_PATH)/system.prop   # [新增] recovery 侧属性（本树附带的 system.prop）

# Verified Boot
BOARD_AVB_ENABLE := true
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 3
BOARD_AVB_RECOVERY_KEY_PATH := external/avb/test/data/testkey_rsa4096.pem   # [OF惯例]
BOARD_AVB_RECOVERY_ALGORITHM := SHA256_RSA4096                             # [OF惯例]
BOARD_AVB_RECOVERY_ROLLBACK_INDEX := 1                                     # [OF惯例]
BOARD_AVB_RECOVERY_ROLLBACK_INDEX_LOCATION := 1                            # [OF惯例]

# Hack: prevent anti rollback
PLATFORM_SECURITY_PATCH := 2099-12-31
VENDOR_SECURITY_PATCH := 2099-12-31
PLATFORM_VERSION := 16.1.0

#
# ============================================================================
#  TWRP 层（原样保留；OF 的 recovery 源码直接读这些）
# ============================================================================
#
DEVICE_SCREEN_WIDTH := 1200
DEVICE_SCREEN_HEIGHT := 1920
TW_ROTATION := 180                             # 面板竖装；翻 180 才是正常方向
TW_THEME := portrait_hdpi
# ★ 中文界面（修复项 #2）：true 才会把 gui/theme/common/languages/*.xml 全量装进
#   ramdisk（否则只有 en.xml，信号里就没有「简体中文」这个语言可选）。
#   ⚠️ of_size.mk 在 BoardConfig 末尾被 include，那里也有一行同名赋值，两处必须同值。
TW_EXTRA_LANGUAGES := true
# fastbootd：device.mk 用 ifeq ($(TW_INCLUDE_FASTBOOTD),true) 守卫，不写就不装二进制。
TW_INCLUDE_FASTBOOTD := true
TW_EXCLUDE_TWRPAPP := true
TW_EXCLUDE_BASH := true
TW_EXCLUDE_NANO := true
TW_EXCLUDE_PYTHON := true
TW_EXCLUDE_APEX := true
TW_INPUT_BLACKLIST := "hbtp_vm"                # Himax hbtp_vm 是虚拟输入，必须屏蔽
TW_USE_TOOLBOX := true
TW_INCLUDE_RESETPROP := true
TW_INCLUDE_LIBRESETPROP := true
TW_HAS_MTP := true
TW_LOAD_VENDOR_BOOT_MODULES := true            # 模块从 vendor_boot 侧加载（生效前提见下注）
TW_BRIGHTNESS_PATH := "/sys/class/backlight/bkl-bl/brightness"   # ★ KTZ8866 背光真实节点
TW_MAX_BRIGHTNESS := 4095
TW_DEFAULT_BRIGHTNESS := 1800
TWRP_INCLUDE_LOGCAT := true
TARGET_USES_LOGD := true

# ★ 关于 TW_LOAD_VENDOR_BOOT_MODULES 的一条实测更正：
#   TWRP 12.1 的 bootable/recovery/Android.mk 里，这两个变量是**嵌套**的：
#     ifneq ($(TW_LOAD_VENDOR_MODULES),)          # ← 外层：必须是列表且非空
#         LOCAL_SRC_FILES += kernel_module_loader.cpp
#         LOCAL_CFLAGS += -DTW_LOAD_VENDOR_MODULES=$(TW_LOAD_VENDOR_MODULES)
#         ifeq ($(TW_LOAD_VENDOR_BOOT_MODULES),true)
#             LOCAL_CFLAGS += -DTW_LOAD_VENDOR_BOOT_MODULES
#         endif
#     endif
#   基线里没有 TW_LOAD_VENDOR_MODULES ⇒ 外层不成立 ⇒ kernel_module_loader 根本没编进去，
#   这条 TW_LOAD_VENDOR_BOOT_MODULES := true 是**死配置**（backref: Android.mk L323-334）。
#   本树沿用基线行为（模块靠 init.recovery.qcom.rc 里那条 insmod 加载，已验证有效）。
#   若要真正启用模块自动加载，改成：
#     TW_LOAD_VENDOR_MODULES := "nvt36523_spi.ko"
#     TW_LOAD_VENDOR_MODULES_EXCLUDE_GKI := true
#   —— 代价是 +kernel_module_loader.cpp +libmodprobe，且会去 vendor_boot 的
#   /lib/modules 找 modules.load（本机 vendor_boot 未必有），未验证，默认不开。

# Crypto / FBE v2 Decryption（QTI KeyMint V2 + Gatekeeper 1.0 + qseecomd）
# 代价明确：打开这一组是 ramdisk 里最大的一块（ICU 等 ≈4.49 MB lz4，见 of_size.mk）。
BOARD_USES_METADATA_PARTITION := true
BOARD_USES_QCOM_FBE_DECRYPTION := true
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
TW_USE_FSCRYPT_POLICY := 2

#
# ============================================================================
#  ★ OrangeFox 层（fox_12.1）
# ============================================================================
#

# ---- 1. A/B + 独立 recovery 分区（三个都必需）----------------------------
# 少设 OF_AB_DEVICE_WITH_RECOVERY_PARTITION，OF 安装器会把 recovery 写进 boot 分区。
FOX_AB_DEVICE := 1                                  # [OF惯例] 新名；OF_AB_DEVICE 仍被识别
OF_AB_DEVICE_WITH_RECOVERY_PARTITION := 1           # [OF惯例] A/B 但有独立 recovery
OF_DYNAMIC_PARTITIONS := true                       # [OF惯例] 让 OF 认出 super/lp

# ---- 2. 屏幕几何（OF 自己一套数字，与 TW_THEME 并行）----------------------
OF_SCREEN_H := 1920                                 # [基线] = DEVICE_SCREEN_HEIGHT
OF_STATUS_H := 96                                   # [OF惯例] 状态栏高度，按 1920 高的 5%
OF_STATUS_INDENT_LEFT := 48                         # [OF惯例]
OF_STATUS_INDENT_RIGHT := 48                        # [OF惯例]
OF_ALLOW_DISABLE_NAVBAR := 0                        # [OF惯例]
OF_CLOCK_POS := 1                                   # [OF惯例] 时钟居中
OF_USE_GREEN_LED := 0                               # [基线] 本机无通知灯
OF_OPTIONS_LIST_NUM := 9                            # [OF惯例] 超过 9 项才出滚动条

# ---- 3. 功能开关（默认按兄弟树开齐；第一轮真机可关掉做对照）-------------
OF_ENABLE_FRP_ADDON := 1                            # [OF惯例]
OF_ENABLE_LPTOOLS := 1                              # [OF惯例] 动态分区工具
OF_ENABLE_ALL_PARTITION_TOOLS := 1                  # [OF惯例]
OF_USE_DMCTL := 1                                   # [OF惯例]
OF_NO_TREBLE_COMPATIBILITY_CHECK := 1               # [OF惯例]
OF_USE_LEGACY_TIME_FIXUP := 1                       # [OF惯例] RTC 另有 TARGET_RECOVERY_QCOM_RTC_FIX 兜
OF_LOOP_DEVICE_ERRORS_TO_LOG := 1                   # [OF惯例] 少刷屏
OF_QUICK_BACKUP_LIST := /boot;/init_boot;/recovery;/vendor_boot;/dtbo;   # [新增]
#   ↑ 本机是 A/B+独立 recovery，能靠 recovery 分区救命的就这几项
OF_DEFAULT_KEYMASTER_VERSION := 4.1                 # [基线] 与树内 keymaster@4.1 blobs 一致
OF_UNBIND_SDCARD_F2FS := 1                          # [OF惯例] f2fs 修复/格式化前先解 bind
OF_USE_TWRP_SAR_DETECT := true                      # [OF惯例]
OF_DISABLE_DM_VERITY := true                        # [OF惯例]
OF_DISABLE_FORCED_ENCRYPTION := true                # [OF惯例]

# ---- 4. 构建环境兜底（真正的来源是 vendorsetup.sh 的 export）-------------
FOX_USE_TWRP_RECOVERY_IMAGE_BUILDER := 1            # [新增] R12.1 用 TWRP 镜像构建器出 recovery.img

# ---- 5. 体积/裁剪预算（硬约束公式与两档开关见 of_size.mk）---------------
include $(DEVICE_PATH)/of_size.mk

#
# ============================================================================
#  ★ 专记「基线已证伪、不要照抄」的四条（本盘旧 OF 树踩过）
# ============================================================================
#   1) BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := false
#       旧树注释称"false 才排除内核并跳过 cmdline" —— 与 build/make 源码相反
#       （`ifneq (true,$(BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE))` 才追加 kernel 与 cmdline）。
#       true 才对；TWRP 基线用它开过机。
#   2) BOARD_SUPER_PARTITION_SIZE := 9126805504 —— 实测 super 是 12 GiB(12884901888)。
#      写小了不影响 recovery 启动，但 lpmake / fastboot flash super 会直接错位。
#   3) TW_BRIGHTNESS_PATH := "/sys/class/backlight/panel0-backlight/brightness"
#      —— 那是 topaz 的；本机实测节点是 bkl-bl（KTZ8866），MAX 4095 不是 2047。
#   4) BOARD_KERNEL_IMAGE_NAME := kernel
#      —— 基线是 Image（占位符只喂 kernel.mk 检查，名字无关紧要，沿用基线省一次变量差异）。
