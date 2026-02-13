@echo off
setlocal

REM Executor unificado de testes (Windows)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 run_tests.py
  exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
  python run_tests.py
  exit /b %errorlevel%
)

echo [run_tests.bat] Python nao encontrado no PATH.
exit /b 9009
