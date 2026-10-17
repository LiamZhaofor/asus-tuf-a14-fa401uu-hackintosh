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

> **明确结论：本机不存在能在 `doConfigure()` 内部取证的内核日志通道。**
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

**可能的额外收益（也许能闭合最后一个开放问题）**：
若新功能出现在某条总线 `B` 上，那么 `B` 就是该隧道端口的**实际次级总线**。
若 `B` 落在 **`0x05–0x64`** 区间内，则"`secondary=0x05 / subordinate=0x64`"的**预测被直接证实**
（这仍然不是配置空间寄存器读数，但已经是**实测的总线号**，比现在的纯推断强一个等级）。
反之若 `B` 在区间外，该预测即被**证伪** —— 两种结果都有价值。

### 4.3 阶段 1 —— 引导对照（**需另行批准**；仍然**零 EFI 改动**）

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
