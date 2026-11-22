$ErrorActionPreference = 'Stop'
$pixelProjectRoot = Split-Path -Parent $PSScriptRoot
$pixelBackendRoot = Join-Path $pixelProjectRoot 'backend'
$pixelPythonPath = Join-Path $pixelBackendRoot '.venv\Scripts\python.exe'
$pixelLogs = Join-Path $pixelBackendRoot '.local'
if (-not (Test-Path -LiteralPath $pixelPythonPath)) { throw 'Install the backend dependencies first.' }
New-Item -ItemType Directory -Path $pixelLogs -Force | Out-Null
$pixelProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'")
# Desktop startup owns port 8000 only. Phone mode has its own API on 8001.
$pixelLaunchers = @($pixelProcesses | Where-Object { $_.ExecutablePath -eq $pixelPythonPath -and $_.CommandLine -match 'manage.py.*runserver\s+(?:127\.0\.0\.1:|localhost:|0\.0\.0\.0:)?8000(?:\s|$)' })
$pixelLauncherIds = @($pixelLaunchers | ForEach-Object { $_.ProcessId })
foreach ($pixelProcess in $pixelProcesses) {
    if ($pixelProcess.ParentProcessId -in $pixelLauncherIds -and $pixelProcess.CommandLine -match 'manage.py.*runserver') {
        Stop-Process -Id $pixelProcess.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
foreach ($pixelProcess in $pixelLaunchers) { Stop-Process -Id $pixelProcess.ProcessId -Force -ErrorAction SilentlyContinue }
$pixelServer = Start-Process -FilePath $pixelPythonPath -ArgumentList @('-u', 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload') -WorkingDirectory $pixelBackendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $pixelLogs 'server.out.log') -RedirectStandardError (Join-Path $pixelLogs 'server.err.log') -PassThru
$pixelSyncRunning = @($pixelProcesses | Where-Object { $_.ExecutablePath -eq $pixelPythonPath -and $_.CommandLine -match 'manage.py.*sync_event_media' })
if (-not $pixelSyncRunning.Count) {
    $pixelWorker = Start-Process -FilePath $pixelPythonPath -ArgumentList @('-u', 'manage.py', 'sync_event_media') -WorkingDirectory $pixelBackendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $pixelLogs 'sync.out.log') -RedirectStandardError (Join-Path $pixelLogs 'sync.err.log') -PassThru
    Write-Output "Event gallery sync worker started (PID $($pixelWorker.Id))."
}
Write-Output "PIXEL desktop backend started (PID $($pixelServer.Id)). Phone services were preserved."
if (Test-Path -LiteralPath (Join-Path $pixelProjectRoot 'face_recognition\models\face_recognition_sface_2021dec.onnx')) {
    & (Join-Path $PSScriptRoot 'start-face-worker.ps1')
}
