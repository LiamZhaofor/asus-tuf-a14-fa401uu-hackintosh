# `audit/` —— 什么入库、什么绝不入库

本目录存放**只读审计脚本与其脱敏输出**，用途是让 `docs/` 里引用的每个结论**可复现**。

## 入库的（可复现 + 已脱敏检查）

| 文件 | 说明 |
|---|---|
| `pci-windows-audit.py` | Round 8 的 Windows 侧只读审计。输入是 Windows **自己写出来**的 PnP 转储 + `1401/plan.json`，输出设备表、桥表、两个数据源的差异、包含性/越界/重叠检查、**登记缺口**。不打开设备、不发 IOCTL、不写任何 PCI 配置寄存器、不需要管理员 |
| `dump-logconf.ps1` | 只读枚举 `HKLM\SYSTEM\CurrentControlSet\Enum\PCI\<dev>\<inst>\LogConf` 的 `BootConfig` / `BasicConfigVector` **原始字节**（`RegOpenKeyEx(KEY_READ)` + `RegQueryValueEx`）。这两种类型 `.NET` 的 `RegistryValueKind` **取不到**（返回 `Unknown`/`null`），所以必须读原始字节 |
| `pci-logconf-audit.py` | 解码上面那些字节：`BootConfig` = `CM_RESOURCE_LIST`（**固件交接**），`BasicConfigVector` = `IO_RESOURCE_REQUIREMENTS_LIST`（**需求孔径**）。含 **Type 7 `MemoryLarge` 长度字段 = length ÷ 256** 这条规则及其证明（见脚本 docstring） |
| `pci-resource-audit.py` | 从 `1401/plan.json` 的 `resource_record` 生成资源图（`docs/08` §10.1 引用）。`plan.json` 路径改为**命令行参数** |
| `cfgmgr-resdes-probe.cs` | 原生 x64 只读探针：`CM_Get_First_Log_Conf(BASIC/ALLOC/BOOT)` + `CM_Get_Next_Res_Des`，**32 位 `ULONG` 句柄声明与零初始化指针宽度声明都试**，`ForType` 扫遍 `0x00…0x41`。只调用 `CM_*` 查询函数与 `*_Handle` 释放函数；**不**调用 `CM_Modify_Res_Des` / `CM_Add_Res_Des` / `CM_Add_Empty_Log_Conf` / `CM_Free_Res_Des` / `CM_Free_Log_Conf` |
| `results/pci-windows-2026-10-13.md` / `.json` | 上者在本机的输出，**已脱敏**：只保留 BDF、`VEN/DEV/SUBSYS/REV`、类名、ACPI 路径、窗口区间、总线号 |
| `results/pci-logconf-2026-10-13.md` / `.json` | 注册表逻辑配置的解码结果（**已脱敏**：不含实例 ID） |
| `results/pci-resource-plan-2026-10-13.txt` | `pci-resource-audit.py` 的原始输出 |

复现：

```powershell
# Windows 侧（零额外介质、非管理员）
pnputil /enum-devices /connected /deviceids /relations /location /properties /resources `
         /format xml /output-file pnputil-all.xml
python audit\pci-windows-audit.py pnputil-all.xml --cfgmgr <1401>\plan.json `
       --out audit\results\pci-windows-<date>

# 注册表逻辑配置（只读；原始转储只留本地，不入库）
pwsh -File audit\dump-logconf.ps1
python audit\pci-logconf-audit.py registry-logconf-all.txt pnputil-all.xml `
       --cfgmgr <1401>\plan.json --out audit\results\pci-logconf-<date>

python audit\pci-resource-audit.py <1401>\plan.json

# CfgMgr32 调用形状探针（原生 x64）
& "$env:SystemRoot\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /platform:x64 `
      /out:cfgmgr-resdes-probe.exe audit\cfgmgr-resdes-probe.cs
```

## **绝不**入库的

| 路径 | 原因 |
|---|---|
| `audit/acpi/**`（`.aml` / `.dat` / `firmware/**`） | ACPI 二进制与反编译，其中 **`MSDM` 含 OEM 密钥** |
| `audit/iopicifamily/**`、`audit/voodooi2c-src/**` | 第三方源码副本，体积与来源都不适合放在本仓库 |
| 屏幕照片 | 可能含机器标识 |
| 任何 `.aml` / `.bin` / `.efi` / `.dmg` / `.zip` / `.kext` / `*.nvram.plist` | 见 `scripts/sync-to-github.ps1` 的 forbidden-list |
| **原始 `pnputil-all.xml`** | 3.2 MB，且逐设备带 `ContainerId` / `BaseContainerId` / 安装与到达日期 / Binary 属性块 —— **机器标识**，只留脱敏摘录 |
| `1401/plan.json` | 含 SMBIOS 决策、真实设备实例、NVIDIA/NVML 细节，**不是**可发布产物 |
| Linux Live 的原始 `dmesg` / `dmidecode` / `/proc/iomem` | 见 `docs/09` §6 |

## 脱敏规则（`pci-windows-audit.py --sanitize`，**默认开启**）

* 每个 PCI 实例 ID 里那段**每机唯一的哈希**（`…&REV_xx\<hash-component>` 的后半段）换成**该设备自己的拓扑标签**
  `…\REV_A1\<01:00.0>`；`Parent` 引用用同一张映射表，保持一致。
* 丢弃：ContainerId / BaseContainerId、安装/首次安装/最后到达时间、CreatorProcessId、
  **全部 Binary 属性块**。
* 保留（**这是板级拓扑，不是机器身份**）：`VEN/DEV/SUBSYS/REV`、类代码、
  `LocationPaths`（含 ACPI 路径）、已分配窗口。
* `--raw` 会把实例 ID 原样写进输出，**只允许本地使用，禁止发布**。

发布前仍以 `scripts/sync-to-github.ps1` 的第 3 步 leak scan 为准：
它会用**卡上真实**的 `SystemSerialNumber` / `MLB` / `SystemUUID`（含字节序变换形式与 8 字符前缀）
与 `ROM`（网卡 MAC 的多种写法）**全仓扫描**，命中即拒绝发布。

## 与 `docs/06` §993 的关系

`docs/06` 曾规定 `audit/*.py` **一律不入库**。该禁令在 Round 8 按用户授权**收窄**为：
**只读**审计脚本可入库（前提：路径参数化、无固件数据、输出经上述脱敏与 leak scan）；
上面"绝不入库"清单里的东西**仍然禁止**。
