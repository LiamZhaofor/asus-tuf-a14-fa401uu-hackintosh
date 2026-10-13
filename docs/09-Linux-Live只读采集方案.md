# 09 · Linux Live 只读采集方案（**已准备，按条件执行；本轮未执行**）

> 状态：**预案**。用户 2026-10-13 指示："**先完成 Windows 侧采集并提交结果，再判断是否有必要使用 Linux Live。**"
> Windows 侧采集已完成（`docs/08` §11），结论是**目前不必为"资源冲突"问题去用 Linux**
> —— 见 §8 的触发条件。本文随时可执行。

---

## 1. 这一步能回答什么、不能回答什么

| | 内容 |
|---|---|
| ✅ **只有 Linux 能给** | **桥的寄存器原值**：`Primary / Secondary / Subordinate Bus Number`（配置空间 `0x18/0x19/0x1A`）、`Memory Base/Limit`（`0x20–0x23`）、**`Prefetchable Memory Base/Limit`（`0x24–0x27`，含 64 位那一对）**、`PCI Command/Status`（`0x04/0x06`）。Windows 的用户态 API **取不到**这些（`docs/08` §11.7） |
| ✅ **顺带** | 一份**第三个内核**（既非 Windows 也非 macOS）对**同一硬件**的分配结论，用来把"Windows 侧干净"与"硬件/固件本身干净"分开 |
| ❌ **仍然不能** | 看到 **macOS** 的 PCI 分配（`docs/06` §7）；也不能把"Linux 正常"当成"macOS 的 `IOPCIFamily` 也正常"（`docs/08` §10.5 第 6 条） |
| ❌ **仍然不能** | 解释 Round 7 的 `[IOPCIConfigurator::configure()] PCI configuration PCI0` 停点。本方案**只**产出"资源/枚举是否一致"的判据，**不产出因果** |

**读数的语义（必须写进记录）**：`lspci` / `/proc/iomem` 反映的是
**Linux 内核初始化之后**的设备状态。
它**不等于** UEFI 固件的原始值（Linux 可能改写过桥窗口），**更不等于** macOS 的分配结果。
要接近"固件原值"，只能靠**不做任何重分配**（见 §5 禁令）来逼近，不能靠断言。

---

## 2. 硬性约束（违反即作废本轮）

1. **不修改 EFI**。本轮不动 `D:\EFI`（Round 7 配置 `58E78A12…` 原样保留）。
2. **从固件启动菜单直接引导 Linux，不经过 OpenCore。**
   理由：Round 7 卡上的 `UEFI.Quirks.ResizeGpuBars = 0` 会在 UEFI 早期把 dGPU BAR1 缩到 64 MiB；
   经过 OpenCore 引导会把这个副作用带进基线。
   做法：开机按 `Esc` / `F8`（ASUS）进 **Boot Menu**，选择 **`UEFI: <Linux 介质名>`**，
   **不要**选 `OpenCore` / `macOS` 那一项。
   核验：进入 Linux 后 `dmesg | grep -i -c 'oc:'` 应为 0（OpenCore 的日志不会出现在 Linux dmesg，
   这里只作为"我确实没走 OC 那条路"的操作记录）。
3. **禁止任何写操作**：
   * ❌ `setpci` 写（任何形式）；
   * ❌ `pci=realloc` / `pci=nocrs` / `pci=assign-busses` 之类**改变分配行为**的内核参数；
   * ❌ 设备复位（`echo 1 > .../reset`）、驱动解绑（`echo > .../driver/unbind`）；
   * ❌ `rmmod` 任何 PCI 相关驱动；
   * ❌ 写任何 PCI 配置寄存器、改 BIOS 设置。
4. **用一块与 macOS 安装盘不同的 U 盘**。**不要**把 Live 镜像写到 `D:`（macOS 引导盘）。
   写入前先确认盘符与容量，`diskpart` 的 `list disk` 结果要**逐条核对**。
5. **采集前记录现场**：BIOS 版本、是否插着 macOS 盘、外接设备清单 —— 跨轮次比较需要。

---

## 3. 第一阶段：采集（用户给定的命令，逐字）

```bash
mkdir -p ~/pci-audit

lspci -Dnn > ~/pci-audit/devices.txt            # 全部功能：域:总线:设备.功能 + 供应商:设备 + 类名
lspci -Dtvnn > ~/pci-audit/topology.txt         # 树形拓扑（父子关系、总线层级）
sudo lspci -Dnnvv > ~/pci-audit/verbose.txt     # 详细：BAR、桥窗口、LnkCap/LnkSta、Slot、能力
sudo dmesg > ~/pci-audit/dmesg.txt              # 内核日志：资源分配/失败/异常
sudo cat /proc/iomem > ~/pci-audit/iomem.txt    # 物理 MMIO 分配（谁占了哪段）
```

> ⚠️ **`~/pci-audit` 在 Live 环境下通常在内存（tmpfs）里，关机即丢。**
> 采集完立刻复制到**另一块 FAT32 介质**（不是 `D:`），或当场逐份上传。
> 复制前记下每份文件的 sha256，便于事后校验未被改动。

### 3.1 第一阶段的可选补充（仍然是只读，且不改变分配）

```bash
sudo lspci -Dnnvvv > ~/pci-audit/verbose3.txt   # 再详细一档（含更多能力结构）
sudo cat /proc/interrupts > ~/pci-audit/interrupts.txt
sudo cat /sys/kernel/debug/pci/* 2>/dev/null > ~/pci-audit/debugfs-pci.txt
uname -a > ~/pci-audit/kernel.txt ; cat /proc/cmdline >> ~/pci-audit/kernel.txt
sudo dmidecode -t bios -t system > ~/pci-audit/dmidecode.txt   # ⚠️ 含序列号，入库前必须脱敏
```

### 3.2 第二阶段：**有限的**原始配置空间读取（**先评估、后执行**）

**不要**对全部设备执行 `lspci -xxxx`（用户明确要求）。只有在第一阶段**显示某座桥确实异常**时，
才针对**具体 BDF** 做有限读取：

```bash
# 只对这 4 个 BDF，逐个执行；每个 256 B 或 4 KiB（-xxxx 全量）
sudo lspci -xxxx -s 00:01.1 > ~/pci-audit/cfg-0001.1.txt   # GPP0（dGPU 的父桥）
sudo lspci -xxxx -s 00:03.1 > ~/pci-audit/cfg-0003.1.txt   # GP11（有窗口无端点）
sudo lspci -xxxx -s 00:08.1 > ~/pci-audit/cfg-0008.1.txt   # GP17（780M 的父桥）
sudo lspci -xxxx -s 01:00.0 > ~/pci-audit/cfg-0100.0.txt   # RTX 4050（BAR1 8 GiB）
```

* 每个 BDF 执行前**记录**"我为什么要读它"（哪一条第一阶段证据触发的）。
* `-xxxx` 是**只读**读取；**不得**紧跟任何 `-s ... -w`（写入）操作。

---

## 4. 优先解析的字段（第一阶段即可得到）

对**每一座 PCI-to-PCI 桥**（`lspci -Dnnvv` 的 `PCI bridge` 段落）：

| 字段 | `lspci -vv` 里的样子 | 用途 |
|---|---|---|
| Primary/Secondary/Subordinate | `Bus: primary=00, secondary=01, subordinate=01` | **直接**回答"两座桥的总线范围是否重叠"（Windows 侧做不到） |
| 桥的 Memory 窗口 | `Memory behind bridge: dc000000-dd0fffff` | 与子设备 BAR 做包含性检查 |
| 桥的 Prefetchable 窗口 | `Prefetchable memory behind bridge: 0000007c00000000-0000007e01ffffff` | **本机最需要的一条**：验证 GPP0 的 8 GiB + 32 MiB 与 GP11 的 64 GiB |
| `PCI Command` / `Status` | 开头的 `Control: I/O+ Mem+ BusMaster+ ...` / `Status: Cap+ ...` | 桥的 decode 是否使能 |
| 设备的 BAR 与类型 | `Region 1: Memory at 7c00000000 (64-bit, prefetchable) [size=8G]` | BAR ↔ 桥窗口的**归属**关系 |
| `Slot` / `LnkSta`（仅 GP11 相关） | `Slot #0, PowerLimit ...` / `LnkSta: Speed 2.5GT/s (downgraded), Width x0` | **区分 §11.6 的三种解释**：空槽 / 过分配 / 真异常 |
| 是否记录重分配 | `dmesg` 里 `pci_bus 0000:..: ...`、`BAR ..: assigned`、`can't assign`、`no space for` | "Linux 是否自己动了资源" |

### 4.1 建议的 `dmesg` 检索式

```bash
grep -nE 'pci (bus|bridge)|BAR [0-9]|can.t assign|no space|failed to assign|realloc|resource window|bridge window|host bridge' ~/pci-audit/dmesg.txt
grep -nE 'GP11|GPP0|GP17|1002:1900|10de:28e1|14c3:0616' ~/pci-audit/dmesg.txt
```

**"没有命中"也是一个结果**（说明 Linux 没有重新分配、没有分配失败），要照实记录。

---

## 5. 预登记判据

| 判据 | 观察 | 结论 |
|---|---|---|
| **(α)** | 发现**桥总线范围重叠** / **桥窗口部分重叠** / **某 BAR 不属于任何父桥窗口** / **子桥 subordinate 越界** 之一 | **得到一个可定位的靶点**；下一轮才有资格讨论"针对性修改"，且仍需用户单独批准 |
| **(β)** | 全部干净（与 `docs/08` §11.5 的 Windows 侧结论一致） | **合并排除"桥资源/枚举不一致"这一整类假设**（Windows + Linux 双内核旁证）。价值与找到问题相同 |
| **(γ)** | 只有 GP11 体现出**链路未 train / 无卡存在 / 槽位为空** | 把 GP11 的 64 GiB 窗口归入"**空槽预留 + 固件过分配**"（`docs/08` §11.6 解释 1/2），**关闭 L1** |
| **(δ)** | Linux **自己改了**桥窗口或总线号（`dmesg` 有重分配记录） | 该轮读数**不能**用来代表固件原值 ⇒ 在记录里降级，并考虑加 `pci=noearly` 之类**只读**参数重采（须用户批准） |

**任一判据命中，都先写进 `docs/08` / 本文，再决定是否进入写盘类实验。**

---

## 6. 脱敏要求（**入库前必做**）

`dmesg` / `dmidecode` / `/proc/iomem` **天然含机器标识**：序列号、MLB/UUID、网卡 MAC、
NVMe 磁盘序列号、CPU/主板序列、机器型号+BIOS 版本组合。
因此：

1. **原始文件一律不入库**（与 `audit/acpi/**`、`audit/iopicifamily/**` 同级对待）。
2. 入库的只能是**派生、脱敏后的摘录**（只留 BDF / 窗口 / 总线号 / 寄存器值）。
3. 入库前跑 `scripts/sync-to-github.ps1` 的第 3 步 leak scan；它会用**卡上的真实**
   `SystemSerialNumber` / `MLB` / `SystemUUID` / `ROM(MAC)`（含字节序变换与 8 字符前缀）
   扫描整个仓库。
4. 另外人工确认：`NVMe(0x1,<serial>)` 形态的磁盘序列号必须已被替换为 `<disk-serial-redacted>`。

---

## 7. 风险与回滚

| 项 | 评估 |
|---|---|
| **对 macOS 引导盘的风险** | **零**（不引导 OpenCore、不写 `D:`、不改 EFI）。执行前**先物理拔掉** macOS 盘最稳 |
| **对固件的风险** | **零**（只读；不动 BIOS；不改配置寄存器） |
| **对 Windows 的风险** | **零**（不写内置盘；Live 只读挂载） |
| **介质风险** | 需要在**另一块 U 盘**上写 Live 镜像 —— 写之前 `list disk` 逐条核对盘符与容量 |
| **回滚** | 不适用（无被改动的持久状态）；若 Live 起不来，直接断电重开进 Windows，本轮记"实验无法完成" |

---

## 8. 触发条件（**什么时候才真的去用**）

满足**任一**条即值得执行：

1. 要**判定 GP11 的三种解读**（空槽 / 过分配 / 真异常）—— 只有 Linux 的
   `Slot` + `LnkSta` + Secondary Bus Number 能把它们分开（Windows 侧已登记为不可得，`docs/08` §11.7）。
2. 后续任何一轮想在**桥寄存器层面**建立基线（例如做 BAR 尺寸类实验前，先确认桥窗口余量）。
3. 需要**第三个内核**的旁证来支撑一个"排除整类假设"的结论。

**不满足这些条件时，不值得为它花一块介质**：Windows 侧已经把"资源/枚举不一致"
这一子类判为干净（`docs/08` §11.5，预登记判据 (β)）。
