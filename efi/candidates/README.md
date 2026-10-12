# `efi/candidates/` —— 待批准的候选配置

**规则（避免"仓库里有两份看起来是当前配置的文件"这类混淆）：**

* **`efi/config.plist` 永远是「卡上现在的真实状态」的脱敏副本。** 由
  `scripts/sync-to-github.ps1` 自动生成，不要手工编辑。
* **本目录下的文件是「尚未写入卡上」的候选方案**，只用于评审。
  一旦获批写入卡上，它就会被提升为 `efi/config.plist`，并从本目录删除。

判断"当前在测什么"永远以 [docs/05-受控实验记录.md](../../docs/05-受控实验记录.md) 为准。

| 候选 | 相对卡上状态 | 状态 |
|---|---|---|
| `round3-drop-npci.plist` | 只删掉 `boot-args` 里的 ` npci=0x2000`（1 行） | **待批准** |

> 该候选与卡上配置的差异已完整记录在 `docs/05` §6.2，并已用 OpenCore 1.0.9 的 `ocvalidate`
> 校验（No issues found）。所有身份字段已按 `scripts/sanitize-config.py` 置零。
