# efi/ 目录说明

## `config.plist`

这是**实机验证过可以引导到内核**的那份 OpenCore 配置（OpenCore 1.0.9）。
官方 `ocvalidate` 复核结果：**0 issues**。

### ⚠️ 使用前必读

`PlatformInfo → Generic` 里的 SMBIOS 身份字段已被人为抹除：

| 字段 | 本文件中的值 | 说明 |
|---|---|---|
| `SystemSerialNumber` | `000000000000` | **必须换成你自己的** |
| `MLB` | `00000000000000000` | **必须换成你自己的** |
| `SystemUUID` | 全零 | **必须换成你自己的** |
| `ROM` | 全零 | 通常填网卡 MAC |

**不要照抄示例里的占位值。** 请用 [1401](https://github.com/nullmoth/1401) 对**本机**重新扫描生成
（它会为该机型生成一套自洽的 SMBIOS），再叠加下面这些"本项目验证过的改动"。
多人共用同一套 SMBIOS 身份会导致 iMessage / iCloud 出问题。

### 本项目叠加在 1401 构建结果之上的改动

```
boot-args += npci=0x2000                     # 越过 "PCI configuration begin" 卡死

Misc → Security → DmgLoading      = Any      # 跳过慢速 DMG 分块校验（静默、耗时长，易误判为死机）
Booter → Quirks → ResizeAppleGpuBars = 0     # 安装器专用：N 卡大 BAR 会顶掉固件帧缓冲
UEFI   → Quirks → ResizeGpuBars      = -1

# bootfix 阶梯第一档（AMD hand-off）：五项必须一起改
Booter → Quirks → DevirtualiseMmio       = （True → 见下）
Booter → Quirks → SetupVirtualMap        = True
Booter → Quirks → RebuildAppleMemoryMap  = False
Booter → Quirks → EnableWriteUnprotector = True
Booter → Quirks → SyncRuntimePermissions = False

# Kernel → Add 追加注入 HoRNDIS（安卓 USB 共享网络，见 docs/02）
```

> `DevirtualiseMmio` 的当前取值取决于你在阶梯的哪一档：
> 第一档保持 `True`，第二档（第一档仍卡住时）翻成 `False`。详见 [../docs/03-引导排错实录.md](../docs/03-引导排错实录.md)。

正确做法是**用 1401 构建一次**，然后用编辑器或 `scripts/patch-stick-config.py` 逐项叠加上述差异，
而不是直接拿这份文件当成品。

## 需要哪些 kext

本项目**不重新分发任何 kext 二进制**（各自的许可见 [../NOTICE.md](../NOTICE.md)）。
用 1401 构建即可自动取得以下版本（它们在 1401 的 `p1401/mirror.json` 里有哈希锁定）：

```
Lilu 1.7.3 · AMFIPass 1.4.1 · VirtualSMC 1.3.9 · SMCBatteryManager 1.3.9 · SMCLightSensor 1.3.9
AppleALC 1.9.9 · WhateverGreen 1.7.2 · NVMeFix 1.1.4 · RestrictEvents 1.1.7 · BrightnessKeys 1.0.4
NullEthernet 1.0.6 · Sinetek-rtsx 9.0 · USBToolBox 1.2.0 · UTBDefault
VoodooI2C 2.9.1 (+ VoodooGPIO 1.1 / VoodooI2CServices / VoodooInput 1.1.7) · VoodooI2CHID 1.0
VoodooPS2Controller 2.3.8 (+ Keyboard/Mouse/Trackpad) · AppleMCEReporterDisabler 1.2
HoRNDIS 9.3（本项目额外注入，见 docs/02）
```

逐个 kext 的架构 / 顺序 / 依赖 / 型号匹配审计见 [../docs/04-驱动核对.md](../docs/04-驱动核对.md)。

## ACPI 表

由 1401 生成：`SSDT-EC`、`SSDT-PLUG-ALT`、`SSDT-RMNE`、`SSDT-USB-Reset`、`SSDT-USBX`、`SSDT-XOSI`、
`SSDT-Disable_Network_GPP6`，并配套 `ACPI → Patch` 里的 `_OSI → XOSI` 重命名。

其中 **`SSDT-Disable_Network_GPP6` 在本机加载失败**（它要定义的 `\_SB.PCI0.GPP6.WLAN._DSM`
在固件 DSDT 里已存在 → `AE_ALREADY_EXISTS`）。它从未生效，也没有存在价值（MT7922 在 macOS 下无驱动），
可以直接删除；换用 macOS 原生无线网卡时则**必须**删除。
