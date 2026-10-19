# 10 · Round 9 撤销与重规划（**只读研究；未写入 EFI、未执行**）

> 状态：**原候选已撤销**。本文件保留撤销理由，并给出重新规划后的**首选实验**。
> 卡上仍是 Round 7：`58E78A12C8102AF7A5DD3B2D7417BE891B17EFC78FF0817C99F69C6BC7A78CA3`（52123 B）。
> 本轮**未**写入 EFI / BIOS / Windows EFI / BCD，**未**改 BAR / `MmioWhitelist` / ACPI，**未**换 SMBIOS。

---

## 0. 结论摘要

1. **`pci-workloop-timeout-ms=2000` 判定为"信息增益不足"，撤销，不写入。**
2. 原文档里的**四条判据全部撤销**（见 §2）。
3. **本机没有能在 `doConfigure()` 内部取证的内核日志通道**（见 §3）——这是硬限制，不因换参数而改变。
4. 新首选实验改为**"USB4 隧道端口枚举对照"**：**零 EFI 改动**，但**必须先证明它真的改变了设备枚举集合**（见 §4）。

---

## 1. 逐条核对（源码 + 行号；每一条都独立致命）

### 1.1 `setMaximumLockTime(interval, 0)` **不会** panic —— 成立

`iokit/IOKit/IOWorkLoop.h`（xnu-11215.81.4）：

```
:344  /*! @function setMaximumLockTime
:347  *   @param options Pass IOWorkLoop::kTimeLockPanics to panic when the time is exceeded,
:348  *   otherwise a log will be generated with OSReportWithBacktrace().
:349  void setMaximumLockTime(uint64_t interval, uint32_t options);
:88   kTimeLockPanics = 0x00000002,
```

`iokit/Kernel/IOWorkLoop.cpp`：

```
:725  IOWorkLoop::lockTime(void)
:728      time = mach_absolute_time() - reserved->lockTime;
:731      if (kTimeLockPanics & reserved->options) {
:732          panic("IOWorkLoop %p lock time %qd us", this, time / 1000ULL);
:734      else
:734          OSReportWithBacktrace("IOWorkLoop %p lock time %qd us", this, time / 1000ULL);
```

IOPCIFamily 传的是 `_configWorkLoop->setMaximumLockTime(maxLockTime, 0)` ⇒ **options 不含 `kTimeLockPanics`**
⇒ 最好的情况也只是 `OSReportWithBacktrace()`（一条带调用栈的**日志**），**不是 panic**。

### 1.2 `lockTime()` **不是**独立定时器 —— 成立

`IOWorkLoop.cpp:94-103`：

```
:94   #define IOStatisticsOpenGate() \
:96       IOStatistics::countWorkLoopOpenGate(reserved->counter); \
:97       if (reserved->lockInterval) lockTime();                 \
:100  #define IOStatisticsCloseGate() \
:102      if (reserved->lockInterval) reserved->lockTime = mach_absolute_time();
```

`IOStatisticsOpenGate()` 的**全部**调用点只有三处：

```
:503  IOWorkLoop::openGate()      -> IOStatisticsOpenGate(); IORecursiveLockUnlock(gateLock);
:527  IOWorkLoop::sleepGate()     -> IOStatisticsOpenGate(); ... IORecursiveLockSleep(...)
:537  IOWorkLoop::sleepGate(AbsoluteTime) -> 同上
```

⇒ 测量发生在**释放门锁的那一刻**（或线程在门上睡眠时）。
⇒ **一个永不返回的动作 → 该线程永不 openGate → 永不测量 → 永不报告。**
"2 秒内必有可观察事件"**不成立**。

### 1.3 `IOKITSTATS` 是编译期开关 —— 成立（但本轮**未能**从本机内核证实其取值）

`IOWorkLoop.cpp:119` 在 `#else` 分支里：

```
#define IOStatisticsOpenGate()
#define IOStatisticsCloseGate()
...
```

`IOWorkLoop.h:40 / :161 / :286` 用 `#if IOKITSTATS` 包住这些成员与 `lockTime()` 声明。
⇒ 若目标内核 `IOKITSTATS=0`，**整套统计与超时检测根本不编译进内核**。

**我能证与不能证**：
* 能证：上述宏/条件编译结构来自 xnu 源码；**OpenCore DEBUG 构建与 XNU 内核构建配置无关**，不能互相推断。
* **不能证**：`xnu-11215` 系列在 apple-oss-distributions **只发布到 `11215.81.4`**（本轮实测 tag 列表：
  `11215.1.10 / 11215.41.3 / 11215.61.5 / 11215.81.4`），**macOS 15.6 的确切 tag 未发布**，
  所以我**没有** 15.6 RELEASE 内核里 `IOKITSTATS` 取值的直接证据。
  `BaseSystem.dmg` 是压缩容器，raw-string 搜索的**负结果不能当作证据**（本轮未据此下结论）。
* ⇒ **本条只作为独立疑点登记，不是结论依据** —— §1.1 / §1.2 / §1.4 已各自足够。

### 1.4 初始 `doConfigure()` **不经过**该工作环 —— 成立（最致命的一条）

`IOPCIFamily-681.140.3/IOPCIConfigurator.cpp`（本轮从上游重新取得）：

```
:440   configure(0);
:699   configure(kIOPCIConfiguratorBoot);          <- start() 里直接调用
:3360  doConfigure(options);                       <- configure() 内部的直接调用
```

并且本轮实测：**`IOPCIConfigurator.cpp` 全文对 `_configWorkLoop` 的引用为 0 命中**。
⇒ 初始 PCI 配置**根本不在任何工作环动作里**执行，`lockTime()` 与它无关 ——
即使 §1.1/§1.2/§1.3 全部反过来，这条也把该判据否掉了。

**（工作环确实被用，但用在别处）**：`IOPCIBridge.cpp:1075` 的 `_configWorkLoop->runAction(… configOp …)`
是**单次配置空间读写**走的路径，不是 `configure()` 的驱动者。

---

## 2. 撤销的判据（**全部停止使用**）

| 原判据 | 为什么错 | 状态 |
|---|---|---|
| "2 秒后必然 panic / 重启 / 出栈" | §1.1 无 panic；§1.2 无定时器；§1.4 不走工作环 | ⛔ **撤销** |
| ">10 分钟无变化即可排除 gated 操作" | 检测机制本身可能一次都不运行 ⇒ 未观测 ≠ 未发生 | ⛔ **撤销** |
| "超时报告能直接识别具体 PCI 设备" | 无 panic 就没栈；即使有栈也只是代码路径，不指认硬件 | ⛔ **撤销** |
| "看到 `[ PCI configuration end ]` 就证明是节流/重试" | 无法区分"变快"与"换了路径" | ⛔ **撤销** |

**⇒ 判定：`pci-workloop-timeout-ms` 候选信息增益不足，不建议执行。本轮不申请写入。**

---

## 3. 观测渠道清单（诚实版，逐项给依据）

| 渠道 | 本机可用？ | 依据 |
|---|---|---|
| **串口 / UART** | ❌ 无 | 该机型没有可用串口（此前各轮已确认） |
| **kdp（内核调试协议）** | ❌ | kdp 需要受支持的传输（以太网 / FireWire）；本机 macOS 侧只有不受支持的 WiFi，且调试内核需要另一台机器直连 |
| **屏幕 `-v`** | ⚠️ 部分 | 可用，但 `doConfigure()` 期间 `kPEDisableScreen(-1)` **关屏** ⇒ **恰好在需要的地方失明**；没有任何 boot-arg 能阻止 IOPCIFamily 关屏 |
| **NVRAM `ApplePanic` → 下次 OpenCore 日志** | ⚠️ **仅当发生 panic** | 本轮在**卡上的 `OpenCore.efi`** 里实测到字符串 `ApplePanic`（2 次）与 `Panic log`（1 次）⇒ 通道**存在**；但它只在**真的 panic 之后**才产出内容，而 §1 已证明**没有可靠手段让参数自动引发 panic** |
| **macOS 用户态 / IOPlatformExpert 日志** | ❌ | 本机 macOS 从未到达用户态 |

> **目前的结论（限定版，用户 2026-10-17 第 4 条要求）**：
> **目前没有经过验证、在现有硬件和工具条件下可用的早期内核取证通道。**
> "没有找到可行方法"**不等于**"证明所有调试方法都不存在" —— 上面是一份**已尝试清单**，
> 不是存在性否定；若将来出现新的可用手段（另一台机器上的串口/kdp、可验证的持久日志机制等），
> 结论必须随之更新。
> 因此**下一阶段的实验不能建立在"抓取内部日志"上**，只能建立在
> **"改变可见状态并观察状态转移"** 上。任何声称"加参数就能拿到栈"的方案都应先被 §1 的四条筛掉。

---

## 4. 新首选实验：**USB4 隧道端口枚举对照**（零 EFI 改动）

### 4.1 为什么是这个

* **完全不需要内核日志**：判据是**屏幕上可见的状态转移**（是否出现 `[ PCI configuration end ]`、停留时长、最后一行）。
* **零 EFI 改动**：卡保持 Round 7 原样 ⇒ 没有"写盘"风险，回滚 = 把设备拔掉。
* **直击已有证据链**：GP11（`00:03.1`，`1022:14EF`）已由**本机固件**证实是 USB4/Thunderbolt 隧道端口
  （`\_SB.PCI0.GP11._DEP` → `\_SB.PCI0.GP19.NHI0`，见 `docs/08` §11.6），
  且它是**唯一没有下游设备的桥**。所以"隧道端口的存在与否会不会移动停点"是一个**有靶点的**问题。
* **可证伪**：无论结果如何都能排除或指认一大块（见 4.3 判据）。

### 4.2 阶段 0 —— **强制前置**：先证明它真的改变了枚举集合（只读，Windows 侧即可）

> ⚠️ **本节的判据已被 §6.1 更正并降级**；且 **Windows 有隧道 ≠ macOS 早期也有**（Windows USB4 Connection Manager 可能在 OS 接管后才建隧道）。以 §6 为准。

用**已入库**的只读工具链，在**插着**与**拔掉** USB4/TB 设备两种状态下各采一次：

```powershell
# 只读；盘符按实际传入，不要假定 D:
pnputil /enum-devices /connected /deviceids /relations /location /properties /resources `
         /format xml /output-file pnputil-all.xml
python audit\pci-windows-audit.py pnputil-all.xml --cfgmgr <1401>\plan.json --out audit\results\pci-windows-<date>
pwsh -File audit\dump-logconf.ps1                     # 若需要注册表侧对照
python audit\pci-logconf-audit.py registry-logconf-all.txt pnputil-all.xml --out audit\results\pci-logconf-<date>
```

**判据（阶段 0，必须满足其一）**：

| 判据 | 观察 | 含义 | 对阶段 1 的影响 |
|---|---|---|---|
| **0-α** | 出现**新的 PCI 功能**，且其 `LocationPaths` 落在 `00:03.1`（GP11）之下 | 枚举集合**确实变了**，且 **GP11 被确认为隧道端口** | ✅ 阶段 1 **有效**，可以执行 |
| **0-β** | 新功能出现在**别处**（例如 `00:08.3`/GP19 之下、或 GP17/18） | **GP11 不是**该设备的隧道端口 | ⛔ 阶段 1 前提被推翻；改为重新核查 GP11 的真实角色（**这本身是高价值结果**） |
| **0-γ** | 什么都没多出来（总线/功能数不变） | 该测试**不改变**枚举集合 | ⛔ 按用户要求：**不得**当作隔离对照使用 |

**⚠️ 关于"额外收益"的更正（用户 2026-10-17 第 2 条）**：
新功能落在某条总线 `B` 上，**只能**说明"至少有某个隧道端口用了 `B`"，
**不能**推出 GP11 的精确 `Secondary/Subordinate`。例如新功能出现在 `0x20`，
**不能**证明 GP11 `secondary=0x05` 且 `subordinate=0x64`。
**完整边界仍然只能靠读取桥的配置空间寄存器（`0x18/0x19/0x1A`）**。
⇒ 阶段 0 得到的总线号**只能当作"与模型一致 / 不一致"的弱证据**，
**不得**把"总线范围预测"升级成"直接证实"。**本文件不再做这种升级。**

### 4.3 阶段 1 —— 引导对照（**需另行批准**；仍然**零 EFI 改动**）

> ⚠️ **本节的否定性判据已被 §6.1(3) 降级**（"仍卡 10 分钟"不得写成"彻底排除 GP11"；"出现 end"不得直接认定根因，必须先复测并排查冷启动/供电/固件状态差异）。

* **单变量**：USB4 设备 **在 / 不在**。
* **做法**：卡保持 Round 7，仅两次引导（无设备一次、插设备一次），各记录：
  ① 是否出现 `[ PCI configuration end, bridges … ]`；② 从 `PCI configuration PCI0` 起的停留时长（精确到分钟）；
  ③ 屏幕最后一行（拍照）；④ 是否重启/panic。
* **预登记判据**：

| 判据 | 观察 | 结论 |
|---|---|---|
| **1-α** | 出现 `[ PCI configuration end … ]`（无论多慢） | 停点**特异地**与"空隧道端口 / 链路未训练"相关 ⇒ 得到**具体靶点** |
| **1-β** | 仍静默 ≥10 min，与无设备时**无差别** | **GP11 的隧道枚举不是触发条件**；且因阶段 0 已证明枚举集合确实变了，**这不是空对照** |
| **1-γ** | 停点**换位置**或更早/更晚出现其它行 | 隧道路径被牵涉，记录新停点 |

* **风险**：
  * 设备热插拔本身低风险；不写任何持久状态；
  * **若 BIOS 需要打开 Thunderbolt 安全/枚举设置才能让设备出现** ⇒ **停止**，**不得**改 BIOS；
  * 引导风险与既有各轮相同（我们本来就在反复引导这台机器）。
* **回滚**：拔掉设备即可；无任何持久改动（**这本轮就没写 EFI**）。
* **不能证明什么**：不能证明"隧道端口是唯一原因"；`1-β` 只能排除**这一条**通路；
  也不能替代 macOS 侧的资源读数。

### 4.4 前置条件与备选

* **前置条件**：手头有一个能被 USB4/Thunderbolt 隧道枚举的 PCIe 设备（TB/USB4 NVMe 盒、TB 扩展坞等）。
* **备选**：若本机有空 M.2 插槽，可用"空槽/插卡"做同类对照 —— 但**必须先确认** 1401 的配置没有用
  `SSDT-Disable_…` 把该设备在 macOS 侧关掉（若已关掉，则 macOS 侧看不出变化 ⇒ **无效**），
  且需要拆机，优先级低于 USB4 方案。
* **明确不推荐**：继续换 boot-arg 赌 panic；`npci` 轴（已关闭）；隐藏 GP11 / 加 SSDT（禁止且凭猜测）；
  `MmioWhitelist`（禁止）；用 Linux 读数推断 macOS（`docs/09` 已否）。

---

## 5. 给下一轮立的规矩（本轮教训）

1. 任何"能拿到栈/panic"的提案，必须**先**说明：定时器在哪、由谁在什么条件下触发、目标内核是否编译了那段代码。
2. 任何"隔离对照"，必须**先**证明它真的改变了枚举集合（如 §4.2）。
3. **没有观测渠道时，只设计"改变可见状态"的实验**，并**明说**它不能证明什么。
4. 不要把"未观测到"当作"未发生"。


---

## 6. 2026-10-17 修订：三处判据更正 + 阶段 0 执行结果

### 6.1 三处判据更正（用户审核）

**(1) Windows 有 PCIe 隧道 ≠ macOS 早期也有。**
Windows 的 **USB4 Connection Manager** 负责 USB4 隧道的建立与管理，
**可能在 OS 接管之后**才创建 PCIe 隧道。
⇒ **阶段 0 只能证明"设备能改变 Windows 的 PCI 枚举集合"，不能证明 XNU 的 `doConfigure()` 会看到同样的变化。**

**(2) 新设备的总线号不能推出 GP11 的精确边界。** 见 §4.2 的更正框。

**(3) 阶段 0 / 阶段 1 的否定性判据全部降级：**

| 观察 | ❌ 不得得出 | ✅ 只能说 |
|---|---|---|
| 新 PCI 功能出现在**其它路径** | "GP11 不是 USB4 隧道端口" | 这台设备**没有**经 GP11 隧道；GP11 的角色**待定** |
| **Windows** 下 GP11 出现子设备 | "macOS 会枚举它" | Windows 枚举了它；**macOS 侧未知** |
| 插设备后**仍卡 ≥10 min** | "彻底排除 GP11" | 在"该设备在场"这一条件下**没有观察到差别**；GP11 仍未被排除 |
| 插设备后出现 `[ PCI configuration end ]` | "空隧道端口就是根因" | 出现了状态转移；**必须复测**，并先排查冷启动/热启动差异、设备供电、固件（M.2/USB4 控制器）状态差异 |

### 6.2 阶段 0 执行结果（2026-10-17 22:51，Windows，只读）

* **快照 A 已采集**（无外接 USB4/TB 设备）：`audit/round9/A-*`（本地，不入库）。
  `pnputil` 全量 XML + **实时**注册表 `LogConf`（**未使用旧 `plan.json`**）。
  解析结果：**42 个 PCI 功能 / 9 座桥**；`LogConf` 设备 25；`BootConfig` 17/17、需求清单 25/25 全部逐字节自洽。
* **B 无法执行** —— 操作者手头**没有**符合要求的设备：
  * 被询问的"D: 盘"经只读核实是 **`15B7:5009` NVMe，挂在 `00:01.2`（新出现的 `GPP1`）之下**，
    `Get-PhysicalDisk` 报 `BusType = NVMe`，容量 238.5 GB ⇒ 这是**内置 M.2 SSD**，不是 USB4/TB 隧道设备；
  * 另一块 `SMI SM3350`（59.6 GB）`BusType = USB` ⇒ **USB 大容量设备**，按规则**不算**。
  * ⇒ 按用户条件（不得为实验采购硬件），**阶段 0 判定为"当前不可行"**，到此停止。

### 6.3 ⚠️ 本轮顺带发现的**平台状态变化**（必须记录，否则后续对比不成立）

> **2026-10-19 更正**：dGPU 消失的原因**已确认** —— 是操作者当时把机器切到了**集显模式（GPU 模式切换）**，现已切回。**原因已知、可逆、非故障。**重采基线见 **§7**（三态对照与更强的结构证据）；本节作为当时的原始记录保留。

快照 A 与 Round 8 快照（2026-10-13）**不是同一个平台状态**：

| 项 | Round 8（10-13） | 快照 A（10-17） |
|---|---|---|
| dGPU | **`01:00.0` RTX 4050 存在**（`10DE:28E1`） | **不存在** —— 全表 **0 个 `10DE` 设备**；`00:01.1`（GPP0）**无子设备** |
| 桥数量 | 8 | **9**（新增 `00:01.2` = `GPP1`） |
| 新设备 | — | `02:00.0` = `15B7:5009` NVMe（D:，SN530）挂在 `GPP1` 下 |
| 在用总线 | `0x00,0x01,0x02,0x03,0x04,0x65,0x66,0x67` | `0x00,0x02,0x03,0x04,0x05,0x66,0x67,0x68` |

* **直接后果**：Round 7 卡上的配置（含 `UEFI.Quirks.ResizeGpuBars=0`）是针对"dGPU 在场"的机器做的；
  **现在 dGPU 不在枚举里**，任何新的 macOS 引导都是**另一种平台状态**，与 Rounds 2/4/6/7 **不可直接比较**。
  若将来要恢复对照，必须先确认 dGPU 为何消失（**通过 Armoury Crate 的 GPU 模式 / MUX、还是别的**），
  并**重新建立基线**——这属于硬件/固件状态变更，需要单独评估与批准，**本轮不做**。
* **顺带的正面观察（仍然只是弱证据）**：`0x05`（低端最大在用总线）与 `0x66`（高端最小在用总线）
  之间**仍然恰好是 96 条总线**；而总线整体**整体右移了 1**（原 `0x04→0x65` 之间也是 96）。
  ⇒ **"96 条连续空洞的大小"是不变量**，但**它的起始总线号随下方分配而移动**
  ⇒ 这**已经否定**了"`secondary=0x05` 是一个固定属性"的说法（阶段 0 前它只是预测，现在更接近被证伪），
  同时**不否定**"存在一段固定大小的连续预留"这一模型。**寄存器仍未读，边界仍未知。**


---

## 7. 2026-10-19 更新：dGPU 原因已确认 + 三态对照 + 新的零 EFI 单变量候选

### 7.1 那个"平台状态变化"的原因已确定

操作者说明：**当时把机器切到了"集显模式"（GPU 模式切换），所以 dGPU 从枚举里消失；现已切回。**
⇒ §6.3 里"原因不明"的保留意见**撤销**：这是**已知、可逆、由操作者主动触发**的状态，不是故障。

### 7.2 重采基线（快照 A′，2026-10-19 18:22，Windows，只读）

`pnputil` 全量 + **实时**注册表 `LogConf`（仍未使用旧 `plan.json`）：
**44 个 PCI 功能 / 9 座桥 / 27 个 LogConf 设备**；`BootConfig` **18/18**、需求清单 **27/27** 逐字节自洽；
BusNumber 描述符 **0**。

* **dGPU 已回来**：`01:00.0` RTX 4050 + `01:00.1` HDA，父桥 `00:01.1`（GPP0）✓
* **第二块 NVMe 仍在**：`00:01.2`（**GPP1**）→ `02:00.0` = `15B7:5009`（那块新 SSD）

### 7.3 三态对照：**96 条空洞是"不变量"，位置随下方分配移动**

| 状态 | 日期 | PCI 功能 | 桥 | 低端在用总线 | 高端起始总线 | 空洞大小 |
|---|---|---|---|---|---|---|
| Round 8 | 10-13 | 42 | 8 | `0x00–0x04` | `0x65` | **96**（`0x05–0x64`） |
| **A**（集显模式） | 10-17 | 42 | 9 | `0x00`,`0x02–0x05` | `0x66` | **96**（`0x06–0x65`） |
| **A′**（混合模式，双 NVMe） | 10-19 | **44** | 9 | `0x00–0x05` | `0x66` | **96**（`0x06–0x65`） |

* 三个独立开机状态给出**同一个公式**：
  **高端起始总线 = (低端最大已分配总线) + 96 + 1**。
* ⇒ **"96 条连续空洞"现在是三态一致的定量规律**（比之前只有两个状态强得多），
  与"某处预留了一段**固定大小**的连续总线"的模型高度一致。
* ❗ **仍然不是**寄存器读数：它**不能**证明那 96 条属于 **GP11**，
  也**不能**给出 GP11 的 `Secondary/Subordinate`（用户第 2 条约束不变）。
* ❗ **`secondary=0x05` 这个具体数值已被证伪**：当前状态（A′）空洞是 `0x06–0x65`，
  起始号随下方分配移动。**固定的是"大小"，不是"起点"。**

### 7.4 由此得到一条**可证伪的预登记预测**（给将来的 USB4 阶段 0）

> **预测 P1**：若将来插入一个**真正走 USB4/雷电 PCIe 隧道**的设备，
> 它**应当**落在当前空洞 `0x06–0x65` 之内（并挂在某个隧道根端口之下）。
> **若它落在空洞之外**，则"GP11（或某个根端口）独占这段 96 条连续预留"的模型**被证伪**，
> 必须重新解释这段空洞的来源。**两种结果都必须照实记录。**

### 7.5 新的**候选**（仅提议，**未批准、未执行**）：GPU 模式单变量隔离

**为什么它是目前最好的候选**

| 维度 | 说明 |
|---|---|
| **单变量已验证** | A 与 A′ 之间**只差 GPU 模式**（同为双 NVMe、同一台机器、同一张卡），而枚举集合**确实变了**：44 vs 42 个功能、GPP0 有/无子设备、总线 `0x01` 在用/不在用 ⇒ **满足"先证明它改变枚举集合"的要求** |
| **零 EFI 改动** | 卡保持 Round 7；**不写任何配置**；不碰 BIOS 设置、不碰 ACPI/SSDT/`MmioWhitelist`/BAR |
| **可逆** | 回滚 = 把 GPU 模式切回去（操作者已会） |
| **直击一大类假设** | Rounds 4/6/7 的整条 **dGPU/BAR 轴**（含 `UEFI.Quirks.ResizeGpuBars`）都建立在"dGPU 在场"之上。**dGPU 不在场时停点是否改变**，直接判定这条轴是"必要条件"还是"无关" |
| **可证伪** | 结果只有三种（见下），每种都排除或指认一大块 |

**做法（未来，需单独批准）**：卡保持 Round 7，只在**两种 GPU 模式**下各做一次引导，记录：
① 是否出现 `[ PCI configuration end … ]`；② 从 `PCI configuration PCI0` 起的停留时长；③ 屏幕最后一行；④ 是否 panic/重启。

**预登记判据**

| 判据 | 观察 | 结论 | 边界 |
|---|---|---|---|
| **G-α** | 集显模式下**仍然**静默 ≥10 min | **dGPU 不是停点的必要条件** ⇒ 整条 dGPU/BAR 轴**大幅降权**（Rounds 4/6/7 的目标设备可以被排除在"触发条件"之外） | 不能推出"与 dGPU 完全无关"；只能说"dGPU 不在场时停点不变" |
| **G-β** | 集显模式下出现 `[ PCI configuration end … ]` 或明显不同的停点 | **dGPU 在场与否是分水岭** ⇒ 得到**具体靶点**（dGPU 枚举或其父桥 GPP0 的资源配置） | **必须复测**（冷/热启动各一次），先排除偶发与固件状态差异，才可认定 |
| **G-γ** | 集显模式下停点更早（例如更早的另一行） | 说明 dGPU 影响的是**更前面**的阶段 | 记录新停点，重新定位 |

**风险**：与既往各轮同级的引导风险；GPU 模式切换由操作者用现有工具完成，**不改 BIOS 设置项**、
不写 EFI、不写 Windows EFI/BCD；**若切换后 Windows 或引导出现异常 ⇒ 立即切回并记录"实验无法完成"**。

**为什么它优于 USB4 方案（当前）**：USB4 方案**缺少合格外设**（阶段 0 的 B 无法执行，已停）；
而 GPU 模式**手头就有**，且**枚举差异已被实测证明**。

### 7.6 与 Round 8 相比，当前基线**仍有**一处真实差异（必须记住）

即使 dGPU 已回来，**当前机器比 Round 8 多一块 NVMe**（`00:01.2`/GPP1 → `02:00.0`）。
⇒ **任何新的 macOS 引导与 Rounds 2/4/6/7 不可逐字等同**：多了一个 PCIe 设备与一座桥。
若要严格复现旧基线，需要（由操作者决定、本轮不做）**移除那块 SSD** 或**在对比时明确把它列为差异项**。

---

## 8. 2026-10-19 重定方向：撤销 §7.5，Round 10 = 最终硬件配置下的**完整屏录**基线（零 EFI 改动）

### 8.0 方向变更（用户指令）
- §7.5 的 GPU 模式 A₁→B→A₂ 对照**正式撤销，不再执行**。
- 最终环境锁定：**独显模式（内屏由 RTX 4050 接管）+ 两块 NVMe 长期保留**；
  第二块 NVMe 是 macOS 安装目标，**不是需要排除的变量**。
- 不再以增加文档/代码行数作为进度；不再扩大没有决策价值的 Windows 静态审计。

### 8.1 本次只读核实结果（2026-10-19，Windows，未改任何设置）

| 核实项 | 结果 | 依据 |
|---|---|---|
| RTX 4050 在场 | ✅ `01:00.0` `10DE:28E1` + `01:00.1` `10DE:22BE`，父桥 `00:01.1`（DSDT `GPP0`，`_ADR 0x00010001`） | `DEVPKEY_Device_BusNumber` = 1 |
| **内屏由 RTX 4050 接管** | ✅ 内屏 `BOE0CA4`（NE140QDM-NX7）**父设备就是 `PCI\VEN_10DE&DEV_28E1`**；780M 名下无任何显示器；内屏连接类型 `0x0B`（eDP） | `DEVPKEY_Device_Parent` + `WmiMonitorConnectionParams` |
| 两块 NVMe 均在 PCI 树内 | ✅ 见下表 | — |
| 仍是 Round 7 原始配置 | ✅ `config.plist` `58E78A12…`（52123 B）、`OpenCore.efi` `1569CD1D…` | SHA-256 |

| 盘 | 型号 | PCI 路径 | 总线 | 父桥（ACPI） | 角色 |
|---|---|---|---|---|---|
| `15B7:5017` | WD PC SN740 512G | `PciRoot(0x0)/Pci(0x2,0x4)/Pci(0x0,0x0)` | `0x05` | `00:02.4` = `GPP8`（`\_SB.PCI0.GPP8.NVME`） | Windows（C:） |
| `15B7:5009` | WDC PC SN530 256G | `PciRoot(0x0)/Pci(0x1,0x2)/Pci(0x0,0x0)` | `0x02` | `00:01.2` = `GPP1`（DSDT `_ADR 0x00010002`；**厂商 ACPI 无具名子节点**） | **macOS 目标盘**（现为 D:，NTFS） |

实测总线分布：`0x00–0x05` 在用；`0x66`（iGPU / PSP / xHCI / ACP / HDA）、`0x67`（AMD PCI + NPU）、
`0x68`（AMD PCI + xHCI + USB4 NHI `1022:1668`）；中间 `0x06–0x65` 共 96 条仍空。

### 8.2 与"此前硬件状态"耦合的配置项（逐项判定）

| 配置 | 目标 | 判定 |
|---|---|---|
| DeviceProperties `Pci(0x1,0x1)/Pci(0x0,0x0)` → `acpi-wake-type=1` | **RTX 4050** | 独显模式下路径始终存在，保留 |
| DeviceProperties `Pci(0x8,0x1)/Pci(0x0,0x0)` → `disable-gpu=true` | **780M iGPU**（`00:08.1` → 总线 `0x66`） | 路径有效。**⚠️ 初稿此处写"Recovery 必然黑屏"是错的，见 §9.1**：Recovery 走的是**固件屏幕**（`IONDRVFramebuffer` 匹配 `.Display_boot`），不需要任何 GPU 驱动，所以 iGPU 被关不影响 Recovery 显示 |
| DeviceProperties `Pci(0x8,0x1)/Pci(0x0,0x6)` → `layout-id=56` | `1022:15E3` ACP 音频 | 实测位于 `0x66:00.6` ✅ |
| `SSDT-Disable_Network_GPP6` | `\_SB.PCI0.GPP6.WLAN`（`Pci(0x2,0x2)`） | MT7922 仍在 bus `0x04`、父桥 `00:02.2` ⇒ 路径有效；但 `docs/03` 已证明该表因 `AE_ALREADY_EXISTS` **从未生效** |
| `boot-args nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth` + `Drivers/NullMothLogo.efi` | NullMoth / NVIDIA 驱动 | **驱动未注入**：`Kexts/` 无 NVRM/NVRMFB/NMDRM，只有 logo 驱动；NullMoth `README.txt` 写明「**After macOS finishes installing**」才装驱动 ⇒ 这些参数当前**无消费者、纯惰性**，不是停点原因，但必须记住 |
| `UEFI.Quirks.ResizeGpuBars=0` / `Booter.Quirks.ResizeAppleGpuBars=0` | GPU BAR | **⚠️ 初稿结论写反了，此处更正：`0` 表示「启用」，`-1` 才表示「禁用」**（OpenCorePkg `963025f`：`OpenCoreUefi.c:982-987` 与 `ServiceOverrides.c:1255-1259` 都以 `>= 0` 判定是否执行）。本轮日志自身即可证实：`OC: Setting GPU BARs to 0` → UEFI 阶段 `RBAR 2/3 supports 0x3FC0, sizing 0 inc 1 results setting from 13 to 6`，Apple 阶段 `inc 0 results setting from 6 to 6`。⇒ **RTX 4050 BAR1 的 8 GiB→64 MiB 双阶段缩容在 Round 7 是「生效且被读回验证」的当前状态，不是历史失效结论** |
| `Misc.Debug.ApplePanic=true` | panic 落盘 | **已开启**；12 份 OC 日志每次都打印 `OC: Panic log does not exist`，`E:\` 下无 `panic-*.txt` ⇒ 通道被检查过，但从未命中 |

### 8.3 结论：**暂不具备值得冒险的 EFI 修改**（三条独立理由）
1. **看得见的那行没有信息量** —— `docs/03` §2：屏幕在两条可见消息之后第 3 行即被关闭，`doConfigure()` 全程遮挡；
   且恢复屏幕那步在 `fPFMConsole` 失效时会被**跳过**，所以「黑屏」既不等于「卡在里面」，也不等于「停住」。
2. **停点归属未定** —— `docs/03` §4：`[ PCI configuration begin ]` 有两个出处（`IOLog`+`bootConfig` / `DLOG_A`），
   `DLOG_A` 在当前 RELEASE 内是否生效无法确认；"首次 / 二次配置"的二分法**已撤销**。
   **分辨之前改参数就是猜。**
3. **最终硬件配置从未引导过** —— 此时改 EFI，会把"EFI 变量"与"硬件拓扑变量"混在同一轮里。

### 8.4 Round 10（**零 EFI 改动**）：完整屏录 / 全程连拍基线引导
**变量**：无。卡保持 `58E78A12…`。
**本轮的目标定位（用户审核后收窄）**：只建立**最终硬件配置下的实际启动观察基线**，
**不承诺**分辨"首次 / 二次 PCI 配置"。保留以下五类证据：

1. 从 OpenCore 选择器到**停止变化那一刻**的手机视频。
2. 最后可见屏幕，以及从该状态开始的观察时长。
3. 约 10 分钟时的照片。
4. 新生成的 OpenCore DEBUG 日志，以及与 Round 7（`opencore-2026-10-13-213656.txt`）的差异。
5. 是否进入 Recovery、是否 panic / 重启、是否出现任何新画面。

> **证据等级提醒**：OpenCore DEBUG 日志只覆盖 **OpenCore 阶段**（到 `EXITBS:START` 为止），
> **不包含 XNU 内部的 PCI 配置轨迹**。因此它只能用于核验 OC 阶段行为（补丁是否应用、BAR 是否缩容、
> MMIO 去虚拟化、交接是否完成），**不能**当作内核侧证据使用。

1. 用手机**录像**整个引导（从选中 macOS 到停住，停住后再录 10 分钟）。不能录像就**从第一行开始连拍**，
   **不要只拍底部** —— 关键是停点上方那几百行。
2. 停住后**不要按键**，按批准的时间窗停留约 **10 分钟**，再长按电源关机。
3. 回 Windows 后把新 `opencore-*.txt` 的文件名告诉我（内容我自己脱敏后再分析）。
4. 若出现任何**新内容**（`[ PCI configuration end … ]`、panic 文本、进度条），立即拍照并关机，**不要交互**。

预登记判据（**只登记观察与证据等级，不做归因**）：

| 观察 | 记录方式 | 证据等级 |
|---|---|---|
| 屏幕完全停在现状、10 分钟无变化 | 记为"可见进展停止"，**不断言**内核卡死在哪条指令 | 直接观察 |
| 出现 `[ PCI configuration end, bridges N, devices M ]` | 逐字抄下 N / M，与 Windows 实测（9 桥 / 44 功能）并列，**不解释差异原因** | 直接观察（内核 `IOLog`） |
| 出现 panic 文本 / 重启 / 新画面 | 拍照并立即关机，不做归因 | 直接观察 |
| 录像里出现**更早**一组相同日志 | 只作为**待交叉核对**的线索；需与 `DLOG_A` 是否生效、`addHostBridge` 调用时机分别核对后才可讨论"是否重配置" | 间接 / 待核实 |
| OC 日志与 Round 7 的差异 | 逐条列出（补丁结果、BAR 缩容、MMIO、交接）；只用于 **OpenCore 阶段**结论 | 直接观察（OC 阶段） |
| 进入 Recovery | **先记录成功状态，不操作磁盘、不立即断电**，等人工决定 | 直接观察 |

**风险**：与既往各轮同级的引导风险；不写 EFI / 不写 BIOS / 不写任何 NVMe / 不碰 Windows 引导。
**回滚**：无需（零改动）。若选择器损坏，用固件启动菜单进 Windows，记录"实验无法完成"。

### 8.5 执行前校验与硬约束（2026-10-19 用户批准后登记）

**执行前必须逐个核对（任一不符 ⇒ 不启动）：**

| 项 | 期望值 | 2026-10-19 18:59 实测 |
|---|---|---|
| `EFI\OC\config.plist` SHA-256 | `58E78A12C8102AF7A5DD3B2D7417BE891B17EFC78FF0817C99F69C6BC7A78CA3` | ✅ 一致 |
| `EFI\OC\OpenCore.efi` SHA-256 | `1569CD1D183C5EE9FDA2ECED767A4B2EFA307E6EDFCF2A50109C9657098671FF` | ✅ 一致 |
| 卡上是否已有本轮新日志 | 启动前应**没有**比 `2026-10-13-213656` 更新的 `opencore-*.txt` | ✅ 没有（最新仍是 10-13 21:37） |

**硬约束（全程不变）：**
- RTX 4050 独显模式，**不切换 GPU 模式**。
- 两块 NVMe 全程保留；**SN530 256 GB 是 macOS 安装目标，禁止格式化 / 改分区**。
- Windows 仍由固件 **Windows Boot Manager** 启动，不动 EFI/BCD。
- **不执行 Reset NVRAM**。
- **不增加任何**启动参数、驱动、ACPI 补丁或 DeviceProperties（本轮零改动）。
- **只执行一次**基线启动。
- 读回日志后**先脱敏**，带设备身份信息的原始日志**不推送**公开仓库。

### 8.6 Round 10 已执行（2026-10-19 19:07）—— 结果与下一步

**结果：未进入 Recovery，无 panic。** 详细对照见 `docs/03` §5。三句要点：

1. **OpenCore 阶段与 Round 7 逐项相同**：quirk 汇总逐字一致、`MAT support is 1`、GPU BAR `13→6` 与 Apple 阶段 `6→6`、MMIO devirt 同样 5 个区域、27 条补丁全 Success、`EXITBS:START` 正常交接。
2. **硬件差异已被两边同时量化**：OC 看见 **45** 个 PCI 功能（Round 7 为 43）、**45** 张 ACPI 表（44），
   多出的一张是 OEM 段为 `NVME` 的 SSDT（1858 B，第二块 M.2 插槽），且 **`IVRS` 由 504 B 增至 568 B**。
3. **可见进展更早**：末屏最后一行是 `RTC: Only single RAM bank (128 bytes)`，
   屏幕上**没有** Round 7 末屏那对 `[ PCI configuration begin ]` / `configure() PCI configuration PCI0`。

**下一步唯一值得做的方向（需另行批准，本轮不执行）：先解决"这一帧是停住还是屏幕停止更新"。**
因为它是所有归因的前置：若为停住 ⇒ 停点已前移到 PCI 配置之前，此前七轮关于 PCI 的结论对最终配置**不适用**；
若为屏幕停止更新 ⇒ 内核可能已跑到 Round 7 或更远，只是不可见，此时追 PCI 参数是错的。
判定手段按约定就是**引导录像**（本次未提供）；若录像仍不可得，则退一步：
在同一硬件配置下再引导一次并**只拍"停止那一刻之前的 30 秒"**，观察画面是否发生重绘/变黑/跳变。

若确认是"真停住"，下一个技术靶点已经明确：**新增的 OEM `NVME` SSDT 与 `IVRS` 变化**
（它们是本次唯一被实测证实的、与停点前移同时发生的差异），且都在 PCI 配置之前生效。

> **⚠️ 2026-10-19 再次修正（用户指令）**：§8.6 里"先解决录像"的要求作废 —— 操作者明确不提供录像、
> 不做重复引导。下面 §9 改为**纯只读的可行性 + 已知前置条件复核**，不再依赖任何新观察。

---

## 9. 显示可行性复核与 Round 11 候选（2026-10-19，只读）

### 9.1 显示路径的四层复核 —— **结论修正：Recovery 有可用显示路径**

依据是**两类一手来源**：① Apple 开源代码（`IOGraphics` / `xnu`）；② NullMoth 驱动仓库的第一方文档（本机 `src/nvidia-macos-driver-main/`，并与**上游 `main` 当日全文核对过**）。

- **通用帧缓冲是 Apple 自己实现的**：`IOGraphics/IOGraphicsFamily/IOBootFramebuffer.cpp`，文件头注释 *"Boot video dumb frambuffer shim"*，是 `IOFramebuffer` 的子类，靠 `AAPL,boot-display` + PE console info 匹配。
- **文本控制台与 GPU 驱动无关**：`xnu/osfmk/console/video_console.c` 的 `initialize_screen(PE_Video *boot_vinfo)`，一切绘制都写到 `vinfo.v_baseaddr`（即 booter 的 framebuffer）。

| 层 | 谁在驱动它 | 是否需要 NVIDIA kext | 本机状态 |
|---|---|---|---|
| ① OpenCore 选择器 | 固件 GOP | 不需要 | ✅ 可见（一直可见） |
| ② 内核早期文本（`-v`） | **固件屏幕**：`IONDRVFramebuffer` 匹配 `.Display_boot`（NVRMFB `Info.plist` 注释：`.Display_boot, probe 20000`） | **不需要** | ✅ 可见（`RTC:` 等全部输出） |
| ③ **Recovery 图形界面** | **同 ① / ②** —— `HOW-IT-WORKS.md:90`：「The macOS installer has no NVIDIA driver, so it **runs on the firmware's screen**」 | **不需要** | ⚠️ **机制上可行，但官方明确不保证**（见下） |
| ④ 安装后的加速桌面 | NullMoth：`NVRMFB`(IOFramebuffer) + `NVAccel` + `NVRMAGDC` + `NVRM` + GSP 固件 | 需要（且只能装到 `/Library/Extensions`） | 未安装（正常，安装阶段不该有） |

⇒ **§8.2 里"两块 GPU 都不参与显示 ⇒ Recovery 必然黑屏"是错的，已就地更正。**
⇒ macOS 确实有一个"通用帧缓冲"路径（`IONDRVSupport` → `IONDRVFramebuffer` → `.Display_boot` 的固件 framebuffer），
所以 **iGPU 被 `disable-gpu` 关掉、dGPU 无 Apple 驱动，都不妨碍 Recovery 显示**。
⇒ 这也解释了为什么屏幕能一路打到 `RTC:`：那本来就是固件屏幕在输出。

> **必须同时记住的官方保留意见**（`p1401/nullmoth.py:63-64`）：
> *"Firmware output may appear during boot, but it does not establish that the installer or
> accelerated desktop will work on this panel."*
> ⇒ ③ 只能记为「**路径存在**」，**不能**记为「Recovery 一定能显示」。
> 另：`IONDRVFramebuffer` 只是"能接管固件 framebuffer"，它在我们的面板上是否成功初始化，本轮没有证据。

**并且：驱动仓库**（`HOW-IT-WORKS.md:54-56`）**给了排除注入的硬理由**：
> *"They are not injected by OpenCore: the display kexts link against Apple frameworks
> (IOGraphicsFamily, IOAcceleratorFamily2) that only exist in macOS's own kernel collections."*

⇒ **"把 kext 注入 EFI 换取安装期显示"不仅不被推荐，而是按设计不可行**，已彻底排除。
⇒ 顺带：`NMIntelFB` 的 `IOPCIPatch` 是 `0x00008086`（**仅 Intel**），所以"用 iGPU 当屏幕"这条路对本机 **不存在**。

### 9.2 与第一方"安装器配方"逐项比对 —— **只差一个标量**

`HOW-IT-WORKS.md:90-93` 给出的安装器（= Recovery）配方，与本机卡上配置对照：

| 项 | 安装器要求（第一方原文） | 卡上现状 | 判定 |
|---|---|---|---|
| `Booter → Quirks → ResizeAppleGpuBars` | `0`（"small BAR"，否则固件屏幕在 macOS 的 PCI 设置后活不下来） | `0` | ✅ |
| `UEFI → Quirks → ResizeGpuBars` | **`-1`**（UEFI 阶段**不要**动 BAR） | **`0`**（UEFI 阶段把 13→6，再"Reprogrammed BARs to original"） | **❌ 唯一不符** |
| `Kernel → Block` | **不排除** `com.apple.iokit.IONDRVSupport` | 空列表（未排除） | ✅ |
| `csr-active-config` | `<430A0000>` | `<43 0A 00 00>` = `0x00000A43`，与日志 `AAPL: #[EB|CSR:OUT] 0x00000A43` 一致 | ✅ |
| `boot-args` | 含 `amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0` | 完全一致 | ✅ |
| `SecureBootModel` | `Disabled` | `Disabled` | ✅ |
| BIOS Above 4G Decoding | 开 | 开（RTX 4050 BAR1 = `0x200000000` = 8 GiB > 4 GiB，实测） | ✅ |
| 无 `nv_disable=1` / 无 `agdpmod=pikera` / 无 WhateverGreen NVIDIA 补丁 | 无 | 无 | ✅ |

⇒ **本机 EFI 与 NullMoth 官方"安装器配方"只差 `UEFI → Quirks → ResizeGpuBars` 一个整数。**

**第二处独立印证**（不只是驱动 README）：装机工具生成安装盘时同样采用该配方。
**⚠️ 2026-10-19 用户审核更正：不能把 `p1401/efidoctor.py:90-93` 当作"同时改两个 Quirk"的代码依据** ——
那一处只直接校正 `Booter` 侧的值；两个 Quirk 的完整生成逻辑在
`https://github.com/nullmoth/1401/blob/main/p1401/policy.py`。
⇒ 本节结论仍成立（上游 `HOW-IT-WORKS.md` 原文 + `policy.py`），但**引用口径已按此更正**。

### 9.2b 实验定位更正：**Round 11 不是首次尝试，而是最终硬件配置下的重验证**

| 配置来源 | `UEFI.Quirks.ResizeGpuBars` | `Booter.Quirks.ResizeAppleGpuBars` | 证据 |
|---|---|---|---|
| **Round 4 基线**（`efi-snapshots/round4-r7-baseline/EFI/OC/config.plist`，`021F02B3…`，52124 B） | **`-1`** | `0` | 本地快照实测读取 |
| **Round 7 / 当前卡上**（`58E78A12…`，52123 B） | **`0`** | `0` | 卡上实测读取 |

⇒ **Round 4 与 Round 6 已经用过 `UEFI=-1、Booter=0`，当时未进入 Recovery。**
⇒ Round 11 的目标组合（`-1` / `0`）**等于 Round 4 基线的那一对值**；它改变的只是"When"（UEFI 阶段是否缩容），
不改变 Apple 阶段（仍为 `0`）。
⇒ **Round 11 的正确定位：在最终硬件配置（RTX 4050 直连 + 双 NVMe）下，对上游安装器推荐设置的一次重新验证。**
⇒ **不得**描述成"首次尝试"，**不得**宣称成功率高；它的价值在于"要么推进、要么把 BAR 通道这一小类排除掉"。

### 9.3 Round 11 候选（**单变量**；未批准、未执行）

**改动：`UEFI → Quirks → ResizeGpuBars`：`0` → `-1`。仅此一处，其它全部不动。**

- **为什么优先**：第一方文档把 UEFI 阶段的 BAR 改动明确排除在安装器配方之外；而 `ResizeAppleGpuBars = 0`
  保留不动，正好维持"macOS 侧小 BAR ⇒ 固件屏幕能活过 PCI 设置"这一条要求。
  这也与已观察到的现象自洽：屏幕在早期正常、在 macOS 开始 PCI 设置之后不再更新。
- **预期结果**：若停住与 UEFI 阶段的 BAR 重编程有关，屏幕应在 `RTC:` 之后继续出现新行，乃至出现
  `[ PCI configuration end, bridges N, devices M ]` 或 Recovery 图形界面；
  若屏幕仍在同一处停住，则**该假设被证伪**，说明停点与 BAR 通道无关 —— 这本身是有效结论。
- **风险**：极低。这是**去掉一次修改**而不是引入修改；OpenCore 不再动 GPU BAR，固件原始布局保留，
  对 Windows 只会更安全。
- **精确 diff**（`config.plist`，`UEFI → Quirks`）：
  ```diff
  @@ UEFI -> Quirks @@
      <key>ResizeGpuBars</key>
  -   <integer>0</integer>
  +   <integer>-1</integer>
  ```
  行号需在写入前用 `Select-String` 定位；`-1` 是 `integer`，不是字符串。
- **回滚**：把该值改回 `0`（一处整数）。config 备份见 `E:\_backup-round0\config.plist.round4-restored`
  （`021F02B3…`）；整卡回滚 `robocopy C:\Users\24269\Documents\macos\efi-snapshots\round4-r7-baseline\EFI <盘符>:\EFI /MIR`。
- **它不做什么**：不改 SMBIOS、不碰 ACPI/SSDT、不碰 NVRAM、不碰两块 NVMe、不碰 Windows 引导、不切 GPU 模式。

### 9.4 未纳入本轮、但属于"未来安装成功后"的已知前置（记录，不执行）

| 项 | 驱动阶段要求 | 与本机现状 |
|---|---|---|
| `UEFI.ResizeGpuBars` / `Booter.ResizeAppleGpuBars` | `13` / `-1`（装完驱动后切换） | 现为 `0` / `0`（安装器态） |
| `Kernel → Block` | **排除** `com.apple.iokit.IONDRVSupport` | 现为不排除（安装器态） |
| SMBIOS | 需「能在 macOS 15 上跑且有独显」的机型，第一方测试 `iMacPro1,1` | 现为 `MacBookPro16,2`（**无独显机型**） |
| RTX 4050 Laptop（Ada `10DE:28E1`） | 在设备表内，但**物理验证 Pending**；公开 issue 里**没有 RTX 4050 Laptop 的成功记录** | 未知，属最大不确定性 |

⇒ 这几项都**只能**在 macOS 装好之后再动（1401 Mac app 会自动切换），**现在改它们没有意义**。

**关于 RTX 4050（`10DE:28E1`）支持程度的准确表述**（逐条有出处）：

| 结论 | 依据 |
|---|---|
| **`28E1` 明确在设备表内** | `nvidia_gsp_ids.json:195`：`"28E1": "NVIDIA GeForce RTX 4050 Laptop GPU"`；`package/install.sh:104` 的 `SUPPORTED_IDS` 也硬编码了 `28E1` |
| 但"测试过"的只有 **`2D05`（RTX 5060 桌面）** | `nvidia_gsp_ids.json:3-5`；`CARD-SUPPORT.md:65-74` 的渲染/CI/MPS 证据仅限该卡 + macOS 15.8.1 |
| **Ada（RTX 40，含笔记本）物理验证 = Pending** | `CARD-SUPPORT.md:11-16` |
| 设备表 ≠ 可用 | `CARD-SUPPORT.md:5-9`：*"A device-table match does not establish that a particular laptop's display routing, firmware, BAR placement, or macOS installation works."* |
| 只提供 4 个 kext：`NVRM / NVAccel / NVRMFB / NVRMAGDC` | `package/install.sh:8`；`NMDRM / NMHDA / NMIntelFB` 不在发布包里 |
| 出像素的最小集 = `NVRM` + `NVRMFB`；`NVAccel` 是 WindowServer 的硬条件 | `NVRMFB` 是唯一 `IOFramebuffer`（`nvrm-fb.cpp:172`）；缺 `NVAccel` 时 `install.sh:249-251` 记录 WindowServer "Failed to create MetalDevice" |
| 内屏背光是独立问题 | 需 `nvRmRegisterBacklight` + NBCI `_DSM`（`nvrm-fb.cpp:1858-1867`）；1.14.1 因"挂死引导"**移除了**自动笔记本亮度，改为 `nvrmacpibl=1` 才启用（`RELEASE-1.14.1.md:9-12`）|

⇒ **"RTX 4050 能不能用"的诚实答案：ID 被支持、代码路径覆盖、但该 SKU 从未被物理验证，且公开 issue 里没有成功记录。**

### 9.5 外部案例与一手来源（2026-10-19 在线核实）

**A. 安装器配方的时效性已核对（重要）**
本机源码副本是 `1.14.2`，而上游当日为 `v2.3.7`。我拉取了**上游 `main` 的 `docs/HOW-IT-WORKS.md` 全文**核对：
`L94-96` 仍原样写着 *"…it runs on the firmware's screen, which only survives macOS's PCI setup with a small BAR:
`ResizeAppleGpuBars = 0`, `ResizeGpuBars = -1`, and `IONDRVSupport` not excluded."*
⇒ **§9.2 的对照不是基于过期文档**，配方在当前版本未变。

**B. 显示机制的一手依据（Apple 源码）**

| 事实 | 来源 |
|---|---|
| macOS 有"傻瓜帧缓冲" | `IOGraphics/IOGraphicsFamily/IOBootFramebuffer.cpp`，*"Boot video dumb frambuffer shim"*，`IOFramebuffer` 子类，匹配 `AAPL,boot-display` |
| 文本控制台不依赖 GPU 驱动 | `xnu/osfmk/console/video_console.c`：`initialize_screen(PE_Video *)`，绘制到 `v_baseaddr` |
| 无加速时的代价 | Dortania：回落到 VESA/CPU 绘制时"many basic functions of macOS are broken… including sleep and general stability" |

**C. 无加速安装器/桌面**：NullMoth 仓库有**两份独立报告**——#68 *"Install macOS 15.8.1 via 1401 installer (runs successfully in unaccelerated 25MB VESA mode)"*、#16 *"booted successfully and reached the desktop using basic framebuffer output (5MB)"*。**[COMM]** 级别，无日志佐证，但方向与第一方"安装器跑在固件屏幕上"一致。

**D. 同类机器（全部带来源等级）**

| 案例 | 配置 | 结果 | 等级 |
|---|---|---|---|
| **#155** | i7-13620H + **RTX 4060 Laptop `10de:28e0`**（与 `28E1` 同 AD107 芯片）+ BIOS Discrete | ✅ 内屏 1080p **已加速**，Metal 3 | [COMM]，最接近的正面先例 |
| #15 | Ryzen 5800H + RTX 3070 Laptop + BIOS Discrete | ✅ eDP 可用（需 `nv_acpi _DSM` 补丁 + Algrey/Zormeister Fix PAT） | [COMM] |
| **#252** | Arrow Lake-HX + RTX 5070 Ti，**面板硬接 dGPU、iGPU 已关** | ❌ **冻结在 EXITBS:START 之后**，未解决 | [COMM]，与本机形态最像的失败案例 |
| 本机同型号 | amd-osx 论坛 "Asus TuF Gaming A14 FA401UU"（8845HS/780M/RTX 4050） | ❌ 版主结论"两块 GPU 都不兼容，建议用 VM" | [COMM]；**该帖早于 NullMoth 发布（2026-02-?? vs 2026-10-07）**，且无裸机 OpenCore 尝试记录 |
| 780M iGPU | NootedRed 官方表只覆盖 Vega Raven（Ryzen 1xxx–5xxx、7x30）；RDNA3 请求 #362/#357/#238 均已关闭未实现 | **无任何驱动** | [PROJ-DOC] 高 |

**E. 一条对本机配置的正面确认**：`#15` 指出混合/直连场景下 **iGPU 必须被隐藏**（`disable-gpu` 或 `-wegnoegpu`）。
本机 `DeviceProperties` 正好对 iGPU 设了 `disable-gpu=true` ⇒ **这个设置是对的，不要删**。

**F. 结论等级**：在"Phoenix/780M + Ada + 直连 eDP"这一具体组合上，**没有正面案例，也没有带日志的失败write-up**。
⇒ 对"Recovery 能否出图形界面"只能记为 **undetermined**（机制存在且被 Apple 源码证实，但本组合无实例）。
