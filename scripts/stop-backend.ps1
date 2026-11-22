$ErrorActionPreference = 'Stop'
$pixelStopRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$pixelStopPython = Join-Path $pixelStopRoot 'backend\.venv\Scripts\python.exe'
$pixelStopProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'")
$pixelStopLaunchers = @($pixelStopProcesses | Where-Object {
    $_.ExecutablePath -eq $pixelStopPython -and $_.CommandLine -match 'manage.py.*(runserver|sync_event_media|run_face_worker)'
})
$pixelStopIds = @($pixelStopLaunchers | ForEach-Object { $_.ProcessId })
foreach ($pixelStopProcess in $pixelStopProcesses) {
    if ($pixelStopProcess.ParentProcessId -in $pixelStopIds -and $pixelStopProcess.CommandLine -match 'manage.py.*(runserver|sync_event_media|run_face_worker)') {
        Stop-Process -Id $pixelStopProcess.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
foreach ($pixelStopProcess in $pixelStopLaunchers) {
    Stop-Process -Id $pixelStopProcess.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Output 'Stopped PIXEL backend and its Drive/face workers. Close Expo terminals separately.'
