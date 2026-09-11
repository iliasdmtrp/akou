<#
autostart.ps1 - Install/remove auto-start of the Greek voice dictation at Windows
logon. Uses the per-user Startup folder (NO admin needed). Runs silently with
pythonw (no console window).

Usage:
    powershell -ExecutionPolicy Bypass -File autostart.ps1 install
    powershell -ExecutionPolicy Bypass -File autostart.ps1 uninstall
    powershell -ExecutionPolicy Bypass -File autostart.ps1 status
#>
param([ValidateSet("install","uninstall","status")] [string]$action = "status")

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $scriptDir "listener.py"
$startup = [Environment]::GetFolderPath("Startup")
$lnk = Join-Path $startup "akou-voice.lnk"

# pythonw = Python with no console window (runs silently in the background)
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) { $pythonw = "pythonw.exe" }

switch ($action) {
  "install" {
    $sh = New-Object -ComObject WScript.Shell
    $s = $sh.CreateShortcut($lnk)
    $s.TargetPath = $pythonw
    $s.Arguments = "`"$target`""
    $s.WorkingDirectory = $scriptDir
    $s.WindowStyle = 7   # minimized
    $s.Description = "akou - Greek accessible voice for Claude Code"
    $s.Save()
    Start-Process -FilePath $pythonw -ArgumentList "`"$target`"" -WorkingDirectory $scriptDir -WindowStyle Hidden
    Write-Output "OK: installed to Startup. Runs automatically at every logon (and started now)."
  }
  "uninstall" {
    if (Test-Path $lnk) { Remove-Item $lnk -Force }
    Get-CimInstance Win32_Process -Filter "name='pythonw.exe' OR name='python.exe'" |
      Where-Object { $_.CommandLine -like '*listener.py*' } |
      ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Write-Output "OK: removed from Startup and stopped the listener."
  }
  "status" {
    if (Test-Path $lnk) { Write-Output "Installed (Startup shortcut present)." }
    else { Write-Output "Not installed." }
  }
}
