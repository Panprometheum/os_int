# osint/run.ps1
# Launcher: nyalain server PHP, tunnel opsional, buka dashboard.
param(
    [int]$Port = 8080,
    [switch]$Tunnel,       # pakai ngrok kalau ada
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$docroot = Join-Path $root "grabber"

Write-Host "=== OSINT Console ===" -ForegroundColor Magenta
Write-Host "Docroot : $docroot"

# 1. Pastikan PHP ada
$php = Get-Command php -ErrorAction SilentlyContinue
if (-not $php) { Write-Host "[!] PHP tidak ditemukan di PATH." -ForegroundColor Red; exit 1 }

# 2. Pastikan folder logs ada
$logs = Join-Path $docroot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

# 3. Tunnel (opsional)
$url = "http://localhost:$Port/dashboard.php"
if ($Tunnel) {
    $ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
    if ($ngrok) {
        Write-Host "[*] Menyalakan ngrok..." -ForegroundColor Yellow
        Start-Process -WindowStyle Minimized ngrok -ArgumentList "http $Port"
        Start-Sleep -Seconds 3
        try {
            $api = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 5
            $pub = ($api.tunnels | Where-Object { $_.proto -eq 'https' } | Select-Object -First 1).public_url
            if ($pub) {
                Write-Host "[+] Public : $pub/dashboard.php" -ForegroundColor Green
                Write-Host "[+] Landing: $pub/" -ForegroundColor Green
            }
        } catch { Write-Host "[!] Gagal ambil URL ngrok (cek http://127.0.0.1:4040)" -ForegroundColor Yellow }
    } else {
        Write-Host "[!] ngrok tidak ada. Install dari ngrok.com atau lanjut localhost." -ForegroundColor Yellow
    }
}

# 4. Buka browser
if (-not $NoBrowser) { Start-Process $url }

# 5. Nyalain server (blocking — jangan close window ini)
Write-Host "[*] Server jalan di http://localhost:$Port" -ForegroundColor Cyan
Write-Host "    Dashboard: $url"
Write-Host "    Landing  : http://localhost:$Port/"
Write-Host "    Tekan CTRL+C untuk stop." -ForegroundColor DarkGray
Write-Host ""
& php -S "localhost:$Port" -t $docroot
