#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрая установка psutil для патча стабильности
"""

import subprocess
import sys

def install_psutil():
    """Установка psutil если не установлен"""
    try:
        import psutil
        print("[OK] psutil уже установлен")
        print(f"   Версия: {psutil.__version__}")
        return True
    except ImportError:
        print("[WARN] psutil не найден, установка...")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
            print("[OK] psutil успешно установлен!")
            
            # Проверяем установку
            import psutil
            print(f"   Версия: {psutil.__version__}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка установки psutil: {e}")
            print("\nПопробуйте установить вручную:")
            print("pip install psutil")
            return False

if __name__ == "__main__":
    print("=" * 50)
    print("Установщик зависимостей для WalletSender v2.4.19")
    print("=" * 50)
    
    if install_psutil():
        print("\n[OK] Все зависимости установлены!")
        print("Теперь можете запустить приложение:")
        print("python main.py")
    else:
        print("\n[ERROR] Не удалось установить зависимости")
        print("Установите вручную и повторите попытку")
