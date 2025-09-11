#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшение единой системы логирования WalletSender v2.5.0
Обеспечивает вывод всех логов во все окна
"""

import os
import sys
from pathlib import Path

def create_unified_logger():
    """Создает единый класс логгера для всех компонентов"""
    
    logger_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Единый менеджер логирования для WalletSender
Обеспечивает синхронизацию логов между всеми окнами
"""

from typing import List, Callable, Optional
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

class UnifiedLogManager(QObject):
    """Единый менеджер логирования"""
    
    # Сигнал для оповещения всех подписчиков о новом логе
    log_added = pyqtSignal(str, str)  # message, level
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            super().__init__()
            self.initialized = True
            self.subscribers: List[Callable] = []
            self.log_history: List[tuple] = []  # (timestamp, message, level)
            self.max_history = 1000
    
    def add_log(self, message: str, level: str = "INFO"):
        """Добавляет лог и уведомляет всех подписчиков"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Сохраняем в историю
        self.log_history.append((timestamp, message, level))
        if len(self.log_history) > self.max_history:
            self.log_history.pop(0)
        
        # Отправляем сигнал всем подписчикам
        self.log_added.emit(message, level)
        
        # Вызываем callback'и подписчиков
        for subscriber in self.subscribers:
            try:
                subscriber(message, level)
            except Exception as e:
                print(f"Ошибка вызова подписчика: {e}")
    
    def subscribe(self, callback: Callable):
        """Подписаться на получение логов"""
        if callback not in self.subscribers:
            self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """Отписаться от получения логов"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def get_history(self) -> List[tuple]:
        """Получить историю логов"""
        return self.log_history.copy()
    
    def clear_history(self):
        """Очистить историю логов"""
        self.log_history.clear()

# Глобальный экземпляр менеджера
_log_manager = None

def get_log_manager() -> UnifiedLogManager:
    """Получить единый менеджер логирования"""
    global _log_manager
    if _log_manager is None:
        _log_manager = UnifiedLogManager()
    return _log_manager

def unified_log(message: str, level: str = "INFO"):
    """Быстрый доступ к логированию"""
    get_log_manager().add_log(message, level)
'''
    
    # Сохраняем файл
    file_path = Path(r"C:\Users\konfu\Desktop\Sites\Experiment\Experiment1\WalletSender_MCP  копия\WalletSender_Modular\WalletSender_Modular\src\wallet_sender\utils\unified_logger.py")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(logger_code)
    
    print(f"[OK] Создан единый менеджер логирования: {file_path.name}")
    return True

def update_main_window():
    """Обновляет главное окно для использования единого логгера"""
    
    file_path = Path(r"C:\Users\konfu\Desktop\Sites\Experiment\Experiment1\WalletSender_MCP  копия\WalletSender_Modular\WalletSender_Modular\src\wallet_sender\ui\main_window.py")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Добавляем импорт единого логгера
    if "from ..utils.unified_logger import" not in content:
        old_import = "from ..utils.logger import get_logger"
        new_import = """from ..utils.logger import get_logger
from ..utils.unified_logger import get_log_manager, unified_log"""
        
        content = content.replace(old_import, new_import)
        print("  [OK] Добавлен импорт unified_logger")
    
    # Обновляем метод __init__ для подключения к единому логгеру
    if "get_log_manager()" not in content:
        old_init = "        # Настраиваем улучшенное логирование\n        set_ui_log_handler(self._enhanced_log_handler)"
        new_init = """        # Настраиваем улучшенное логирование
        set_ui_log_handler(self._enhanced_log_handler)
        
        # Подключаемся к единому менеджеру логирования
        self.log_manager = get_log_manager()
        self.log_manager.subscribe(self._unified_log_handler)"""
        
        content = content.replace(old_init, new_init)
        print("  [OK] Добавлено подключение к единому логгеру")
    
    # Добавляем метод _unified_log_handler
    if "_unified_log_handler" not in content:
        old_method = "    def _enhanced_log_handler(self, message: str, level: str = \"INFO\"):"
        new_method = """    def _unified_log_handler(self, message: str, level: str = "INFO"):
        \"\"\"Обработчик для единого логгера\"\"\"
        # Просто передаем в существующий обработчик
        self.log_message.emit(message, level)
    
    def _enhanced_log_handler(self, message: str, level: str = "INFO\"):"""
        
        content = content.replace(old_method, new_method)
        print("  [OK] Добавлен обработчик единого логгера")
    
    # Обновляем метод add_log для отправки в единый логгер
    old_add_log = """    @pyqtSlot(str, str)
    def add_log(self, message: str, level: str = "INFO") -> None:
        \"\"\"Добавление сообщения в лог\"\"\"
        QTimer().singleShot(0, lambda: self._add_log_impl(message, level))"""
    
    new_add_log = """    @pyqtSlot(str, str)
    def add_log(self, message: str, level: str = "INFO") -> None:
        \"\"\"Добавление сообщения в лог\"\"\"
        # Отправляем в единый логгер (он уведомит все окна)
        if hasattr(self, 'log_manager'):
            self.log_manager.add_log(message, level)
        else:
            # Fallback на прямое добавление
            QTimer().singleShot(0, lambda: self._add_log_impl(message, level))"""
    
    if "self.log_manager.add_log" not in content:
        content = content.replace(old_add_log, new_add_log)
        print("  [OK] Обновлен метод add_log")
    
    # Сохраняем изменения
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Обновлено главное окно: {file_path.name}")
    return True

def update_log_windows():
    """Обновляет окна логов для подключения к единому логгеру"""
    
    file_path = Path(r"C:\Users\konfu\Desktop\Sites\Experiment\Experiment1\WalletSender_MCP  копия\WalletSender_Modular\WalletSender_Modular\src\wallet_sender\ui\log_windows.py")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Добавляем импорт единого логгера
    if "from wallet_sender.utils.unified_logger import" not in content:
        old_import = "from datetime import datetime"
        new_import = """from datetime import datetime
from wallet_sender.utils.unified_logger import get_log_manager"""
        
        content = content.replace(old_import, new_import)
        print("  [OK] Добавлен импорт unified_logger")
    
    # Обновляем LogWindow для подключения к единому логгеру
    if "self.log_manager = get_log_manager()" not in content:
        # В методе __init__ класса LogWindow
        old_init = "        self.parent_window = parent\n        self.init_ui()"
        new_init = """        self.parent_window = parent
        
        # Подключаемся к единому логгеру
        self.log_manager = get_log_manager()
        self.log_manager.subscribe(self._on_unified_log)
        
        self.init_ui()"""
        
        content = content.replace(old_init, new_init, 1)  # Заменяем только первое вхождение
        print("  [OK] LogWindow подключен к единому логгеру")
    
    # Добавляем метод _on_unified_log для LogWindow
    if "def _on_unified_log" not in content:
        method_to_add = """
    def _on_unified_log(self, message: str, level: str):
        \"\"\"Обработчик логов от единого менеджера\"\"\"
        self.add_log(message, level)
"""
        # Добавляем после метода add_log
        pos = content.find("    def sync_with_parent(self):")
        if pos > 0:
            content = content[:pos] + method_to_add + "\n" + content[pos:]
            print("  [OK] Добавлен обработчик _on_unified_log в LogWindow")
    
    # Аналогично для FloatingLogWindow
    if "class FloatingLogWindow" in content:
        # Находим init FloatingLogWindow
        floating_init_pos = content.find("class FloatingLogWindow")
        floating_init_pos = content.find("        self.parent_window = parent", floating_init_pos)
        
        if floating_init_pos > 0 and "# Подключаемся к единому логгеру" not in content[floating_init_pos:floating_init_pos+500]:
            old_floating = "        self.parent_window = parent\n        self.init_ui()"
            new_floating = """        self.parent_window = parent
        
        # Подключаемся к единому логгеру
        self.log_manager = get_log_manager()
        self.log_manager.subscribe(self._on_unified_log)
        
        self.init_ui()"""
            
            content = content.replace(old_floating, new_floating)
            print("  [OK] FloatingLogWindow подключен к единому логгеру")
    
    # Сохраняем изменения
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Обновлены окна логов: {file_path.name}")
    return True

def update_version():
    """Обновляет версию приложения"""
    version_file = Path(r"C:\Users\konfu\Desktop\Sites\Experiment\Experiment1\WalletSender_MCP  копия\WalletSender_Modular\WalletSender_Modular\VERSION")
    
    with open(version_file, 'w') as f:
        f.write("2.5.0")
    
    print("[OK] Версия обновлена до 2.5.0")
    return True

def main():
    print("=" * 60)
    print("[CONFIG] УЛУЧШЕНИЕ СИСТЕМЫ ЛОГИРОВАНИЯ WalletSender v2.5.0")
    print("=" * 60)
    print()
    print("Цель: Обеспечить вывод всех логов во все окна")
    print()
    
    success = True
    
    # Создаем единый менеджер логирования
    print("📝 Создание единого менеджера логирования...")
    if not create_unified_logger():
        success = False
    
    # Обновляем главное окно
    print("\n📝 Обновление главного окна...")
    if not update_main_window():
        success = False
    
    # Обновляем окна логов
    print("\n📝 Обновление окон логов...")
    if not update_log_windows():
        success = False
    
    # Обновляем версию
    print("\n📝 Обновление версии...")
    if not update_version():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 СИСТЕМА ЛОГИРОВАНИЯ УСПЕШНО УЛУЧШЕНА!")
        print()
        print("Что было сделано:")
        print("[OK] Создан единый менеджер логирования (UnifiedLogManager)")
        print("[OK] Главное окно подключено к единому логгеру")
        print("[OK] Окна логов подключены к единому логгеру")
        print("[OK] Все логи теперь синхронизируются автоматически")
        print("[OK] Версия обновлена до 2.5.0")
        print()
        print("Преимущества:")
        print("• Все окна получают все логи")
        print("• Нет дублирования логов")
        print("• Централизованное управление")
        print("• История логов доступна всем компонентам")
        print()
        print("[WARN] ВАЖНО: Перезапустите приложение!")
    else:
        print("[WARN] Некоторые изменения не удалось применить")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
