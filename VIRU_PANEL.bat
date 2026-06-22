@echo off
setlocal
set "ROOT=%~dp0"
set "LOG_DIR=%ROOT%logs"
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
echo 4. PUBLICAR WEB ESTABLE
echo 5. ESTADO WEB ESTABLE
echo 6. DETENER WEB ESTABLE
echo 7. PUBLICO TEMPORAL START
echo 8. PUBLICO TEMPORAL STATUS
echo 9. PUBLICO TEMPORAL STOP
echo ----------------------------------------
echo A. Ver logs publico temporal
echo B. DUCKDNS SETUP
echo C. DUCKDNS STATUS
echo D. DUCKDNS ENABLE
echo E. DUCKDNS DISABLE
echo F. Ver logs DuckDNS updater
echo G. Forzar update DuckDNS
echo H. PUBLICAR RAPIDO (local + URL temporal)
echo I. GUARDAR ESTA RED COMO PERFIL WEB ESTABLE
echo J. VER PERFILES WEB ESTABLE
echo ----------------------------------------
echo 0. Salir
echo.
choice /C 1234567890ABCDEFGHIJ /N /M "Opcion: "
if errorlevel 20 goto stable_profiles
if errorlevel 19 goto stable_profile_save
if errorlevel 18 goto public_quick_start
if errorlevel 17 goto duckdns_force_update
if errorlevel 16 goto duckdns_logs
if errorlevel 15 goto duckdns_disable
if errorlevel 14 goto duckdns_enable
if errorlevel 13 goto duckdns_status
if errorlevel 12 goto duckdns_setup
if errorlevel 11 goto public_logs
if errorlevel 10 goto :eof
if errorlevel 9 goto public_stop
if errorlevel 8 goto public_status
if errorlevel 7 goto public_start
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

:public_stable_start
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-stable-start.ps1"
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

:public_stable_status
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-stable-status.ps1"
goto menu

:public_stable_stop
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-stable-stop.ps1"
goto menu

:public_quick_start
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_viru_publico.ps1"
goto menu

:stable_profile_save
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-stable-profile-save.ps1"
goto menu

:stable_profiles
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\public-stable-profiles.ps1"
goto menu
