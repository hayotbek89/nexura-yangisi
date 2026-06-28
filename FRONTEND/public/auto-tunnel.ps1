# NEXURA GPU Tunnel - Auto-start script
# VPS ga SSH tunnel ochib, local GPU ni ulaydi

$LOCAL_PORT = 11434
$VPS_PORT = 11435
$VPS_USER = "hayotbek"
$VPS_HOST = "185.191.141.247"
$SSH_KEY = "$env:USERPROFILE\.ssh\nexura-tunnel"
$LOG = "$env:USERPROFILE\.nexura-tunnel.log"

function Write-Log {
    param([string]$Msg)
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$time $Msg" | Out-File -FilePath $LOG -Append
}

Write-Log "NEXURA GPU Tunnel ishga tushdi"

while ($true) {
    Write-Log "Tunnel ochilmoqda: $VPS_PORT -> localhost:$LOCAL_PORT"
    ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=3 `
        -o ExitOnForwardFailure=yes `
        -i "$SSH_KEY" `
        -R "${VPS_PORT}:localhost:${LOCAL_PORT}" `
        -N `
        "${VPS_USER}@${VPS_HOST}" 2>&1 | ForEach-Object {
            Write-Log $_
        }
    
    $exitCode = $LASTEXITCODE
    Write-Log "Tunnel uzildi (exit code: $exitCode). 10 soniyadan keyin qayta ulanadi..."
    Start-Sleep -Seconds 10
}
