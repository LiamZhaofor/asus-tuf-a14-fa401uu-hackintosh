# =====================================================================
#  fetch-kexts.ps1 — 把 EFI/OC/Kexts 需要的第三方 kext 按固定哈希拉回来
#
#  用法（在仓库根目录）：
#      pwsh -File scripts/fetch-kexts.ps1
#      pwsh -File scripts/fetch-kexts.ps1 -Proxy http://127.0.0.1:7897
#      pwsh -File scripts/fetch-kexts.ps1 -Force        # 重新下载、覆盖已有 kext
#
#  这个仓库不保存第三方 kext 二进制，只保存一份"固定清单"：
#      scripts/kext-pins.json       每个压缩包的 URL + SHA256（取自 1401 的 mirror.json，已复核）
#      scripts/kext-manifest.json   每个 kext 的 bundle id / 版本 / 二进制 SHA256（本机实测）
#
#  脚本做四件事：下载 → 校验 SHA256 → 解包 → 复制 kext 到位 → 逐个核对二进制哈希。
#  任何一个哈希对不上就报错，不会静默写入。
# =====================================================================
param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$Proxy = $env:HTTPS_PROXY,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$pinsPath = Join-Path $PSScriptRoot 'kext-pins.json'
$manPath  = Join-Path $PSScriptRoot 'kext-manifest.json'
$kextDir  = Join-Path $RepoRoot 'EFI/OC/Kexts'
$toolsDir = Join-Path $RepoRoot 'EFI/OC/Tools'
$cacheDir = Join-Path $env:TEMP 'asus-fa401uu-kext-cache'
$workDir  = Join-Path $env:TEMP 'asus-fa401uu-kext-work'

$pins = Get-Content $pinsPath -Raw | ConvertFrom-Json
$manifest = Get-Content $manPath -Raw | ConvertFrom-Json

New-Item -ItemType Directory -Force -Path $kextDir, $cacheDir | Out-Null
if ($Force) { Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue }

function Write-Step($m) { Write-Host "`n== $m" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "   OK   $m" -ForegroundColor Green }
function Write-Warn2($m){ Write-Host "   WARN $m" -ForegroundColor Yellow }
function Write-Bad($m)  { Write-Host "   FAIL $m" -ForegroundColor Red }

function Get-File([string]$url, [string]$dest) {
    $params = @{ Uri = $url; OutFile = $dest; UseBasicParsing = $true; TimeoutSec = 300 }
    if ($Proxy) { $params.Proxy = $Proxy }
    Invoke-WebRequest @params
}

Write-Step "1/4 下载并校验压缩包（$($pins.artifacts.Count) 个）"
$bad = 0
foreach ($a in $pins.artifacts) {
    $zip = Join-Path $cacheDir ("{0}.zip" -f $a.name)
    if ((Test-Path $zip) -and -not $Force) {
        $h = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
        if ($h -eq $a.sha256) { Write-Ok "$($a.name) $($a.version)（缓存命中）"; continue }
        Remove-Item $zip -Force
    }
    try {
        Get-File $a.url $zip
        $h = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
        if ($h -ne $a.sha256) {
            Write-Bad "$($a.name) SHA256 不符`n        期望 $($a.sha256)`n        实际 $h"
            Remove-Item $zip -Force -ErrorAction SilentlyContinue
            $bad++
        } else {
            Write-Ok "$($a.name) $($a.version)"
        }
    } catch {
        Write-Bad "$($a.name) 下载失败：$($_.Exception.Message)"
        $bad++
    }
}
if ($bad -gt 0) {
    Write-Host "`n有 $bad 个压缩包失败，停止。" -ForegroundColor Red
    exit 1
}

Write-Step "2/4 解包并复制 kext"
Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $workDir | Out-Null
$copied = @()
foreach ($a in $pins.artifacts) {
    $zip = Join-Path $cacheDir ("{0}.zip" -f $a.name)
    $sub = Join-Path $workDir $a.name
    New-Item -ItemType Directory -Force -Path $sub | Out-Null
    tar.exe -xf $zip -C $sub 2>$null
    foreach ($kname in $a.provides) {
        # 有些包同时带 Debug/ 和 Release/（例如 Sinetek-rtsx），必须优先 Release，
        # 否则拿到的二进制和 manifest 对不上。__MACOSX 与 .dSYM 一律排除。
        $cands = Get-ChildItem -Path $sub -Recurse -Directory -Filter $kname -ErrorAction SilentlyContinue |
                 Where-Object { $_.FullName -notmatch '__MACOSX|\.dSYM' }
        $prefer = $cands | Where-Object { $_.FullName -match '[\\/]Release[\\/]' }
        if (-not $prefer) { $prefer = $cands | Where-Object { $_.FullName -notmatch '[\\/]Debug[\\/]' } }
        if (-not $prefer) { $prefer = $cands }
        $found = $prefer | Sort-Object { $_.FullName.Length } | Select-Object -First 1
        if (-not $found) { Write-Bad "$($a.name) 里找不到 $kname"; continue }
        $dest = Join-Path $kextDir $kname
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        robocopy $found.FullName $dest /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
        Write-Ok "$kname  <- $($a.name)"
        $copied += $kname
    }
}

Write-Step "3/4 补齐 NullMothSafe.efi（1401 的救急工具，无公开直链）"
$toolDone = $false
$target = Join-Path $toolsDir 'NullMothSafe.efi'
if ((Test-Path $target) -and -not $Force) {
    Write-Ok "已存在 EFI/OC/Tools/NullMothSafe.efi"; $toolDone = $true
} else {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'NullMoth/1401/OCK_Files/NullMothSafe.efi'),
        'E:\EFI\OC\Tools\NullMothSafe.efi',
        'D:\EFI\OC\Tools\NullMothSafe.efi'
    )
    # 1401 的架构目录可能有多层，做一次浅搜
    if (Test-Path (Join-Path $env:LOCALAPPDATA 'NullMoth/1401')) {
        $candidates += (Get-ChildItem (Join-Path $env:LOCALAPPDATA 'NullMoth/1401') -Recurse -Filter 'NullMothSafe.efi' -ErrorAction SilentlyContinue |
                        Select-Object -ExpandProperty FullName)
    }
    foreach ($c in $candidates) {
        if (-not $c) { continue }
        if (-not (Test-Path -LiteralPath $c -ErrorAction SilentlyContinue)) { continue }
        try {
            New-Item -ItemType Directory -Force -Path $toolsDir -ErrorAction Stop | Out-Null
            Copy-Item -LiteralPath $c -Destination $target -Force -ErrorAction Stop
            Write-Ok "从 $c 复制过来"
            $toolDone = $true
            break
        } catch {
            # 典型情况：直接读 E:\EFI（ESP）会被拒绝 —— 那是权限问题，换个候选继续
            Write-Warn2 "读不了 $c（$($_.Exception.Message.Split([char]10)[0])），跳过"
        }
    }
    if (-not $toolDone) {
        Write-Warn2 "没找到 NullMothSafe.efi。"
        Write-Warn2 "影响：OpenCore 菜单里那两条 '1401: ...' 救急项不会出现（不影响正常启动）。"
        Write-Warn2 "取得方式：跑一次 1401 构建，或从已经写好 EFI 的 ESP 上复制 EFI/OC/Tools/NullMothSafe.efi。"
    }
}

Write-Step "4/4 按 manifest 逐个核对二进制 SHA256"
$fail = 0
foreach ($kext in $manifest.PSObject.Properties) {
    $name = $kext.Name
    $info = $kext.Value
    $dir  = Join-Path $kextDir $name
    if (-not (Test-Path $dir)) {
        if ($name -eq 'RogProbe2.kext') {
            Write-Bad "$name 缺失（这是本仓库自带的 kext，应该跟着仓库来，不该缺）"
            $fail++
        } else {
            Write-Bad "$name 缺失"
            $fail++
        }
        continue
    }
    if (-not $info.binary) { Write-Ok "$name（无独立二进制）"; continue }
    $bin = Join-Path $dir $info.binary
    if (-not (Test-Path $bin)) { Write-Bad "$name 缺少 $($info.binary)"; $fail++; continue }
    $h = (Get-FileHash $bin -Algorithm SHA256).Hash.ToLower()
    if ($h -eq $info.sha256) {
        Write-Ok "$name $($info.version) $($h.Substring(0,16))…"
    } else {
        Write-Bad "$name 哈希不符`n        期望 $($info.sha256)`n        实际 $h"
        $fail++
    }
}

Write-Host ""
if ($fail -eq 0) {
    Write-Host "全部完成：$($manifest.PSObject.Properties.Name.Count) 个 kext 就位，二进制哈希全部匹配。" -ForegroundColor Green
    Write-Host "下一步：把 EFI/ 复制到 ESP，并换上你自己的 SMBIOS 三码。" -ForegroundColor Green
    exit 0
} else {
    Write-Host "有 $fail 项不一致，见上面的 FAIL。" -ForegroundColor Red
    exit 1
}
