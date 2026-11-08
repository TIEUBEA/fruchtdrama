$ErrorActionPreference = 'Stop'
$studioRoot = $PSScriptRoot
$studioPython = (Get-Command python -ErrorAction Stop).Source
$studioAddress = 'http://127.0.0.1:8840'
$studioRunning = $false
try {
    $studioResponse = Invoke-RestMethod -Uri "$studioAddress/api/state" -TimeoutSec 2
    $studioLocalState = Get-Content -LiteralPath (Join-Path $studioRoot 'data/state.json') -Raw | ConvertFrom-Json
    $studioRunning = $studioLocalState.pair_code -and ($studioResponse.pair_code -eq $studioLocalState.pair_code)
} catch {}
if (-not $studioRunning) {
    New-Item -ItemType Directory -Force -Path (Join-Path $studioRoot 'data') | Out-Null
    Start-Process -FilePath $studioPython -ArgumentList @('"' + (Join-Path $studioRoot 'server.py') + '"') -WorkingDirectory $studioRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $studioRoot 'data/server.log') -RedirectStandardError (Join-Path $studioRoot 'data/server-errors.log')
    for ($studioAttempt = 0; $studioAttempt -lt 20; $studioAttempt++) {
        Start-Sleep -Milliseconds 250
        try { Invoke-RestMethod -Uri "$studioAddress/api/state" -TimeoutSec 1 | Out-Null; break } catch {}
    }
}
Start-Process $studioAddress
