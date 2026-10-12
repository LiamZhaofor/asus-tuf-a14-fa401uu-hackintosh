#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Redact identity values from an OpenCore boot log so it is safe to publish.

Usage:
    python scrub-log.py <in.txt> [out.txt]

The real values are read from the live stick config (D:\\EFI\\OC\\config.plist) so the
script itself contains no secrets, and it redacts BOTH forms of each value:

  * SMBIOS serial / MLB / UUID as written into NVRAM
  * the UUID **byte-swapped** - OpenCore prints system-id with the first three GUID
    fields in little-endian order, so a naive search for the config's UUID string
    misses it. That is exactly how one published log kept a real UUID.
  * the MAC from the ROM field, in colon form, dash form and packed hex
  * the NVMe disk serial, which appears as hex bytes inside NVMe(0x1,...) device paths

Placeholders match the convention already used by the published logs, so the redacted
file reads the same as its siblings. Idempotent: running it twice changes nothing the
second time. Exit status is 1 if any real value survives, so a silent miss cannot
publish.
"""
import os
import re
import sys

STICK = r"D:\EFI\OC\config.plist"

PLACEHOLDER = {
    "rom": "<rom-redacted>",
    "mlb": "<MLB-REDACTED>",
    "ssn": "<SMBIOS-SERIAL-REDACTED>",
    "uuid": "<UUID-REDACTED>",
    "disk": "<disk-serial-redacted>",
}


def read_identity():
    with open(STICK, "rb") as fh:
        text = fh.read().decode("utf-8", "replace")
    out = {}
    for key, name in (("SystemSerialNumber", "ssn"), ("MLB", "mlb"), ("SystemUUID", "uuid")):
        m = re.search(rf"<key>{key}</key>\s*<string>([^<]+)</string>", text)
        if m:
            out[name] = m.group(1).strip()
    m = re.search(r"<key>ROM</key>\s*<data>\s*([^<\s]+)\s*</data>", text)
    if m:
        import base64
        raw = base64.b64decode(m.group(1).strip())
        out["rom_hex"] = raw.hex().upper()
        out["rom_colon"] = ":".join(f"{b:02X}" for b in raw)
        out["rom_dash"] = "-".join(f"{b:02X}" for b in raw)
    return out


def swap_guid(u):
    """Apple/OpenCore little-endian rendering of the first three GUID fields."""
    h = u.replace("-", "")
    if len(h) != 32:
        return None
    d1, d2, d3, rest = h[0:8], h[8:12], h[12:16], h[16:32]
    return "-".join([
        "".join(reversed([d1[i:i+2] for i in range(0, 8, 2)])),
        "".join(reversed([d2[i:i+2] for i in range(0, 4, 2)])),
        "".join(reversed([d3[i:i+2] for i in range(0, 4, 2)])),
        rest[0:4], rest[4:16],
    ]).upper()


def main(argv):
    if not 1 <= len(argv) <= 2:
        print(__doc__)
        return 2
    src = argv[0]
    dst = argv[1] if len(argv) == 2 else src

    ident = read_identity()
    out = open(src, "r", encoding="utf-8", errors="replace").read()
    before = out

    # 1) the labelled lines OpenCore prints for NVRAM writes
    if "rom_colon" in ident:
        for v in {ident["rom_colon"], ident["rom_dash"], ident["rom_hex"]}:
            out = out.replace(v, PLACEHOLDER["rom"])
    if "mlb" in ident:
        out = out.replace(ident["mlb"], PLACEHOLDER["mlb"])
    if "ssn" in ident:
        out = out.replace(ident["ssn"], PLACEHOLDER["ssn"])
    if "uuid" in ident:
        for v in {ident["uuid"], ident["uuid"].upper(), swap_guid(ident["uuid"]) or ident["uuid"]}:
            out = out.replace(v, PLACEHOLDER["uuid"])

    # 2) disk serial inside NVMe device paths (hex bytes, dash separated)
    out = re.sub(r"(NVMe\(0x1,)([0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2})+)(\))",
                 lambda m: m.group(1) + PLACEHOLDER["disk"] + m.group(3), out)

    # 3) belt and braces: generic MAC renderings, wherever they appear
    out = re.sub(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", PLACEHOLDER["rom"], out)

    if src == dst:
        with open(dst, "w", encoding="utf-8", newline="") as fh:
            fh.write(out)
    else:
        with open(dst, "w", encoding="utf-8", newline="") as fh:
            fh.write(out)

    changed = sum(1 for a, b in zip(before.splitlines(), out.splitlines()) if a != b)
    print(f"{os.path.basename(src)}: {changed} line(s) redacted -> {dst}")

    # ------------------------------------------------------------------ verify
    leftovers = []
    for name, val in ident.items():
        if name in ("rom_hex", "rom_dash", "rom_colon"):
            continue
        if val and val in out:
            leftovers.append(name)
    if "uuid" in ident and (swap_guid(ident["uuid"]) or "") in out:
        leftovers.append("uuid(swapped)")
    # a truncated earlier scrub left the tail of the GUID behind: catch that too
    if "uuid" in ident:
        tail = ident["uuid"].replace("-", "").upper()[-12:]
        if tail in out:
            leftovers.append("uuid(tail)")
    for name, val in ident.items():
        if name.startswith("rom_") and val in out:
            leftovers.append(name)
    if re.search(r"NVMe\(0x1,(?!<disk-serial-redacted>)[0-9A-Fa-f]{2}-", out):
        leftovers.append("disk-serial")
    if leftovers:
        print(f"REFUSING: real value(s) still present: {sorted(set(leftovers))}")
        return 1
    print("  verified: no real identity value remains")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
