#!/bin/bash
#
# OrangeFox build environment — Lenovo TB331FC (khaje)
# SPDX-License-Identifier: GPL-3.0-or-later
#
# OF/TWRP 12.1 在 lunch 之前会 source 本文件。三条纪律：
#   1) **不要** add_lunch_combo —— 现代 AOSP/OF 树里该函数已删除，source 到它就 abort lunch。
#      lunch 目标由 AndroidProducts.mk 的 COMMON_LUNCH_CHOICES 提供。
#   2) 这里的 export 对 OF 构建**一定生效**（Makefile 变量作用域到不了 shell）；
#      同一个开关如果也要进编译器 CFLAG，就必须在 BoardConfig.mk 里再写一遍。
#   3) 键名与 BoardConfig.mk 保持同名同值，避免"两处不同值"这种最难查的漂移。
#

export FOX_AB_DEVICE=1
export OF_AB_DEVICE_WITH_RECOVERY_PARTITION=1
export OF_DYNAMIC_PARTITIONS=true

# R12.1 用 TWRP 镜像构建器（OF 自己的 builder 不出 recovery.img，快进不了 bundle）
export FOX_USE_TWRP_RECOVERY_IMAGE_BUILDER=1

# AromaFM / OF 应用管理器默认就带 ~1.5 MB，本机额度紧，先关
export FOX_DELETE_AROMAFM=1
export FOX_DISABLE_APP_MANAGER=1

# 体积档：默认 full（加密封解密全保）。越线时执行 `export OF_TB331FC_SLIM=1`
# 再 source build/envsetup.sh，见 BoardConfig.mk 末尾 include 的 of_size.mk
export OF_TB331FC_SLIM=${OF_TB331FC_SLIM:-0}

# 构建期固定 locale，否则 OF 脚本里 grep 中文/排序会出岔
export LC_ALL=C
