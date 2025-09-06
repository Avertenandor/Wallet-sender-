"""
Модуль совместимости Qt для поддержки PyQt6, PyQt5 и PySide6
"""

import sys
import os

# Флаг для отслеживания, какой бэкенд используется
QT_BACKEND = None

# Пытаемся импортировать доступный Qt бэкенд (минимальный набор импортов)
backend_error = None
try:
    # Сначала пробуем PyQt5 (самый стабильный для проекта)
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QLabel, QStatusBar, QMenuBar, QAction, QMenu,
        QMessageBox, QProgressBar, QTextEdit, QFileDialog, QSplitter,
        QScrollBar, QGroupBox, QPushButton, QLineEdit, QComboBox,
        QTableWidget, QTableWidgetItem, QHeaderView
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QCoreApplication
    from PyQt5.QtGui import QIcon, QFont, QCloseEvent
    QT_BACKEND = 'PyQt5'
except Exception as e:
    backend_error = e
    try:
        # Затем пробуем PyQt6
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QTabWidget, QLabel, QStatusBar, QMenuBar, QAction, QMenu,
            QMessageBox, QProgressBar, QTextEdit, QFileDialog, QSplitter,
            QScrollBar, QGroupBox, QPushButton, QLineEdit, QComboBox,
            QTableWidget, QTableWidgetItem, QHeaderView
        )
        from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QCoreApplication
        from PyQt6.QtGui import QIcon, QFont, QCloseEvent
        QT_BACKEND = 'PyQt6'
        if not hasattr(Qt, 'MidButton'):
            Qt.MidButton = Qt.MouseButton.MiddleButton  # type: ignore[attr-defined]
    except Exception as e2:
        backend_error = e2
        try:
            # В крайнем случае пробуем PySide6
            from PySide6.QtWidgets import (
                QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                QTabWidget, QLabel, QStatusBar, QMenuBar, QAction, QMenu,
                QMessageBox, QProgressBar, QTextEdit, QFileDialog, QSplitter,
                QScrollBar, QGroupBox, QPushButton, QLineEdit, QComboBox,
                QTableWidget, QTableWidgetItem, QHeaderView
            )
            from PySide6.QtCore import (
                Qt, QTimer, Signal as pyqtSignal, Slot as pyqtSlot, QCoreApplication
            )
            from PySide6.QtGui import QIcon, QFont, QCloseEvent
            QT_BACKEND = 'PySide6'
        except Exception as e3:
            backend_error = e3
            print("ОШИБКА: Не найден ни один Qt бэкенд!")
            print("Установите один из следующих пакетов:")
            print("  pip install PyQt6")
            print("  pip install PyQt5") 
            print("  pip install PySide6")
            if backend_error:
                print(f"Последняя ошибка импорта: {backend_error}")
            sys.exit(1)


def enable_high_dpi():
    """
    Включение поддержки High DPI дисплеев
    Должно вызываться ДО создания QApplication
    """
    if QT_BACKEND == 'PyQt6':
        # В PyQt6 High DPI включен по умолчанию
        pass
        
    elif QT_BACKEND == 'PyQt5':
        # Включаем High DPI для PyQt5
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
            
    elif QT_BACKEND == 'PySide6':
        # В PySide6 High DPI включен по умолчанию
        pass
    
    # Устанавливаем переменную окружения для всех бэкендов
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'


def get_qt_backend():
    """
    Получение информации о текущем Qt бэкенде
    
    Returns:
        str: Название используемого бэкенда ('PyQt6', 'PyQt5', 'PySide6')
    """
    return QT_BACKEND


# Дополнительные утилиты для совместимости
def create_action(parent, text, slot=None, shortcut=None, icon=None, 
                  tip=None, checkable=False, signal="triggered"):
    """
    Создание QAction с поддержкой разных Qt версий
    
    Args:
        parent: Родительский виджет
        text: Текст действия
        slot: Слот для подключения
        shortcut: Горячая клавиша
        icon: Иконка
        tip: Подсказка
        checkable: Делать ли действие переключаемым
        signal: Имя сигнала для подключения
        
    Returns:
        QAction: Созданное действие
    """
    action = QAction(text, parent)
    
    if icon is not None:
        action.setIcon(icon)
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    if slot is not None:
        getattr(action, signal).connect(slot)
    if checkable:
        action.setCheckable(True)
        
    return action


def get_open_file_name(parent=None, caption="", directory="", 
                       filter="", selected_filter=""):
    """
    Обертка для QFileDialog.getOpenFileName с поддержкой разных Qt версий
    """
    if QT_BACKEND == 'PyQt6' or QT_BACKEND == 'PyQt5':
        return QFileDialog.getOpenFileName(
            parent, caption, directory, filter
        )
    else:  # PySide6
        return QFileDialog.getOpenFileName(
            parent, caption, directory, filter, selected_filter
        )


def get_save_file_name(parent=None, caption="", directory="",
                       filter="", selected_filter=""):
    """
    Обертка для QFileDialog.getSaveFileName с поддержкой разных Qt версий
    """
    if QT_BACKEND == 'PyQt6' or QT_BACKEND == 'PyQt5':
        return QFileDialog.getSaveFileName(
            parent, caption, directory, filter
        )
    else:  # PySide6
        return QFileDialog.getSaveFileName(
            parent, caption, directory, filter, selected_filter
        )


# Экспортируем информацию о бэкенде
__all__ = [
    'QT_BACKEND',
    'enable_high_dpi',
    'get_qt_backend',
    'create_action',
    'get_open_file_name',
    'get_save_file_name'
]

# Выводим информацию о используемом бэкенде
if __name__ != '__main__':
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Используется Qt бэкенд: {QT_BACKEND}")
