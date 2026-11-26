#
# OrangeFox product makefile — Lenovo Xiaoxin Pad 2024 (TB331FC / khaje)
# SPDX-License-Identifier: GPL-3.0-or-later
#
# 相对 TWRP 基线 twrp_TB331FC.mk 的四处差异：
#   1) PRODUCT_NAME / 文件名改成 fox_（OF 的 lunch 前缀，vendorsetup.sh 里也认这个）
#   2) 继承 OF 侧 vendor/twrp/config/common.mk —— fox_12.1 里 OF 自己的 UI/脚本/工具都挂在
#      这个目录下（分支名就叫 fox_12.1，OF 的 vendor/twrp 不是 TWRP 上游那一份）
#   3) 补 TARGET_SUPPORTS_32_BIT_APPS := false —— 64-bit-only 产品不写这条 lunch 会 abort
#   4) TW_DEVICE_VERSION / OF 版本串
#

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)

# 64-bit only（本机 vendor 只有 arm64 ABI，没有 32 位 userspace）
TARGET_SUPPORTS_32_BIT_APPS := false
TARGET_SUPPORTS_64_BIT_APPS := true

# OrangeFox / TWRP common（主题、加密、OF 的 fox_* 工具与脚本）
$(call inherit-product, vendor/twrp/config/common.mk)

# Inherit from TB331FC device
$(call inherit-product, device/lenovo/TB331FC/device.mk)

PRODUCT_DEVICE := TB331FC
PRODUCT_NAME := fox_TB331FC
PRODUCT_BRAND := Lenovo
PRODUCT_MODEL := TB331FC
PRODUCT_MANUFACTURER := LENOVO

# 主屏上显示的版本串（TW 源码读 TW_DEVICE_VERSION）
TW_DEVICE_VERSION := TB331FC-Fox-R12.1

# OF R12.1 的发布串；FOX_BUILD_TYPE 只影响 Stable 时的日志历史策略（见 fox_topaz.mk 惯例）
FOX_MAINTAINER_PATCH_VERSION := 0
FOX_BUILD_TYPE := Beta

PRODUCT_GMS_CLIENTID_BASE := android-lenovo

PRODUCT_BUILD_PROP_OVERRIDES += \
    PRIVATE_BUILD_DESC="TB331FC_PRC-user 14 UKQ1.230917.001 ZUI_16.0.544_241115_PRC release-keys"

BUILD_FINGERPRINT := Lenovo/TB331FC_PRC/TB331FC:14/UKQ1.230917.001/ZUI_16.0.544_241115_PRC:user/release-keys
