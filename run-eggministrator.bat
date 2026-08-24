@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title EggMinistrator launcher

rem ===================================================================
rem  Brings the whole station up in the right order, checking as it goes.
rem
rem  Order is not cosmetic: mysql2 throws on its first query if MySQL is
rem  not up, the listener polls a dead port if the backend is not up, and
rem  the dashboard shows an empty shell if it starts before either.
rem
rem  Each process gets its own titled window so a crash is visible at a
rem  glance and one can be restarted without killing the other three.
rem
rem    run-eggministrator.bat                 everything
rem    run-eggministrator.bat --no-listener   leaves the webcam free for
rem                                           ai\capture.py
rem ===================================================================

set "MYSQL_BIN=C:\xampp\mysql\bin"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "SKIP_LISTENER="
if /i "%~1"=="--no-listener" set "SKIP_LISTENER=1"

echo.
echo  ================================================================
echo   EggMinistrator
echo  ================================================================

rem --- 0. the number secrets.h has to match -------------------------
echo.
echo  [ 0 ] This machine's addresses on the network:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "IP=%%a"
    set "IP=!IP: =!"
    echo         !IP!
)
echo.
echo         SERVER_HOST in firmware\...\secrets.h must be one of these,
echo         and the board must be on the SAME 2.4 GHz network. The classic
echo         ESP32 has no 5 GHz radio.

rem --- 1. preflight -------------------------------------------------
echo.
echo  [ 1 ] Checking what is installed...

if not exist "backend\.env" (
    echo         MISSING: backend\.env
    echo         Fix:     copy backend\.env.example backend\.env   then fill it in
    goto :failed
)
if not exist "backend\node_modules" (
    echo         MISSING: backend\node_modules
    echo         Fix:     cd backend ^&^& npm install
    goto :failed
)
if not exist "dashboard\node_modules" (
    echo         MISSING: dashboard\node_modules
    echo         Fix:     cd dashboard ^&^& npm install
    goto :failed
)
if not exist "%VENV_PY%" (
    echo         MISSING: .venv\Scripts\python.exe
    echo         Fix:     py -m venv .venv ^&^& .venv\Scripts\pip install -r ai\requirements.txt
    goto :failed
)
echo         ok

rem --- 2. MySQL -----------------------------------------------------
echo.
echo  [ 2 ] MySQL...
call :is_port_up 3306
if !ERRORLEVEL! EQU 0 (
    echo         already running
) else (
    if not exist "%MYSQL_BIN%\mysqld.exe" (
        echo         MISSING: %MYSQL_BIN%\mysqld.exe
        echo         Is XAMPP installed somewhere else? Edit MYSQL_BIN at the top of this file.
        goto :failed
    )
    echo         starting XAMPP's mysqld...
    start "EggMinistrator MySQL" /min "%MYSQL_BIN%\mysqld.exe" --defaults-file="%MYSQL_BIN%\my.ini"
    call :wait_for_port 3306 30
    if !ERRORLEVEL! NEQ 0 (
        echo         MySQL never came up on 3306.
        echo         Try starting it from the XAMPP Control Panel and look at its log.
        goto :failed
    )
    echo         up
    echo         NOTE: started from here, so the XAMPP Control Panel will not show
    echo               it as running. That is cosmetic.
)

rem --- 3. backend ---------------------------------------------------
echo.
echo  [ 3 ] Backend...
call :is_port_up 3001
if !ERRORLEVEL! EQU 0 (
    echo         already running on 3001
) else (
    start "EggMinistrator backend" cmd /k "cd /d "%~dp0backend" && npm start"
    call :wait_for_port 3001 30
    if !ERRORLEVEL! NEQ 0 (
        echo         Backend never answered on 3001. Look at its window.
        echo         Most likely: .env missing a value, or MySQL refused the connection.
        goto :failed
    )
    echo         up on 3001
)

rem --- 4. listener --------------------------------------------------
echo.
echo  [ 4 ] Classifier listener...
if defined SKIP_LISTENER (
    echo         SKIPPED ^(--no-listener^). The webcam is free for ai\capture.py.
    goto :dashboard
)
if not exist "ai\models\egg.keras" (
    echo         SKIPPED: no model at ai\models\egg.keras
    echo         Train one first: "%VENV_PY%" ai\scripts\train.py
    echo         Everything else below still comes up.
    goto :dashboard
)

rem The device key comes out of backend\.env so it can never drift from
rem what the backend is checking against, and so nobody has to type it.
set "DEVICE_API_KEY="
for /f "usebackq tokens=1,* delims==" %%a in (`findstr /b /c:"DEVICE_API_KEY=" backend\.env`) do set "DEVICE_API_KEY=%%b"
if not defined DEVICE_API_KEY (
    echo         SKIPPED: no DEVICE_API_KEY in backend\.env -- every call would 401.
    goto :dashboard
)

rem The zoom comes out of the capture settings for the same reason. If the
rem listener crops differently from the way the dataset was shot, the model
rem sees a framing it never trained on and NOTHING about the failure looks
rem like a framing problem.
rem Read outside an if-block on purpose: cmd treats an unescaped ')' inside a
rem parenthesised block as the end of the block, and the reader is a script
rem rather than an inline one-liner for the same reason.
set "STATION_ZOOM="
if not exist "ai\capture_settings.json" goto :zoom_done
for /f "usebackq delims=" %%z in (`"%VENV_PY%" ai\scripts\print_zoom.py`) do set "STATION_ZOOM=%%z"
:zoom_done
if defined STATION_ZOOM (
    echo         zoom !STATION_ZOOM!x, taken from ai\capture_settings.json
    start "EggMinistrator listener" cmd /k ""%VENV_PY%" ai\listen_station.py --key "!DEVICE_API_KEY!" --zoom !STATION_ZOOM!"
) else (
    echo         WARNING: no saved zoom. Using the listener's default, which may
    echo                  not match how the dataset was shot.
    start "EggMinistrator listener" cmd /k ""%VENV_PY%" ai\listen_station.py --key "!DEVICE_API_KEY!""
)
echo         started -- it holds the webcam until you stop it

:dashboard
rem --- 5. dashboard -------------------------------------------------
echo.
echo  [ 5 ] Dashboard...
call :is_port_up 5173
if !ERRORLEVEL! EQU 0 (
    echo         already running on 5173
) else (
    start "EggMinistrator dashboard" cmd /k "cd /d "%~dp0dashboard" && npm run dev"
    call :wait_for_port 5173 45
    if !ERRORLEVEL! NEQ 0 (
        echo         Vite never came up on 5173. Look at its window.
        goto :failed
    )
)
start "" "http://localhost:5173"

echo.
echo  ================================================================
echo   Running.  backend 3001   dashboard 5173
echo.
echo   To stop everything:      stop-eggministrator.bat
echo   To free the webcam only: stop-eggministrator.bat listener
echo  ================================================================
echo.
pause
exit /b 0

:failed
echo.
echo  ---------------------------------------------------------------
echo   STOPPED. Nothing further was started.
echo  ---------------------------------------------------------------
echo.
pause
exit /b 1

rem --- helpers ------------------------------------------------------
:is_port_up
netstat -an | findstr /c:":%~1" | findstr /c:"LISTENING" >nul 2>&1
exit /b !ERRORLEVEL!

:wait_for_port
set /a "_tries=0"
:wait_loop
call :is_port_up %~1
if !ERRORLEVEL! EQU 0 exit /b 0
set /a "_tries+=1"
if !_tries! GEQ %~2 exit /b 1
timeout /t 1 /nobreak >nul
goto :wait_loop
