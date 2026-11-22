param([switch]$Restart)
$ErrorActionPreference = 'Stop'
$pixelRoot = Split-Path -Parent $PSScriptRoot
$pixelBackend = Join-Path $pixelRoot 'backend'
$pixelPython = Join-Path $pixelBackend '.venv\Scripts\python.exe'
$pixelExisting = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.ExecutablePath -eq $pixelPython -and $_.CommandLine -match 'manage.py.*run_face_worker' })
if ($pixelExisting.Count -and -not $Restart) { Write-Output 'PIXEL face matching worker is already running.'; return }
if ($Restart) {
    $pixelLauncherIds = @($pixelExisting | ForEach-Object { $_.ProcessId })
    $pixelAllPython = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'")
    foreach ($pixelChild in $pixelAllPython) {
        if ($pixelChild.ParentProcessId -in $pixelLauncherIds -and $pixelChild.CommandLine -match 'manage.py.*run_face_worker') {
            Stop-Process -Id $pixelChild.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($pixelParent in $pixelExisting) { Stop-Process -Id $pixelParent.ProcessId -Force -ErrorAction SilentlyContinue }
    Push-Location $pixelBackend
    try { & $pixelPython manage.py shell -c "from django.conf import settings; from apps.face_search.models import FaceWorkerState; FaceWorkerState.objects.filter(node_id=settings.FACE_WORKER_NODE_ID).update(lease_until=None, token=None, last_seen_at=None)" | Out-Null } finally { Pop-Location }
}
$pixelLogs = Join-Path $pixelBackend '.local'
New-Item -ItemType Directory -Path $pixelLogs -Force | Out-Null
$pixelFaceWorker = Start-Process -FilePath $pixelPython -ArgumentList @('-u', 'manage.py', 'run_face_worker') -WorkingDirectory $pixelBackend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $pixelLogs 'faces.out.log') -RedirectStandardError (Join-Path $pixelLogs 'faces.err.log') -PassThru
Write-Output "PIXEL face matching worker started (PID $($pixelFaceWorker.Id))."
