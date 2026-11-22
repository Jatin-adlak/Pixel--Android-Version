$ErrorActionPreference = 'Stop'
try {
    $pixelHelperPath = Join-Path $PSScriptRoot 'enable-phone-access.ps1'
    $pixelHelper = Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'RemoteSigned', '-File',
        ('"{0}"' -f $pixelHelperPath)
    ) -Verb RunAs -WindowStyle Hidden -PassThru -Wait
    $pixelStatus = Join-Path (Split-Path -Parent $PSScriptRoot) 'backend\.local\phone-firewall-status.txt'
    if (Test-Path -LiteralPath $pixelStatus) { Get-Content -LiteralPath $pixelStatus }
    if ($pixelHelper.ExitCode -ne 0) { exit 1 }
    Write-Output 'Open the phone health link again, then tap Try again in PIXEL.'
} catch {
    Write-Output ('Phone access was not enabled: ' + $_.Exception.Message)
    exit 1
}
