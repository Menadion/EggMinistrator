@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title EggMinistrator stop

rem ===================================================================
rem  Stops what run-eggministrator.bat started.
rem
rem    stop-eggministrator.bat            listener + dashboard + backend
rem    stop-eggministrator.bat listener   only the classifier, which frees
rem                                       the webcam for ai\capture.py
rem    stop-eggministrator.bat dashboard  only the dashboard
rem    stop-eggministrator.bat backend    only the backend
rem    stop-eggministrator.bat mysql      MySQL, only if you ask for it
rem
rem  MySQL is NOT stopped by default, on purpose. XAMPP's MySQL is shared
rem  with the D.H-Azada work, and stopping the database to shut down an
rem  egg station would take that down with it.
rem
rem  Processes are found by the PORT they hold, not by window title.
rem  taskkill's WINDOWTITLE filter reports success while matching nothing
rem  when the window is a 'cmd /k' wrapper, so it silently does nothing.
rem ===================================================================

if "%~1"=="" goto :default
if /i "%~1"=="listener"  call :kill_listener      & goto :done
if /i "%~1"=="dashboard" call :kill_port 5173 dashboard & goto :done
if /i "%~1"=="backend"   call :kill_port 3001 backend   & goto :done
if /i "%~1"=="mysql"     call :kill_port 3306 MySQL     & goto :done

echo Unknown target "%~1".
echo Use: listener ^| dashboard ^| backend ^| mysql, or no argument for the station.
exit /b 1

:default
rem Reverse of the start order: dependents first.
call :kill_listener
call :kill_port 5173 dashboard
call :kill_port 3001 backend
echo.
echo   MySQL on 3306 left running -- it is shared with your other XAMPP work.
echo   Stop it with: stop-eggministrator.bat mysql

:done
echo.
exit /b 0

rem --- kill whatever is LISTENING on a port -------------------------
:kill_port
set "_port=%~1"
set "_name=%~2"
set "_hit="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /c:":%_port% " ^| findstr /c:"LISTENING"') do (
    if not "%%p"=="0" (
        taskkill /PID %%p /T /F >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo   stopped: %_name% ^(port %_port%, pid %%p^)
            set "_hit=1"
        )
    )
)
if not defined _hit echo   not running: %_name% ^(port %_port%^)
exit /b 0

rem --- the listener holds no port, so match it by command line ------
:kill_listener
set "_found="
rem Two traps here, both found the hard way:
rem
rem  1. No '=' and no escaped double quotes -- batch mangles both on the way
rem     through a for /f backtick command, which silently broke the -Filter form.
rem  2. The Name test is NOT optional. Without it the query matches the
rem     PowerShell process running it, because that process's own command line
rem     contains the search string. This script then killed its own query and
rem     left the listener running, while reporting success.
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*listen_station.py*' } | ForEach-Object { $_.ProcessId }"`) do (
    taskkill /PID %%i /T /F >nul 2>&1
    echo   stopped: listener ^(pid %%i^) -- webcam is free
    set "_found=1"
)
if not defined _found echo   not running: listener
exit /b 0
