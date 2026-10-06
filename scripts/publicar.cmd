@echo off
rem publicar.cmd - lanza scripts\publicar.py con el Python del .venv de la carpeta
rem principal (los worktrees no tienen .venv). Funciona desde cualquier worktree.
rem Uso: scripts\publicar.cmd [--sin-deploy ^| --solo-sync] [--simular]
setlocal
set "GCD="
for /f "delims=" %%i in ('git rev-parse --path-format^=absolute --git-common-dir 2^>nul') do set "GCD=%%i"
if not defined GCD (
  echo No estas dentro del repositorio de FIN-SYS.
  exit /b 1
)
set "PY=%GCD%\..\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo No encuentro el Python de la carpeta principal: %PY%
  exit /b 1
)
"%PY%" "%~dp0publicar.py" %*
