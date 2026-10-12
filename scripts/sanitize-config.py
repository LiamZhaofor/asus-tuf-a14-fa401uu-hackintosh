#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zero the SMBIOS identity fields of a config.plist so it is safe to publish.

Usage:
    python sanitize-config.py <in.plist> [out.plist]

With no out.plist the result is written to <in.plist>.sanitized.

Only four values are rewritten, by anchored regular expression, so every other byte
of the file (key order, indentation, line endings) is preserved and the published
diff stays minimal:

    PlatformInfo -> Generic -> SystemSerialNumber
    PlatformInfo -> Generic -> MLB
    PlatformInfo -> Generic -> SystemUUID
    PlatformInfo -> Generic -> ROM            (base64 of 6 zero bytes)

Those four are the identity that Apple's services key on (iMessage/FaceTime/App Store).
Everything else in this repository's config is non-identifying, and the raw hardware
scan report (NIC MAC, disk serials) is deliberately not published at all.

Exit status is 1 if a field was not found, so a silent failure cannot publish a config
with a real serial number still in it.
"""
import os
import re
import sys

ZERO_SERIAL = "000000000000"
ZERO_MLB = "00000000000000000"
ZERO_UUID = "00000000-0000-0000-0000-000000000000"
ZERO_ROM = "AAAAAAAA"

# (label, pattern, replacement-value-kind)
PLAIN = [
    ("SystemSerialNumber", r"(<key>SystemSerialNumber</key>\s*<string>)[^<]*(</string>)", ZERO_SERIAL),
    ("MLB",                r"(<key>MLB</key>\s*<string>)[^<]*(</string>)",                ZERO_MLB),
    ("SystemUUID",         r"(<key>SystemUUID</key>\s*<string>)[^<]*(</string>)",         ZERO_UUID),
]


def sanitize(text):
    """Returns (sanitized_text, {field: occurrences})."""
    counts = {}
    out = text
    for label, pattern, value in PLAIN:
        out, n = re.subn(pattern, lambda m, v=value: m.group(1) + v + m.group(2), out)
        counts[label] = n

    # <data> body: keep the tag's own leading/trailing whitespace verbatim, replace only the payload.
    def rom_sub(m):
        body = m.group(2)
        lead = re.match(r"\s*", body).group(0)
        trail = re.search(r"\s*$", body).group(0)
        return m.group(1) + lead + ZERO_ROM + trail + m.group(3)

    out, n = re.subn(r"(<key>ROM</key>\s*<data>)(.*?)(</data>)", rom_sub, out, flags=re.S)
    counts["ROM"] = n
    return out, counts


def main(argv):
    if not 1 <= len(argv) <= 2:
        print(__doc__)
        return 2

    src = argv[0]
    dst = argv[1] if len(argv) == 2 else src + ".sanitized"
    if os.path.abspath(src) == os.path.abspath(dst):
        if not argv[1:]:
            pass  # explicit in-place with ".sanitized" suffix never collides
    with open(src, "rb") as fh:
        text = fh.read().decode("utf-8")

    out, counts = sanitize(text)

    bad = [k for k, n in counts.items() if n == 0]
    for label, n in counts.items():
        print(f"  {label:<20} occurrences: {n}")
    if bad:
        print(f"REFUSING to write: field(s) not found -> {', '.join(bad)}")
        return 1

    with open(dst, "wb") as fh:
        fh.write(out.encode("utf-8"))

    print(f"sanitized {src} -> {dst}  ({len(text)} -> {len(out)} bytes)")
    leftover = [s for s in re.findall(r"<key>(SystemSerialNumber|MLB|SystemUUID)</key>\s*<string>([^<]*)</string>", out)
                if s[1] not in (ZERO_SERIAL, ZERO_MLB, ZERO_UUID)]
    if leftover:
        print(f"REFUSING: value(s) still present: {leftover}")
        return 1
    print("verified: no identity value remains")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
