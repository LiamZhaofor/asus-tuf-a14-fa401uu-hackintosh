# U 盘日志的自动诊断结果

用 [1401](https://github.com/nullmoth/1401) 内置的 `p1401.bootfix` 诊断器读取 `logs/` 下的真实引导日志，
产出如下（可直接复现）。

## findings()

```
startimage_aborted : False      # 没有 "StartImage failed - Aborted"
stop16             : False      # 没有 EB.MM.AKM / STOP 0x16 / Couldn't allocate runtime area
secureboot_dmg     : False      # 没有 "Cannot use Secure Boot with Any DmgLoading"
no_slide           : False      # 没有 "No slide values are usable" → KASLR 正常
devirt_ran         : True       # 日志里有 OCABC: MMIO devirt 行
vmap               : True
mmio               : 5 个区域
boots              : 3 次（logs/ 有 4 份日志，但只有 3 份跑到了 EXITBS）
```

> **一个值得记下来的盲区：`findings()` 完全不检查 `boot-args` 是否真的生效。**
> 它只看 `EXITBS` / `STOP 0x16` / `MMIO devirt` / slide 这些线索，
> 而 `OCVAR: …boot-args - ignored, exists` 和 `AAPL: #[EB|MBA:OUT]` 都没被读。
> 结果就是：配置里写着 `npci=0x2000`、日志里明明白白写着它被忽略，
> 诊断器却一路认为"配置已经应用了" —— 这个盲区让一个失效的 boot-arg 藏了好几次引导。
> **复查任何一轮时，`OCVAR:` 与 `MBA:OUT` 必须单独核对。**

## 每次引导的判定

| 时间戳 | 选的入口 | DevirtualiseMmio | EnableWriteUnprotector | 内置盘出现 macOS 卷 |
|---|---|---|---|---|
| 2026-10-12T23:55:51 | 安装器 (T:4) | True | False | 否 |
| 2026-10-13T00:10:46 | 安装器 (T:4) | True | False | 否 |
| 2026-10-13T00:24:13 | 安装器 (T:4) | True | **True** | 否 |

判定逻辑（`bootfix.handoff_stuck()`）：**安装器引导 ≥ 2 次，且始终没有 macOS 卷出现在内置盘上**。

> 依据是：正常的安装器在**第一次重启之前**就会在目标盘上创建 macOS 卷。
> 从没出现 → 说明安装器根本没走到那一步。
>
> 而"日志以 `EXITBS:START` 结尾"这件事**不能作为判据** —— 每次启动（包括成功的）都这样，
> 因为交接之后 OpenCore 就不再写日志了。源码注释里也记着这一点：
> *"10-09: 29 photos in chat froze on EXITBS:START, but only 3 users typed it."*

## 由此触发的修复阶梯

| 档位 | 规则名 | 改动 | 结果 |
|---|---|---|---|
| 1 | `bootlog-amd-exitbs` | `RebuildAppleMemoryMap=False`、`EnableWriteUnprotector=True`、`SyncRuntimePermissions=False`（`DevirtualiseMmio`/`SetupVirtualMap` 保持 True） | 第 4 次引导（`wrunprot=1`）仍停住 |
| 2 | `bootlog-handoff-devirt` | 保留上组，`DevirtualiseMmio` 翻为 `False` | **从未引导过 → 已在第一轮主动撤下** |

第一档的源码注释记录了一模一样的先例：

> *"measured on a Ryzen 5 5500 / B550 (10-09): it hung with the default, got past with the MMIO pair,
> then panicked (type 14) until the write-unprotector pair was on. **All five change together.**"*

### ⚠️ 这份判定有两条必须一起读的更正

**更正 1：`findings()` 只收了 3 次引导，但 `logs/` 里有 4 份日志。**
`logs/opencore-2026-10-12-233441.txt` **没有 `EXITBS:START`**（它只有 43 KB，最后一行是
`OCB: Found chunklist BaseSystem.chunklist …`，即卡在 DMG 分块校验里、**`boot.efi` 从未启动**），
所以 `_boot()` 直接返回 `None`，不计入 `boots`。**"4 份日志"不等于"4 次引导"。**

**更正 2：`handoff_stuck()` 的判据前提在本机不成立。**
判据（`bootfix.py` 第 38–51 行）是"用户说卡在 EXITBS"**或**"安装器引导 ≥ 2 次且从未出现 macOS 卷"。
它推断的是 *"the screen freezes on EXITBS:START, **the kernel never prints**"*（第 156–158 行）。
但屏幕照片证明**内核已经跑起来了**：

```
AppleACPICPU: ProcessorId=0..15 ... Enabled
IOAPIC: Version 0x21 Vectors 64:87 / 88:111
ACPI: Executed 29 blocks of module-level executable AML code
ACPI: sleep states S4 S5
RTC: Only single RAM bank (128 bytes)          ← 最后一行
```

这些全是 ExitBootServices **之后**的内核输出（内核消息不会落进 OpenCore 的日志，所以"日志止于
`EXITBS:START`"和"屏幕还在滚"是同时成立的，两者不矛盾）。**因此第一档放弃 Dortania MAT 组合的
理由不成立** —— 而且本机 `OCABC: MAT support is 1`（固件**有** MAT），Dortania 给"无 MAT"组合的
唯一前提就是固件缺 MAT。

另需注意：`handoff_stuck()` **在当前 1.14.2 源码中确实存在**（第 38 行定义、第 165 行调用），
不是历史遗留规则 —— 问题在于它的前提，不在于它的存在。

### 还缺什么才能定论

`RTC:` 之后**停在哪里**目前无从判断：内核输出不落盘，照片又只是裁切片段。要真正定位，需要
**一张全屏照片**，或（更好）**串口 / USB 调试日志**。在此之前，任何"死在某个具体子系统"的说法
都只是猜测。

→ 当前处置与判据见 [受控实验记录](../docs/05-受控实验记录.md)。

## MMIO 区域（DevirtualiseMmio 打开时 OpenCore 会逐条列出）

```
(3758096384,  65536, False)    # 0xE0000000      256 MiB
(4244635648,   7680, False)    # 0xFD000000       30 MiB
(4276092928,      1, False)    # 0xFEE00000
(4276097024,   4607, False)    # 0xFEDC4000 附近
(18790481920, 131584, False)   # 0x460000000    ~514 MiB
```

格式：`(基址, 页数, 是否被 MmioWhitelist 跳过)`。当前**没有任何区域被白名单跳过**。
如果后续需要（例如某块 MMIO 必须留给固件），可以把上表里可疑的区域加进
`Booter → MmioWhitelist` —— 打开 `DevirtualiseMmio` 时 OpenCore 会把每块区域打出来便于定位。

## 复现方式

```bash
# 把 U 盘根目录的 opencore-*.txt 全部读进来
python - <<'PY'
import glob
from p1401 import bootfix
logs = sorted(glob.glob(r"D:\opencore-*.txt"))
f = bootfix.findings(bootfix.read_logs(logs))
print(f)
print(bootfix.handoff_stuck(f, ""))
PY
```

> 注意 `bootfix.findings()` 需要 `p1401` 包（来自 1401 的发行包）。

---

## 追加：第 5 份日志（`opencore-2026-10-13-011110.txt`）

第一轮修复后产生了第 5 份日志，它也跑到了 `EXITBS:START`，所以现在 `findings()["boots"]`
是 **4 次**（不是 3 次）。关键差异是 **`boot-args` 第一次真正生效**：

```
00:231  OC: Deleting NVRAM 7C436110-…:boot-args - Success
00:280  OCVAR: Setting NVRAM 7C436110-…:boot-args - Success
15:255  AAPL: #[EB|MBA:OUT] <"… ipc_control_port_options=0 npci=0x2000 slide=159">
```

`OCABC:` 显示本轮真正生效的 quirk 与第 4 次引导一致
（`DEVMMIO 1 … WRUNPROT 1` / `RBMAP 0 VMAP 1 RTPERMS 0`），即对照基线没有被破坏。

**因此 `findings()` 的输出含义在跨轮比较时必须重新解释**：前 4 份日志里有 3 次是在
`npci` 完全没生效的条件下跑出来的，"某组 quirk 失败"这类结论对它们不成立。
详见 [受控实验记录](../docs/05-受控实验记录.md)。
