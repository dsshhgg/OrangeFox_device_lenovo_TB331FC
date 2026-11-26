# OrangeFox device tree — Lenovo TB331FC (`khaje` / SM6225-AD)

OrangeFox **R12.1（`fox_12.1`）** 设备树 + GitHub Actions 云编译流水线，
目标产物：**能在真机启动、触摸可用、带中文界面的 `recovery.img`**。

真机：联想小新 Pad 2024 **TB331FC**（骁龙 685 / `bengal` / A/B + **独立 recovery 分区**）。

## 仓库结构

```
.github/workflows/build_fox.yml      云编译（workflow_dispatch，含体积闸门）
ci/fox-postprocess.py                出厂后处理：清 cmdline / 拆 ramdisk 体检 / 补到 104,857,600 / 预算断言
ci/verify-recovery.py                独立复验（第二双眼睛，8 项判据）
device/lenovo/TB331FC/               设备树本体（OF 版，派生自已开机的 TWRP 基线）
```

设备树随带到源码树的 `device/lenovo/TB331FC`。CI 里 `devicetree/` 是检出目录，
`ci/` 与 `.github/` 都从那里读，所以两者始终在同一个 commit 上。

## 相对 TWRP 基线必须带上的四项修复

| # | 修复 | 落点 | 依据（实机） |
|---|---|---|---|
| 1 | **触摸换 Himax** | `recovery/root/vendor/lib/modules/hxchipset.ko`（607,560 B）+ `recovery/root/lib/firmware/Himax_firmware.bin`（261,120 B，另附 `_hx83102j` 别名）+ `init.recovery.qcom.rc` 里 **先** `insmod hxchipset.ko` 再 `insmod nvt36523_spi.ko` | `nvt36523_spi.ko` 在真机打印 `unknown panel, exit` 后退出；补 `hxchipset.ko` 后 `himax-touchscreen` 注册成功、`irqnum=209`、触摸可用 |
| 2 | **中文界面** | `BoardConfig.mk` + `of_size.mk` 两处 `TW_EXTRA_LANGUAGES := true`；`prebuilt/languages/zh_CN.xml` 由 CI bootstrap 进源码主题目录 | 默认只有 `en.xml`，语言列表里没有「简体中文」 |
| 3 | **CJK 字形** | `prebuilt/fonts/DroidSansFallback.ttf`（3,939,852 B）由 CI bootstrap 进字体目录 | `zh_CN.xml` 用 `fontoverride filename="DroidSansFallback.ttf"` 指名要这个文件；缺它中文全是方块 |
| 4 | **ABL 预算断言** | `ci/fox-postprocess.py` + `ci/verify-recovery.py` + workflow `max_ramdisk` 默认 `31707004` | ABL **单项**上限 31,707,004 B（K = 现役 KSU `0x29C0000`）。**不要**再减 vendor/init_boot，那是总量口径；21,618,637 B 已实测能启动 |

## 产物判据（CI 里任一不满足即 fail）

```
Android Boot Header 魔数   "ANDROID!"
header_version             4
header_size                1584
kernel_size                0            # ramdisk-only，内核在 boot.img
cmdline                    全零         # Lenovo ABL 对非空 cmdline 有缺陷
ramdisk 压缩               legacy LZ4   # 头 4 字节 = 02 21 4c 18
ramdisk_size               ≤ 31,707,004
文件长度                   104,857,600  # 与实测能启动的 recovery_hx_fw.img 同形
ramdisk 内含               hxchipset.ko / Himax_firmware.bin / nvt36523_spi.ko /
                           novatek_ts_fw.bin / languages/zh_CN.xml /
                           DroidSansFallback.ttf / init.recovery.qcom.rc /
                           bin/recovery / recovery.fstab / twres/ui.xml
```

> `ci/fox-postprocess.py` 的"拆包→重拼"路径已在真机实测能启动的
> `recovery_hx_fw.img`（104,857,600 B，sha256 `76b85251…`）上回归：
> 重拼输出与原文件 **sha256 逐字节相同**，即该脚本不会改变产物语义。

## 怎么跑

GitHub → Actions → `Build OrangeFox R12.1 for TB331FC` → **Run workflow**

| 输入 | 默认 | 说明 |
|---|---|---|
| `of_branch` | `12.1` | `sync_script` 收 `12.1`（脚本自己拼 `fox_12.1`）；`repo_init` 两种都收 |
| `sync_method` | `sync_script` | 官方 `orangefox_sync.sh`；没产出会自动回退 `repo init Manifest.git` |
| `slim` | `0` | `1` = SLIM 档（关 crypto/fastbootd/MTP/lpdumpd/AromaFM） |
| `max_ramdisk` | `31707004` | ABL 单项预算 |
| `jobs` | `4` | 标准 runner 4 vCPU / 16 GB |

产物 artifact：`OrangeFox-TB331FC-recovery`
（`recovery_fox.img` = 可刷件、`recovery_fox_unpadded.img` = 头+ramdisk、
`recovery.img` = 构建原始件、`/tmp/build.log`、`/tmp/ramdisk_listing.txt`）。

## 本地复验（拿到 artifact 之后）

```bash
python3 ci/verify-recovery.py /path/to/recovery_fox.img \
    --max-ramdisk 31707004 --expect-size 104857600 --inspect
```

## 已知缺陷（本轮不修，只记录）

真机 `himax-touchscreen` 是**纯 MT 协议**：只报 `ABS_MT_POSITION_X/Y`，**没有单点
`ABS_X/ABS_Y`**，且量程是 `11999×19199`（面板像素的 10 倍）。TWRP 的「滑动确认」控件
依赖单点事件，因此滑不过去（鼠标可用）。**OF 是否同样问题要真机验**，判据：
进 OF 界面后试「滑动以允许修改」/ 锁屏滑动，看是否需要鼠标。

## 刷写（本仓库不做刷机，只出镜像）

```bash
fastboot flash recovery_a recovery_fox.img
adb reboot recovery            # 本机不支持 fastboot boot / fastboot reboot recovery
```

* **绝不写 `recovery_b`**：b 槽三件是 ZUI17，而 `vbmeta_b` 是 ZUI16，摘要不符。
* 回滚：`fastboot flash recovery_a <原厂 recovery.img>`（100,663,296 B）。
* 卡死（无 adb 无 fastboot）：长按电源 15–30 s → 按住 **音量+ 与 音量−** 插 USB → 9008 单刷 `recovery_a`。

## 许可

设备树部分：GPL-3.0-or-later / Apache-2.0（沿用基线与 OrangeFox 的约定）。
`ci/*.py`：Apache-2.0。
