@echo off
title Установка зависимостей WalletSender
color 0E
cls

echo ============================================
echo   Установка зависимостей WalletSender v2.0
echo ============================================
echo.

echo [*] Обновление pip...
python -m pip install --upgrade pip

echo.
echo [*] Установка основных зависимостей...
echo.

REM Основные зависимости
pip install PyQt5>=5.15.0
pip install web3>=6.0.0
pip install eth-account>=0.8.0
pip install sqlalchemy>=2.0.0

echo.
echo [*] Установка дополнительных библиотек...
echo.

REM Дополнительные библиотеки
pip install aiohttp>=3.8.0
pip install requests>=2.28.0
pip install cryptography>=39.0.0
pip install mnemonic>=0.20
pip install python-dotenv>=1.0.0
pip install colorlog>=6.7.0
pip install openpyxl>=3.1.0
pip install qdarkstyle>=3.1.0

echo.
echo [*] Установка блокчейн утилит...
echo.

REM Блокчейн утилиты
pip install eth-utils>=2.0.0
pip install eth-typing>=3.0.0
pip install hexbytes>=0.3.0

echo.
echo ============================================
echo   Установка завершена!
echo ============================================
echo.
echo Теперь вы можете запустить приложение через START.bat
echo.

pause
