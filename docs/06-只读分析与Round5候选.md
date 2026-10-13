# 06 · 只读分析与 Round 5 候选

> 本文件对应一次**只读**作业：核对 Round 4 引导结果 → 只读检查 ACPI/PCI → 复核上游案例 →
> 给出 Round 5 候选（**只给 diff，不写入 U 盘**）。
>
> **本轮没有改任何东西**：U 盘、BIOS、Windows EFI、分区、`config.plist` 全部未动。
> 唯一新增的写入是**本仓库的文档与日志**（见 §6）。

> **初版勘误（同一次作业内自查更正，留档）**
>
> 1. `_CRS` 的第二个 32-bit 窗口：初版写成 `0xFEE00000 + 0x1200000 = 0xFEE00000–0xFEF1FFFF`。
>    **算术与控制流都错**（`+0x1200000` 会进位到 `0x1_0000_0000`；且 `NBTP=0xFEC00000` 使
>    `:2537` 成立、`:2561` 分支不可达、静态结果为 `LEN7=0`）。已按 §2.2 重写。
> 2. `NBTP`/`NBTS`：初版写成"静态未找到定义"。**错** —— 它们是
>    `dsdt.dsl:292 Name (NBTP, 0xFEC00000)` 与 `:237 Name (NBTS, 0x5000)`。已按 §2.2 / §2.7 更正。
> 3. 五块 MMIO 的来源：初版按"ACPI 对象"叙述。**错** —— 它们是
>    `EFI memory map` 里 `Type==EfiMemoryMappedIO && EFI_MEMORY_RUNTIME` 的描述符
>    （`ServiceOverrides.master.c:281-310`），ACPI 只能解释。已按 §2.5 重写。
> 4. ACPI 错误串 `[_SBW]` → **`[_S0W]`**（见 §2.4）。

---

## 1. Round 4 引导结果核对（第一阶段）

### 1.1 六项必须验证项 —— 全部通过

数据源：`logs/opencore-2026-10-13-095517.txt`（卡上 `D:\opencore-2026-10-13-095517.txt`，
262144 B，**首字节 0 偏移 = 68181**，即日志**未被写满/截断**，747 行，末行
`12:577 AAPL: #[EB|LOG:EXITBS:START]`）。

| # | 验证项 | 期望 | 实测 | 结论 |
|---|---|---|---|---|
| 1 | `WRUNPROT` | `0` | `OCABC: ALRBL 1 RTDFRG 1 DEVMMIO 1 NOSU 0 NOVRWR 1 NOSB 0 FBSIG 0 NOHBMAP 0 SMSLIDE 1 WRUNPROT 0 CLRTS 0` | ✅ |
| 2 | `RBMAP` | `1` | `OCABC: FEXITBS 0 PRMRG 0 CSLIDE 1 MSLIDE 0 PRSRV 0 RBMAP 1 VMAP 1 APPLOS 0 RTPERMS 1 ARBAR 0 RBIO 0` | ✅ |
| 3 | `RTPERMS` | `1` | 同上 | ✅ |
| 4 | `DEVMMIO` | `1` | 见 #1 行 | ✅ |
| 5 | `VMAP` | `1` | 见 #2 行；且 `MAT support is 1` | ✅ |
| 6 | `MBA:OUT` 无 `npci` | 无 | 全文件 `npci` 出现 **0 次**；`MBA:NV` 与 `MBA:OUT` 逐字相同（只多 `slide=219`） | ✅ |
| 7 | VoodooI2C 四项仍禁用 | 四个 BundlePath 均不出现 | 26 条 `Kernel.Add` 中 21 条注入；日志里**只有** `VoodooI2C.kext\Contents\PlugIns\VoodooInput.kext`（有意保留的那一份 VoodooInput）、`VoodooPS2Controller.kext`（+3 个 PlugIns），**没有** `VoodooI2C.kext` / `VoodooI2CHID.kext` / `VoodooI2CServices.kext` / `VoodooGPIO.kext` 作为独立条目 | ✅ |

> 备注：`OC: Not deleting NVRAM …:boot-args, matches add` + `OCVAR: Setting NVRAM …:boot-args - ignored, exists`
> 是**预期**行为——固件里那份变量已经等于我们 `Add` 的内容（Round 3 已成功写入并持久化），
> OpenCore 的 `OcDeleteNvram` 对"内容与 Add 相同"的变量有**免擦写保护**。这不是失败。

### 1.2 关键新对照：**Round 2 与 Round 4 停在同一点**

我们把历史照片重新裁切放大后逐行核对（`shots/r1_bottom.jpg`、`shots/r2_bottom.jpg`）：

| 轮次 | `npci=0x2000`（在 `MBA:OUT` 里） | `WRUNPROT/RBMAP/RTPERMS` | 屏幕最后可见的两行 |
|---|---|---|---|
| **Round 2**（`020808`，照片 `IMG20261013020953.jpg`） | **有**（实测 `MBA:OUT` 含 `npci=0x2000 slide=244`） | `1 / 0 / 0` | `[ PCI configuration begin ]` + `[IOPCIConfigurator::configure()] PCI configuration PCI0` |
| **Round 4**（`095517`） | **无** | `0 / 1 / 1` | **完全相同** |

**这是本机第一次出现"同一停点、两个变量都无影响"的对照。** 由此可确认：

1. 在**这个**停点上，`npci=0x2000` **不足**（它当时确实进了内核并出现在 `MBA:OUT` 里）；
2. 在**这个**停点上，MAT 三件套（`WRUNPROT=0/RBMAP=1/RTPERMS=1`）**也没有移动停点**。

> 措辞约束：这两条**只**说明"该变量在此停点不足以解决问题"，**不能**排除它们的其它作用，
> 也**不能**据此锁定任何子系统。与 §7.6 B 的口径一致。

### 1.3 对 Round 3 "在 `RTC:` 停留 ≥10 分钟" 的修正

- Round 2 的照片证明：**同一次启动里 `RTC: Only single RAM bank (128 bytes)` 之后还有大量输出**
  （`AppleCredentialManager`、`AppleKeyStore`、`AppleSSE`、`CoreAnalyticsHub`、5×`AppleVTD addMemoryRange`
  ……直到 `PCI configuration begin`）。
- Round 4（**无** `npci`）已经走到了 `PCI configuration begin`。
- ⇒ Round 3 与 Round 2 的唯一差异是移除 `npci`，而 Round 4 在**同样没有 `npci`** 的情况下越过了 `RTC:`。
  **"移除 npci 使其停在 RTC" 被 Round 4 证伪**；Round 3 的 `RTC:` 停留最可能是**观察窗口不足**
  （该行之后有一段长静默），而非独立的死锁点。

### 1.4 屏幕停点的**结构性**解释 —— 为什么四轮最后一行都长这样

这一条是本轮最重要的方法论修正。读 `IOPCIConfigurator.cpp`：

```cpp
3306: void CLASS::configure(uint32_t options)
3308:     bool bootConfig = (kIOPCIConfiguratorBoot & options);
3310:     if (bootConfig) IOLog("[ PCI configuration begin ]\n");
...
3321:     IOLog("[IOPCIConfigurator::%s()] PCI configuration %s\n", __func__, fRoot->child->dtNub->getName());
3328:     if (bootConfig) {
3330:         IOService::getPlatform()->getConsoleInfo(&consoleInfo);
...
3342:         getPlatform()->setConsoleInfo(0, kPEDisableScreen);   // <<<< 屏幕在这里被关掉
3343:     }
3346:     doConfigure(options);                                     // <<<< 四遍 iterate，全程静默
...
3377:     if (bootConfig) { ... getPlatform()->setConsoleInfo(NULL, kPEEnableScreen); ... }
3379:         IOLog("console relocated to 0x%llx\n", fPFMConsole);
3388:     if (bootConfig) IOLog("[ PCI configuration end, bridges %d, devices %d ]\n", fBridgeCount, fDeviceCount);
```

结论：

* `[ PCI configuration begin ]` 与 `[IOPCIConfigurator::configure()] PCI configuration PCI0` 是
  **`doConfigure()` 之前**打印的最后两行；之后 PE 屏幕被**主动关闭**，`doConfigure()` 期间的任何
  `IOLog` 都**不会上屏**（真机上也一样，所以正常机器上这两行与 `PCI configuration end` 是紧挨着的）。
* 因此 **"屏幕停在这两行" 等价于 "`doConfigure()` 没有返回"**，而不是"停在第 3321 行的某条指令"。
  `doConfigure()` 内部是四遍 `iterate`：
  ```cpp
  3210: if (bootConfig) iterate("boot reset", &CLASS::scanProc, &CLASS::bootResetProc, this);
  3211:                iterate("scan total", &CLASS::scanProc, &CLASS::totalProc, NULL);
  3212:                iterate("allocate",   &CLASS::allocateProc, NULL, NULL);
  3213:                iterate("finalize",   &CLASS::bridgeFinalizeConfigProc, &CLASS::domainFinalizeConfigProc, NULL);
  ```
* **只凭屏幕无法知道挂在四遍中的哪一遍、也不知道挂在哪个设备上** —— 这正是第四阶段候选 A 要解决的问题。
* 判定 `doConfigure()` 确实没有返回，仍需**停留时长**：`PCI configuration end` 那一行会在屏幕重新开启
  **之后**打印，所以"等了 N 分钟没有出现 `PCI configuration end`"就是死锁的直接证据。
  **Round 4 没有停留时长证据 → 本节结论按"待补时长"处理，本文件不代填。**

### 1.5 照片状态（**必须如实说明**）

* **Round 4 的屏幕照片不在本机、也不在本会话中。** 已检索
  `Downloads / Pictures / Desktop / Documents / %TEMP% / %APPDATA% / .dsh\attachments`，
  09:00 之后**没有任何**新增图片文件；`.dsh\attachments` 里只有本次分析自己生成的裁切图。
* 因此 Round 4 的屏幕内容在本文件中**只记为"用户口述"**，不作为照片证据：
  > 口述（原话大意）：同一次启动先出现 `RTC: Only single RAM bank (128 bytes)`，继续出现
  > `AppleCredentialManager`、`AppleKeyStore`、`CoreAnalyticsHub` 等，最后停在
  > `PCI configuration begin` / `IOPCIConfigurator::configure() PCI configuration PCI0`。
* 已核对**确实存在**的历史照片（用于 §1.2 的对照）：`IMG20261013011501.jpg`（Round 1 引导）、
  `IMG20261013020953.jpg`（Round 2 引导）、`IMG20261013001447.jpg`（`001004` 引导）；
  裁切件在 `shots/`。
* **发布照片的注意事项**：屏幕照片可能包含 ACPI 表清单、device path 等；本项目**不把屏幕照片入库**
  （现有 `shots/` 只在本机，未发布）。若要把 Round 4 照片留档，建议先按 `scripts/scrub-log.py`
  的同一标准人工过一遍，或只留裁切后的纯 ACPI/PCI 片段。

---

## 2. 只读 ACPI/PCI 分析（第二阶段）

### 2.1 本轮新增的只读转储（**不入库**）

用 1401 自带的 `acpidump.exe -b -z`（Intel ACPICA 20241212）把本机**全部 43 张固件 ACPI 表**导到
`audit/acpi/firmware/*.dat`，再用 `iasl` 反编译成 `audit/acpi/firmware/dsl/*.dsl`（46 个文件）。
这些是**只读**操作（不触碰硬件状态），但产物**不能入库**（`MSDM` 表含 Windows OEM 密钥，
且 `sync-to-github.ps1` 明确禁止 `*.aml`/`*.bin`）。它们只用于本文件的证据。

关键表 ↔ 日志索引的对应（按 XSDT 顺序）：

| XSDT idx | OemTableId | 大小 | 说明 |
|---|---|---|---|
| 0 | `Notebook` | 77592 | **DSDT**（`_SB.PCI0` 在这里） |
| 2 | `AmdTable` | 33814 | AMD 平台主 SSDT |
| 3 | `CPUSSDT` | 545 | **固件的 CPU 对象在这里**（见 §2.3） |
| 11 | `AmdTable` | 21630 | AMD 第二个 SSDT |
| 23 | `CPMCMN` | 39170 | 29 处 `_OSI→XOSI` 命中的那张 |
| 40 | `WLAN` | 2859 | **第 1 个失败表**（§2.4） |
| 42 | `GpMsSsdt` | 2729 | **第 2 个失败表**（§2.4） |
| 44 | `DNET` | 212 | 本项目注入的 `SSDT-Disable_Network_GPP6`（**第 3 个失败表**） |
| 46 | `CpuPlugA` | 1096 | 本项目注入的 `SSDT-PLUG-ALT`（**没有**失败） |

### 2.2 `\_SB.PCI0` 的 `_CRS` / `_OSC`（问题 1）

`dsdt.dsl:2182` `Device (PCI0)`：

```asl
2184:  Name (_HID, EisaId ("PNP0A08"))   // PCI Express Bus
2185:  Name (_CID, EisaId ("PNP0A03"))   // PCI Bus
2186:  Name (_ADR, Zero)
2192:  Method (_BBN) { Return (BN00()) }  // BN00() → Zero
2197:  Name (_UID, Zero)
2240:  Name (CPRB, One)        // ← 决定 _CRS 走 CRS1 分支
2242:  Name (STAV, 0x0F)      // _STA
2249:  Name (MAB, 0x0000000460000000)
2250:  Name (MAL, 0x0000007BA0000000)
2251:  Name (MAM, 0x0000007FFFFFFFFF)
2422:  Method (_STA)  { Return (STAV) }
2427:  Method (_CRS, 0, Serialized)
2646:  Method (_OSC, 4, Serialized)
```

**`_CRS`（`:2427`，Serialized，返回 `CRS1`）实际给出的窗口：**

| 资源 | 范围 | 依据 |
|---|---|---|
| Bus number | `0x00 – 0x7F` | `CRS1` `WordBusNumber` + `MIN0=BRB(0)`, `LEN0=BRL(0x0100)` |
| I/O | `0x0000–0x03AF`、`0x03E0–0x0CF7`、`0x0D00–0x0FFF`，加 `0x0CF8/0x0CFC` | `CRS1`，`MIN1=IOL` 分支 |
| 32-bit MEM #1 | `MBB=0xA0000000` … `NBTP-1` | `:2539-2552` |
| 32-bit MEM #2 | **静态路径下为空（`MIN7=MAX7=LEN7=Zero`）** | `:2536-2545`，见下 |
| 64-bit MEM | `MAB=0x460000000` … `MAM=0x7FFFFFFFFF`（长度 `MAL=0x7BA0000000` ≈ 494 GiB） | `:2571-2579`（不受 `Local7` 影响） |

**⚠️ 一处必须先纠正的读法（对 `docs/06` 初版的勘误）**：初版把 32-bit MEM #2 写成
`0xFEE00000 + 0x1200000 = 0xFEE00000–0xFEF1FFFF`，**这是错的**，两处都错：

1. **算术**：`0xFEE00000 + 0x1200000 = 0x1_0000_0000`，所以任何以 `0xFEE00000` 起 18 MiB 的区间
   都是 `0xFEE00000–0xFFFFFFFF`（32 位空间顶部 18 MiB），**不是** `0xFEF1FFFF`
   （那只有 `0x120000` ≈ 1.125 MiB）。
2. **控制流**：`NBTP = 0xFEC00000`（`:292 Name (NBTP, 0xFEC00000)`）、`NBTS = 0x5000`（`:237`）是
   **静态 root-scope Name**（已核实；全文件无写入者，运行配置的 `ACPI → Patch` 只有 `_OSI→XOSI` 一条）。
   于是 `Local0 = MBB+MBL = 0xE0000000`，`:2537 If ((Local0 < NBTP))` 即 `0xE0000000 < 0xFEC00000`
   **成立** → 走 `:2543-2545` 把 `MIN7/MAX7/LEN7` 全部置 **Zero**。
   **`:2561 MIN7 = 0xFEE00000` 那条 `Else` 分支在本文件里静态不可达**，而且即便可达，
   代数化简 `LEN7 = MBB+MBL-0xFEE00000 = -0x1EE00000` 截断进 32 位 `LEN7` 字段也只会得到 `0xE1200000`。
   （要得到 `0x1200000` 需要 `MBL = 0x60000000`，本 DSDT 是 `0x40000000`。）
3. **那实际值从哪来**：只有 `:2492 If ((RSTE == One))` → `:2504-2505 MIN7 = RSB1, LEN7 = RSS1`
   这条路径能给出真实窗口；`RSB1/RSS1` 是
   `OperationRegion (NRSV, SystemMemory, NRSB, 0x1000)`（`:2252 Name (NRSB, 0x96931000)`，
   偏移 `:2263 RSB1, 32` / `:2265 RSS1, 32`）的字段，即**固件写在物理 `0x96931028` 的 RAM 状态**，
   从 ACPI 反编译结果**看不出来**。另外若 `RSTE != 1`，则整段 `MBB/MBL` 逻辑跑完也是"第二窗口为空"。

**`_OSC`（`:2646`）**：标准 PCI Host Bridge UUID `33db4d5b-…-7441c03dd766`；
`SUPP & 0x16 != 0x16` 时 `CTRL &= 0x1E`，再按 `PEHP/SHPC/PEPM/PEER/PECS` 逐位收敛；
`Arg1 != One` 时 `CDW1 |= 0x08`；`CDW3 != CTRL` 时 `CDW1 |= 0x10`。
**没有任何路径把 `CDW1` 的 bit0（Failure）置位** → 这是一个**正常实现**，
**不存在**"固件拒绝 PCIe 控制权导致 macOS 自己枚举"的情形。

**最重要的结论（对 §5 的 PFM64 讨论）：本机 host bridge 明确声明了 64-bit MMIO 窗口**
（`:2571 If (MAL)` 位于 `Local7` 判断之外，无条件生效；且 `MAB + MAL - 1 = 0x7FFFFFFFFF = MAM` 自洽），
所以 `IOPCIConfigurator` 里那段"固件没给 64-bit 窗口就合成一个"的分支
（`hasHostMemory && !hasHost64 && !fAddedHost64`）**在本机不成立**。
`npci` 通过清 `kIOPCIConfiguratorPFM64` 影响的是**上限**（`maxAddress = ~0ULL`），
**不是**"有没有窗口"——这与 `docs/05` §5.1/5.2 的勘误一致。

> **修正后的未决项（见 §2.7 U1）**：不是"`NBTP/NBTS` 找不到定义"（已找到，且是静态的），
> 而是 **`RSTE`/`RSB0..3`/`RSS0..3` 是固件写在 `0x96931000` 的 RAM 状态，ASL 层面不可知**；
> 也就是说 `_CRS` 到底报哪几个 32-bit 窗口，取决于那份 RAM，而不取决于 DSDT 文本。

### 2.3 `SSDT-PLUG-ALT` 对 Ryzen 8845H 的适用性（问题 2）

**注入表**（`SSDT-PLUG-ALT.aml`，OemTableId `CpuPlugA`，1096 B，反编译 317 行）：

```asl
21: DefinitionBlock ("", "SSDT", 2, "ZPSS", "CpuPlugA", 0x00003000)
25:     Scope (\_SB)
27:         Processor (C000, 0x00, 0x00000510, 0x06) {
29:             Name (_HID, "ACPI0007")
30:             Name (_UID, Zero)
31:             Method (_STA) { If (_OSI ("Darwin")) Return (0x0F) Else Return (Zero) }
43:             Method (_DSM, 4) { ... Return (Package (0x02) { "plugin-type", One }) }
59:         }
61:         Processor (C001, 0x01, 0x00000510, 0x06) { ... }     // 无 _DSM
...                                                                 // 一直到
299:        Processor (C00F, 0x0F, 0x00000510, 0x06) { ... }
```

**固件本来就提供 CPU 对象**（`ssdt1.dat` = SSDT `CPUSSDT`，545 B，XSDT idx 3）：

```asl
23:     Scope (\_SB)
25:         Device (PLTF) {
27:             Name (_HID, "ACPI0010")      // Processor Container Device
28:             Name (_CID, EisaId ("PNP0A05"))
29:             Name (_UID, One)
30:             Device (C000) { Name (_HID, "ACPI0007"); Name (_UID, Zero) }   // ← 无 _STA
36:             Device (C001) { ... }
...                                                                          // 一直到
120:            Device (C00F) { Name (_HID, "ACPI0007"); Name (_UID, 0x0F) }
125:        }
```

**逐条回答提问：**

1. **是否出现额外 CPU 对象？—— 是，多了 16 个。**
   固件的是 `\_SB.PLTF.C000..C00F`；注入的是 `\_SB.C000..C00F`。macOS 命名空间里因此同时存在
   **32 个 `ACPI0007` 节点**。注入的 16 个在 `_OSI("Darwin")` 下 `_STA=0x0F`（全部"在场"），
   固件那 16 个**根本不写 `_STA`**（缺省即在场）。
2. **是否出现 ACPI 命名冲突？—— 没有。** 两者作用域不同（`\_SB` vs `\_SB.PLTF`）。
   日志侧独立佐证：3 个表加载失败**没有一个是 `CpuPlugA`**；Round 1 照片里 `AppleACPICPU`
   恰好 16 条（`ProcessorId=0..15`，与 MADT 一致），**没有**出现 16–31 的"幽灵 CPU"。
3. **是否适合 Ryzen 8845H？—— 结构上冗余。** 这个 `-ALT` 版是给"固件没有 `ACPI0007` CPU 对象"的
   机器用的（参见 issue #21 第二位报告人：他所在的主板也带 `\_SB.PLTF` 结构）。本机固件**已经有**，
   所以注入表带来的实际增量是：16 个多余节点 + 一个**未接线的 P_BLK**（`Processor` 的第 3/4 参数
   `0x00000510, 0x06`，即 IO 端口 0x510 长度 6，在 AMD Zen 上并不是真的 P_BLK） + `plugin-type=1`。
4. **不能证明什么**：不能因为"冗余"就断定它有害；也不能因为"没有幽灵 CPU"就断定它与 PCI 停点无关。
   上游有一个**相反方向**的数据点：issue #21 的第二位报告人（ASUS TUF B650M-PLUS WIFI + 7800X3D）
   正是**禁用 SSDT-PLUG-ALT** 才越过 `AppleACPICPU` 停点。

### 2.4 三个 `AE_ALREADY_EXISTS` 的**完整闭环**（问题 3）

Round 1 屏幕照片（`shots/acpi_errors.jpg`，裁切放大后逐字确认）原文：

```
ACPI Error: [_DSM] Namespace lookup failure, AE_ALREADY_EXISTS (20160930/dswload-462)
ACPI Exception: AE_ALREADY_EXISTS, During name lookup/catalog (20160930/psobject-310)
ACPI Exception: AE_ALREADY_EXISTS, (SSDT:    WLAN) while loading table (20160930/tbxfload-319)
ACPI Error: [_S0W] Namespace lookup failure, AE_ALREADY_EXISTS (20160930/dswload-462)
ACPI Exception: AE_ALREADY_EXISTS, During name lookup/catalog
ACPI Exception: AE_ALREADY_EXISTS, (SSDT:GpMsSsdt) while loading table
ACPI Error: [\_SB.PCI0.GPP6.WLAN._DSM] Namespace lookup failure, AE_ALREADY_EXISTS
ACPI Exception: AE_ALREADY_EXISTS, During name lookup/catalog
ACPI Exception: AE_ALREADY_EXISTS, (SSDT:    DNET) while loading table
ACPI Error: 3 table load failures, 32 successful (20160930/tbxfload-342)
```

> **勘误**：我们此前把第二行记成 `[_SBW]`。放大后确认是 **`[_S0W]`**（S-零-W），
> ACPI 里并不存在 `_SBW`。这个更正让下面三条全部有了唯一解释。

**闭环链条（每条都有 file:line）：**

1. **`\_SB.PCI0.GPP6.WLAN._DSM` 由 DSDT 自己提供**：
   `dsdt.dsl:15259 Scope (\_SB.PCI0.GPP6)` → `:15261 Device (WLAN)` → `:15556 Method (_DSM, 4, Serialized)`。
2. **固件 SSDT `WLAN` 重复定义它**：`ssdt23_WLAN____.dsl:299 Scope (\_SB.PCI0.GPP6.WLAN)` →
   `:308 Method (_DSM, 4, Serialized)`。（该表头部 40 余条 `External (...)`，说明它只做 `Scope`。）
   ⇒ 第 1 个 `AE_ALREADY_EXISTS`，**该表在此中止**。
3. **连带后果**：`WLAN` 表在中止**之前**已经建好了 `ssdt23:165 Scope (\_SB.PCI0.GPP6)` →
   `:167 Method (_S0W, 0, NotSerialized)`。随后固件 SSDT `GpMsSsdt` 在
   `ssdt25_GpMsSsdt.dsl:299 Scope (\_SB.PCI0.GPP6)` → `:301 Name (_S0W, Zero)` 想建**同名的 Name**。
   ⇒ 第 2 个 `AE_ALREADY_EXISTS`，**该表也中止**。
4. **本项目注入的 `DNET` 撞的是第 1 条同一个对象**：`SSDT-Disable_Network_GPP6.aml`（212 B）想在
   `\_SB.PCI0.GPP6.WLAN` 下建 `_DSM` ⇒ 同冲突。⇒ 第 3 个。
   **D6 因此从"实测无效"升级为"可证明不可能生效"。**

**是否会影响后续 PCI 设备初始化？—— 不会删掉任何 PCI 设备节点。** 证据：

* `ssdt23_WLAN____.dsl` 与 `ssdt25_GpMsSsdt.dsl` 的 `Device (` 计数**都是 0**（全部固件表中只有
  DSDT(177)、`CPUSSDT`(17)、`AmdTable`(12) 等少数几张自己建设备）。它们只对**已存在**的设备做 `Scope`。
* 三个失败表涉及的设备（`\_SB.PCI0.GPP6`、`\_SB.PCI0.GPP6.WLAN`）都由 **DSDT** 创建，而 DSDT 加载成功。
* 丢掉的只是 `_DSM` / `_S0W` / `QDSW` / `QBME` 这类**方法**（WLAN 的电源/唤醒语义），
  它们不参与 `IOPCIConfigurator` 的 BAR 分配。

> **不能证明什么**：不能因此说"这三个错误与 PCI 无关就万事大吉"。§2.2 修正后，
> `NBTP/NBTS` 是**静态**定义（与这些失败表无关），所以原先担心的那条路径**已被排除**；
> 仍在的未知量是 `_CRS` 依赖的 `NRSV` RAM 状态（U1），那不是这三张表能影响的东西。

### 2.5 五块 MMIO 去虚拟化区域（问题 4）

**先纠正机制**（这决定怎么读这五行）：这五行**不是 ACPI 对象**。
OpenCore 遍历的是 **EFI 内存描述符表**，逐条打印 `Type == EfiMemoryMappedIO` 且
`Attribute & EFI_MEMORY_RUNTIME` 的描述符，然后把该位清掉 ——
`1401/ref/oc/ServiceOverrides.master.c:281-310`：

```c
281: for (Index = 0; Index < NumEntries; ++Index) {
282:   if (  (Desc->NumberOfPages > 0)
283:      && (Desc->Type == EfiMemoryMappedIO)
284:      && ((Desc->Attribute & EFI_MEMORY_RUNTIME) != 0))
285:   {
...      for (Index2 …) if (AREA_WITHIN_DESCRIPTOR (Desc, Whitelist[Index2], 1)) { Skipped = TRUE; }
298:     DEBUG "OCABC: MMIO devirt 0x%Lx (0x%Lx pages, 0x%Lx) skip %d\n" …
306:     if (!Skipped) { Desc->Attribute &= ~EFI_MEMORY_RUNTIME; PagesSaved += Desc->NumberOfPages; }
```

**ACPI 只能"解释"这些区域，不能生成它们。** `skip 0` = 未被 `MmioWhitelist` 覆盖（本空白名单）。
页数自检：`0x10000 + 0x1E00 + 1 + 0x11FF + 0x20200 = 209408` 页 × 4 KiB = **837632 KiB**，
与日志 `saved 837632 KB` **完全一致**。

实测（`logs/opencore-2026-10-13-095517.txt:491-497`）：

```
11:122 OCABC: MMIO devirt start
11:125 OCABC: MMIO devirt 0xE0000000 (0x10000 pages, 0x800000000000100D) skip 0
11:127 OCABC: MMIO devirt 0xFD000000 (0x1E00 pages, 0x800000000000100D) skip 0
11:129 OCABC: MMIO devirt 0xFEE00000 (0x1 pages, 0x8000000000000001) skip 0
11:131 OCABC: MMIO devirt 0xFEE01000 (0x11FF pages, 0x800000000000100D) skip 0
11:134 OCABC: MMIO devirt 0x460000000 (0x20200 pages, 0x800000000000100D) skip 0
11:136 OCABC: MMIO devirt end, saved 837632 KB
```

| # | base | 大小 | ACPI 侧最能解释它的对象 | 结论 |
|---|---|---|---|---|
| 0 | `0xE0000000` | 256 MiB | **PCIe ECAM**：`mcfg_Notebook.dsl:25-28`（base `0xE0000000`、Segment 0、**bus `00`–`FF`** ⇒ 256×1 MiB）；旁证 `dsdt.dsl:266 Name (PEBS, 0xE0000000)` / `:236 Name (PEBL, 0x10000000)`，经 `\_SB.PCI0.AMDN._CRS`（`:2213-2226`）转发，且 `ssdt3_OemNv2T_.dsl:589-590` 用 ECAM 步进（device≪15、fn≪12） | **精确匹配**，且是 macOS 自己会重映射的硬件 |
| 1 | `0xFD000000` | 30 MiB | **无**。全部 44 张 `.dsl` 文本搜索 `0xFD000000` **0 命中**（只有 `0xFD300000`/`0xFD500000`）；全部 47 个 ACPI 二进制做小端字节扫描 `00 00 00 FD` 也 **0 命中**（对照模式有命中，说明扫描有效）。该区间**内部**确实有声明：`\_SB.PCI0.GP17.APSP` `0xFD300000`+1 MiB（`:3150-3167`）、`\_SB.TPM` HPM `0xFD500000`+1 MiB（`:6633-6634`, `:6777-6783`），以及芯片组簇 `0xFEC00000–0xFEE00FFF`。780M（`\_SB.PCI0.GP17.VGA`，`:3002-3017`）**根本没有 `_CRS`**，其 Windows BAR 在 `0x7E10000000`+256 MiB / `0xDD200000`+2 MiB（`1401/plan.json:10098-10118`）——**不在 `0xFD000000`** | **未确定** |
| 2 | `0xFEE00000` | 4 KiB | `dsdt.dsl:3646-3649` `Memory32Fixed (ReadWrite, 0xFEE00000, 0x00001000)`（`\_SB.PCI0.S900`）+ `apic_Notebook.dsl:23 Local Apic Address : FEE00000` | **精确匹配**（LAPIC 页） |
| 3 | `0xFEE01000` | `0x11FF000` = 18 MiB − 4 KiB | **没有同 base/size 的 ACPI 对象**；它只是内存描述符从 LAPIC 页之后**一路续到 4 GiB 顶端**（属性字不同：`…100D` vs `…0001`），覆盖 `S900._Y18` ROM 窗 `0xFF000000`+16 MiB（`:3711-3714`）与 `\_SB.SMIC` `0xFED80000`+8 MiB（`:4522`） | **部分**（是内存图描述符，不是 ACPI 声明） |
| 4 | `0x460000000` | 514 MiB | base = `dsdt.dsl:2249 Name (MAB, 0x0000000460000000)`（全 44 张表里该值的**唯一**出现处），即 DSDT 64-bit 窗口（`:2576-2578` / `:2636-2638`）的**基址**；**没有任何 ACPI 对象声明这 514 MiB 的子区间** | **基址匹配；子区间未确定** |

**两条结构性发现：**

* **#1+#3 拼接成一块连续 48 MiB**：`0xFD000000 + 0x1E00000 = 0xFEE00000`，
  `0xFEE00000 + 0x1200000 = 0x1_0000_0000` —— 即 32 位空间顶部的
  **`0xFD000000–0xFFFFFFFF`（`0x3000000` = 48 MiB）一整块固件保留 MMIO**，
  只因属性字不同被切成三个描述符。
* `#0` 与 `#2` 是 **ACPI 已声明、OS 自己拥有的硬件**（ECAM、LAPIC）；
  `#1` 与 `#4` 是 **ACPI 里完全没有主人的两块**。这正好回答了"`DevirtualiseMmio=false`
  是否值得单独测"：**只有这两块存在"保住它的虚拟映射"这一机制的着力点**，
  而 OpenCore 自己在 `ServiceOverrides.master.c:264-270` 写的失败模式
  （Haswell 的 `0xFED1C000`、`0xFF000000`："某些固件的运行期服务/SMM 仍会解引用这些虚拟地址"）
  说的正是这种情况 —— 本机 `MmioWhitelist` 为空，所以**什么都没被保护**。

**怎么读这个结果（对"`DevirtualiseMmio=false` 是否值得单独测"）：**

* 这 5 块都被 OpenCore 摘掉 `EFI_MEMORY_RUNTIME`（共 818 MiB）。摘掉的是
  **运行期虚拟映射**，描述符仍是 `EfiMemoryMappedIO`，所以**不会**被当作 RAM 交给 OS。
* 上游证据是**分裂**的，必须并列：
  * **issue #9（维护者 `nullmoth` 唯一实质回复）**：AM5 上 `DevirtualiseMmio off` 会导致
    `EB.MM.AKM` / STOP 0x16（"firmware runtime MMIO regions are in the way"），必须 `true`。
  * **issue #6**：`false` 消掉一个早期 Type-14 页错误（`CR2=0xFF00004C`），但随后改挂 ACPI。
  * **issue #10**：`false` 只是让 `MMIO devirt` 行消失，"the boot still stops at exactly the same line"。
  * **issue #21**：在同一轮里试过 `MmioWhitelist` 四个区域（`E0000000/F7000000/FEE00000/FEE01000` 全 `skip 1`）
    + `npci=0x3000`，**没有改变**他那边（CoreAnalyticsHub 之前的）停点。
* 本机**从未**测过 `DevirtualiseMmio=false`。因此它确实是一个**尚未走过的单变量**；
  但它的**主要预期风险**是把停点**前移**到 `EB.MM.AKM`（本机 4 份历史日志里出现过 `EB.MM.AKMr2`）。
  所以它的判据必须写成三岔：停点前移/消失（devirt 是变量）／退回 `EB.MM.AKM`（devirt 必须开）／
  停在**同一行**（与 #10 一致，devirt 与本停点无关）。
* **不能证明什么**：即使停点不变，也**不能**排除 devirt 的影响（与 §7.6 B 的口径相同）。
* 附带勘误：本项目已发布的 `logs/bootfix-findings.md:97` 把 base `0xFEE01000` 记成
  "`0xFEDC4000` 附近、4607 pages"，与日志原文不符（那是 1401 诊断器自己的输出，此处只登记差异）。

### 2.6 RTX 4050 BAR 的**实际**处理路径（问题 5）

源码依据：`Library/OcDeviceMiscLib/SetResizableBar.c`（本轮取回，`1401/ref/oc/SetResizableBar.c`）：

```c
249:  // When the bit of Capabilities Set, indicates that the Function supports
254:  // Bit n is set: supports operating with the BAR sized to (2^n) MB
272:  NewCapabilities = Capabilities = LShiftU64(...,28) | Entries[Index].ResizableBarCapability...
278:  NewCapabilities &= PCI_BAR_CAP_LIMIT (Size);
284:  if (!Increase) NewCapabilities &= PCI_BAR_CAP_LIMIT (Entries[Index].ResizableBarControl.Bits.BarSize);
291:  if ((NewCapabilities == 0) && (…BarSize > (UINT32)Size)) { Bit = LowBitSet64 (Capabilities); }
299:  DEBUG "OCDM: RBAR %u/%u supports 0x%Lx, sizing %u inc %d results setting from %u to %d"
322:  Entries[Index].ResizableBarControl.Bits.BarSize = (UINT32)Bit;   // 写 RBAR control
334:  if (ChangedBars) { …DEBUG "OCDM: New BAR …"…
363:  // PCI BARs are reset after resizing, so we must restore them. This follows the spec:
369:  if (!IsZeroBuffer (OldBar, sizeof (OldBar))) { …写回 OldBar…
377:      DEBUG "OCDM: Reprogrammed BARs to original - %r"
```

本机实测（Round 4 日志）：

```
11:097 OCDM: RBAR using PciIo
11:099 OCDM: Setting RBAR to 0 inc 0 on 5/43
11:101 OCDM: RBAR control is 460, total 3 - Success
11:103 OCDM: Old BAR DC000000 0000000C 0000007C 0000000C 0000007E 0000F001 - Success
11:106 OCDM: RBAR 1/3 supports 0x10,   sizing 0 inc 0 results setting from 4  to 4
11:108 OCDM: RBAR 2/3 supports 0x3FC0, sizing 0 inc 0 results setting from 13 to 6
11:110 OCDM: RBAR 3/3 supports 0x20,   sizing 0 inc 0 results setting from 5  to 5
11:112 OCDM: New BAR DC000000 0000000C 0000007C 0000000C 0000007E 0000F001 - Success
11:115 OCDM: Reprogrammed BARs to original - Success
11:118 OCDM: Setting RBAR to 0 inc 0 on 19/43
11:120 OCDM: RBAR is unsupported by device - Not Found
```

**精确读法：**

1. 触发者是 **`Booter → Quirks → ResizeAppleGpuBars = 0`**（`UEFI → Quirks → ResizeGpuBars = -1` 被跳过）。
   `sizing 0` 就是"设成最小支持尺寸"。
2. 尺寸索引的含义按 `:254` 的注释：**索引 n = 2^n MB**。
   `RBAR 2/3` 从 **13 → 6** 就是 **2^13 MB = 8 GiB → 2^6 MB = 64 MiB**。
   `1/3`（2^4 = 16 MiB）与 `3/3`（2^5 = 32 MiB）本来就是最小，**没有变化**。
3. `Old BAR` / `New BAR` 那 6 个数是 **BAR0…BAR5 的原始寄存器读回值**，不是容量表。
   低位值 `0x0000000C` / `0x0000007C` / `0x0000000E` 带 bit2（64-bit）+ bit3（prefetchable），
   说明**后一个 dword 才是地址高 32 位**：`0x7C` → 一个 64-bit BAR 落在 `0x7C00000000`，
   `0x7E` → 另一个落在 `0x7E00000000`。后者与 Windows `Win32_PnPAllocatedResource` 报的
   GPU 地址 **`0x7E00000000`** 一致（该值 + 8 GiB = `0x8000000000`，正好等于 DSDT 的 `MAM + 1`）。
4. **`New BAR` 与 `Old BAR` 完全相同，并且紧接着打印 `Reprogrammed BARs to original - Success`**：
   按 `:363-378` 的注释，写 RBAR control 会把 BAR 地址寄存器**复位**，规范要求软件再把它写回。
   OpenCore 做的正是这件事。**所以：尺寸位被改成 6，地址被恢复到固件原值。**
5. **但"尺寸位"不在这 6 个 dword 里**（它在 PCIe 扩展能力的 RBAR control 里）。
   因此 **"macOS 最终看到多大 BAR1" 无法由本机日志单独判定。**
6. 上游同代码路径的实测（issue #23，MSI Z370M-S01 + i5-9400F + RTX 4060 Ti 16 GB，BIOS ReBAR ON）：
   `setting from 14 to 13` + `Reprogrammed BARs to original`，报告人自己的结论是
   *"Index 14 = 16 GB, index 13 = 8 GB -- so the BAR ended up back at 16 GB"*，
   并且他**唯一验证过的解法是"BIOS 关掉 Re-Size BAR"**（固件给 256 MB BAR1，于是才有 `from 8 to 13`）。
   > 注：他的这句话与他引用的日志行（`from 14 to 13`）**并不自洽**，本文件不替他解释。
7. **对本机的诚实结论**：Windows 报的 8 GiB 只能当作"固件原始布局"的**旁证**，
   **不能**当作"macOS 实际所见"。所以 Round 5 **不应**把 BAR 当作已确立变量。

### 2.7 未决项（必须登记，不许含糊）

| # | 未决 | 影响 |
|---|---|---|
| U1 | **`_CRS` 报出的 32-bit 窗口取决于固件写在 RAM `0x96931000` 的 `RSTE/RSB0..3/RSS0..3`，ASL 层面不可知。** `NBTP/NBTS` 本身**已闭合**（`:292 Name (NBTP, 0xFEC00000)`、`:237 Name (NBTS, 0x5000)`，静态、无写入者），且静态路径下第二个 32-bit 窗口为 **空**，`:2561` 分支不可达 | 无法从 ACPI 反编译判断 `_CRS` 实际报哪几个窗口；要确认只能靠内核侧 ACPI 日志（本轮没有） |
| U2 | `0xFD000000`（30 MiB）的占用者（ACPI 无声明；780M 的 BAR 在别处） | 决定"保住它虚拟映射"的白名单 A/B 是否有必要 |
| U3 | `0x460000000` 那 514 MiB 的具体占用者（只知道是 `MAB` 基址、且 ACPI 未声明该子区间） | 同上 |
| U4 | macOS 24.6.0 是否支持 `pci_log` / `pci_log_mode`（源码来自本机取回的 IOPCIFamily，未与 24.6.0 逐版本对齐） | 决定候选 A 是否有信息量 |
| U5 | Round 4 的**停留时长** | 决定 §1.4 的"`doConfigure()` 未返回"是否成立 |
| U6 | Round 4 的照片 | 本文件只用口述 |
| U7 | `VoodooI2CACPIController` 在 Round 1 照片里的 HID 字样 | 与当前问题无关，仅登记 |

---

## 3. 上游案例复核（第三阶段）

### 3.1 issue #21（`AM5 / X870E … hard lock right after "CoreAnalyticsHub start completed"`）

* **状态**：open；2 条评论（都来自第三方 `bitrange`，`author_association: NONE`），
  **维护者 `nullmoth` 从未回复**；issue 作者本人也没有确认修复。
* **DSDT 问题的形状**：`ACPI Error: [\_SB_.PCI0.GPP7.UP00.DP60.XH00.RHUB.POT6] Namespace lookup failure, AE_NOT_FOUND`
  → `[DSDT] table load failed`，`6 table load failures, 11 successful`。根因是芯片组设备被包在顶层
  `If (G002 …)` 里，而后面又有顶层 `Scope (\_SB.PCI0.GPP7…)` 去引用它们；条件在 macOS 下不成立
  → 设备没建 → `Scope` 解析失败。
* **修复的**原理**（用户重点问的）**：**不是改名，也不是屏蔽设备，而是把 `If` 谓词整段 NOP 掉。**
  以 patch 1 为例，`Find` 的 AML 是 `A0`（`IfOp`）+ PkgLength（两位，`Mask` 标成 don't-care）
  + `90`(`LAnd`)+`92`(`LNot`)+`93`(`LEqual`)+`R 4-byte name G002`+`0A 03`+`93`+`G000`+`01`；
  `Replace` 用等长的 `0xA3`（`NoopOp`）覆盖。谓词被抹掉后主体**无条件执行**，
  于是那些设备总是存在，后面的顶层 `Scope` 能解析，DSDT 不再加载失败。
  四个补丁对应 `G002 != 3 && G000 == 1`（两种 PkgLength 宽度，故 #1 与 #1a 分开）、
  再加 `G004 != 0x43FA1022`、再加 `G000 == 2`。
* **对本案的适用性：不适用。** 三条硬理由：
  1. **症状位置不同**：#21 是**在 `PCI configuration begin` 之前**硬锁（他明确写 "No `PCI configuration begin`"）；
     本机是**已经进入** `IOPCIConfigurator::configure()`。
  2. **ACPI 错误类型不同**：#21 是 `AE_NOT_FOUND`（`Scope` 指向被 `If` 门控而未建的设备）；
     本机是 `AE_ALREADY_EXISTS`（**重复定义** `_DSM` / `_S0W`），形状完全不同（§2.4 已闭环）。
  3. **本机不存在那种门控结构**：本机 DSDT 没有顶层 `If (G00x …)` 包住 PCIe 设备的模式，
     失败表是"重复定义"，NOP 掉任何 `If` 都不会修好重复定义。
* **作者自陈的限制**（必须原样保留）："these patches may be specific to that board's DSDT layout"、
  "I cannot guarantee they apply to other hardware"、"I did not author these patches"；
  修复者在 **ASUS TUF B650M-PLUS WIFI + 7800X3D + RTX 4070 Super** 上验证，
  补丁来源是 **ASUS PRIME X670E-Pro + 9700X + RX 6750 XT** 的第三方 EFI；
  **X870E + RTX 4090 的 OP 从未确认**。
  他另有一次"重编译整个 DSDT → 中途**瞬间重启**"的失败记录。

> **本项目的执行口径：不搬运。** 用户明确禁止直接复制其它主板的 DSDT Find/Replace。

### 3.2 issue #34（`The more newer version, the more errors i have`）

* **状态**：open；**0 条评论**，维护者从未回复，**issue 内没有任何技术细节**
  （无 `config.plist`、无日志、无 quirk 名、无 ACPI 文件）。
* **正文可用的全部信息**：Acer Nitro ANV16-41，**Ryzen 7 8845HS** + Radeon 780M + **RTX 4050 Laptop**；
  **1.10.0 起无法进入外置 Recovery**；"更早的版本"能安装并能进系统（键盘/触控板时好时坏、USB 鼠标不可用）；
  装 NVIDIA 驱动后触发 AppleKeyStore 错误。
* **版本边界是真的**（这是从仓库代码查到的，不是 issue 提供的）：`v1.10.0` 的提交
  `1d84d960` 新增 `ZEN45_CODENAMES` / `is_zen4_or_later()`，对 Zen 4/5 **强制**
  `DevirtualiseMmio=True` + `SetupVirtualMap=True`（≤1.9.0 在这类板子上是**两者皆 off**）；
  `v1.14.0` 的 `068e23e0` 又追加 `DisableVariableWrite=True`。
  仓库自带测试 `tests/test_zen4_devirt.py` 里**逐字出现了** `AMD Ryzen 7 8845HS w/ Radeon 780M Graphics`。
* **但必须注意时间线**：#34 创建于 2026-10-11T07:52Z，当时最新发布是 **v1.13.0**；
  `v1.14.0` 发布于 10-12T02:41Z、`v1.14.2` 发布于 10-12T06:24Z，**都在 #34 之后**。
  所以那位报告人**不可能**测过 1.14.x，issue 里也从没出现过 "1.9.x" 或 "1.14.2"。
* **与本机的关系**：本机就是 1.14.2 生成的 EFI，且 `DevirtualiseMmio/SetupVirtualMap/DisableVariableWrite`
  三个值**恰好都是 `true`**，并且本机**确实进不了 Recovery**。这条方向**可测**，
  但 **#34 自身不提供任何可作为依据的 diff** —— 它只是"版本边界假设"，不是证据。

### 3.3 与本机停点**逐字相同**的其它上游案例（本轮新查到，价值最高）

| issue | 机器 | 与本机的关系 |
|---|---|---|
| **#23** | MSI Z370M-S01 + i5-9400F + **RTX 4060 Ti 16 GB**，BIOS **Re-Size BAR ON / Above 4G ON**，1401 1.9.0 | 屏幕停在**完全相同的两行**。**`npci=0x2000` 真的越过了这一点**（随后卡在 AppleKeyStore 循环）。**唯一验证过的解法是 BIOS 关掉 Re-Size BAR + `ResizeGpuBars=-1`**，让固件给 256 MB BAR1 |
| **#25** | X99 + Xeon E5-2690 v4 + RTX 2070 | 1401 的 1.0.24 / 1.1.0 / 1.5.0 / 1.9.0 **四个版本**都停在同一个 `PCI configuration` 字符串，无解 |
| **#29** | Gigabyte B760 + i7-12700KF + RTX 4060 | `PCI configuration` 附近 + `STOP 0x16` + AppleKeyStore 刷屏 |
| **#9** | MSI X870 + 9950X + RTX 4070 Ti Super | 维护者唯一实质回复：`DevirtualiseMmio=true` + `SetupVirtualMap=true` 修 `EB.MM.AKM`/STOP 0x16 |
| **#10** | （AMD 桌面） | `DevirtualiseMmio=false` 只是让 `MMIO devirt` 行消失，"stops at exactly the same line" |
| **#6** | Lenovo Y7000 + RTX 4060 Laptop | `DevirtualiseMmio=false` 消掉早期 Type-14 页错误，但改挂 ACPI |
| **#15** | （MAT 组合测试） | `EnableWriteUnprotector=false` + `RebuildAppleMemoryMap=true` + `SyncRuntimePermissions=true` —— "reached userspace **without a GUI**"，**与本机 Round 4 的负结果一致** |
| **#30** | MSI X870 + 9950X + RTX 5060 Ti | 安装 19 分钟冻结 → `DisableVariableWrite=true`（1.14.0 已内置） |

> **#23 是对本机最有价值的一份数据**：同一停点、同一 GPU 家族（Ada）、同一 BIOS ReBAR 开启状态，
> 而且**只有关掉 BIOS ReBAR 才是他验证过的解法**。这既解释了为什么"BAR 方向"看起来可疑，
> 也说明该方向**必须动 BIOS**，超出当前授权（§5 候选 E）。

### 3.4 关于"优先只读比较 1401 旧版与 1.14.2 生成的 EFI"

* 本机没有 1401 旧版的构建产物可比（`1401/build`、`build2`、`build3` 都是 1.14.2 前后、
  ACPI 七件套与 `SSDT-PLUG-ALT` 大小**完全相同**：212/125/1096/240/435/166/237 B）。
* 因此比对的替代物是**上游仓库的版本差异**（§3.2），结论是：
  **1.9 → 1.10 的边界上，唯一与本 CPU 类相关的改动就是 `DevirtualiseMmio` + `SetupVirtualMap`
  由 off 变 on**；ACPI 文件集、Kernel Patch、NVRAM 模板**都没有变**。1.14.0 另加 `DisableVariableWrite`。
* 这三项本机**都已生效**（见 §7 的卡上现状表）。所以"旧版能装、新版不能进 Recovery"这条线索
  在本机方向上唯一剩下的可测变量就是**这三个 quirk 的取值**，而不是 ACPI/BAR。

---

## 4. Round 5 候选（**只给 diff 与分析，全部不写入**）

### 4.1 排序依据

`IOPCIConfigurator::configure()` 在 `doConfigure()` 期间**关闭屏幕**（§1.4），
所以现在**根本不知道**挂在四遍 `iterate` 中的哪一遍、哪个设备。**在拿到这个信息之前**，
任何"改一个 quirk 再看"的试验都是在赌 —— 而且 Round 4 已经演示了这种赌法的产出：
`npci` 与 MAT 两组变量换来的是**同一个屏幕停点**。

所以排序原则：**先买"看得见"，再买单变量。**

### 候选 A（首选）—— 打开 IOPCIFamily 自己的 PCI 日志

**性质**：**只改日志开关**，不改任何 `gIOPCIFlags` 语义（语义由 `pci=` / `npci=` 控制，本轮绝不动）。

源码依据（`audit/iopicifamily/IOPCIPrivate.h:528-611`）：

```c
529: // pci_log_mode= flags (if unspecified, defaults to os_log())
532: #define kPCI_LOG_MODE_KPRINTF  (0x00000001)
533: #define kPCI_LOG_MODE_IOLOG    (0x00000002)
534: #define kPCI_LOG_MODE_OSLOG    (0x00000004)
537: // pci_log= flags (if unspecified, defaults to ALWAYS_ON | AER)
572: #define kPCI_LOG_ENUMERATION   (0x00000200)
580: #define kPCI_LOG_ALWAYS_ON     (0x80000000)

590: #define pci_log(domain, facility, fmt, args...)                       \
592:   if ((gIOPCILogDomains & (1 << domain))                              \
593:    && (gIOPCILogFlags & (kPCI_LOG_ ## facility))) {                   \
597:     if (gIOPCILogModeFlags & kPCI_LOG_MODE_KPRINTF) kprintf(...);     \
601:     if ((gIOPCILogModeFlags & kPCI_LOG_MODE_IOLOG) && ml_get_interrupts_enabled()) IOLog(...); \
606:     if (gIOPCILogModeFlags & kPCI_LOG_MODE_OSLOG)   os_log(...);      \
```

而 `IOPCIConfigurator.cpp` 里：

```c
77: #define DLOG_A(fmt, args...)  pci_log(fDomainId, ALWAYS_ON,   fmt, ## args)
74: #define DLOGC(domainId, fmt, args...) pci_log(domainId, ENUMERATION, fmt, ## args)
80: #define DLOG(fmt, args...)    DLOGC(fDomainId, fmt, ## args);
```

也就是说：`iterate %s: start/end`、`scan %s`、`Found type %u device class-code …`、
`bridge … probe child ranges`、`Request pause …`、`kConfigOpPaused …` 全都已经是
`pci_log(..., ENUMERATION 或 ALWAYS_ON, ...)`，只是**默认只往 `os_log` 写**（`kPCI_LOG_MODE_OSLOG`），
屏幕上看不到。

**候选 diff（`config.plist` → `NVRAM → Add → 7C436110-…:boot-args` 末尾追加两项）**：

```diff
-  <string>-v debug=0x100 keepsyms=1 -vi2c-force-polling nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0</string>
+  <string>-v debug=0x100 keepsyms=1 -vi2c-force-polling nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0 pci_log=0x200 pci_log_mode=0x3</string>
```

* `pci_log=0x200` = `ENUMERATION`（解析器会自己 `| ALWAYS_ON`）。
* `pci_log_mode=0x3` = `KPRINTF | IOLOG`（`0x1|0x2`）。选 IOLOG 是因为它走 `IOLog`（`-v` 上屏），
  选 KPRINTF 是因为它**不检查** `ml_get_interrupts_enabled()`，中断上下文里也能出。
  **两项都加**是为了在只有一次引导机会的前提下最大化上屏概率。

**预期观察**：
* (a) `PCI configuration begin` 之后**出现大量** `[PCIe:0 …ns] scan (boot) …` / `Found type N device …`
  → **立刻推翻 §1.4 的悲观读法**，而且能看到最后一条落在哪个设备；
* (b) 仍然只有那两行 → `doConfigure()` 内屏幕通道确实关闭，A **信息量为零**（这本身也是结论：
  必须换手段，例如只读比较 `pci_log_mode=0x1` 与 `0x4` 的差异）；
* (c) 新行停在一个具体设备/BAR → 直接定位，下一轮可以做**针对性**单变量。

**风险**：极低。不碰 `gIOPCIFlags`；不碰 ACPI/MMIO/kext；日志量增大可能把有用行刷出屏幕
（对策：拍照时对准**最后**一屏，并同时记录停留时长）。

**回滚**：把 `boot-args` 里的 ` pci_log=0x200 pci_log_mode=0x3` 删掉即可（`NVRAM → Delete` 已含 `boot-args`，
所以写入会生效）。

**不能证明什么**：日志没出现 ≠ 没发生（通道可能被关）。另外 `pci_log*` 的存在性
是本机取回的 IOPCIFamily 源码里确认的，**尚未与 macOS 24.6.0 逐版本对齐（U4）**；
若该内核不支持这两个 boot-arg，本轮的产出就是"什么都没变"，判据必须预先承认这种结果。

### 候选 B —— 单独 `DevirtualiseMmio=false`（`SetupVirtualMap` 保持 `true`）

**diff**：

```diff
   <key>DevirtualiseMmio</key>
-  <true/>
+  <false/>
   <key>SetupVirtualMap</key>
   <true/>
```

**依据**：本机**从未**测过；上游证据分裂（§2.5）。

**预期观察（三岔，必须预先写死）**：
| 结果 | 含义 | 下一步 |
|---|---|---|
| 屏幕越过 `PCI configuration` / 进入 Recovery | devirt 是本停点的变量 | 复测一次确认 |
| 退回 `EB.MM.AKM` / STOP 0x16（在 boot.efi 之前） | 与 issue #9 同型，devirt 在本机**必须开** | 记结论，回滚，转别的轴 |
| 停在**同一行** | 与 issue #10 一致，devirt 与本停点无关 | 记为"不足以移动停点"，**不排除**其影响 |

**风险**：本批候选中**最高** —— 可能连 `boot.efi` 都进不去。**回滚**：改回
`Copy-Item D:\_backup-round0\config.plist.round4 D:\EFI\OC\config.plist -Force`（写入前创建该备份）。

**不能证明什么**：同 §2.5 末条。

### 候选 C —— 删掉已证无效的 `SSDT-Disable_Network_GPP6`

**diff（`ACPI → Add` 的第 0 条）**：

```diff
   <dict>
     <key>Comment</key><string>SSDT-Disable_Network_GPP6.aml</string>
-    <key>Enabled</key><true/>
+    <key>Enabled</key><false/>
     <key>Path</key><string>SSDT-Disable_Network_GPP6.aml</string>
   </dict>
```

（也可以整条删除；`Enabled=false` 更利于回滚。）

**依据**：§2.4 —— 该表要在 `\_SB.PCI0.GPP6.WLAN` 下建 `_DSM`，而 DSDT `:15556` 已经定义了它，
所以它**每次引导都必然失败**（D6）。

**预期观察**：屏幕 ACPI 段 `3 table load failures` → **`2 table load failures`**，
`AE_ALREADY_EXISTS` 少一条。

**风险**：极低（该表从不生效，不改变任何行为）。

**信息量**：对 PCI 停点**低**；它的价值是**校准**——如果失败数确实 3→2，说明我们对
"哪张表为什么失败"的模型是**对的**，可以放心用它去解读"若 U1 成立会发生什么"。
如果**没有** 3→2，说明我们的模型有洞，必须回去修 §2.4。

**不能证明什么**：即使 3→2，也**不能**说明这三个错误与 PCI 停点无关。

### 候选 D —— `SSDT-PLUG-ALT` 的 A/B（禁用注入表）

**diff**：同候选 C 的写法，把 `ACPI → Add` 里 `SSDT-PLUG-ALT.aml` 那条 `Enabled` 置 `false`。

**依据**：§2.3（本机固件**自有** `\_SB.PLTF.C000..C00F`，注入表额外加了 16 个 `\_SB.C000..C00F`）
+ issue #21 第二位报告人"禁用 SSDT-PLUG-ALT 才越过 AppleACPICPU"。

**预期观察**：屏幕 ACPI 段的表清单少一行 `CpuPlugA`；`AppleACPICPU` 段是否变化；
停点是否移动。

**风险**：低–中。macOS 会失去 `plugin-type=1` 那个 `_DSM` → CPU 电源管理可能退化；
但这是 **Recovery**（不安装），可接受。PCI 设备节点不变（§2.3）。

**不能证明什么**：即使有变化，也分不清是 `plugin-type` 缺失还是"16 个多余 ACPI0007 节点"消失造成的。

### 候选 E —— `npci=0x3000` / BIOS Re-Size BAR：**登记但本轮不排入**

* `npci=0x3000`：1401 的 `bootfix.py` 阶梯恰好以它为终点，issue #23 里 `npci=0x2000`
  **确实**越过了本停点。但本机 Round 2 已证明 `npci=0x2000` 在**本停点无效**
  （`MBA:OUT` 含 `npci=0x2000`，屏幕照样停在 `PCI configuration begin`）。
  在先验概率低、且候选 A 尚未做完的情况下**不排入**；需单独批准。
* BIOS 关 Re-Size BAR：issue #23 的**唯一验证解法**，但**改 BIOS 超出当前授权**，不排入。
* OpenCore 侧的 `ResizeAppleGpuBars` / `ResizeGpuBars`：issue #23 明确记录 `ResizeGpuBars=13`
  会**破坏 GOP framebuffer**（选择界面变 4 列小字/不显示）。在拿到候选 A 的日志前**不动**。

### 4.6 推荐组合与判据

**推荐 Round 5 = 候选 A（唯一改动量：2 个 boot-arg 词）**；若用户希望顺带做一次"零行为变化"的校准，
可**同轮**加上候选 C（删无效注入表）。A + C 互不干扰：A 只加 boot-arg，C 只关一张**从不生效**的表。

**成功判据（预先写死）**
1. 对照未破：`MBA:OUT` 仍无 `npci`；四个 VoodooI2C 条目仍不注入；`OC: Prelinked status - Success`；
   `WRUNPROT 0 / RBMAP 1 / VMAP 1 / RTPERMS 1 / DEVMMIO 1` 保持不变。
2. A 生效：`PCI configuration begin` 之后出现 `[PCIe:0 …]` 前缀的 PCI 行。
3. C 生效：`table load failures` 由 `3` 变 `2`。
4. **停留时长 ≥10 分钟**，并明确回答是否出现 `[ PCI configuration end, bridges N, devices M ]`。

**失败判据**：若 A 没带来任何新行，本轮**只能**记为"PCI 日志通道在 `doConfigure()` 内不可用"，
**不能**记为"PCI 配置没有进展"。

---

## 5. 本轮明确不做

* ❌ 不写入 U 盘、不改 `config.plist`（本文件只给 diff）。
* ❌ 不改 BIOS / Windows EFI / BCD / 任何分区。
* ❌ 不试 `npci=0x3000`、不叠 `MmioWhitelist`、不动 `IOMMU`/`DisableIoMapper`。
* ❌ 不批量套用任何 ACPI 补丁；**特别是不搬 issue #21 的四个 DSDT Find/Replace**（§3.1）。
* ❌ 不进 Round 5，直到用户逐项批准且先回滚到已验证基线。

---

## 6. 本轮实际写入仓库的内容

| 文件 | 变化 |
|---|---|
| `logs/opencore-2026-10-13-095517.txt` | **新增**（Round 4 引导日志；已按 `scripts/scrub-log.py` 脱敏，11 行被替换，自检 `no real identity value remains`） |
| `docs/06-只读分析与Round5候选.md` | **新增**（本文件） |
| `docs/05-受控实验记录.md` | 追加 §7.10 / §7.11（Round 4 引导结果与判定），并指向本文件 |
| `README.md` | 追加 Round 4 实测结果段，并在文档索引里加入本文件 |

**未入库**（且不得入库）：`audit/acpi/firmware/**`（ACPI 二进制与反编译，含 `MSDM` 的 OEM 密钥）、
屏幕照片、任何 `.aml` / `.bin` / `.efi`。
