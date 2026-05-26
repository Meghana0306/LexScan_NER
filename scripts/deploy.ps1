# LexScan — one-command Docker deploy (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

foreach ($dir in @("models\general_best_model", "models\medical_best_model", "models\legal_best_model")) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

$freeGb = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
if ($freeGb -lt 5) {
    Write-Warning "Low disk space on C: ($freeGb GB free). Docker needs at least 5 GB."
}

Write-Host "Building and starting LexScan containers..."
docker compose down --remove-orphans 2>$null
docker compose up -d --build

Write-Host "Waiting for API health..."
$ok = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep -Seconds 5 }
}
if (-not $ok) {
    Write-Host "API not healthy yet. Check: docker compose logs api"
    exit 1
}

Write-Host ""
Write-Host "LexScan is running:"
Write-Host "  API: http://localhost:8000/docs"
Write-Host "  UI:  http://localhost:7860"
docker compose ps
