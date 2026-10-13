# `efi/candidates/` —— 待批准的候选配置

**规则（避免"仓库里有两份看起来是当前配置的文件"这类混淆）：**

* **`efi/config.plist` 永远是「卡上现在的真实状态」的脱敏副本。** 由
  `scripts/sync-to-github.ps1` 自动生成，不要手工编辑。
* **本目录下的文件是「尚未写入卡上」的候选方案**，只用于评审。
  一旦获批写入卡上，它就会被提升为 `efi/config.plist`，并从本目录删除。

判断"当前在测什么"永远以 [docs/05-受控实验记录.md](../../docs/05-受控实验记录.md) 为准。

| 候选 | 相对卡上状态 | 状态 |
|---|---|---|
| [`round6-npci-0x3000.plist`](round6-npci-0x3000.plist) | `NVRAM → Add → 7C436110-…:boot-args` 末尾追加 ` npci=0x3000`（**仅此 1 行**，1-based 行号 1920；52124 → 52136 B） | **待批准**（Round 6 唯一候选，见 `docs/07` §8 与 §10） |

> `round5B-devirtualisemmio-false.plist` 已于 **2026-10-13 获批并写入卡上**
> （`Booter.Quirks.DevirtualiseMmio`：`true` → `false`，**只此 1 行**，1-based 行号 171；
> 卡上 `021F02B3…` → `34605D9D…`，52124 → 52125 B，`ocvalidate` → No issues found）。
> **该轮已引导并结案**：配置生效、实机未能成功启动、**首轮已确认 ≥10 分钟无新屏幕输出**
> （次轮只有 OpenCore 日志、无照片，**不得**记为同样等待 10 分钟）。
> **随后已按批准回滚到 Round 4**（卡上现为 `021F02B3…`）。
> 记录见 `docs/05` §7.13 / §7.14，候选评估见 `docs/06` §4.6。

> `round4-mat-triple.plist` 已于获批后**写入卡上**，因此转正为 `efi/config.plist` 并从本目录移除。
> 其改动（3 行，`EnableWriteUnprotector` / `RebuildAppleMemoryMap` / `SyncRuntimePermissions`）
> 记录在 `docs/05` §7.4 与 §7.9。
>
> `round3-drop-npci.plist` 同理，已于更早一轮转正；改动（1 行）见 `docs/05` §6.2 与 §6.7。

本目录下的任何文件在提交前都必须经过 `scripts/sanitize-config.py` 置零身份字段，
并通过 OpenCore 1.0.9 的 `ocvalidate`（同步脚本会自动做这两件事）。
