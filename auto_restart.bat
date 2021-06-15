@echo off
tasklist|findstr /i "rsoc"
if errorlevel 1 goto start
ping -n 3 127.1>nul
%0

:start
start rsoc_test.exe
%0