#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only, Windows-side PCI topology + resource audit (Round 8).

WHY THIS EXISTS
    docs/08 section 10 needed PCI *bridge-level* data (bus ranges, forwarded /
    prefetchable windows) that 1401's plan.json does not present as a topology.
    Round 8 collects it from Windows only: no extra medium, no third-party tool,
    no administrator right, and not a single PCI configuration-register access.

WHAT IT READS (both read-only, both Windows)
    1. --xml   a PnP dump Windows already wrote:
                 pnputil /enum-devices /connected /deviceids /relations /location \
                          /properties /resources /format xml /output-file pnputil-all.xml
    2. --cfgmgr (optional but recommended) 1401's plan.json, whose
       capture.device_map.pci_resources records come from the CfgMgr32
       device-management API (`CM_Get_First_Log_Conf(ALLOC_LOG_CONF)` +
       `CM_Get_Res_Des_Data`).  It is the RICHER of the two sources: see
       `source_comparison` in the output.

    python pci-windows-audit.py pnputil-all.xml --cfgmgr plan.json \
           --out audit/results/pci-windows

WHY TWO SOURCES AND NOT ONE
    `pnputil /resources` silently omits every `CmResourceTypeMemoryLarge`
    descriptor, i.e. every memory window whose length needs more than 32 bits
    (>= 4 GiB).  Those are exactly the windows that matter on this machine
    (RTX 4050 BAR1 = 8 GiB, GP11 = 64 GiB, the PCI0 64-bit window = 494 GiB).
    A containment/overlap conclusion drawn from the pnputil dump alone is
    therefore unsound - this script proves that, per device, instead of
    asserting it.

DESIGN CONSTRAINTS
    * read-only: opens two files.  No IOCTL, no device handle, no config write.
    * no guessing: every field that Windows cannot supply is listed in `gaps`
      with the reason and the failed attempt, not inferred from something else.
    * derived vs reported is always labelled.  A bus range inferred from the
      children Windows enumerated is `derived`; it cannot distinguish "the
      bridge claims a wider range than it uses" from "it claims exactly that".

REDACTION (--sanitize, the default)
    * the per-machine hash component of every PCI instance ID becomes the
      device's own topology label, e.g. ...\\REV_A1\\<01:00.0>
    * container GUIDs, install / first-install / last-arrival dates, creator
      PIDs and all Binary property blobs are dropped
    * kept on purpose: VEN/DEV/SUBSYS/REV, class codes, LocationPaths including
      the ACPI path, and assigned windows - board topology, not identity.
    Use --raw locally only; never publish --raw output.
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

# --------------------------------------------------------------------------
# Firmware-declared limits, transcribed from this machine's own DSDT.
# Source: audit/acpi/dsdt.dsl (local only - see audit/README.md)
# --------------------------------------------------------------------------
BUS_MIN = 0x00
BUS_MAX_LEGAL = 0xFF            # PCI bus numbers are 8 bit: there is no bus 0x100
BUS_LEN_DECLARED = 0x0100       # _LEN of the WordBusNumber descriptor after the _CRS patch
BUS_MAX_DECLARED = 0xFF         # _MAX after the _CRS patch (see BUS_RANGE_NOTE)

W32_LO, W32_HI = 0xA0000000, 0xDFFFFFFF          # PCI0 32-bit memory window
W64_LO, W64_HI = 0x460000000, 0x7FFFFFFFFF       # PCI0 64-bit memory window
ECAM_LO, ECAM_HI = 0xE0000000, 0xEFFFFFFF        # MCFG ECAM aperture

# CfgMgr32 CM_RESOURCE_MEMORY_* flag bits we actually use
CM_MEM_PREFETCHABLE = 0x04

BUS_RANGE_NOTE = (
    "DSDT \\_SB.PCI0._CRS patches the WordBusNumber template _Y01: "
    "_MIN = BRB = 0x0000, _LEN = BRL = 0x0100, _MAX = _MIN + Local0-- "
    "where Local0 is a *copy* of _LEN. The decrement therefore never touches "
    "_LEN, which stays 0x0100. A bus-number descriptor must satisfy "
    "_LEN = _MAX - _MIN + 1, so _MAX = 0xFF and the range is 0x00-0xFF "
    "(256 buses). Reading BRL as if it were the maximum - '0x00-0x100' - is a "
    "mistake: 0x100 is not a legal bus number. The static template "
    "(_MIN 0, _MAX 0x7F, _LEN 0x80) is dead code, because both _CRS branches "
    "patch the descriptor before returning it."
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
INT_RE = re.compile(r"0x[0-9A-Fa-f]+|\d+")


def as_int(text):
    if text is None:
        return None
    t = str(text).strip()
    try:
        return int(t, 16) if t.lower().startswith("0x") else int(t)
    except ValueError:
        return None


def parse_range(text):
    parts = str(text).split("-")
    if len(parts) != 2:
        return None
    lo, hi = as_int(parts[0]), as_int(parts[1])
    return (lo, hi) if lo is not None and hi is not None else None


def bdf_str(bus, dev, fn):
    if bus is None or dev is None or fn is None:
        return "??:??.?"
    return "%02X:%02X.%X" % (bus, dev, fn)


def to_hex(x):
    return "0x%X" % x


# --------------------------------------------------------------------------
# source 1: the pnputil XML dump
# --------------------------------------------------------------------------
class Pnp(object):
    pass


def load_pnputil(xml_path):
    root = ET.parse(xml_path).getroot()
    devices = []
    for dev in root.findall("Device"):
        props = {}
        for prop in dev.findall("Properties/Property"):
            vals = [v.text for v in prop.findall("Value")]
            props[prop.get("Key")] = vals[0] if len(vals) == 1 else vals
        devices.append({
            "instance_id": dev.get("InstanceId"),
            "description": (dev.findtext("DeviceDescription") or "").strip(),
            "class": (dev.findtext("ClassName") or "").strip(),
            "status": (dev.findtext("Status") or "").strip(),
            "parent": (dev.findtext("Parent") or "").strip() or None,
            "location_info": (dev.findtext("LocationInfo") or "").strip() or None,
            "hardware_ids": [e.text.strip() for e in dev.findall("HardwareIds/HardwareId") if e.text],
            "compatible_ids": [e.text.strip() for e in dev.findall("CompatibleIds/CompatibleId") if e.text],
            "location_paths": [e.text.strip() for e in dev.findall("LocationPaths/LocationPath") if e.text],
            "props": props,
            "mem": [parse_range(r.text or "") for r in dev.findall("MemoryResources/Resource")],
            "io": [parse_range(r.text or "") for r in dev.findall("IoResources/Resource")],
            "irq": [(r.text or "").strip() for r in dev.findall("IrqResources/Resource")],
        })
    return devices


def derive_bdf(rec):
    """BDF from every source Windows offers, cross-checked against each other."""
    bus = as_int(rec["props"].get("DEVPKEY_Device_BusNumber"))
    addr = as_int(rec["props"].get("DEVPKEY_Device_Address"))
    dev = fn = None
    if addr is not None:
        dev, fn = (addr >> 16) & 0xFFFF, addr & 0xFFFF

    path_dev = path_fn = None
    pci_path = acpi_path = None
    for p in rec["location_paths"]:
        if p.startswith("PCIROOT"):
            pci_path = p
            m = re.match(r"PCI\(([0-9A-Fa-f]{4})\)", p.split("#")[-1])
            if m:
                path_dev, path_fn = int(m.group(1)[:2], 16), int(m.group(1)[2:], 16)
        elif p.startswith("ACPI("):
            acpi_path = p

    loc = rec["location_info"] or ""
    nums = [int(x[2:], 16) if x.lower().startswith("0x") else int(x) for x in INT_RE.findall(loc)]
    info = (nums + [None, None, None])[:3] if len(nums) >= 2 else (None, None, None)

    dis = []
    for name, a, b in (("device: Address vs LocationPaths", dev, path_dev),
                       ("function: Address vs LocationPaths", fn, path_fn),
                       ("device: Address vs LocationInfo", dev, info[1]),
                       ("function: Address vs LocationInfo", fn, info[2]),
                       ("bus: BusNumber vs LocationInfo", bus, info[0])):
        if a is not None and b is not None and a != b:
            dis.append("%s (%s vs %s)" % (name, a, b))
    return {"bus": bus, "dev": dev, "fn": fn, "pci_path": pci_path, "acpi_path": acpi_path,
            "location_info": loc or None,
            "sources": {"BusNumber": bus, "Address": addr,
                        "LocationPaths": (path_dev, path_fn) if path_dev is not None else None,
                        "LocationInfo": tuple(info) if info[0] is not None else None},
            "disagreements": dis}


def is_bridge(rec):
    for cid in rec["compatible_ids"]:
        if "CC_060400" in cid or cid.endswith("CC_0604"):
            return True
    dt = rec["props"].get("DEVPKEY_PciDevice_DeviceType")
    return bool(dt and "ridge" in str(dt))


# --------------------------------------------------------------------------
# source 2: 1401's plan.json (CfgMgr32 ALLOC_LOG_CONF records)
# --------------------------------------------------------------------------
def load_cfgmgr(plan_path):
    data = json.load(open(plan_path, encoding="utf-8"))
    recs = []

    def walk(o):
        if isinstance(o, dict):
            if "resource_record" in o and "allocated" in o:
                recs.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    out = {}
    for r in recs:
        loc = r.get("location") or ""
        nums = [int(x) for x in INT_RE.findall(loc.replace("0x", ""))][:3]
        if len(nums) != 3:
            continue
        label = bdf_str(nums[0], nums[1], nums[2])
        windows = []
        irqs = []
        for a in r.get("allocated", []) or []:
            t = a.get("type")
            if t in ("memory", "memory_large") and a.get("base"):
                lo, hi = as_int(a["base"]), as_int(a["end"])
                if lo is not None and hi is not None:
                    windows.append({"lo": lo, "hi": hi, "large_descriptor": t == "memory_large",
                                    "length": hi - lo + 1,
                                    "prefetchable": bool(int(str(a.get("flags", "0")), 16) & CM_MEM_PREFETCHABLE)})
            elif t == "io" and a.get("base"):
                lo, hi = as_int(a["base"]), as_int(a["end"])
                if lo is not None and hi is not None:
                    windows.append({"lo": lo, "hi": hi, "large_descriptor": False,
                                    "length": hi - lo + 1, "io": True})
            elif t == "irq":
                irqs.append(a.get("vector"))
        out.setdefault(label, {"record": r.get("resource_record"),
                               "device_id": r.get("device_id"),
                               "windows": [], "irqs": irqs, "status": r.get("status")})
        out[label]["windows"].extend(windows)
    return out


# --------------------------------------------------------------------------
# analysis
# --------------------------------------------------------------------------
def redact(devices):
    """Instance-ID hash -> the device's own BDF label (topology, not identity)."""
    label_of = {}
    for d in devices:
        if (d["instance_id"] or "").upper().startswith("PCI\\"):
            b = d["_bdf"]
            label_of[d["instance_id"]] = bdf_str(b["bus"], b["dev"], b["fn"])
        else:
            label_of[d["instance_id"]] = "non-pci"
    return label_of


def analyse(xml_path, plan_path=None, sanitize=True):
    devices = load_pnputil(xml_path)
    for d in devices:
        if (d["instance_id"] or "").upper().startswith("PCI\\"):
            d["_bdf"] = derive_bdf(d)
    label_of = redact(devices)
    pci = [d for d in devices if (d["instance_id"] or "").upper().startswith("PCI\\")]

    cfg = load_cfgmgr(plan_path) if plan_path else {}

    # ---------------- device table (merged view; cfgmgr wins where present)
    table = []
    for d in sorted(pci, key=lambda x: (x["_bdf"]["bus"] if x["_bdf"]["bus"] is not None else 1 << 30,
                                        x["_bdf"]["dev"] or 0, x["_bdf"]["fn"] or 0)):
        b = d["_bdf"]
        label = bdf_str(b["bus"], b["dev"], b["fn"])
        cw = cfg.get(label, {}).get("windows", [])
        pw = [w for w in (d["mem"] or []) if w]
        pwns = set(pw)
        cwns = set((w["lo"], w["hi"]) for w in cw if not w.get("io"))
        merged = sorted(cwns | pwns)
        table.append({
            "bdf": label,
            "vendor_device": next((h.split("\\")[1] for h in d["hardware_ids"] if "VEN_" in h), None),            "subsys_rev": next((h.split("\\")[1] for h in d["hardware_ids"] if "SUBSYS_" in h), None),
            "desc": d["description"], "class": d["class"], "status": d["status"],
            "problem": d["props"].get("DEVPKEY_Device_ProblemCode"),
            "parent_bdf": label_of.get(d["parent"]),
            "acpi_path": b["acpi_path"], "pci_path": b["pci_path"],
            "is_bridge": is_bridge(d),
            "windows_merged": [[to_hex(lo), to_hex(hi)] for lo, hi in merged],
            "windows_pnputil": [[to_hex(lo), to_hex(hi)] for lo, hi in sorted(pwns)],
            "windows_cfgmgr": [{"range": [to_hex(w["lo"]), to_hex(w["hi"])],
                                "length": w["length"], "prefetchable": w["prefetchable"],
                                "large_descriptor": w["large_descriptor"]}
                               for w in sorted((w for w in cw if not w.get("io")),
                                               key=lambda w: w["lo"])],
            "io_merged": sorted({(w[0], w[1]) for w in (d["io"] or []) if w} |
                                {(w["lo"], w["hi"]) for w in cw if w.get("io")}),
            "irq": d["irq"],
            "instance_id": d["instance_id"] if not sanitize else None,
            "parent_instance_id": d["parent"] if not sanitize else None,
        })

    # ---------------- topology
    children = {}
    for d in pci:
        p = label_of.get(d["parent"])
        if p:
            children.setdefault(p, []).append(bdf_str(d["_bdf"]["bus"], d["_bdf"]["dev"], d["_bdf"]["fn"]))
    for k in children:
        children[k] = sorted(children[k])

    bridges = []
    for d in pci:
        if not is_bridge(d):
            continue
        label = bdf_str(d["_bdf"]["bus"], d["_bdf"]["dev"], d["_bdf"]["fn"])
        kids = children.get(label, [])
        desc_buses = set()
        queue = list(kids)
        while queue:
            cur = queue.pop()
            bnum = int(cur[:2], 16)
            if bnum not in desc_buses:
                desc_buses.add(bnum)
                queue.extend(children.get(cur, []))
        cw = cfg.get(label, {}).get("windows", [])
        pwns = sorted({w for w in (d["mem"] or []) if w})
        cwns = sorted({(w["lo"], w["hi"]) for w in cw if not w.get("io")})
        bridges.append({
            "bdf": label,
            "vendor_device": next((h.split("\\")[1] for h in d["hardware_ids"] if "VEN_" in h), None),
            "desc": d["description"], "acpi_path": d["_bdf"]["acpi_path"],
            "primary_bus_reported": d["_bdf"]["bus"],
            "secondary_bus_derived": min(int(k[:2], 16) for k in kids) if kids else None,
            "subordinate_bus_derived": max(desc_buses) if desc_buses else None,
            "children": kids, "no_children": not kids,
            "windows_cfgmgr": [{"range": [to_hex(w["lo"]), to_hex(w["hi"])], "length": w["length"],
                                "prefetchable": w["prefetchable"], "large_descriptor": w["large_descriptor"]}
                               for w in sorted((w for w in cw if not w.get("io")), key=lambda w: w["lo"])],
            "windows_pnputil": [[to_hex(lo), to_hex(hi)] for lo, hi in pwns],
            "windows_merged": [[to_hex(lo), to_hex(hi)] for lo, hi in sorted(set(pwns) | set(cwns))],
            "io_merged": sorted({(w[0], w[1]) for w in (d["io"] or []) if w} |
                                {(w["lo"], w["hi"]) for w in cw if w.get("io")}),
        })

    # ---------------- source comparison (the round's key methodological result)
    comparison, only_p, only_c = [], [], []
    for t in table:
        if not t["windows_cfgmgr"] and not t["windows_pnputil"]:
            continue
        cwns = {(as_int(w["range"][0]), as_int(w["range"][1])) for w in t["windows_cfgmgr"]}
        pwns = {(as_int(a), as_int(b)) for a, b in t["windows_pnputil"]}
        for w in sorted(cwns - pwns):
            only_c.append({"bdf": t["bdf"], "window": [to_hex(w[0]), to_hex(w[1])],
                           "length": w[1] - w[0] + 1})
        for w in sorted(pwns - cwns):
            only_p.append({"bdf": t["bdf"], "window": [to_hex(w[0]), to_hex(w[1])],
                           "length": w[1] - w[0] + 1})
        if cwns != pwns:
            comparison.append({"bdf": t["bdf"],
                               "only_in_cfgmgr": [[to_hex(a), to_hex(b)] for a, b in sorted(cwns - pwns)],
                               "only_in_pnputil": [[to_hex(a), to_hex(b)] for a, b in sorted(pwns - cwns)]})
    hyp = {
        "statement": "SCOPE-LIMITED: on this machine the ONLY windows present in the CfgMgr32 "
                     "records but absent from pnputil /resources are the three MemoryLarge "
                     "(>= 4 GiB) ones. The wider rule 'pnputil omits every MemoryLarge "
                     "descriptor' is a HYPOTHESIS consistent with those three observations, "
                     "NOT a verified property of the API - it is not generalised anywhere.",
        "threshold_bytes": 4 * 1024 ** 3,
        "windows_only_in_cfgmgr": len(only_c),
        "all_only_in_cfgmgr_are_over_threshold": all(w["length"] >= 4 * 1024 ** 3 for w in only_c) if only_c else None,
        "min_length_only_in_cfgmgr": min((w["length"] for w in only_c), default=None),
        "windows_only_in_pnputil": len(only_p),
        "verdict": ("the three observations are consistent with the hypothesis"
                    if only_c and all(w["length"] >= 4 * 1024 ** 3 for w in only_c) and not only_p
                    else "NOT consistent - inspect"),
    }

    # ---------------- checks on the MERGED window set
    def contained(lo, hi, ranges):
        return any(a <= lo and hi <= b for a, b in ranges)

    violations = []
    for br in bridges:
        br_ranges = [(as_int(a), as_int(b)) for a, b in br["windows_merged"]]
        br_io = [(lo, hi) for lo, hi in br["io_merged"]]
        for kid in br["children"]:
            kt = next((t for t in table if t["bdf"] == kid), None)
            if not kt:
                continue
            for rng in kt["windows_merged"]:
                lo, hi = as_int(rng[0]), as_int(rng[1])
                if not contained(lo, hi, br_ranges):
                    violations.append({"bridge": br["bdf"], "child": kid,
                                       "child_window": rng,
                                       "bridge_windows": br["windows_merged"],
                                       "kind": "child memory window not inside any bridge window"})
            for rng in kt["io_merged"]:
                lo, hi = as_int(rng[0]), as_int(rng[1])
                if not contained(lo, hi, br_io):
                    violations.append({"bridge": br["bdf"], "child": kid,
                                       "child_window": [to_hex(lo), to_hex(hi)],
                                       "bridge_windows": [[to_hex(a), to_hex(b)] for a, b in br_io],
                                       "kind": "child IO window not inside any bridge window"})

    outside = []
    for t in table:
        for rng in t["windows_merged"]:
            lo, hi = as_int(rng[0]), as_int(rng[1])
            if W32_LO <= lo and hi <= W32_HI:
                continue
            if W64_LO <= lo and hi <= W64_HI:
                continue
            outside.append({"bdf": t["bdf"], "window": rng,
                            "kind": "32-bit address space, outside the DSDT PCI0 32-bit window"
                            if lo < 0x100000000 else
                            "64-bit address space, outside the DSDT PCI0 64-bit window"})

    wins = []
    for t in table:
        for rng in t["windows_merged"]:
            wins.append((as_int(rng[0]), as_int(rng[1]), t["bdf"]))
    wins.sort()
    overlaps = []
    for i in range(len(wins)):
        for j in range(i + 1, len(wins)):
            if wins[j][0] > wins[i][1]:
                break
            a, b = wins[i], wins[j]
            if a[2] == b[2]:
                continue
            lo, hi = max(a[0], b[0]), min(a[1], b[1])
            if lo > hi:
                continue
            overlaps.append({"a": a[2], "b": b[2], "range": [to_hex(lo), to_hex(hi)],
                             "containment": (a[0] <= b[0] and b[1] <= a[1]) or (b[0] <= a[0] and a[1] <= b[1])})
    partial = [o for o in overlaps if not o["containment"]]

    used_buses = sorted({t["bdf"] and int(t["bdf"][:2], 16) for t in table if "?" not in t["bdf"]})

    # ---------------- things Windows provably cannot answer
    # GUID-keyed property names are collapsed to a placeholder: what matters is that a
    # GUID-keyed property exists, not which driver GUID it is.
    guid_re = re.compile(r"\{[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                         r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}")

    def redact_key(k):
        return guid_re.sub("{device-property-guid}", k)

    prop_keys = {}
    for d in pci:
        for k in d["props"]:
            rk = redact_key(k)
            prop_keys[rk] = prop_keys.get(rk, 0) + 1
    gaps = [
        {"field": "PCI-to-PCI bridge Primary / Secondary / Subordinate Bus Number "
                  "registers (config space 0x18/0x19/0x1A)",
         "available": False,
         "attempted": [
             "DEVPKEY_Device_DeviceNumber / DEVPKEY_Device_FunctionNumber: DO NOT EXIST "
             "on this build - the full per-device property inventory contains "
             "DEVPKEY_Device_BusNumber and DEVPKEY_Device_Address only (see prop_keys).",
             "CfgMgr32 CM_Get_First_Log_Conf(ALLOC_LOG_CONF / BASIC_LOG_CONF / BOOT_LOG_CONF) "
             "opens successfully here, but CM_Get_Next_Res_Des never returns CR_SUCCESS for "
             "these devices: the documented first-descriptor form (LOG_CONF handle passed as "
             "rdResDes) returns CR_INVALID_FLAG (4) for every ForType 0x00..0x41, with both a "
             "32-bit ULONG handle declaration and a zero-initialised pointer-sized one, and "
             "NULL also returns 4. So that particular CALL SHAPE was not usable in this "
             "session. (CM_Get_First_Res_Des is not exported by cfgmgr32.dll here, but that "
             "is NOT offered as the reason the values are unavailable - see below.)",
             "The registry logical-configuration values WERE read and fully decoded "
             "(audit/pci-logconf-audit.py): BootConfig is a complete REG_RESOURCE_LIST and "
             "BasicConfigVector a complete REG_RESOURCE_REQUIREMENTS_LIST, each parsing to "
             "its declared size with zero residual bytes. Neither contains ANY descriptor of "
             "type CmResourceTypeBusNumber - checked on all 25 PCI functions that have a "
             "LogConf key (0 found). So Windows does not record a bus-number resource for "
             "these bridges at all, regardless of which call is used.",
         ],
         "proxy": "primary = the bridge's own DEVPKEY_Device_BusNumber (reported); secondary and "
                  "subordinate are DERIVED from the buses of the functions Windows enumerated "
                  "underneath the bridge.",
         "consequence": "a derived range cannot distinguish 'bridge claims a wider bus range than "
                        "it uses' from 'bridge claims exactly what it uses'; a childless bridge "
                        "yields unknown, not empty. The question 'do two bridges claim "
                        "overlapping bus ranges?' cannot be answered from Windows data - and the "
                        "real reason is that no Windows source carries the value, not a missing "
                        "API name."},
        {"field": "bridge Memory Base/Limit and Prefetchable Memory Base/Limit registers",
         "available": "proxy only",
         "attempted": ["raw configuration space is not exposed by any Windows user-mode API."],
         "proxy": "the CfgMgr32 ALLOC_LOG_CONF window records (base, end, flags) which pci.sys "
                  "built from those registers, incl. CM_RESOURCE_MEMORY_PREFETCHABLE (0x04).",
         "consequence": "this is a decoded record, not a register read: a window that the "
                        "firmware never assigned cannot be reconstructed from it, and the "
                        "register's alignment/granularity bits are invisible."},
        {"field": "PCI Command (0x04) / Status (0x06) registers",
         "available": False,
         "attempted": ["not exposed as a device property."],
         "proxy": "DEVPKEY_PciDevice_* capability bits only (AcsSupport, AriSupport, AtsSupport, "
                  "BarTypes, DeviceType, ExpressSpecVersion, ...), all captured."},
        {"field": "individual BAR registers with index and size encoding",
         "available": "proxy only",
         "attempted": ["not exposed."],
         "proxy": "resource ranges give base+length; DEVPKEY_PciDevice_BarTypes gives the per-BAR "
                  "type flags. The BAR *index* is not given."},
        {"field": "the bridge's REQUIRED (unassigned) window, i.e. what it would request on a "
                  "clean re-enumeration",
         "available": False,
         "attempted": ["Windows reports what it assigned or accepted, not the requirement list; "
                       "CM_Get_First_Res_Des - the requirement-side call - is unavailable here."],
         "proxy": None},
        {"field": "an undocumented Binary device property on 33 devices, "
                  "GUID {f0e20f09-d97a-49a9-8046-bb6e22e6bb2e}[2]",
         "available": False,
         "attempted": ["dumped as bytes for every device that carries it (96 / 184 / 360 / 1504 B).",
                       "it DOES carry the device's interrupt pseudo-vector (offset 64 = 0xFFFFFFFE "
                       "for GPP0 = -2, matching its CfgMgr32 irq record) and 0xFEE00000 (Local APIC).",
                       "it does NOT carry the bridge 64-bit windows: 0x7C00000000, 0x7E01FFFFFF, "
                       "0x6C00000000 and 0x7BFFFFFFFF appear nowhere in the whole dump, in text or "
                       "in the byte blobs."],
         "proxy": None,
         "consequence": "unidentified, therefore NOT used as evidence anywhere in this document."},
        {"field": "macOS's own PCI resource assignment",
         "available": False,
         "attempted": ["not observable: this machine's macOS never reaches a userland in which it "
                       "could be read (docs/06 section 7)."],
         "proxy": None},
    ]

    root_bus = next(({"acpi_id": "PNP0A08",
                      "instance_id": d["instance_id"] if not sanitize else None,
                      "description": d["description"],
                      "mem": [[to_hex(a), to_hex(b)] for a, b in (d["mem"] or []) if a is not None],
                      "io": [[to_hex(a), to_hex(b)] for a, b in (d["io"] or []) if a is not None]}
                     for d in devices if "PNP0A08" in (d["instance_id"] or "")), None)

    return {
        "sources": {
            "pnputil_xml": os.path.basename(xml_path),
            "cfgmgr_plan_json": os.path.basename(plan_path) if plan_path else None,
            "note": "pnputil = PnP IRP/CM view; cfgmgr = CfgMgr32 ALLOC_LOG_CONF. Both are "
                    "Windows-side snapshots of the SAME boot; neither is a register dump and "
                    "neither is macOS's assignment.",
        },
        "device_count_pci": len(pci),
        "devices": table,
        "bridges": bridges,
        "pci_root_bus": root_bus,
        "source_comparison": comparison,
        "memory_large_hypothesis": hyp,
        "containment_violations": violations,
        "windows_outside_declared": outside,
        "buses_observed": ["0x%02X" % b for b in used_buses],
        "buses_above_legal_max": ["0x%02X" % b for b in used_buses if b > BUS_MAX_LEGAL],
        "overlaps": overlaps,
        "partial_overlaps": partial,
        "declared_limits": {"bus_min": to_hex(BUS_MIN), "bus_len_declared": to_hex(BUS_LEN_DECLARED),
                            "bus_max_declared": to_hex(BUS_MAX_DECLARED),
                            "bus_max_legal": to_hex(BUS_MAX_LEGAL), "note": BUS_RANGE_NOTE,
                            "w32": [to_hex(W32_LO), to_hex(W32_HI)],
                            "w64": [to_hex(W64_LO), to_hex(W64_HI)],
                            "ecam": [to_hex(ECAM_LO), to_hex(ECAM_HI)]},
        "gaps": gaps,
        "prop_keys": dict(sorted(prop_keys.items())),
        "device_number_property_present": any("Device_DeviceNumber" in k for k in prop_keys),
        "function_number_property_present": any("Device_FunctionNumber" in k for k in prop_keys),
        "bdf_source_disagreements": [{"bdf": d["bdf"], "disagreements": d["_bdf"]["disagreements"]}
                                     for d in pci if d["_bdf"]["disagreements"]],
    }


# --------------------------------------------------------------------------
def render(r):
    L = []
    L.append("# Round 8 - Windows-side PCI topology and resource audit (read-only)")
    L.append("")
    L.append("Sources: `%s` + `%s`" % (r["sources"]["pnputil_xml"], r["sources"]["cfgmgr_plan_json"]))
    L.append("")
    L.append("## 1. PCI functions (%d)" % r["device_count_pci"])
    L.append("")
    L.append("| BDF | vendor:device | class | problem | parent | ACPI path | windows (merged) |")
    L.append("|---|---|---|---|---|---|---|")
    for d in r["devices"]:
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            d["bdf"], d["vendor_device"], d["class"],
            "-" if d["problem"] in (None, "0x00000000") else d["problem"],
            d["parent_bdf"] or "-", d["acpi_path"] or "-",
            ", ".join("%s-%s" % (a, b) for a, b in d["windows_merged"]) or "-"))
    L.append("")
    L.append("## 2. PCI-to-PCI bridges (%d)" % len(r["bridges"]))
    for b in r["bridges"]:
        L.append("")
        L.append("### %s - %s (%s)" % (b["bdf"], b["vendor_device"], b["desc"]))
        L.append("* ACPI: `%s`" % b["acpi_path"])
        L.append("* primary bus (reported) = %s" % b["primary_bus_reported"])
        L.append("* secondary / subordinate (**derived from children, not read**) = %s / %s" % (
            b["secondary_bus_derived"], b["subordinate_bus_derived"]))
        L.append("* children: %s" % (", ".join(b["children"]) or "(none - derived range unknown)"))
        L.append("* forwarded memory, CfgMgr32 (authoritative): %s" % (
            ", ".join("%s-%s%s%s" % (w["range"][0], w["range"][1],
                                     " [PREFETCHABLE]" if w["prefetchable"] else "",
                                     " [MemoryLarge]" if w["large_descriptor"] else "")
                      for w in b["windows_cfgmgr"]) or "(none)"))
        L.append("* forwarded memory, pnputil (lossy - drops MemoryLarge): %s" % (
            ", ".join("%s-%s" % (a, b2) for a, b2 in b["windows_pnputil"]) or "(none)"))
        L.append("* forwarded IO: %s" % (", ".join("%X-%X" % (a, b2) for a, b2 in b["io_merged"]) or "(none)"))
    L.append("")
    L.append("## 3. Source comparison - pnputil vs CfgMgr32")
    L.append("")
    L.append("* devices whose window set differs: **%d**" % len(r["source_comparison"]))
    for c in r["source_comparison"]:
        L.append("  * `%s` only_in_cfgmgr=%s only_in_pnputil=%s" % (
            c["bdf"], c["only_in_cfgmgr"] or "[]", c["only_in_pnputil"] or "[]"))
    h = r["memory_large_hypothesis"]
    L.append("* hypothesis: %s" % h["statement"])
    L.append("  * windows only in cfgmgr: %d ; min length: %s B ; all >= 4 GiB: %s" % (
        h["windows_only_in_cfgmgr"], h["min_length_only_in_cfgmgr"],
        h["all_only_in_cfgmgr_are_over_threshold"]))
    L.append("  * windows only in pnputil: %d" % h["windows_only_in_pnputil"])
    L.append("  * verdict: **%s**" % h["verdict"])
    L.append("")
    L.append("## 4. Checks on the MERGED window set")
    L.append("* buses observed: %s ; above the legal 0xFF: %s" % (
        ", ".join(r["buses_observed"]), ", ".join(r["buses_above_legal_max"]) or "none"))
    L.append("* child window not inside any parent-bridge window: **%d**" % len(r["containment_violations"]))
    for v in r["containment_violations"]:
        L.append("  * %s" % json.dumps(v, ensure_ascii=False))
    L.append("* windows outside the DSDT-declared PCI0 windows: **%d**" % len(r["windows_outside_declared"]))
    for v in r["windows_outside_declared"]:
        L.append("  * %s" % json.dumps(v, ensure_ascii=False))
    L.append("* overlapping window pairs: %d ; of which PARTIAL: **%d**" % (
        len(r["overlaps"]), len(r["partial_overlaps"])))
    for v in r["partial_overlaps"]:
        L.append("  * PARTIAL %s" % json.dumps(v, ensure_ascii=False))
    L.append("")
    L.append("## 5. PCI root bus (ACPI\\PNP0A08)")
    rb = r["pci_root_bus"]
    if rb:
        L.append("* memory as reported by pnputil: %s" % ", ".join("%s-%s" % tuple(m) for m in rb["mem"]))
        L.append("* IO as reported by pnputil: %s" % ", ".join("%s-%s" % tuple(m) for m in rb["io"]))
        L.append("* NOTE: the DSDT's 64-bit window %s-%s is NOT in this list - it is a "
                 "MemoryLarge descriptor, see section 3." % tuple(r["declared_limits"]["w64"]))
    L.append("")
    L.append("## 6. What Windows cannot answer (registered, not guessed)")
    for g in r["gaps"]:
        L.append("* **%s** -> available=%s" % (g["field"], g["available"]))
        for a in g.get("attempted", []) or []:
            L.append("  * attempted: %s" % a)
        if g.get("proxy"):
            L.append("  * proxy: %s" % g["proxy"])
        if g.get("consequence"):
            L.append("  * consequence: %s" % g["consequence"])
    L.append("")
    L.append("## 7. BDF provenance")
    L.append("* DEVPKEY_Device_DeviceNumber present: %s ; DEVPKEY_Device_FunctionNumber present: %s" % (
        r["device_number_property_present"], r["function_number_property_present"]))
    L.append("* devices where BusNumber / Address / LocationPaths / LocationInfo disagree: %d" % (
        len(r["bdf_source_disagreements"])))
    for d in r["bdf_source_disagreements"]:
        L.append("  * %s: %s" % (d["bdf"], "; ".join(d["disagreements"])))
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xml")
    ap.add_argument("--cfgmgr", default=None, help="1401 plan.json carrying CfgMgr32 records")
    ap.add_argument("--out", default=None)
    ap.add_argument("--raw", action="store_true", help="do NOT redact (local only)")
    args = ap.parse_args()

    result = analyse(args.xml, args.cfgmgr, sanitize=not args.raw)
    if args.out:
        d = os.path.dirname(os.path.abspath(args.out))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(args.out + ".json", "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=1, ensure_ascii=False)
        with open(args.out + ".md", "w", encoding="utf-8") as fh:
            fh.write(render(result))
        print("wrote %s.json / %s.md" % (args.out, args.out))
    else:
        print(render(result))


if __name__ == "__main__":
    sys.exit(main())
