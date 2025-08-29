@echo off
title WalletSender Modular v2.0 - Production
color 0A
cls

echo ============================================
echo    WalletSender Modular v2.0 Production
echo ============================================
echo.

echo [1] Проверка Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python не найден! Установите Python 3.8+
    echo     https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version

echo.
echo [2] Проверка зависимостей...

REM Проверка PyQt5
python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] PyQt5 не установлен
    echo [*] Установка PyQt5...
    pip install PyQt5
)

REM Проверка web3
python -c "import web3" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] web3 не установлен
    echo [*] Установка web3...
    pip install web3
)

REM Проверка других зависимостей
python -c "import eth_account" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] eth-account не установлен
    echo [*] Установка eth-account...
    pip install eth-account
)

python -c "import sqlalchemy" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] sqlalchemy не установлен
    echo [*] Установка sqlalchemy...
    pip install sqlalchemy
)

echo.
echo [3] Запуск WalletSender Modular...
echo ============================================
echo.

cd /d "%~dp0"
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [X] Ошибка запуска приложения!
    echo     Проверьте логи для деталей.
    pause
)

exit /b %errorlevel%
