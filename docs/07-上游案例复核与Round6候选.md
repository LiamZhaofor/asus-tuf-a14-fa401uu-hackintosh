# 07 · 上游案例复核与 Round 6 候选

> 本文件对应一次**只读复核 + 候选准备**作业：
> Round 5B 结案 → 回滚 Round 4 → 复核三个上游来源 → 准备 Round 6 单变量候选。
>
> **本轮不写入 U 盘。** Round 6 候选只以文件形式放在 `efi/candidates/`，等批准。
> 卡上现为**已回滚的 Round 4**（`021F02B3…`）。

---

## 0. 证据分级（本文件所有结论都标注等级）

| 等级 | 含义 |
|---|---|
| **① 实机验证** | 本机自己的引导日志 / 照片 / 配置哈希，可直接复核 |
| **② 上游案例** | 别人仓库 / issue 里的事实（引原文），**不能**直接搬到本机 |
| **③ 源码推论** | Apple / OpenCore 源码读出来的机制，**是推论**，不是本机实测 |
| **UNKNOWN** | 文件里查不到 —— 一律标 UNKNOWN，不猜 |

---

## 1. Round 5B 结案

**结论（① 实机验证）**：

> **配置生效、实机未能成功启动、首轮已确认 ≥10 分钟无新屏幕输出。**

* 首轮（`logs/opencore-2026-10-13-143611.txt`）照片最后一行是 `#[EB|LOG:EXITBS:START]`，
  其后**连续等待 >10 分钟**无新屏幕输出，未进入 Recovery。
* 次轮（`logs/opencore-2026-10-13-143926.txt`）**只有 OpenCore 日志，没有照片** ⇒
  **不得**写成"次轮也确认等待了 10 分钟"；只能记为"次轮 OpenCore 阶段与首轮逐行同型，屏幕状态未验证"。
* 记录（①）：**禁用 `DevirtualiseMmio` 后，最后可见输出相比 Round 4 明显前移**
  （Round 4 到过 `[ PCI configuration begin ]`；Round 5B 内核一行未打印），
  **但不能确认具体故障指令或 MMIO 地址**。
* 日志侧三项（①）：`DEVMMIO=0` ✅；5 条 `OCABC: MMIO devirt …` 全部消失 ✅；
  **无** `EB.MM.AKM` / `STOP 0x16` / `No slide values are usable` ✅。
  详细差异清单见 `docs/05` §7.13。

---

## 2. 回滚记录（① 实机验证）

| 步骤 | 结果 |
|---|---|
| 回滚前卡上 SHA-256 核对 | ✅ == `34605D9DA312DC0B5DA3E6F37A5BA3E0CAAABC7659CA3DBC744249DA979C99C4` |
| 备份有效性核对 | ✅ `D:\_backup-round0\config.plist.round4` SHA-256 == `021F02B3…`，且反序列化后 `DevirtualiseMmio=True`、`SetupVirtualMap=True`、MAT 三元组 `False/True/True`、`ResizeAppleGpuBars=0`、`MmioWhitelist=[]` |
| 执行 | `Copy-Item D:\_backup-round0\config.plist.round4 D:\EFI\OC\config.plist -Force` |
| 回滚后 SHA-256 | ✅ == `021F02B3B46953021FF31835518790DD6BEB57074BE822D127305434581815E4`（52124 B） |
| `ocvalidate` 1.0.9 DEBUG（对卡上文件） | ✅ **No issues found**（exit 0） |

**现在卡上 = Round 4。** 未做任何其它 EFI 修改。

---

## 3. Acer 成功案例复核（② 上游案例）

来源：<https://github.com/bruhiamandy/Hackintosh-ANV16-41-R7HU>

### 3.1 时间与内容（②，GitHub API + 原文）

| 项 | 值 |
|---|---|
| 描述 | "EFI file for Acer Nitro V 16 with Ryzen 7 8845HS" |
| **created_at** | **2025-05-08T21:20:51Z** |
| **pushed_at** | **2025-05-08T21:27:24Z**（同一天，之后**再无更新**） |
| README（499 B，全文要点） | **"WHAT WORKS**: It boots most of the times. If it gets stuck, restart your laptop and try again… I understand it hangs because of a USB issue. / Ethernet"；**"WHAT DOESN'T WORK**: **Graphic Acceleration** / Wi-Fi & Bluetooth"；"I did not test it much… Do not expect further updates." |
| `Kernel.Add` | 31 条（30 启用）——**没有任何 NVIDIA 驱动 kext** |
| dGPU 相关 | 无（`DeviceProperties.Add` **完全为空**） |

### 3.2 为什么**不能**当作"NullMoth RTX 4050 驱动成功"的证据（①+②）

1. **时间上不可能**：该仓库 2025-05-08 定稿，而 nullmoth/1401 的 RTX 40 系讨论
   （issue #21/#23/#30/#34）全部发生在 **2025-10 月**。五月不可能有十月的驱动成果。
2. **它自己说显卡加速不工作**：README 明确把 "Graphic Acceleration" 列在 **DOESN'T WORK**。
3. **它里面没有任何 NVIDIA 组件**：31 个 kext 里没有 NullMoth 驱动，`DeviceProperties` 为空。
4. **它连"稳定能引导"都不是**：README 自述 "boots most of the times"，卡住要重启，
   并把原因猜成 USB 问题。
5. 它的 boot-args 里有 `agdpmod=pikera`（Navi dGPU 的 WhateverGreen 参数）与 `-no_compat_check`，
   说明这是一份**给 AMD 显卡场景的模板**，而不是为 RTX 4050 调过的配置。

⇒ **结论**：该仓库只能证明"**同一颗 8845HS 的 Acer 机器，用一份 2025 年 5 月的 AMD-only 模板，
配 `npci=0x3000` 与 `DevirtualiseMmio=False`，能（多数时候）引导到无显卡加速的桌面**"。
**它与本项目的 PCI 初始化卡点没有可用的对照价值**，更**不是**驱动成功案例。

### 3.3 它的配置 vs 本机 Round 4（② vs ①）

| 项 | Acer ANV16-41 | 本机 FA401UU（Round 4） |
|---|---|---|
| CPU | Ryzen 7 8845HS | Ryzen 7 8845H —— **同代同族** |
| boot-args | `-v debug=0x100 keepsyms=1 **npci=0x3000** -no_compat_check agdpmod=pikera` | `-v debug=0x100 keepsyms=1 -vi2c-force-polling nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0`（**无 npci**） |
| `DevirtualiseMmio` | **False** | True |
| `SetupVirtualMap` | True | True |
| `AllowRelocationBlock` | **False** | True |
| `EnableWriteUnprotector` / `RebuildAppleMemoryMap` / `SyncRuntimePermissions` | `False / True / True` | `False / True / True`（**相同**） |
| `ResizeAppleGpuBars` / `UEFI.ResizeGpuBars` | **-1** / -1 | **0** / -1 |
| `DisableVariableWrite` | False | True |
| `ReleaseUsbOwnership` | False | True |
| `MmioWhitelist` | 2 条但**都 `Enabled: False`**（等于空） | `[]`（空） |
| ACPI.Add | SSDT-EC / **HPET** / PLUG-ALT / **PNLF** / USBX / XOSI（**6 张，含 .dsl 源码**） | 7 张：Disable_Network_GPP6 / EC / PLUG-ALT / RMNE / USB-Reset / USBX / XOSI |
| ACPI.Patch | **HPET `_STA→XSTA`、HPET `_CRS→XCRS`、PIC IRQ2、RTC IRQ8、TMR IRQ0**、`_OSI→XOSI`（共 6 条启用） | **只有 `_OSI→XOSI`** |
| `Kernel.Patch` | 25 条 | 27 条（AMD_Vanilla） |
| SMBIOS | `MacBookPro16,3` + **占位身份**（serial `W000…`、MLB `M000…`、UUID 全 0、ROM `11 22 33 44 55 66`） | 真实身份（脱敏后入库） |
| OpenCore 版本 | `OpenCore.efi` 622592 B（与本机 872448 B **不同**，非同一构建） | 1401 内置 OpenCore DBG-109-2026-10-10 |

**ACPI 文件能不能复用？不能（② 实测哈希）**：
`SSDT-PLUG-ALT.aml` 两侧**同为 1096 B**，但 sha256 不同（Acer `77E6EF8C…` / 本机 `2DAE0780…`）。
逐字节比对：**1096 字节里只有 8 个字节不同**，即
`offset 9`（checksum）、`offset 10–15`（OEM ID：Acer `CORP` / 本机 `ZPSS`）、
`offset 32–34`（iasl 版本：`20250425` / `20241212`）。
⇒ **载荷（16 个 `Processor (C000..C00F)`、OemTableId 都是 `CpuPlugA`）逐字节相同。**
`SSDT-EC` / `SSDT-USBX` / `SSDT-XOSI` 同样都是**长度相同、sha 不同**（应属同类差异）。
⇒ 结论：**这些表是同一个模板族的产物，复制它们不带来任何新东西**；
本机缺的是 `SSDT-HPET` / `SSDT-PNLF`，而那属于 §7 明确"不复制"的范围。

### 3.4 用户要求逐项核对的硬件维度 —— **大部分必须标 UNKNOWN**

| 维度 | Acer ANV16-41 | 本机 FA401UU | 能否比较 |
|---|---|---|---|
| PCI root bridge（`_HID`/`_UID`/`_BBN`/`_STA`） | **UNKNOWN** —— 该仓库**不含 DSDT/ACPI 转储**，只有它自己那 6 张 SSDT | ① `dsdt.dsl:2182` `_HID=PNP0A08`、`_CID=PNP0A03`、`_UID=0`、`_BBN=0`、`_STA=0x0F` | ❌ **无法比较** |
| `_CRS`（窗口布局、`NBTP/MBTS`、`NVSV`） | **UNKNOWN** | ① `dsdt.dsl:2427`，32-bit `0xA0000000+0x40000000`，64-bit `MAB=0x460000000…0x7FFFFFFFFF`，第二 32-bit 窗口取决于固件写的 RAM（见 `docs/06` §2.2） | ❌ **无法比较** |
| GPU BAR / 显存 BAR 尺寸 | **UNKNOWN**（只有 `ResizeAppleGpuBars=-1`，**没有**任何 BAR 地址/尺寸数据） | ① 本机从 OpenCore 日志读到 `RBAR 2/3 supports 0x3FC0 … from 13 to 6` 与 `Old BAR` 6 dword（§6） | ❌ **无法比较** |
| Above 4G Decoding | **UNKNOWN**（README 未提，仓库无可读数据） | ① Windows `Win32_PnPAllocatedResource` 显示 dGPU 有 `0x7E00000000`（>4 GiB）⇒ **已开启** | ❌ Acer 侧未知 |
| 显示路由（MUX / iGPU 直连 / dGPU 直连） | **UNKNOWN**。只能从 `DeviceProperties.Add` 为空 + `agdpmod=pikera` 推断"未做 dGPU 路由配置"（③ 推论） | ① 内置屏走 dGPU 直连（MUX），iGPU 用 `disable-gpu` 屏蔽 | ❌ Acer 侧未知 |
| 结果 | 无显卡加速，多数时候能进桌面 | 卡在 `configure()`，进不了 Recovery | — |

> **必须写死的边界**：**凡是无法从文件确认的硬件状态，一律标 UNKNOWN。**
> 本节的对比**只**能说明"两份 EFI 的软件配置不同"，**不能**说明"两台机器的
> PCI 根桥 / `_CRS` / BAR / Above 4G / 显示路由相同或不同"。

---

## 4. IOPCIFamily-681 里 `0x2000` 与 `0x1000` 的含义与关联度（③ 源码推论）

来源：`apple-oss-distributions/IOPCIFamily` tag **`IOPCIFamily-681.140.3`**（2025-08-20，
即本机 macOS 15.6 所属系列）。

```c
// IOPKit/pci/IOPCIConfigurator.h (681.140.3)
kIOPCIConfiguratorTBMSIEnable    = 0x00001000,
kIOPCIConfiguratorPFM64          = 0x00002000,
...
// IOPCIBridge.cpp (681.140.3) 默认值
gIOPCIFlags = 0
            | 0*kIOPCIConfiguratorFPBEnable
            | kIOPCIConfiguratorPFM64            // ← 默认置位
            | kIOPCIConfiguratorCheckTunnel
            | kIOPCIConfiguratorTBMSIEnable      // ← 默认置位
            ...
```

`npci=` 的语义（同文件）：`if (PE_parse_boot_argn("npci", &debug, ...)) gIOPCIFlags &= ~debug;`
（而 `pci=` 是 `|=`）。

⇒ **`npci=0x2000` 只清 `PFM64`；`npci=0x3000` 清 `PFM64 | TBMSIEnable`。
两者的唯一差别就是多清掉 `TBMSIEnable`。**

**`TBMSIEnable` 在本机相关路径上的关联程度：低。** 依据（③）：

* 全部源码里它只被**读**一处：`IOPCIBridge.cpp:5723`
  `if (!(kIOPCIConfiguratorTBMSIEnable & gIOPCIFlags) …)`，紧邻 `nub->getProperty(gIOPCITunnelledKey)`
  —— 即 **Thunderbolt 隧穿设备的 MSI 配置**路径。
* 本机卡住的阶段是 **boot 期的 `IOPCIConfigurator::configure()`**（`doConfigure()` 四遍 `iterate`），
  这时**还没有**任何 Thunderbolt 隧穿设备被建立，`gIOPCITunnelledKey` 相关的分支不参与。
* 而且 ①：Round 2 已经在本**停点**上实测过 `npci=0x2000`（`MBA:OUT` 确实含它），
  结果**没有**进入 Recovery。

**⇒ 评估结论**：`npci=0x3000` 相对 `npci=0x2000` 的**增量只有 `TBMSIEnable`**，
而该位的作用面是 Thunderbolt 隧穿 MSI —— **与本机 `configure()` 卡点的先验关联度低**。
它仍然值得做一次的原因**不是**"可能有效"，而是**消除性价值**（见 §8.4）。

> 另一条必须记住的 ③ 事实：`PFM64` 管的是**地址上限**
> （`if (kIOPCIConfiguratorPFM64 & fFlags) range->maxAddress = 0xFFFFFFFFFFFFFFFFULL;`），
> **不是**"有没有 64-bit 窗口" —— 本机 host bridge 自己就声明了
> `MAB=0x460000000 … MAM=0x7FFFFFFFFF`（见 `docs/06` §2.2）。

---

## 5. 1401 各版本 `p1401/policy.py` 的 AMD 策略对比（② 上游案例）

来源：`raw.githubusercontent.com/nullmoth/1401/<tag>/p1401/policy.py`，四份都逐行读过。

| 规则 | **main（= tag v1.1.0）** | v1.9.0 | v1.10.0 | **v1.14.2**（构建本机卡的那个） |
|---|---|---|---|---|
| `AMD_SVM_ON` / `AMD_DEVMMIO_ON` 集合 | 有（内容同左） | 有 | 有 | 有 |
| `ZEN45_CODENAMES` + `is_zen4_or_later()` | **不存在** | **不存在** | **新增** | 有 |
| 非 zen45 的 AMD：`SetupVirtualMap=False` | ✅ | ✅ | ✅（`not zen45` 守卫） | ✅（同） |
| 非 zen45 的 AMD：`DevirtualiseMmio=False` | ✅ | ✅ | ✅（`not zen45` 守卫） | ✅（同） |
| **zen45：强制 `DevirtualiseMmio=True` + `SetupVirtualMap=True`** | **❌ 无此规则** | **❌ 无** | **✅ 新增** | **✅ 有** |
| **zen45：强制 `DisableVariableWrite=True`**（issue #30） | ❌ | ❌ | ❌ | **✅（v1.14.0 起）** |
| `ResizeAppleGpuBars=0` / `ResizeGpuBars=-1`（installer BAR） | ✅ | ✅ | ✅ | ✅ |
| **`npci` / IOPCIFamily patch** | **从不添加** | 从不 | 从不 | 从不（注释明说 "npci … were never in it, so they are not added here either"） |

**必须写死的三点（用户 item 3 的要求）**：

1. **`main` ≠ "当前默认策略"。** `main` 的 HEAD 就是 **tag `v1.1.0`**，比 v1.14.2 **落后 87 个提交**，
   而且**完全没有** `ZEN45_CODENAMES` / `is_zen4_or_later` / 两条 zen45 强制规则。
   ⇒ 用 `main` 的代码去推断"1401 现在会给这台机器什么"是**错的**；
   判断"卡上这份 EFI 是怎么来的"只能看 **v1.14.2**。
2. **v1.9.0 → v1.10.0 的边界**才是本 CPU 类的关键变化：新增 zen45 判定并**强制**
   `DevirtualiseMmio=True` + `SetupVirtualMap=True`（本机卡上正是这两个 True）。
3. **`policy.py` 里根本没有 `npci`**。1401 的 `npci` 阶梯在 **`bootfix.py`**（读取上一份日志后的修复动作），
   与 `policy.py` 的默认策略是**两套东西**，不能混为一谈。

**与本机实测的关系（①）**：Round 5B 把 `DevirtualiseMmio` 单独改成 `False`
（`SetupVirtualMap` 保持 `True`）后，失败点**前移**到内核零输出
⇒ 这是 **v1.10.0+ 对 zen45 强制两条 quirk 的一个经验性旁证**：
在这台机器上，把 devirt 关掉**不是**改善方向。

---

## 6. 本机 RTX 4050 ReBAR 缩容日志审计（①+③）

### 6.1 日志原文（Round 4 / Round 5B 逐字相同）

```
OCDM: RBAR using PciIo
OCDM: Setting RBAR to 0 inc 0 on 5/43
OCDM: RBAR control is 460, total 3 - Success
OCDM: Old BAR DC000000 0000000C 0000007C 0000000C 0000007E 0000F001 - Success
OCDM: RBAR 1/3 supports 0x10,   sizing 0 inc 0 results setting from 4  to 4
OCDM: RBAR 2/3 supports 0x3FC0, sizing 0 inc 0 results setting from 13 to 6
OCDM: RBAR 3/3 supports 0x20,   sizing 0 inc 0 results setting from 5  to 5
OCDM: New BAR DC000000 0000000C 0000007C 0000000C 0000007E 0000F001 - Success
OCDM: Reprogrammed BARs to original - Success
```

### 6.2 代码含义（③，`Library/OcDeviceMiscLib/SetResizableBar.c`）

| 步骤 | 源码位置 | 含义 |
|---|---|---|
| 读旧 BAR | `:~225-245` | `PciIo->Pci.Read(… OFFSET_OF(PCI_TYPE00, Device.Bar), PCI_MAX_BAR, OldBar)` —— **读 PCI 配置空间 0x10 起的 6 个 dword（BAR0..BAR5）** |
| 算目标 bit | `:~254, 272-297` | 注释："**Bit n is set: supports operating with the BAR sized to (2^n) MB**"；`Size=0`（= `ResizeAppleGpuBars=0`）时取最小支持尺寸 |
| 写尺寸 | `:~322-331` | 写的是 **RBAR control 寄存器**（在 **PCIe 扩展配置空间**里），`ChangedBars = TRUE` |
| 读新 BAR | `:~334-360` | 仅在 `ChangedBars` 时读回同样那 6 个 dword，打印 `New BAR` |
| **写回旧 BAR** | `:~363-378` | 注释："**PCI BARs are reset after resizing, so we must restore them**"，把 `OldBar` 那 6 个 dword 写回 |

### 6.3 `ResizeAppleGpuBars=0` 到底有没有改变 BAR size？

**结论：不能确认它改变了 size；日志里能证实的只有"地址被写回原值"。** 逐条说清：

1. **可以证实（①+③）**：`from 13 to 6` 是**计算出来的目标**（2^13 MB = 8 GiB → 2^6 MB = 64 MiB），
   并且代码确实把该值写进了 RBAR control；随后打印了 `Reprogrammed BARs to original - Success`，
   即**把 6 个 BAR 地址 dword 写回固件原值**。
2. **不能证实（关键）**：**BAR 的"尺寸"不在这 6 个 dword 里**（它在扩展配置空间的 RBAR control 里），
   而**日志从不打印 RBAR control 写后的值**。所以：
   * `Old BAR` 与 `New BAR` **六个 dword 完全相同**，只能说明
     "**写尺寸这一步没有在这 6 个地址寄存器上留下可见变化**"；
   * 按 PCIe 规范，写 `BarSize` 之后该 BAR 的内容是 **undefined**（通常会被复位）。
     这里**没有被复位** ⇒ 两种解释都还活着：
     **(a) 这台 GPU 忽略了/锁住了尺寸写入**，
     **(b) 设备在尺寸变化时保留了 BAR 内容**。
   * **源码与日志都无法在两者之间判别。**
3. **⇒ 所以**：`ResizeAppleGpuBars=0` 在本机的**实际效果是未经证实的**；
   "macOS 最终看到 8 GiB 还是 64 MiB BAR1" **仍然无法回答**。
4. **上游旁证（②，issue #23）**：同一条代码路径下，报告人写了
   `setting from 14 to 13` + `Reprogrammed BARs to original`，他的结论是
   *"the BAR ended up back at 16 GB"*（**注意：这句话与他引用的日志行并不自洽**），
   而他**唯一验证过的解法是"BIOS 关掉 Re-Size BAR"**。
   ⇒ 上游也没有提供"OpenCore 侧真的改小了 BAR"的干净证据。

**对本项目的直接后果**：**不能**把 GPU BAR 当作"已确立的变量"，
**本轮也不批准**任何 BAR / BIOS 修改（用户已明确禁止）。

---

## 7. 本轮明确不做

* ❌ **不复制 Acer 的 `SSDT-HPET` / PIC IRQ2 / RTC IRQ8 / TMR IRQ0 / HPET `_STA`·`_CRS` 补丁**（用户 item 6）。
  理由（①+②）：本机 ACPI 失败清单与 IRQ 冲突无关；Acer 的 IRQ 补丁是为**它的** DSDT 写的；
  而且 §3.3 已证这些 ACPI 文件是"同模板不同标识"，搬过来不带来新信息。
* ❌ **不更换 AMD Vanilla 核心补丁**（保持 27 条不变）。
* ❌ 不改 BIOS / 显卡 BAR / `MmioWhitelist` / Windows EFI / BCD / 内置 SSD 分区。
* ❌ 不重新生成并覆盖整个 EFI（只在卡上**就地**改被批准的那一处）。
* ❌ 本轮**不写入 U 盘**。

---

## 8. Round 6 候选（**只准备，不写入**）

### 8.1 基线

**卡上现为已回滚的 Round 4**：`021F02B3B46953021FF31835518790DD6BEB57074BE822D127305434581815E4`，
52124 B，`ocvalidate` → **No issues found**（本轮实测）。

### 8.2 唯一改动：`NVRAM → Add → 7C436110-…:boot-args` 末尾追加 ` npci=0x3000`

```diff
--- D:\EFI\OC\config.plist        (Round 4 基线, 52124 B, 021F02B3…)
+++ D:\EFI\OC\config.plist        (Round 6 候选, 52136 B, 预测 43ABBAD5…)
@@ -1917,7 +1917,7 @@
 				Rg==
 				</data>
 				<key>boot-args</key>
-				<string>-v debug=0x100 keepsyms=1 -vi2c-force-polling nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0</string>
+				<string>-v debug=0x100 keepsyms=1 -vi2c-force-polling nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0 npci=0x3000</string>
 				<key>csr-active-config</key>
 				<data>
 				QwoAAA==
```

**注入路径说明（①）**：`boot-args` 同时列在 `NVRAM → Delete` 里，所以 `Add` 的内容会被真正写入
（Round 1 已经实测过这个机制：`OC: Deleting NVRAM … - Success` → `OCVAR: Setting NVRAM … - Success`）。
本轮**不新增**任何删除项。

| 项 | 值 |
|---|---|
| 改动行数 | **1 行**（1-based **1920**） |
| 字节变化 | 52124 → **52136** B（+12） |
| 语义差异（`plistlib` 递归全文件） | **恰好** `NVRAM.Add.7C436110-AB2A-4BBB-A880-FE41995C9F82.boot-args` |
| **卡上预测 SHA-256** | **`43ABBAD56F14A70B64ED0297358CDC236B022AE46DE44C2B638DD65C733DBDF3`** |
| 候选文件（脱敏） | `efi/candidates/round6-npci-0x3000.plist` |
| 候选 SHA-256（脱敏） | `5A52E4D1A4B5D38A7BE8608E81AFDC2C5BD62C013A9F0E954A4E807AB1AF0661` |
| `ocvalidate` 1.0.9 DEBUG（对候选文件） | **No issues found**（exit 0） |
| 生成脚本 | `audit/make-round6.py`（断言"只允许这一处变化"，并逐项校验下表不变量） |

**保持不变（脚本逐项断言 PASS，用户指定）**：
`DevirtualiseMmio=True`、`SetupVirtualMap=True`、MAT 三元组 `EnableWriteUnprotector=False /
RebuildAppleMemoryMap=True / SyncRuntimePermissions=True`、`ResizeAppleGpuBars=0`、
`UEFI.ResizeGpuBars=-1`、四个 VoodooI2C 组件仍禁用、`MmioWhitelist=[]`、
`ACPI.Add` 7 条不变、`Kernel.Patch` 27 条**逐条不变**、`Kernel.Add` 26 条不变、
`PlatformInfo`（真实 SMBIOS）不变。

### 8.3 预期观测（预先写死）

| # | 结果 | 证据在哪 | 含义 | 下一步 |
|---|---|---|---|---|
| 1 | 屏幕越过 `[ PCI configuration begin ]`（出现 `[ PCI configuration end, … ]`）或进入 Recovery | 屏幕 + 停留时长 | `PFM64` 之外的 `TBMSIEnable` 竟是变量 —— 与 §4 的先验相反 | **复测一次**确认；再谈后续 |
| 2 | 仍停在同样两行、≥10 分钟无新输出 | 屏幕 + 停留时长 | `npci` 阶梯**到此关闭**：`0x2000` 与 `0x3000` 都不足以进入 Recovery | npci 轴判死，转资源分配假设 |
| 3 | 提前失败 / 行为与 Round 2 或 Round 4 明显不同 | 屏幕 **+ 优先看 `logs/opencore-*.txt`** | 说明 `TBMSIEnable` 在本机某处真的被用到；需先回滚再分析 | 回滚，单独立项 |

**必须同时核对（对照未破）**：
`DEVMMIO=1`、`MmioWhitelist` 空、MAT 三元组不变、四个 VoodooI2C 仍未注入、
`OC: Prelinked status - Success`、`MBA:OUT` 里**确实出现** `npci=0x3000`（这是"本轮改动生效"的直接证据）。

**判据限制（沿用上轮修正）**：
* 屏幕停点相同 **不能**证明 `doConfigure()` 内部停在同一位置；只能说"不足以进入 Recovery"。
* OpenCore 日志是早期错误的**主要**证据来源，但**不保证**硬卡死时完整写盘；缺日志时以照片为准。
* 出现早期错误时，**不能**据此推断固件运行期访问了某块 MMIO，也**不能**据此确定 `MmioWhitelist` 地址。

### 8.4 为什么仍然值得做一次（信息增益，**不是**预期它有效）

1. **它把"npci 无效"从半个结论变成一个闭合结论。** 目前只有 `npci=0x2000` 在**本停点**上被测过
   （Round 2）；而 Dortania 与 1401 的 `bootfix.py` 都会在 `0x2000` 失败后**再试 `0x3000`**。
   不测它，我们就无法诚实地写"npci 这条路走完了"。
2. **零风险的单变量。** 只加 boot-arg，不动 quirk / ACPI / BAR / kext；
   最坏情况（结果 2）与 Round 2/4 完全同型，不会像 Round 5B 那样把失败点**前移**而损失可观测性。
3. **它同时校准一个 ③ 推论。** 若结果 3（行为不同），说明我们对
   `TBMSIEnable` 作用面的判断（"只在 Thunderbolt 隧穿路径"）**有漏**，
   这本身会改变对 `gIOPCIFlags` 的理解。

**风险**：极低。回滚 = 删掉 ` npci=0x3000`（或直接 `Copy-Item` 备份）。

### 8.5 回滚

```powershell
# 写入前先建本轮基线备份
Copy-Item D:\EFI\OC\config.plist D:\_backup-round0\config.plist.round4-restored -Force
# 回滚
Copy-Item D:\_backup-round0\config.plist.round4-restored D:\EFI\OC\config.plist -Force
# 回滚后 SHA-256 必须回到 021F02B3B46953021FF31835518790DD6BEB57074BE822D127305434581815E4
```

写入时的强制校验（与 Round 5B 同一套流程）：基线 SHA == `021F02B3…` → 备份并核验逐字节一致
→ 就地只改那一处 → `ocvalidate` == 0 issues → 读回 SHA == `43ABBAD5…` → 语义差异**只有** boot-args。

---

## 9. 另一候选：`SetupVirtualMap=False` 的评估

**它是否适合作为紧接着的下一组受控对照？——设计上成立，但顺序上应排在 `npci=0x3000` 之后。**

**支持它的理由**：

* ① Dortania 在 `[EB|#LOG:EXITBS:START]` 一节里的顺序是
  **`DevirtualiseMmio` → `SetupVirtualMap` → `EnableWriteUnprotector`**；
  第三条已在 Round 3/4 覆盖，第一条刚在 Round 5B 覆盖，**剩下没动过的就是它**。
* ① 记忆-映射的 2×2 已经有两格：`(devirt=ON, SVM=ON)` = Round 4（停在 `PCI configuration begin`）、
  `(devirt=OFF, SVM=ON)` = Round 5B（内核零输出，**更早**）。
  做 `(devirt=ON, SVM=OFF)` 就能把这一轴补齐三格。
* ① 本机是 **UEFI**、且 `ProvideCustomSlide=True`、`AllowRelocationBlock=True`，
  `SetupVirtualMap` 与 `RebuildAppleMemoryMap` 是同一套运行期映射机制的两半，
  本机确实"用得到"它（Round 5B 已证明内存图这一轴**能动**结果）。

**反对现在就做的理由**：

* **方向已经指向"不是内存映射"**：Round 5B 把 devirt 关掉的后果是**变差**（失败前移）。
  这暗示本机的瓶颈**不在**"运行期映射的可用性"，而在
  `configure()` 内部的资源/BAR 分配。把 SVM 也关掉，先验上更可能是**又一次变差**，
  而不是变好。
* **失败模式不友好**：`SetupVirtualMap=False` 一旦破坏运行期映射，可能表现为
  更早失败或运行期服务异常（本机依赖 `DisableVariableWrite=True` 来避免 NVRAM 写入问题），
  也就是说**可能损失可观测性**（与 Round 5B 同样的代价）。
* 而 `npci=0x3000` 是**零风险**且能**闭合**一条推理链 —— 在只有一次引导机会的预算下，
  先做闭合、再做探索更划算。
* 2×2 也不完整：要做"补齐"至少还要 `(devirt=OFF, SVM=OFF)`，那一格与 Acer 的
  `(OFF, ON)` 无关，价值主要在于**归因**，而不是**解决问题**。

**⇒ 结论**：`SetupVirtualMap=False` **是一个合法且必要的后续对照，但不是本轮的首选**。
若 `npci=0x3000` 给出结果 2（无变化），它的优先级会上升到第一位，
因为那时"npci 轴已闭合、内存图轴还差一格"就是唯一剩下的干净实验空间。

---

## 10. 最终推荐

> **推荐：Round 6 = 仅向 boot-args 追加 `npci=0x3000`（候选文件
> `efi/candidates/round6-npci-0x3000.plist`，卡上预测 SHA-256 `43ABBAD5…`）。**

**为什么是它，而不是别的**：

| 对比项 | `npci=0x3000`（推荐） | `SetupVirtualMap=False` | 禁用 `SSDT-PLUG-ALT` | 禁用 `SSDT-Disable_Network_GPP6` |
|---|---|---|---|---|
| 改动面 | 1 个 boot-arg 词 | 1 个布尔 | 1 个布尔 | 1 个布尔 |
| 风险 | **最低**（最坏=无变化） | 中（可能像 R5B 一样前移失败点） | 低–中（丢 `plugin-type`） | 极低 |
| **预期信息增益** | **高（闭合 npci 阶梯 + 校准 `TBMSIEnable` 的 ③ 推论）** | 中（补齐 2×2 一格，但方向已指向"不是内存图"） | 低（① §3.3 已证模板与 Acer 相同、Acer 能引导；② 无证据表明冗余=有害） | 极低（① 那张表**从不生效**，只影响 ACPI 失败计数 3→2，而该计数在停到 PCI 的引导里**拍不到**） |
| 是否新增待测轴 | 否（关闭已有轴） | 是 | 是 | 否 |

**一句话**：Round 5B 已经把"内存图"这一轴指向**变差**的方向，所以下一步不该继续在同一轴上试错，
而应当**用最低成本把唯一还没走完的 boot-arg 轴（`npci`）走完**，
从而把结论从"`npci=0x2000` 不足"升级为"**整条 `npci` 阶梯都不足以进入 Recovery**"。
这条结论一旦成立，就把剩下的怀疑范围**干净地**压到
"`configure()` 内部的资源/BAR 分配"上 —— 而那是目前唯一还没有被任何实验触碰过的区域。

**状态：只准备候选，未写入 U 盘；等批准。**
