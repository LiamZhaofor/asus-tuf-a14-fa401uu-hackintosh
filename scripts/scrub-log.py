#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Redact identity values from an OpenCore boot log so it is safe to publish.

Usage:
    python scrub-log.py <in.txt> [out.txt] [--stick <path-to-config.plist>]

The real values are read from the live stick config so the script itself contains no
secrets. The path defaults to D:\\EFI\\OC\\config.plist but **must be passed explicitly
when the stick enumerates under another drive letter** (e.g. --stick E:\\EFI\\OC\\config.plist,
or the SCRUB_STICK_CONFIG environment variable). `sync-to-github.ps1 -StickConfig <path>`
forwards its value here, so the two never disagree.

It redacts BOTH forms of each value:

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

STICK_DEFAULT = r"D:\EFI\OC\config.plist"


def resolve_stick(argv):
    """--stick <path>, else $SCRUB_STICK_CONFIG, else the default D: path."""
    for i, a in enumerate(argv):
        if a == "--stick" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--stick="):
            return a.split("=", 1)[1]
    return os.environ.get("SCRUB_STICK_CONFIG") or STICK_DEFAULT

PLACEHOLDER = {
    "rom": "<rom-redacted>",
    "mlb": "<MLB-REDACTED>",
    "ssn": "<SMBIOS-SERIAL-REDACTED>",
    "uuid": "<UUID-REDACTED>",
    "disk": "<disk-serial-redacted>",
}


REQUIRED_IDENTITY = ("ssn", "mlb", "uuid", "rom_colon")


def read_identity(stick=STICK_DEFAULT):
    """Read the four SMBIOS identity values. FAIL CLOSED: a config that does not carry all
    four is rejected rather than silently scrubbing with a partial (or foreign) identity set,
    which would let a real value survive the check."""
    if not os.path.exists(stick):
        raise SystemExit(
            "REFUSING TO RUN - stick config not found: %s\n"
            "  the card may enumerate under another drive letter; pass --stick <path>\n"
            "  (sync-to-github.ps1 does this automatically from its -StickConfig value)\n"
            "  there is deliberately NO fallback to a default path: a config belonging to a\n"
            "  different disk would produce the wrong identity set and no leak would be found."
            % stick)
    with open(stick, "rb") as fh:
        text = fh.read().decode("utf-8", "replace")

    # sanity: this must look like an OpenCore config, not an arbitrary plist
    if "<key>PlatformInfo</key>" not in text:
        raise SystemExit("REFUSING TO RUN - %s has no <key>PlatformInfo</key>; "
                         "that is not an OpenCore config" % stick)

    out = {}
    for key, name in (("SystemSerialNumber", "ssn"), ("MLB", "mlb"), ("SystemUUID", "uuid")):
        m = re.search(rf"<key>{key}</key>\s*<string>([^<]+)</string>", text)
        if m:
            out[name] = m.group(1).strip()
    m = re.search(r"<key>ROM</key>\s*<data>\s*([^<\s]+)\s*</data>", text)
    if m:
        import base64
        try:
            raw = base64.b64decode(m.group(1).strip())
        except Exception as exc:
            raise SystemExit("REFUSING TO RUN - ROM is not valid base64 in %s (%s)" % (stick, exc))
        if len(raw) < 6:
            raise SystemExit("REFUSING TO RUN - ROM is %d bytes in %s; expected at least 6"
                             % (len(raw), stick))
        out["rom_hex"] = raw.hex().upper()
        out["rom_colon"] = ":".join(f"{b:02X}" for b in raw)
        out["rom_dash"] = "-".join(f"{b:02X}" for b in raw)

    missing = [k for k in REQUIRED_IDENTITY if not out.get(k) or not str(out[k]).strip()]
    if missing:
        raise SystemExit(
            "REFUSING TO RUN - %s is missing real identity field(s): %s\n"
            "  publishing after a partial read could let a real value through, so this is fatal."
            % (stick, ", ".join(missing)))
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
    stick = resolve_stick(argv)
    argv = [a for i, a in enumerate(argv)
            if a != "--stick" and (i == 0 or argv[i - 1] != "--stick") and not a.startswith("--stick=")]
    if not 1 <= len(argv) <= 2:
        print(__doc__)
        return 2
    src = argv[0]
    dst = argv[1] if len(argv) == 2 else src

    ident = read_identity(stick)
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
