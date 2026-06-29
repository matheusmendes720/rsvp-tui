@echo off
rem =====================================================================
rem  RSVP workspace — Windows-native task dispatcher
rem ---------------------------------------------------------------------
rem  Usage:   rspv-task <name> [args...]
rem  Example: rspv-task tui
rem
rem  Mirrors bin/rsvp-task (POSIX bash). This wrapper is for users
rem  running cmd.exe / PowerShell; it does not require bash.
rem =====================================================================

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "ROOT=%SCRIPT_DIR%.."
pushd "%ROOT%"

rem Pick a Python interpreter (venv first, then PATH).
if exist "%ROOT%\.venv\Scripts\python.exe" (
    set "PY=%ROOT%\.venv\Scripts\python.exe"
) else (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        set "PY=%%P"
        goto :have_py
    )
    echo error: no python on PATH 1>&2
    exit /b 127
)
:have_py

rem Map of task -> module. Forwarded as:  py -m <module> <task> [args]
set "MODULE="
if /i "%~1"=="tui"        set "MODULE=rsvp_tui.cli"
if /i "%~1"=="rspv-tui"    set "MODULE=rsvp_tui.cli"
if /i "%~1"=="read"       set "MODULE=rsvp_tui.cli"
if /i "%~1"=="r"          set "MODULE=rsvp_tui.cli"
if /i "%~1"=="import"     set "MODULE=rsvp_tui.cli"
if /i "%~1"=="i"          set "MODULE=rsvp_tui.cli"
if /i "%~1"=="library"    set "MODULE=rsvp_tui.cli"
if /i "%~1"=="ls"         set "MODULE=rsvp_tui.cli"
if /i "%~1"=="config"     set "MODULE=rsvp_tui.cli"
if /i "%~1"=="cfg"        set "MODULE=rsvp_tui.cli"
if /i "%~1"=="remove"     set "MODULE=rsvp_tui.cli"
if /i "%~1"=="rm"         set "MODULE=rsvp_tui.cli"
if /i "%~1"=="stats"      set "MODULE=rsvp_tui.cli"
if /i "%~1"=="info"       set "MODULE=rsvp_tui.cli"
if /i "%~1"=="doctor"     set "MODULE=rsvp_tui.cli"
if /i "%~1"=="diagnose"   set "MODULE=rsvp_tui.cli"
if /i "%~1"=="themes"     set "MODULE=rsvp_tui.cli"
if /i "%~1"=="where"      set "MODULE=rsvp_tui.cli"
if /i "%~1"=="version"    set "MODULE=rsvp_tui.cli"
if /i "%~1"=="palette"    set "MODULE=scripts.palette"
if /i "%~1"=="demo"       set "MODULE=scripts.demo"
if /i "%~1"=="build"      set "MODULE=scripts.build"
if /i "%~1"=="dev"        set "MODULE=scripts.build"
if /i "%~1"=="sync"       set "MODULE=scripts.sync"
if /i "%~1"=="clean"      set "MODULE=scripts.clean"
if /i "%~1"=="test"       set "MODULE=scripts.test"
if /i "%~1"=="lint"       set "MODULE=scripts.lint"
if /i "%~1"=="format"     set "MODULE=scripts.format"
if /i "%~1"=="typecheck"  set "MODULE=scripts.typecheck"
if /i "%~1"=="verify"     set "MODULE=scripts.verify"
if /i "%~1"=="docs"       set "MODULE=scripts.docs"
if /i "%~1"=="man"        set "MODULE=scripts.man"
if /i "%~1"=="bench"      set "MODULE=scripts.bench"
if /i "%~1"=="tasks"      set "MODULE=scripts.tasks"
if /i "%~1"=="help"       set "MODULE=scripts.tasks"
if "%MODULE%"=="" set "MODULE=rsvp_tui.cli"

rem dev = build --editable
set "EXTRA="
if /i "%~1"=="dev" set "EXTRA=--editable"

rem Build the rest of the args (skipping the task name and "help").
set "ARGS="
:loop
if "%~1"=="" goto :run
if /i "%~1"=="dev"        goto :next
if /i "%~1"=="clean-all"  goto :next
if /i "%~1"=="help"       goto :next
if defined ARGS (
    set "ARGS=!ARGS! %~1"
) else (
    set "ARGS=%~1"
)
:next
shift
goto :loop

:run
if defined EXTRA (
    "%PY%" -m "%MODULE%" %~1 %EXTRA% %ARGS%
) else (
    "%PY%" -m "%MODULE%" %~1 %ARGS%
)
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
