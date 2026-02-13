@echo off
setlocal

REM Alias legado para manter compatibilidade com chamadas antigas
call run_tests.bat
exit /b %errorlevel%
