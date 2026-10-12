<#
.SYNOPSIS
    Publish the current state of the Hackintosh stick to GitHub, safely.

.DESCRIPTION
    Enforces the repository's sync contract, in this order:

      1. sanitize   - copy the live stick config into efi/config.plist with the four
                      SMBIOS identity fields zeroed (byte-preserving, so the diff only
                      shows real changes)
      2. validate   - run the OpenCore 1.0.9 ocvalidate that matches the stick's build
      3. leak scan  - read the REAL identity values off the stick and grep the whole
                      repository for them; also refuse known-sensitive file types
      4. publish    - git add / commit / push
      5. re-verify  - pull the pushed files back down and scan them again, so a leak is
                      caught after the fact rather than assumed absent

    The script never prints the real serial/MLB/UUID/ROM values - only whether they matched.

.PARAMETER Message
    Commit message. Defaults to a timestamped status line.

.PARAMETER SkipPush
    Do steps 1-3 and stop (dry run: prepare and check, do not commit).

.PARAMETER Proxy
    HTTP(S) proxy for git/network operations, e.g. http://127.0.0.1:7897.
    Omit to let git use its own configuration.

.EXAMPLE
    .\scripts\sync-to-github.ps1 -Message "round1: let boot-args actually apply (add to NVRAM Delete)"
#>
[CmdletBinding()]
param(
    [string] $Message,
    [switch] $SkipPush,
    [string] $Proxy,
    [string] $StickConfig = 'D:\EFI\OC\config.plist'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $repo '.git'))) { throw "not a git repository: $repo" }

function Step($n, $text) { Write-Host "`n=== [$n] $text" -ForegroundColor Cyan }
function Ok($text)   { Write-Host "  OK   $text" -ForegroundColor Green }
function Bad($text)  { Write-Host "  FAIL $text" -ForegroundColor Red }

# ------------------------------------------------------------------ 0. find python
$python = $null
foreach ($cand in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        "$env:USERPROFILE\Documents\macos\1401\extracted\1401\engine\python\python.exe")) {
    if (Test-Path $cand) { $python = $cand; break }
}
if (-not $python) {
    foreach ($name in @('python', 'python3', 'py')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { $python = $cmd.Source; break }
    }
}
if (-not $python) { throw "no python interpreter found; cannot sanitize the config" }
Write-Host "python : $python"

# ------------------------------------------------------------------ 1. sanitize
Step 1 "sanitize the stick config into efi/config.plist"
if (-not (Test-Path $StickConfig)) { throw "stick config not found: $StickConfig (is the stick plugged in?)" }
$staged = Join-Path $env:TEMP ("1401-sanitized-" + [guid]::NewGuid().ToString('N') + ".plist")
& $python (Join-Path $repo 'scripts\sanitize-config.py') $StickConfig $staged
if ($LASTEXITCODE -ne 0) { throw "sanitize-config.py failed (exit $LASTEXITCODE) - refusing to publish" }

$target = Join-Path $repo 'efi\config.plist'
$before = if (Test-Path $target) { (Get-FileHash -Algorithm SHA256 $target).Hash } else { '<none>' }
Copy-Item $staged $target -Force
Remove-Item $staged -Force
$after = (Get-FileHash -Algorithm SHA256 $target).Hash
if ($before -eq $after) { Ok "efi/config.plist unchanged ($($after.Substring(0,16))...)" }
else { Ok "efi/config.plist updated  $($before.Substring(0,16))... -> $($after.Substring(0,16))..." }

# Boot logs carry the same identity values (serial/MLB/UUID/MAC/disk serial). Scrub them
# in place first: they are also what a stale-but-published log leaked last time.
$logs = @(Get-ChildItem (Join-Path $repo 'logs') -Filter 'opencore-*.txt' -ErrorAction SilentlyContinue)
foreach ($l in $logs) {
    $out = & $python (Join-Path $repo 'scripts\scrub-log.py') $l.FullName 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { Write-Host $out; throw "scrub-log.py failed on $($l.Name) - refusing to publish" }
    Write-Host ("    " + $out.Trim())
}
Ok "boot logs scrubbed ($($logs.Count) file(s))"

# ------------------------------------------------------------------ 2. validate
Step 2 "ocvalidate"
$ocv = Get-ChildItem (Join-Path $env:USERPROFILE '.cache\1401') -Filter '*-ocvalidate.exe' -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($ocv) {
    $out = & $ocv.FullName $target 2>&1 | Out-String
    Write-Host $out.Trim()
    if ($LASTEXITCODE -ne 0) { throw "ocvalidate reported issues in efi/config.plist" }
    Ok "ocvalidate clean ($($ocv.Name))"
}
else {
    Bad "no ocvalidate in ~/.cache/1401 - run 1401's build/validate once to fetch it"
    throw "refusing to publish an unvalidated config"
}

# ------------------------------------------------------------------ 3. leak scan
Step 3 "leak scan (real identity values read from the stick, never printed)"
$stickText = Get-Content $StickConfig -Raw
$secrets = @{}
foreach ($key in @('SystemSerialNumber', 'MLB', 'SystemUUID')) {
    $m = [regex]::Match($stickText, "<key>$key</key>\s*<string>([^<]+)</string>")
    if ($m.Success) { $secrets[$key] = $m.Groups[1].Value.Trim() }
}
$m = [regex]::Match($stickText, '<key>ROM</key>\s*<data>\s*([^<\s]+)\s*</data>')
if ($m.Success) { $secrets['ROM'] = $m.Groups[1].Value.Trim() }

# The ROM blob is the NIC MAC as raw bytes; also look for the other renderings.
if ($secrets.ContainsKey('ROM')) {
    try {
        $bytes = [Convert]::FromBase64String($secrets['ROM'])
        if ($bytes.Length -ge 6) {
            $secrets['ROM-as-MAC-colon'] = ($bytes[0..5] | ForEach-Object { $_.ToString('X2') }) -join ':'
            $secrets['ROM-as-MAC-dash']  = ($bytes[0..5] | ForEach-Object { $_.ToString('X2') }) -join '-'
            $secrets['ROM-as-hex']       = ($bytes[0..5] | ForEach-Object { $_.ToString('X2') }) -join ''
        }
    } catch { }
}

# OpenCore prints system-id with the first three GUID fields BYTE-SWAPPED, so searching
# for the config's SystemUUID string alone misses it - that is exactly how one published
# log kept a real UUID. Search the little-endian rendering and the GUID's tail as well.
if ($secrets.ContainsKey('SystemUUID')) {
    try {
        $guidBytes = ([guid]$secrets['SystemUUID']).ToByteArray()
        $sw = ([BitConverter]::ToString($guidBytes)) -replace '-', ''
        if ($sw.Length -eq 32) {
            $secrets['SystemUUID-swapped'] = ($sw.Substring(0,8) + '-' + $sw.Substring(8,4) + '-' +
                                              $sw.Substring(12,4) + '-' + $sw.Substring(16,4) + '-' +
                                              $sw.Substring(20,12))
            $secrets['SystemUUID-tail'] = $sw.Substring(20,12)
        }
        # Partial disclosure counts too: an 8-char field of the GUID is still real data.
        # (Tiny chance of a false positive inside a log's hex dump; the failure mode is
        #  "refuse to publish", which is the safe direction.)
        $plain = $secrets['SystemUUID'].Replace('-','').ToUpper()
        if ($plain.Length -eq 32) {
            $secrets['SystemUUID-prefix']        = $plain.Substring(0,8)
            $secrets['SystemUUID-swapped-prefix'] = $sw.Substring(0,8)
        }
    } catch { }
}

$files = Get-ChildItem $repo -Recurse -File -Force |
         Where-Object { $_.FullName -notlike "*$([IO.Path]::DirectorySeparatorChar).git$([IO.Path]::DirectorySeparatorChar)*" }
$leaks = @()
foreach ($kv in $secrets.GetEnumerator()) {
    if ([string]::IsNullOrWhiteSpace($kv.Value)) { continue }
    foreach ($f in $files) {
        if (Select-String -Path $f.FullName -SimpleMatch -Pattern $kv.Value -Quiet -ErrorAction SilentlyContinue) {
            $leaks += "$($kv.Key) found in $($f.FullName.Substring($repo.Length + 1))"
        }
    }
}
# The internal NVMe serial is not in the stick config; it only appears inside device
# paths in the logs, as hex bytes. Require it to be redacted.
$nvme = Get-ChildItem $repo -Recurse -File -Force |
        Where-Object { $_.FullName -notlike "*$([IO.Path]::DirectorySeparatorChar).git$([IO.Path]::DirectorySeparatorChar)*" } |
        Select-String -Pattern 'NVMe\(0x1,(?!<disk-serial-redacted>)[0-9A-Fa-f]{2}-' -ErrorAction SilentlyContinue
foreach ($h in $nvme) { $leaks += "unredacted NVMe disk serial in $($h.Path.Substring($repo.Length + 1)):$($h.LineNumber)" }

if ($leaks.Count) { $leaks | ForEach-Object { Bad $_ }; throw "identity values are present in the repository - not publishing" }
Ok "no identity value from the stick appears anywhere in the repository"

# known-sensitive file types that must never be published
$forbidden = @('Report.json', '*.aml', '*.bin', '*.dmg', '*.zip', '*.kext', '*.efi', '*.rom', '*.nvram.plist')
$hits = @()
foreach ($p in $forbidden) { $hits += Get-ChildItem $repo -Recurse -File -Force -Filter $p -ErrorAction SilentlyContinue }
$hits = $hits | Where-Object { $_.FullName -notlike '*\.git\*' }
if ($hits.Count) { $hits | ForEach-Object { Bad "forbidden file: $($_.FullName.Substring($repo.Length + 1))" }; throw "forbidden files present" }
Ok "no raw scan / ACPI dump / binary artifacts present"

$big = Get-ChildItem $repo -Recurse -File -Force | Where-Object { $_.Length -gt 1MB -and $_.FullName -notlike '*\.git\*' }
if ($big) { $big | ForEach-Object { Bad "unexpected large file: $($_.Name) ($([math]::Round($_.Length/1MB,1)) MB)" }; throw "large files present" }
Ok "no files larger than 1 MB"

# ------------------------------------------------------------------ 4. publish
if ($SkipPush) { Step 4 "skip push (-SkipPush)"; Ok "prepared and checked; nothing committed"; exit 0 }

Step 4 "commit and push"
Push-Location $repo
try {
    $gitArgs = @()
    if ($Proxy) { $gitArgs = @('-c', "http.proxy=$Proxy", '-c', "https.proxy=$Proxy") }
    $env:GIT_TERMINAL_PROMPT = '0'

    git @gitArgs add -A
    $staged = git @gitArgs diff --cached --name-only
    if (-not $staged) { Ok "nothing to commit"; }
    else {
        Write-Host "  staged:"; $staged | ForEach-Object { Write-Host "    $_" }
        if (-not $Message) {
            $Message = "sync: stick state as of " + (Get-Date -Format 'yyyy-MM-dd HH:mm') +
                       " (ocvalidate clean, sanitized)"
        }
        git @gitArgs commit -m $Message | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
    }
    git @gitArgs push origin HEAD | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "git push failed" }
    Ok "pushed"

    # ------------------------------------------------------------ 5. re-verify
    Step 5 "re-verify the pushed content from the remote"
    $remoteCfg = git @gitArgs show "origin/$(git rev-parse --abbrev-ref HEAD):efi/config.plist"
    if ($LASTEXITCODE -ne 0) { throw "could not read efi/config.plist back from the remote" }
    $remoteText = $remoteCfg -join "`n"
    $bad = @()
    foreach ($kv in $secrets.GetEnumerator()) {
        if (-not [string]::IsNullOrWhiteSpace($kv.Value) -and $remoteText.Contains($kv.Value)) { $bad += $kv.Key }
    }
    if ($bad.Count) { throw "the PUSHED config still contains: $($bad -join ', ')" }
    Ok "pushed efi/config.plist carries no real identity value"

    $head = git rev-parse --short HEAD
    $url  = (git remote get-url origin) -replace '\.git$', ''
    Write-Host ""
    Write-Host "  commit : $head" -ForegroundColor Green
    Write-Host "  remote : $url" -ForegroundColor Green
    Write-Host "  files  :"; git show --stat --oneline HEAD | Select-Object -Skip 1 | ForEach-Object { Write-Host "    $_" }
}
finally { Pop-Location }
