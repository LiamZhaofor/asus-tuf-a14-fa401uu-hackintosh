# ASUS TUF Gaming A14 (FA401UU) — macOS 15 Sequoia + NVIDIA RTX 4050

> 用 [NullMoth NVIDIA 驱动](https://github.com/nullmoth/nvidia-macos-driver) 在 **RTX 4050 Laptop** 上跑起硬件加速的 macOS 15 Sequoia。
> 本仓库记录这台具体机型的完整踩坑过程、已验证配置、真实引导日志与排错脚本。
>
> **状态：进行中（未安装完成）。** 第一轮修好了"`boot-args` 从未生效"这个把此前所有结论都
> 污染掉的问题（`npci=0x2000` 已真正进入内核）；第二轮（禁用 VoodooI2C 家族）已执行，
> 六项预注册检查**全部符合预期**。屏幕最后停在 `PCI configuration begin`，但**没有停留时长**，
> 因此**尚不能**判定为永久卡死。第三轮（只移除 `npci=0x2000`）**已写入卡上、待引导验证**
> （将记录 ≥10 分钟停留情况）—— 见 [受控实验记录](docs/05-受控实验记录.md) 与
> [引导排错实录](docs/03-引导排错实录.md)。

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
hardware/本机配置摘要.md           脱敏后的硬件清单
efi/config.plist                 与卡上一致的配置（SMBIOS 身份已抹除）
efi/README.md                    kext 清单与用 1401 重建的方法
logs/opencore-*.txt              6 份真实 OpenCore 引导日志（已脱敏）
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
