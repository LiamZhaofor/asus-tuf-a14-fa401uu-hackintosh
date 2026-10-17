#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decode the Windows registry logical-configuration blobs (read-only) for PCI functions.

WHY
    `pnputil /resources` drops large windows, and the CfgMgr32 descriptor walk needs a
    correctly declared 5-argument CM_Get_Next_Res_Des.  A third, fully read-only Windows
    source carries the complete descriptor sets:

        HKLM\\SYSTEM\\CurrentControlSet\\Enum\\PCI\\<device>\\<instance>\\LogConf
            BootConfig          REG_RESOURCE_LIST                (what the FIRMWARE handed over)
            BasicConfigVector   REG_RESOURCE_REQUIREMENTS_LIST   (min/max RANGE + required LENGTH)

    .NET's RegistryValueKind cannot materialise either type (both read back as
    `Unknown`/null), so they must be read with RegQueryValueEx - see audit/dump-logconf.ps1.

LAYOUTS (Windows SDK)
    CM_RESOURCE_LIST               { ULONG Count; CM_FULL_RESOURCE_DESCRIPTOR[]; }
    CM_FULL_RESOURCE_DESCRIPTOR    { INTERFACE_TYPE InterfaceType; ULONG BusNumber;
                                     CM_PARTIAL_RESOURCE_LIST; }
    CM_PARTIAL_RESOURCE_LIST       { USHORT Version; USHORT Revision; ULONG Count;
                                     CM_PARTIAL_RESOURCE_DESCRIPTOR[]; }
    CM_PARTIAL_RESOURCE_DESCRIPTOR { UCHAR Type; UCHAR ShareDisposition; USHORT Flags; union; }
                                   -> 20-byte stride on this machine
    IO_RESOURCE_REQUIREMENTS_LIST  { ULONG ListSize; INTERFACE_TYPE; ULONG BusNumber;
                                     ULONG SlotNumber; ULONG Reserved[3]; ULONG AlternativeLists;
                                     IO_RESOURCE_LIST[]; }
    IO_RESOURCE_LIST               { USHORT Version; USHORT Revision; ULONG Count;
                                     IO_RESOURCE_DESCRIPTOR[]; }
    IO_RESOURCE_DESCRIPTOR         { UCHAR Option; UCHAR Type; UCHAR ShareDisposition;
                                     UCHAR Spare1; USHORT Flags; USHORT Spare2; union; }
                                   -> 32-byte stride

*** LARGE-MEMORY LENGTHS: THE 40/48/64 RULE ***
    A memory descriptor may need a length that does not fit the 32-bit `Length` field.  The
    `Flags` word then says HOW the field is encoded (wdm.h):

        CM_RESOURCE_MEMORY_LARGE_40 = 0x0200  -> the field holds length >> 8   (40-bit length)
        CM_RESOURCE_MEMORY_LARGE_48 = 0x0400  -> the field holds length >> 16  (48-bit length)
        CM_RESOURCE_MEMORY_LARGE_64 = 0x0800  -> the field holds length >> 32  (64-bit length)

    So the reconstruction is `length = raw << shift(flags)`, with the shift chosen by which
    bit is present - never a hard-coded 256.  The same convention applies to the `Alignment`
    field of a requirement descriptor (Length40/Alignment40 etc.).

    Cross-checks (all three use flags 0x0244, i.e. LARGE_40, so shift 8):
      * RTX 4050 BAR1: raw 0x2000000 -> 0x200000000 = 8 GiB, matching the independent capture,
        nvidia-smi's 8192 MiB and OpenCore's RBAR size index 13.
      * GPP0 prefetchable: raw 0x2020000 -> 0x202000000 = 8 GiB + 32 MiB.
      * GP11 prefetchable: raw 0x10000000 -> 0x1000000000 = 64 GiB.
      * CONTROL: the same device's Type 3 BAR3 has the same numeric field 0x2000000 and really
        is 32 MiB, so the scaling is flag/type dependent.
    If a Type 7 descriptor carries NONE of the three bits, the length is NOT guessed: it is
    reported as `ambiguous` and no conclusion may rest on it.

*** TRAILING DESCRIPTORS ***
    For some functions the requirement lists consume fewer bytes than `ListSize`.  The
    remainder is an extra descriptor (observed on this machine: an interrupt requirement with
    MinVector=0 / MaxVector=0xFFFFFFFF) that its list's `Count` does not include.  This decoder
    consumes it, attaches it to the last alternative list with `trailing = true`, and reports
    `self_consistent` only when every byte is accounted for.  A buffer that is not fully
    consumed, or a read that would run past the end, is reported - never silently accepted,
    and never used as the basis of a conclusion.

READ-ONLY: parses a text dump of registry values.  No API that modifies, adds or deletes a
resource configuration is touched anywhere in this pipeline.

USAGE
    python pci-logconf-audit.py <registry-dump.txt> <pnputil-all.xml> [--cfgmgr plan.json]
                                [--out PREFIX]
    python pci-logconf-audit.py --selftest
"""
import argparse
import json
import os
import re
import sys

# ---- large-memory encoding (wdm.h) ---------------------------------------
MEM_LARGE_40 = 0x0200
MEM_LARGE_48 = 0x0400
MEM_LARGE_64 = 0x0800
LARGE_BITS = ((MEM_LARGE_64, 32), (MEM_LARGE_48, 16), (MEM_LARGE_40, 8))

# ---- CM_RESOURCE_TYPE (the `Type` byte inside a descriptor) --------------
TYPES = {0: "Null", 1: "Port/IO", 2: "Interrupt", 3: "Memory", 4: "DMA",
         5: "DeviceSpecific", 6: "BusNumber", 7: "MemoryLarge", 8: "ConfigData",
         129: "DevicePrivate"}
FLAG_BITS = [(0x0001, "READABLE"), (0x0002, "WRITABLE"), (0x0004, "PREFETCHABLE"),
             (0x0008, "SHARED"), (0x0010, "ALIAS"), (0x0020, "CACHEABLE"),
             (0x0040, "ALIGN32"), (0x0080, "ALIGN64"),
             (0x0200, "LARGE40"), (0x0400, "LARGE48"), (0x0800, "LARGE64")]


class DecodeError(Exception):
    pass


def u8(b, o):
    if o + 1 > len(b):
        raise DecodeError("read past end at %d (len %d)" % (o, len(b)))
    return b[o]


def u16(b, o):
    if o + 2 > len(b):
        raise DecodeError("read past end at %d (len %d)" % (o, len(b)))
    return int.from_bytes(b[o:o + 2], "little")


def u32(b, o):
    if o + 4 > len(b):
        raise DecodeError("read past end at %d (len %d)" % (o, len(b)))
    return int.from_bytes(b[o:o + 4], "little")


def u64(b, o):
    if o + 8 > len(b):
        raise DecodeError("read past end at %d (len %d)" % (o, len(b)))
    return int.from_bytes(b[o:o + 8], "little")


def flags_str(f):
    return "|".join(n for bit, n in FLAG_BITS if f & bit) or "-"


def large_shift(flags):
    """Shift implied by the LARGE40/48/64 bits, or None when none is set."""
    for bit, shift in LARGE_BITS:
        if flags & bit:
            return shift
    return None


def scaled_length(raw, flags, is_type7):
    """-> (value, shift, ambiguous)"""
    if not is_type7:
        return raw, 0, False
    shift = large_shift(flags)
    if shift is None:
        return None, None, True      # never guess
    return raw << shift, shift, False


# --------------------------------------------------------------------------
# CM_RESOURCE_LIST  (BootConfig)
# --------------------------------------------------------------------------
BOOT_HDR = 16
BOOT_DESC = 20


def decode_boot_config(b):
    """-> (fulls, bytes_used, total, problems)"""
    if len(b) < 4:
        raise DecodeError("buffer shorter than the Count field")
    problems = []
    fulls = []
    off = 4
    for _ in range(u32(b, 0)):
        iface = u32(b, off)
        bus = u32(b, off + 4)
        ver = u16(b, off + 8)
        rev = u16(b, off + 10)
        n = u32(b, off + 12)
        off += BOOT_HDR
        entries = []
        for _ in range(n):
            t = u8(b, off)
            f = u16(b, off + 2)
            u = b[off + 4:off + BOOT_DESC]
            if len(u) < 16:
                raise DecodeError("descriptor at %d runs past end" % off)
            e = {"type": t, "type_name": TYPES.get(t, "?"), "flags": f, "flags_str": flags_str(f)}
            if t in (1, 3, 7):
                e["start"] = u64(u, 0)
                raw = u32(u, 8)
                e["raw_length_field"] = raw
                length, shift, ambiguous = scaled_length(raw, f, t == 7)
                e["length"] = length
                e["length_shift"] = shift
                e["ambiguous_length"] = ambiguous
                e["end"] = e["start"] + length - 1 if length else None
            elif t == 2:
                e["vector"] = u32(u, 4)
            elif t == 6:
                e["bus_start"] = u32(u, 0)
                e["bus_length"] = u32(u, 4)
                e["bus_end"] = e["bus_start"] + e["bus_length"] - 1 if e["bus_length"] else None
            entries.append(e)
            off += BOOT_DESC
        fulls.append({"interface_type": iface, "bus_number": bus, "version": ver,
                      "revision": rev, "count": n, "entries": entries})
    if off != len(b):
        problems.append("consumed %d of %d bytes" % (off, len(b)))
    return fulls, off, len(b), problems


# --------------------------------------------------------------------------
# IO_RESOURCE_REQUIREMENTS_LIST  (BasicConfigVector)
# --------------------------------------------------------------------------
REQ_HDR = 32
REQ_LIST_HDR = 8
REQ_DESC = 32


def _decode_req_entry(b, off):
    opt = u8(b, off)
    t = u8(b, off + 1)
    share = u8(b, off + 2)
    f = u16(b, off + 4)
    u = b[off + 8:off + REQ_DESC]
    if len(u) < 24:
        raise DecodeError("requirement descriptor at %d runs past end" % off)
    e = {"option": opt, "type": t, "type_name": TYPES.get(t, "?"), "share": share,
         "flags": f, "flags_str": flags_str(f)}
    if t in (1, 3, 7):
        raw_len = u32(u, 0)
        raw_align = u32(u, 4)
        e["raw_length_field"] = raw_len
        e["raw_alignment_field"] = raw_align
        length, shift, ambiguous = scaled_length(raw_len, f, t == 7)
        align, ashift, aambiguous = scaled_length(raw_align, f, t == 7)
        e["required_length"] = length
        e["alignment"] = align
        e["length_shift"] = shift
        e["alignment_shift"] = ashift
        e["ambiguous"] = bool(ambiguous or aambiguous)
        e["range_min"] = u64(u, 8)
        e["range_max"] = u64(u, 16)
        e["range_span"] = e["range_max"] - e["range_min"] + 1
        e["free_placement"] = (e["range_span"] > length) if length else None
    elif t == 2:
        e["min_vector"] = u32(u, 0)
        e["max_vector"] = u32(u, 4)
    elif t == 6:
        e["min_bus"] = u32(u, 0)
        e["max_bus"] = u32(u, 4)
        e["bus_count"] = e["max_bus"] - e["min_bus"] + 1
    elif t == 129:
        e["private_data"] = [u32(u, 0), u32(u, 4), u32(u, 8)]
    return e


def decode_requirements(b):
    """-> (head, bytes_used, total, problems)"""
    head = {"list_size": u32(b, 0), "interface_type": u32(b, 4), "bus_number": u32(b, 8),
            "slot_number": u32(b, 12), "reserved": [u32(b, 16 + 4 * i) for i in range(3)],
            "alternative_lists": u32(b, 28)}
    problems = []
    if head["list_size"] != len(b):
        problems.append("ListSize=%d but the value is %d bytes" % (head["list_size"], len(b)))
    off = REQ_HDR
    lists = []
    for li in range(head["alternative_lists"]):
        if off + REQ_LIST_HDR > len(b):
            problems.append("alternative list %d header past end" % li)
            break
        ver = u16(b, off)
        rev = u16(b, off + 2)
        n = u32(b, off + 4)
        off += REQ_LIST_HDR
        entries = []
        for _ in range(n):
            entries.append(_decode_req_entry(b, off))
            off += REQ_DESC
        lists.append({"version": ver, "revision": rev, "count": n, "entries": entries,
                      "trailing_descriptors": 0})

    # ---- trailing descriptors: consume the whole remainder, only in 32-byte units
    trailing = 0
    while off + REQ_DESC <= len(b):
        e = _decode_req_entry(b, off)
        e["trailing"] = True
        if lists:
            lists[-1]["entries"].append(e)
            lists[-1]["trailing_descriptors"] += 1
        else:
            lists.append({"version": 0, "revision": 0, "count": 0, "entries": [e],
                          "trailing_descriptors": 1})
        trailing += 1
        off += REQ_DESC
    if trailing:
        problems.append("%d trailing descriptor(s) beyond the declared Count" % trailing)
    if off != len(b):
        problems.append("consumed %d of %d bytes (%d left over)" % (off, len(b), len(b) - off))

    head["lists"] = lists
    head["trailing_descriptors"] = trailing
    head["bytes_used"] = off
    head["bytes_total"] = len(b)
    head["self_consistent"] = off == len(b)
    return head, off, len(b), problems


# --------------------------------------------------------------------------
def bdf_map(xml_path):
    raw = open(xml_path, encoding="utf-8").read()
    out = {}
    for iid, body in re.findall(r'<Device InstanceId="(.*?)">(.*?)</Device>', raw, re.S):
        bus = re.search(r'DEVPKEY_Device_BusNumber" Type="UINT32">\s*<Value>0x([0-9A-Fa-f]+)</Value>', body)
        addr = re.search(r'DEVPKEY_Device_Address" Type="UINT32">\s*<Value>0x([0-9A-Fa-f]+)</Value>', body)
        desc = re.search(r"<DeviceDescription>(.*?)</DeviceDescription>", body, re.S)
        acpi = re.search(r"<Value>(ACPI\(.*?)</Value>", body)
        if bus and addr:
            bb = int(bus.group(1), 16)
            a = int(addr.group(1), 16)
            out[iid.replace("&amp;", "&")] = {
                "bdf": "%02X:%02X.%X" % (bb, (a >> 16) & 0xFFFF, a & 0xFFFF),
                "desc": (desc.group(1).strip() if desc else "?"),
                "acpi_path": (acpi.group(1) if acpi else None),
            }
    return out


def hx(x):
    return "0x%X" % x


# --------------------------------------------------------------------------
# self-tests: crafted buffers only, no machine data
# --------------------------------------------------------------------------
def _cm_list(entries, iface=5, bus=0):
    """Build a CM_RESOURCE_LIST. entries = [(type, flags, union16bytes)]"""
    b = bytearray()
    b += (1).to_bytes(4, "little")
    b += iface.to_bytes(4, "little") + bus.to_bytes(4, "little")
    b += (1).to_bytes(2, "little") + (1).to_bytes(2, "little") + len(entries).to_bytes(4, "little")
    for t, fl, un in entries:
        b += bytes([t, 1]) + fl.to_bytes(2, "little") + un
    return bytes(b)


def _mem_union(start, raw_len):
    return start.to_bytes(8, "little") + raw_len.to_bytes(4, "little") + b"\0\0\0\0"


def _reqs(lists, iface=5, bus=0, slot=0, alts=None):
    """Build an IO_RESOURCE_REQUIREMENTS_LIST. lists = [[(type, flags, union24), ...], ...]"""
    body = bytearray()
    for entries in lists:
        body += (1).to_bytes(2, "little") + (1).to_bytes(2, "little") + len(entries).to_bytes(4, "little")
        for t, fl, un in entries:
            body += bytes([1, t, 1, 0]) + fl.to_bytes(2, "little") + (0).to_bytes(2, "little") + un
    n = alts if alts is not None else len(lists)
    total = REQ_HDR + len(body)
    head = (total.to_bytes(4, "little") + iface.to_bytes(4, "little") + bus.to_bytes(4, "little")
            + slot.to_bytes(4, "little") + (0).to_bytes(4, "little") * 3 + n.to_bytes(4, "little"))
    return head + bytes(body)


def _req_mem_union(length, align, mn, mx):
    return (length.to_bytes(4, "little") + align.to_bytes(4, "little")
            + mn.to_bytes(8, "little") + mx.to_bytes(8, "little"))


def selftest():
    fails = []

    def check(name, cond, detail=""):
        if cond:
            print("  OK   " + name)
        else:
            fails.append(name + " " + detail)
            print("  FAIL " + name + " " + detail)

    print("selftest: LARGE40/48/64 scaling (BootConfig, Type 7)")
    for bit, shift in ((MEM_LARGE_40, 8), (MEM_LARGE_48, 16), (MEM_LARGE_64, 32)):
        raw = 0x200000000 >> shift
        buf = _cm_list([(7, bit | 0x0044, _mem_union(0x7C00000000, raw))])
        fulls, used, total, _ = decode_boot_config(buf)
        e = fulls[0]["entries"][0]
        check("0x%04X (shift %d) -> 8 GiB" % (bit, shift),
              e["length"] == 0x200000000 and e["length_shift"] == shift and used == total,
              str(e.get("length")))

    print("selftest: Type 7 with no LARGE bit is ambiguous, never guessed")
    buf = _cm_list([(7, 0x0044, _mem_union(0x7C00000000, 0x2000000))])
    fulls, _, _, _ = decode_boot_config(buf)
    e = fulls[0]["entries"][0]
    check("ambiguous flagged", e["ambiguous_length"] is True and e["length"] is None, str(e))

    print("selftest: Type 3 length is plain bytes even with the same numeric field")
    buf = _cm_list([(3, 0x0084, _mem_union(0x7E00000000, 0x2000000))])
    fulls, _, _, _ = decode_boot_config(buf)
    e = fulls[0]["entries"][0]
    check("Type 3 = 32 MiB", e["length"] == 0x2000000 and e["length_shift"] == 0, str(e["length"]))

    print("selftest: bus-number descriptor")
    buf = _cm_list([(6, 0, (0).to_bytes(4, "little") + (0x100).to_bytes(4, "little") + b"\0" * 8)])
    fulls, _, _, _ = decode_boot_config(buf)
    e = fulls[0]["entries"][0]
    check("bus 0x00-0xFF", e["bus_start"] == 0 and e["bus_end"] == 0xFF, str(e))

    print("selftest: requirements with a trailing descriptor (the 5/25 case)")
    body = _reqs([[(3, 0x0040, _req_mem_union(0x18000000, 1, 0xC4000000, 0xDBFFFFFF))]])
    extra = (bytes([1, 2, 1, 0]) + (0x0007).to_bytes(2, "little") + (0).to_bytes(2, "little")
             + (0xFFFFFFFE).to_bytes(4, "little") + (0xFFFFFFFE).to_bytes(4, "little")
             + (0).to_bytes(16, "little"))
    body = (len(body) + REQ_DESC).to_bytes(4, "little") + body[4:] + extra
    head, used, total, probs = decode_requirements(body)
    check("trailing consumed, every byte accounted",
          head["trailing_descriptors"] == 1 and head["self_consistent"] and used == total,
          str((head["trailing_descriptors"], head["self_consistent"], used, total)))
    check("trailing descriptor is the interrupt requirement",
          head["lists"][-1]["entries"][-1]["type"] == 2,
          str(head["lists"][-1]["entries"][-1].get("type")))

    print("selftest: truncated buffer fails closed (raises, is not silently accepted)")
    body = _reqs([[(3, 0x0040, _req_mem_union(0x1000, 1, 0x1000, 0x1FFF))]])
    raised = False
    try:
        decode_requirements(body[:-5])
    except DecodeError:
        raised = True
    check("decoder raises DecodeError on truncation", raised)
    # and the caller records it per-device instead of dying: simulate one good + one bad blob
    good_ok = True
    try:
        decode_requirements(body)
    except DecodeError:
        good_ok = False
    check("intact buffer still decodes", good_ok)

    print("selftest: LARGE40 also scales the alignment field")
    body = _reqs([[(7, MEM_LARGE_40 | 0x0044,
                    _req_mem_union(0x10000000, 1, 0x6C00000000, 0x7BFFFFFFFF))]])
    head, _, _, _ = decode_requirements(body)
    e = head["lists"][0]["entries"][0]
    check("length 64 GiB, alignment 256",
          e["required_length"] == 0x1000000000 and e["alignment"] == 256,
          str((e["required_length"], e["alignment"])))

    print("selftest: BusNumber requirement (the GP11 0x05-0x64 shape)")
    body = _reqs([[(6, 0, (0x05).to_bytes(4, "little") + (0x64).to_bytes(4, "little") + b"\0" * 16)]])
    head, _, _, _ = decode_requirements(body)
    e = head["lists"][0]["entries"][0]
    check("min 5 max 0x64 = 96 buses", e["min_bus"] == 5 and e["max_bus"] == 0x64
          and e["bus_count"] == 96, str(e))

    print()
    if fails:
        print("SELFTEST FAILURES: %d" % len(fails))
        for f in fails:
            print("   - " + f)
        return 1
    print("selftest: all checks passed")
    return 0


# --------------------------------------------------------------------------
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("registry_dump", nargs="?")
    ap.add_argument("pnputil_xml", nargs="?")
    ap.add_argument("--cfgmgr", default=None, help="1401 plan.json, for cross-check")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.registry_dump or not args.pnputil_xml:
        ap.error("registry_dump and pnputil_xml are required (or use --selftest)")

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
            nums = [int(x) for x in re.findall(r"\d+", (r.get("location") or "").replace("0x", ""))[:3]]
            if len(nums) != 3:
                continue
            plan["%02X:%02X.%X" % tuple(nums)] = [
                [hx(int(a["base"], 16)), hx(int(a["end"], 16)), a.get("type")]
                for a in (r.get("allocated") or [])
                if a.get("type") in ("memory", "memory_large") and a.get("base")
            ]

    devices, busnumber, problems = [], [], []
    for iid, vals in parse_dump(args.registry_dump):
        meta = xml.get("PCI\\" + iid) or xml.get(iid)
        if not meta:
            continue
        rec = {"bdf": meta["bdf"], "desc": meta["desc"], "acpi_path": meta["acpi_path"],
               "boot_config": None, "requirements": None, "plan_windows": None}
        if "BootConfig" in vals:
            kind, b = vals["BootConfig"]
            if kind == 8 and b:
                try:
                    fulls, used, total, probs = decode_boot_config(b)
                    rec["boot_config"] = {"bytes_used": used, "bytes_total": total,
                                          "self_consistent": used == total, "fulls": fulls,
                                          "problems": probs}
                    for p in probs:
                        problems.append((meta["bdf"], "BootConfig", p))
                    for f in fulls:
                        for e in f["entries"]:
                            if e["type"] == 6:
                                busnumber.append({"bdf": meta["bdf"], "where": "BootConfig", "entry": e})
                except DecodeError as ex:
                    problems.append((meta["bdf"], "BootConfig", "DECODE ERROR: %s" % ex))
        if "BasicConfigVector" in vals:
            kind, b = vals["BasicConfigVector"]
            if kind == 10 and b:
                try:
                    head, used, total, probs = decode_requirements(b)
                    rec["requirements"] = head
                    for p in probs:
                        problems.append((meta["bdf"], "Requirements", p))
                    for l in head["lists"]:
                        for e in l["entries"]:
                            if e["type"] == 6:
                                busnumber.append({"bdf": meta["bdf"], "where": "Requirements", "entry": e})
                except DecodeError as ex:
                    problems.append((meta["bdf"], "Requirements", "DECODE ERROR: %s" % ex))
        rec["plan_windows"] = plan.get(meta["bdf"])
        devices.append(rec)

    devices.sort(key=lambda r: r["bdf"])
    result = {
        "source": "HKLM\\SYSTEM\\CurrentControlSet\\Enum\\PCI\\<dev>\\<inst>\\LogConf",
        "values": {"BootConfig": "REG_RESOURCE_LIST (firmware hand-over)",
                   "BasicConfigVector": "REG_RESOURCE_REQUIREMENTS_LIST (range + required length)"},
        "large_memory_rule": {
            "CM_RESOURCE_MEMORY_LARGE_40 (0x0200)": "length = raw << 8",
            "CM_RESOURCE_MEMORY_LARGE_48 (0x0400)": "length = raw << 16",
            "CM_RESOURCE_MEMORY_LARGE_64 (0x0800)": "length = raw << 32",
            "none set": "reported ambiguous; never guessed",
        },
        "device_count": len(devices),
        "busnumber_descriptors_found": len(busnumber),
        "busnumber_descriptors": busnumber,
        "fully_parsed": {
            "boot_config": sum(1 for d in devices if d["boot_config"] and d["boot_config"]["self_consistent"]),
            "boot_config_total": sum(1 for d in devices if d["boot_config"]),
            "requirements": sum(1 for d in devices if d["requirements"] and d["requirements"]["self_consistent"]),
            "requirements_total": sum(1 for d in devices if d["requirements"]),
        },
        "problems": [{"bdf": b, "value": v, "problem": p} for b, v, p in problems],
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
    return 0


def _fmt_entry(e):
    if "start" in e and e.get("end") is not None:
        s = "%-12s %s-%s len=%s" % (e["type_name"], hx(e["start"]), hx(e["end"]), hx(e["length"]))
        if e.get("length_shift"):
            s += " [raw %s << %d]" % (hx(e["raw_length_field"]), e["length_shift"])
        if e.get("ambiguous_length"):
            s += " ** AMBIGUOUS LENGTH (no LARGE40/48/64 bit) **"
        return s + " flags=%s(%s)" % (hex(e["flags"]), e["flags_str"])
    if "range_min" in e:
        s = "%-12s RANGE %s-%s span=%s REQUIRED %s align=%s" % (
            e["type_name"], hx(e["range_min"]), hx(e["range_max"]), hx(e["range_span"]),
            "AMBIGUOUS" if e.get("ambiguous") else hx(e["required_length"]),
            hx(e["alignment"]) if e.get("alignment") is not None else "?")
        if e.get("length_shift"):
            s += " [raw len %s << %d]" % (hx(e["raw_length_field"]), e["length_shift"])
        return s + " free_placement=%s flags=%s(%s)" % (e["free_placement"], hex(e["flags"]), e["flags_str"])
    if "max_bus" in e:
        return "%-12s BUS %s-%s (%d buses)" % (e["type_name"], hx(e["min_bus"]), hx(e["max_bus"]),
                                               e["bus_count"])
    if "min_vector" in e:
        return "%-12s vector %s..%s" % (e["type_name"], hx(e["min_vector"]), hx(e["max_vector"]))
    if "private_data" in e:
        return "%-12s data=%s" % (e["type_name"], [hx(x) for x in e["private_data"]])
    return "%-12s %s" % (e["type_name"], {k: v for k, v in e.items()
                                          if k not in ("type", "type_name", "flags", "flags_str")})


def render(r):
    L = ["# Registry LogConf audit - firmware resource descriptors (read-only)", "",
         "Source: `%s`" % r["source"], "",
         "* `BootConfig` = %s" % r["values"]["BootConfig"],
         "* `BasicConfigVector` = %s" % r["values"]["BasicConfigVector"],
         "* **Large-memory rule**: " + "; ".join("%s: %s" % kv for kv in r["large_memory_rule"].items()),
         "* **BusNumber descriptors found: %d**" % r["busnumber_descriptors_found"],
         "* **Fully parsed**: BootConfig %d/%d, Requirements %d/%d" % (
             r["fully_parsed"]["boot_config"], r["fully_parsed"]["boot_config_total"],
             r["fully_parsed"]["requirements"], r["fully_parsed"]["requirements_total"]),
         "* **Parser problems**: %d" % len(r["problems"]), ""]
    if r["problems"]:
        L.append("## Parser problems (no conclusion may rest on these values)")
        for p in r["problems"]:
            L.append("* `%s` %s: %s" % (p["bdf"], p["value"], p["problem"]))
        L.append("")
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
                    L.append("    * " + _fmt_entry(e))
        rq = d["requirements"]
        if rq:
            L.append("* Requirements, self-consistent=%s slot=%d alts=%d trailing=%d:" % (
                rq["self_consistent"], rq["slot_number"], rq["alternative_lists"],
                rq["trailing_descriptors"]))
            for l in rq["lists"]:
                L.append("  * list v=%d r=%d count=%d trailing=%d" % (
                    l["version"], l["revision"], l["count"], l["trailing_descriptors"]))
                for e in l["entries"]:
                    L.append("    * " + _fmt_entry(e))
        if d["plan_windows"]:
            L.append("* 1401 capture (independent): %s" % ", ".join("%s-%s(%s)" % tuple(w)
                                                                    for w in d["plan_windows"]))
    return "\n".join(L) + "\n"


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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
