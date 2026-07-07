$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsDir = Join-Path $root "tools"
$hostName = "127.0.0.1"
$port = 35000
$startupTimeoutSeconds = 20

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutMs = 800
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($async) | Out-Null
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

Set-Location $root

if (Test-TcpPort -HostName $hostName -Port $port) {
    throw (
        "Le port $hostName`:$port est deja occupe. " +
        "Fermez l'emulateur ou le service OBD deja actif avant de lancer ce script, " +
        "afin de garantir le scenario fake DTC attendu."
    )
} else {
    Write-Host "Demarrage de l'emulateur DTC..." -ForegroundColor Cyan
    $env:PYTHONPATH = $toolsDir
    $emulatorProcess = Start-Process python -ArgumentList @(
        ".\start_fake_dtc_emulator.py"
    ) -WorkingDirectory $toolsDir -PassThru

    $deadline = (Get-Date).AddSeconds($startupTimeoutSeconds)
    do {
        Start-Sleep -Milliseconds 500
        if ($emulatorProcess.HasExited) {
            throw "L'emulateur s'est ferme immediatement (code $($emulatorProcess.ExitCode)). Verifiez tools\\elm.log."
        }
        if (Test-TcpPort -HostName $hostName -Port $port) {
            Write-Host "Emulateur pret sur $hostName`:$port" -ForegroundColor Green
            break
        }
    } while ((Get-Date) -lt $deadline)

    if (-not (Test-TcpPort -HostName $hostName -Port $port)) {
        throw "L'emulateur n'a pas ouvert $hostName`:$port dans les $startupTimeoutSeconds secondes."
    }
}

Write-Host "Demarrage de l'application..." -ForegroundColor Cyan
Start-Process python -ArgumentList ".\main.py" -WorkingDirectory $root
