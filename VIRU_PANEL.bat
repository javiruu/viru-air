@echo off
setlocal
set "ROOT=%~dp0"
set "LOG_DIR=%ROOT%logs"
set "WAN_OUT=%LOG_DIR%\wan_tunnel.out.log"
set "WAN_ERR=%LOG_DIR%\wan_tunnel.err.log"
set "WAN_PID=%LOG_DIR%\wan_tunnel.pid"
set "REMODEX_OUT=%LOG_DIR%\remodex.out.log"
set "REMODEX_ERR=%LOG_DIR%\remodex.err.log"
set "REMODEX_PID=%LOG_DIR%\remodex.pid"
set "CF_OUT=%LOG_DIR%\cf_tunnel.out.log"
set "CF_ERR=%LOG_DIR%\cf_tunnel.err.log"
set "CF_PID=%LOG_DIR%\cf_tunnel.pid"
set "CF_CONFIG=%ROOT%infra\cloudflared-config.local.yml"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

:menu
echo.
echo ================================
echo         VIRU PANEL v3
echo ================================
echo 1. Iniciar VIRU (foreground)
echo 2. Detener VIRU
echo 3. Estado local (3000 / 8000)
echo 4. WAN START (tunel publico)
echo 5. WAN STATUS (URL activa)
echo 6. WAN STOP
echo 7. Ver logs tunel (ultimas 80 lineas)
echo 8. REMODEX START (background)
echo 9. REMODEX STOP
echo ----------------------------------------
echo A. CF TUNNEL START (viruair.dpdns.org)
echo B. CF TUNNEL STATUS
echo C. CF TUNNEL STOP
echo D. Ver logs CF tunnel
echo ----------------------------------------
echo 0. Salir
echo.
choice /C 1234567890ABCD /N /M "Opcion: "
if errorlevel 14 goto cf_logs
if errorlevel 13 goto cf_stop
if errorlevel 12 goto cf_status
if errorlevel 11 goto cf_start
if errorlevel 10 goto :eof
if errorlevel 9 goto remodex_stop
if errorlevel 8 goto remodex_start
if errorlevel 7 goto wan_logs
if errorlevel 6 goto wan_stop
if errorlevel 5 goto wan_status
if errorlevel 4 goto wan_start
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

:wan_start
powershell -ExecutionPolicy Bypass -Command "$out='%WAN_OUT%'; $err='%WAN_ERR%'; $pidFile='%WAN_PID%'; if(Test-Path $pidFile){$existing=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if($existing -gt 0 -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)){Write-Host 'Ya existe un tunel WAN activo (PID' $existing '). Usa WAN STATUS.'; exit 0} else {Remove-Item $pidFile -Force -ErrorAction SilentlyContinue}}; if(Test-Path $out){Remove-Item $out -Force -ErrorAction SilentlyContinue}; if(Test-Path $err){Remove-Item $err -Force -ErrorAction SilentlyContinue}; $cmd = '$ErrorActionPreference=''SilentlyContinue''; ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:127.0.0.1:3000 nokey@localhost.run 2>&1 | Tee-Object -FilePath ''%WAN_OUT%'' -Append'; $p=Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit','-ExecutionPolicy','Bypass','-Command',$cmd) -PassThru; Set-Content -Path $pidFile -Value $p.Id -Encoding ASCII; $url=''; for($i=0;$i -lt 20;$i++){Start-Sleep -Milliseconds 500; $line=(Get-Content $out -ErrorAction SilentlyContinue | Where-Object {$_ -match 'https://[a-z0-9-]+\.[a-z]{3}\.life'} | Select-Object -Last 1); if($line){$m=[regex]::Match($line,'https://[a-z0-9-]+\.[a-z]{3}\.life'); if($m.Success){$url=$m.Value; break}}}; if($url){Write-Host ('WAN URL: ' + $url)} else {Write-Host 'Tunel foreground abierto. Espera 3-10s y usa WAN STATUS para ver URL real.'}"
goto menu

:wan_status
powershell -ExecutionPolicy Bypass -Command "$pidFile='%WAN_PID%'; $out='%WAN_OUT%'; if(-not (Test-Path $pidFile)){Write-Host 'No hay PID de tunel. Usa WAN START.'; exit 1}; $tpid=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if(-not (Get-Process -Id $tpid -ErrorAction SilentlyContinue)){Write-Host 'El proceso de tunel no esta activo. Usa WAN START.'; exit 1}; $line=(Get-Content $out -ErrorAction SilentlyContinue | Where-Object {$_ -match 'https://[a-z0-9-]+\.[a-z]{3}\.life'} | Select-Object -Last 1); if($line){$m=[regex]::Match($line,'https://[a-z0-9-]+\.[a-z]{3}\.life'); if($m.Success){Write-Host ('Tunel activo (PID ' + $tpid + ')'); Write-Host ('WAN URL: ' + $m.Value); exit 0}}; Write-Host ('Tunel activo (PID ' + $tpid + '), sin URL real detectada aun.');"
goto menu

:wan_stop
powershell -ExecutionPolicy Bypass -Command "$pidFile='%WAN_PID%'; if(-not (Test-Path $pidFile)){Write-Host 'No habia tunel WAN activo.'; exit 0}; $tpid=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if($tpid -gt 0){Stop-Process -Id $tpid -Force -ErrorAction SilentlyContinue}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue; Write-Host 'Tunel WAN detenido.'"
goto menu

:wan_logs
powershell -ExecutionPolicy Bypass -Command "Write-Host '--- wan_tunnel.out.log ---'; Get-Content -Tail 80 '%WAN_OUT%' -ErrorAction SilentlyContinue; Write-Host '--- wan_tunnel.err.log ---'; Get-Content -Tail 80 '%WAN_ERR%' -ErrorAction SilentlyContinue"
goto menu

:remodex_start
powershell -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $pidFile='%REMODEX_PID%'; $out='%REMODEX_OUT%'; $err='%REMODEX_ERR%'; $cmd=Get-Command remodex -ErrorAction SilentlyContinue; if(-not $cmd){Write-Host 'remodex no esta instalado o no esta en PATH. Instala/actualiza con: npm install -g remodex@latest'; exit 1}; if(Test-Path $pidFile){$raw=(Get-Content $pidFile -Raw -ErrorAction SilentlyContinue).Trim(); $existing=0; [void][int]::TryParse($raw,[ref]$existing); if($existing -gt 0 -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)){Write-Host ('Remodex ya esta activo (PID ' + $existing + ').'); exit 0}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue}; if(Test-Path $out){Remove-Item $out -Force -ErrorAction SilentlyContinue}; if(Test-Path $err){Remove-Item $err -Force -ErrorAction SilentlyContinue}; $p=Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-Command','remodex up') -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru; Start-Sleep -Seconds 2; if($p.HasExited){Write-Host ('Remodex no pudo iniciarse (exit ' + $p.ExitCode + '). Revisa logs en: ' + $err); exit 1}; Set-Content -Path $pidFile -Value $p.Id -Encoding ASCII; Write-Host ('Remodex iniciado en background (PID ' + $p.Id + ').')"
goto menu

:remodex_stop
powershell -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $pidFile='%REMODEX_PID%'; if(-not (Test-Path $pidFile)){Write-Host 'No habia PID de remodex. Nada que detener.'; exit 0}; $raw=(Get-Content $pidFile -Raw -ErrorAction SilentlyContinue).Trim(); $tpid=0; [void][int]::TryParse($raw,[ref]$tpid); if($tpid -gt 0){$proc=Get-Process -Id $tpid -ErrorAction SilentlyContinue; if($proc){Stop-Process -Id $tpid -Force -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 300; if(Get-Process -Id $tpid -ErrorAction SilentlyContinue){Write-Host ('No se pudo detener remodex (PID ' + $tpid + '). Revisa permisos.'); exit 1}; Write-Host ('Remodex detenido (PID ' + $tpid + ').')} else {Write-Host 'PID guardado no estaba activo; limpiando estado.'}} else {Write-Host 'PID invalido; limpiando estado.'}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue"
goto menu

:cf_start
powershell -ExecutionPolicy Bypass -Command "$out='%CF_OUT%'; $err='%CF_ERR%'; $pidFile='%CF_PID%'; $config='%CF_CONFIG%'; if(-not (Test-Path $config)){Write-Host 'Config no encontrado: ' $config; Write-Host 'Ejecuta primero: powershell -File scripts\\setup-cloudflared.ps1'; exit 1}; $cf=Get-Command cloudflared -ErrorAction SilentlyContinue; if(-not $cf){Write-Host 'cloudflared no esta instalado.'; Write-Host 'Ejecuta: powershell -File scripts\\setup-cloudflared.ps1'; exit 1}; if(Test-Path $pidFile){$existing=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if($existing -gt 0 -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)){Write-Host ('CF Tunnel ya activo (PID ' + $existing + '). Usa CF TUNNEL STATUS.'); exit 0} else {Remove-Item $pidFile -Force -ErrorAction SilentlyContinue}}; if(Test-Path $out){Remove-Item $out -Force -ErrorAction SilentlyContinue}; if(Test-Path $err){Remove-Item $err -Force -ErrorAction SilentlyContinue}; Write-Host 'Iniciando Cloudflare Tunnel...'; Write-Host ('Dominio: viruair.dpdns.org'); Write-Host ('Config:  ' + $config); if((Get-Content $config -Raw) -match 'YOUR_TUNNEL_ID'){Write-Host 'ERROR: El archivo de config tiene valores placeholder.'; Write-Host 'Ejecuta primero: powershell -File scripts\\setup-cloudflared.ps1'; exit 1}; $p=Start-Process -FilePath 'cloudflared.exe' -ArgumentList @('tunnel','--config',$config,'run') -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru; Start-Sleep -Seconds 3; if($p.HasExited){Write-Host ('ERROR: Tunnel fallo (exit ' + $p.ExitCode + '). Revisa logs con opcion D.'); $errContent=Get-Content $err -ErrorAction SilentlyContinue; if($errContent){Write-Host '--- stderr ---'; $errContent | Select-Object -Last 15}; exit 1}; Set-Content -Path $pidFile -Value $p.Id -Encoding ASCII; Start-Sleep -Seconds 5; $outContent=Get-Content $out -ErrorAction SilentlyContinue; $connected=$outContent | Where-Object {$_ -match 'Registered tunnel connection'}; if($connected){Write-Host ('CF Tunnel ONLINE (PID ' + $p.Id + ')'); Write-Host 'URL: https://viruair.dpdns.org'} else {Write-Host ('CF Tunnel iniciado (PID ' + $p.Id + '). Esperando conexion...'); Write-Host 'Usa CF TUNNEL STATUS en unos segundos.'}"
goto menu

:cf_status
powershell -ExecutionPolicy Bypass -Command "$pidFile='%CF_PID%'; $out='%CF_OUT%'; if(-not (Test-Path $pidFile)){Write-Host 'CF Tunnel no esta activo. Usa CF TUNNEL START.'; exit 1}; $tpid=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if(-not (Get-Process -Id $tpid -ErrorAction SilentlyContinue)){Write-Host 'CF Tunnel no esta corriendo (PID ' + $tpid + ' muerto). Usa CF TUNNEL START.'; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue; exit 1}; Write-Host ('CF Tunnel ACTIVO (PID ' + $tpid + ')'); Write-Host 'Dominio: https://viruair.dpdns.org'; $outContent=Get-Content $out -ErrorAction SilentlyContinue; $connected=$outContent | Where-Object {$_ -match 'Registered tunnel connection'}; if($connected){$latest=$connected | Select-Object -Last 1; Write-Host ('Estado:  CONNECTED - ' + $latest)} else {Write-Host 'Estado:  Conectando... (revisa logs con opcion D)'}"
goto menu

:cf_stop
powershell -ExecutionPolicy Bypass -Command "$pidFile='%CF_PID%'; if(-not (Test-Path $pidFile)){Write-Host 'CF Tunnel no esta activo.'; exit 0}; $tpid=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if($tpid -gt 0){Stop-Process -Id $tpid -Force -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 500; if(Get-Process -Id $tpid -ErrorAction SilentlyContinue){Write-Host ('No se pudo detener CF Tunnel (PID ' + $tpid + ').'); exit 1}; Write-Host ('CF Tunnel detenido (PID ' + $tpid + ').')}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue"
goto menu

:cf_logs
powershell -ExecutionPolicy Bypass -Command "Write-Host '--- cf_tunnel.out.log (ultimas 40 lineas) ---'; Get-Content -Tail 40 '%CF_OUT%' -ErrorAction SilentlyContinue; Write-Host '--- cf_tunnel.err.log (ultimas 40 lineas) ---'; Get-Content -Tail 40 '%CF_ERR%' -ErrorAction SilentlyContinue"
goto menu
