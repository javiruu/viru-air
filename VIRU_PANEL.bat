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
echo 4. PUBLICAR WEB ESTABLE
echo 5. ESTADO WEB ESTABLE
echo 6. DETENER WEB ESTABLE
echo 7. USAR TAILSCALE FUNNEL
echo 8. ESTADO TAILSCALE FUNNEL
echo 9. DETENER TAILSCALE FUNNEL
echo ----------------------------------------
echo A. Ver logs del tunel
echo ----------------------------------------
echo 0. Salir
echo.
choice /C 1234567890A /N /M "Opcion: "
if errorlevel 11 goto tunnel_logs
if errorlevel 10 goto :eof
if errorlevel 9 goto tailscale_stop
if errorlevel 8 goto tailscale_status
if errorlevel 7 goto tailscale_start
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

:tailscale_start
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\tailscale-funnel-start.ps1"
goto menu

:tailscale_status
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\tailscale-funnel-status.ps1"
goto menu

:tailscale_stop
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\tailscale-funnel-stop.ps1"
goto menu

:tunnel_logs
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\stable-tunnel-logs.ps1"
goto menu
