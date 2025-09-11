"""
Диагностический модуль для поиска причины краша
Версия 2.4.20
"""

import sys
import traceback
import functools
from datetime import datetime

# Файл для записи трассировки
TRACE_FILE = "execution_trace.txt"

def trace_execution(func):
    """Декоратор для трассировки выполнения"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Записываем вход в функцию
        trace_msg = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] >>> ENTER: {func.__module__}.{func.__name__}"
        print(trace_msg)
        
        # Записываем в файл
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(trace_msg + "\n")
            
        try:
            # Выполняем функцию
            result = func(*args, **kwargs)
            
            # Записываем успешный выход
            trace_msg = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] <<< EXIT: {func.__module__}.{func.__name__} (OK)"
            print(trace_msg)
            
            with open(TRACE_FILE, "a", encoding="utf-8") as f:
                f.write(trace_msg + "\n")
                
            return result
            
        except Exception as e:
            # Записываем ошибку
            trace_msg = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] !!! ERROR in {func.__module__}.{func.__name__}: {e}"
            print(trace_msg)
            
            with open(TRACE_FILE, "a", encoding="utf-8") as f:
                f.write(trace_msg + "\n")
                f.write(f"Traceback:\n{traceback.format_exc()}\n")
            
            # Пробрасываем исключение дальше
            raise
            
    return wrapper

def check_qt_thread():
    """Проверка, что мы в главном потоке Qt"""
    try:
        from PyQt5.QtCore import QThread
        current = QThread.currentThread()
        
        # Получаем главный поток приложения
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            main_thread = app.thread()
            if current != main_thread:
                msg = f"WARNING: Qt operation in wrong thread! Current: {current}, Main: {main_thread}"
                print(msg)
                with open(TRACE_FILE, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
                return False
        return True
    except:
        return True  # Если не можем проверить, считаем что все ок

def trace_qt_operation(func):
    """Декоратор для проверки Qt операций"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Проверяем поток перед Qt операцией
        if not check_qt_thread():
            trace_msg = f"!!! Qt THREAD VIOLATION in {func.__module__}.{func.__name__}"
            print(trace_msg)
            with open(TRACE_FILE, "a", encoding="utf-8") as f:
                f.write(trace_msg + "\n")
        
        return trace_execution(func)(*args, **kwargs)
    
    return wrapper

def diagnose_crash_point():
    """Анализ точки краша по трассировке"""
    try:
        with open(TRACE_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # Находим последний ENTER без EXIT
        enter_stack = []
        for line in lines:
            if ">>> ENTER:" in line:
                func_name = line.split(">>> ENTER:")[1].strip()
                enter_stack.append(func_name)
            elif "<<< EXIT:" in line:
                func_name = line.split("<<< EXIT:")[1].split("(")[0].strip()
                if enter_stack and enter_stack[-1] == func_name:
                    enter_stack.pop()
        
        if enter_stack:
            print("\n" + "="*50)
            print("🔴 ТОЧКА КРАША НАЙДЕНА!")
            print(f"Последняя функция перед крашем: {enter_stack[-1]}")
            print("Стек вызовов на момент краша:")
            for i, func in enumerate(enter_stack):
                print(f"  {'  '*i}└─> {func}")
            print("="*50)
            return enter_stack[-1]
        else:
            print("[OK] Краша не обнаружено в трассировке")
            return None
            
    except FileNotFoundError:
        print("Файл трассировки не найден. Запустите приложение с диагностикой.")
        return None

# Очистка трассировки при импорте
with open(TRACE_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== Execution trace started at {datetime.now()} ===\n")

print(f"[OK] Диагностика активирована. Трассировка в {TRACE_FILE}")
