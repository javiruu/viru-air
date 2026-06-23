@echo off
setlocal
set "ROOT=%~dp0"

:menu
echo.
echo ================================
echo         VIRU PANEL v4
echo ================================
echo 1. Iniciar VIRU (foreground)
echo 2. Detener VIRU
echo 3. Estado local (3000 / 8000)
echo 4. PUBLICAR WEB
echo 5. ESTADO WEB PUBLICA
echo 6. DETENER WEB PUBLICA
echo 7. VER LOGS PUBLICACION
echo ----------------------------------------
echo 0. Salir
echo.
choice /C 12345670 /N /M "Opcion: "
if errorlevel 8 goto :eof
if errorlevel 7 goto tunnel_logs
if errorlevel 6 goto public_stable_stop
if errorlevel 5 goto public_stable_status
if errorlevel 4 goto public_stable_start
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

:public_stable_start
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-stable-start.ps1"
goto menu

:public_stable_status
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-stable-status.ps1"
goto menu

:public_stable_stop
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-stable-stop.ps1"
goto menu

:tunnel_logs
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\stable-tunnel-logs.ps1"
goto menu
