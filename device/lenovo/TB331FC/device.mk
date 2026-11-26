#
# SPDX-License-Identifier: Apache-2.0
#
# OrangeFox 版 device.mk。
#
# 相对 TWRP 基线 device.mk（只有 PRODUCT_USE_DYNAMIC_PARTITIONS 一行）的差异，
# 全部以 **if-guard 包住**：只有真的解得密（TW_INCLUDE_CRYPTO=true）时才装解密包，
# of_size.mk 里 SLIM 档把它关掉时这里自动不装，不会白占体积 / 白报缺依赖。
#

LOCAL_PATH := device/lenovo/TB331FC

# Dynamic Partitions
PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_BUILD_SUPER_PARTITION := false

PRODUCT_SOONG_NAMESPACES += $(LOCAL_PATH)

# A/B 槽位 HAL（recovery 里看得到当前槽/回滚，边际 ~11 KB）
PRODUCT_PACKAGES += \
    android.hardware.boot@1.2-impl-qti.recovery

#
# ---- 以下仅 [新增] 项，TWRP 基线没有 -------------------------------------
#

# 解密（QCOM FBE）。基线把这些二进制/libs 直接放在 recovery/root/ 里靠 rc 手起，
# OF 树里改为走 PRODUCT_PACKAGES（OF 的 fox_ 工具会检查这些模块是否在）。
ifeq ($(TW_INCLUDE_CRYPTO),true)
PRODUCT_PACKAGES += \
    qcom_decrypt \
    qcom_decrypt_fbe \
    android.hardware.keymaster@4.1
TARGET_RECOVERY_DEVICE_MODULES += \
    android.hardware.keymaster@4.1
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/android.hardware.keymaster@4.1.so
endif

# fastbootd：开关在 BoardConfig（TW_INCLUDE_FASTBOOTD 只改 CFLAG），**二进制在 device.mk**。
# — 折中对齐基线：TW_HAS_MTP=true 与 fastbootd 都要 IUsb 的 asyncio 后端（同一套 Coffee/Gadget
#   栈），OF 的兄弟树（topaz）从来是把 fastbootd 一起装的；两个都开不会互相拆台。
# — 代价（实测 lz4 Δ）：fastbootd 1,244,448 + fastboot@1.0/1.1 205,072 ≈ −739,520 B。
ifeq ($(TW_INCLUDE_FASTBOOTD),true)
PRODUCT_PACKAGES += \
    android.hardware.fastboot@1.1-impl-mock \
    fastbootd
endif

# 注意：**不装** update_engine / update_engine_sideload / update_verifier /
#       otapreopt_script / cppreopts.sh —— 旧 OF 树照抄了 topaz 的 OTA 三件，
#       对"只求进 recovery"的镜像纯属浪费（≈ −950,000 B lz4，实测边际）。
#       要侧载官方 A/B OTA 时再单独加回。
#
# 注意：**不装** lenovo_prebuilt_modules / prebuilt/vendor/lib/modules/1.1/*
#       —— 那是旧 OF 树的写法（把整套 vendor_dlkm 塞进 ramdisk，光 msm_drm.ko 就 4.2 MB）。
#       基线的做法是 TW_LOAD_VENDOR_BOOT_MODULES + rc 里 insmod 一个 nvt36523_spi.ko（473,824 B），
#       触摸模块与固件已经在 recovery/root/ 里，本树原样照抄。
