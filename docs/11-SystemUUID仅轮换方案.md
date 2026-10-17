# 11 · 仅轮换 SystemUUID 的独立方案（**仅方案，未执行**）

> 状态：**方案**。本轮**未**修改 `SystemUUID` / `MLB` / `SystemSerialNumber` / `ROM`，
> **未**改写历史、**未** force-push。卡上仍是 Round 7（`58E78A12…`）。

---

## 0. 触发本方案的事实：历史审计的**分类结果**

`scripts/audit-history-secrets.py`（只读）扫描全部 ref 可达的 258 个对象 / 133 个 blob / 所有提交信息后，
按**命中形态**分类（不打印任何真实值）：

| 类别 | Blob 数 | 文件 |
|---|---|---|
| **完整 `SystemUUID`（明文）** | **0** | — |
| **完整 `SystemUUID`（字节序变换形式，即 OpenCore 打印的那种）** | **4** | `logs/opencore-2026-10-12-233441.txt`、`-235506`、`logs/opencore-2026-10-13-001004.txt`、`-002330`（**均为历史版本**；当前版本已脱敏） |
| **仅 8 字符前缀**（明文 与 变换式各一段） | **1** | `docs/05-受控实验记录.md` |
| 序列号 / MLB / ROM-MAC / NVMe 序列号 | **0** | — |
| 提交信息 | **0** | — |
| 当前工作树 | 干净 | 同一批 needle 在 HEAD 上 0 命中 |

涉及提交：`ea104b90`、`d4b01172`、`e8c329b6` —— **均仍可从 HEAD 到达**，即已进入公开历史。

⇒ **结论：完整 UUID 确实泄漏**（以 OpenCore 的字节序变换形式，在 4 份最早日志里）。
⇒ 因此准备本方案：**只换 `SystemUUID`，不动其余三个字段。**

---

## 1. 为什么只换 UUID（而不是三者都换）

| 选项 | 收益 | 代价/风险 | 结论 |
|---|---|---|---|
| 只换 `SystemUUID` | 让**已泄漏的那个标识**不再是本机身份 | 影响面最小；序列号/MLB 语义不变 | ✅ **推荐** |
| 换 `SystemSerialNumber` / `MLB` | 泄漏面为 0，**无收益** | iCloud/iMessage/FaceTime 重新激活、序列号可能"已被占用"、可能触发激活异常 | ❌ 不做 |
| 换 `ROM`（网卡 MAC） | 泄漏面为 0 | 与真实网卡解耦，可能影响 iServices 一致性 | ❌ 不做 |
| 改写 Git 历史 | — | **不能**取消已公开内容；需 force-push；破坏所有既有提交标识 | ❌ 不做（见 §5） |

---

## 2. 影响评估（改 `SystemUUID` 会碰到什么）

| 层 | 影响 | 说明 / 需要核实的点 |
|---|---|---|
| **注入层** | `config.plist → PlatformInfo → Generic → SystemUUID` 被 OpenCore 写进 SMBIOS Type 1 的 UUID 字段 | 这是**唯一的改动点**；`ocvalidate` 会校验格式 |
| **NVRAM** | **UUID 确实有直接对应的 NVRAM 变量**（此前本文件写"没有"是**错的**，已更正）：`Configuration.tex`（OpenCore `963025f`）明确 `SystemUUID` 会被写入 **`4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14:system-id`**，且是**字节序变换**形式；本仓库配置 `PlatformInfo.Automatic/UpdateNVRAM/UpdateDataHub/UpdateSMBIOS = True`、`UpdateSMBIOSMode = Custom` ⇒ 这条写入是**生效的** | 见 §2.1：必须把 **OpenCore 注入 / 启动服务变量 / 固件持久变量 / 操作系统缓存** 分开看；**不得默认重启后必然残留**，也**不得未经核实就清 NVRAM** |
| **Apple 服务（iCloud / iMessage / FaceTime / App Store）** | 设备标识的一部分改变 ⇒ 可能需要**重新登录/重新激活** | UUID 只是标识之一（序列号/MLB 也参与）；只换 UUID 通常在**首次登录**时表现为"新设备"，但**必须实测**，不能保证无感 |
| **许可证 / 激活缓存 / 偏好** | 个别 App 以 `IOPlatformUUID` 做机器绑定 ⇒ 可能需要重新授权 | 需要在换之前列出受影响的自签/授权类软件 |
| **现有引导基线** | 停点**不应**改变（UUID 与 PCI 初始化无关） | 换完仍应停在 `PCI configuration begin`/`PCI0`；**若停点变化，说明有别的变量被带进来了**，必须回滚 |
| **Time Machine / 备份标识** | 机器标识变化可能使既有备份"看起来是另一台机器" | 仅影响后续备份的归属判断，不破坏数据 |
| **Windows 侧** | ⚠️ **有条件**（此前写"不受影响"是**过强**的）：若 Windows 是**经 OpenCore 引导**的（即在 OpenCore 的启动项里选 Windows），它走的是**同一条 SMBIOS 注入路径**，因此**同样会看到被修改的 SMBIOS/UUID**；只有**直接从固件的 Windows Boot Manager 引导**，才绕开 OpenCore 的注入 | 执行前后需分别确认"这次 Windows 是从哪条路径起来的"，并记录；**不要**把"Windows 没出问题"当作"注入无效"的证据 |

---

## 3. 候选做法

| 方案 | 描述 | 评价 |
|---|---|---|
| **(a) 生成一个全新的随机 UUID** | 标准 RFC 4122 v4 | ✅ **推荐**：与旧值无任何可关联性 |
| (b) 旧 UUID 改一小段 | 例如只改最后 12 位 | ❌ 仍可被关联到旧值，等于没换 |
| (c) 用一个"通用/已知"UUID | 例如某些教程里的示例值 | ❌ 可能与其它机器冲突，反而制造新问题 |

---

## 4. 执行步骤（**未来**，需用户单独批准；本轮不执行）

1. **记录现状**（不打印真实值）：只记录"四个字段是否齐全"、`ocvalidate` 是否通过。
2. **备份**：`config.plist` 两份（卡上 + 本地 `_backup-round0`）。
3. **只改一个键**：`PlatformInfo → Generic → SystemUUID`。
4. **断言 diff 只有一个键变化**（沿用 `apply-roundN-stick.py` 的"有界 diff"做法）。
5. **`ocvalidate`** → 必须 0 issues。
6. **读回校验**：SHA-256 记录 + 语义 diff 核对。
7. **引导核验**：① 停点是否仍为 `PCI configuration begin`/`PCI0`（**不应该变**）；
   ② NVRAM 是否残留旧 UUID（需要只读工具核对）；
   ③ iServices 是否要求重新登录（人工观察）。
8. **若任一项异常** → 立即回滚到备份 config。

**回滚**：`Copy-Item <备份> <盘符>:\EFI\OC\config.plist -Force`（盘符**动态传入**，**不得**假定 `D:`）。

---

## 5. 本方案**不做**的事（硬边界）

* ❌ 不改 `MLB` / `SystemSerialNumber` / `ROM`；
* ❌ 不改写 Git 历史、不 force-push、不 `filter-repo`；
* ❌ 不宣称"轮换后泄漏就消失了"—— 它只是让**已泄漏的那个值不再代表本机**；
* ❌ 不把"轮换"与"历史清理"捆在一起做。

## 6. 历史清理的单独评估（**不在本方案内**）

若将来确实要清理仓库历史，必须作为**独立且明确批准**的操作：
先完整备份（含 `.git`）、在**副本**上演练、确认所有协作者同步，再做；
并且要接受一个事实：**已公开的内容无法撤回**，清理只是让仓库本身不再携带它。
本仓库的审计脚本只做只读检测，**永远不会**自动执行这类操作。


---

## 7. 2026-10-17 更正记录（用户审核要求）

### 7.1 已核实的事实（只读）

* 仓库 `efi/config.plist`（Round 7 脱敏副本）中：`PlatformInfo.Automatic = true`、
  `UpdateNVRAM = true`、`UpdateDataHub = true`、`UpdateSMBIOS = true`、`UpdateSMBIOSMode = Custom`。
* `1401/ref/oc/Configuration.tex`（OpenCore `963025f`）：
  * `L5827-5829`：该选项 **Sets `system-id` in … `SystemUUID` … `(with swapped byte order)`**；
  * `L6260`：变量全名为 **`4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14:system-id`**；
  * `L5949`：`system-id` 变量**或** SMBIOS 会被"贯穿各节"使用；
  * `L4343/L4372`：`SystemUUID` / `system-id` 的**前 8 字节**还被用作某个随机种子的替代来源
    ⇒ **UUID 不只影响身份，还参与其它初始化输入**，改它可能带来**非身份类**的副作用。
* ⇒ 因此：**"UUID 没有直接相关的 NVRAM 变量"这句话作废**，已在上表更正。

### 7.2 必须分开的四层（不得混为一谈）

| 层 | 内容 | 换 UUID 后的行为 | 需要怎么核实 |
|---|---|---|---|
| **OpenCore 注入** | 每次引导由 OpenCore 把 `PlatformInfo.Generic.SystemUUID` 写进 SMBIOS（并按 `UpdateSMBIOSMode=Custom` 处理），同时写 `system-id` | **每次引导都会被重新写** ⇒ 旧值不会"自然消失"，**也不会"自动变新"以外的残留** | 换完后用只读工具读 SMBIOS/变量，确认已是新值 |
| **启动服务变量** | macOS 运行时可能写入的服务型 NVRAM 变量（与身份相关者） | 可能**保留**到下次引导，也可能被重写 | 逐项只读核对，**不预设** |
| **固件持久变量** | OpenCore/固件写入并**跨引导保留**的变量 | **可能保留**旧值 | 必须在换之前**导出全量变量清单**，换后对比 |
| **操作系统缓存** | macOS 侧的账户/服务缓存（iCloud、iMessage、许可证、`IOPlatformUUID` 绑定） | **不会**因为改 SMBIOS 自动失效 | 只能实测（重新登录/重新授权），并记录 |

**⇒ 结论（写给将来执行的人）**：**不得**默认"重启后必然残留"，**也不得**未经核实就清 NVRAM
（清 NVRAM 会连带清掉 `boot-args` 等，可能让机器**再也进不去当前实验状态**）。
正确做法：**先导出全量变量清单 → 只改一个键 → 引导 → 再导出对比 → 逐项判断**。

### 7.3 本轮的边界（再次确认）

* 本轮**没有**生成、写入或轮换任何 UUID；**没有**清 NVRAM；**没有**改 `MLB`/序列号/`ROM`；
  **没有**改写历史、**没有** force-push。
* 卡上仍是 Round 7：`58E78A12C8102AF7A5DD3B2D7417BE891B17EFC78FF0817C99F69C6BC7A78CA3`。
