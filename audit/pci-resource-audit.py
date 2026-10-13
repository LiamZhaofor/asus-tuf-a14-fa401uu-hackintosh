#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only PCI resource-map audit of 1401's plan.json (cited by docs/08 section 10.1).

The records this reads are 1401's `capture.device_map.pci_resources` entries, which are
collected with the CfgMgr32 device-management API:

    CM_Get_First_Log_Conf(hDevInst, ALLOC_LOG_CONF)  ->  CM_Get_Next_Res_Des  ->  CM_Get_Res_Des_Data

i.e. the *allocated logical configuration* Windows' pci.sys recorded for each function.
That is NOT a PCI configuration-space dump: it is what Windows believes it assigned.
Two consequences, both load-bearing:

  * every window the firmware assigned AND Windows kept is present, including 64-bit /
    prefetchable ones (flags bit 0x04) - which the `pnputil /resources` view silently drops
    whenever the descriptor is a CmResourceTypeMemoryLarge one (length >= 4 GiB);
  * windows the firmware never assigned cannot be reconstructed from it, and the bridge
    registers behind it (Memory Base/Limit, Prefetchable Base/Limit, bus numbers) are
    still not readable this way.

Usage:
    python pci-resource-audit.py [plan.json]

Answers, with data already on disk (no new hardware step, no writes):
  * every PCI function's allocated memory / memory_large / io window
  * whether each window lies inside the DSDT-declared PCI0 windows
    (32-bit 0xA0000000-0xDFFFFFFF, 64-bit 0x460000000-0x7FFFFFFFFF)
  * pairwise overlaps between those windows
  * 32-bit / 64-bit window occupancy and headroom
  * the PCI topology (buses and functions) recorded in the capture
"""
import json
import sys

DEFAULT_PLAN = r"1401\plan.json"

W32_LO, W32_HI = 0xA0000000, 0xDFFFFFFF          # DSDT PCI0 32-bit window (MBB..MBB+MBL-1)
W64_LO, W64_HI = 0x460000000, 0x7FFFFFFFFF       # DSDT PCI0 64-bit window (MAB..MAM)
ECAM_LO, ECAM_HI = 0xE0000000, 0xEFFFFFFF        # MCFG ECAM aperture
RT_LO, RT_HI = 0x460000000, 0x4801FFFFF          # firmware runtime-MMIO descriptor #4


def find_records(o, out, path=""):
    if isinstance(o, dict):
        if "resource_record" in o and "allocated" in o:
            out.append((path, o))
        for k, v in o.items():
            find_records(v, out, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            find_records(v, out, path + "/%d" % i)


def num(x):
    if isinstance(x, str):
        return int(x, 16) if x.lower().startswith("0x") else int(x)
    return int(x)


def main():
    plan = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PLAN
    data = json.load(open(plan, encoding="utf-8"))
    recs = []
    find_records(data, recs)
    print("resource records found:", len(recs))

    ranges = []          # (lo, hi, kind, device, location, record)
    for path, rec in recs:
        dev = rec.get("device_id", "?")
        loc = rec.get("location", "?")
        for a in rec.get("allocated", []):
            t = a.get("type")
            if t not in ("memory", "memory_large", "io"):
                continue
            try:
                lo, hi = num(a["base"]), num(a["end"])
            except Exception:
                continue
            ranges.append((lo, hi, t, dev, loc, rec.get("resource_record")))

    print("allocated memory/io ranges:", len(ranges))
    print()

    print("=== every memory / memory_large window (sorted by base) ===")
    print("%-14s %-6s %-3s %-38s %-26s %s" % ("base", "end", "kind", "device", "location", "note"))
    for lo, hi, t, dev, loc, rr in sorted(ranges):
        if t == "io":
            continue
        note = []
        if W32_LO <= lo and hi <= W32_HI:
            note.append("in-32bit-win")
        elif W64_LO <= lo and hi <= W64_HI:
            note.append("in-64bit-win")
        else:
            note.append("*** OUTSIDE declared PCI0 windows")
        if not (W32_LO <= lo <= W32_HI) and (lo < 0x100000000):
            note.append("32-bit-addr-but-outside")
        print("0x%-12X 0x%-4X %-3s %-38s %-26s %s"
              % (lo, hi, "M" if t == "memory" else "L", dev[-36:], loc[-24:], " ".join(note)))

    print()
    print("=== IO windows ===")
    for lo, hi, t, dev, loc, rr in sorted(ranges):
        if t == "io":
            print("  0x%X-0x%X  %s  %s" % (lo, hi, dev[-36:], loc[-24:]))

    print()
    print("=== pairwise overlaps among memory windows ===")
    mem = sorted([r for r in ranges if r[2] != "io"])
    seen = set()
    ov = 0
    for i in range(len(mem)):
        for j in range(i + 1, len(mem)):
            a, b = mem[i], mem[j]
            if a[1] < b[0]:
                break
            lo, hi = max(a[0], b[0]), min(a[1], b[1])
            if lo <= hi:
                ov += 1
                key = (a[3], b[3], lo, hi)
                if key in seen:
                    continue
                seen.add(key)
                print("  OVERLAP 0x%X-0x%X : %s  <->  %s"
                      % (lo, hi, a[3][-34:], b[3][-34:]))
    if ov == 0:
        print("  none")

    print()
    print("=== window occupancy ===")
    used32 = sum(hi - lo + 1 for lo, hi, t, *_ in mem if t == "memory" and W32_LO <= lo and hi <= W32_HI)
    used64 = sum(hi - lo + 1 for lo, hi, t, *_ in mem if t == "memory_large" and W64_LO <= lo and hi <= W64_HI)
    print("  DSDT 32-bit window : 0x%X-0x%X  size %.1f MiB ; assigned inside = %.1f MiB (%.1f%%) ; headroom = %.1f MiB"
          % (W32_LO, W32_HI, (W32_HI - W32_LO + 1) / 1048576, used32 / 1048576,
             100.0 * used32 / (W32_HI - W32_LO + 1), ((W32_HI - W32_LO + 1) - used32) / 1048576))
    print("  DSDT 64-bit window : 0x%X-0x%X  size %.0f GiB ; assigned inside = %.1f MiB ; headroom = %.0f GiB"
          % (W64_LO, W64_HI, (W64_HI - W64_LO + 1) / 1073741824, used64 / 1048576,
             ((W64_HI - W64_LO + 1) - used64) / 1073741824))
    print("  ECAM               : 0x%X-0x%X" % (ECAM_LO, ECAM_HI))
    print("  runtime MMIO #4    : 0x%X-0x%X  (overlaps DSDT 64-bit window base: %s)"
          % (RT_LO, RT_HI, W64_LO <= RT_HI and RT_LO <= W64_HI))

    print()
    print("=== PCI topology present in the capture (from location_paths) ===")
    paths = set()

    def walk_paths(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "location_paths" and isinstance(v, list):
                    for p in v:
                        if isinstance(p, str) and p.startswith("PCIROOT"):
                            paths.add(p)
                else:
                    walk_paths(v)
        elif isinstance(o, list):
            for v in o:
                walk_paths(v)

    walk_paths(data)
    for p in sorted(paths):
        print("  ", p)
    print("  total distinct PCI paths:", len(paths))


if __name__ == "__main__":
    main()
