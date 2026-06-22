@echo off
setlocal
set "ROOT=%~dp0"
set "LOG_DIR=%ROOT%logs"
set "REMODEX_OUT=%LOG_DIR%\remodex.out.log"
set "REMODEX_ERR=%LOG_DIR%\remodex.err.log"
set "REMODEX_PID=%LOG_DIR%\remodex.pid"
set "DUCKDNS_LOG=%LOG_DIR%\duckdns-update.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

:menu
echo.
echo ================================
echo         VIRU PANEL v3
echo ================================
echo 1. Iniciar VIRU (foreground)
echo 2. Detener VIRU
echo 3. Estado local (3000 / 8000)
echo 4. PUBLICO TEMPORAL START
echo 5. PUBLICO TEMPORAL STATUS
echo 6. PUBLICO TEMPORAL STOP
echo 7. Ver logs publico temporal
echo 8. REMODEX START (background)
echo 9. REMODEX STOP
echo ----------------------------------------
echo A. DUCKDNS SETUP
echo B. DUCKDNS STATUS
echo C. DUCKDNS ENABLE
echo D. DUCKDNS DISABLE
echo E. Ver logs DuckDNS updater
echo F. Forzar update DuckDNS
echo G. PREFLIGHT PUBLICACION ESTABLE
echo H. CADDY START
echo I. CADDY STATUS
echo J. CADDY STOP
echo K. PUBLICAR RAPIDO (local + URL temporal)
echo ----------------------------------------
echo 0. Salir
echo.
choice /C 1234567890ABCDEFGHIJK /N /M "Opcion: "
if errorlevel 21 goto public_quick_start
if errorlevel 20 goto caddy_stop
if errorlevel 19 goto caddy_status
if errorlevel 18 goto caddy_start
if errorlevel 17 goto public_preflight
if errorlevel 16 goto duckdns_force_update
if errorlevel 15 goto duckdns_logs
if errorlevel 14 goto duckdns_disable
if errorlevel 13 goto duckdns_enable
if errorlevel 12 goto duckdns_status
if errorlevel 11 goto duckdns_setup
if errorlevel 10 goto :eof
if errorlevel 9 goto remodex_stop
if errorlevel 8 goto remodex_start
if errorlevel 7 goto public_logs
if errorlevel 6 goto public_stop
if errorlevel 5 goto public_status
if errorlevel 4 goto public_start
if errorlevel 3 goto status
if errorlevel 2 goto stop
if errorlevel 1 goto start_fg

goto :eof

:start_fg
powershell -ExecutionPolicy Bypass -File "%~dp0iniciar_viru.ps1" -Foreground
goto menu

:stop
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\viru-local-stop.ps1"
goto menu

:status
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\viru-local-status.ps1"
goto menu

:public_start
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-temp-start.ps1"
goto menu

:public_status
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-temp-status.ps1"
goto menu

:public_stop
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-temp-stop.ps1"
goto menu

:public_logs
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-temp-logs.ps1"
goto menu

:remodex_start
powershell -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $pidFile='%REMODEX_PID%'; $out='%REMODEX_OUT%'; $err='%REMODEX_ERR%'; $cmd=Get-Command remodex -ErrorAction SilentlyContinue; if(-not $cmd){Write-Host 'remodex no esta instalado o no esta en PATH. Instala/actualiza con: npm install -g remodex@latest'; exit 1}; if(Test-Path $pidFile){$raw=(Get-Content $pidFile -Raw -ErrorAction SilentlyContinue).Trim(); $existing=0; [void][int]::TryParse($raw,[ref]$existing); if($existing -gt 0 -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)){Write-Host ('Remodex ya esta activo (PID ' + $existing + ').'); exit 0}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue}; if(Test-Path $out){Remove-Item $out -Force -ErrorAction SilentlyContinue}; if(Test-Path $err){Remove-Item $err -Force -ErrorAction SilentlyContinue}; $p=Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-Command','remodex up') -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru; Start-Sleep -Seconds 2; if($p.HasExited){Write-Host ('Remodex no pudo iniciarse (exit ' + $p.ExitCode + '). Revisa logs en: ' + $err); exit 1}; Set-Content -Path $pidFile -Value $p.Id -Encoding ASCII; Write-Host ('Remodex iniciado en background (PID ' + $p.Id + ').')"
goto menu

:remodex_stop
powershell -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $pidFile='%REMODEX_PID%'; if(-not (Test-Path $pidFile)){Write-Host 'No habia PID de remodex. Nada que detener.'; exit 0}; $raw=(Get-Content $pidFile -Raw -ErrorAction SilentlyContinue).Trim(); $tpid=0; [void][int]::TryParse($raw,[ref]$tpid); if($tpid -gt 0){$proc=Get-Process -Id $tpid -ErrorAction SilentlyContinue; if($proc){Stop-Process -Id $tpid -Force -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 300; if(Get-Process -Id $tpid -ErrorAction SilentlyContinue){Write-Host ('No se pudo detener remodex (PID ' + $tpid + '). Revisa permisos.'); exit 1}; Write-Host ('Remodex detenido (PID ' + $tpid + ').')} else {Write-Host 'PID guardado no estaba activo; limpiando estado.'}} else {Write-Host 'PID invalido; limpiando estado.'}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue"
goto menu

:duckdns_setup
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\setup-duckdns.ps1"
goto menu

:duckdns_status
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\duckdns-status.ps1"
goto menu

:duckdns_enable
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\duckdns-enable.ps1"
goto menu

:duckdns_disable
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\duckdns-disable.ps1"
goto menu

:duckdns_logs
powershell -ExecutionPolicy Bypass -Command "Write-Host '--- duckdns-update.log ---'; Get-Content -Tail 40 '%DUCKDNS_LOG%' -ErrorAction SilentlyContinue"
goto menu

:duckdns_force_update
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\duckdns-update.ps1"
goto menu

:public_preflight
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-domain-preflight.ps1"
goto menu

:caddy_start
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\caddy-start.ps1"
goto menu

:caddy_status
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\caddy-status.ps1"
goto menu

:caddy_stop
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\caddy-stop.ps1"
goto menu

:public_quick_start
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_viru_publico.ps1"
goto menu
