# 第三方组件与归属

**本仓库不重新分发任何第三方二进制文件。** 下列组件仅被引用/链接，请到各自上游获取，
并遵守其各自的许可条款（下面列出的是上游项目地址，具体许可请以各仓库为准）。

## 核心组件

| 组件 | 作者 / 上游 | 说明 |
|---|---|---|
| **NullMoth NVIDIA 驱动** | [nullmoth/nvidia-macos-driver](https://github.com/nullmoth/nvidia-macos-driver) | ⚠️ **PolyForm Noncommercial 1.0.0 —— 禁止商业使用**。个人/研究/教育可用。本项目只链接，不打包。其 `translator/` 部分为 LGPL-3.0-or-later（基于 metal2vulkan），`nvk/` 部分为 Mesa 的 MIT 改动，GSP 固件适用 NVIDIA 的可再分发固件许可。 |
| **1401**（装机工具，本项目的构建基础） | [nullmoth/1401](https://github.com/nullmoth/1401) | ⚠️ 同样为 **PolyForm Noncommercial 1.0.0**。本项目用它的 `p1401.bootfix` 做引导日志诊断、用 `p1401.usbwriter` 写盘。它内部基于 OpCore-Simplify。 |
| **OpenCore** | [acidanthera/OpenCorePkg](https://github.com/acidanthera/OpenCorePkg) | BSD-3-Clause。本项目验证的配置针对 **OpenCore 1.0.9**（`ocvalidate` 复核 0 issues）。 |
| **AMD_Vanilla 内核补丁** | [AMD-OSX/AMD_Vanilla](https://github.com/AMD-OSX/AMD_Vanilla) | AMD CPU 在 macOS 上运行所需。其中 Zen 4 的 `IOPCIFamily` 补丁（CaseySJ）在本机日志中确认生效。 |

## 本项目验证过的 kext（均由 1401 按其哈希锁定下载，本仓库不含二进制）

| kext | 上游 |
|---|---|
| Lilu / VirtualSMC / AppleALC / WhateverGreen / NVMeFix / RestrictEvents / BrightnessKeys / AppleMCEReporterDisabler | [Acidanthera](https://github.com/acidanthera) 及各自仓库 |
| AMFIPass | dhinakg |
| VoodooI2C / VoodooI2CHID / VoodooGPIO / VoodooInput | [VoodooI2C](https://github.com/VoodooI2C/VoodooI2C) |
| VoodooPS2Controller | [acidanthera/VoodooPS2](https://github.com/acidanthera/VoodooPS2) |
| USBToolBox / UTBDefault | [USBToolBox](https://github.com/USBToolBox) |
| Sinetek-rtsx | Sinetek 等（Realtek 读卡器） |
| NullEthernet | RehabMan |
| **HoRNDIS**（本项目额外注入，用于安卓 USB 共享网络） | 原始作者 jwise；本项目使用的是 [TomHeaven/HoRNDIS](https://github.com/TomHeaven/HoRNDIS) 的维护分支 **9.3** |

## 参考资料

- [Dortania OpenCore Install Guide](https://dortania.github.io/OpenCore-Install-Guide/) —— 尤其是
  "Stuck on `[PCI configuration begin]`" → `npci=0x2000` / `npci=0x3000` 这一条
- [Dortania GPU Buyers Guide](https://github.com/dortania/GPU-Buyers-Guide)
- 华硕官方 FAQ：笔记本 NVIDIA Resizable BAR 支持说明（Ryzen 5000 系以上默认开启，且 BIOS 不显示该选项）

## 免责

- 黑苹果（在非 Apple 硬件上运行 macOS）**违反 Apple 的软件许可协议**，本项目仅供研究与学习。
- 本项目采用的配置会**显著降低系统安全性**：放宽 SIP（`csr-active-config = 0x0A43`）、
  通过 `amfi=0x80` 旁路 AMFI 签名校验、关闭 Apple 安全启动。**请勿用于处理敏感数据的主力机。**
- 文档里的实测结论对应的是 2026-10 时点的驱动/工具版本，上游更新后可能不再适用。
