#!/usr/bin/env python3
"""直接修改 U 盘上的 OpenCore config.plist —— 不需要管理员权限。

为什么需要这个：`config.plist` 只是 FAT32 分区上的一个普通文件，
**改一个 boot-arg 或一个 quirk 根本不需要提权、更不需要重写整个安装盘**。
而重写安装盘（`1401` 的 usbwriter）需要管理员权限，一次要一两分钟。
调试阶段"改一个参数 → 重启试试"的迭代，用本脚本是秒级的。

每次修改前会自动备份到 `<config>.backup-<时间戳>`。

用法示例
--------
# 看看当前的关键参数
python patch-stick-config.py --show

# 追加一个启动参数（npci=0x2000 用于越过 "PCI configuration begin" 卡死）
python patch-stick-config.py --boot-arg npci=0x2000

# 删除一个启动参数
python patch-stick-config.py --del-boot-arg npci=0x2000

# 改 quirks / 任意嵌套键（值自动推断 bool / int / string）
python patch-stick-config.py --set Booter.Quirks.DevirtualiseMmio False
python patch-stick-config.py --set Booter.Quirks.EnableWriteUnprotector True
python patch-stick-config.py --set Misc.Security.DmgLoading Any

# 删掉一个 kext 注入项（按 BundlePath 匹配）
python patch-stick-config.py --remove-kext HoRNDIS.kext

# 删掉一张 ACPI 表（按文件名匹配）
python patch-stick-config.py --remove-acpi SSDT-Disable_Network_GPG6.aml

# 指定别的盘/路径
python patch-stick-config.py --config E:\\EFI\\OC\\config.plist --show
"""
import argparse
import datetime
import os
import plistlib
import shutil
import sys


def traverse(cfg, dotted, create=False):
    """按 'A.B.C' 走到嵌套 dict，返回 (parent, key)。"""
    parts = dotted.split(".")
    node = cfg
    for p in parts[:-1]:
        if p not in node:
            if not create:
                raise KeyError(dotted)
            node[p] = {}
        node = node[p]
    return node, parts[-1]


def coerce(text):
    low = text.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    try:
        return int(text, 0)
    except ValueError:
        return text


def boot_args(cfg):
    return cfg["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]


def do_show(cfg):
    print("=== 启动参数 ===")
    print("  boot-args        :", boot_args(cfg).get("boot-args"))
    print("  csr-active-config:", (boot_args(cfg).get("csr-active-config") or b"").hex())
    print("\n=== Booter.Quirks（内存映射相关）===")
    q = cfg["Booter"]["Quirks"]
    for k in ("DevirtualiseMmio", "SetupVirtualMap", "RebuildAppleMemoryMap",
              "EnableWriteUnprotector", "SyncRuntimePermissions", "ResizeAppleGpuBars"):
        print(f"  {k:26} = {q.get(k)}")
    print("\n=== UEFI.Quirks ===")
    print("  ResizeGpuBars             =", cfg["UEFI"]["Quirks"].get("ResizeGpuBars"))
    print("\n=== Misc.Security ===")
    for k in ("DmgLoading", "SecureBootModel", "Vault"):
        print(f"  {k:26} = {cfg['Misc']['Security'].get(k)}")
    print("\n=== Kernel.Add（%d 项）===" % len(cfg["Kernel"]["Add"]))
    for e in cfg["Kernel"]["Add"]:
        flag = "on " if e.get("Enabled") else "off"
        print(f"  [{flag}] {e.get('BundlePath')}")
    print("\n=== ACPI.Add ===")
    for e in cfg["ACPI"]["Add"]:
        flag = "on " if e.get("Enabled") else "off"
        print(f"  [{flag}] {e.get('Path')}")


def main():
    ap = argparse.ArgumentParser(description="免提权修改 U 盘上的 OpenCore config.plist")
    ap.add_argument("--config", default=None,
                    help="卡上 EFI/OC/config.plist 的路径，必须显式给出（盘符会变化，没有默认值）")
    ap.add_argument("--show", action="store_true", help="只显示当前配置，不修改")
    ap.add_argument("--boot-arg", action="append", default=[], help="追加启动参数")
    ap.add_argument("--del-boot-arg", action="append", default=[], help="删除启动参数")
    ap.add_argument("--set", nargs=2, action="append", default=[], metavar=("KEY", "VALUE"),
                    help="设置嵌套键，如 Booter.Quirks.DevirtualiseMmio False")
    ap.add_argument("--remove-kext", action="append", default=[], help="按 BundlePath 删除 kext 注入项")
    ap.add_argument("--remove-acpi", action="append", default=[], help="按 Path 删除 ACPI 注入项")
    a = ap.parse_args()

    if not a.config:
        sys.exit("必须用 --config 指定卡上 EFI/OC/config.plist 的真实路径（盘符会变化，没有默认值）")
    if not os.path.isfile(a.config):
        sys.exit(f"找不到 {a.config}（U 盘插好了吗？）")

    with open(a.config, "rb") as f:
        cfg = plistlib.load(f)

    if a.show and not (a.boot_arg or a.del_boot_arg or a.set or a.remove_kext or a.remove_acpi):
        do_show(cfg)
        return

    changes = []

    if a.boot_arg or a.del_boot_arg:
        nv = boot_args(cfg)
        args = nv.get("boot-args", "").split()
        for x in a.del_boot_arg:
            before = len(args)
            args = [y for y in args if y != x and not y.startswith(x + "=")]
            changes.append(f"删除启动参数 {x}（{before - len(args)} 项）")
        for x in a.boot_arg:
            if x in args:
                changes.append(f"启动参数 {x} 已存在，跳过")
            else:
                args.append(x)
                changes.append(f"追加启动参数 {x}")
        nv["boot-args"] = " ".join(args)

    for key, val in a.set:
        parent, leaf = traverse(cfg, key, create=True)
        old = parent.get(leaf, "<不存在>")
        parent[leaf] = coerce(val)
        changes.append(f"{key}: {old!r} -> {parent[leaf]!r}")

    for name in a.remove_kext:
        before = len(cfg["Kernel"]["Add"])
        cfg["Kernel"]["Add"] = [e for e in cfg["Kernel"]["Add"] if e.get("BundlePath") != name]
        changes.append(f"删除 kext 注入 {name}（{before - len(cfg['Kernel']['Add'])} 项）")

    for name in a.remove_acpi:
        before = len(cfg["ACPI"]["Add"])
        cfg["ACPI"]["Add"] = [e for e in cfg["ACPI"]["Add"] if e.get("Path") != name]
        changes.append(f"删除 ACPI 注入 {name}（{before - len(cfg['ACPI']['Add'])} 项）")

    if not changes:
        print("没有任何改动。用 --show 查看当前配置，或 --help 看用法。")
        return

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{a.config}.backup-{stamp}"
    shutil.copyfile(a.config, backup)

    with open(a.config, "wb") as f:
        plistlib.dump(cfg, f)

    print("改动：")
    for c in changes:
        print("  -", c)
    print(f"\n已写入 {a.config}")
    print(f"备份   {backup}")

    # 尽量用官方 ocvalidate 复核
    try:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "1401", "engine", "app")))
        from p1401 import validate
        ok, n, text = validate.run_ocvalidate(a.config)
        print(f"\nocvalidate: {'OK' if ok else '有问题'}  issues={n}")
        print(" ", text.strip().splitlines()[-1])
    except Exception:
        print("\n（未找到 p1401 包，跳过 ocvalidate 复核）")


if __name__ == "__main__":
    main()
