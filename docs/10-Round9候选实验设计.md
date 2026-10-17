# 10 · Round 9 候选实验设计（**只给候选与证据，未写入 EFI、未执行**）

> 状态：**候选**。本轮**不改** U 盘 EFI、**不改** BIOS / ReBAR / `MmioWhitelist` / Windows EFI / BCD / 分区，
> **不加入** SSDT，**不隐藏 GP11**，**不执行** Round 9。
> 基线：卡上仍是 Round 7（`config.plist` = `58E78A12C8102AF7A5DD3B2D7417BE891B17EFC78FF0817C99F69C6BC7A78CA3`，52123 B）。

---

## 1. 结论先行

**唯一候选：给现有 boot-args 追加一个参数 `pci-workloop-timeout-ms=2000`，其余一个字节都不改。**

* 它**不改变寻址、不改变资源配置、不改变 ACPI、不碰任何设备**；
* 它做的是**给 IOPCIConfigurator 的工作环装一个 2 秒看门狗**；
* 于是"静默卡 10 分钟以上"会被**强制变成一个可在数秒内判读的事件** —— 这正是本轮缺的东西；
* 判读结果是**三态**，分别指向"设备/配置空间访问"、"桥枚举/资源配置逻辑"或"其它"。

---

## 2. 证据链：为什么停点就在 `doConfigure()` 里面

### 2.1 停点定位（**用 681.140.3 —— 即 macOS 15.6 那份源码**，不是本地那份 726）

用户要求"结合 XNU/IOPCIFamily 源码"。本地 `audit/iopicifamily/` 是 **726.0.5**，
所以本轮**重新从上游取了 `IOPCIFamily-681.140.3`** 的 `IOPCIConfigurator.cpp` 与 `IOPCIBridge.cpp` 来对照
（`raw.githubusercontent.com/apple-oss-distributions/IOPCIFamily/IOPCIFamily-681.140.3/…`）。

`IOPCIConfigurator.cpp`（681.140.3）的 `configure()`：

| 行 | 代码 | 与屏幕的关系 |
|---|---|---|
| `:3324` | `if (bootConfig) IOLog("[ PCI configuration begin ]\n");` | 屏幕第一行 |
| `:3321`/`:3357` | `IOLog("[IOPCIConfigurator::%s()] PCI configuration %s\n", __func__, …)` | 屏幕第二行（`PCI configuration PCI0`） |
| `:3360` | `doConfigure(options);` | **停点在这之后、`:3402` 之前** |
| `:3402` | `if (bootConfig) IOLog("[ PCI configuration end, bridges %d, devices %d ]\n", …)` | **从未出现** |

⇒ **停点被夹在 `doConfigure()` 内部**，不是 ACPI 解析、不是 MAT、不是 `_CRS` 读取、也不是驱动匹配
（驱动匹配在 `configure()` 返回之后）。

### 2.2 为什么"没有新输出"**不能**当作"没有进展"

`doConfigure()` 内部调用 `kPEDisableScreen(-1)` 把 PE 屏幕**关掉**，返回后才重新打开
（`docs/06` §7 已记录这一机制）。
⇒ **在停点期间，屏幕本来就不会更新**。
所以历史上"≥10 分钟无新输出"只能说明**没有走到 `[ PCI configuration end ]`**，
**不能**说明内核在死循环、也不能说明它没有在推进。

这一点决定了 Round 9 的设计目标：**必须想办法把一个"看不见的等待"变成一个"看得见的事件"**，
而不是再换一个配置去赌。

### 2.3 `doConfigure()` 内部包含的三类工作（对应三个假设）

| 假设 | 在 `doConfigure()` 里的位置 | 若成立，实验应看到什么 |
|---|---|---|
| **A 桥枚举** | 遍历桥、读 secondary/subordinate、递归扫总线 | 与"总线/设备集合"相关；与地址空间余量无关 |
| **B 资源配置** | 为每个 range 分配地址、编程桥的 base/limit | 与地址空间/窗口/对齐相关（`npci`、RBAR 都属于这一轴） |
| **C 设备初始化/访问** | 对设备做配置空间读写、链路/电源等待（`waitForLinkUp`、`setPowerStateGated` 等 **gated** 动作） | 会被"工作环看门狗"捕获 —— **这就是下面那个实验要分离的** |

### 2.4 这个轴**在 681 上确实可用**（已核实，不是从 726 推的）

在 `IOPCIBridge.cpp`（681.140.3）里：

```c
// pci-workloop-timeout-ms is passed to IOWorkLoop::setMaximumLockTime(); see IOWorkLoop.h
uint64_t workloopTimeout;
if (!PE_parse_boot_argn("pci-workloop-timeout-ms", &workloopTimeout, sizeof(workloopTimeout)))
    workloopTimeout = 0;
if (workloopTimeout) {
    uint64_t maxLockTime;
    clock_interval_to_absolutetime_interval(workloopTimeout, kMillisecondScale, &maxLockTime);
    _configWorkLoop->setMaximumLockTime(maxLockTime, 0);
}
```

* 同一个文件在 681 里**有** `pci-workloop-timeout-ms`（2 处）、`pci-aspm-default`（2 处）、`pci-dev-aspm-default`（3 处）；
* 681 里**没有** `pci_log`（0 处）—— 与之前"`pci_log` 只在 726 系列"的结论一致；
* 681 里**没有** `pci-uncached-link-status`（0 处，726 才有）。
* ⇒ **本候选不依赖任何"726 才有"的东西**，这是本轮特意核实的。

`_configWorkLoop` 是 IOPCIConfigurator 的**唯一**工作环，配置空间读写
（`configOp`、`probeBusGated` 等）都在它上面串行执行。
`setMaximumLockTime()` 就是 IOKit 的"动作超时"机制：
**一次 gated 动作占用工作环超过该时限，就会被判定为超时并报告**。

---

## 3. 实验设计（单变量）

| 项 | 内容 |
|---|---|
| **基线** | 卡上现有 Round 7 配置（`58E78A12…`），**不改任何结构** |
| **唯一改动** | `NVRAM → Add → 7C436110-AB2A-4BBB-A880-FE41995C9F82 → boot-args`：在现有字符串**末尾追加** ` pci-workloop-timeout-ms=2000` |
| **现有 boot-args（逐字）** | `-v debug=0x100 keepsyms=1 -vi2c-force-polling nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0` |
| **为什么 2000 ms** | 正常配置空间操作是**微秒级**，2 s 不可能误伤正常流程；同时远小于操作者已有的 ≥10 min 观察窗，任何超时都会**明显早于**现在的静默期出现 |
| **不改的东西** | 不加/不减 kext、不改 `DeviceProperties`、不改 `Booter/UEFI/Kernel` 任何 quirk、不改 ACPI、不隐藏 GP11、不碰 `MmioWhitelist`/BAR/BIOS |
| **观测** | ① 屏幕是否出现 `[ PCI configuration end … ]`；② 是否出现 panic 画面/栈回溯（`keepsyms=1` 已开）；③ **是否在卡住后约 2 秒发生重启或停机**；④ 总停留时长（精确到分钟） |
| **执行方式** | 与以往各轮相同：先出候选 → 展示 diff → 用户批准 → 校验基线 SHA → 备份 → 单点改动 → `ocvalidate` → 读回校验 |

### 3.1 预登记判据（**三态，互斥**）

| 判据 | 观察 | 结论 | 下一步 |
|---|---|---|---|
| **α** | 卡住后**数秒内**出现：panic 画面/栈回溯，**或**明确的"重启/停机"（时间戳与进入停点相差约 2 s） | **停点发生在一个 gated 工作环动作里** ⇒ 属于 **C（设备访问/初始化）** 这一类 | 读栈顶：`IOPCIBridge::configOp` / `readConfig` → 配置空间读被卡；`probeBusGated` → 扫总线时被卡；`waitForLinkUp` / `setPowerStateGated` → 链路/电源等待被卡。**栈里出现的设备与桥名就是靶点**，下一轮才谈针对性动作 |
| **β** | 行为**完全不变**：仍然静默 ≥10 min，无 panic、无重启、`[ PCI configuration end ]` 不出现 | 停点**不在** gated 动作里 ⇒ 排除 C 的这一大类，指向 **A（桥枚举）或 B（资源配置）** 的**非 gated 逻辑**（纯 C++ 循环/分配器） | 下一轮转向"A vs B"的分离：用**地址空间压力**或**总线集合**作为单变量（需要单独的、明确批准的杠杆），而不是继续猜设备 |
| **γ** | 出现**第三种**变化：例如**真的走到了** `[ PCI configuration end ]`，或停点**提前/推后**到另一行 | 说明这个"等待"其实是被当作重试/节流在用 ⇒ 停点与**时序**相关，不是死锁 | 记录新的停点，重新定位（不追加改动） |

### 3.2 ⚠️ 必须预登记的**可见性不确定性**（否则会被误判成 β）

`doConfigure()` 期间屏幕是**关闭**的，而 `setMaximumLockTime(maxLockTime, 0)` 的第二个实参是 `0`。
因此有两种可能的表现形式：

1. **panic 可见**（`debug=0x100 keepsyms=1` 已开）⇒ 直接拿到栈，α 成立且信息量最大；
2. **panic/超时不可见**（屏幕仍关闭）⇒ 此时**只能靠"卡住后约 2 s 的重启/停机"**来判定 α。

⇒ **判读时必须同时记录"是否重启/停机"与"时间差"**；只有"既没有栈、也没有重启、也没有走到 end"才算 β。
**这一点写在预登记里，避免把"看不见的 α"错记成 β。**

---

## 4. 风险与回滚

| 项 | 评估 |
|---|---|
| **改的是什么** | **仅 boot-args 字符串**（NVRAM 注入），EFI 结构、驱动、ACPI、设备属性**全部不动** |
| **对新配置的风险等级** | **低**。最坏结果是"更早 panic/重启"，不会写坏任何持久状态 |
| **对卡的风险** | 与以往各轮相同：单点编辑 + 基线 SHA 校验 + 备份 + `ocvalidate` + 读回校验；`apply-roundN-stick.py` 会在任一预条件不满足时**拒绝写入** |
| **回滚** | 一步：`Copy-Item D:\_backup-round0\config.plist.round4-pre-r7 D:\EFI\OC\config.plist -Force`（或 Round 7 备份）；整套 EFI 回滚：`robocopy <round4-r7-baseline>\EFI D:\EFI /MIR` |
| **若选择器黑屏** | 用**固件启动菜单**直接进 Windows，本轮记"实验无法完成"，**不叠加修改** |
| **禁止项** | 不改 BIOS/ReBAR、不改 `MmioWhitelist`、不改 Windows EFI/BCD/内置分区、不换 `OpenCore.efi`、不加驱动、不加 SSDT、**不隐藏 GP11** |

---

## 5. 这个实验**不能**证明什么

1. **不能**直接区分 A 与 B —— β 只把范围收窄到"A 或 B 的非 gated 逻辑"，**不是**二选一。
2. **不能**证明停点与 `configure()` 的死锁有关：α 只说明"某个 gated 动作超过了 2 s"，
   而"超过 2 s"既可能是**永久卡死**，也可能是**极其缓慢**（例如链路超时重试）。
3. **不能**证明某个具体设备有故障 —— 栈只能给出**被卡住的代码路径**，不能证明硬件坏。
4. **不能**替代 macOS 侧的资源读数（仍然没有）。
5. **不是**修复：它**不改变** macOS 能否进入 Recovery 的概率，只提高**可观测性**。

---

## 6. 为什么**不**选其它候选（明确排除理由）

| 候选 | 排除理由 |
|---|---|
| 继续调 `npci=` / `pci=` 的寻址位 | 用户已指示**停止** npci 轴；R2（`0x2000`）、R6（`0x3000`）都已失败 |
| 8 GiB BAR 实验（Round 4 基线 + `ResizeAppleGpuBars=-1`） | 已按用户指示**降级**；且它属于 B 轴，在 A/B/C 未分离前做它信息量低 |
| 隐藏/禁用 GP11、加 SSDT 绕过 USB4 端口 | **禁止**，且是**凭猜测**的动作；本轮已用固件证据证明 GP11 是 USB4 隧道端口，不是异常 |
| `MmioWhitelist` | 用户明确禁止 |
| 用 Linux 读数推断 macOS | `docs/09` 已明确：Linux 读数**不能**替代 macOS 的枚举结果 |
| `SetupVirtualMap` / `DevirtualiseMmio` 组合 | R5B 已测（零内核输出）；且它们属于 Booter 内存映射轴，不是"区分 A/B/C"的杠杆 |
| 加 `-x` 安全模式 | 对 `configure()` 之前的路径几乎没有影响，信息量低 |

---

## 7. 若 α 成立，下一轮的自然延伸（**现在不做，仅登记**）

* 栈若指向**链路/电源等待**（`waitForLinkUp`、`setPowerStateGated`）：
  下一个单变量是 `pci-aspm-default=0`（**681 里有**，已核实），检验 ASPM/L1 是否是链路卡住的原因。
* 栈若指向**配置空间读**（`configOp`/`readConfig`）且出现具体设备：
  才轮到讨论"是否要针对该设备做 ACPI/属性层面的处理" —— 仍然需要用户单独批准。
* 若 β：把单变量换成"地址空间压力"（B 轴）或"总线集合"（A 轴），
  但这两个杠杆都必须**先**得到明确批准，且**不能**用 `pci=realloc` 之类的重分配参数伪装成"只读"。

---

## 8. 结论

**这是目前唯一一个"单变量、低风险、可回滚、且能把不可见等待变成可判读事件"的实验。**
它不承诺修好任何东西；它承诺的是：**要么拿到一个指名道姓的栈，要么排除一整个类别。**
在拿到那个判读之前，Round 10 及以后的一切写盘类实验都应当被认为**没有靶点**。
