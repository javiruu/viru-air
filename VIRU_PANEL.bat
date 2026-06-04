@echo off
setlocal
set "ROOT=%~dp0"
set "LOG_DIR=%ROOT%logs"
set "PUBLIC_OUT=%LOG_DIR%\public_temp_tunnel.out.log"
set "PUBLIC_ERR=%LOG_DIR%\public_temp_tunnel.err.log"
set "PUBLIC_PID=%LOG_DIR%\public_temp_tunnel.pid"
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
echo C. Ver logs DuckDNS updater
echo D. Forzar update DuckDNS
echo E. PUBLICAR RAPIDO (local + URL temporal)
echo ----------------------------------------
echo 0. Salir
echo.
choice /C 1234567890ABCDE /N /M "Opcion: "
if errorlevel 15 goto public_quick_start
if errorlevel 14 goto duckdns_force_update
if errorlevel 13 goto duckdns_logs
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
powershell -ExecutionPolicy Bypass -Command "$ports=@(3000,8000); foreach($p in $ports){$c=Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue; foreach($i in $c){try{Stop-Process -Id $i.OwningProcess -Force -ErrorAction SilentlyContinue}catch{}}}; Write-Host 'Puertos 3000/8000 detenidos (si estaban activos).'"
goto menu

:status
powershell -ExecutionPolicy Bypass -Command "$ports=@(3000,8000); foreach($p in $ports){$c=Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue; if($c){Write-Host "Puerto" $p "OK"} else {Write-Host "Puerto" $p "OFF"}}"
goto menu

:public_start
powershell -ExecutionPolicy Bypass -Command "$out='%PUBLIC_OUT%'; $err='%PUBLIC_ERR%'; $pidFile='%PUBLIC_PID%'; if(Test-Path $pidFile){$existing=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if($existing -gt 0 -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)){Write-Host 'Ya existe una URL temporal activa (PID' $existing '). Usa PUBLICO TEMPORAL STATUS.'; exit 0} else {Remove-Item $pidFile -Force -ErrorAction SilentlyContinue}}; if(Test-Path $out){Remove-Item $out -Force -ErrorAction SilentlyContinue}; if(Test-Path $err){Remove-Item $err -Force -ErrorAction SilentlyContinue}; $cmd = '$ErrorActionPreference=''SilentlyContinue''; ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:127.0.0.1:3000 nokey@localhost.run 2>&1 | Tee-Object -FilePath ''%PUBLIC_OUT%'' -Append'; $p=Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit','-ExecutionPolicy','Bypass','-Command',$cmd) -PassThru; Set-Content -Path $pidFile -Value $p.Id -Encoding ASCII; $url=''; for($i=0;$i -lt 20;$i++){Start-Sleep -Milliseconds 500; $line=(Get-Content $out -ErrorAction SilentlyContinue | Where-Object {$_ -match 'https://[^ ]+'} | Select-Object -Last 1); if($line){$m=[regex]::Match($line,'https://[^ ]+'); if($m.Success){$url=$m.Value; break}}}; if($url){Write-Host ('URL temporal: ' + $url)} else {Write-Host 'Tunel temporal abierto. Espera 3-10s y usa PUBLICO TEMPORAL STATUS para ver la URL real.'}"
goto menu

:public_status
powershell -ExecutionPolicy Bypass -Command "$pidFile='%PUBLIC_PID%'; $out='%PUBLIC_OUT%'; if(-not (Test-Path $pidFile)){Write-Host 'No hay URL temporal activa. Usa PUBLICO TEMPORAL START.'; exit 1}; $tpid=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if(-not (Get-Process -Id $tpid -ErrorAction SilentlyContinue)){Write-Host 'El proceso temporal no esta activo. Usa PUBLICO TEMPORAL START.'; exit 1}; $line=(Get-Content $out -ErrorAction SilentlyContinue | Where-Object {$_ -match 'https://[^ ]+'} | Select-Object -Last 1); if($line){$m=[regex]::Match($line,'https://[^ ]+'); if($m.Success){Write-Host ('Tunel temporal activo (PID ' + $tpid + ')'); Write-Host ('URL temporal: ' + $m.Value); exit 0}}; Write-Host ('Tunel temporal activo (PID ' + $tpid + '), sin URL detectada aun.');"
goto menu

:public_stop
powershell -ExecutionPolicy Bypass -Command "$pidFile='%PUBLIC_PID%'; if(-not (Test-Path $pidFile)){Write-Host 'No habia URL temporal activa.'; exit 0}; $tpid=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if($tpid -gt 0){Stop-Process -Id $tpid -Force -ErrorAction SilentlyContinue}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue; Write-Host 'Tunel temporal detenido.'"
goto menu

:public_logs
powershell -ExecutionPolicy Bypass -Command "Write-Host '--- public_temp_tunnel.out.log ---'; Get-Content -Tail 80 '%PUBLIC_OUT%' -ErrorAction SilentlyContinue; Write-Host '--- public_temp_tunnel.err.log ---'; Get-Content -Tail 80 '%PUBLIC_ERR%' -ErrorAction SilentlyContinue"
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

:duckdns_logs
powershell -ExecutionPolicy Bypass -Command "Write-Host '--- duckdns-update.log ---'; Get-Content -Tail 40 '%DUCKDNS_LOG%' -ErrorAction SilentlyContinue"
goto menu

:duckdns_force_update
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\duckdns-update.ps1"
goto menu

:public_quick_start
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_viru_publico.ps1"
goto menu
