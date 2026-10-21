# 第三方组件与归属

> **政策变更（2026-10-21）**：本仓库此前只发布 `config.plist`、**不重新分发任何二进制**。
> 现在为了"开箱能引导"，`EFI/` 目录**直接包含了一套完整可引导的 EFI**，因此开始分发第三方二进制。
> 下面逐条列出这些组件、它们的上游与版本。**具体许可条款请以各上游仓库为准**，
> 本仓库不代替、也不修改上游的许可。
>
> 如果你是某个组件的作者，不希望二进制出现在这里 —— 开一个 issue，我会立即移除对应文件。

## 一、本仓库分发的二进制（`EFI/`）

### 引导器

| 组件 | 上游 | 版本 | 许可 |
|---|---|---|---|
| OpenCore（`BOOTx64.efi` / `OpenCore.efi` / `OpenRuntime.efi` / `HfsPlus.efi` / `ResetNvramEntry.efi`） | [acidanthera/OpenCorePkg](https://github.com/acidanthera/OpenCorePkg) | 1401 v2.3.6 内置的 **DEBUG** 构建 | BSD-3-Clause |

### kext（`EFI/OC/Kexts`，共 22 个 kext / 29 条 `Kernel → Add`）

| kext | 上游 | 版本 | 许可（以上游为准） |
|---|---|---|---|
| Lilu | [acidanthera/Lilu](https://github.com/acidanthera/Lilu) | 1.7.3 | BSD-3-Clause |
| VirtualSMC | [acidanthera/VirtualSMC](https://github.com/acidanthera/VirtualSMC) | 1.3.9 | BSD-3-Clause |
| SMCBatteryManager | 同上 | 1.3.9 | BSD-3-Clause |
| SMCLightSensor | 同上 | 1.3.9 | BSD-3-Clause |
| WhateverGreen | [acidanthera/WhateverGreen](https://github.com/acidanthera/WhateverGreen) | 1.7.2 | BSD-3-Clause |
| AppleALC | [acidanthera/AppleALC](https://github.com/acidanthera/AppleALC) | 1.9.9 | BSD-3-Clause |
| NVMeFix | [acidanthera/NVMeFix](https://github.com/acidanthera/NVMeFix) | 1.1.4 | BSD-3-Clause |
| RestrictEvents | [acidanthera/RestrictEvents](https://github.com/acidanthera/RestrictEvents) | 1.1.7 | BSD-3-Clause |
| BrightnessKeys | [acidanthera/BrightnessKeys](https://github.com/acidanthera/BrightnessKeys) | 未标注 | BSD-3-Clause |
| VoodooPS2Controller（+ Keyboard / Mouse / Trackpad / VoodooInput） | [acidanthera/VoodooPS2](https://github.com/acidanthera/VoodooPS2) | 2.3.8 | GPL-2.0 |
| BlueToolFixup | BrcmPatchRAM（acidanthera） | 2.7.3 | GPL-2.0 |
| AMFIPass（`com.dhinakg.AMFIPass`） | dhinakg | 1.4.1 | 见上游 |
| AppleMCEReporterDisabler | XLNC / dortania | 未标注 | 见上游 |
| USBToolBox / UTBDefault | [USBToolBox](https://github.com/USBToolBox) | 1.2.0 / 1.0 | 见上游 |
| VoodooI2C（+ VoodooGPIO / VoodooI2CServices / VoodooInput） | [VoodooI2C/VoodooI2C](https://github.com/VoodooI2C/VoodooI2C) | 2.9.1 | GPL-2.0 |
| VoodooI2CHID | 同上 | 1.0 | GPL-2.0 |
| Sinetek-rtsx（Realtek 读卡器） | Sinetek 等 | 9.0.0 | GPL-2.0 |
| **HoRNDIS**（安卓 USB 共享） | 原作者 jwise；本项目用 [TomHeaven/HoRNDIS](https://github.com/TomHeaven/HoRNDIS) 维护分支 | 9.3 | 见上游 |
| **itlmt7922**（MT7922 Wi-Fi，实验性） | [hbyonly1/itlmt7922-wifi](https://github.com/hbyonly1/itlmt7922-wifi) | 0.2.2 | Clear BSD（含 MediaTek 固件，另有其许可） |
| **SimpleMtkBtFw**（MT7921/7922 蓝牙固件加载） | [laobamac/SimpleMtkBtFw](https://github.com/laobamac/SimpleMtkBtFw) | 1.0.0 | 见上游 |
| **RogProbe2** | **本项目自有**（`com.zhao.RogProbe2`） | 1.0.0 | 随本仓库 |

### 工具（`EFI/OC/Tools`）

| 工具 | 来源 | 许可 |
|---|---|---|
| `NullMothSafe.efi`（菜单里显示为 `1401: Remove NVIDIA driver` / `1401: Start once without NVIDIA driver`） | [nullmoth/1401](https://github.com/nullmoth/1401) | ⚠️ **PolyForm Noncommercial 1.0.0 —— 禁止商业使用** |

### GPL 组件的源码

`VoodooPS2`、`VoodooI2C`、`Sinetek-rtsx`、`BlueToolFixup` 等按 GPL-2.0 分发，
**源码在各自上游仓库**（上表已给链接），未做任何修改。若需要离线获取源码，
请到对应 upstream 的对应 tag/commit 下载；如你有更严格的合规要求，
直接从 `EFI/OC/Kexts` 删除这些 kext 也不影响其余功能（会失去触摸板/键盘/读卡器/蓝牙修复）。

## 二、仅作为参考、不分发的组件

| 组件 | 上游 | 说明 |
|---|---|---|
| **NullMoth NVIDIA 驱动 2.3.6** | [nullmoth/nvidia-macos-driver](https://github.com/nullmoth/nvidia-macos-driver) | ⚠️ **PolyForm Noncommercial 1.0.0**。本仓库只链接，**不打包**。它装在 macOS 的 `/Library/Extensions/`（`NVRM.kext` / `NVAccel.kext` / `NVRMFB.kext`）、`/Library/GPUBundles/`、`/Library/NullMoth/`，由 `1401.app` 安装。 |
| **1401**（装机/引导工具） | [nullmoth/1401](https://github.com/nullmoth/1401) | ⚠️ **PolyForm Noncommercial 1.0.0**。用它的 `p1401.bootfix` 做引导诊断、`p1401.usbwriter` 写介质；内部基于 OpCore-Simplify。 |
| **AMD_Vanilla 内核补丁** | [AMD-OSX/AMD_Vanilla](https://github.com/AMD-OSX/AMD_Vanilla) | 只是 `config.plist` 里的字节序列，非二进制分发。Zen 4 的 `IOPCIFamily`（CaseySJ）补丁在本机日志中确认生效。 |

## 三、参考资料

- [Dortania OpenCore Install Guide](https://dortania.github.io/OpenCore-Install-Guide/) ——
  尤其是 "Stuck on `[PCI configuration begin]`" 一节
- [Dortania GPU Buyers Guide](https://github.com/dortania/GPU-Buyers-Guide)
- [itlmt7922-wifi](https://github.com/hbyonly1/itlmt7922-wifi) 的 README 与 `docs/PORTING.md`
- 华硕官方 FAQ：笔记本 NVIDIA Resizable BAR 支持说明（Ryzen 5000 系以上默认开启，BIOS 不显示该选项）

## 四、免责

- 黑苹果（在非 Apple 硬件上运行 macOS）**违反 Apple 的软件许可协议**，本项目仅供研究与学习。
- 这套配置**显著降低系统安全性**：放宽 SIP（`csr-active-config = 0x0A43`）、
  通过 `amfi=0x80` + `amfi_get_out_of_my_way=0x1` 旁路 AMFI 签名校验、关闭 Apple 安全启动。
  **请勿用于处理敏感数据的主力机。**
- 文档里的实测结论对应 **2026-10** 的驱动/工具版本，上游更新后可能不再适用。
- 使用本仓库的任何文件所造成的后果由使用者自行承担。
