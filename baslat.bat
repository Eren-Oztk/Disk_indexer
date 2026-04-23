@echo off
title Disk Indexer
echo Disk Indexer baslatiliyor...

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo HATA: Python bulunamadi. Python 3.8+ kurulu olmali.
    pause
    exit /b 1
)

pip show PyQt5 >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo PyQt5 kuruluyor, lutfen bekleyin...
    pip install PyQt5 --quiet
)

python disk_indexer.py
pause
