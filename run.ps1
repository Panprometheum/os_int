# osint/run.ps1
# Launcher: start the PHP server, optional tunnel, open the dashboard.
param(
    [int]$Port = 8080,
    [switch]$Tunnel,       # use ngrok if available
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$docroot = Join-Path $root "grabber"

Write-Host "=== OSINT Console ===" -ForegroundColor Magenta
Write-Host "Docroot : $docroot"

# 1. Make sure PHP is available
$php = Get-Command php -ErrorAction SilentlyContinue
if (-not $php) { Write-Host "[!] PHP not found in PATH." -ForegroundColor Red; exit 1 }

# 2. Make sure the logs folder exists
$logs = Join-Path $docroot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

# 3. Tunnel (optional)
$url = "http://localhost:$Port/dashboard.php"
if ($Tunnel) {
    $ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
    if ($ngrok) {
        Write-Host "[*] Starting ngrok..." -ForegroundColor Yellow
        Start-Process -WindowStyle Minimized ngrok -ArgumentList "http $Port"
        Start-Sleep -Seconds 3
        try {
            $api = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 5
            $pub = ($api.tunnels | Where-Object { $_.proto -eq 'https' } | Select-Object -First 1).public_url
            if ($pub) {
                Write-Host "[+] Public : $pub/dashboard.php" -ForegroundColor Green
                Write-Host "[+] Landing: $pub/" -ForegroundColor Green
            }
        } catch { Write-Host "[!] Failed to fetch ngrok URL (check http://127.0.0.1:4040)" -ForegroundColor Yellow }
    } else {
        Write-Host "[!] ngrok not found. Install it from ngrok.com or continue on localhost." -ForegroundColor Yellow
    }
}

# 4. Open browser
if (-not $NoBrowser) { Start-Process $url }

# 5. Start server (blocking — do not close this window)
Write-Host "[*] Server running at http://localhost:$Port" -ForegroundColor Cyan
Write-Host "    Dashboard: $url"
Write-Host "    Landing  : http://localhost:$Port/"
Write-Host "    Press CTRL+C to stop." -ForegroundColor DarkGray
Write-Host ""
& php -S "localhost:$Port" -t $docroot
