# ASUS TUF Gaming A14 (FA401UU) — macOS 15 Sequoia + NVIDIA RTX 4050

> 用 [NullMoth NVIDIA 驱动](https://github.com/nullmoth/nvidia-macos-driver) 在 **RTX 4050 Laptop** 上跑起硬件加速的 macOS 15 Sequoia。
> 本仓库记录这台具体机型的完整踩坑过程、已验证配置、真实引导日志与排错脚本。
>
> **状态：进行中（未安装完成）。** 引导已进入 macOS 内核，正在逐个试 booter 内存映射 quirk —— 见 [引导排错实录](docs/03-引导排错实录.md)。

---

## 这台机器

| 部件 | 型号 | macOS 侧结论 |
|---|---|---|
| 机型 | ASUS TUF Gaming A14 **FA401UU** | BIOS `FA401UU.311`，UEFI |
| CPU | **AMD Ryzen 7 8845H**（Zen 4 / Hawk Point，8C/16T） | ✅ 可用，需 AMD_Vanilla 内核补丁 |
| 核显 | AMD Radeon 780M (`1002:1900`) | ❌ macOS 无驱动 → 用 `disable-gpu` 屏蔽 |
| 独显 | **NVIDIA RTX 4050 Laptop** (`10DE:28E1`, AD107) | ⚠️ 在驱动设备表内，Ada 家族未验证 |
| 内屏 | BOE NE140QDM-NX7，**2560×1600 @165Hz**，eDP | ⚠️ 需 MUX 切「独显直连」才能由 N 卡驱动 |
| 内存 | 16GB LPDDR5X-7500（板载） | ✅ |
| 硬盘 | WD PC SN740 512G NVMe | ✅ 与 Windows 共用，分出 128GiB 给 macOS |
| 无线 | MediaTek MT7922 (RZ616) | ❌ 无驱动，且被 SSDT 主动屏蔽 |
| 声卡 | Realtek ALC256 | ⚠️ AppleALC `layout-id 56`（该 ID 在 AppleALC 1.9.9 中确实存在） |
| 有线 | 无 RJ45 口 | ❌ USB 网卡仅 RTL8153 类可用（RTL8156 不行） |

关键前提：**FA401 系列有 MUX 开关**。必须先在 Armoury Crate 里切到「独显直连 / Ultimate」，
官方扫描工具才会报告 `Monitor: NE140QDM-NX7, Connected GPU: NVIDIA GeForce RTX 4050 Laptop GPU` ——
这是内屏能被点亮的必要条件（否则内屏挂在无驱动的 780M 上，必然全黑）。

---

## 已验证清单

| 项目 | 结果 | 证据 |
|---|---|---|
| U 盘 OpenCore 引导 | ✅ | MBR + active FAT32，走 `\EFI\BOOT\BOOTX64.EFI`，实机启动成功 |
| OpenCore 配置合法性 | ✅ | 官方 `ocvalidate` 1.0.9：**0 issues** |
| boot.efi 交接 | ✅ | 日志出现 `AAPL: #[EB|LOG:EXITBS:START]` |
| macOS 内核启动 | ✅ | 见 [排错实录](docs/03-引导排错实录.md) 的屏幕记录 |
| kext 加载 | ✅ | VoodooI2C / VoodooPS2 / VirtualSMC / WhateverGreen 等均加载 |
| AMD 内核补丁 | ✅ | 日志：`IOPCIFamily (CaseySJ probeBusGated) ... Success` |
| 内屏由 N 卡驱动 | ✅ | 官方扫描工具的输出 |
| 安装 macOS | ⬜ | 当前卡在内核早期，见下 |

---

## 三个卡点与它们的解法

完整证据（日志行 + 源码依据）见 **[docs/03-引导排错实录.md](docs/03-引导排错实录.md)**。

### 1. 选择器停在 `Timeout` —— 其实只是慢，不是死机

第一反应会以为是键盘不工作。**不是。** OpenCore 日志显示倒计时正常走完并自动选中了安装器：

```
09:988 05:020 OCHK: FreeHotKeys
10:021 00:010 OCB: Should boot from 1. 1401 (T:4|F:1|G:0|E:1|DEF:0)
```

真正的"卡"是 `DmgLoading = Signed` 触发的 **DMG 分块校验**（85 个分块 / 847 MiB 的 SHA-256）。
这段路径**按设计没有任何日志输出**（[`DmgBootSupport.c`](https://github.com/acidanthera/OpenCorePkg) 里每个*失败*分支才打日志），
所以看起来像死机，其实在算。**等 1–2 分钟就过去了**，或者把 `Misc → Security → DmgLoading` 设为 `Any` 直接跳过。

### 2. `PCI configuration begin` —— `npci=0x2000`

```
PCI configuration begin
IOPCIConfigurator::configure() PCI configuration PCI0
```

1401 的 `bootfix.py` 里对这两行字有**逐字对应**的规则（它的自测用例就是 `"[IOPCIConfigurator::configure()] PCI configuration PCI0"`）：

```python
# Dortania troubleshooting, "Stuck on [PCI configuration begin]": npci=0x2000, then npci=0x3000
```

加 `npci=0x2000` 后 **确实越过了**。

### 3. 内核早期停住 —— booter 内存映射 quirk（进行中）

越过 PCI 枚举后内核跑得很远：ACPI 表解析完、16 个 CPU 全部启用、IOAPIC 与 RTC 初始化，
最后一行是 `RTC: Only single RAM bank (128 bytes)`。

把 U 盘上 4 份真实日志喂给 1401 自己的 `bootfix` 诊断器，它判定为 AMD hand-off 情形并按阶梯改配置：

| 档位 | 规则 | 改动 | 结果 |
|---|---|---|---|
| 第一档 | `bootlog-amd-exitbs` | `RebuildAppleMemoryMap=False`、`EnableWriteUnprotector=True`、`SyncRuntimePermissions=False` | ❌ 仍停 |
| 第二档 | `bootlog-handoff-devirt` | 保留上组，`DevirtualiseMmio=False` | ⬜ **当前状态，待验证** |

---

## 快速上手

本项目**不重新分发任何第三方二进制**（驱动包 / kext / OpenCore 发行版），需要用 1401 现场生成：

1. 用 [1401](https://github.com/nullmoth/1401) 的「Check this PC」扫描本机 → 得到 `Report.json` + ACPI 转储
2. 用 1401 构建 EFI（会自带 AMD Vanilla 补丁、`ProvideCurrentCpuInfo` 等），然后按下表叠加本项目验证过的改动
3. 写入 U 盘：`1401` 的 Mac App 或 `p1401.usbwriter`
4. BIOS：**Above 4G Decoding / Resizable BAR 无需手动开**（华硕对 Ryzen 5000+ 默认开启且不显示该选项；
   实测 `nvidia-smi` 报 `BAR1 = 8192 MiB` 即为已开启）。Secure Boot 关、CSM 关即可。
5. 引导：开机连按 Esc → 选 U 盘 → OpenCore 里选 `1401 (external) (dmg)`

### 本项目已验证的配置改动（叠加在 1401 的构建结果上）

```
boot-args    ... npci=0x2000
Misc.Security.DmgLoading              = Any          （跳过慢速 DMG 校验）
Booter.Quirks.DevirtualiseMmio        = False        ← 第二档，待验证
Booter.Quirks.SetupVirtualMap         = True
Booter.Quirks.RebuildAppleMemoryMap   = False
Booter.Quirks.EnableWriteUnprotector  = True
Booter.Quirks.SyncRuntimePermissions  = False
Booter.Quirks.ResizeAppleGpuBars      = 0            （安装器专用，N 卡大 BAR 会顶掉固件帧缓冲）
UEFI.Quirks.ResizeGpuBars             = -1
Kernel.Add                            26 个 kext（含注入的 HoRNDIS，见下）
```

`efi/config.plist` 是**已验证可引导**的那份配置（SMBIOS 身份字段已抹除，见下）。

### 安装期的联网（本机特有难点）

无 RJ45 口 + MT7922 无驱动 + RTL8156 型 USB 网卡在 macOS 下无原生支持（它以厂商自定义类 0xFF 枚举，
不是 CDC-ECM）→ 安装器里没网。本项目注入 **HoRNDIS**（`TomHeaven/HoRNDIS` 9.3，x86_64 切片、仅依赖原生 IOKit）
以支持**安卓手机 USB 共享网络**；备选是 RTL8153 芯片的 USB 网卡（macOS 自带 `AppleUSBRealtek8153Patcher`）。

---

## 仓库结构

```
README.md                     本文件
docs/01-可行性评估.md          项目可行性、硬件逐项判定、已知风险
docs/02-安装手册.md            完整操作手册（BIOS/分区/驱动安装/风险对策）
docs/03-引导排错实录.md         ★ 每次引导卡死的证据、根因、解法
docs/04-驱动核对.md            kext 逐个审计（版本/架构/顺序/依赖）
hardware/本机配置摘要.md        脱敏后的硬件清单
efi/config.plist              已验证配置（SMBIOS 身份已抹除）
efi/README.md                 kext 清单与用 1401 重建的方法
logs/opencore-*.txt           4 份真实 OpenCore 引导日志（已脱敏）
logs/bootfix-findings.md      1401 诊断器对这些日志的判定
scripts/read-screen-photo.py  把手机拍的启动画面裁切放大以读清文字
scripts/patch-stick-config.py 免提权、直接改 U 盘上 config.plist 的小工具
scripts/rewrite-stick-as-admin.cmd  提权重写 U 盘的模板脚本
```

## 隐私说明

公开前已抹除：SMBIOS `SystemSerialNumber` / `MLB` / `SystemUUID` / `ROM`、
原始扫描报告（含网卡 MAC 与磁盘序列号）**未收录**、日志中的磁盘序列号。
**直接使用 `efi/config.plist` 前请用自己的序列号**（用 1401 重新生成即可），不要照抄示例里的占位值。

## 许可与致谢

本项目自有内容（文档、脚本、配置）以 **MIT** 发布，见 [LICENSE](LICENSE)。
**不包含**任何第三方二进制。第三方组件的归属与许可见 [NOTICE.md](NOTICE.md) ——
特别是 **NullMoth NVIDIA 驱动为 PolyForm Noncommercial 1.0.0（禁止商业使用）**，本项目只链接、不分发。

> 免责：黑苹果违反 Apple 软件许可协议，仅供研究。本仓库的配置会降低系统安全性
> （放宽 SIP、旁路 AMFI、关闭安全启动），请勿用于处理敏感数据的主力机。
