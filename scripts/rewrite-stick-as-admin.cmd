@echo off
REM ============================================================================
REM  以管理员身份重写 macOS 安装 U 盘（1401 的 usbwriter）
REM
REM  为什么需要管理员：直接写裸磁盘 \\.\PhysicalDriveN 和调用 diskpart 都要提权。
REM  注意：如果只是改一个 boot-arg 或 quirk，**不需要**用这个脚本 ——
REM        用 scripts\patch-stick-config.py 直接改 U 盘上的 config.plist 即可（免提权、秒级）。
REM
REM  用法：把下面的 3 个路径改成你自己的，然后右键「以管理员身份运行」。
REM ============================================================================

setlocal

REM --- 改成你自己的路径 ---------------------------------------------------------
set "PYTHON=C:\path\to\1401\engine\python\python.exe"
set "APP=%~dp0..\1401\engine\app"
set "BUILD=C:\path\to\1401\build"
set "REPORT=C:\path\to\1401\scan\Report.json"
set "DRIVER=C:\path\to\1401\NullMoth\nullmoth-nvidia-1.14.2.tar.gz"
set "MACAPP=C:\path\to\1401\NullMoth\1401-Mac-1.14.2.zip"
REM U 盘盘号：先用  python -m p1401.usbwriter  列出（不带参数会打印磁盘列表）
set "DISKNUM=1"
REM macOS 的 Darwin 主版本：24 = Sequoia 15
set "DARWIN=24"
REM ---------------------------------------------------------------------------

echo.
echo   ================================================================
echo    Rewriting USB stick: disk %DISKNUM%
echo    WARNING: the WHOLE stick will be erased.
echo   ================================================================
echo.

cd /d "%APP%" || (echo 找不到 %APP% & pause & exit /b 1)

"%PYTHON%" -u -m p1401.usbwriter write %DISKNUM% "%BUILD%" %DARWIN% ^
  --driver "%DRIVER%" --extra "%MACAPP%" --profile "%REPORT%"

echo.
echo   EXIT CODE: %ERRORLEVEL%   (0 = success)
echo.
echo   -- 回读 U 盘上的配置 --
"%PYTHON%" -c "import plistlib; c=plistlib.load(open(r'D:\EFI\OC\config.plist','rb')); s=c['NVRAM']['Add']['7C436110-AB2A-4BBB-A880-FE41995C9F82']; print('boot-args :', s['boot-args']); print('DmgLoading:', c['Misc']['Security']['DmgLoading']); print('Kernel.Add:', len(c['Kernel']['Add']), 'kexts')"

echo.
pause
