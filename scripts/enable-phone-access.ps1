#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$pixelAccessRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$pixelAccessPython = Join-Path $pixelAccessRoot 'backend\.venv\Scripts\python.exe'
$pixelAccessLog = Join-Path $pixelAccessRoot 'backend\.local\phone-firewall-status.txt'
try {
    $pixelListener = Get-NetTCPConnection -State Listen -LocalPort 8001 | Select-Object -First 1
    if (-not $pixelListener) { throw 'Start Run PIXEL Phone.bat before enabling phone access.' }
    $pixelOwner = Get-CimInstance Win32_Process -Filter "ProcessId = $($pixelListener.OwningProcess)"
    $pixelParent = Get-CimInstance Win32_Process -Filter "ProcessId = $($pixelOwner.ParentProcessId)"
    if ($pixelOwner.Name -ne 'python.exe' -or
        $pixelOwner.CommandLine -notmatch 'manage.py.*runserver.*:8001' -or
        ($pixelOwner.ExecutablePath -ne $pixelAccessPython -and $pixelParent.ExecutablePath -ne $pixelAccessPython)) {
        throw 'Port 8001 is not owned by this PIXEL project. No firewall rule was changed.'
    }
    $pixelRuleName = 'PIXEL-Phone-API-8001-LocalSubnet'
    $pixelRuleOptions = @{
        Name = $pixelRuleName
        Direction = 'Inbound'
        Action = 'Allow'
        Enabled = 'True'
        Profile = @('Private', 'Public')
        Protocol = 'TCP'
        LocalPort = '8001'
        RemoteAddress = 'LocalSubnet'
        Program = $pixelOwner.ExecutablePath
    }
    if (Get-NetFirewallRule -Name $pixelRuleName -ErrorAction SilentlyContinue) {
        Set-NetFirewallRule @pixelRuleOptions
    } else {
        New-NetFirewallRule @pixelRuleOptions -DisplayName 'PIXEL phone API - local network only' | Out-Null
    }
    'Enabled: PIXEL Python API, TCP 8001, local subnet only.' | Set-Content -LiteralPath $pixelAccessLog
} catch {
    ('Failed: ' + $_.Exception.Message) | Set-Content -LiteralPath $pixelAccessLog
    exit 1
}
