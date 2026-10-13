# 08 · RTX 4050 BAR 专项与 PCI 资源审计（Round 7 候选）

> 本文件对应一次**只读**作业：Round 6 结案 → 回滚 Round 4 → RTX 4050 BAR1 专项 →
> PCI root bridge / ACPI `_CRS` 审计 → Round 7 候选排序。
>
> **本轮未写入 U 盘、未改任何 EFI。** 卡上现为**已回滚的 Round 4**（`021F02B3…`）。
> 所有 Windows 侧读数都是**只读**查询；**没有写任何 PCI 配置寄存器**。

---

## 0. 证据分级

| 等级 | 含义 |
|---|---|
| **①** | 本机实测：OpenCore 日志 / 屏幕照片 / **本机 Windows 只读查询** / 配置哈希 |
| **②** | 上游文件：1401 扫描产物 `plan.json`、Apple/OpenCore 源码、1401 policy（引用原文） |
| **③** | 源码推论 |
| **UNKNOWN** | 文件与读数都回答不了 —— 一律标 UNKNOWN，不猜 |

---

## 1. Round 6 正式结案

> **Round 6：配置生效，内核启动未成功，≥10 分钟无新输出。**

* **① 屏幕证据（本轮独立复核）**：`IMG20261013170545.jpg`（17:05:45，即 `EXITBS:START`
  17:04:40 之后约 65 秒）最后可见两行为
  ```text
  [ PCI configuration begin ]
  [IOPCIConfigurator::configure()] PCI configuration PCI0
  ```
  其上方依次是 5× `[addMemoryRange()] AppleVTD is not yet installed as gSystem`、
  `CoreAnalyticsHub start completed` —— **与 Round 4 的屏幕内容逐行一致**。
* **① 停留时长**：操作者确认在该画面**连续等待 >10 分钟无新屏幕输出、未进入 Recovery**。
* **① 日志侧**：`MBA:OUT` 含 `npci=0x3000`；`Prelinked status - Success`；
  MAT / `DEVMMIO=1` / VoodooI2C / RBAR 段与 Round 4 逐字一致；无早期内存映射错误。
  详见 `docs/05` §7.17 / §7.18。
* **⚠️ 措辞约束（必须遵守）**：**不得**把"最后可见的两行 PCI 日志"直接等同于
  "已经定位到的死锁指令"。严格可得的结论只有：
  **≥10 分钟没有出现 `[ PCI configuration end, … ]` ⇒ `configure()` 没有走到 `IOPCIConfigurator.cpp:3388`**。
  这**不能**证明内部死锁（也可能是极慢或无限循环），也**不能**指出停在哪台 PCI 设备 ——
  因为 `:3342` 在 `doConfigure()` 期间**主动关闭 PE 屏幕**（`docs/06` §1.4、`docs/06` §7）。

**回滚记录见 `docs/05` §7.18。**

---

## 2. RTX 4050 的 PCI 标识与 BAR 布局（用户问题 1）

### 2.1 标识（① / ②）

| 项 | 值 | 来源 |
|---|---|---|
| 名称 | NVIDIA GeForce RTX 4050 Laptop GPU | ② `plan.json` `capture.gpus[0]` |
| 设备 ID | `10DE:28E1`，Subsystem `1E43:1043`，Rev `A1` | ② 同上 |
| **BDF** | **总线 1、设备 0、功能 0 → `01:00.0`** | ② `location: "PCI 总线 1、设备 0、功能 0"` |
| PCI 路径 | `PciRoot(0x0)/Pci(0x1,0x1)/Pci(0x0,0x0)` | ② 同上 + ① 本机 `DeviceProperties` 用同一路径 |
| **ACPI 路径** | **`\_SB.PCI0.GPP0.PEGP`** | ② `acpi_path`（本轮已用 DSDT/SSDT 独立核对，见 §6） |
| 驱动 | NVIDIA `32.0.16.1714`，`started: true, problem: 0` | ② |

### 2.2 已分配资源（② `plan.json` 资源记录 `r29`，1401 扫描时的 Windows PnP 快照）

| 资源 | 范围 | 长度 | flags | 对应 |
|---|---|---|---|---|
| `memory` | `0xDC000000 – 0xDCFFFFFF` | **16 MiB** (16777216) | `0x83` | **BAR0**（MMIO 寄存器窗） |
| `type 32769` | — | — | — | 1401 未解码的描述符（占位） |
| `memory_large` | **`0x7C00000000 – 0x7DFFFFFFFF`** | **8 GiB** (8589934592) | `0x87` | **BAR1**（VRAM，64-bit 预取） |
| `type 32769` | — | — | — | 同上 |
| `memory` | `0x7E00000000 – 0x7E01FFFFFF` | **32 MiB** (33554432) | `0x87` | **BAR3** |
| `type 32769` | — | — | — | 同上 |
| `io` | `0xF000 – 0xF07F` | 128 B | `0x131` | **BAR5** |

**① 独立交叉验证**：OpenCore 日志的 6 个原始 BAR dword 是
`DC000000 0000000C 0000007C 0000000C 0000007E 0000F001`。逐字段解码：

| 寄存器 | 值 | 读数 |
|---|---|---|
| BAR0 | `0xDC000000` | 32-bit 内存 BAR @ `0xDC000000` ✓ 与上表一致 |
| BAR1 | `0x0000000C` | 低位 dword：bit2(64-bit)+bit3(prefetchable) 置位，地址低 32 位 = 0 |
| BAR2 | `0x0000007C` | 高位 dword = `0x7C` ⇒ **BAR1/2 = 64-bit BAR @ `0x7C00000000`** ✓ |
| BAR3 | `0x0000000C` | 另一个 64-bit 可预取 BAR 的低位 dword |
| BAR4 | `0x0000007E` | 高位 dword = `0x7E` ⇒ **BAR3/4 = 64-bit BAR @ `0x7E00000000`** ✓ |
| BAR5 | `0x0000F001` | bit0=1 ⇒ I/O BAR @ `0xF000` ✓ |

⇒ **两条独立来源完全一致。**

### 2.3 ⚠️ 本轮勘误：8 GiB 的 BAR 在 `0x7C00000000`，**不在** `0x7E00000000`

此前（`docs/06` §2.6 与本项目若干处）把 `0x7E00000000` 当成 8 GiB 的 BAR1 起点，
并据此推论"`0x7E00000000 + 8 GiB = 0x8000000000` 恰好顶到 DSDT 的 64 位窗口上限"。
**这是误读**：`0x7E00000000` 处只有一个 **32 MiB** 的 BAR3；
**8 GiB 的 BAR1 在 `0x7C00000000–0x7DFFFFFFFF`**。
影响见 §5（用户问题 5 的结论因此被推翻）。

### 2.4 Resizable BAR Capability / Control 结构（① 日志 + ③ 源码）

① OpenCore 日志（Round 4 / Round 6 逐字相同）：

```
OCDM: RBAR control is 460, total 3 - Success
OCDM: RBAR 1/3 supports 0x10,   sizing 0 inc 0 results setting from 4  to 4
OCDM: RBAR 2/3 supports 0x3FC0, sizing 0 inc 0 results setting from 13 to 6
OCDM: RBAR 3/3 supports 0x20,   sizing 0 inc 0 results setting from 5  to 5
```

② 语义（`SetResizableBar.c:249-254` 注释：**"Bit n is set: supports operating with the BAR
sized to (2^n) MB"**；OpenCore `Configuration.tex:9312`：**"Use `0` for 1 MB, `1` for 2 MB,
`2` for 4 MB, and so on up to `19` for 512 GB"**）。据此逐条解码：

| OpenCore 条目 | Capability 掩码 | 支持的最小尺寸 | 当前 → 目标 | 对应真实 BAR | 与 §2.2 是否一致 |
|---|---|---|---|---|---|
| `RBAR 1/3` | `0x10`（bit4） | 2⁴ MB = **16 MiB** | `4 → 4`（不变） | **BAR0** = 16 MiB | ✓ |
| `RBAR 2/3` | `0x3FC0`（bit6–13） | 2⁶ MB = **64 MiB** | **`13 → 6`（8 GiB → 64 MiB）** | **BAR1** = 8 GiB | ✓ |
| `RBAR 3/3` | `0x20`（bit5） | 2⁵ MB = **32 MiB** | `5 → 5`（不变） | **BAR3** = 32 MiB | ✓ |

* `RBAR control is 460`：该 dword 是**第一个** resizable BAR 的 Control 寄存器原值。
  按 PCIe 规范 Control 的 **BarSize 字段在 bit 13:8**，`0x460 = 0b100_0110_0000` →
  bit10 置位、bit8/9/11/12/13 为 0 ⇒ **BarSize = 0b000100 = 4** ⇒ 2⁴ MB = **16 MiB**，
  正是 BAR0 的当前尺寸 ✓。（`total 3` = 该设备有 3 个可调 BAR。）
* ② 源码里 Capability/Control 的寄存器**偏移**由扩展能力链表决定（`ResizableBarOffset`），
  **本机日志没有打印该偏移**，所以**无法从现有产物得到 RBAR 扩展能力的 config-space 地址**。
  这是 UNKNOWN（要拿到它必须读 config space，见 §3.2）。

### 2.5 ① 本机 Windows 的**实时只读**读数（本轮新增，零成本）

```powershell
nvidia-smi -q -d MEMORY
```
```
FB Memory Usage
 Total : 6141 MiB          <- 显存 6 GB
BAR1 Memory Usage
 Total : 8192 MiB          <- BAR1 视窗 = 8 GiB
 Used  : 8163 MiB
 Free  : 29 MiB
```

* 这与 ② `plan.json` 的 `bar1_bytes = {status: measured, source: nvml:nvmlDeviceGetBAR1MemoryInfo,
  value: 8589934592}` **完全一致**。
* ⇒ **`nvidia-smi -q -d MEMORY` 是本机可用的、快速的、只读的 BAR1 尺寸读数仪**
  （不需要额外硬件、不需要重启、不写任何寄存器）。这是本轮最有用的工具发现。

> **⚠️ 证据等级限定（用户 2026-10-13 要求，必须遵守）**
>
> 这条读数的**证明力仅限 Windows 启动路径**：
> * 它反映的是 **Windows 这次启动**时 GPU 的 BAR1 状态，
>   即"**固件 POST 分配的结果**"（因为 Windows 路径上 OpenCore 的
>   `UEFI.Quirks.ResizeGpuBars` 当时是 `-1`，**什么都没做**）。
> * 它**不能**用来证明 **Apple 启动路径**上的缩容结果 —— 那是由**另一个调用**
>   （`ServiceOverrides.c` 的 `ResizeAppleGpuBars`，**只对 Apple OS 生效**、发生在**不同阶段**）做的，
>   两者是**两个不同的调用点**，不能互相代替（见 §9.1）。
> * ⇒ **不得**用"Windows 下 BAR1 = 8192 MiB"去论证"OpenCore 在 Apple 路径上的缩容成功/失败"。
>   它只能作为**固件基线**与**读数仪可用性**的证据（等级 ①，但**仅限该路径**）。

### 2.6 ⚠️ ② 1401 扫描的 `"Resizable BAR": "Disabled"` **不可信**

`plan.json` 的 `hardware.GPU[0]` 写：
```json
"Resizable BAR": "Disabled"
```
但**同一份文件**的测量区却写 `bar1_bytes = 8589934592`（8 GiB = 已启用 ReBAR 的典型值），
且 ① 本机 `nvidia-smi` 现在就读到 **8192 MiB**。
⇒ **`plan.json` 自相矛盾**；`Resizable BAR: Disabled` 是**错误读数**
（1401 读的是并不存在的注册表键 `KMD_RebarControlMode`）。**任何基于该字段的推理都必须作废。**

---

## 3. OpenCore 改 RBAR Control 的实际流程与"能否读回"（用户问题 2、3、4）

### 3.1 流程（③ `Library/OcDeviceMiscLib/SetResizableBar.c`）

| 步 | 位置 | 做了什么 |
|---|---|---|
| 1 | `:~155-183` `SetResizableBarOnDevicePciIo` | 打开设备的 PciIo；② 本机日志 `OCDM: RBAR using PciIo` 说明走的是 **PciIo** 路径（与 `ResizeUsePciRbIo=False` 一致） |
| 2 | `:~200` | 读 RBAR 扩展能力的 header，打印 `RBAR control is %X, total %u` |
| 3 | `:~225-245` | **读 6 个 BAR 地址 dword**（config offset 0x10 起，`PCI_MAX_BAR`）→ `OldBar` |
| 4 | `:~272-297` | 由 Capability 掩码 + `Size`（= `ResizeAppleGpuBars`）算目标 bit；`Size=0` 时取最小支持尺寸 |
| 5 | `:~322-331` | **写 RBAR Control 的 BarSize 字段**（扩展配置空间）；置 `ChangedBars=TRUE` |
| 6 | `:~334-360` | **只读回那 6 个 BAR 地址 dword** → `NewBar`（DEBUG） |
| 7 | `:~363-378` | 把 `OldBar` **写回**那 6 个地址 dword（注释：写 BarSize 后 BAR 内容 undefined，规范要求重编程） |

### 3.2 **要读回"当前 BAR size"，只有三个渠道**

| 渠道 | 能读到什么 | 可信度 | 备注 |
|---|---|---|---|
| **(a) OpenCore 自身** | `from N`（写**之前**的 BarSize） | ① 已证 | **当前构建从不读回写后的 Control** ⇒ 拿不到"写后值" |
| **(b) 操作系统侧（Windows）** | BAR 视窗长度（由 BarSize 决定）；`nvidia-smi` 的 `BAR1 Total` | ① 已证可用 | **混淆**：Windows 自己的 PCI 仲裁器与 NVIDIA 驱动**可能重编程/重设 ReBAR**，不一定保留 OpenCore 留下的值 |
| **(c) Linux Live，只读 dump config space** | **`lspci -xxxx -s 01:00.0`** 直接给出 Resizable BAR 扩展能力（ID 0x15）的 Capability/Control 原始 dword ⇒ 可**精确**解出当前 BarSize 索引 | ②/③，未在本机验证 | **不写任何寄存器**；Linux 默认不重设 ReBAR（无 GPU 驱动时更不会）⇒ 混淆最小。**但要观察 OpenCore 的写入，必须经由 OpenCore 引导 Linux**，否则读到的是固件基线 |

**关键的 ③ 结论**：RBAR Control 的 BarSize 字段是**持久**的，只有"谁最后写了它"能改变它。
因此**要么有一个能读 config space 的观察者 OS（且它不自己重设），要么改 OpenCore 让它自己读回**。
本项目**不需要**改 OpenCore —— 观察者可以换。

### 3.3 `New BAR == Old BAR` 的**严格**含义（用户问题 3）

**只能得到这一条**：写 BarSize **之前与之后**，那 6 个 **BAR 地址寄存器**的值**完全相同**。

**不能**由它得到"BAR size 没变"。理由：
* **BAR 的 size 不在这 6 个 dword 里** —— 它在**扩展配置空间**的 RBAR Control 里
  （`SetResizableBar.c` 从不读回该字段，日志也从不打印它）。
* 按 PCIe 规范，写 BarSize 后"the contents of the corresponding BAR are undefined"（通常被复位）。
  这里**没有复位**，于是有两种都还活着的解释：
  **(a)** 该 GPU **忽略/锁住**了尺寸写入（⇒ `ResizeAppleGpuBars=0` 是空操作）；
  **(b)** 该 GPU 在尺寸变化时**保留了 BAR 内容**（⇒ 写入生效，地址被 OpenCore 正确还原）。
* **源码与日志都无法在 (a)/(b) 之间判别。** 这正是用户问题 2 需要"读回方式"的原因。

### 3.4 用户问题 4：**不需要改 OpenCore 二进制；仅增加诊断读回的方案**

**方案 A-1（推荐，零写入、零 OC 改动）**：**换观察者 OS，而不是改 OpenCore。**
1. 让 OpenCore 的 **`UEFI → Quirks → ResizeGpuBars`** 从 `-1` 改成 `0`
   （② `Configuration.tex:9304-9313`：值 n ⇒ 2^n MB，`0` ⇒ 最小支持尺寸；
   `:9350` Note 1 说明它与 `ResizeAppleGpuBars` **互补**，**没有**"两者不能同时非 −1"的限制；
   `:9353` Note 2 说明**增大** BAR 会重叠，而**缩小**不需要搬移地址）。
2. 经由 **OpenCore 选择界面引导 Windows**（`ResizeGpuBars` 对**所有** OS 生效）。
3. 在 Windows 里跑**只读**读数：`nvidia-smi -q -d MEMORY`（BAR1 Total）+ 1401 扫描 / CIM 资源查询。
4. **若 BAR1 Total 变成 64 MiB** ⇒ OpenCore 的尺寸写入**确实生效**（解释 (b)）；
   **若仍是 8192 MiB** ⇒ 要么写入无效 (a)，要么被 Windows 重设 —— 用方案 A-2 判别。

**方案 A-2（判别 (a)/(b) 的最终手段，仍需零写入）**：用 **Linux Live（或现有 Live 环境）**，
经 OpenCore 引导后执行**只读**命令：
```bash
lspci -Dnnvv            # 人类可读，含 Resizable BAR 能力与当前尺寸
lspci -xxxx -s 01:00.0  # 全 config space 十六进制 dump（纯读）
cat /proc/iomem         # BAR/桥窗口的内存映射视图（纯读）
```
**禁止**任何 `setpci` 写操作。⇒ 从 dump 里直接解出 Resizable Bar 扩展能力（ID `0x15`）的
Capability/Control，得到**当前 BarSize 索引**，从而**无歧义**地判定 (a)/(b)。

**方案 A-3（不推荐，仅按要求评估风险）**：改 OpenCore 源码
（在 `SetResizableBar.c` 的两处写入之后各加一条 `DEBUG` 打印 Control 值），重新编译 `OpenCore.efi`
并替换卡上的二进制。
**风险评估**：① 需要 EDK2 + 工具链在 Windows 上重建，**产出必须与 1401 内置的
`DBG-109-2026-10-10` 构建兼容**（否则 `ocvalidate` 与行为都可能不符）；
② 替换 `OpenCore.efi` 属于**核心引导组件替换**，失败会**直接无法引导**；
③ 收益（一条 DEBUG 行）远小于风险。⇒ **不实施**（与用户要求一致）。

---

## 4. ⚠️ DSDT 的 64 位窗口与地址 `0x7E00000000`（用户问题 5）—— **前提被推翻**

* ② DSDT `\_SB.PCI0`（`dsdt.dsl:2249-2251`）：
  `Name (MAB, 0x0000000460000000)`、`MAL = 0x7BA0000000`、**`Name (MAM, 0x0000007FFFFFFFFF)`**
  ⇒ 64 位窗口 = **`0x460000000 – 0x7FFFFFFFFF`**（上界 `0x7FFFFFFFFF`，即 512 GiB − 1）。
* ① 实测 64 位分配（§2.2、§6）：
  * dGPU BAR1 8 GiB @ `0x7C00000000` → 结束于 `0x7E00000000`
  * dGPU BAR3 32 MiB @ `0x7E00000000` → 结束于 `0x7E02000000`
  * iGPU 256 MiB @ `0x7E10000000` → 结束于 `0x7E20000000`
  * GPP0 桥窗口 `0x7C00000000 – 0x7E01FFFFFF`；GP17 桥窗口上界 `0x7E207FFFFF`
* ⇒ **使用的最高地址 ≈ `0x7E207FFFFF`，距 DSDT 上界 `0x7FFFFFFFFF` 还有约 1.5 GiB 之上的巨大余量**
  （实际余量 `0x7FFFFFFFFF − 0x7E207FFFFF ≈ 0x1DF800000` ≈ 7.5 GiB… 精确值 `0x1DF800000` = 8,045,101,056 B ≈ 7.49 GiB）。

**结论（必须写死）**：
1. **`0x7E00000000 + 8 GiB = 0x8000000000 = MAM + 1` 这个"恰好顶到上限"的关系，
   是建立在 §2.3 那个误读之上的 —— 前提不成立。** 真实的 8 GiB BAR 在 `0x7C00000000`，
   它自身结束于 `0x7E00000000`，**完全落在 DSDT 窗口内**。
2. 因此**不存在**"8 GiB BAR 恰好越过 DSDT 64 位窗口上限"这一边界问题。
3. 仍成立的一条结构性事实：**GPP0 的 64 位桥窗口结束于 `0x7E01FFFFFF`，而 iGPU 的 256 MiB
   从 `0x7E10000000` 开始 —— 中间有 `0xE000000` ≈ 14 MiB 的空隙**，两者**不重叠** ✓。

---

## 5. 严格区分三个层次（用户问题 6）

| 层次 | 内容 | 本机已知值 | 证据来源 |
|---|---|---|---|
| **(1) Windows/UEFI 固件原始分配** | 固件在 POST 时分配的 BAR 地址与尺寸 | BAR0 16 MiB @0xDC000000；**BAR1 8 GiB @0x7C00000000**；BAR3 32 MiB @0x7E00000000；BAR5 IO 128 B @0xF000 | ② `plan.json` r29；① OpenCore 的 `Old BAR` 6 dword；① `nvidia-smi` BAR1 = 8192 MiB |
| **(2) OpenCore 修改后的结果** | `ResizeAppleGpuBars=0` 把 BAR1 的 **BarSize 字段**从 13 改为 6；随后**把地址 dword 写回原值** | **尺寸字段的最终值：UNKNOWN**（无法读回，§3.2/§3.3）；地址：已还原为 (1) | ① 日志 `RBAR 2/3 … from 13 to 6` + `New BAR == Old BAR` + `Reprogrammed BARs to original - Success`；③ 源码 |
| **(3) macOS IOPCIFamily 实际枚举的资源** | macOS `configure()` 看到的 BAR/桥窗口 | **UNKNOWN** —— 没有任何可取的 macOS 侧读数（`pci_log*` 在 15.6 不存在、无串口/kdp、硬卡死无持久化；见 `docs/06` §7） | —— |

> **三层不能混同。** 特别是：**不能**用 (1) 的 8 GiB 去断言 (3) 也是 8 GiB，
> 也**不能**用 OpenCore 日志的 `from 13 to 6` 去断言 (2)/(3) 真的变成了 64 MiB。

---

## 6. PCI root bridge 与 ACPI `_CRS` 审计（第四阶段）

### 6.1 dGPU 的 ACPI 层级（① DSDT + 固件 SSDT 逐行核对）

```
\_SB.PCI0                      dsdt.dsl:2182   _HID PNP0A08 / _CID PNP0A03 / _UID 0 / _BBN 0 / _STA 0x0F
└── Device (GPP0)              dsdt.dsl:2778   Name (_ADR, 0x00010001)  → 总线0 设备1 功能1
    │                                          仅 _PRW / _PRT / 子设备 D008(_ADR 0xFF)；**无 _CRS、无 _DSM**
    └── Device (PEGP)          **不在 DSDT 里**；由固件 SSDT **`OemNv2`** 定义：
                               ssdt3_OemNv2T_.dsl:320 `Scope (\_SB.PCI0.GPP0)` → `:341 Device (PEGP)`
                               `:343 Name (_ADR, Zero)`（⇒ 总线1 设备0 功能0）、`:344 _STA`、`:422 _DSM`、`:1298 _ROM`
```

* ① 交叉验证：② `plan.json` 的 `acpi_path = "\\_SB.PCI0.GPP0.PEGP"` 与 `pci_path`
  `Pci(0x1,0x1)/Pci(0x0,0x0)` **完全对得上**。
* **`GPP0` 与 `PEGP` 在全部 44 张固件表里都没有 `_CRS`**（本轮已 grep 确认：
  44 张表共有 90 处 `_CRS` 声明，但没有一处属于 `GPP0`/`PEGP`）。
  ⇒ **dGPU 路径上的资源窗口在 ACPI 里根本没有描述**，只能从 **PCI config space** 读。
  这是一个重要的方法学结论：**用 ACPI 反编译去审计 dGPU 的窗口是做不到的**。
* iGPU 路径：`\_SB.PCI0.GP17.VGA_`（`dsdt.dsl:3002-3017`），**同样没有 `_CRS`**
  （`docs/06` §2.5 已证）。

### 6.2 父桥的资源窗口（② `plan.json` 资源记录）

| 桥 | 设备 | 32-bit 窗口 | 64-bit / 预取窗口 |
|---|---|---|---|
| `GPP0`（dGPU 父桥） | `1022:14ED` @ 0/1/1 | `0xDC000000 – 0xDD0FFFFF`（17 MiB） | **`0x7C00000000 – 0x7E01FFFFFF`**（8 GiB + 32 MiB） |
| `GP17`（iGPU 父桥） | — | `0xDD200000 – 0xDD7FFFFF`（6 MiB） | `0x7E10000000 – 0x7E207FFFFF`（256 MiB + 512 KiB） |

* GPP0 的 64 位窗口 = **dGPU BAR1（8 GiB）+ BAR3（32 MiB）** 的并集，**紧密贴合、无空隙** ✓
  ⇒ 说明固件是**按 BAR 实际尺寸**生成父桥窗口的，`ReBAR=ON` 时固件**确实**把 BAR1 放到了 8 GiB。
* 32-bit 窗口 17 MiB = BAR0 的 16 MiB + 1 MiB 对齐余量 ✓
* `GPP0` 与 `GP17` 的 32-bit 窗口 **不重叠**（`0xDD0FFFFF < 0xDD200000`）✓

### 6.3 ACPI 侧声明的窗口（① DSDT）

| 资源 | 范围 | 依据 |
|---|---|---|
| Bus | `0x00 – 0x7F` | `_CRS` `CRS1` |
| I/O | `0x0000–0x03AF`、`0x03E0–0x0CF7`、`0x0D00–0x0FFF` + `CF8/CFC` | 同上 |
| 32-bit MEM | **`0xA0000000 – 0xDFFFFFFF`**（1 GiB，`MBB`/`MBL`） | `:2247-2248`、`:2539-2545` |
| 32-bit MEM #2 | `MIN7/MAX7/LEN7`：**静态路径下为 0**；实际值取决于 `NRSV` RAM（`RSTE/RSB0..3/RSS0..3` @ 物理 `0x96931000`） | `:2480-2485`、`:2492-2531`、`:2536-2545`；详见 `docs/06` §2.2 |
| 64-bit MEM | **`0x460000000 – 0x7FFFFFFFFF`** | `:2249-2251`、`:2571-2579` |

**静态 DSDT 与动态 `_CRS` 的区分（用户要求）**：
`_CRS`（`:2427`）依赖 `OperationRegion (NRSV, SystemMemory, NRSV, 0x1000)`（`NRSB = 0x96931000`，
`:2252`）读取固件写入的 RAM；`RSTE/RSB1/RSS1` 等是**运行期 RAM 状态**。
⇒ **ACPI 反编译只能告诉我们"可能报什么"，不能告诉我们"这次报告了什么"。**
本轮**没有**任何 macOS 侧 `_CRS` 实测值（原因见 §5 第 (3) 层）。

### 6.4 对齐 / 边界 / 重叠核查（① + ②）

| 检查 | 结果 |
|---|---|
| dGPU BAR0 `0xDC000000` 是否落在 ACPI 32-bit 窗口内 | ✅ 在 `0xA0000000–0xDFFFFFFF` 内 |
| iGPU 32-bit BARs `0xDD200000`/`0xDD700000` | ✅ 在窗口内 |
| dGPU/iGPU 64-bit BARs 是否落在 ACPI 64-bit 窗口内 | ✅ `0x7C00000000`、`0x7E00000000`、`0x7E10000000` 全在 `0x460000000–0x7FFFFFFFFF` 内 |
| 32-bit PCI 窗口上界 `0xDFFFFFFF` 与 **ECAM `0xE0000000`** | ✅ **紧邻但不重叠**（`0xDFFFFFFF` 之下 vs `0xE0000000` 之上）⇒ 32-bit 窗口**无法向上扩张** |
| ECAM `0xE0000000–0xEFFFFFFF` 与 MMIO devirt #1 `0xFD000000`(+30 MiB) | ✅ 不重叠（`0xFD000000 > 0xF0000000`） |
| GPP0 64-bit 窗口上界 `0x7E01FFFFFF` 与 iGPU `0x7E10000000` | ✅ 不重叠 |
| **MMIO devirt #4 `0x460000000` (+514 MiB) 与 DSDT 64-bit 窗口基址 `MAB = 0x460000000`** | ⚠️ **完全重合**（同一基址，前 514 MiB 被同时声明） |

### 6.5 **是否存在已证实的冲突？**

* **已证实的**只有"**声明重叠**"这一条：固件把 `0x460000000–0x4801FFFFF`（514 MiB）登记为
  `EfiMemoryMappedIO|EFI_MEMORY_RUNTIME`（① 日志 `OCABC: MMIO devirt 0x460000000 (0x20200 pages…)`），
  而 ② DSDT 又把 `0x460000000` 声明为 **PCI 64 位窗口的起点**。
  ⇒ **同一段地址同时被"固件运行期 MMIO"和"PCI 64 位可分配窗口"声明。**
* **未证实的**：这是否**真的**导致 macOS 的分配失败或固件运行期冲突。
  `DevirtualiseMmio=true` 会摘掉该描述符的 `EFI_MEMORY_RUNTIME` 位，但描述符**仍是
  `EfiMemoryMappedIO`**，所以它**不会**被当成可用 RAM 交给 OS；而 IOPCIFamily 分配的是
  **PCI 地址空间**（写桥/BAR 寄存器），并不查 EFI 内存图。
  ⇒ **机制上没有显然的因果链**，因此**不能**把它称为"已证实的冲突"。
* 这条仍是**唯一一条具体、可测的地址级线索**，但它**既不能靠 ACPI 补丁修**（用户禁止新增 SSDT），
  也**没有**运行期证据支持 —— 见 §7 候选 C。

### 6.6 建议的只读补充采集（不写配置寄存器）

| 环境 | 命令/做法 | 能补什么 | 成本 |
|---|---|---|---|
| **Windows（现在就能做）** | `nvidia-smi -q -d MEMORY`（已做，①）、`Get-CimInstance Win32_PnPAllocatedResource`（配合 `Win32_DeviceMemoryAddress`） | BAR 地址与长度；BAR1 尺寸 | **零**（只读） |
| **Windows** | 1401「Check this PC」再扫一次 | 与 `plan.json` 对比 | 低，但会写一个报告文件 |
| **Linux Live（经 OpenCore 引导）** | `lspci -Dnnvv`、`lspci -xxxx -s 01:00.0`、`cat /proc/iomem` | **RBAR Capability/Control 原始值**、全部桥窗口、ECAM 视图 | 需额外介质 + 经 OpenCore 选择 |
| **禁止** | 任何 `setpci` 写、任何会改 BAR/桥窗口的操作 | — | — |

---

## 7. Round 7 候选（只评估，**不写入**）

> 先给一条贯穿全部候选的判据：**本轮的可观测性没有改善**。
> `docs/06` §7 已证：macOS 侧**没有**任何内核日志/串口/持久化通道；
> 唯一能用的是"屏幕最后约 40 行 + 停留时长"，而 `doConfigure()` 期间屏幕被关。
> ⇒ **凡是把结果押在"macOS 屏幕停点"上的实验，其信息量天生有限**；
> 而**能给出硬数字的，必须把观察者换成 Windows/Linux**。

### 候选 A（首选）：**验证 OpenCore 改完 RBAR Control 之后的实际 BAR size**

| 项 | 内容 |
|---|---|
| **现有证据** | ① `RBAR 2/3 … from 13 to 6`（8 GiB → 64 MiB 的计算目标）；① `New BAR == Old BAR`（地址 dword 未变）；① `Reprogrammed BARs to original - Success`；② `plan.json` + ① `nvidia-smi` 证明**固件/Windows 侧 BAR1 = 8 GiB**；③ 源码从不读回 Control ⇒ **写后值从未被观测** |
| **尚未确定的假设** | 假设 H1：写入**生效**（GPU 保留地址、尺寸变为 64 MiB）；假设 H2：写入**无效**（GPU 忽略/锁定，`ResizeAppleGpuBars=0` 实为空操作） |
| **预期新信息** | **一个硬数字**：BAR1 的当前尺寸（64 MiB 或 8192 MiB）。它一次性决定 `ResizeAppleGpuBars=0` 这台机器上是否**有任何作用**，并因此决定整个 BAR 轴是否值得继续 |
| **成功/失败/无变化怎么解释** | *BAR1 = 64 MiB* ⇒ H1 成立 ⇒ macOS 一直在 64 MiB BAR1 下运行，"BAR 太大"这条假设**被排除**；*BAR1 = 8192 MiB* ⇒ 要么 H2 成立、要么 Windows 重设了它 ⇒ 需 A-2 的 raw config 读数判别；*无法引导/界面异常* ⇒ 记录后回滚（见风险） |
| **风险** | **中**。① 改的是 **GPU BAR**（用户当前未批准）；② ② `Configuration.tex:9353` Note 2 说明**缩小**不需要搬地址，但仍会改变 GPU 的视窗；③ **有记录的副作用**：issue #23 报告 `ResizeGpuBars` 真正生效时**会破坏 OpenCore 选择界面所用的 GOP framebuffer**（选择菜单变成 4 列小字或完全不显示）⇒ **可能难以选中 Windows**。对 Windows 本身、固件、内置盘**无持久影响**（重启即由固件重新枚举） |
| **精确修改范围** | 只改 `UEFI → Quirks → ResizeGpuBars`：`-1` → `0`。**不动** `ResizeAppleGpuBars`（保持 `0`）、不动 `ResizeUsePciRbIo`（保持 `False`）、不动其它任何键 |
| **回滚** | 一步 `Copy-Item` 本轮基线备份；或把 `ResizeGpuBars` 改回 `-1` |

### 候选 B：**单独改变 `ResizeAppleGpuBars`，研究 BAR 缩容与故障的关系**

| 项 | 内容 |
|---|---|
| **现有证据** | ① Round 1–6 全部在 `ResizeAppleGpuBars=0` 下运行，停点从 VoodooI2C → RTC → `PCI configuration begin` 变化过，但**没有一轮把 BAR 尺寸当变量**；② `Configuration.tex:9350` Note 1 说明这个 quirk 才是给 macOS 用的 |
| **未定假设** | 假设 H3：macOS 的停点与它看到的 BAR1 尺寸有关 |
| **预期新信息** | **取决于 A**：如果 A 证明写入生效（H1），那么 `-1` 与 `0` 的两臂分别是 8 GiB 与 64 MiB，**停点差异就变得可解释**；如果 A 证明写入无效（H2），则两臂**都是 8 GiB**，本候选**天然无信息** |
| **成功/失败/无变化** | *停点变化* ⇒ BAR 尺寸与故障有关（但仍不知具体机制）；*停点不变* ⇒ **无信息**（无法区分"BAR 无关"与"两臂其实一样"） |
| **风险** | **低–中**。`ResizeAppleGpuBars` 在 **Booter 阶段**（选择界面**之后**）生效 ⇒ **没有选择界面被破坏的风险**（比 A 更安全）；但它仍然改变 GPU 视窗 |
| **精确修改范围** | 只改 `Booter → Quirks → ResizeAppleGpuBars`：`0` → `-1`（跳过缩容，让 macOS 保持固件的 8 GiB） |
| **结论** | **逻辑上必须在 A 之后**（A 是 B 的可解释性前提） |

### 候选 C：**针对具体 PCI 资源或 ACPI 错误做修复**

| 项 | 内容 |
|---|---|
| **现有证据** | Phase 4 只找到**一条**具体地址级线索：`0x460000000`+514 MiB 被"固件运行期 MMIO"与"DSDT 64 位窗口基址"**同时声明**（§6.4/§6.5）。此外：dGPU/iGPU 路径**没有任何 `_CRS`** 可修；三个 `AE_ALREADY_EXISTS` 已在 `docs/06` §2.4 完整闭环且**不删任何 PCI 设备节点**；`_OSC` 实现正常（`docs/06` §2.2） |
| **未定假设** | 假设 H4：那段重叠真的干扰 macOS 分配 |
| **预期新信息** | 若能修，直接命中；但**当前没有任何运行期证据**支持 H4，且**机制上没有显然因果链**（§6.5） |
| **风险/改动范围** | 任何"修 `_CRS`/屏蔽该窗口"的做法都需要**新增 SSDT 或 DSDT 补丁** —— 用户**明确禁止**。⇒ **C 本轮不可行** |
| **结论** | **不可行**（不是"不值得"，而是"当前授权下没有可写的手段"） |

### 候选 D：**常规配置测试（`SetupVirtualMap=False`、禁用 `SSDT-PLUG-ALT`）**

| 项 | 内容 |
|---|---|
| **现有证据** | ① Round 5B 已证：单独把 `DevirtualiseMmio` 关掉会让失败点**前移**（内核零输出）⇒ 方向是**变差**；① `SSDT-PLUG-ALT` 载荷与 Acer 同模板（`docs/07` §3.3），而 Acer 能引导；① `SSDT-Disable_Network_GPP6` 那张表**从不生效** |
| **预期新信息** | 低：`SetupVirtualMap=False` 只是补齐内存图 2×2 的第三格（归因价值），并不指向故障；禁用 `SSDT-PLUG-ALT` 的机制与本停点相距更远 |
| **风险** | 中（可能像 R5B 一样前移失败点、损失可观测性）／低–中（丢 `plugin-type`） |
| **结论** | **只有当 A、B、C 都不可行时才轮到 D** |

---

## 8. 最终推荐

> **推荐 Round 7 = 候选 A，并采用"两步走"：先零成本校准读数仪，再做单变量 BAR 验证。**

**第 0 步（**零 EFI 改动、零风险、现在就能做**）——"读数仪校准"**
在 Windows 里跑**只读**命令：
```powershell
nvidia-smi -q -d MEMORY          # 期望 BAR1 Total = 8192 MiB（本轮已实测确认）
```
这一步**本轮已经完成并记录**（§2.5），因此 Round 7 只需要"第 1 步"。

**第 1 步（Round 7 本体，需批准写盘一次）——单变量 `ResizeGpuBars: -1 → 0`**
1. 校验卡上 SHA-256 == `021F02B3…`（已回滚的 Round 4），先备份；
2. **只改** `UEFI → Quirks → ResizeGpuBars` 一处；
3. `ocvalidate` 1.0.9 → 0 issues；读回校验 SHA-256 与语义差异只有一处；
4. 经 **OpenCore 选择界面引导 Windows**（若选择界面被破坏，记录现象后回滚，见风险）；
5. 在 Windows 里跑 `nvidia-smi -q -d MEMORY` 与（可选）CIM 资源查询；
6. **BAR1 Total 从 8192 MiB 变成 64 MiB ⇒ H1 成立**；仍是 8192 MiB ⇒ 转 A-2（Linux 只读 `lspci`）；
7. 回滚到 Round 4 的备份，恢复 `ResizeGpuBars=-1`。

**为什么它比其它候选更有信息量**：
* 它是**唯一**能以**硬数字**回答 Phase 3 核心问题（"显卡是否真的采用了 64 MiB BAR"）的方案；
  而这个问题一旦回答，就同时决定：
  (i) `ResizeAppleGpuBars=0` 在本机**是否为空操作**；
  (ii) 候选 B（改 `ResizeAppleGpuBars`）**是否值得做**；
  (iii) macOS 侧"BAR 太大"这一整类假设**是否被排除**。
* 它的**观察者是 Windows，不是 macOS 屏幕** —— 这恰好绕开了本项目最大的观测瓶颈
  （macOS 侧无日志、无串口、硬卡死无持久化、`doConfigure()` 期间屏幕被关）。
* 候选 B 逻辑上依赖 A；候选 C 在现行授权下不可写；候选 D 只提供归因价值。
  ⇒ **A 是唯一能推动故障范围收敛的实验。**

**状态：只给候选与风险评估，未写入 U 盘。等批准。**
未获批准前**不**修改 BIOS / ReBAR（BIOS 项）/ `MmioWhitelist` / Windows EFI / BCD /
内置磁盘分区，**不**自行新增 SSDT，**不**替换 `OpenCore.efi`。

> **⚠️ 本节（§8）的方案形态已被用户 2026-10-13 的修正取代**：§8 里"用 Windows
> `nvidia-smi` 读回"的形态**不再成立**（理由见 §2.5 的证据等级限定与 §9.1）。
> **Round 7 的最终形态见 §9**：改为**在同一次 Apple 启动的 OpenCore DEBUG 日志里做两阶段对照**。

---

## 9. Round 7 定稿：两阶段 RBAR 日志对照（**已写入卡上，待实机启动**）

### 9.1 本机 OpenCore 的**确切源码版本**已定位（①+②）

* ① 卡上 `OpenCore.efi` 自报 `DBG-109-2026-10-10`；② `ocvalidate` 报
  "only compatible with OpenCore version 1.0.9"。
* ② **上游 `acidanthera/OpenCorePkg` 并没有 `1.0.9` tag**（最新 tag 是 `1.0.8`）。
  真正的来源在 1401 自己的镜像清单里：
  `1401/engine/app/p1401/mirror.json:397-399`
  ```json
  "https://github.com/dortania/build-repo/releases/download/OpenCorePkg-963025f/OpenCore-1.0.9-DEBUG.zip": {
    "sha256": "4a35bc9409d4bbacb7a9e72127be6cc4c677b22a0399a4c430e21460e65df886",
    "size": 11837410
  }
  ```
  ⇒ 本机 OpenCore = **Dortania build-repo 的 `OpenCorePkg-963025f`**，
  即 **OpenCorePkg 提交 `963025f`** 的构建（不是任何 release tag）。
* ⇒ 因此"实际构建对应的源码版本"**是可查的**：以下三处都已按 **commit `963025f`** 取回并逐行核对。

### 9.2 两个调用点：**确认存在、顺序成立**（② commit 963025f）

**阶段 A —— UEFI 早期**，`Library/OcMainLib/OpenCoreUefi.c:982-987`
（所在函数为 **`OcLoadUefiSupport`**，行 900 起）：
```c
  if (  (Config->Uefi.Quirks.ResizeGpuBars >= 0)
     && (Config->Uefi.Quirks.ResizeGpuBars < PciBarTotal))
  {
    DEBUG ((DEBUG_INFO, "OC: Setting GPU BARs to %d\n", Config->Uefi.Quirks.ResizeGpuBars));
    ResizeGpuBars (Config->Uefi.Quirks.ResizeGpuBars, TRUE, Config->Uefi.Quirks.ResizeUsePciRbIo);
  }
```

**阶段 B —— Apple 启动路径**，`Library/OcAfterBootCompatLib/ServiceOverrides.c:1255-1259`：
```c
    if (  (BootCompat->Settings.ResizeAppleGpuBars >= 0)
       && (BootCompat->Settings.ResizeAppleGpuBars < PciBarTotal))
    {
      ResizeGpuBars (BootCompat->Settings.ResizeAppleGpuBars, FALSE, BootCompat->Settings.ResizeUsePciRbIo);
    }
```

**核对结论（逐条）**：

| 核对项 | 结果 |
|---|---|
| 两处调用**都存在** | ✅ 均在 commit `963025f` 原文中逐字确认 |
| **执行顺序**成立 | ✅ A 在 `OcLoadUefiSupport`（OpenCore 启动早期）→ B 在 `AppleMapPrepareBooterState` **之后**、boot.efi 交接之前 |
| A 会输出 RBAR DEBUG | ✅ 有独立的 `OC: Setting GPU BARs to %d`；且 `ResizeGpuBars()` 本身会打印 `OCDM: RBAR using PciIo` 等 |
| B 会输出 RBAR DEBUG | ✅ `ResizeGpuBars()` 的 `OCDM:` 行会再打一遍；**⚠️ 但 B 处源码里没有 `OC: Setting GPU BARs` 那一行** |
| **重要差异 1** | A 传 `Increase = TRUE`，B 传 `Increase = FALSE`。该形参**会打进 DEBUG 日志**（`sizing %u inc %d`、`Setting RBAR to %d inc %d`）⇒ **阶段 A 必然是 `inc 1`、阶段 B 必然是 `inc 0`**，这是判别"哪一组输出属于哪个阶段"的**直接依据**（§9.4）。语义上它影响 `PCI_BAR_CAP_LIMIT` 的"不许增大"封顶；`Size=0` 时两者都落在最小支持尺寸，但代码路径不同 |
| **重要差异 2** | 目前 `ResizeGpuBars = -1` ⇒ 阶段 A 的 `if` **不成立** ⇒ **一次都不调用、一行都不打印**。这正好解释了本机现有日志里**只有一组** RBAR 输出（那组来自阶段 B） |
| **重要风险** | A 位于 **`OcLoadUefiSupport`，即 OpenCore 启动早期、选择界面绘制之前** ⇒ 一旦 BAR 缩小破坏了 GOP framebuffer，**选择界面本身会受损**（与 issue #23 的记录一致） |

### 9.3 六项严格区分（用户第三阶段要求）

| # | 事项 | ② 源码依据（commit 963025f） | 本机是否已证 |
|---|---|---|---|
| 1 | **成功计算目标 size** | `SetResizableBar.c:272-297` 算出 `Bit` | ✅ ① 日志 `results setting from 13 to 6` |
| 2 | **发送 RBAR Control 写入** | `SetResizableBar.c:322-329` 写 `ResizableBarControl`，随后 `ChangedBars = TRUE`（`:331`） | ⚠️ 无直接证据（无日志），只能③推论"已发送" |
| 3 | **PCI 写操作返回成功** | **❗ 该写操作的返回状态根本没有被捕获**：`:323` 是裸调用 `PciIo->Pci.Write(...)`，**没有 `Status =`**；而 `SetResizableBarOnDevicePciIo` 末尾 `:381` **无条件 `return EFI_SUCCESS`** | ❌ **从未被检查、从未被记录** ⇒ **未知** |
| 4 | **写后读取到新的 BarSize** | **源码从不读回 BarSize**（只读回 6 个 BAR 地址 dword：`:337`） | ❌ **不存在** |
| 5 | **Apple 阶段读取到新的 BarSize** | 阶段 B 的 `ResizeGpuBars()` 会**重新读** `Entries[i].ResizableBarControl.Bits.BarSize`（就是日志里 `from N` 的来源） | ⏳ **这正是 Round 7 要造的观测** |
| 6 | **macOS 内核实际获得的 BAR 资源** | —— | ❌ **不可观测**（`docs/06` §7） |

**⇒ `OCDM: Reprogrammed BARs to original - Success` 究竟证明了什么？**
**只证明一件事**：把 6 个 BAR **地址** dword 写回原值的那个 `Pci.Write`（`:370`）返回了 `EFI_SUCCESS`。
它**不证明**尺寸写入成功，**不证明** BAR 被改成 64 MiB，也**不证明**任何阶段读到了新尺寸。
（另外：读操作 `Pci.Read` 的返回状态**是**被检查的，例如 `:60/:220` 会打印 `Capability I/O error`。）

### 9.4 实验设计（已执行：单变量 `UEFI.Quirks.ResizeGpuBars: -1 → 0`）

**预期观测（同一次 Apple 启动的 DEBUG 日志里应出现两组 RBAR 输出）**

> **🔑 阶段判别器：日志里的 `inc` 字段**（用户 2026-10-13 修正，**必须按此核对**）
> `ResizeGpuBars()` 的 DEBUG 里有两处带 `inc %d`：`Setting RBAR to %d inc %d on %d/%d` 与
> `RBAR %u/%u supports 0x%Lx, sizing %u inc %d results setting from %u to %d`。
> 该字段就是调用点传入的 **`Increase`** 形参：阶段 A 传 **`TRUE` ⇒ `inc 1`**，
> 阶段 B 传 **`FALSE` ⇒ `inc 0`**（§9.2）。
> ⇒ **`inc 1` 的那组必是 UEFI 阶段，`inc 0` 的那组必是 Apple 阶段** —— 这比"靠位置/序号猜"可靠得多。

| 阶段 | 期望看到 | 说明 |
|---|---|---|
| **A（UEFI 早期）** | `OC: Setting GPU BARs to 0`<br>`OCDM: RBAR using PciIo`<br>`OCDM: Setting RBAR to 0 **inc 1** on 5/43`<br>`OCDM: RBAR 2/3 supports 0x3FC0, sizing 0 **inc 1** results setting **from 13 to 6**` | 第一次调整：从固件的 8 GiB 缩到 64 MiB。**`inc 1`** |
| **B（Apple 路径）** | `OCDM: RBAR using PciIo`（第二次）<br>`OCDM: Setting RBAR to 0 **inc 0** on 5/43`（第二次）<br>`OCDM: RBAR 2/3 supports 0x3FC0, sizing 0 **inc 0** results setting **from 6 to 6**` 或 **`from 13 to 6`** | **`from 6 to 6`** ⇒ 阶段 A 的 64 MiB **保持到了 Apple 阶段**；<br>**`from 13 to 6`** ⇒ **没有保持**（但**不能**立刻断定是哪一步恢复或写入失败）。**`inc 0`** |

> **✅ 模型预验证（① 现有日志已能佐证）**：Round 4 / Round 6 的日志里**只有一组** RBAR 输出，
> 且全部是 **`inc 0`**：`Setting RBAR to 0 inc 0 on 5/43`、`RBAR 2/3 … sizing 0 inc 0 … from 13 to 6`。
> 这与"`ResizeGpuBars = -1` ⇒ 阶段 A 的 `if` 不成立 ⇒ 那一组只可能来自阶段 B（`Increase=FALSE`）"
> **完全一致** ⇒ 说明"`inc` 判别阶段"这个读法在本机是**可用的**。

> **⚠️ 不要去找第二行 `OC: Setting GPU BARs`** —— 阶段 B 的调用点**源码里没有这条 DEBUG**（§9.2）。
> 阶段 B 的判据**只有** `OCDM: RBAR 2/3 … from X to Y`、第二次的 `OCDM: RBAR using PciIo`
> 以及 **`inc 0`**。

**阶段 A 在日志里的确切位置（① 用 Round 6 日志定位，可逐行核对）**

Round 6（`ResizeGpuBars = -1`）里该处**没有任何输出**，但上下文锚点齐全：

```
00:233 00:003 OC: OcLoadUefiSupport...
...
00:286 00:003 OCDM: Found 0x20050/0x20050 UEFI version (376 bytes, …)
00:289 00:003 OC: AVX enabled - 1
00:293 00:003 OC: Got 4 drivers          ← 阶段 A 的 if 块就在这两行之间
```

⇒ **Round 7 的 `OC: Setting GPU BARs to 0` 应紧跟在 `OC: AVX enabled - 1` 之后、
`OC: Got 4 drivers` 之前出现**（`OcLoadUefiSupport` 内 AVX 块之后即该 `if` 块），
随后是阶段 A 的一整组 `OCDM:` 行。

⇒ 这也**量化了风险**：阶段 A 发生在 **`00:2xx`（OpenCore 启动约 0.3 秒）**，
即**选择界面绘制之前很久** —— 一旦 BAR 缩小破坏 GOP framebuffer，
**受影响的是选择界面本身**（与 issue #23 一致）。

**必须确认两组输出对应同一台 RTX 4050**（用户明确要求，不得只看"两行相似字符串"）

> **⚠️ 不要仅靠设备枚举序号（用户 2026-10-13 补充要求）**
> **UEFI 阶段可能扫描到多台显示设备**（本机至少还有 780M iGPU `08:00.0` 与 NVIDIA HD Audio `01:00.1`），
> 且两阶段各自独立调用 `gBS->LocateHandleBuffer(ByProtocol, &gEfiPciIoProtocolGuid)` ——
> 序号只反映**那一次**枚举的顺序，**不足以证明是同一台设备**。
> ⇒ **主判据必须是与设备身份绑定的字段**：**RBAR Capability 掩码**与**BAR 地址**；
> `inc` 只用于判别**阶段**，`序号` 只作辅助一致性检查。

| 交叉核对项 | 期望值（两侧必须一致） | 权重 |
|---|---|---|
| **RBAR Capability 掩码** | `RBAR 2/3 supports **0x3FC0**`（恰好对应 BAR1 的 64 MiB…8 GiB 支持集） | **主判据**（与设备+具体 BAR 绑定） |
| 整套能力集 | `RBAR 1/3 supports **0x10**` → BAR0(16 MiB)、`RBAR 3/3 supports **0x20**` → BAR3(32 MiB) | **主判据**（三件套同时吻合才排他） |
| **`Old BAR` 六 dword** | `DC000000 0000000C 0000007C 0000000C 0000007E 0000F001` | **主判据**（BAR 地址布局与设备绑定） |
| `RBAR control is … total 3` | `460, total 3`（Control 原值 + 可调 BAR 数量） | 强旁证 |
| **`inc` 字段** | 阶段 A = **`inc 1`**；阶段 B = **`inc 0`** | 判别**阶段**（不是判别设备） |
| 设备扫描序号 | `… on **5/43**`（两次一致） | **仅辅助**：一致不证明同一设备，不一致也不必然说明换了设备 |
| 紧随其后的无 RBAR 设备 | `… on 19/43` + `RBAR is unsupported by device - Not Found` | 辅助：两侧枚举序列形状应相同 |

⇒ 若两组输出的 **Capability 掩码 / 能力集 / `Old BAR` 六 dword** 有任何一项不吻合，
就必须按"**可能是不同显示设备**"处理，**不得**把它们当作同一台 GPU 的前后两阶段。

**结果判定（用户第五阶段，原样写死）**

| 观察 | 只能得出的结论 | 下一步 |
|---|---|---|
| macOS **越过** `PCI configuration` | 记录新日志并**复测**；**不能**立即认定 BAR 是唯一根因 | 复测确认 |
| 阶段 B 显示 **`from 6 to 6`**，但仍卡在 PCI | **早期 64 MiB 缩容不足以**让该配置进入 Recovery；**不能排除** macOS 后续重新分配资源 | 记录；不自动推进 |
| 阶段 B 仍为 **`from 13 to 6`** | **重点调查"为何早期缩容没有保持"**，而**不是**立即改 BIOS ReBAR | 记录；单独立项 |
| **GOP 损坏导致无法选择系统** | 本轮记为「**实验无法完成**」 | **恢复基线**，不擅自执行后续实验 |

### 9.5 写入记录（条件逐条满足）

| 条件 | 结果 |
|---|---|
| 1. Round 4 基线 SHA-256 == `021F02B3…` | ✅ 写入前实测相符（52124 B） |
| 2. 独立测试 U 盘 / 可独立回退的 EFI 副本 | ✅ **本机只有 D: 一个可移动盘** ⇒ 采用"**可独立回退的 EFI 副本**"路线：整棵 `D:\EFI` 已完整复制到 **`C:\Users\24269\Documents\macos\efi-snapshots\round4-r7-baseline\EFI`**（137 文件 / 12,206,164 B；副本内 `config.plist` = `021F02B3…`、`OpenCore.efi` = `1569CD1D…` 与卡上一致） |
| 3. 只改 `UEFI.Quirks.ResizeGpuBars` 一个整数 | ✅ **1 行**（1-based **2285**），52124 → **52123** B |
| 4. 与实际构建匹配的 `ocvalidate` | ✅ `01e07a898e65-ocvalidate.exe`（1.0.9 DEBUG）→ **No issues found**（exit 0） |
| 5. 保留不经 OpenCore 直接启动 Windows 的方案 | ✅ **未修改 Windows EFI / BCD**（全程未动）⇒ 固件启动菜单（Esc/F8）里的 Windows 项**原样可用** |
| 6. 不改 BIOS / Windows EFI / BCD / 内置分区 | ✅ 未动 |
| 7. 不改 `ResizeAppleGpuBars` / `ResizeUsePciRbIo` / 其它 Booter 参数 | ✅ 脚本逐项断言：`ResizeAppleGpuBars=0`、`ResizeUsePciRbIo=false`、MAT 三元组、`DevirtualiseMmio=true`、`SetupVirtualMap=true`、`MmioWhitelist=[]`、`boot-args` 不变（仍无 `npci`） |
| 8. 不换 `OpenCore.efi` / 不加驱动 | ✅ `OpenCore.efi` SHA 写入前后均为 `1569CD1D183C5EE9FDA2ECED767A4B2EFA307E6EDFCF2A50109C9657098671FF` |
| 语义差异 | ✅ 恰好 `UEFI.Quirks.ResizeGpuBars` 一项 |
| **写入后卡上 SHA-256** | **`58E78A12C8102AF7A5DD3B2D7417BE891B17EFC78FF0817C99F69C6BC7A78CA3`**（52123 B） |
| 脚本 | `audit/apply-round7-stick.py`（任一预条件不满足即拒绝写入；原子替换） |

**风险（**不是零风险**）**：阶段 A 在**选择界面绘制之前**执行（§9.2）⇒ 若 BAR 缩小破坏 GOP framebuffer，
**可能难以或无法选中目标系统**。对固件、Windows、内置盘**无持久影响**（重启后由固件重新枚举）。

**回滚（两条，随时可用）**
```powershell
# A. 只回滚配置
Copy-Item D:\_backup-round0\config.plist.round4-pre-r7 D:\EFI\OC\config.plist -Force
# B. 整棵 EFI 回滚（含 OpenCore.efi 与全部 kext/ACPI/driver）
robocopy C:\Users\24269\Documents\macos\efi-snapshots\round4-r7-baseline\EFI D:\EFI /MIR
# 回滚后 config.plist SHA-256 必须回到 021F02B3B46953021FF31835518790DD6BEB57074BE822D127305434581815E4（52124 B）
```
若**选择器损坏或完全黑屏**：**优先用备用启动路径**（固件启动菜单直接进 Windows）恢复，
**不盲目按键、不继续叠加修改**；本轮记为「实验无法完成」。

**下次启动请记录**：`OC: Setting GPU BARs to 0`（阶段 A）、两组 `OCDM: RBAR using PciIo`、
阶段 A 与阶段 B 的 `RBAR 2/3 … from X to Y`、`Old BAR` 六 dword、`5/43` 设备序号、
以及是否出现 `[ PCI configuration end, … ]`；若停止输出**至少观察 10 分钟并拍摄完整屏幕**。

**状态：Round 7 已写入卡上并已引导一次 —— 结果见 §9.6。**
**未经批准不执行 Round 8**；**不**修改 BIOS / ReBAR（BIOS 项）/ `MmioWhitelist` /
Windows EFI / BCD / 内置分区；**不**换 `OpenCore.efi`、**不**加驱动、**不**加 SSDT。

### 9.6 Round 7 引导结果（**已回填**）—— **两阶段读回成功，H1 成立**

日志：`logs/opencore-2026-10-13-213656.txt`（卡上 `D:\opencore-2026-10-13-213656.txt`，
262144 B，未写满：首字节 0 偏移植 68834，756 行，末行 `16:477 AAPL: #[EB|LOG:EXITBS:START]`）。

#### A. 两组输出（逐字，①）

**阶段 A（UEFI 早期，`00:283`–`00:314`）** —— 位置与 §9.4 的预测**完全一致**
（紧跟在 `OC: AVX enabled - 1` 之后、`OC: Got 4 drivers` 之前）：

```
00:280  OC: AVX enabled - 1
00:283  OC: Setting GPU BARs to 0                      ← 预测命中
00:286  OCDM: RBAR using PciIo
00:289  OCDM: Setting RBAR to 0 inc 1 on 5/43          ← inc 1 = UEFI 阶段
00:292  OCDM: RBAR control is 460, total 3 - Success
00:295  OCDM: Old BAR DC000000 0000000C 0000007C 0000000C 0000007E 0000F001 - Success
00:297  OCDM: RBAR 1/3 supports 0x10,   sizing 0 inc 1 results setting from 4  to 4
00:300  OCDM: RBAR 2/3 supports 0x3FC0, sizing 0 inc 1 results setting from 13 to 6
00:303  OCDM: RBAR 3/3 supports 0x20,   sizing 0 inc 1 results setting from 5  to 5
00:305  OCDM: New BAR DC000000 0000000C 0000007C 0000000C 0000007E 0000F001 - Success
00:308  OCDM: Reprogrammed BARs to original - Success
00:311  OCDM: Setting RBAR to 0 inc 1 on 19/43
00:314  OCDM: RBAR is unsupported by device - Not Found
```

**阶段 B（Apple 路径，`14:884`–`14:906`）**：

```
14:884  OCDM: RBAR using PciIo                          ← 第二次（阶段 B 没有 "Setting GPU BARs" 行，与源码一致）
14:887  OCDM: Setting RBAR to 0 inc 0 on 5/43           ← inc 0 = Apple 阶段
14:890  OCDM: RBAR control is 460, total 3 - Success
14:893  OCDM: Old BAR DC000000 0000000C 0000007C 0000000C 0000007E 0000F001 - Success
14:895  OCDM: RBAR 1/3 supports 0x10,   sizing 0 inc 0 results setting from 4  to 4
14:898  OCDM: RBAR 2/3 supports 0x3FC0, sizing 0 inc 0 results setting from 6  to 6   ★
14:901  OCDM: RBAR 3/3 supports 0x20,   sizing 0 inc 0 results setting from 5  to 5
14:904  OCDM: Setting RBAR to 0 inc 0 on 19/43
14:906  OCDM: RBAR is unsupported by device - Not Found
```

#### B. "同一台 GPU"确认（按 §9.4 的**主判据**，不是靠序号）

| 主判据 | 阶段 A | 阶段 B | 一致？ |
|---|---|---|---|
| RBAR Capability 掩码全组 | `0x10` / `0x3FC0` / `0x20` | `0x10` / `0x3FC0` / `0x20` | ✅ |
| `Old BAR` 六 dword | `DC000000 0000000C 0000007C 0000000C 0000007E 0000F001` | **完全相同** | ✅ |
| `RBAR control is … total 3` | `460, total 3` | `460, total 3` | ✅ |
| （辅助）序号 | `5/43`，随后 `19/43` unsupported | `5/43`，随后 `19/43` unsupported | ✅ |

⇒ **两组输出确认属于同一台 RTX 4050（`01:00.0`，`\_SB.PCI0.GPP0.PEGP`）。**

#### C. **结论：OpenCore 的 RBAR Control 写入确实生效（H1 成立，(a) 被证伪）**

* 阶段 B 读到 **`from 6`**，而阶段 A 已经把 BAR1 设成 **index 6 = 64 MiB**
  ⇒ **阶段 A 的缩容保持到了 Apple 阶段**。
* ⇒ 此前 §3.3 里的二义性 **就此解决**：
  **(a) "该 GPU 忽略/锁住尺寸写入" 被证伪**；
  **(b) "设备在尺寸变化时保留 BAR 内容" 成立**
  —— 这也正是 `New BAR == Old BAR` 的正确解释（**不是**"没写进去"）。
* **阶段 B 一次写操作都没有发生**（关键）：
  `New BAR` 计数 = **0**、`Reprogrammed` 计数 = **0**（阶段 A 各为 1）
  —— 因为 `from 6 to 6` ⇒ `Bit == 当前 BarSize` ⇒ 源码走 `continue` ⇒ `ChangedBars` 保持 `FALSE`
  ⇒ `if (ChangedBars)` 整块被跳过。
  ⇒ **`from 6 to 6` 是一次"零写入"的纯读回**，**没有被本阶段自己的动作污染** —— 这是本条证据最强的地方。

#### D. **跨轮次推论（本轮最重要的一条）**：**已测各轮的 macOS 都跑在 64 MiB BAR1 之下**

① 逐份日志统计（`RBAR using PciIo` / `New BAR` / `Reprogrammed` 的出现次数）：

| 轮次 | `UEFI.ResizeGpuBars` | 通过次数 | 阶段 A | 阶段 B | `New BAR`+`Reprogrammed` |
|---|---|---|---|---|---|
| Round 4 / Round 6 | `-1` | **1** | 无（`if` 不成立） | `inc 0`，`from 13 to 6` | **1 + 1** ⇒ 阶段 B **写了** |
| **Round 7** | `0` | **2** | `inc 1`，`from 13 to 6` | `inc 0`，**`from 6 to 6`** | 阶段 A：1+1（写了）；**阶段 B：0 + 0（没写）** |

⇒ 在 **R4/R6** 里，虽然阶段 A 不存在，但**阶段 B 自己把 BAR1 从 13 写成了 6**（有 `New BAR` + `Reprogrammed` 为证）
⇒ **那些轮次在"交给 XNU 之前"就已经是 64 MiB 的 BAR1**。

> **⚠️ 证据等级（用户 2026-10-13 要求下调，必须按此措辞）**
> * **① 直证**只覆盖 **Round 7**：该 GPU 的尺寸写入**有效**，且 64 MiB **保持到了 Apple 交接阶段**。
> * R2/R4/R5B/R6 走的是**同一套底层缩容流程**，且 R4/R6 日志显示阶段 B **确实发出了写入**
>   ⇒ 这构成**很强的间接证据**，但**那些轮次没有各自的写后读回**。
> * ❗ 因此 **不能**声称"当时 XNU 一定使用了 64 MiB BAR1"。
> * ❗ 尤其 **不能**把「Apple 交接阶段的 BAR1 尺寸」等同于「XNU PCI 枚举阶段的最终尺寸」——
>   macOS 自己可能重新分配资源，而本机**没有任何可取的 macOS 侧读数**（`docs/06` §7）。
> * ⇒ 正确表述：**"BAR1 在交给 XNU 之前已是 64 MiB"证据很强；"XNU 枚举时用的是 64 MiB"仍未证。**
>   因此 **BAR 轴的嫌疑下降，但没有被排除**。

#### E. 屏幕侧（**已由实机操作者确认 ≥10 分钟**，①）

最后可见两行仍为：
```text
[ PCI configuration begin ]
[IOPCIConfigurator::configure()] PCI configuration PCI0
```
上方是 `CoreAnalyticsHub start completed` 与 5× `[addMemoryRange()] AppleVTD is not yet installed as gSystem`
—— **与 Round 4 / Round 6 的屏幕内容逐行一致**。

**结案证据（另见中途照片 `IMG20261013214007.jpg`，21:40:07，`EXITBS` 后约 3 分钟）**：

> **实机操作者确认：在 `PCI configuration begin` / `PCI configuration PCI0` 之后连续等待超过 10 分钟，
> 没有任何新的屏幕输出，也没有进入 Recovery。**
> **⇒ Round 7 正式结案：BAR 双阶段读回成功，macOS Recovery 启动失败，已确认 ≥10 分钟无新输出。**
> （中途照片只是"停点已出现"的旁证；**≥10 分钟无新输出**这个结论由操作者的观察给出，不由照片推断。）

**按 §9.4 预登记的判据回填**：

| 观察 | 结论 |
|---|---|
| 阶段 B **`from 6 to 6`** | ✅ **早期 64 MiB 缩容保持到了 Apple 阶段**（H1 成立） |
| 但仍**卡在 `PCI configuration`** | ⇒ **早期 64 MiB BAR 缩容不足以**使该配置进入 Recovery；**不能排除** macOS 后续重新分配资源 |
| GOP / 选择界面 | ✅ **本次未观察到选择界面损坏**（引导正常到达 Apple 路径并跑到 `EXITBS`，操作者未报告异常）—— 但只说明"本次未触发"，**不等于无风险** |

#### F. ⛔ 原"候选 B"判定为**设计无效**（用户 2026-10-13 修正）

> **`Booter.Quirks.ResizeAppleGpuBars: 0 → -1`（在 Round 7 基线上）测不到它想测的东西，不得写盘。**
>
> 因为 Round 7 已把 `UEFI.Quirks.ResizeGpuBars` 设为 `0`，**阶段 A 在 UEFI 早期就把 BAR1 缩到 64 MiB**；
> 此时只把 `ResizeAppleGpuBars` 改成 `-1` 只是让**阶段 B 不再做二次调整**，
> **BAR1 不会自动恢复成 8 GiB** ⇒ **Apple 启动阶段仍然是 64 MiB**，该候选无效。

**若将来确实要测"macOS 用 8 GiB BAR1"，必须以 Round 4 为基线**：

| 键 | Round 4 | 8 GiB 测试候选 |
|---|---|---|
| `UEFI → Quirks → ResizeGpuBars` | `-1` | **`-1`**（不变） |
| `Booter → Quirks → ResizeAppleGpuBars` | `0` | **`-1`**（唯一改动） |

⇒ 相对 Round 4 **只差 Booter 一项**，这才是那类实验的正确形态。

**但该实验已按用户 2026-10-13 的指示降级**：
优先级改为**先分析 PCI 桥资源 / 固件 ACPI·IRQ / 设备枚举**，而不是先让 macOS 去用 8 GiB BAR。
其余候选：**C** 仍不可行（需新增 SSDT / 改 `_CRS`，用户禁止）；**D** 仍是低信息量。
⇒ **下一轮方向重排与只读证据见 §10。**

**状态：Round 7 正式结案 —— 「BAR 双阶段读回成功，macOS Recovery 启动失败，已确认 ≥10 分钟无新输出」；
卡上仍为 Round 7（`58E78A12…`）；Round 8 为纯只读（见 §11），未改任何 EFI。**
**未获批准不修改任何 EFI 配置**；**不**修改 BIOS / ReBAR / `MmioWhitelist` /
Windows EFI / BCD / 分区，**不**换 `OpenCore.efi`、**不**加驱动、**不**加 SSDT。

---

## 10. 下一轮方向重排 + PCI 资源图只读审计（用户第四阶段要求）

> 用户指示：**优先分析 PCI 桥资源、固件 ACPI/IRQ 和设备枚举问题**，而不是直接让 macOS 使用 8 GiB BAR。
> 本节给出**只用已有产物**（① 本机 Windows 只读查询 + ② `plan.json` + ① ACPI 反编译）就能得到的证据。

### 10.1 方法（全部只读，零 EFI 改动）

* ② 解析 `1401/plan.json` 里**全部 42 条 `resource_record`**（每条含设备 ID、位置、已分配内存/IO 窗口）。
  * **本轮查明这些记录的真正来源**（此前文档只泛称"1401 的扫描"）：
    `capture.device_map.pci_resources`，采集方式是 **CfgMgr32 设备管理 API 的
    `CM_Get_First_Log_Conf(hDevInst, ALLOC_LOG_CONF)` + `CM_Get_Res_Des_Data`**，
    即 **Windows `pci.sys` 记录的"已分配逻辑配置"**。
    ⇒ **它不是 PCI 配置空间转储**；它是"Windows 认为已经分配给该功能的东西"。
    这一点在 §11.2 变成关键：它是**比 `pnputil /resources` 更完整**的那个来源。
* ① 用 `Get-PnpDeviceProperty`（**只读**）取关键设备的 `DEVPKEY_Device_BusNumber` / `LocationInfo`，
  解决 `location` 字符串里的进制歧义。
* ① 与 DSDT 声明的窗口对照：32-bit `0xA0000000–0xDFFFFFFF`、64-bit `0x460000000–0x7FFFFFFFFF`。
* 脚本：`audit/pci-resource-audit.py`（**已入库**，见 §10.5；用法
  `python audit/pci-resource-audit.py <plan.json>`）。
  输出已归档：`audit/results/pci-resource-plan-2026-10-13.txt`。
  **未写任何 PCI 配置寄存器。**

### 10.2 结果（①+②）

**（a）四条"排除性"结论（都是负结果，但很有价值）**

> ⚠️ **每条都只在它自己的量程内成立。"负结果"不等于"整类假设被排除"——**
> 越界说明见 §10.5。表头已按此改写。

| # | 在本量程内成立的结论 | 证据 | **不能**外推到什么 |
|---|---|---|---|
| 1 | **这 42 条 record 里所有已分配窗口都落在 ACPI 声明的窗口之内** | 44 个内存/IO 区间逐一比对，无一处越界 | 不能推出"所有固件/Windows 分配都无越界"，更不能推出"macOS 的分配也无越界"（macOS 侧不可观测） |
| 2 | **这 42 条 record 里没有"真正的"资源冲突** | 26 对区间相交**全部是"父桥窗口 ⊇ 子设备窗口"的包含关系**；**部分重叠（partial overlap）= 0** | 不能推出"不存在冲突"：这只覆盖**已分配且已记录**的窗口；（本轮补充）记录**缺**了 2 条 ≤ 42 之外的桥 64 位窗口的问题已在 §11.2 修正 |
| 3 | **在用总线号都在声明范围内** | 实测在用总线 **0/1/2/3/4/101/102/103**（= `0x00/0x01/0x02/0x03/0x04/0x65/0x66/0x67`），**最大 0x67** | ⚠️ 原表述"全部在 `0x00–0x100` 之内"**记法有误**：`0x100` 不是合法总线号，**PCI 总线号上限是 `0xFF`**。端点语义已重新核对，见 §10.5(3) |
| 4 | **32 位地址窗口 1024 MiB 中用掉 440 MiB（43.0%），余 584 MiB** | 占用率计算 | ❌ **不能**推出"32 位空间够用" —— 总量有余量**不排除碎片、对齐（alignment）与单个桥窗口上限的约束**；macOS 的分配器怎么切这块空间完全不可见 |

**（b）三条"值得继续追"的正面线索**

| # | 线索 | 数据 | 为什么值得追 |
|---|---|---|---|
| **L1** | **`GP11`（`dsdt.dsl:2966 Name (_ADR, 0x00030001)`，PCI `0/3/1`，`1022:14EF`）持有超大窗口，但背后没有任何设备** | 32-bit **`0xC4000000–0xDBFFFFFF`（384 MiB）** + 64-bit **`0x6C00000000–0x7BFFFFFFFF`（64 GiB）**；`plan.json` 里**没有**任何设备的 BAR 落在这两个窗口内 | 一个"有窗口、无端点"的根端口；`configure()` 的 `boot reset/scan` 会走到它 |
| **L2** | **DSDT 64 位窗口的**基址**同时被固件登记为运行期 MMIO，而固件自己在该区域**什么都没放** | DSDT `MAB = 0x460000000`；MMIO devirt #4 = `0x460000000` + `0x20200` 页（514 MiB）；而**最低的 64 位分配是 `0x6C00000000`**（GP11 的窗口） | 同一个 514 MiB 区域被"两个身份"声明；macOS 的分配器**可能**从窗口基址开始放东西 |
| **L3** | **64 位窗口的**顶部**被完全占满**：WiFi 的 64 位 BAR 恰好结束在 `MAM` | MediaTek MT7922（`14C3:0616`，bus 3）与其父桥 `1022:14EE`（`0/2/x`）都是 `0x7FFFF00000–0x7FFFFFFFFF`；而 `MAM = 0x7FFFFFFFFF` | 窗口**上沿无余量**；任何需要"往上长"的分配都会失败 |
| **L4** | 32 位窗口的**上沿被 ECAM 顶死** | 32-bit 窗口上界 `0xDFFFFFFF`；ECAM = `0xE0000000–0xEFFFFFFF`（紧邻其上） | 32 位窗口**无法向上扩张** |

> ⚠️ **这四条是"线索"（待追），不是"异常"（已认定）。**每条都**必须**同时列出替代解释，
> 且**不得**由一个奇怪的资源窗口直接跳到"需要新增 SSDT"。
> 尤其 **L1**：`plan.json` 里没有下游设备，**不等于**该端口没有设备、
> 不等于没有热插拔/空槽预留、也不等于一定异常 —— 完整的三分解读见 **§11.6**。

**（c）仍然缺少的关键数据（这正是下一轮该补的）**

`plan.json` **只有每个功能的"已分配窗口"**，**没有桥的寄存器级窗口定义**：

* 每个桥的 **Primary / Secondary / Subordinate Bus Number**；
* **Memory Base/Limit** 与 **Prefetchable Memory Base/Limit** 寄存器。

这三组值**只存在于 PCI 配置空间**，Windows 的 CIM/PnP 属性里拿不到（也不在 `plan.json` 里）。
没有它们就**无法**回答"某个桥的下级总线范围是否与另一个桥重叠"这类**枚举级**问题 ——
而这恰恰是 L1（`GP11` 有窗口无端点）最需要对照的东西。

### 10.3 关于"固件 ACPI / IRQ"

* **目前 IRQ 方向的证据是弱证据，不是否证**（用户 2026-10-13 修正措辞）：
  * 已有的**弱**论据：`IOPCIConfigurator::configure()` 负责的是**总线号 / 内存 / IO 的扫描与分配**，
    中断分配发生在**之后**（设备启动、`_PRT` / 链接设备生效时）。
    所以 HPET / PIC IRQ2 / RTC IRQ8 / TMR IRQ0 这类 **IRQ 补丁**，
    **先验上不太可能移动 `configure()` 的停点**。
  * ❗ **但不能宣布"IRQ 完全不可能有关"**：本机**没有** macOS 侧 `configure()` 内部的执行轨迹
    （`docs/06` §7），"中断分配发生在之后"是**对代码结构的解读**，不是对本机的观测；
    若停点其实在更早/更晚的相位，或存在 IRQ 与 MMIO 的耦合（如 MSI 使能顺序），
    该解读就不适用。
  * ⇒ 结论只到"**不作为优先试项**"，**不到**"已排除"。
    且用户已明确**禁止**套用 Acer 的 HPET/IRQ 补丁，所以这条路本轮**连只读材料都没有新增**。
* ① ACPI 侧可审计且**已知的两条事实**依然是：
  `GPP0`/`PEGP` **没有 `_CRS`**（dGPU 的窗口在 ACPI 里完全没有描述）；
  `_CRS` 的第二个 32-bit 窗口**取决于 `NRSV` RAM**（静态为 0）—— 都已在 `docs/06` §2.2 记录。
* ⇒ **ACPI/IRQ 方向目前没有可写手段**（要改就得加 SSDT / 打 ACPI 补丁，用户禁止），
  所以它只能作为**只读审计**继续，不能作为下一轮的写盘候选。
* 本轮**新增**了一条与 ACPI 有关的可核对事实（**总线号端点语义**），见 §10.5(3) 与 §11.9。

### 10.4 Round 8 候选（**已获批准并于本轮执行：Windows 侧只读采集，见 §11**）

> **用户 2026-10-13 批准：Round 8 = 零 EFI 改动的"PCI 桥资源与设备枚举"只读审计。**
> **本轮只做了 Windows 侧；Linux Live 侧只写预案（`docs/09`），未执行。**
> 下表的"做什么"保留为当时的预登记，实际执行与结果见 **§11**。

| 项 | 内容 |
|---|---|
| **目标** | 拿到**桥寄存器级**的窗口定义与总线号，判定 L1/L2/L3/L4 里哪一条构成**真实的不一致** |
| **做什么（只读）** | **① Windows 侧（零额外介质）**：对**所有** PCI 功能抓 `DEVPKEY_Device_BusNumber/DeviceNumber/FunctionNumber`、`DEVPKEY_Device_ProblemCode`、以及全部 `Win32_DeviceMemoryAddress` 区间（把 42 条 record 扩到"全部功能"）。**② Linux Live 侧（需一个 Live 介质，仍只读）**：`lspci -Dnnvv`（含桥的 Bus/Mem/Prefetch 寄存器译码）+ `lspci -xxxx -s <bdf>` 全配置空间 dump + `cat /proc/iomem`。**全程不执行任何 `setpci` 写操作** |
| **预登记判据** | (α) 若发现**桥总线范围重叠**／**桥窗口部分重叠**／**BAR 不属于任何父窗口**／**子桥 subordinate 越界** 之一 ⇒ **得到一个具体的、可定位的靶点**，下一轮才谈针对性修改；(β) 若全部干净 ⇒ **排除"桥资源/枚举"这一整类假设**（与 10.2(a) 的四条负结论合并，价值同样大） |
| **风险** | **EFI 风险为零**（不改配置、不写 U 盘）；Linux Live 路径需一个额外介质，且**不得**写入任何 PCI 配置寄存器、不得改 BIOS |
| **不能证明什么** | 仍然**看不到 macOS 的分配结果**（`docs/06` §7）；即使发现不一致，也**不能**直接断定它是 `configure()` 卡死的原因 |
| **回滚** | 不适用（无 EFI 改动） |

**次选（明确降级、需另行批准）**：以 Round 4 为基线的 8 GiB 测试
（`Booter.ResizeAppleGpuBars: 0 → -1`，`UEFI.ResizeGpuBars` 保持 `-1`）——
用户已指示**先不改**，故**本轮不批准**。

**本轮不批准**：Round 8 的 EFI 改动、8 GiB BAR 实验、BIOS 修改、ACPI 补丁、`MmioWhitelist` 修改。

---

### 10.5 §10 过度推断勘误（用户 2026-10-13 要求，逐条）

> 本节**保留 §10 原文**（历史语境），在下面逐条更正。**§10.2(a) 的表头已就地改写**，
> 这里的条目是同一件事的集中记录。

| # | §10 的过度推断 | 更正后的表述 | 更正依据 |
|---|---|---|---|
| **1** | "**没有任何**'真正的'资源冲突" | **只能说**：在 plan.json 的 42 条 record 里，**没有部分重叠**。这**不代表**"所有固件或 macOS 的 PCI 资源分配均无冲突" —— 该量程只覆盖**已分配且被记录**的窗口，且**完全不含 macOS 侧的分配** | §11.2 还证明"记录本身"曾经是**缺**的 |
| **2** | "32 位窗口**没有耗尽**（余 584 MiB）" | 总量有余量**不证明**不存在**碎片 / 对齐 / 单个桥窗口上限**问题。一个 8 MiB 的 BAR 仍然可能因为"必须 8 MiB 对齐且落在一个已占用的高位"而放不进去 | 分配器的行为在 Windows 侧不可见，在 macOS 侧完全不可观测 |
| **3** | "总线号**全部在 `0x00–0x100` 之内**" | ❗ **记法错误**：`0x100` **不是合法总线号**，**PCI 总线号上限是 `0xFF`**。本机 DSDT 的 `_CRS` 会**在运行时**把 WordBusNumber 模板改成 `_MIN=0x00`、`_LEN=0x0100`、`_MAX=0xFF`（= 256 条总线）⇒ 合法。**实测在用总线最大 `0x67`**，离上沿很远 | §10.5(3) 详解，见下 |
| **4** | "`GP11` 背后**没有任何设备**" | **只能**说：`plan.json` 与本轮 Windows 采集里**都没有** GP11 下游的设备。**不等于**该端口没有设备、**不等于**没有空槽/热插拔预留、**更不等于**一定异常。三种解读并列见 §11.6 | §11.3/§11.6 |
| **5** | "IRQ 路由**不可能**是本停点的原因" | 降级为：IRQ **目前是弱证据，不作为优先试项**；但**不能宣布 IRQ 完全不可能有关** —— 那是对代码结构的解读，不是对本机的观测 | §10.3 已改写 |
| **6** | 隐含"若 Windows/Linux 资源正常则问题在 OpenCore/macOS 侧" | ❗ 反过来同样成立：**Linux 资源正常也不能完全排除 macOS `IOPCIFamily` 自身的兼容性问题**。Windows/Linux 用的是各自的分配器与驱动，**没有一条证据能替代 macOS 侧读数** | `docs/06` §7（可观测性审计）|

#### 10.5(3) 总线号端点语义（逐行核对，①）

DSDT `\_SB.PCI0`：

| 对象 | 值 | 位置 |
|---|---|---|
| `Name (BRB, 0x0000)` | 总线基址 | `dsdt.dsl:2243` |
| `Name (BRL, 0x0100)` | 总线**长度**（= 256 条） | `dsdt.dsl:2244` |
| `CRS1` 静态 `WordBusNumber _Y01` | Min `0x0000` / Max `0x007F` / Len `0x0080` | `dsdt.dsl:2279-2285` |
| `CRS2` 静态 `WordBusNumber _Y0A` | Min `0x0080` / Max `0x00FF` / Len `0x0080` | `dsdt.dsl:2372-2378` |
| `_CRS` 运行时改写（两个分支都一样） | `MIN0 = BRB`；`LEN0 = BRL`；`MAX0 = MIN0 + Local0--` | `dsdt.dsl:2435-2438`（CRS1）/ `:2589-2592`（CRS2） |

**关键**：`Local0 = LEN0` 是**复制**，`Local0--` **只递减 `Local0`，`_LEN0` 始终保持 `0x0100`**。
于是描述符必须满足固件自己在别处反复使用的约定 **`_LEN = _MAX - _MIN + 1`**
（两个静态模板都精确满足：`0x7F-0x00+1 = 0x80`、`0xFF-0x80+1 = 0x80`；
I/O 分支甚至显式写了 `LEN1 = (MAX1 - MIN1) + One`，见 `:2446-2447`）：

* ⇒ `_MAX = _MIN + _LEN - 1 = 0x0000 + 0x0100 - 1 = **0xFF**`
* ⇒ 运行时总线范围 = **`0x00–0xFF`（256 条）**，**合法**。
* 另一种读法（若把 `Local0--` 当成"先取值后递减"）会得到 `_MAX = 0x100` —— 那既是**非法总线号**，
  又**同时违反**上述约定，而同一文件里两个静态模板都严格遵守该约定 ⇒ **取 `0xFF` 这个读法**。
* **无论取哪种读法，实测在用的最大总线号都是 `0x67`（103），差异不落在任何观测点上。**
* ⇒ 原文档里的 "`0x00–0x100`" 是**把 `BRL`（长度）误当成了 `_MAX`（上界）**。

#### 10.5(4) 关于"脚本只在本地"

用户问：`audit/pci-resource-audit.py` 是否只保存在本地？—— **是，此前确实只在本地**
（`docs/06` §993 曾明文规定 `audit/*.py` **未入库**）。本轮按用户授权**收窄该禁令**：

* **新入库**（可复现 + 已脱敏检查）：
  * `audit/pci-resource-audit.py` —— 路径改为命令行参数，不再硬编码本机绝对路径；
  * `audit/pci-windows-audit.py` —— 本轮新增的 Windows 侧只读审计；
  * `audit/results/pci-resource-plan-2026-10-13.txt`（上者的原始输出）；
  * `audit/results/pci-windows-2026-10-13.{md,json}`（后者的输出，已脱敏）。
* **仍然严禁入库**（不变）：`audit/acpi/**`（含 `MSDM` 的 OEM 密钥）、`audit/iopicifamily/**`、
  `audit/voodooi2c-src/**`、屏幕照片、任何 `.aml` / `.bin` / `.efi` / `.dmg`，
  以及本轮产生的**原始** `pnputil-all.xml`（3.2 MB，含 ContainerId / 安装日期等机器标识）。
  详见 `audit/README.md`。

---

## 11. Round 8：Windows 侧 PCI 拓扑与资源只读审计（**已执行，零 EFI 改动**）

> **用户 2026-10-13 批准。本轮不改 EFI、不写 U 盘、不改 BIOS、不加 SSDT、不动 `MmioWhitelist`。**
> 采集与解析脚本：`audit/pci-windows-audit.py`（入库）。
> 归档结果：`audit/results/pci-windows-2026-10-13.md` / `.json`（已脱敏）。

### 11.1 两个数据源（都只读，都是 Windows）

| 源 | 取法 | 性质 |
|---|---|---|
| **P1** | `pnputil /enum-devices /connected /deviceids /relations /location /properties /resources /format xml` | PnP 枚举（**无需管理员**，零额外介质） |
| **P2** | `1401/plan.json` 的 `capture.device_map.pci_resources` | **CfgMgr32 `CM_Get_First_Log_Conf(ALLOC_LOG_CONF)` + `CM_Get_Res_Des_Data`**（"已分配逻辑配置"） |

两者都是**同一次开机**的 Windows 侧快照：
在有窗口的 **24 个设备**里，**21 个**的窗口集合与 P1 **逐位相同**，
剩下 **3 个**的差异**全部单向**（只在 P2 里有）且**恰好**是 §11.2 那一类 ⇒ 可以合并使用。
**两者都不是寄存器转储，也都不是 macOS 的分配结果。**

**必须点名的失败尝试（已登记，不猜）**：本轮试图直接调用 CfgMgr32 的
`CM_Get_First_Res_Des` 走完"第一个资源描述符"这一步 ——
**该导出在本机 `cfgmgr32.dll` 上不存在**（字符串扫描 `System32` 下全部 DLL：**0 命中**），
改为给 `CM_Get_Next_Res_Des` 传 `NULL` 当前句柄时返回 **`CR_INVALID_FLAG (4)`**。
⇒ 这条路**本机走不通**，于是改用 P2（1401 已经用同一族 API 采到的数据），
并把它标注为**单一来源**。

### 11.2 本轮最重要的方法论结果：**`pnputil /resources` 会静默丢掉 ≥4 GiB 的窗口**

对照 P1 与 P2，**只有 3 个设备的窗口集合不同，且差异全部是"只在 P2 里有"**：

| BDF | 只在 P2（CfgMgr32）中出现的窗口 | 长度 | 该设备扮演的角色 |
|---|---|---|---|
| `00:01.1`（GPP0，dGPU 的父桥） | `0x7C00000000 – 0x7E01FFFFFF` | 8623489024 B（**8 GiB + 32 MiB**） | dGPU 的 64 位可预取窗口 |
| `00:03.1`（GP11） | `0x6C00000000 – 0x7BFFFFFFFF` | 68719476736 B（**64 GiB**） | 空端口的大预留窗口 |
| `01:00.0`（RTX 4050） | `0x7C00000000 – 0x7DFFFFFFFF` | 8589934592 B（**8 GiB = BAR1**） | **dGPU 的 BAR1 本身** |

**反向差异 = 0**。三条被丢掉的窗口**长度都 ≥ 4 GiB**（最小 8589934592）。

* 判据：`CmResourceTypeMemoryLarge` 正是"长度放不进 32 位 `Length` 字段"的描述符；
  P1（`pnputil /resources`）**不打印这一类**。
* ⇒ **凡是用 P1 单独做的"无重叠 / 都在声明范围内"结论，对"大窗口"这一类是不成立的** ——
  而本机**恰好**是这些大窗口最有意思。
* ⇒ 本节所有后续检查都在 **`P1 ∪ P2` 的合并窗口集**上做。
* 另：**PCI0 根总线（`ACPI\PNP0A08`）的 64 位窗口 `0x460000000–0x7FFFFFFFFF`（494 GiB）
  在 P1 和 P2 里都没有记录** —— P2 只登记 PCI 功能，不含 ACPI 根总线。
  ⇒ "根总线 64 位窗口"仍然**只有 DSDT 一个来源**。
* ⚠️ 这条本身也是**本轮才被发现**的：`docs/08` §10 的结论当时基于 P2（完整），
  但**今天先用 P1 做的包含性检查曾产出一个假阳性**（"dGPU 的 64 位窗口不在父桥窗口内"）
  —— 该假阳性**已被 §11.5 的合并检查推翻**，原因是 P1 缺了父桥的那条 8 GiB 窗口。

### 11.3 采集到的拓扑（① P1，逐条可复现）

**42 个 PCI 功能 / 8 个 PCI-to-PCI 桥。**桥的从属关系与 ACPI 名字（P1 的 `LocationPaths` 同时给出
**PCI 路径与 ACPI 路径**，这是本轮比预期更好的一点）：

| 桥 BDF | 设备 | ACPI | 子设备总线（**派生**） | 子设备 |
|---|---|---|---|---|
| `00:01.1` | `1022:14ED` | `GPP0` | 1 | `01:00.0`（RTX 4050）、`01:00.1`（HDMI HDA） |
| `00:02.1` | `1022:14EE` | `GPP5` | 2 | `02:00.0`（Realtek 读卡器 `10EC:525A`） |
| `00:02.2` | `1022:14EE` | `GPP6` | 3 | `03:00.0`（**MT7922** `14C3:0616`） |
| `00:02.4` | `1022:14EE` | `GPP8` | 4 | `04:00.0`（Sandisk NVMe `15B7:5017`） |
| `00:03.1` | `1022:14EF` | `GP11` | **无** | **（无）** |
| `00:08.1` | `1022:14EB` | `GP17` | **0x65=101** | `65:00.0`（**780M** `1002:1900`）、`.1` HDA、`.2` PSP、`.3/.4` xHCI、`.5` ACP、`.6` AZAL |
| `00:08.2` | `1022:14EB` | `GP18` | **0x66=102** | `66:00.0`、`66:00.1`（**NPU `1022:1502`**，Windows 报 `ComputeAccelerator`） |
| `00:08.3` | `1022:14EB` | `GP19` | **0x67=103** | `67:00.0`、`.3/.4` xHCI、`.5`（`1022:1668` USB4） |

* 另有一族 `00:01.0 / 00:02.0 / 00:03.0 / 00:04.0 / 00:08.0`（全部 `1022:14EA`，class `System`）
  —— **无窗口、无子设备、也不是桥**（只有功能 1 才是根端口桥）。
* `00:18.0–00:18.7` = `1022:14F0–14F7`（data fabric），`00:14.0/14.3` = FCH，均无窗口。
* **`DEVPKEY_Device_DeviceNumber` / `DEVPKEY_Device_FunctionNumber` 在本机上不存在**
  （用户预先警告过）—— 枚举**全部**属性键后确认：只有 `DEVPKEY_Device_BusNumber` 与
  `DEVPKEY_Device_Address`。
  BDF 由**四个独立来源**交叉核对：`BusNumber`、`Address`（高/低 16 位 = 设备/功能）、
  `LocationPaths`（`PCIROOT(0)#PCI(0101)#PCI(0000)`）、`LocationInfo`（本地化字符串里的三个整数）。
  **不一致数 = 0**（见 `audit/results/pci-windows-2026-10-13.md` §7）。
  ⇒ 本节的 BDF 是本节最硬的数据。

### 11.4 桥的窗口（合并视图，含可预取标志）

| 桥 | 32 位窗口 | 64 位窗口 | IO | 可预取 |
|---|---|---|---|---|
| `00:01.1` GPP0 | `DC000000–DD0FFFFF`（17 MiB） | **`7C00000000–7E01FFFFFF`（8 GiB + 32 MiB）** | `F000–FFFF` | 64 位那条 **是**（flags `0x47`） |
| `00:02.1` GPP5 | `DDF00000–DDFFFFFF` | — | — | — |
| `00:02.2` GPP6 | `DDB00000–DDCFFFFF` | `7FFFF00000–7FFFFFFFFF`（1 MiB） | — | 是（`0x47`） |
| `00:02.4` GPP8 | `DDE00000–DDEFFFFF` | — | — | — |
| `00:03.1` GP11 | **`C4000000–DBFFFFFF`（384 MiB）** | **`6C00000000–7BFFFFFFFF`（64 GiB）** | `A000–DFFF`（16 KiB） | 64 位那条 **是**（`0x47`）；32 位那条**否**（`0x43`） |
| `00:08.1` GP17 | `DD200000–DD7FFFFF`（6 MiB） | `7E10000000–7E207FFFFF`（264 MiB） | `E000–EFFF` | 是 |
| `00:08.2` GP18 | `DDD00000–DDDFFFFF` | `7E20900000–7E209FFFFF`（1 MiB） | — | 是 |
| `00:08.3` GP19 | `DD800000–DDAFFFFF` | — | — | — |

**GPP0 的 64 位窗口 = `0x7C00000000–0x7E01FFFFFF`，恰好等于"BAR1(8 GiB) ∪ BAR3(32 MiB)"，
余量为 0。** 这是一条**具体**的事实，对"能不能让 BAR 变大"直接相关
（缩小安全，变大一定越界）。

### 11.5 检查结果（**全部在合并窗口集上**）

| 检查 | 结果 |
|---|---|
| 子设备窗口不被任何父桥窗口包含 | **0 例**（用 P1 单独做时曾出现 1 例假阳性，见 §11.2） |
| 窗口落在 DSDT 声明的 PCI0 窗口之外 | **0 例** |
| 内存窗口两两相交 | 26 对，**全部是包含关系**；**部分重叠 = 0** |
| 在用的 PCI 总线号 | `0x00,0x01,0x02,0x03,0x04,0x65,0x66,0x67` —— **最大 `0x67`**，**超 `0xFF` 的 0 个** |
| 8 个桥的"派生"次级总线 | `1,2,3,4,101,102,103` + GP11 未知 —— **互不重复、无嵌套**（全部单层星形） |
| BDF 四来源不一致 | **0** |

⇒ 按 §10.4 的**预登记判据 (β)**：**"桥总线范围重叠 / 桥窗口部分重叠 / BAR 不属于任何父窗口 /
子桥 subordinate 越界"四项一个都没出现** ⇒
**Windows 侧没有给出任何"资源/枚举不一致"的靶点**。
（**这不等于** macOS 侧也没问题 —— 见 §11.10。）

### 11.6 L1–L4 复核：每条线索的**原始证据 + 替代解释**

**L1 —— `GP11`（`00:03.1`）持有超大窗口但下游没有设备**

* 原始证据（① P1）：`00:03.1` = `1022:14EF`，class `CC_060400`（PCI-to-PCI 桥），
  `DEVPKEY_PciDevice_DeviceType = 0x8`（PCI Express 根端口），
  `LocationPaths = PCIROOT(0)#PCI(0301)` + `ACPI(_SB_)#ACPI(PCI0)#ACPI(GP11)`，
  **子设备数 = 0**，`ProblemCode = 0`。
* 原始证据（② P2，**单一来源**）：窗口 `C4000000–DBFFFFFF`（384 MiB，非可预取）
  + `6C00000000–7BFFFFFFFF`（64 GiB，**可预取**，`MemoryLarge` 描述符）+ IO `A000–DFFF`
  + IRQ 伪向量 `-52`（`0xFFFFFFCC`）。
* 原始证据（① DSDT）：`Device (GP11) { Name (_ADR, 0x00030001); Method (_PRT) {...};
  Device (D01B) { Name (_ADR, 0xFF) } }` —— **没有 `_CRS`**；子节点是一个
  `_ADR = 0xFF` 的**永不匹配的占位**（Insyde 的模板写法）。
  并且 DSDT **同时**声明了 `GP12`（`_ADR 0x00040001`，`dsdt.dsl:2983`），
  而 **`00:04.1` 在硬件上根本不存在**。
* ⚠️ **"没有设备"的三种替代解释（并列，不选边）**：
  1. **空槽/未装配的端口**：本 SKU 该端口没有装设备（第二 M.2 槽、或另一个 dGPU/独显走线），
     固件**仍然**按 DSDT 给启用中的桥分配了窗口 —— **完全正常**。
     （旁证：DSDT 声明了比硬件实际存在的更多的根端口，见上。）
  2. **固件过分配**：固件为"可能的扩展"预留了 64 GiB 的**可预取**窗口，Windows 只是**接受**了它，
     `pci.sys` 没有做重新平衡。
  3. **真的异常**（例如桥被错误使能/上电，或与之相连的器件不上报）—— **本轮没有拿到支持它的证据**。
* ⇒ **不能**据此要求新增 SSDT。**下一步该看的**见 §11.9。

**L2 —— DSDT 64 位窗口基址 `0x460000000` 同时是固件运行期 MMIO**

* 原始证据：DSDT `MAB = 0x460000000`；OpenCore 日志的 MMIO devirt #4 = `0x460000000` + `0x20200` 页；
  而最低的 64 位**分配**是 `0x6C00000000`（GP11）。
* **替代解释**：`_CRS` 声明的是"**可用区间**"，固件从**低端**开始保留了自己的运行期区域，
  于是实际分配从更高的地址开始 —— 这**正是**"窗口基址被保留区占用"的正常表现，
  **不构成冲突**（本轮 §11.5 的越界检查 = 0 也支持这一点）。
* ⇒ 仍是"值得看一眼"，但**不是**不一致。

**L3 —— WiFi 的 64 位 BAR 顶到 `MAM`**

* 原始证据：MT7922（`14C3:0616`，bus 3）与其父桥 GPP6 都在 `7FFFF00000–7FFFFFFFFF`，
  `MAM = 0x7FFFFFFFFF`；长度仅 1 MiB。
* **替代解释**：向下分配（descending allocation）是固件的常见策略，**从窗口顶端开始放**
  是**预期行为**，不是"顶死"。
* ⇒ 措辞从"上沿无余量"改为"**这一块**贴着上沿；上沿**整体**没有余量，但**整体** 494 GiB
  窗口里只用了约 80 GiB，**没有证据表明剩余空间不够**"。

**L4 —— 32 位窗口上沿被 ECAM 顶死**

* 原始证据：32 位窗口上界 `0xDFFFFFFF`，ECAM `0xE0000000–0xEFFFFFFF` 紧邻其上
  （P1 里 `ACPI\PNP0A08` 的 memory 列表确实含 `0xA0000000–0xDFFFFFFF`）。
* **替代解释**：32 位窗口**本来**就不需要向上长 —— 任何 >4 GiB 的需求都去 64 位窗口。
  本轮实测 32 位窗口**只用掉 440 MiB / 1024 MiB**。
* ⇒ 这是**布局事实**，不是**资源不足的证据**。

### 11.7 Windows 侧**登记缺口**（明确"取不到"，不猜）

| 想拿的东西 | 能否拿到 | 为什么 / 试过什么 |
|---|---|---|
| 桥的 **Primary/Secondary/Subordinate 总线号寄存器** | ❌ | 不是设备属性；`DEVPKEY_Device_DeviceNumber/FunctionNumber` **本机不存在**；`CM_Get_First_Res_Des` **本机 DLL 未导出**，`CM_Get_Next_Res_Des(NULL,…)` 返回 `CR_INVALID_FLAG(4)`。只能**派生**：primary = 桥自己的 `BusNumber`；secondary/subordinate = 从其**已枚举子设备**的总线推。**派生值区分不了"桥声明的范围比它用的宽"**；无子设备的桥 = **未知**（不是"空"）|
| 桥的 **Memory / Prefetchable Base·Limit 寄存器** | ⚠️ 只有代理 | 配置空间不可读；P2 的窗口记录是 `pci.sys` **按这些寄存器算出来的结果**，且**带可预取位**（`0x04`）。但它是**解码结果**，不是寄存器：**固件从未分配的窗口无法从它反推**，寄存器的**对齐/粒度**位不可见 |
| **PCI Command (0x04) / Status (0x06)** | ❌ | 无属性暴露；只有 `DEVPKEY_PciDevice_*` 能力位（已全部采集） |
| 每个 **BAR 的原始内容与 size 编码** | ⚠️ 只有代理 | 只有 base+length；**不给 BAR 序号**；`DEVPKEY_PciDevice_BarTypes` 给类型位 |
| 桥的**需求清单**（干净重枚举时它会申请什么） | ❌ | Windows 只报"它分配/接受了什么"；需求侧的 `CM_Get_First_Res_Des` 本机不可用 |
| 一个**未识别的 Binary 设备属性** `{f0e20f09-d97a-49a9-8046-bb6e22e6bb2e}[2]`（33 个设备有） | ❌ | 已按字节转储（96/184/360/1504 B）。它**确实**含中断伪向量（GPP0 偏移 64 = `0xFFFFFFFE` = `-2`，与 P2 的 irq 记录一致）与 `0xFEE00000`（Local APIC）；但**不含**桥的 64 位窗口。**未识别 ⇒ 本文件任何地方都不把它当证据** |
| **macOS 自己的 PCI 资源分配** | ❌ | 本机 macOS 从未到达可读取的用户态（`docs/06` §7） |

⇒ 按 §10.4 预登记：**"桥总线范围是否重叠"这个问题，Windows 侧答不了**；
而"桥窗口 / BAR 归属"这一问题，**Windows 侧给了明确的否定答案**（§11.5）。

### 11.8 是否需要 Linux Live？

* **结论：目前不需要为"资源冲突"问题去用 Linux** —— §11.5 的四项预登记判据在 Windows 侧
  已经是 (β)（全部干净）。
* **Linux 能补上而 Windows 补不上的，只有两件**（都写在 `docs/09`）：
  1. 桥的**寄存器原值**（Primary/Secondary/Subordinate、Mem/Prefetch Base·Limit，
     含 **prefetchable 那一对**）—— `lspci -vv` 直接译码；
  2. 一份**独立内核**（非 Windows、非 macOS）对同一硬件的分配结论，用来把
     "Windows 侧干净"与"硬件/固件本身干净"分开。
* **若要用，必须**：从**固件启动菜单**直接引导，**不经过 OpenCore**
  （避免 Round 7 的 `UEFI.ResizeGpuBars` 影响基线）；
  **禁止** `setpci` 写、设备复位、驱动解绑、`pci=realloc` 之类的重分配试验。
  完整步骤、预登记判据与风险见 **`docs/09`**。

### 11.9 GP11 / GPP0 / GP17 的下一步检查重点（**只读，未执行**）

| 对象 | 该看什么 | 为什么 | 需要什么 |
|---|---|---|---|
| **GP11**（`00:03.1`） | ① **它的 Secondary/Subordinate 寄存器**到底写了什么（`04:00.0`？还是子总线根本没使能）；② **Link Status / Slot Capabilities**：链路是否 train、是否有卡存在（Presence Detect）、是否热插拔槽；③ 该桥的 **Clock/PM 与 `_STA`** 相关 DSDT 路径 | 只有这三样能把 §11.6 的三种解释**分开**：空槽 vs 过分配 vs 真异常 | Linux `lspci -vv -s 00:03.1`（含 `Bus: primary=00, secondary=.., subordinate=..`、`LnkSta`、`Slot`）；**Windows 侧无解** |
| **GPP0**（`00:01.1`） | ① prefetchable 窗口是否**恰好**等于"BAR1 ∪ BAR3"（本轮：**是，余量 0**）；② 若将来做 8 GiB 实验，**桥窗口不会跟着变大** ⇒ 只能"缩小安全、变大必失败" | 直接决定"BAR 尺寸"这一类实验的**上界** | 已有（本轮结论）；Linux 可用 `lspci -vv` 复核寄存器原值 |
| **GP17**（`00:08.1`） | ① 264 MiB 的可预取窗口里，780M 的 256 MiB BAR 与 ACP 的 8 MiB 如何切分；② 32 位那 6 MiB 的用途（`DD200000–DD7FFFFF` 被 7 个功能瓜分） | 核显是**唯一**在 macOS 下需要工作的显示通路；它所在桥的资源形状直接决定 iGPU 能否被正常枚举 | 已有（本轮）；如需寄存器原值同 GP11 |

### 11.10 本轮**不能**证明什么（必须保留的限制）

1. **仍然看不到 macOS 的分配结果**（`docs/06` §7）。§11.5 的"全部干净"是
   **Windows 侧**的分配，**不是** macOS `IOPCIFamily` 的分配。
2. **Linux/Windows 资源正常，不能完全排除 macOS `IOPCIFamily` 自身的兼容性问题**
   （用户 2026-10-13 第 6 条）。
3. **"没有部分重叠"不等于"macOS 不会遇到碎片/对齐/桥窗口上限问题"**（第 2 条）。
4. **GP11 的 64 GiB 窗口只有 P2 一个来源**（P1 会丢它）⇒ 证据等级 ②，不是 ①。
5. **两个源都是同一次开机的 Windows 快照**；固件/Windows 的分配**可能跨开机不同**，
   本轮**没有**做多次开机的稳定性对照。
6. **GP11 的三种解读本轮无法判定**（§11.6）—— 本轮**不**提议任何 SSDT/ACPI 修改。
7. **停点性质未变**：Round 7 的 `PCI configuration begin / configure() PCI0` 停点
   与本节结论**没有建立因果**；本节只是**排除了一整类假设的一个子集**。
