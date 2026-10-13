# ASUS TUF Gaming A14 (FA401UU) — macOS 15 Sequoia + NVIDIA RTX 4050

> 用 [NullMoth NVIDIA 驱动](https://github.com/nullmoth/nvidia-macos-driver) 在 **RTX 4050 Laptop** 上跑起硬件加速的 macOS 15 Sequoia。
> 本仓库记录这台具体机型的完整踩坑过程、已验证配置、真实引导日志与排错脚本。
>
> **状态：进行中（未安装完成）。** 第一轮修好了"`boot-args` 从未生效"这个把此前所有结论都
> 污染掉的问题；第二轮（禁用 VoodooI2C 家族）六项预注册检查**全部符合预期**。
> 第三轮（只移除 `npci=0x2000`）已正式记录为「**实验配置生效，但未能成功启动**」——
> 配置侧有日志实证，屏幕侧在 `RTC: Only single RAM bank` 处 **≥10 分钟无输出且未进 Recovery**；
> 该行**不是**已确认死因，且**未**据此排除 npci 的影响。
> 第四轮（MAT 内存映射三元组）**已写入卡上、待引导验证** —— 见
> [受控实验记录](docs/05-受控实验记录.md) 与 [引导排错实录](docs/03-引导排错实录.md)。

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
| OpenCore 配置合法性 | ✅ | 官方 `ocvalidate` 1.0.9：**0 issues**（与 U 盘上 `DBG-109` 同版本） |
| boot.efi 交接 | ✅ | 日志出现 `AAPL: #[EB|LOG:EXITBS:START]` |
| macOS 内核启动 | ✅ | `AppleACPICPU ×16`、`IOAPIC`、`ACPI: Executed 29 blocks`、`RTC:` 均已在屏幕上出现 |
| kext 加载 | ✅ | 25 个 kext 全部 `Prelinked injection … Success`，`OC: Prelinked status - Success` |
| AMD 内核补丁 | ✅ | 27 条全部命中；核心数补丁确认为 **8 核**；Zen4 IOPCIFamily 与 Sequoia PAT 补丁版本门控正确 |
| `boot-args` 实际生效 | ✅ | 第一轮修复后：`OC: Deleting NVRAM …:boot-args - Success` → `OCVAR: Setting NVRAM …:boot-args - Success`，且 `MBA:OUT` 含 `npci=0x2000` |
| 内屏由 N 卡驱动 | ✅ | 官方扫描工具的输出 |
| 安装 macOS | ⬜ | 当前停在 AMD I2C 控制器 `start()`，见下 |

---

## 卡点与解法（含两处勘误）

完整证据（日志行 + 上游源码行号）见 **[docs/03-引导排错实录.md](docs/03-引导排错实录.md)**；
每一步改动的实验设计与回滚见 **[docs/05-受控实验记录.md](docs/05-受控实验记录.md)**。

### 1. 选择器停在 `Timeout` —— 其实只是慢，不是死机

第一反应会以为是键盘不工作。**不是。** OpenCore 日志显示倒计时正常走完并自动选中了安装器：

```
09:988 05:020 OCHK: FreeHotKeys
10:021 00:010 OCB: Should boot from 1. 1401 (T:4|F:1|G:0|E:1|DEF:0)
```

真正的"卡"是 [DMG 分块校验](https://github.com/acidanthera/OpenCorePkg)（85 个分块 / 847 MiB 的 SHA-256）。
`DmgBootSupport.c` 里每个*失败*分支才打日志，**成功路径按设计完全静默**，所以看起来像死机，
其实在算 —— 实测这段要 **27.45 秒**（U 盘只有 38.9 MB/s）。
**等 1–2 分钟就过去了**，或者把 `Misc → Security → DmgLoading` 设为 `Any` 直接跳过。

> 我们第一份日志（`logs/opencore-2026-10-12-233441.txt`）就是**死在这一段**的，
> 它只有 43 KB、没有 `AAPL:` 行、`boot.efi` 从未启动。**别把它当成一次"引导失败"。**

### 2. `PCI configuration begin` → `npci=0x2000` **其实从来没有生效**

第一次我们加了 `npci=0x2000` 并认为"越过了"。**这个归因是错的。**

四份日志一起看：**在所有有日志的引导里，内核拿到的 `boot-args` 里都没有 `npci=0x2000`。**

```
OCVAR: Setting NVRAM 7C436110-...:boot-args - ignored, exists
AAPL: #[EB|MBA:NV]  <"-v debug=0x100 ... ipc_control_port_options=0 slide=246">
AAPL: #[EB|MBA:OUT] <"-v debug=0x100 ... ipc_control_port_options=0 slide=246">
```

原因是 OpenCore 的机制（`OpenCoreNvram.c`）：`OcDeleteNvram()` 先跑、`OcAddNvram()` 后跑，
而 `OcAddNvram` **硬编码 `Overwrite = FALSE`** —— 变量已存在就只打印 `ignored, exists`，不写。
唯一能清掉它的是 `Delete` 阶段，而当时 `Delete` 里**没有 `boot-args`**。
→ 变量被第一次引导写入的值永久冻住了。

**教训：判断"配置是否生效"必须看日志里的 `OCABC:` / `OCVAR:` / `AAPL: #[EB|MBA:OUT]`，
而不是看 `config.plist` 写了什么。** 详见 [排错实录](docs/03-引导排错实录.md) 第 2 节。

### 3. 内核跑得很远，然后停住 —— booter 内存映射 quirk（进行中）

内核推进得很深，最后几行（照片裁切放大后读取）：

```
AppleACPICPU: ProcessorId=0..15 ... Enabled
IOAPIC: Version 0x21 Vectors 64:87
ACPI: Executed 29 blocks of module-level executable AML code
ACPI: sleep states S4 S5
RTC: Only single RAM bank (128 bytes)                       ← 最后一行
```

1401 的 `bootfix` 诊断器把它判为 "AMD hand-off 情形"并逐档改配置：

| 档位 | 规则 | 改动 | 实际结果 |
|---|---|---|---|
| 第一档 | `bootlog-amd-exitbs` | `RebuildAppleMemoryMap=False`、`EnableWriteUnprotector=True`、`SyncRuntimePermissions=False` | ❌ 仍停（第 4 次引导） |
| 第二档 | `bootlog-handoff-devirt` | 保留上组，`DevirtualiseMmio=False` | ⬜ **从未引导过 → 已在第一轮主动撤下** |

> **勘误**：这一档的触发前提是"内核从未打印"（`bootfix.py` 第 156–158 行注释：
> *"the screen freezes on EXITBS:START, the kernel never prints"*）。
> 但屏幕照片证明**内核已经跑起来了** —— 上面那些行全是 ExitBootServices **之后**的输出。
> **所以第一档放弃 Dortania MAT 组合的理由对这台机器不成立。**
> 详见 [受控实验记录](docs/05-受控实验记录.md) 的 D3。

### 4. 第一轮：把实测条件弄干净 —— ✅ 已成功

`npci` 从未生效，意味着此前所有"某改动有效/无效"的结论都不可靠。所以第一轮**只做一件事**：
把 `boot-args` 加入 `NVRAM → Delete`，让那个写了很久的 `npci=0x2000` **第一次真正进入内核**，
同时把未实测的第二档撤回实测基线。相对基线的 diff **只有 1 行**。

**结果**（`logs/opencore-2026-10-13-011110.txt`）：

```
00:231  OC: Deleting NVRAM 7C436110-…:boot-args - Success      ← 冻结值被清掉
00:280  OCVAR: Setting NVRAM 7C436110-…:boot-args - Success    ← 新值写入
15:255  AAPL: #[EB|MBA:OUT] <"… ipc_control_port_options=0 npci=0x2000 slide=159">
```

同时 `OCABC:` 确认本轮真正生效的内存映射参数就是实测基线
（`DEVMMIO 1 / VMAP 1 / WRUNPROT 1 / RBMAP 0 / RTPERMS 0`），
`OC: Prelinked status - Success`，且仓库配置经脱敏后与卡上**逐字节相同**。

### 5. 第二轮（已写入卡上，待引导验证）：隔离 AMD I2C（AMDI0010）控制器

屏幕最后一行停在 `VoodooI2C…Controller::AMDI0010 Starting I2C controller`。
经 DSDT 反编译确认，**触摸板正是挂在 `\_SB.I2CA`（`_HID = AMDI0010`）上**，
所以这不是无关旁支，而是触摸板所在控制器。

单变量改动：禁用 4 个 VoodooI2C 家族条目（`VoodooI2C` / `VoodooGPIO` /
`VoodooI2CServices` / `VoodooI2CHID`），diff **只有 4 行 `true` → `false`**；
`VoodooInput` 保留启用（它与 I2C bundle 无加载依赖，且 `VoodooPS2Trackpad` 运行时需要它），
`VoodooPS2Controller` 一族全部保留。详见
[受控实验记录](docs/05-受控实验记录.md) 第 4 节（含依赖闭包证明与判定标准）。

**写入结果**：`08781B25C755B1B5…`（52137 B，`ocvalidate` 0 issues，SMBIOS 原样保留，
其余段落逐字节未变）。回滚：`D:\_backup-round0\config.plist.round1`。

**实测结果**（`logs/opencore-2026-10-13-020808.txt`）：六项**全部符合预期** ——
`MBA:OUT` 仍含 `npci=0x2000`；`OCABC` 与 Round 1 逐字相同；`Prelinked status - Success`；
四个 VoodooI2C kext **各 0 条注入**；独立 `VoodooInput` 成功注入（且只有一份）；
无 panic 文件、无新错误。截图停在 `PCI configuration begin`，但**无停留时长**，见 §6。

### 6. 第三轮（已写入卡上，待引导验证）：只移除 `npci=0x2000`

**为什么它是干净的单一变量**：Apple 自己的 `IOPCIFamily` 源码里 `npci=` 是 `pci=` 的**取反**
（`gIOPCIFlags &= ~debug`），而 `kIOPCIConfiguratorPFM64 = 0x2000` **默认是置位的** ——
所以 `npci=0x2000` 等于**清除 PFM64 标志**。

该标志在源码里只被**引用 5 次、其中仅 3 处是行为测试**，且全部是把 `maxAddress` 设为全 1
（即"允许 64 位 BAR 与 prefetchable 区间落在 64 位地址空间的任意位置"）。
**合成窗口那段并不检查该标志**（只看 `hasHostMemory && !hasHost64 && !fAddedHost64`，
尺寸由 `fPFM64Size` / `pci64=` 决定）—— 所以**不能说** `npci=0x2000` "关闭了 64 位 MMIO"。

本机的实测事实是：**Above 4G Decoding 已启用**（GPU 的 BAR 被固件放在 `0x7E00000000` ≈ 504 GiB，
不是靠 BAR1 大小推的）、**BAR1 = 8 GiB ReBAR**（已超出 macOS 1 GB 的理论上限，靠
`ResizeAppleGpuBars=0` 缩到 64 MB）。这类设备的 64 位 BAR 恰好依赖上面那条许可，所以本轮要检验的
**推论**是"清除 PFM64 收回了本机需要的 64 位安置余量"。**这只是推论，不是已知结论。**

同时 `docs/03` 那句"加 npci 就越过了 `PCI configuration begin`"**已被证伪**：
第 2、3 次引导是在 `MBA:OUT` 里**根本没有 npci** 的情况下越过该阶段的。

**改动：相对 Round 2 只有 1 行**（删掉 `boot-args` 末尾的 ` npci=0x2000`），
`Booter.Quirks` / AMD 补丁 / ACPI / SMBIOS / BAR / DeviceProperties 全部逐字节不变，
`NVRAM → Delete` 里**继续保留 `boot-args`**。

**写入结果**：`4642CD80748AF3A6…`（52125 B，`ocvalidate` 1.0.9 → 0 issues，SMBIOS 原样保留，
其余段落逐字节未变；33 项自检全 PASS）。回滚：`D:\_backup-round0\config.plist.round2`。

> **不**替换成 `npci=0x3000`，**不**改 BIOS，**不**动 IOMMU，**不**自动切 MAT。
> 若本轮仍卡住，**只能**记为"移除 npci 不足以解决当前问题"—— **不能**据此排除 npci 本身的影响，
> **也不能**因此锁定 ACPI/MAT。详见 [受控实验记录](docs/05-受控实验记录.md) §6。

**屏幕现象（用户报告并已确认停留时长）**：最后一行是 `RTC: Only single RAM bank (128 bytes)`，
在此处**连续 ≥10 分钟无新输出、未进入 Recovery**。

> **正式结论：实验配置生效，但未能成功启动。**
> **⚠️ 两条不许越界的推论**：(1) 该行**不是**已确认死因 —— 它是 AppleRTC 的信息性输出，
> 且"最后一行"在四轮之间来回移动（修复前是这条、round1 是 VoodooI2C `start()`、
> round2 是 `PCI configuration begin`），本轮没有任何指向 RTC 子系统的独立证据；
> (2) 本轮只证明"**移除 npci 不足以解决问题**"，**不能**说明 npci 原本没有影响，
> 也**不能**据此锁定 ACPI / MAT / IOMMU。
> 另：`OC: Panic log does not exist` 出现在 `01:129`（boot.efi 启动**之前**），
> **不能**用来证明内核没有故障。

> **勘误（第四轮引导后补充）**：本节"停在 `RTC:`"这一读法**已被证伪**。Round 2 的照片证明
> **同一次启动**里 `RTC: Only single RAM bank (128 bytes)` 之后还有大量输出
> （`AppleCredentialManager` / `AppleKeyStore` / `CoreAnalyticsHub` / `AppleVTD` … 一直到
> `PCI configuration begin`）；Round 4 在**同样没有 `npci`** 的条件下也越过了 `RTC:`。
> 所以 `RTC:` 这一行**不是**独立卡点，本轮的停点是 `IOPCIConfigurator::configure()`。
> 详见 [受控实验记录](docs/05-受控实验记录.md) §7.11 与
> [只读分析](docs/06-只读分析与Round5候选.md) §1.3 / §1.4。

### 7. 第四轮：MAT 内存映射三元组（已写入并已实测）

| Quirk | round3（改前） | round4（**卡上现状**） |
|---|---|---|
| `EnableWriteUnprotector` | `True` | **`False`** |
| `RebuildAppleMemoryMap` | `False` | **`True`** |
| `SyncRuntimePermissions` | `False` | **`True`** |

其余全部不变（`DevirtualiseMmio=True`、`SetupVirtualMap=True`、I2C 仍禁用、无 `npci`、
AMD 补丁 / ACPI / SMBIOS / BAR / DeviceProperties 逐字节相同）。

**为什么适合 FA401UU**：Dortania 的条件原文是 *"If your firmware supports MATs (2018+ firmwares)"*，
并让你用日志确认 —— 本机**每轮引导都打印 `OCABC: MAT support is 1`**，条件满足；
而 OpenCore 文档写明 `RebuildAppleMemoryMap` 是**取代** `EnableWriteUnprotector` 的那一个，
所以卡上现状用的正是 Dortania 给**不支持 MAT 的旧固件**的组合。

**必须同时知道的反面证据**：第 2、3 次引导**已经跑过这组组合**并同样停住 ——
但那两次 `npci` **未被应用**、I2C 家族**仍启用**。所以本轮是它**第一次**在干净条件下运行。

精确 diff（**3 行**，1-based 行号 181 / 199 / 207）、判定标准、回滚与 Round 5 方向见
[受控实验记录](docs/05-受控实验记录.md) §7。

**写入结果**：`021F02B3B4695302…`（52124 B，`ocvalidate` 1.0.9 → 0 issues，SMBIOS 原样保留，
`Booter.Quirks` 里**恰好只有这 3 个键**变化，其余段落逐字节未变；42 项自检全 PASS）。
回滚：`D:\_backup-round0\config.plist.round3`。

**实测结果**（`logs/opencore-2026-10-13-095517.txt`）：日志侧 **7 项全部符合预期** ——
`WRUNPROT 0 / RBMAP 1 / VMAP 1 / RTPERMS 1 / DEVMMIO 1 / MAT support is 1`
（日志 `12:484 OC: Prelinked status - Success`，21 条 kext 注入全部 `- Success`）、
`MBA:OUT` 无 `npci`、四个 VoodooI2C 条目仍不注入。

> ### Round 4 正式结论（已定稿）
>
> **配置生效，内核启动未成功，已确认 ≥10 分钟无新屏幕输出。**
>
> 实机操作者确认：在下面两行连续停留 **>10 分钟**，屏幕无新输出，**未进入 macOS Recovery**：
> ```text
> [ PCI configuration begin ]
> [IOPCIConfigurator::configure()] PCI configuration PCI0
> ```
> 同一次启动在此之前已出现 `RTC:`、`AppleCredentialManager`、`AppleKeyStore`、`AppleSSE`、
> `CoreAnalyticsHub`。（照片文件仍未提供，故屏幕内容记为**操作者确认陈述**；**时长已确认**。）

> **两条必须同时成立的限制**
>
> 1. **屏幕停点是"结构性"的**：`IOPCIConfigurator.cpp` 在 `:3342` 调
>    `setConsoleInfo(0, kPEDisableScreen)` **之后**才执行 `doConfigure()`，而
>    `[ PCI configuration end ]` 在屏幕重新开启**之后**才打印。所以严格可得的结论只有
>    **"≥10 分钟没出现 `PCI configuration end` ⇒ `configure()` 没走到 `:3388`"** ——
>    这**不等于**证明内部死锁，也**不能**指出停在哪台 PCI 设备。
> 2. **控制台会滚动，屏幕上只有最后约 40 行**（Round 2 照片顶端可见行已是
>    `ACPI: sleep states S4 S5`）⇒ 停在 PCI 的那类引导里，**早期的 ACPI 失败计数读不到**。

> **本轮最重要的新事实**：Round 2（`MBA:OUT` 里**有** `npci=0x2000`，`WRUNPROT 1/RBMAP 0/RTPERMS 0`）
> 与 Round 4（**无** `npci`，`0/1/1`）**最后可见行完全相同**。
> ⇒ 在这个停点上，`npci=0x2000` 与这组 MAT 组合**都不足以**让系统进入 Recovery；
> 但**不能**因此说它们"对内核行为无影响"（两轮**内部**停点是否相同**无法证明**）。
> 详见 [受控实验记录](docs/05-受控实验记录.md) §7.10 / §7.11。

> **Round 3 的观测保留**：实机操作者确认 Round 3 曾在
> `RTC: Only single RAM bank (128 bytes)` 处停留 ≥10 分钟无新输出。
> 该事实**不改写**；Round 4 在同样没有 `npci` 的情况下出现了后续 PCI 日志，
> ⇒ **不同轮次执行结果存在差异，目前无法解释**（只能说 `RTC:` 不一定是稳定复现的独立根因）。

**⛔ 执行后即停止** —— 未获批准**不执行 Round 5**，**不**修改 MMIO 白名单、ACPI、IOMMU、
`npci`、BAR 或其它 kext。

**Round 5B 已获批并写入卡上（待引导验证）** —— 详见 [docs/05](docs/05-受控实验记录.md) §7.12 与
[docs/06](docs/06-只读分析与Round5候选.md) §4.6：

* **唯一改动**：`Booter → Quirks → DevirtualiseMmio`：`true` → **`false`**（**只此 1 行**，
  1-based 行号 **171**）。
* 卡上 `021F02B3…`（52124 B）→ **`34605D9D…`（52125 B）**，读回哈希与批准前给出的预测值**完全一致**。
* `ocvalidate` 1.0.9 DEBUG（对卡上文件）→ **No issues found**。
* 备份：`D:\_backup-round0\config.plist.round4`；回滚一步命令见 `docs/05` §7.12。
* 未使用 GitHub 脱敏候选覆盖真实 EFI —— **SMBIOS 与备份逐字节相同**。

**已引导，结果见 [docs/05](docs/05-受控实验记录.md) §7.13**（两次引导，
`logs/opencore-2026-10-13-143611.txt` 与 `…-143926.txt`）：

| 检查项 | 结果 |
|---|---|
| `DEVMMIO=0` | ✅ |
| 5 条 `OCABC: MMIO devirt …` 不再出现 | ✅ **0 次** |
| 是否提前出现内存映射错误 | ❌ **没有**（无 `EB.MM.AKM`/`STOP 0x16`/`No slide values are usable`；`Valid slides - 81-255` 与 Round 4 逐字相同） |
| 是否重新到达 `PCI configuration` | ❌ **没有** |
| 是否出现 `PCI configuration end` / 进入 Recovery | ❌ **都没有** |

> **屏幕侧（仅第 1 次引导有照片 `IMG20261013143753.jpg`）**：屏幕停在 boot.efi 的
> `#[EB|LOG:EXITBS:START]`，**其下没有任何 macOS 内核输出**（OpenCore 选择菜单仍留在顶部）
> ⇒ **内核零输出**。参照：Round 2 在引导后约 90 秒时屏幕已滚过约 40 行内核输出。
> ⇒ **失败点前移**：Round 4 到过 `PCI configuration begin`，本轮内核一行未打印。
>
> **推论限制（按批准时的判据修正）**：这**只**说明 `DevirtualiseMmio=false`
> **影响了内存映射或启动兼容性**。**不能**推断"固件运行期访问了某块 MMIO"，
> **不能**据此确定任何 `MmioWhitelist` 地址。且**未出现** `EB.MM.AKM`/`STOP 0x16`
> ⇒ **不是** issue #9 那类 boot.efi 阶段失败；失败点落在 `EXITBS:START` 之后、
> 内核首次打印之前，**日志无法定位**。
>
> **观测完整性（结案后）**：**首轮已确认** —— 实机操作者确认照片最后显示
> `[EB|LOG:EXITBS:START]`，其后**连续等待 >10 分钟**无新屏幕输出，未进入 Recovery。
> **次轮（14:39）只有 OpenCore 日志、没有照片** ⇒ **不得**写成"次轮也确认等待了 10 分钟"，
> 只能记为"次轮 OpenCore 阶段与首轮逐行同型，屏幕状态未验证"。

### Round 5B 正式结案 + 已回滚到 Round 4

> **Round 5B 定稿：配置生效、实机未能成功启动、首轮已确认 ≥10 分钟无新屏幕输出。**

记录（实机）：**禁用 `DevirtualiseMmio` 后，最后可见输出相比 Round 4 明显前移**
（Round 4 到过 `[ PCI configuration begin ]`；Round 5B 内核一行未打印），
**但不能确认具体故障指令或 MMIO 地址**。

| 回滚步骤 | 结果 |
|---|---|
| 回滚前卡上 SHA-256 | ✅ `34605D9D…`（== 批准基线） |
| 备份有效性 | ✅ `D:\_backup-round0\config.plist.round4` == `021F02B3…` |
| 执行 | `Copy-Item D:\_backup-round0\config.plist.round4 D:\EFI\OC\config.plist -Force` |
| **回滚后 SHA-256** | ✅ **`021F02B3B46953021FF31835518790DD6BEB57074BE822D127305434581815E4`**（52124 B） |
| `ocvalidate` 1.0.9 DEBUG（卡上） | ✅ **No issues found**（exit 0） |

**卡上现状 = Round 4**（`021F02B3…`）。本轮未批准任何其它 EFI 修改。
上游案例复核与 Round 6 候选见 **[docs/07-上游案例复核与Round6候选.md](docs/07-上游案例复核与Round6候选.md)**。

### Round 6 候选（**只准备，未写入 U 盘**）

**单变量**：`NVRAM → Add → 7C436110-…:boot-args` 末尾追加 ` npci=0x3000`（**仅此 1 行**，
1-based 行号 **1920**；52124 → **52136** B；卡上预测 SHA-256 **`43ABBAD5…`**）。
候选文件 [`efi/candidates/round6-npci-0x3000.plist`](efi/candidates/round6-npci-0x3000.plist)
（`ocvalidate` → No issues found）。其余全部不动：`DevirtualiseMmio=True`、`SetupVirtualMap=True`、
MAT 三元组、`ResizeAppleGpuBars=0`、`UEFI.ResizeGpuBars=-1`、四个 VoodooI2C 仍禁用、
`MmioWhitelist=[]`、ACPI 7 条、`Kernel.Patch` 27 条、SMBIOS。详见 docs/07 §8 / §10。

> **为什么是它**：Round 5B 已把"内存图"这一轴指向**变差**方向，所以下一步不该在同一轴继续试错，
> 而应当**用最低成本把唯一还没走完的 boot-arg 轴（`npci`）走完** ——
> 目前只有 `npci=0x2000` 在**本停点**被测过；Dortania 与 1401 的 `bootfix.py` 都会在它失败后
> 再试 `0x3000`。测完就能把结论从"`0x2000` 不足"升级为
> "**整条 `npci` 阶梯都不足以进入 Recovery**"，从而把怀疑范围**干净地**压到
> `configure()` 内部的资源/BAR 分配上。
> **不预设它比 `npci=0x2000` 更有效。** 就这两个 boot-arg 而言，`0x3000` 相对 `0x2000`
> 只多清一位 `kIOPCIConfiguratorTBMSIEnable`（只作用于 Thunderbolt 隧穿 MSI 路径，
> IOPCIFamily-681.140.3 `IOPCIBridge.cpp:5723`），与本机卡点先验关联度低；它的价值是**消除性**的。
>
> **⚠️ 判据修正（批准 Round 6 时要求）**
> 1. **不得把 Round 6 描述成"只测试 `TBMSIEnable`"。** 基线是 **Round 4（无 `npci`）**，
>    所以 `npci=0x3000` **同时清掉 `PFM64` 与 `TBMSIEnable` 两位**。
>    而且 Round 2 虽然用过 `npci=0x2000`，但**那轮 MAT 三元组不同**（`1/0/0` vs `0/1/1`）
>    ⇒ **不能**把 Round 2 与 Round 6 当作"只差一位"的严格对照。
>    * **若 Round 6 成功**：只能说明这两位（或其中之一）有效；**要定位到哪一位，必须在同一基线上再做单一位实验**。
>    * **若 Round 6 失败**：只能记为"**`npci=0x3000` 在本配置下不足以解决启动问题**"，
>      **不能**完全排除 PCI 参数的影响。
> 2. **风险是"较低、可回滚"，不是"零风险"。** 修改 PCI 标志**仍可能造成更早的引导失败或显示异常**，
>    **不得预设最坏结果只是"无变化"**。

> **🔥 Round 6 已引导并正式结案 —— 配置生效，内核启动未成功，≥10 分钟无新输出。**
> 日志 [`logs/opencore-2026-10-13-170428.txt`](logs/opencore-2026-10-13-170428.txt)：
> ✅ `MBA:OUT` 含 `npci=0x3000`；✅ `OC: Prelinked status - Success`；
> ✅ MAT 三元组 / `DEVMMIO=1` / 7 条 `MMIO devirt` / 四个 VoodooI2C 仍禁用 / RBAR 段
> 与 Round 4 **逐字相同**；✅ 无 `EB.MM.AKM` / `STOP 0x16` / `No slide values`。
>
> **关键新证据**：与 Round 4 逐行比对（行数都是 **746**，差异 17 行），唯一带机制意义的差异是
> `OC: Not deleting NVRAM … matches add` + `OCVAR: … - ignored, exists`（R4）
> → **`OC: Deleting NVRAM … - Success` + `OCVAR: Setting NVRAM … - Success`**（R6）
> ⇒ **`npci=0x3000` 确实被写进 NVRAM 并进入有效命令行**。
>
> **屏幕侧（操作者补充照片，已独立复核）**：`IMG20261013170545.jpg` 最后两行确认是
> `[ PCI configuration begin ]` + `[IOPCIConfigurator::configure()] PCI configuration PCI0`，
> 上方是 5× `[addMemoryRange()] AppleVTD …` 与 `CoreAnalyticsHub start completed`
> —— **与 Round 4 的屏幕内容逐行一致**；操作者确认在该画面**连续等待 >10 分钟无新输出、未进入 Recovery**。
>
> **⚠️ 措辞约束**：**不得**把最后可见的两行 PCI 日志等同于"已定位的死锁指令"。
> 严格可得的只有：**≥10 分钟没出现 `[ PCI configuration end, … ]` ⇒ `configure()` 没走到 `:3388`**；
> 这不能证明内部死锁（也可能极慢/无限循环），也不能指出停在哪台 PCI 设备
> —— 因为 `:3342` 在 `doConfigure()` 期间**主动关闭 PE 屏幕**。
> 详见 [docs/05](docs/05-受控实验记录.md) §7.17 / §7.18。

> **✅ 已按批准回滚到 Round 4**：卡上 `43ABBAD5…` → **`021F02B3B46953021FF31835518790DD6BEB57074BE822D127305434581815E4`**（52124 B），
> `ocvalidate` → **No issues found**。回滚路径保留：
> `D:\_backup-round0\config.plist.round4-restored` 与 `…\config.plist.round4`。
> **npci 轴到此停止**：`0x2000`（Round 2）与 `0x3000`（Round 6）都**不足以进入 Recovery**。

> **RTX 4050 BAR 专项 + PCI 资源审计见 [docs/08](docs/08-RTX4050-BAR与PCI资源审计.md)。**
> 三条硬结果：
> ① **8 GiB 的 BAR1 在 `0x7C00000000`，不在 `0x7E00000000`**（后者只有 32 MiB 的 BAR3）
> —— 此前"8 GiB BAR 恰好顶到 DSDT 64 位窗口上限"的推论**前提被推翻**；
> ② **`nvidia-smi -q -d MEMORY` 是本机可用、快速、只读的 BAR1 读数仪**，本轮实测
> **BAR1 Total = 8192 MiB**，与 `plan.json` 的 `bar1_bytes = 8589934592` 一致
> （也证明 1401 扫描里的 `"Resizable BAR": "Disabled"` 是**错误读数**）。
> **⚠️ 证据等级限定**：它反映的**只是 Windows 那条路径**（当时 `ResizeGpuBars=-1`，OpenCore 什么都没做），
> **不能**用来证明 **Apple 启动路径**的缩容结果 —— 那是**另一个调用点**（下条）。
> ③ **`New BAR == Old BAR` 只能说明地址寄存器相同，不能证明 BAR size 没变** ——
> OpenCore 从不读回写后的 Control 寄存器，所以"显卡是否真的采用了 64 MiB BAR"**目前仍是 UNKNOWN**。
>
> **🔥 Round 7（已写入卡上，待实机启动）—— 两阶段日志对照**
> ① 本机 OpenCore 的**确切源码已定位**：卡上 `OpenCore.efi` = Dortania build-repo 的
> **`OpenCorePkg-963025f`**（`1401/.../mirror.json:397` 的 pin）—— 上游 **没有 `1.0.9` tag**，
> 必须按 **commit `963025f`** 取源码。
> ② 两个调用点**已在 `963025f` 逐字确认**：
> **阶段 A** `Library/OcMainLib/OpenCoreUefi.c:982-987`（函数 `OcLoadUefiSupport`，**选择界面之前**）
> → `DEBUG("OC: Setting GPU BARs to %d")` + `ResizeGpuBars(…, TRUE, …)`；
> **阶段 B** `Library/OcAfterBootCompatLib/ServiceOverrides.c:1255-1259`
> → `ResizeGpuBars(ResizeAppleGpuBars, FALSE, …)` —— **该处源码没有 `OC: Setting GPU BARs` 这行**。
> ③ 六项严格区分：目标 size **已算出**；Control 写入**已发送但返回状态未被捕获**
> （`:323` 裸调用，无 `Status =`；`SetResizableBarOnDevicePciIo` 末尾**无条件 `return EFI_SUCCESS`**）；
> **写后 BarSize 从不读回**；Apple 阶段读回是本轮要造的观测；macOS 内核实际拿到的资源**不可观测**。
> ⇒ **`Reprogrammed BARs to original - Success` 只证明"地址写回"那次 `Pci.Write` 成功。**
>
> **唯一改动**：`UEFI → Quirks → ResizeGpuBars`：`-1` → **`0`**（**1 行**，1-based 2285；
> `021F02B3…`（52124 B）→ **`58E78A12C8102AF7A5DD3B2D7417BE891B17EFC78FF0817C99F69C6BC7A78CA3`**（52123 B）；
> `ocvalidate` 1.0.9 → **No issues found**；`ResizeAppleGpuBars=0`、`ResizeUsePciRbIo=false`、
> MAT/`DevirtualiseMmio`/`SetupVirtualMap`/`MmioWhitelist`/`boot-args`/SMBIOS **全部未动**）。
> **独立可回退副本**：整棵 `D:\EFI` → `C:\Users\24269\Documents\macos\efi-snapshots\round4-r7-baseline\EFI`。
> **⚠️ 有风险、不是零风险**：阶段 A 在**选择界面绘制之前**执行 ⇒ 可能破坏 GOP framebuffer，
> **导致难以/无法选中目标系统**（与 issue #23 一致）；对固件/Windows/内置盘**无持久影响**。
> ```powershell
> Copy-Item D:\_backup-round0\config.plist.round4-pre-r7 D:\EFI\OC\config.plist -Force      # A 配置回滚
> robocopy C:\Users\24269\Documents\macos\efi-snapshots\round4-r7-baseline\EFI D:\EFI /MIR   # B 整棵 EFI
> ```
> 若选择器损坏/黑屏：**优先用固件启动菜单直接进 Windows**，不盲目按键、不叠加修改，记为「实验无法完成」。
>
> **✅ Round 7 已引导并判读完毕**（日志 [`logs/opencore-2026-10-13-213656.txt`](logs/opencore-2026-10-13-213656.txt)）：
> **两组 RBAR 输出都出现了，位置与预测逐字命中** ——
> 阶段 A：`00:283 OC: Setting GPU BARs to 0`（紧跟 `00:280 OC: AVX enabled - 1` 之后）、
> `Setting RBAR to 0 **inc 1** on 5/43`、`RBAR 2/3 … sizing 0 **inc 1** … **from 13 to 6**`、`New BAR …`、`Reprogrammed … - Success`；
> 阶段 B：`14:884 RBAR using PciIo`（第二次，**无** `Setting GPU BARs`，与源码一致）、
> `Setting RBAR to 0 **inc 0** on 5/43`、**`RBAR 2/3 … sizing 0 inc 0 … from 6 to 6`**。
> 两组的能力掩码组（`0x10`/`0x3FC0`/`0x20`）、`Old BAR` 六 dword、`RBAR control is 460, total 3`
> **逐字相同** ⇒ **确认同属 `01:00.0` 的 RTX 4050**。
>
> **结论**：① **阶段 B 一次写都没做**（`New BAR` 计数 **0**、`Reprogrammed` **0** ⇒ `from 6 to 6` 是**零写入的纯读回**）；
> ② ⇒ **OpenCore 的 RBAR Control 写入确实生效**，`docs/08` §3.3 的二义性解决：
> **"GPU 忽略/锁住写入"被证伪**，`New BAR == Old BAR` 的真实原因是**设备保留了 BAR 内容**；
> ③ **跨轮次推论**：R4/R6 虽无阶段 A，但**阶段 B 自己把 13 写成了 6**（`New BAR`+`Reprogrammed` 为证）
> ⇒ **R2/R4/R5B/R6/R7 的 macOS 全都跑在 64 MiB BAR1 之下** ⇒ **"BAR1 太大"从来不是当时的条件**，
> **整条 BAR 轴对本停点的嫌疑大幅下降**；
> ④ **屏幕仍停在** `[ PCI configuration begin ]` + `[IOPCIConfigurator::configure()] PCI configuration PCI0`
> （照片 `IMG20261013214007.jpg`，与 R4/R6 逐行一致）⇒ **早期 64 MiB 缩容不足以**进入 Recovery，
> **不能排除** macOS 后续重新分配资源；
> ⑤ **GOP 风险本次未触发**（引导正常到达 Apple 路径并跑到 `EXITBS`）—— 只说明"本次未触发"，**不等于无风险**。
>
> **下一轮首选（待批准）= 候选 B**：`Booter → Quirks → ResizeAppleGpuBars: 0 → -1`
> —— 让 macOS **第一次**看到固件的 **8 GiB** BAR1（该条件从未被测过），
> 且它在 **Booter 阶段（选择界面之后）**生效 ⇒ **无选择界面被破坏的风险**。
> 详见 [docs/08](docs/08-RTX4050-BAR与PCI资源审计.md) §9.6 / §F 与 [docs/05](docs/05-受控实验记录.md) §7.20。

> **为什么不是"先加 PCI 日志"**：本轮独立核查了上游 `apple-oss-distributions/IOPCIFamily` 的
> 全部 tag —— `pci_log` / `pci_log_mode` / `pci_log_rc` **只存在于 726.x 系列（macOS 26 时代）**，
> 而 macOS 15.6 时代的 tag（≤ `681.140.3`，2025-08-20）**全都没有**；
> 本项目此前引用的本地源码 **sha256 与 `IOPCIFamily-726.0.5` 逐字节相同**，
> 即被误当成了 15.6 的代码。⇒ 在实机上追加 `pci_log=…` 是**空操作**，该候选**已撤销**。
> 同时确认本机**没有**串口 / `kdp` / 任何"硬卡死后仍能取回内核输出"的通道，
> 唯一可用的采集方式仍是**拍照 + 停留时长**。完整审计见 docs/06 §7。

> **判据修正（2026-10-13 批准时要求）**：
> ① 出现 `EB.MM.AKM`/`STOP 0x16` 等早期错误，**只**说明该设置影响了内存映射或启动兼容性，
> **不能**据此推断固件运行期访问了某块 MMIO，**不能**据此确定 `MmioWhitelist` 地址；
> ② OpenCore DEBUG 日志是早期错误的主要证据来源，**但不保证硬卡死时都能完整写盘** ——
> 缺日志时仍须结合屏幕照片判断。

**本轮只读作业的三条硬结论**（完整证据见 `docs/06`）：

1. **三个 `AE_ALREADY_EXISTS` 已完整闭环**：`\_SB.PCI0.GPP6.WLAN._DSM` 由**DSDT 自己**提供
   （`dsdt.dsl:15556`），固件 SSDT `WLAN` 重复定义它而中止；那次中止留下的
   `\_SB.PCI0.GPP6._S0W`（Method）又让固件 SSDT `GpMsSsdt` 的 `Name (_S0W, Zero)` 撞车；
   本项目注入的 `SSDT-Disable_Network_GPP6` 撞的是同一个 `_DSM`，
   **因此它是"可证明不可能生效"的注入（D6 升级）**。这三张表都**不创建任何设备节点**
   （`Device (` 计数为 0），删不掉任何 PCI 设备。
2. **`SSDT-PLUG-ALT` 与本机固件无命名冲突，但多出 16 个 CPU 对象**：固件自带
   `SSDT:CPUSSDT` 的 `\_SB.PLTF.C000..C00F`（`ACPI0007`），注入表又在 `\_SB` 下加了
   16 个 `Processor (C000..C00F)`。作用域不同 → 无 `AE_ALREADY_EXISTS`；但命名空间里
   有 32 个 `ACPI0007` 节点，说明这个 `-ALT` 版对本机是**冗余**的。
3. **RTX 4050 的 BAR 不能再当"已确立变量"**：`OCDM: RBAR 2/3 … from 13 to 6` 是
   **8 GiB → 64 MiB**（索引 n = 2^n MB），但紧接的 `Old BAR` 与 `New BAR` **六个数完全相同**，
   并打印 `Reprogrammed BARs to original - Success` —— BAR **地址**被恢复成固件原值，
   而**尺寸位不在这六个 dword 里**。所以"macOS 最终看到多大 BAR1"**无法由本机日志判定**；
   Windows 报的 8 GiB 只能算旁证。

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
NVRAM.Delete[7C436110-...]     += boot-args   ← 第一轮：让下面的 boot-args 真正生效
boot-args    ... npci=0x2000
Misc.Security.DmgLoading              = Any          （跳过慢速 DMG 校验）
Booter.Quirks.DevirtualiseMmio        = True         （= 最后一次实测值；曾误设 False，未验证）
Booter.Quirks.SetupVirtualMap         = True
Booter.Quirks.RebuildAppleMemoryMap   = False
Booter.Quirks.EnableWriteUnprotector  = True
Booter.Quirks.SyncRuntimePermissions  = False
Booter.Quirks.ResizeAppleGpuBars      = 0            （安装器专用，N 卡大 BAR 会顶掉固件帧缓冲）
Booter.Quirks.ResizeGpuBars           = 缺省(-1)     （不改 BAR）
Kernel.Quirks.ProvideCurrentCpuInfo   = True
Kernel.Add                            26 个 kext（含注入的 HoRNDIS，见下）
```

`efi/config.plist` 是**与卡上完全一致**的那份配置（只抹除了 SMBIOS 身份字段，见下）。

> ⚠️ 注意 `NVRAM → Delete` 的一个设计行为：当变量**同时在 `Delete` 和 `Add`** 里，
> OpenCore 会比较二者内容，**相同就不删**（打印 `Not deleting NVRAM … matches add`）以保护 Flash 寿命。
> 所以正确的值稳定之后，日志反而会一直显示 `ignored, exists` —— 那是**证明值正确**，不是没生效。

### 安装期的联网（本机特有难点）

无 RJ45 口 + MT7922 无驱动 + RTL8156 型 USB 网卡在 macOS 下无原生支持（它以厂商自定义类 0xFF 枚举，
不是 CDC-ECM）→ 安装器里没网。本项目注入 **HoRNDIS**（`TomHeaven/HoRNDIS` 9.3，x86_64 切片、仅依赖原生 IOKit）
以支持**安卓手机 USB 共享网络**；备选是 RTL8153 芯片的 USB 网卡（macOS 自带 `AppleUSBRealtek8153Patcher`）。

---

## 仓库结构

```
README.md                        本文件
docs/01-可行性评估.md             项目可行性、硬件逐项判定、已知风险
docs/02-安装手册.md               完整操作手册（BIOS/分区/驱动安装/风险对策）
docs/03-引导排错实录.md            ★ 每次引导卡死的证据、根因、解法（含勘误）
docs/04-驱动核对.md               kext 逐个审计（版本/架构/顺序/依赖）
docs/05-受控实验记录.md            ★ 当前在测什么：实验设计、精确 diff、判据、回滚
docs/06-只读分析与Round5候选.md    ★ 只读 ACPI/PCI 分析、上游案例复核、Round 5 候选（只给 diff）
docs/07-上游案例复核与Round6候选.md ★ Round 5B 结案与回滚、Acer 案例复核、IOPCIFamily-681 标志位、1401 版本策略对比、Round 6 候选
docs/08-RTX4050-BAR与PCI资源审计.md  ★ RTX 4050 BAR1 专项（BDF/地址/尺寸/RBAR 解码/读回手段）、PCI root bridge 与 _CRS 审计、Round 7 候选
hardware/本机配置摘要.md           脱敏后的硬件清单
efi/config.plist                 与卡上一致的配置（SMBIOS 身份已抹除）
efi/README.md                    kext 清单与用 1401 重建的方法
logs/opencore-*.txt              8 份真实 OpenCore 引导日志（已脱敏）
logs/bootfix-findings.md         1401 诊断器对这些日志的判定
efi/candidates/                  尚未写入卡上的候选方案（评审用；规则见其 README）
scripts/sanitize-config.py       把卡上配置脱敏后搬进仓库（字节级保真）
scripts/scrub-log.py             清洗引导日志里的身份值（含 UUID 字节序反转形式、磁盘序列号）
scripts/sync-to-github.ps1       ★ 一键同步：双重脱敏 → ocvalidate → 泄漏扫描 → push → 远端复核
scripts/read-screen-photo.py     把手机拍的启动画面裁切放大以读清文字
scripts/patch-stick-config.py    免提权、直接改 U 盘上 config.plist 的小工具
scripts/rewrite-stick-as-admin.cmd  提权重写 U 盘的模板脚本
```

### 每次修改后同步到 GitHub

仓库必须**始终反映卡上真实状态**，否则"仓库配置 ≠ 实测配置"这个坑会再次出现。固定流程：

```powershell
.\scripts\sync-to-github.ps1 -Message "round1: ..."
```

它会依次执行：**脱敏**（把卡上 `D:\EFI\OC\config.plist` 的 4 个身份字段置零后写入 `efi/config.plist`，
其余字节原样保留，所以 diff 只显示真实改动）→ **`ocvalidate`**（版本不符或报错就拒绝发布）→
**泄漏扫描**（从卡上读出**真实**的序列号/MLB/UUID/ROM/MAC，在整仓搜索；同时拒绝 `Report.json`、
`*.aml`、`*.bin`、`>1MB` 的文件）→ **push** → **把远端内容拉回来再扫一遍**。

---

## 隐私说明

公开前已抹除：`config.plist` 里的 SMBIOS `SystemSerialNumber` / `MLB` / `SystemUUID` / `ROM`，
以及引导日志里的同一批值 + 网卡 MAC + 内置 NVMe 磁盘序列号。
原始扫描报告（含网卡 MAC 与磁盘序列号）与 ACPI 转储**未收录**。
`scripts/sanitize-config.py` / `scripts/scrub-log.py` / `scripts/sync-to-github.ps1`
会在发布前自动完成脱敏与扫描，任一身份字段找不到就直接失败退出。

> **一处已修复的泄漏，留档说明**：最初发布的 4 份日志里残留了真实 SMBIOS UUID。
> 两个原因：(1) OpenCore 打印 `system-id` 时把 GUID 前三个字段**字节序反转**，
> 只搜配置里的原字符串会漏掉；(2) 当时的校验命令把
> `Get-ChildItem | Select-String -Quiet` 的整条管道聚合成一个布尔值，误判为"已脱敏"。
> 现已修正，并在同步脚本里加入字节序反转 UUID、GUID 尾段、未脱敏 `NVMe` 路径三类检查。
> **注意：修复只作用于当前分支内容，旧提交历史里仍可追溯。**

**直接使用 `efi/config.plist` 前请换成自己的序列号**（用 1401 重新生成即可），不要照抄示例里的占位值。

## 许可与致谢

本项目自有内容（文档、脚本、配置）以 **MIT** 发布，见 [LICENSE](LICENSE)。
**不包含**任何第三方二进制。第三方组件的归属与许可见 [NOTICE.md](NOTICE.md) ——
特别是 **NullMoth NVIDIA 驱动为 PolyForm Noncommercial 1.0.0（禁止商业使用）**，本项目只链接、不分发。

> 免责：黑苹果违反 Apple 软件许可协议，仅供研究。本仓库的配置会降低系统安全性
> （放宽 SIP、旁路 AMFI、关闭安全启动），请勿用于处理敏感数据的主力机。
