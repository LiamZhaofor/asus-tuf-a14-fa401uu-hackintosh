# 第三方组件与归属

> **仓库策略（2026-10-21 定稿）**
>
> - **仓库树里不放第三方二进制。** `EFI/` 只包含 OpenCore 自己的文件（BSD-3-Clause）、
>   本项目生成的 ACPI/config，以及自研的 `RogProbe2.kext`。
> - 22 个第三方 kext 由 `scripts/fetch-kexts.ps1` 按 `scripts/kext-pins.json` 里
>   **固定的 URL + SHA256** 从上游拉取，再用 `scripts/kext-manifest.json` 逐个核对二进制哈希。
>   清单里的 URL/哈希取自 1401 v2.3.6 的 `p1401/mirror.json`，并已逐条下载复核。
> - **Release 里那份 `EFI-<日期>.zip` 是包含第三方 kext 的便捷包**（开箱可引导）。
>   如果你不想碰第三方二进制，就用仓库 + fetch 脚本。
>
> 如果你是某个组件的作者，不希望产物被这样聚合 —— 开 issue，我会立即移除对应条目。

## 一、由 `fetch-kexts.ps1` 拉取的 kext（22 个）

版本与哈希以 `scripts/kext-pins.json` / `scripts/kext-manifest.json` 为准，这里是来源索引。

| kext | 上游 | 版本 | 许可（以上游为准） |
|---|---|---|---|
| Lilu | [acidanthera/Lilu](https://github.com/acidanthera/Lilu) | 1.7.3 | BSD-3-Clause |
| VirtualSMC / SMCBatteryManager / SMCLightSensor | [acidanthera/VirtualSMC](https://github.com/acidanthera/VirtualSMC) | 1.3.9 | BSD-3-Clause |
| WhateverGreen | [acidanthera/WhateverGreen](https://github.com/acidanthera/WhateverGreen) | 1.7.2 | BSD-3-Clause |
| AppleALC | [acidanthera/AppleALC](https://github.com/acidanthera/AppleALC) | 1.9.9 | BSD-3-Clause |
| NVMeFix | [acidanthera/NVMeFix](https://github.com/acidanthera/NVMeFix) | 1.1.4 | BSD-3-Clause |
| RestrictEvents | [acidanthera/RestrictEvents](https://github.com/acidanthera/RestrictEvents) | 1.1.7 | BSD-3-Clause |
| BrightnessKeys | [acidanthera/BrightnessKeys](https://github.com/acidanthera/BrightnessKeys) | 1.0.4 | BSD-3-Clause |
| VoodooPS2Controller（+ Keyboard / Mouse / Trackpad / VoodooInput） | [acidanthera/VoodooPS2](https://github.com/acidanthera/VoodooPS2) | 2.3.8 | **GPL-2.0** |
| BlueToolFixup | BrcmPatchRAM（acidanthera） | 2.7.3 | **GPL-2.0** |
| VoodooI2C（+ VoodooGPIO / VoodooI2CServices / VoodooInput）、VoodooI2CHID | [VoodooI2C/VoodooI2C](https://github.com/VoodooI2C/VoodooI2C) | 2.9.1 / 1.0 | **GPL-2.0** |
| Sinetek-rtsx（Realtek 读卡器） | [cholonam/Sinetek-rtsx](https://github.com/cholonam/Sinetek-rtsx) | 9.0 | **GPL-2.0** |
| AMFIPass | dhinakg（经 dortania/OCLP 分发） | 1.4.1 | 见上游 |
| AppleMCEReporterDisabler | XLNC（acidanthera bugtracker 分发） | 1.2 | 见上游 |
| USBToolBox / UTBDefault | [USBToolBox](https://github.com/USBToolBox) | 1.2.0 / 1.0 | 见上游 |
| HoRNDIS（安卓 USB 共享） | 原作者 jwise；本项目用 [TomHeaven/HoRNDIS](https://github.com/TomHeaven/HoRNDIS) 维护分支 | 9.3（rel9.3_2，x86_64 + arm64e） | 见上游 |
| **itlmt7922**（MT7922 Wi-Fi，实验性） | [hbyonly1/itlmt7922-wifi](https://github.com/hbyonly1/itlmt7922-wifi) | 0.2.2 | Clear BSD（内含 MediaTek 固件，另有其许可） |
| **SimpleMtkBtFw**（MT7921/7922 蓝牙固件加载） | [laobamac/SimpleMtkBtFw](https://github.com/laobamac/SimpleMtkBtFw) | 1.0.0 | 见上游 |

**GPL-2.0 组件的源码**在各自上游仓库（上表已给链接），本项目未做任何修改。
不需要某个 kext 时，直接从 `EFI/OC/Kexts` 删掉并同步删 `config.plist` 里对应的
`Kernel → Add` 条目即可（例如不要读卡器就删 `Sinetek-rtsx`）。

## 二、仓库自带（非第三方）

| 项 | 说明 |
|---|---|
| `EFI/OC/Kexts/RogProbe2.kext` | 本项目自研（bundle id `com.zhao.RogProbe2`），随仓库分发 |
| `EFI/OC/ACPI/*.aml`、`EFI/OC/config.plist` | 本项目生成/整理 |
| `EFI/BOOT`、`EFI/OC/Drivers`、`EFI/OC/Resources`、`EFI/OC/OpenCore.efi` | OpenCore（BSD-3-Clause） |

## 三、需要自己获取、本仓库不提供的

| 组件 | 上游 | 说明 |
|---|---|---|
| **NullMoth NVIDIA 驱动 2.3.6** | [nullmoth/nvidia-macos-driver](https://github.com/nullmoth/nvidia-macos-driver) | ⚠️ **PolyForm Noncommercial 1.0.0**。装到 macOS 的 `/Library/Extensions/`（`NVRM` / `NVAccel` / `NVRMFB`）、`/Library/GPUBundles/`、`/Library/NullMoth/`，由 `1401.app` 安装。**不随本仓库分发。** |
| **1401**（装机/引导工具） | [nullmoth/1401](https://github.com/nullmoth/1401) | ⚠️ **PolyForm Noncommercial 1.0.0**。用它的 `p1401.bootfix` 做引导诊断、`p1401.usbwriter` 写介质；内部基于 OpCore-Simplify。 |
| `EFI/OC/Tools/NullMothSafe.efi`（菜单里的两条 `1401:` 救急项） | 来自 1401，无公开直链 | `fetch-kexts.ps1` 会去 `%LOCALAPPDATA%\NullMoth\1401`、`E:\EFI\OC\Tools` 等位置找并复制；找不到只警告，不影响正常启动（只是少了两条救急菜单项）。 |
| **AMD_Vanilla 内核补丁** | [AMD-OSX/AMD_Vanilla](https://github.com/AMD-OSX/AMD_Vanilla) | 只是 `config.plist` 里的字节序列，非二进制。Zen 4 的 `IOPCIFamily`（CaseySJ）补丁在本机日志中确认生效。 |

## 四、参考资料

- [Dortania OpenCore Install Guide](https://dortania.github.io/OpenCore-Install-Guide/) ——
  尤其是 "Stuck on `[PCI configuration begin]`" 一节
- [Dortania GPU Buyers Guide](https://github.com/dortania/GPU-Buyers-Guide)
- [itlmt7922-wifi](https://github.com/hbyonly1/itlmt7922-wifi) 的 README 与 `docs/PORTING.md`
- 华硕官方 FAQ：笔记本 NVIDIA Resizable BAR 支持说明（Ryzen 5000 系以上默认开启，BIOS 不显示该选项）

## 五、免责

- 黑苹果（在非 Apple 硬件上运行 macOS）**违反 Apple 的软件许可协议**，本项目仅供研究与学习。
- 这套配置**显著降低系统安全性**：放宽 SIP（`csr-active-config = 0x0A43`）、
  通过 `amfi=0x80` + `amfi_get_out_of_my_way=0x1` 旁路 AMFI 签名校验、关闭 Apple 安全启动。
  **请勿用于处理敏感数据的主力机。**
- 文档里的实测结论对应 **2026-10** 的驱动/工具版本，上游更新后可能不再适用。
- 使用本仓库的任何文件所造成的后果由使用者自行承担。
