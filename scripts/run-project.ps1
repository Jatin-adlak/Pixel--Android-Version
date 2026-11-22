param([switch]$FrontendProcess, [switch]$Phone, [string]$LanAddress)

$ErrorActionPreference = 'Stop'
$pixelRunRoot = Split-Path -Parent $PSScriptRoot
$pixelRunFrontend = Join-Path $pixelRunRoot 'frontend'
$pixelRunBackend = Join-Path $pixelRunRoot 'backend'
$pixelRunPython = Join-Path $pixelRunBackend '.venv\Scripts\python.exe'
$pixelRunLogs = Join-Path $pixelRunBackend '.local'

if ($FrontendProcess) {
    # Only the child process receives this setting. The launcher opens one tab
    # after both services are ready, instead of Expo opening an extra tab.
    $env:BROWSER = 'none'
    Set-Location -LiteralPath $pixelRunFrontend
    & npm.cmd run web -- --port 8081
    exit $LASTEXITCODE
}

function Test-PixelPort([int]$Port, [string]$Service) {
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    if (-not $listeners.Count) { return $false }
    foreach ($ownerId in ($listeners.OwningProcess | Select-Object -Unique)) {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $ownerId"
        $belongsToPixel = $false
        if ($Service -eq 'backend' -and $owner.CommandLine -match 'manage.py.*runserver') {
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId = $($owner.ParentProcessId)"
            $belongsToPixel = $owner.ExecutablePath -eq $pixelRunPython -or $parent.ExecutablePath -eq $pixelRunPython
        }
        elseif ($Service -eq 'frontend' -and $owner.CommandLine) {
            $belongsToPixel = $owner.CommandLine.Replace('/', '\').IndexOf($pixelRunFrontend, [StringComparison]::OrdinalIgnoreCase) -ge 0
        }
        if (-not $belongsToPixel) {
            throw "Port $Port is occupied by another program. Close that program or free the port, then run this launcher again."
        }
    }
    return $true
}

function Wait-PixelEndpoint([string]$Url, [string]$Service, [int]$TimeoutSeconds = 120) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $responseText = if ($response.Content -is [byte[]]) { [Text.Encoding]::UTF8.GetString($response.Content) } else { $response.Content }
                if ($Service -eq 'backend' -and ($responseText | ConvertFrom-Json).status -eq 'ok') { return }
                if ($Service -eq 'frontend' -and $responseText -match 'packager-status:running') { return }
            }
        }
        catch { }
        Start-Sleep -Milliseconds 500
    }
    throw "$Service did not become ready. See the log files in $pixelRunLogs."
}

function Start-PixelWorkers {
    $syncRunning = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
        $_.ExecutablePath -eq $pixelRunPython -and $_.CommandLine -match 'manage.py.*sync_event_media'
    })
    if (-not $syncRunning.Count) {
        Start-Process -FilePath $pixelRunPython -ArgumentList @('-u', 'manage.py', 'sync_event_media') -WorkingDirectory $pixelRunBackend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $pixelRunLogs 'sync.out.log') -RedirectStandardError (Join-Path $pixelRunLogs 'sync.err.log') | Out-Null
    }
    if (Test-Path -LiteralPath (Join-Path $pixelRunRoot 'face_recognition\models\face_recognition_sface_2021dec.onnx')) {
        & (Join-Path $PSScriptRoot 'start-face-worker.ps1')
    }
}

$pixelRunMutex = [Threading.Mutex]::new($false, 'Local\PIXEL.RunProject')
$pixelRunLocked = $false
try {
    try { $pixelRunLocked = $pixelRunMutex.WaitOne(0) }
    catch [Threading.AbandonedMutexException] { $pixelRunLocked = $true }
    if (-not $pixelRunLocked) {
        Write-Output 'PIXEL is already starting. Please wait for the browser to open.'
        exit 0
    }
    Write-Output 'Starting PIXEL...'
    foreach ($required in @($pixelRunPython, (Join-Path $pixelRunBackend '.env'), (Join-Path $pixelRunFrontend 'node_modules\expo\bin\cli'))) {
        if (-not (Test-Path -LiteralPath $required)) {
            throw "Required setup file is missing: $required. Complete project setup before using the launcher."
        }
    }
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue) -or -not (Get-Command node.exe -ErrorAction SilentlyContinue)) {
        throw 'Node.js and npm must be installed and available on PATH.'
    }
    New-Item -ItemType Directory -Path $pixelRunLogs -Force | Out-Null
    if ($Phone) {
        if (-not $LanAddress) {
            $lan = Get-NetIPConfiguration | Where-Object {
                $_.IPv4DefaultGateway -and $_.IPv4Address -and $_.NetAdapter.Status -eq 'Up'
            } | Sort-Object @{ Expression = { if ($_.InterfaceAlias -match 'Wi-Fi|Wireless|WLAN') { 0 } else { 1 } } }, InterfaceIndex | Select-Object -First 1
            $LanAddress = $lan.IPv4Address.IPAddress | Select-Object -First 1
        }
        $parsedAddress = $null
        if (-not [Net.IPAddress]::TryParse($LanAddress, [ref]$parsedAddress) -or $parsedAddress.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or [Net.IPAddress]::IsLoopback($parsedAddress) -or $LanAddress -eq '0.0.0.0') {
            throw 'No usable LAN IPv4 address was found. Connect to Wi-Fi, or run: "Run PIXEL Phone.bat" 192.168.1.10 (replace with your PC address).'
        }
        $phoneUrl = "http://${LanAddress}:8001"
        $phoneStatePath = Join-Path $pixelRunLogs 'phone-backend.json'
        $phoneBackendRunning = Test-PixelPort 8001 'backend'
        $phoneFrontendRunning = Test-PixelPort 8082 'frontend'
        # These settings affect this launcher and its children only; .env stays unchanged.
        $env:EXPO_PUBLIC_API_URL = $phoneUrl
        $env:REACT_NATIVE_PACKAGER_HOSTNAME = $LanAddress
        $env:BACKEND_URL = $phoneUrl
        $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,testserver,$LanAddress"
        $env:FRONTEND_URL = "http://${LanAddress}:8082"
        $env:EXPO_PUBLIC_WEB_URL = $env:FRONTEND_URL
        $env:CORS_ALLOWED_ORIGINS = "http://localhost:8081,http://localhost:8082,http://${LanAddress}:8082"
        $env:DJANGO_DEBUG = 'true'
        $env:BROWSER = 'none'
        if ($phoneBackendRunning) {
            $previousPhone = if (Test-Path -LiteralPath $phoneStatePath) { Get-Content -LiteralPath $phoneStatePath -Raw | ConvertFrom-Json } else { $null }
            if (-not $previousPhone -or $previousPhone.url -ne $phoneUrl) {
                throw 'Port 8001 already has a phone backend with an unknown or different LAN configuration. Close that backend before switching Wi-Fi addresses or running this launcher.'
            }
            Write-Output 'Reusing the PIXEL phone backend.'
        }
        else {
            $phoneServer = Start-Process -FilePath $pixelRunPython -ArgumentList @('-u', 'manage.py', 'runserver', '0.0.0.0:8001', '--noreload') -WorkingDirectory $pixelRunBackend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $pixelRunLogs 'phone-backend.out.log') -RedirectStandardError (Join-Path $pixelRunLogs 'phone-backend.err.log') -PassThru
            @{ url = $phoneUrl; pid = $phoneServer.Id } | ConvertTo-Json | Set-Content -LiteralPath $phoneStatePath
        }
        Wait-PixelEndpoint "$phoneUrl/health/" 'backend'
        Start-PixelWorkers
        Write-Output "Phone API: $phoneUrl"
        Write-Output "On your phone, check $phoneUrl/health/ if connection fails."
        if ($phoneFrontendRunning) {
            Wait-PixelEndpoint 'http://127.0.0.1:8082/status' 'frontend'
            Write-Output "Expo phone server is already running. Open exp://${LanAddress}:8082 in Expo Go and tap Try again."
            exit 0
        }
        Write-Output 'Connect your phone and computer to the same Wi-Fi. Open Expo Go and scan the QR below.'
        Write-Output 'Keep this CMD window open. Allow Node/Python on your private network if Windows prompts.'
        Write-Output 'Use an Expo Go version compatible with SDK 58. Google OAuth may require a development build.'
        # The Expo terminal stays visible inside the CMD launcher for scanning.
        $pixelRunMutex.ReleaseMutex()
        $pixelRunLocked = $false
        Set-Location -LiteralPath $pixelRunFrontend
        & npx.cmd expo start --go --lan --port 8082 --clear
        if ($LASTEXITCODE -ne 0) { throw "Expo exited with code $LASTEXITCODE." }
        exit 0
    }
    # Check both ports before starting anything, and never stop an unrelated process.
    $backendRunning = Test-PixelPort 8000 'backend'
    $frontendRunning = Test-PixelPort 8081 'frontend'
    if (-not $backendRunning) {
        & (Join-Path $PSScriptRoot 'start-backend.ps1')
    }
    else { Write-Output 'Reusing the running PIXEL backend.' }
    Wait-PixelEndpoint 'http://127.0.0.1:8000/health/' 'backend'

    Start-PixelWorkers
    if (-not $frontendRunning) {
        Write-Output 'Starting the PIXEL frontend...'
        Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'RemoteSigned', '-File', ('"{0}"' -f $PSCommandPath), '-FrontendProcess') -WorkingDirectory $pixelRunRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $pixelRunLogs 'frontend.out.log') -RedirectStandardError (Join-Path $pixelRunLogs 'frontend.err.log') | Out-Null
    }
    else { Write-Output 'Reusing the running PIXEL frontend.' }
    Wait-PixelEndpoint 'http://127.0.0.1:8081/status' 'frontend'
    Write-Output 'PIXEL is ready at http://localhost:8081. Opening your browser...'
    Start-Process 'http://localhost:8081'
}
catch {
    Write-Host "PIXEL startup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    if ($pixelRunLocked) { $pixelRunMutex.ReleaseMutex() }
    $pixelRunMutex.Dispose()
}
