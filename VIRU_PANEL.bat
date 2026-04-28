@echo off
setlocal
set "ROOT=%~dp0"
set "LOG_DIR=%ROOT%logs"
set "WAN_OUT=%LOG_DIR%\wan_tunnel.out.log"
set "WAN_ERR=%LOG_DIR%\wan_tunnel.err.log"
set "WAN_PID=%LOG_DIR%\wan_tunnel.pid"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

:menu
echo.
echo ================================
echo         VIRU PANEL v2
echo ================================
echo 1. Iniciar VIRU (foreground)
echo 2. Detener VIRU
echo 3. Estado local (3000 / 8000)
echo 4. WAN START (tunel publico)
echo 5. WAN STATUS (URL activa)
echo 6. WAN STOP
echo 7. Ver logs tunel (ultimas 80 lineas)
echo 8. Salir
echo.
choice /C 12345678 /N /M "Opcion: "
if errorlevel 8 goto :eof
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
powershell -ExecutionPolicy Bypass -Command "$logDir='%LOG_DIR%'; $out='%WAN_OUT%'; $err='%WAN_ERR%'; $pidFile='%WAN_PID%'; if(Test-Path $pidFile){$existing=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if($existing -gt 0 -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)){Write-Host 'Ya existe un tunel WAN activo (PID' $existing '). Usa WAN STATUS.'; exit 0} else {Remove-Item $pidFile -Force -ErrorAction SilentlyContinue}}; if(Test-Path $out){Remove-Item $out -Force -ErrorAction SilentlyContinue}; if(Test-Path $err){Remove-Item $err -Force -ErrorAction SilentlyContinue}; $p=Start-Process -FilePath 'C:\Windows\System32\OpenSSH\ssh.exe' -ArgumentList @('-o','StrictHostKeyChecking=no','-o','ServerAliveInterval=30','-R','80:127.0.0.1:3000','nokey@localhost.run') -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden; Set-Content -Path $pidFile -Value $p.Id -Encoding ASCII; Start-Sleep -Seconds 6; $line=(Get-Content $out -ErrorAction SilentlyContinue | Where-Object {$_ -match 'https://[a-z0-9.-]+'} | Select-Object -Last 1); if($line){$m=[regex]::Match($line,'https://[a-z0-9.-]+'); if($m.Success){Write-Host ('WAN URL: ' + $m.Value); exit 0}}; Write-Host 'Tunel levantado, pero URL aun no visible. Usa WAN STATUS en 5-10s.'"
goto menu

:wan_status
powershell -ExecutionPolicy Bypass -Command "$pidFile='%WAN_PID%'; $out='%WAN_OUT%'; if(-not (Test-Path $pidFile)){Write-Host 'No hay PID de tunel. Usa WAN START.'; exit 1}; $pid=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if(-not (Get-Process -Id $pid -ErrorAction SilentlyContinue)){Write-Host 'El proceso de tunel no esta activo. Usa WAN START.'; exit 1}; $line=(Get-Content $out -ErrorAction SilentlyContinue | Where-Object {$_ -match 'https://[a-z0-9.-]+'} | Select-Object -Last 1); if($line){$m=[regex]::Match($line,'https://[a-z0-9.-]+'); if($m.Success){Write-Host ('Tunel activo (PID ' + $pid + ')'); Write-Host ('WAN URL: ' + $m.Value); exit 0}}; Write-Host ('Tunel activo (PID ' + $pid + '), sin URL detectada aun.');"
goto menu

:wan_stop
powershell -ExecutionPolicy Bypass -Command "$pidFile='%WAN_PID%'; if(-not (Test-Path $pidFile)){Write-Host 'No habia tunel WAN activo.'; exit 0}; $pid=[int](Get-Content $pidFile -ErrorAction SilentlyContinue); if($pid -gt 0){Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue; Write-Host 'Tunel WAN detenido.'"
goto menu

:wan_logs
powershell -ExecutionPolicy Bypass -Command "Write-Host '--- wan_tunnel.out.log ---'; Get-Content -Tail 80 '%WAN_OUT%' -ErrorAction SilentlyContinue; Write-Host '--- wan_tunnel.err.log ---'; Get-Content -Tail 80 '%WAN_ERR%' -ErrorAction SilentlyContinue"
goto menu
