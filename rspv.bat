@echo off
rem =====================================================================
rem  RSVP TUI launcher
rem  Usage: rspv [OPTIONS] COMMAND [ARGS]...
rem  Or:    uv run rspv.py [OPTIONS] COMMAND [ARGS]...
rem =====================================================================
set "ROOT=%~dp0"
if exist "%ROOT%.venv\Scripts\python.exe" (
    "%ROOT%.venv\Scripts\python.exe" -m rsvp_tui.cli %*
) else if exist "%ROOT%Scripts\python.exe" (
    "%ROOT%Scripts\python.exe" -m rsvp_tui.cli %*
) else (
    python -m rsvp_tui.cli %*
)
