#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only audit: does any REAL SMBIOS identity value survive in this repository's history?

WHY
    The working tree can be clean while an earlier commit still carries a value.  The sync
    script only scans the current tree, so history needs its own check.

WHAT IT DOES
    * reads the four identity values from the live stick config (same fail-closed rules as
      scrub-log.py: the file must be an OpenCore config and must carry all four fields);
    * builds the same renderings the sync script checks for (plain, upper/lower, the
      byte-swapped UUID that OpenCore prints, both 8-character UUID prefixes, and the MAC in
      colon / dash / packed-hex form), plus a structural check for an unredacted
      `NVMe(0x1,<disk-serial>)` device path;
    * walks EVERY object reachable from EVERY ref (`git rev-list --objects --all`), reads the
      blob contents through `git cat-file --batch`, and searches them;
    * also scans every commit message;
    * for each hit, reports the file path, the commits that contain that object
      (`git log --all --find-object=<oid>`) and whether the object is still reachable from HEAD.

WHAT IT NEVER DOES
    * it never prints a real identity value - only the KIND of value and where it was found;
    * it never writes to the repository: no commit, no reset, no force-push, no history
      rewrite, no reflog or gc operation. Every git invocation is a read-only query
      (`rev-list`, `cat-file`, `log --find-object`, `rev-parse`).

USAGE
    python audit-history-secrets.py --stick E:\\EFI\\OC\\config.plist [--repo PATH]
                                    [--out report.json]
    Exit code 0 = clean, 1 = hits found, 2 = could not audit (refuses rather than guessing).
"""
import argparse
import json
import os
import re
import subprocess
import sys

# paths in this repository contain non-ASCII characters; do not let the console encoding
# turn them into mojibake (or crash the audit).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REQUIRED = ("ssn", "mlb", "uuid", "rom_colon")


def read_identity(stick):
    if not os.path.exists(stick):
        sys.stderr.write("REFUSING - stick config not found: %s\n" % stick)
        sys.exit(2)
    text = open(stick, "rb").read().decode("utf-8", "replace")
    if "<key>PlatformInfo</key>" not in text:
        sys.stderr.write("REFUSING - %s is not an OpenCore config (no PlatformInfo)\n" % stick)
        sys.exit(2)
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
        except Exception:
            raw = b""
        if len(raw) >= 6:
            out["rom_colon"] = ":".join("%02X" % b for b in raw[:6])
            out["rom_dash"] = "-".join("%02X" % b for b in raw[:6])
            out["rom_hex"] = "".join("%02X" % b for b in raw[:6])
    missing = [k for k in REQUIRED if not out.get(k)]
    if missing:
        sys.stderr.write("REFUSING - missing identity field(s): %s\n" % ", ".join(missing))
        sys.exit(2)
    return out


def swap_guid(u):
    h = u.replace("-", "")
    if len(h) != 32:
        return None
    d1, d2, d3, rest = h[0:8], h[8:12], h[12:16], h[16:32]
    return "-".join([
        "".join(reversed([d1[i:i + 2] for i in range(0, 8, 2)])),
        "".join(reversed([d2[i:i + 2] for i in range(0, 4, 2)])),
        "".join(reversed([d3[i:i + 2] for i in range(0, 4, 2)])),
        rest[0:4], rest[4:16],
    ]).upper()


def build_secrets(ident):
    """[(kind, needle_bytes)] - kinds are safe labels, never values."""
    out = []

    def add(kind, s):
        if not s:
            return
        for variant in {s, s.upper(), s.lower()}:
            if len(variant) >= 6:
                out.append((kind, variant.encode()))

    add("SMBIOS serial", ident.get("ssn"))
    add("MLB", ident.get("mlb"))
    add("SystemUUID", ident.get("uuid"))
    sw = swap_guid(ident.get("uuid", ""))
    if sw:
        add("SystemUUID (byte-swapped, as OpenCore prints it)", sw)
    for label, src in (("SystemUUID", ident.get("uuid")), ("SystemUUID (byte-swapped)", sw)):
        if src:
            plain = src.replace("-", "")
            if len(plain) == 32:
                add(label + " first 8 chars", plain[:8])
    add("ROM MAC (colon)", ident.get("rom_colon"))
    add("ROM MAC (dash)", ident.get("rom_dash"))
    add("ROM MAC (packed)", ident.get("rom_hex"))
    return out


def git(repo, *args, binary=False, stdin=None):
    cmd = ["git", "-C", repo] + list(args)
    r = subprocess.run(cmd, input=stdin, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace")[:300]))
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stick", required=True)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        sys.stderr.write("REFUSING - not a git repository: %s\n" % repo)
        return 2

    ident = read_identity(args.stick)
    secrets = build_secrets(ident)

    # ---- every object reachable from every ref
    listing = git(repo, "rev-list", "--objects", "--all")
    oid_path = {}
    for line in listing.splitlines():
        parts = line.split(" ", 1)
        oid_path.setdefault(parts[0], parts[1] if len(parts) > 1 else "")

    # ---- types in one pass
    types = {}
    batch = "\n".join(oid_path) + "\n"
    out = git(repo, "cat-file", "--batch-check", binary=True, stdin=batch.encode())
    for line in out.decode("utf-8", "replace").splitlines():
        p = line.split()
        if len(p) >= 2:
            types[p[0]] = p[1]

    blobs = [o for o, t in types.items() if t == "blob"]
    hits = []
    # ---- read every blob in one batch and search
    payload = ("\n".join(blobs) + "\n").encode() if blobs else b""
    raw = git(repo, "cat-file", "--batch", binary=True, stdin=payload) if blobs else b""
    pos = 0
    for oid in blobs:
        nl = raw.find(b"\n", pos)
        if nl < 0:
            break
        header = raw[pos:nl].decode("utf-8", "replace").split()
        if len(header) < 3:
            pos = nl + 1
            continue
        size = int(header[2])
        body = raw[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1
        found = []
        for kind, needle in secrets:
            if needle and needle in body:
                found.append(kind)
        # structural: an NVMe disk serial that was never redacted
        if re.search(rb"NVMe\(0x1,(?!<disk-serial-redacted>)[0-9A-Fa-f]{2}-", body):
            found.append("NVMe disk serial (unredacted device path)")
        if found:
            hits.append({"oid": oid, "path": oid_path.get(oid, ""), "kinds": sorted(set(found))})

    # ---- commit messages
    log = git(repo, "log", "--all", "--format=%H%x1f%B%x1e")
    msg_hits = []
    for rec in log.split("\x1e"):
        rec = rec.strip("\n")
        if not rec or "\x1f" not in rec:
            continue
        h, body = rec.split("\x1f", 1)
        found = sorted({kind for kind, needle in secrets if needle and needle in body.encode()})
        if found:
            msg_hits.append({"commit": h.strip(), "kinds": found})

    head = git(repo, "rev-parse", "HEAD").strip()
    # ---- for each hit blob: which commits contain it, and is it in HEAD's history
    for h in hits:
        try:
            cl = git(repo, "log", "--all", "--format=%H", "--find-object=" + h["oid"])
            h["commits"] = [c for c in cl.split() if c]
        except RuntimeError:
            h["commits"] = []
        try:
            in_head = git(repo, "log", "HEAD", "--format=%H", "--find-object=" + h["oid"]).strip()
            h["reachable_from_head"] = bool(in_head)
        except RuntimeError:
            h["reachable_from_head"] = None

    report = {
        "audited": {
            "repo_head": head,
            "objects": len(oid_path),
            "blobs": len(blobs),
            "commits_scanned": log.count("\x1e"),
            "secret_needles": len(secrets),
            "needle_kinds": sorted({k for k, _ in secrets}),
        },
        "blob_hits": hits,
        "commit_message_hits": msg_hits,
        "clean": not hits and not msg_hits,
    }

    print("read-only git history identity audit")
    print("  repo HEAD        : %s" % head)
    print("  objects / blobs  : %d / %d" % (len(oid_path), len(blobs)))
    print("  needle kinds     : %s" % ", ".join(sorted({k for k, _ in secrets})))
    print("  blob hits        : %d" % len(hits))
    for h in hits:
        print("    - %s  kinds=%s  commits=%d  in HEAD history=%s"
              % (h["path"] or "(no path)", ",".join(h["kinds"]), len(h["commits"]),
                 h["reachable_from_head"]))
        for c in h["commits"][:6]:
            print("        commit %s" % c[:12])
        if len(h["commits"]) > 6:
            print("        ... %d more" % (len(h["commits"]) - 6))
    print("  commit-message hits: %d" % len(msg_hits))
    for m in msg_hits:
        print("    - commit %s kinds=%s" % (m["commit"][:12], ",".join(m["kinds"])))
    if report["clean"]:
        print("\nRESULT: CLEAN - no real identity value found in any reachable object or message.")
    else:
        print("\nRESULT: HITS FOUND - see above. This script does NOT rewrite history.")
        print("  Recommendation: the value is already published, so rewriting history does not")
        print("  un-publish it. Prefer (a) rotating the affected identity on the stick, and")
        print("  (b) if the repository must be scrubbed anyway, do it as a separate, explicitly")
        print("  approved operation with a backup - never from an audit script.")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=False)
        print("wrote %s" % args.out)
    return 0 if report["clean"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
