# ASUS TUF Gaming A14 (FA401UU) — macOS 15 Sequoia + RTX 4050 Laptop

**状态：已装好，可正常进系统并使用（2026-10-20）。**
本仓库现在包含一套**实测可引导的完整 EFI**（`EFI/`，143 个文件 / 14 MB），
以及从"卡在 `[PCI configuration begin]`"一路到"装完之后怎么联网"的全部证据、踩坑记录与脚本。

| | |
|---|---|
| 机型 | ASUS TUF Gaming A14 **FA401UU**，BIOS `FA401UU.311`，UEFI |
| CPU | **AMD Ryzen 7 8845H**（Zen 4 / Hawk Point，8C/16T） |
| 独显 | **NVIDIA RTX 4050 Laptop**（`10DE:28E1`，AD107）← 内屏直连这颗 |
| 核显 | Intel 无关；AMD Radeon 780M（`1002:1900`）在 macOS 无驱动 → `disable-gpu` 屏蔽 |
| 已装系统 | **macOS 15.7.7 / 24G720**（Sequoia） |
| 引导 | OpenCore（DEBUG 构建，来自 [1401](https://github.com/nullmoth/1401) v2.3.6），装在内置 ESP |
| SMBIOS | `MacBookPro16,2`（**仓库里已抹除身份字段，见下方警告**） |
| 无线 | MediaTek **MT7922 / RZ616**（`14c3:0616`）→ 实验驱动，见 [Wi-Fi](#wi-fi实验驱动能连但不稳) |
| 蓝牙 | MT7922 的 USB 侧（`0489:e0f6`） |
| 声卡 | Realtek ALC256（AppleALC `layout-id 97`） |

> **English TL;DR** — A complete, booted-and-verified OpenCore EFI for the ASUS TUF
> Gaming A14 (FA401UU): Ryzen 7 8845H + RTX 4050 Laptop + MT7922, running macOS 15
> Sequoia with the NullMoth NVIDIA driver. `EFI/` is the exact tree that boots on this
> unit; the SMBIOS identity fields are zeroed, so generate your own before use.
> `docs/` holds the full investigation log (Chinese).

---

## ⚠️ 用之前必须知道的三件事

1. **SMBIOS 身份字段是全零占位符**（`SystemSerialNumber` / `MLB` / `SystemUUID` / `ROM`）。
   直接刷这套 EFI 会有各种怪问题。请用 1401 对**本机**重新生成一套，或自己填一套
   互不相同的值。**不要多人共用同一套 SMBIOS —— 会让 iMessage / iCloud 掉线。**
2. **这套配置为了跑起来牺牲了大量安全性**：`csr-active-config = 0x0A43`（放宽 SIP）、
   `amfi=0x80` + `amfi_get_out_of_my_way=0x1`（旁路 AMFI 签名校验）、
   `SecureBootModel = Disabled`。**不要拿它当处理敏感数据的主力机。**
3. **内屏是独显直连**（MUX）。如果 NVIDIA 驱动没起来，内屏就是黑的或只剩文字界面。
   救急工具在 OpenCore 菜单里（见 [卡死处置](#卡死处置症状--怎么办)）。

---

## 现在到底能用什么

实测结论。"证据"列写的是本仓库里能复查的出处。

| 功能 | 状态 | 证据 / 说明 |
|---|---|---|
| 开机进系统 | ✅ | OpenCore 菜单 → macOS，可日常使用 |
| 内屏 + 显卡加速 | ✅ | NullMoth NVIDIA 驱动 2.3.6，`NVRMFB/NVAccel/NVRM` 加载；**冷启动有小概率卡 BAR1，见下** |
| CPU 16 线程 | ✅ | `AppleACPICPU ProcessorId=0..15 Enabled`，无 `cpus=1` |
| 声音（ALC256） | ✅ | AppleALC，`layout-id = 97` |
| 亮度键 / 音量键 | ✅ | BrightnessKeys |
| 键盘 | ✅ | VoodooPS2Controller（PS/2 接口） |
| 电池百分比 / 电源 | ✅ | SMCBatteryManager + `SSDT-ADP1`（伪装 AC，修 USB-C PD 显示） |
| 触摸板 | ✅ | VoodooI2C + VoodooGPIO + VoodooI2CHID，实测正常 |
| 蓝牙 | ⚠️ | `SimpleMtkBtFw` 已匹配本机 `0489:e0f6`、驱动已加载；配对与传输**未测试** |
| Wi-Fi | ⚠️ | `itlmt7922` 实验驱动：**能连、能跑 866 Mbps，但高负载约 1 小时后固件 coredump 掉线** |
| 有线网络 | ❌ | 本机无 RJ45。USB 网卡只认 **RTL8153** 类；RTL8156 不认 |
| 安卓 USB 共享 | ⚠️ | HoRNDIS 9.3 已注入，macOS 能识别出网络服务但链路起不来（`status: inactive`），未打通 |
| 读卡器 | ⚠️ | Sinetek-rtsx |
| 睡眠 / 唤醒 | ❌ **无法睡眠** | 实测：睡下去就醒不回来。装完请关掉睡眠与合盖休眠（见下） |
| AirDrop / 接力 / 通用控制 | ❌ | 依赖原生 Wi-Fi 卡，MT7922 没有 |
| iMessage / FaceTime | ❌ | 需要真实三码 + 原生 Wi-Fi，这里都没有 |

---

## 快速上手（已经有本机 Win/macOS 双系统的人）

```text
1. 先拉 kext（仓库不存第三方二进制，见「第三方组件与许可」）
       pwsh -File scripts/fetch-kexts.ps1
   → 按固定 SHA256 下载 17 个压缩包，解出 22 个 kext 到 EFI/OC/Kexts，并逐个核对二进制哈希
2. 挂载 ESP，把本仓库 EFI/ 整个复制进去（ESP 根只剩 EFI/ 一个目录）
3. 用 1401 重新生成你自己的 SMBIOS 三码，替换 EFI/OC/config.plist 里
   PlatformInfo → Generic 的 SystemSerialNumber / MLB / SystemUUID / ROM
4. 重启 → Esc 选 OpenCore
```

从零开始的完整流程见 [安装手册](docs/02-安装手册.md)；下面只写**这次真正成功用的那条路**。

> 不想 clone 整个仓库？[**最新 Release**](https://github.com/LiamZhaofor/asus-tuf-a14-fa401uu-hackintosh/releases/latest)
> 里有打好包的 `EFI-<日期>.zip`（**已包含第三方 kext**，开箱可引导，config 同样已脱敏）
> + `SHA256SUMS.txt`。走 Release 就不需要跑 fetch 脚本。

---

## 怎么装（从零复现）

### 0. 前置

- 一块能当引导介质的盘：本项目最后用的是**内置 ESP**（12 GB），不是 U 盘
  （USB 盘在反复写入中把桥接芯片写死过两次，不建议）
- Windows 侧：`1401` v2.3.6 + 一个能联网的环境（下载 kext / 驱动）
- 一个能读写的 **exFAT** 分区给安装器用（本次 26 GB）——原因见 §3

### 1. 用 1401 生成 EFI 并写引导介质

1401 会扫描本机 ACPI/PCI 生成一份 EFI，并按哈希拉取 kext。它内置的 OpenCore 是
**DEBUG** 构建（会往 ESP 写 `opencore-*.txt` 日志，排错很有用）。

生成后写到内置 ESP：`usbwriter write <disk> <efi目录> <darwin大版本>`，
例如 `... 24` 表示 Sequoia（**不是** `--macos 15`）。写完整盘会被格式化，注意别选错盘。

### 2. 叠加本项目验证过的改动

| 位置 | 改动 | 为什么 |
|---|---|---|
| `Kernel → Patch` | 启用 `CaseySJ \| IOPCIIsHotplugPort \| Fix PCI bus enumeration on AM5 \| 13.0+` | **这才是 `[PCI configuration begin]` 卡死的真正解药** |
| `ACPI → Delete` | 删 `IVRS` | 同上，AMD IOMMU 表冲突 |
| `Kernel → Quirks` | `DisableIoMapper` / `DisableIoMapperMapping` = true | 同上 |
| `boot-args` | `npci=0x3000` | 辅助；**单独去掉它会 100% 丢包**，别删 |
| `Kernel → Add` | 追加 `HoRNDIS.kext`（TomHeaven 9.3 分支） | 安卓 USB 共享（本次未打通） |
| `Kernel → Add` | 追加 `itlmt7922.kext` + `itl_lvl=2 itl_amsdu=0` | MT7922 Wi-Fi，见下 |
| `Misc → Tools` | `NullMothSafe.efi` 两条 | NVIDIA 驱动卡死时的救急入口 |

`npci=0x2000` 那条是网上流传最广的偏方，**在本机从未真正生效**——详细证伪过程见
[引导排错实录](docs/03-引导排错实录.md)。

### 3. 装 macOS —— 离线安装的两个坑（本项目最重要的贡献）

没有可用网络时，macOS 安装器要**本地完整安装包**才装得下去。做法是把 Apple 的
`InstallAssistant.pkg` 拆成两半放到 exFAT 上，在恢复模式终端里跑 `startosinstall`：

```text
/Volumes/MACINSTALL/
├── SharedSupport.dmg     ← 苹果原版 InstallAssistant.pkg「改名」，不解压
└── app.tar               ← 安装器 .app（952 条目 / 25 个符号链接，tar 保住符号链接）
```

**坑 1：`SharedSupport.dmg` 必须是整个 pkg，不能是解出来的裸 dmg。**

安装器 `OSInstallerSetupInternal` 里的逻辑是：

```text
Will verify dmg as pkgdmg.
Getting offset for dmg in pkg: %s        ← 读 xar 的 data/offset、data/length
pkgdmg is missing a footer.
pkgdmg validation has failed.
→ Operation failed - OSISVerifyBaseSystemOperation
→ 错误 255「安装无法继续，因为安装器已损坏」
```

正确的文件就是 `InstallAssistant.pkg` 本身：头 4 字节 `78 61 72 21`（`xar!`）、
文件末尾那 512 字节的开头是 `6b 6f 6c 79`（`koly`）、大小 15,655,501,868 B。
从 pkg 里解出来的"纯 dmg"头是 FAT32 引导扇区（`eb 58 90 …`），会被判为无效。

**坑 2：`startosinstall --nointeractive` 在 macOS 13 之后被删除了。**

现在等价的是 `--forcequitapps`，传旧参数会得到 `unrecognized option` + 退出码 64。

最终可用的命令：

```sh
"/Volumes/INSTAPP/Install macOS Sequoia.app/Contents/Resources/startosinstall" \
    --volume /Volumes/MACOS \
    --agreetolicense --forcequitapps
```

安装器 `.app` 的符号链接必须保住：这里用 `tar` 打包再在 APFS 上解开
（exFAT 不支持符号链接，直接拷会把 `IAESD.framework`、`Versions/Current` 等 25 个链接
变成普通文本文件，`startosinstall` 连 dyld 都过不去）。
`Contents/SharedSupport/SharedSupport.dmg` 用**符号链接**指向 exFAT 上的 pkg，省掉 15 GB 拷贝。

### 4. 装完之后

1. 从 ESP 里拿出 `NullMoth\1401-Mac-2.3.6.zip`，把 `1401.app` 拖到 `/Applications` 再运行
   （**不要在 exFAT 上直接跑**），它会装 NVIDIA 驱动到 `/Library/Extensions/` 并注册两条救急工具
2. 重启
3. 用 1401 重新生成并写入你自己的 SMBIOS 三码

---

## EFI 目录说明

```text
EFI/
├── BOOT/BOOTx64.efi
└── OC/
    ├── ACPI/          7 张 SSDT
    ├── Drivers/       HfsPlus / OpenRuntime / ResetNvramEntry
    ├── Kexts/         只有 RogProbe2.kext（本项目自研）
    │                  ← 其余 21 个第三方 kext 由 scripts/fetch-kexts.ps1 拉取
    ├── Resources/     OpenCanopy GoldenGate 主题 + 字体（3.5 MB）
    ├── OpenCore.efi
    └── config.plist   ← 已脱敏；配置里引用 29 条 Kernel/Add
```

仓库树里**不含第三方 kext 二进制**（也**没有** `Tools/NullMothSafe.efi`），原因见
[第三方组件与许可](#第三方组件与许可)。跑一次 `scripts/fetch-kexts.ps1` 会把 22 个 kext 补齐，
并按 `scripts/kext-manifest.json` 逐个核对二进制 SHA256；`NullMothSafe.efi` 只能从
1401（或已有 ESP）取，脚本会去几个常见位置找，找不到只警告——那两条 `1401:` 菜单项不会出现，
不影响正常启动。

ACPI 表：`SSDT-EC`、`SSDT-PLUG-ALT`、`SSDT-USB-Reset`、`SSDT-USBX`、`SSDT-XOSI`、
`SSDT-ADP1`（伪装 AC）、`SSDT-ROG`；配套 `ACPI → Patch` 的 `_OSI → XOSI` 重命名。

---

## 关键参数的来历（逐条）

### boot-args

```text
-v debug=0x100 keepsyms=1     # 详细模式 + 内核符号，排错用；稳定后可去掉
nvfb=1 nvaccel=1 nvfbheads=4  # NullMoth 驱动必需（帧缓冲 / 加速 / 头数）
-nvkmsnosmooth                # NullMoth：关掉平滑缩放，修闪屏
amfi_get_out_of_my_way=0x1 amfi=0x80   # 旁路 AMFI，第三方 kext 才加载得起来
ipc_control_port_options=0    # 修部分场景的进程间通信 panic
gfxrst=4                      # NullMoth：GPU 复位档位
npci=0x3000                   # 辅助 PCI 枚举；单独去掉会 100% 丢包，别删
itl_lvl=2 itl_amsdu=0         # itlmt7922：降档 + 关 A-MSDU，缓解固件崩溃
```

> ⚠️ **绝对不要加 `nvfbhidpi=1`。** 它会让冷启动卡死在
> `NVNe: bar1: placing BAR1 8192 MB …`，而且"改完当时没事、下次开机才炸"。
> 详见 [卡死处置](#卡死处置症状--怎么办)。

### Kernel / Booter quirks（只列真正起作用的）

| 位置 | 项 | 说明 |
|---|---|---|
| Booter | `RebuildAppleMemoryMap` / `SetupVirtualMap` / `SyncRuntimePermissions` / `DevirtualiseMmio` / `ProvideCustomSlide` / `AvoidRuntimeDefrag` | AMD 交接内存映射这一组必须一起给 |
| Booter | `AllowRelocationBlock` / `FixupAppleEfiImages` / `DisableVariableWrite` | 1401 生成；修 EFI 镜像与 NVRAM 写 |
| Kernel | `DisableIoMapper` / `DisableIoMapperMapping` | 关 IOMMU 映射，配 `ACPI Delete IVRS` |
| Kernel | `ProvideCurrentCpuInfo` | AMD 必需的 CPU 信息伪造 |
| Kernel | `CustomSMBIOSGuid` | 自定义 SMBIOS |
| Kernel | `DisableRtcChecksum` / `SetApfsTrimTimeout=-1` | RTC 校验、APFS TRIM |
| Kernel | `PanicNoKextDump` / `PowerTimeoutKernelPanic` | 少 panic 现场，纯减噪 |

### Kernel → Patch

27 条，全部来自 [AMD_Vanilla](https://github.com/AMD-OSX/AMD_Vanilla)
（algrey / CaseySJ / Visual / Goldfish64 / laobamac / Zormeister），覆盖 Zen 4 的 CPUID、
`rdmsr`/`wrmsr`、`cpuid_cores_per_package`、PAT、非单调时间 panic。
**其中 `CaseySJ | IOPCIIsHotplugPort | Fix PCI bus enumeration on AM5` 是本机 PCI 卡死的真正解药。**

### DeviceProperties

```text
PciRoot(0x0)/Pci(0x8,0x1)/Pci(0x0,0x0)  disable-gpu: true   ← 屏蔽 Radeon 780M（macOS 无驱动）
PciRoot(0x0)/Pci(0x8,0x1)/Pci(0x0,0x6)  layout-id: 97       ← ALC256
PciRoot(0x0)/Pci(0x1,0x1)/Pci(0x0,0x0)  acpi-wake-type: 1   ← 唤醒类型
```

---

## 卡死处置（症状 → 怎么办）

| 症状 | 结论 | 处置 |
|---|---|---|
| 卡 `[PCI configuration begin]` | PCI 总线枚举死锁 | 启用 `CaseySJ IOPCIIsHotplugPort` 补丁 + 删 `IVRS` + `DisableIoMapper` |
| 卡 `NVNe: bar1: placing BAR1 8192 MB …` | NullMoth 驱动重排 root port 的 64 位窗口时挂住（**冷启动**最容易触发） | OpenCore 菜单 → **`1401: Start once without NVIDIA driver`**（只这次不加载驱动）；反复出现就用 **`1401: Remove NVIDIA driver`** |
| Wi-Fi 连上一小时后掉线、之后一直「连接失败」 | 固件 coredump，芯片进死状态，驱动自恢复失败 | **彻底断电**（关机 → 拔电源 → 长按电源 10 s → 开机），单纯重启不够 |
| 睡眠后黑屏 / 醒不过来 | **实测无法睡眠**（睡下去唤不醒） | 装完先关睡眠：`sudo pmset -a sleep 0 hibernatemode 0 standby 0 autopoweroff 0`；合盖休眠也在「系统设置 → 电池/锁定屏幕」里关掉 |

> 冷启动比热重启更容易踩 BAR1 那条。**尽量用重启而不是关机**，能躲掉大部分情况。

---

## Wi-Fi（实验驱动：能连，但不稳）

本机 Wi-Fi 是 **MediaTek MT7922 / RZ616**（`14c3:0616`），macOS 没有原生驱动。
本项目用的是社区实验驱动 [itlmt7922 v0.2.2](https://github.com/hbyonly1/itlmt7922-wifi)
（x86_64 / macOS 15，作者实测硬件正是 `14c3:0616`）。

**实测结论（来自驱动自己的 ioreg 日志）**：

```text
固件加载   stage1→stage9 全过，FIRMWARE READY MISC=00000003
扫描       CE scan done=1 ms=2925 aps=10 / aps=14
握手       auth status=0 → assoc status=0 aid=25 → eapol m1/m2/m3/m4 micBad=0
           → key_v2(ptk/gtk) rc=0 → RESULT rc=0 link up
速率       ch=161 bw=2 nss=2 rate~866   (5 GHz / 80 MHz / 2 流)
稳定段     up=3835s  rxd=357840  tx=319444  fail=0
然后崩了   3920s lost after 3847s at lvl 3: firmware coredump
崩后       recover: M1 rc=-5 → 每次扫描 CE scan submit rc=-110（超时）
```

也就是说：**能连、能跑满 866 Mbps，但持续高负载约 1 小时后固件会 coredump，
之后芯片不再响应，只能断电恢复。** 这是驱动/固件稳定性问题，不是配置问题。

已做的缓解（都在 `EFI/OC/config.plist` 里）：`itl_lvl=2` 降档、`itl_amsdu=0` 关 A-MSDU。
还可以加 `itl_no160=1`（关 160 MHz）、`itl_reo=0`（关重排）、`itl_pwr=N`（发射功率）。

**如果 Wi-Fi 是刚需，别赌这个驱动。** 本机没有 RJ45，四条现实路径：

| 方案 | 成本 | 稳定性 |
|---|---|---|
| **USB-A 千兆网卡，认准 RTL8153** | ~¥20 | ✅ macOS 原生免驱，插上就用 |
| 换 Wi-Fi 卡（Intel AX210 + itlwm / BCM94360NG） | ¥60~150 + 拆机 | ✅ 成熟方案；Intel 卡没有原生 AirDrop |
| 手机 USB 共享（HoRNDIS） | 免费 | ⚠️ 本机未打通 |
| 等 itlmt7922 上游修 | 免费 | ❌ 目前不适合日常 |

---

## 仓库结构

```text
EFI/                    可引导树（config + ACPI + OpenCore + 自研 RogProbe2），不含第三方 kext
hardware/               本机配置摘要
docs/                   完整调查过程（中文，按轮次）
  01-可行性评估.md
  02-安装手册.md         ← 从零安装步骤
  03-引导排错实录.md     ← "PCI configuration begin" 的完整证伪与解法
  04-驱动核对.md         ← 逐个 kext 的架构/依赖审计
  05-受控实验记录.md
  06 / 07 / 10           候选方案与实验设计
  08-RTX4050-BAR与PCI资源审计.md
  09-Linux-Live只读采集方案.md
  11-SystemUUID仅轮换方案.md
  12-候选配置说明.md
audit/                  PCI 资源 / 日志配置审计脚本与结果
logs/                   真实 OpenCore 引导日志（已脱敏）
scripts/
  fetch-kexts.ps1       ← 按固定哈希拉齐 22 个 kext（本仓库不再存第三方二进制）
  kext-pins.json        17 个上游压缩包的 URL + SHA256（取自 1401 mirror.json 并复核）
  kext-manifest.json    22 个 kext 的 bundle id / 版本 / 二进制 SHA256（本机实测）
  sync-to-github.ps1    最早那套"把卡上状态同步到 GitHub"的脚本
  sanitize-config.py    抹掉 SMBIOS 身份字段
  …                     其余为配置叠加 / 日志脱敏脚本
NOTICE.md               第三方组件与许可
```

---

## 第三方组件与许可

**仓库树不含第三方二进制。** `EFI/` 里只有 OpenCore 自己的文件（BSD-3-Clause）、
本项目生成的 ACPI/config，以及自研的 `RogProbe2.kext`。
22 个第三方 kext 用 `scripts/fetch-kexts.ps1` 按固定 SHA256 从上游拉取，
清单见 `scripts/kext-pins.json`，来源与许可见 [NOTICE.md](NOTICE.md)。

要点：

- **NullMoth NVIDIA 驱动 / 1401**：**PolyForm Noncommercial 1.0.0 —— 禁止商业使用**。
  驱动本体（`NVRM/NVAccel/NVRMFB`）从不进本仓库，只由 `1401.app` 装进 macOS；
  `NullMothSafe.efi` 同样只在本地从 1401 取
- **OpenCore**：BSD-3-Clause（`EFI/BOOT`、`EFI/OC/Drivers`、`EFI/OC/Resources`、`OpenCore.efi`）
- **AMD_Vanilla 内核补丁**：只是 config 里的字节序列，来源 AMD-OSX/AMD_Vanilla
- ✅ **打好的 Release zip 里包含第三方 kext**（方便直接用），但库里不存；
  如果你要完全避开第三方二进制，用仓库 + fetch 脚本这条路
- 若某上游作者不希望其产物被这样聚合，开 issue，我会立即移除对应条目

---

## 免责

- 黑苹果（在非 Apple 硬件上运行 macOS）**违反 Apple 的软件许可协议**，本项目仅供研究与学习
- 这套配置**显著降低系统安全性**（放宽 SIP、旁路 AMFI、关闭安全启动、SMBIOS 伪装）
- 文档里的实测结论对应 **2026-10** 的版本（1401 v2.3.6 / OpenCore 内置 DEBUG 构建 /
  itlmt7922 v0.2.2 / macOS 15.7.7），上游更新后可能不再适用
- 照做导致的数据丢失、保修失效、硬件损坏，本项目不承担任何责任

---

## 变更记录（本轮）

- ✅ **首次成功装进系统**：macOS 15.7.7 / 24G720，内屏 + NVIDIA 硬件加速可用
- ✅ 打通离线安装：确认 `SharedSupport.dmg` 必须是整个 pkg（pkgdmg），
  用 `startosinstall --forcequitapps` 替代已删除的 `--nointeractive`
- ✅ 定位并修掉 `nvfbhidpi=1` 导致的冷启动 BAR1 死锁
- ✅ 接入 MT7922 Wi-Fi（itlmt7922 v0.2.2），记录固件 coredump 的完整证据链与缓解参数
- ✅ 实测结论补完：**触摸板正常**、**无法睡眠**；蓝牙驱动已加载但**未测试**
- ✅ 仓库策略调整：第三方 kext 不再入库，改由 `scripts/fetch-kexts.ps1` 按固定 SHA256 拉取
  （17 个上游包 → 22 个 kext，全部哈希与本机实测一致）；需要开箱即用的走 Release zip
