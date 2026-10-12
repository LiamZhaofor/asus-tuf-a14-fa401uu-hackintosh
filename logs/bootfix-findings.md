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
boots              : 3 次完整引导
```

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
| 1 | `bootlog-amd-exitbs` | `RebuildAppleMemoryMap=False`、`EnableWriteUnprotector=True`、`SyncRuntimePermissions=False`（`DevirtualiseMmio`/`SetupVirtualMap` 保持 True） | 第 3 次引导（`wrunprot=True`）仍停住 |
| 2 | `bootlog-handoff-devirt` | 保留上组，`DevirtualiseMmio` 翻为 `False` | 待验证 |

第一档的源码注释记录了一模一样的先例：

> *"measured on a Ryzen 5 5500 / B550 (10-09): it hung with the default, got past with the MMIO pair,
> then panicked (type 14) until the write-unprotector pair was on. **All five change together.**"*

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
