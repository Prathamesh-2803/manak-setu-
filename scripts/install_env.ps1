# Elevated bootstrap: enable WSL2 features + install Docker Desktop (silent).
# Launched by the build agent with -Verb RunAs; logs to %TEMP%\manak_install.log.
$ErrorActionPreference = "Continue"
$log = "$env:TEMP\manak_install.log"
Start-Transcript -Path $log -Force | Out-Null

Write-Output "=== [1/3] Enable WSL feature ==="
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

Write-Output "=== [2/3] Enable VirtualMachinePlatform ==="
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

Write-Output "=== [3/3] winget install Docker Desktop ==="
$winget = Get-Command winget -ErrorAction SilentlyContinue
if ($winget) {
    winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements --silent --disable-interactivity
} else {
    Write-Output "winget not found in elevated PATH - Docker must be installed manually"
}

Write-Output "=== DONE (reboot required before Docker runs) ==="
Stop-Transcript | Out-Null
