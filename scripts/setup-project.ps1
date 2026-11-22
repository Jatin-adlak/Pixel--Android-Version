$ErrorActionPreference = 'Stop'
$pixelSetupRoot = Split-Path -Parent $PSScriptRoot
try {
    foreach ($tool in @('node.exe', 'npm.cmd', 'uv.exe')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Install $tool first. See docs/friend-setup.md, then reopen CMD." }
    }
    $pixelNode = (& node.exe --version).TrimStart('v').Split('.')
    $pixelMajor, $pixelMinor = [int]$pixelNode[0], [int]$pixelNode[1]
    if (-not (($pixelMajor -eq 22 -and $pixelMinor -ge 13) -or ($pixelMajor -eq 24 -and $pixelMinor -ge 3) -or $pixelMajor -ge 26)) { throw 'Install Node 24.3 or later in the Node 24 release line (recommended), Node 22.13+, or Node 26+.' }
    Push-Location (Join-Path $pixelSetupRoot 'backend')
    try {
        Write-Output 'Installing locked backend dependencies and Python 3.12...'
        & uv.exe sync --locked --python 3.12
        if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
    } finally { Pop-Location }
    $pixelSetupPython = Join-Path $pixelSetupRoot 'backend\.venv\Scripts\python.exe'
    & $pixelSetupPython (Join-Path $PSScriptRoot 'configure-local.py')
    if ($LASTEXITCODE -ne 0) { throw 'Private database configuration is incomplete. Follow the message above and rerun setup.' }
    Push-Location (Join-Path $pixelSetupRoot 'frontend')
    try {
        Write-Output 'Installing locked frontend dependencies...'
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    } finally { Pop-Location }
    & $pixelSetupPython (Join-Path $pixelSetupRoot 'face_recognition\download_models.py')
    if ($LASTEXITCODE -ne 0) { throw 'Recognition model verification/download failed.' }
    Push-Location (Join-Path $pixelSetupRoot 'backend')
    try {
        & $pixelSetupPython manage.py check
        if ($LASTEXITCODE -ne 0) { throw 'Backend configuration check failed.' }
        & $pixelSetupPython manage.py migrate --check
        if ($LASTEXITCODE -ne 0) { throw 'The shared database has pending migrations or cannot be reached. Ask the database owner to update it; setup does not alter live data.' }
    } finally { Pop-Location }
    Write-Output 'PIXEL setup complete. Double-click Run PIXEL.bat for desktop or Run PIXEL Phone.bat for Expo Go.'
} catch {
    Write-Output ('Setup stopped: ' + $_.Exception.Message)
    exit 1
}
