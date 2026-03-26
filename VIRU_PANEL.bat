@echo off
setlocal
:menu
echo.
echo ===== VIRU PANEL =====
echo 1. Iniciar (background)
echo 2. Iniciar (foreground)
echo 3. Detener
echo 4. Estado
echo 5. Ver logs (ultimas 50 lineas)
echo 6. Salir
echo.
choice /C 123456 /N /M "Opcion: "
if errorlevel 6 goto :eof
if errorlevel 5 goto logs
if errorlevel 4 goto status
if errorlevel 3 goto stop
if errorlevel 2 goto start_fg
if errorlevel 1 goto start_bg

goto :eof

:start_bg
powershell -ExecutionPolicy Bypass -File "%~dp0iniciar_viru.ps1"
goto menu

:start_fg
powershell -ExecutionPolicy Bypass -File "%~dp0iniciar_viru.ps1" -Foreground
goto menu

:stop
call "%~dp0PARAR_VIRU.bat"
goto menu

:status
powershell -ExecutionPolicy Bypass -Command "$ports=@(3000,8000); foreach($p in $ports){$c=Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue; if($c){Write-Host "Puerto" $p "OK"} else {Write-Host "Puerto" $p "OFF"}}"
goto menu

:logs
powershell -ExecutionPolicy Bypass -Command "Write-Host '--- backend.log ---'; Get-Content -Tail 50 backend\backend.log -ErrorAction SilentlyContinue; Write-Host '--- frontend.log ---'; Get-Content -Tail 50 frontend\frontend.log -ErrorAction SilentlyContinue"
goto menu
