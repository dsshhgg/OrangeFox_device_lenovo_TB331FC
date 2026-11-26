#
# SPDX-License-Identifier: Apache-2.0
#
# 只留 fox_ 一个产品（基线里有 twrp_ 一份，本树删掉，避免 lunch 选错目标）。
#

PRODUCT_MAKEFILES := \
    $(LOCAL_DIR)/fox_TB331FC.mk

# TWRP/OF 12.1 的 build/make 是 TeamWin 的三段式 lunch；先给最短形式，
# 报 "Invalid lunch combo" 时依次再试 -ap2a-eng / -ap3a-eng / -trunk_staging-eng。
COMMON_LUNCH_CHOICES := \
    fox_TB331FC-eng \
    fox_TB331FC-userdebug \
    fox_TB331FC-user
