$ErrorActionPreference = 'Stop'
# Read-only enumeration of every PCI device that has a LogConf key in the Enum hive.
# RegOpenKeyEx(KEY_READ) + RegQueryValueEx only; nothing is written anywhere.
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class RegRaw2 {
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern int RegOpenKeyExW(IntPtr hKey, string subKey, uint opts, uint samDesired, out IntPtr phkResult);
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern int RegQueryValueExW(IntPtr hKey, string valueName, IntPtr reserved, out uint type, byte[] data, ref uint cbData);
    [DllImport("advapi32.dll", SetLastError=true)]
    public static extern int RegCloseKey(IntPtr hKey);
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern int RegEnumKeyExW(IntPtr hKey, uint dwIndex, StringBuilder lpName, ref uint lpcchName,
        IntPtr lpReserved, IntPtr lpClass, IntPtr lpcchClass, IntPtr lpftLastWriteTime);
}
'@
$HKLM = [IntPtr]0x80000002
$KEY_READ = 0x20019
$ENUM = 'SYSTEM\CurrentControlSet\Enum\PCI'

function Open-Key([string]$sub) {
    $hk = [IntPtr]::Zero
    $rc = [RegRaw2]::RegOpenKeyExW($HKLM, $sub, 0, $KEY_READ, [ref]$hk)
    if ($rc -ne 0) { return $null }
    return $hk
}
function Get-Bytes($hk, [string]$value) {
    $type = [uint32]0; $cb = [uint32]0
    $rc = [RegRaw2]::RegQueryValueExW($hk, $value, [IntPtr]::Zero, [ref]$type, $null, [ref]$cb)
    if ($rc -ne 0) { return $null }
    $buf = New-Object byte[] $cb
    $rc = [RegRaw2]::RegQueryValueExW($hk, $value, [IntPtr]::Zero, [ref]$type, $buf, [ref]$cb)
    if ($rc -ne 0) { return $null }
    return @{ type = $type; bytes = $buf }
}
function Enum-SubKeys($hk) {
    $names = New-Object System.Collections.Generic.List[string]
    $i = 0
    while ($true) {
        $sb = New-Object System.Text.StringBuilder 512
        $len = [uint32]512
        $rc = [RegRaw2]::RegEnumKeyExW($hk, [uint32]$i, $sb, [ref]$len, [IntPtr]::Zero, [IntPtr]::Zero, [IntPtr]::Zero, [IntPtr]::Zero)
        if ($rc -ne 0) { break }
        $names.Add($sb.ToString())
        $i++
    }
    return $names
}

$out = 'C:\Users\24269\Documents\macos\audit\round8\registry-logconf-all.txt'
$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# every HKLM Enum\PCI\<dev>\<inst>\LogConf value, raw (read-only RegQueryValueEx)")
$lines.Add("# KIND 8=REG_RESOURCE_LIST 9=REG_FULL_RESOURCE_DESCRIPTOR 10=REG_RESOURCE_REQUIREMENTS_LIST")

$root = Open-Key $ENUM
$devKeys = Enum-SubKeys $root
[void][RegRaw2]::RegCloseKey($root)
$count = 0
foreach ($dev in $devKeys) {
    $dh = Open-Key "$ENUM\$dev"
    if ($null -eq $dh) { continue }
    $insts = Enum-SubKeys $dh
    [void][RegRaw2]::RegCloseKey($dh)
    foreach ($inst in $insts) {
        $iid = "$dev\$inst"
        $lh = Open-Key "$ENUM\$iid\LogConf"
        if ($null -eq $lh) { continue }
        $count++
        $lines.Add("===DEVICE $iid")
        foreach ($v in @('BootConfig', 'BasicConfigVector')) {
            $r = Get-Bytes $lh $v
            if ($null -eq $r) { continue }
            $hex = ($r.bytes | ForEach-Object { $_.ToString('x2') }) -join ''
            $lines.Add("VAL $v kind=$($r.type) len=$($r.bytes.Length)")
            $lines.Add("HEX $hex")
        }
        [void][RegRaw2]::RegCloseKey($lh)
    }
}
$lines | Set-Content -Path $out -Encoding utf8
Write-Host "devices with LogConf: $count -> $out"