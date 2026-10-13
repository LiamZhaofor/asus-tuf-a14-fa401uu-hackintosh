#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decode the Windows registry logical-configuration blobs (read-only) for a PCI function.

WHY
    Round 8 established that `pnputil /resources` drops >= 4 GiB windows, and that the
    CfgMgr32 descriptor-walk call we could construct never returns CR_SUCCESS on this
    build.  There is a third, fully read-only Windows source that DOES carry the complete
    descriptor sets:

        HKLM\\SYSTEM\\CurrentControlSet\\Enum\\PCI\\<device>\\<instance>\\LogConf
            BootConfig          REG_RESOURCE_LIST               (what the FIRMWARE handed over)
            BasicConfigVector   REG_RESOURCE_REQUIREMENTS_LIST (min/max RANGE + required LENGTH)

    `.NET`'s RegistryValueKind cannot materialise either type (both come back as
    `Unknown`/null), so they must be read with RegQueryValueEx - see audit/dump-logconf.ps1.

LAYOUTS (Windows SDK)
    CM_RESOURCE_LIST              { ULONG Count; CM_FULL_RESOURCE_DESCRIPTOR[]; }
    CM_FULL_RESOURCE_DESCRIPTOR   { INTERFACE_TYPE InterfaceType; ULONG BusNumber;
                                    CM_PARTIAL_RESOURCE_LIST; }
    CM_PARTIAL_RESOURCE_LIST      { USHORT Version; USHORT Revision; ULONG Count;
                                    CM_PARTIAL_RESOURCE_DESCRIPTOR[]; }
    CM_PARTIAL_RESOURCE_DESCRIPTOR{ UCHAR Type; UCHAR ShareDisposition; USHORT Flags; union; }
                                  -> 20-byte stride observed and validated on this machine
    IO_RESOURCE_REQUIREMENTS_LIST { ULONG ListSize; INTERFACE_TYPE; ULONG BusNumber;
                                    ULONG SlotNumber; ULONG Reserved[3]; ULONG AlternativeLists;
                                    IO_RESOURCE_LIST[]; }
    IO_RESOURCE_LIST              { USHORT Version; USHORT Revision; ULONG Count;
                                    IO_RESOURCE_DESCRIPTOR[]; }
    IO_RESOURCE_DESCRIPTOR        { UCHAR Option; UCHAR Type; UCHAR ShareDisposition; UCHAR Spare1;
                                    USHORT Flags; USHORT Spare2; union; } -> 32-byte stride

*** THE ONE FIELD THAT NEEDS A RULE, AND THE PROOF FOR IT ***
    For Type 7 (`CmResourceTypeMemoryLarge`) the descriptor's length field holds
    length / 256, not the length in bytes.  Evidence, all from this machine:

      * RTX 4050 BAR1 is 8 GiB = 0x200000000 (33 bits).  Its BootConfig entry reads
        0x2000000.  A plain 32-bit *byte* field would have wrapped 0x200000000 to 0,
        so the field cannot be plain bytes; 0x2000000 == 0x200000000 / 256 exactly.
      * GPP0's prefetchable window: field 0x2020000 -> 0x202000000 = 8 GiB + 32 MiB, which
        is exactly the length reported independently by 1401's capture (8623489024).
      * GP11's prefetchable window: field 0x10000000 -> 0x1000000000 = 64 GiB, likewise
        matching the independent capture.
      * Control case with the SAME numeric value: the RTX 4050's BAR3 (Type 3, plain bytes)
        also reads 0x2000000 and really is 32 MiB.  So the field means 32 MiB for Type 3
        and 8 GiB for Type 7 - the scaling is type-specific, not a misread.

    Types 1 (Port/IO) and 3 (Memory) are plain bytes and were validated against known
    BAR sizes.

READ-ONLY: parses a text dump of registry values.  No API that modifies, adds or deletes a
resource configuration is touched anywhere in this pipeline.
"""
import json
import os
import re
import sys

MEMLARGE_SCALE = 256

TYPES = {0: "Null", 1: "Port/IO", 2: "Interrupt", 3: "Memory", 4: "DMA",
         5: "DeviceSpecific", 6: "BusNumber", 7: "MemoryLarge", 8: "ConfigData",
         129: "DevicePrivate"}
FLAG_BITS = [(0x0001, "READABLE"), (0x0002, "WRITABLE"), (0x0004, "PREFETCHABLE"),
             (0x0008, "SHARED"), (0x0010, "ALIAS"), (0x0020, "CACHEABLE"),
             (0x0040, "ALIGN32"), (0x0080, "ALIGN64"), (0x0200, "FLAG200")]


def u8(b, o):
    return b[o]


def u16(b, o):
    return int.from_bytes(b[o:o + 2], "little")


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def u64(b, o):
    return int.from_bytes(b[o:o + 8], "little")


def flags_str(f):
    return "|".join(n for bit, n in FLAG_BITS if f & bit) or "-"


def parse_dump(path):
    """registry dump text -> [(instance_id, {valueName: (kind, bytes)})]"""
    out = []
    cur = None
    pend = None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^===DEVICE (\S+)", line)
        if m:
            cur = (m.group(1), {})
            out.append(cur)
            pend = None
            continue
        m = re.match(r"^VAL (\w+) kind=(\d+) len=(\d+)", line)
        if m and cur:
            pend = m.group(1)
            cur[1][pend] = [int(m.group(2)), None]
            continue
        m = re.match(r"^HEX ([0-9a-f]*)", line)
        if m and cur and pend:
            cur[1][pend][1] = bytes.fromhex(m.group(1))
            pend = None
    return [(i, {k: (v[0], v[1]) for k, v in d.items()}) for i, d in out]


def decode_boot_config(b):
    """CM_RESOURCE_LIST -> (list of full descriptors, bytes_used, total)"""
    out = []
    off = 4
    for _ in range(u32(b, 0)):
        iface, bus = u32(b, off), u32(b, off + 4)
        ver, rev, n = u16(b, off + 8), u16(b, off + 10), u32(b, off + 12)
        off += 16
        entries = []
        for _ in range(n):
            t, share, f = u8(b, off), u8(b, off + 1), u16(b, off + 2)
            u = b[off + 4:off + 20]
            e = {"type": t, "type_name": TYPES.get(t, "?"), "flags": f,
                 "flags_str": flags_str(f)}
            if t in (1, 3, 7):
                e["start"] = u64(u, 0)
                raw_len = u32(u, 8)
                e["length"] = raw_len * (MEMLARGE_SCALE if t == 7 else 1)
                e["raw_length_field"] = raw_len
                e["scaled"] = t == 7
                e["end"] = e["start"] + e["length"] - 1 if e["length"] else None
            elif t == 2:
                e["vector"] = u32(u, 4)
            elif t == 6:
                e["bus_start"] = u32(u, 0)
                e["bus_length"] = u32(u, 4)
            entries.append(e)
            off += 20
        out.append({"interface_type": iface, "bus_number": bus, "version": ver,
                    "revision": rev, "count": n, "entries": entries})
    return out, off, len(b)


def decode_requirements(b):
    """IO_RESOURCE_REQUIREMENTS_LIST -> (dict, bytes_used, total)"""
    head = {"list_size": u32(b, 0), "interface_type": u32(b, 4), "bus_number": u32(b, 8),
            "slot_number": u32(b, 12), "reserved": [u32(b, 16 + 4 * i) for i in range(3)],
            "alternative_lists": u32(b, 28)}
    off = 32
    lists = []
    for _ in range(head["alternative_lists"]):
        ver, rev, n = u16(b, off), u16(b, off + 2), u32(b, off + 4)
        off += 8
        entries = []
        for _ in range(n):
            opt, t = u8(b, off), u8(b, off + 1)
            f = u16(b, off + 4)
            u = b[off + 8:off + 32]
            e = {"option": opt, "type": t, "type_name": TYPES.get(t, "?"), "flags": f,
                 "flags_str": flags_str(f)}
            if t in (1, 3, 7):
                e["range_min"] = u64(u, 8)
                e["range_max"] = u64(u, 16)
                raw_len = u32(u, 0)
                e["required_length"] = raw_len * (MEMLARGE_SCALE if t == 7 else 1)
                e["raw_length_field"] = raw_len
                e["scaled"] = t == 7
                e["alignment"] = u32(u, 4)
                e["range_span"] = e["range_max"] - e["range_min"] + 1
                e["free_placement"] = e["range_span"] > e["required_length"]
            elif t == 2:
                e["min_vector"] = u32(u, 0)
                e["max_vector"] = u32(u, 4)
            elif t == 6:
                e["min_bus"] = u32(u, 0)
                e["max_bus"] = u32(u, 4)
            elif t == 129:
                e["private_data"] = [u32(u, 0), u32(u, 4), u32(u, 8)]
            entries.append(e)
            off += 32
        lists.append({"version": ver, "revision": rev, "count": n, "entries": entries})
    head["lists"] = lists
    return head, off, len(b)


def bdf_map(xml_path):
    raw = open(xml_path, encoding="utf-8").read()
    out = {}
    for iid, body in re.findall(r'<Device InstanceId="(.*?)">(.*?)</Device>', raw, re.S):
        bus = re.search(r'DEVPKEY_Device_BusNumber" Type="UINT32">\s*<Value>0x([0-9A-Fa-f]+)</Value>', body)
        addr = re.search(r'DEVPKEY_Device_Address" Type="UINT32">\s*<Value>0x([0-9A-Fa-f]+)</Value>', body)
        desc = re.search(r"<DeviceDescription>(.*?)</DeviceDescription>", body, re.S)
        acpi = re.search(r"<Value>(ACPI\(.*?)</Value>", body)
        if bus and addr:
            b = int(bus.group(1), 16)
            a = int(addr.group(1), 16)
            out[iid.replace("&amp;", "&")] = {
                "bdf": "%02X:%02X.%X" % (b, (a >> 16) & 0xFFFF, a & 0xFFFF),
                "desc": (desc.group(1).strip() if desc else "?"),
                "acpi_path": (acpi.group(1) if acpi else None),
            }
    return out


def hx(x):
    return "0x%X" % x


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("registry_dump")
    ap.add_argument("pnputil_xml")
    ap.add_argument("--cfgmgr", default=None, help="1401 plan.json, for cross-check")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    xml = bdf_map(args.pnputil_xml)
    plan = {}
    if args.cfgmgr:
        raw = json.load(open(args.cfgmgr, encoding="utf-8"))
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

        walk(raw)
        for r in recs:
            nums = [int(x) for x in re.findall(r"\d+", (r.get("location") or "").replace("0x", ""))][:3]
            if len(nums) != 3:
                continue
            plan["%02X:%02X.%X" % tuple(nums)] = [
                [hx(int(a["base"], 16)), hx(int(a["end"], 16)), a.get("type")]
                for a in (r.get("allocated") or [])
                if a.get("type") in ("memory", "memory_large") and a.get("base")
            ]

    devices = []
    busnumber = []
    for iid, vals in parse_dump(args.registry_dump):
        # the registry key is <device>\<instance>; the PnP instance id is PCI\<device>\<instance>
        meta = xml.get("PCI\\" + iid) or xml.get(iid)
        if not meta:
            continue
        rec = {"bdf": meta["bdf"], "desc": meta["desc"], "acpi_path": meta["acpi_path"],
               "boot_config": None, "requirements": None, "plan_windows": None}
        if "BootConfig" in vals:
            kind, b = vals["BootConfig"]
            if kind == 8 and b:
                fulls, used, total = decode_boot_config(b)
                rec["boot_config"] = {"bytes_used": used, "bytes_total": total,
                                      "self_consistent": used == total, "fulls": fulls}
                for f in fulls:
                    for e in f["entries"]:
                        if e["type"] == 6:
                            busnumber.append({"bdf": meta["bdf"], "where": "BootConfig", "entry": e})
        if "BasicConfigVector" in vals:
            kind, b = vals["BasicConfigVector"]
            if kind == 10 and b:
                head, used, total = decode_requirements(b)
                rec["requirements"] = {"bytes_used": used, "bytes_total": total,
                                       "self_consistent": used == total, **head}
                for l in head["lists"]:
                    for e in l["entries"]:
                        if e["type"] == 6:
                            busnumber.append({"bdf": meta["bdf"], "where": "Requirements", "entry": e})
        rec["plan_windows"] = plan.get(meta["bdf"])
        devices.append(rec)

    devices.sort(key=lambda r: r["bdf"])
    result = {
        "source": "HKLM\\SYSTEM\\CurrentControlSet\\Enum\\PCI\\<dev>\\<inst>\\LogConf",
        "values": {"BootConfig": "REG_RESOURCE_LIST (firmware hand-over)",
                   "BasicConfigVector": "REG_RESOURCE_REQUIREMENTS_LIST (range + required length)"},
        "memory_large_scale": MEMLARGE_SCALE,
        "memory_large_scale_note": "Type 7 length field = length/256. Proof in the module docstring; "
                                  "control case: the RTX 4050's Type 3 BAR3 and Type 7 BAR1 both read "
                                  "0x2000000 while really being 32 MiB and 8 GiB respectively.",
        "device_count": len(devices),
        "busnumber_descriptors_found": len(busnumber),
        "busnumber_descriptors": busnumber,
        "devices": devices,
    }

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


def render(r):
    L = ["# Registry LogConf audit - the complete firmware resource descriptors (read-only)", "",
         "Source: `%s`" % r["source"], "",
         "* `BootConfig` = %s" % r["values"]["BootConfig"],
         "* `BasicConfigVector` = %s" % r["values"]["BasicConfigVector"],
         "* **MemoryLarge (Type 7) length is `length / %d`.** %s" % (
             r["memory_large_scale"], r["memory_large_scale_note"]),
         "* **BusNumber descriptors found anywhere: %d**" % r["busnumber_descriptors_found"], ""]
    L.append("## Per-device")
    for d in r["devices"]:
        L.append("")
        L.append("### %s  %s" % (d["bdf"], d["desc"]))
        L.append("* ACPI: `%s`" % d["acpi_path"])
        bc = d["boot_config"]
        if bc:
            L.append("* BootConfig (firmware hand-over), self-consistent=%s:" % bc["self_consistent"])
            for f in bc["fulls"]:
                L.append("  * iface=%d ownBus=%d count=%d" % (f["interface_type"], f["bus_number"], f["count"]))
                for e in f["entries"]:
                    if "start" in e:
                        L.append("    * %-12s %s-%s len=%s%s flags=%s(%s)" % (
                            e["type_name"], hx(e["start"]), hx(e["end"]), hx(e["length"]),
                            " [raw field %s x%d]" % (hx(e["raw_length_field"]), MEMLARGE_SCALE) if e["scaled"] else "",
                            hex(e["flags"]), e["flags_str"]))
                    elif e["type"] == 6:
                        L.append("    * BUSNUMBER start=%s len=%s" % (hx(e["bus_start"]), hx(e["bus_length"])))
                    else:
                        L.append("    * %-12s %s" % (e["type_name"], {k: v for k, v in e.items()
                                                                     if k not in ("type", "type_name", "flags", "flags_str")}))
        rq = d["requirements"]
        if rq:
            L.append("* Requirements, self-consistent=%s, slot=%d:" % (rq["self_consistent"], rq["slot_number"]))
            for l in rq["lists"]:
                for e in l["entries"]:
                    if "range_min" in e:
                        L.append("    * %-12s RANGE %s-%s span=%s REQUIRED %s%s align=%s free_placement=%s flags=%s(%s)" % (
                            e["type_name"], hx(e["range_min"]), hx(e["range_max"]), hx(e["range_span"]),
                            hx(e["required_length"]),
                            " [raw field %s x%d]" % (hx(e["raw_length_field"]), MEMLARGE_SCALE) if e["scaled"] else "",
                            hx(e["alignment"]), e["free_placement"], hex(e["flags"]), e["flags_str"]))
                    elif e["type"] == 6:
                        L.append("    * BUSNUMBER min=%s max=%s" % (hx(e["min_bus"]), hx(e["max_bus"])))
                    elif e["type"] == 2:
                        L.append("    * Interrupt   vector %s..%s" % (hx(e["min_vector"]), hx(e["max_vector"])))
                    else:
                        L.append("    * %-12s %s" % (e["type_name"], {k: v for k, v in e.items()
                                                                     if k not in ("type", "type_name", "flags", "flags_str")}))
        if d["plan_windows"]:
            L.append("* 1401 capture (independent): %s" % ", ".join(
                "%s-%s(%s)" % tuple(w) for w in d["plan_windows"]))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
