#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Окна для отображения логов WalletSender
Включает отдельное окно и плавающее окно
"""

from PyQt5.QtWidgets import (
    QDialog, QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QDockWidget, QAction, QMenu,
    QMenuBar, QFileDialog, QMessageBox, QSizeGrip, QCheckBox,
    QLabel, QLineEdit, QSlider, QShortcut
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRect
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QKeySequence, QTextDocument
from datetime import datetime
import re


class LogWindow(QDialog):
    """Отдельное окно для отображения логов"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("[INFO] Логи WalletSender")
        self.setGeometry(200, 200, 900, 600)
        
        # Делаем окно изменяемым по размеру
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowMinimizeButtonHint
        )
        
        # Основной layout
        layout = QVBoxLayout(self)
        
        # Панель инструментов
        toolbar_layout = QHBoxLayout()
        
        # Кнопка очистки
        self.clear_btn = QPushButton("[DELETE] Очистить")
        self.clear_btn.clicked.connect(self.clear_logs)
        self.clear_btn.setMaximumWidth(100)
        toolbar_layout.addWidget(self.clear_btn)
        
        # Кнопка экспорта
        self.export_btn = QPushButton("[SAVE] Экспорт")
        self.export_btn.clicked.connect(self.export_logs)
        self.export_btn.setMaximumWidth(100)
        toolbar_layout.addWidget(self.export_btn)
        
        # Кнопка копирования
        self.copy_btn = QPushButton("[INFO] Копировать всё")
        self.copy_btn.clicked.connect(self.copy_all)
        self.copy_btn.setMaximumWidth(120)
        toolbar_layout.addWidget(self.copy_btn)
        
        # Чекбокс автопрокрутки
        self.autoscroll_cb = QCheckBox("Автопрокрутка")
        self.autoscroll_cb.setChecked(True)
        toolbar_layout.addWidget(self.autoscroll_cb)
        
        # Чекбокс для синхронизации с главным окном
        self.sync_cb = QCheckBox("Синхронизация с главным окном")
        self.sync_cb.setChecked(True)
        toolbar_layout.addWidget(self.sync_cb)
        
        toolbar_layout.addStretch()
        
        # Кнопка поиска
        self.search_btn = QPushButton("[SEARCH] Поиск")
        self.search_btn.clicked.connect(self.toggle_search)
        self.search_btn.setMaximumWidth(100)
        toolbar_layout.addWidget(self.search_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Поле поиска (изначально скрыто)
        self.search_widget = QWidget()
        search_layout = QHBoxLayout(self.search_widget)
        
        search_layout.addWidget(QLabel("Поиск:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите текст для поиска...")
        self.search_input.textChanged.connect(self.search_logs)
        self.search_input.returnPressed.connect(self.find_next)
        search_layout.addWidget(self.search_input)
        
        self.prev_btn = QPushButton("◀ Назад")
        self.prev_btn.clicked.connect(self.find_previous)
        self.prev_btn.setMaximumWidth(80)
        search_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Вперед ▶")
        self.next_btn.clicked.connect(self.find_next)
        self.next_btn.setMaximumWidth(80)
        search_layout.addWidget(self.next_btn)
        
        self.search_widget.setVisible(False)
        layout.addWidget(self.search_widget)
        
        # Текстовое поле для логов
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        
        # Стиль для текстового поля
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 5px;
            }
            QTextEdit::selection {
                background-color: #264f78;
            }
        """)
        
        layout.addWidget(self.log_text)
        
        # Статусная строка
        self.status_label = QLabel("Готов")
        layout.addWidget(self.status_label)
        
        # Горячие клавиши
        # Ctrl+F для поиска
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.toggle_search)
        
        # Ctrl+C для копирования
        copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        copy_shortcut.activated.connect(self.copy_selected)
        
        # Ctrl+A для выделения всего
        select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        select_all_shortcut.activated.connect(self.log_text.selectAll)
        
        # Esc для закрытия поиска
        esc_shortcut = QShortcut(QKeySequence("Escape"), self)
        esc_shortcut.activated.connect(self.hide_search)
        
        # Подключаемся к единому менеджеру логирования
        if self.parent_window:
            try:
                from ..utils.unified_logger import get_log_manager
                self.log_manager = get_log_manager()
                # Подписываемся на получение логов
                self.log_manager.subscribe(self.add_log)
                
                # Загружаем историю логов
                history = self.log_manager.get_history()
                for timestamp, message, level in history:
                    self.add_log(message, level)
            except ImportError:
                # Fallback на старую синхронизацию
                self.sync_timer = QTimer()
                self.sync_timer.timeout.connect(self.sync_with_parent)
                self.sync_timer.start(500)  # Обновление каждые 500мс
            
    def add_log(self, message: str, level: str = "INFO"):
        """Добавление лога в окно"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Цветовая схема
        colors = {
            "DEBUG": "#888",
            "INFO": "#ff8c00",
            "SUCCESS": "#0a0",
            "WARNING": "#f90",
            "ERROR": "#f00",
            "SALE": "#00ff88",
            "PROFIT": "#00ffff"
        }
        
        color = colors.get(level, "#ff8c00")
        formatted_message = f'<span style="color: {color}">[{timestamp}] {message}</span>'
        
        # Сохраняем позицию курсора
        cursor_pos = self.log_text.textCursor().position()
        scrollbar = self.log_text.verticalScrollBar()
        scroll_pos = scrollbar.value()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
        
        # Добавляем текст
        self.log_text.append(formatted_message)
        
        # Восстанавливаем позицию или прокручиваем вниз
        if self.autoscroll_cb.isChecked() and was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(scroll_pos)
            
    def sync_with_parent(self):
        """Синхронизация с логами главного окна"""
        if not self.sync_cb.isChecked() or not self.parent_window:
            return
            
        try:
            parent_logs = self.parent_window.log_area.toHtml()
            current_logs = self.log_text.toHtml()
            
            if parent_logs != current_logs:
                # Сохраняем позицию скролла
                scrollbar = self.log_text.verticalScrollBar()
                was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
                
                self.log_text.setHtml(parent_logs)
                
                # Восстанавливаем позицию или прокручиваем вниз
                if self.autoscroll_cb.isChecked() and was_at_bottom:
                    scrollbar.setValue(scrollbar.maximum())
        except:
            pass
            
    def clear_logs(self):
        """Очистка логов"""
        self.log_text.clear()
        self.status_label.setText("Логи очищены")
        
    def export_logs(self):
        """Экспорт логов в файл"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить логи",
            f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;HTML Files (*.html)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    if filename.endswith('.html'):
                        f.write(self.log_text.toHtml())
                    else:
                        f.write(self.log_text.toPlainText())
                self.status_label.setText(f"Логи экспортированы: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {e}")
                
    def copy_all(self):
        """Копирование всех логов в буфер обмена"""
        self.log_text.selectAll()
        self.log_text.copy()
        self.status_label.setText("Логи скопированы в буфер обмена")
        
    def copy_selected(self):
        """Копирование выделенного текста"""
        if self.log_text.textCursor().hasSelection():
            self.log_text.copy()
            self.status_label.setText("Выделенный текст скопирован")
            
    def toggle_search(self):
        """Переключение видимости поиска"""
        is_visible = self.search_widget.isVisible()
        self.search_widget.setVisible(not is_visible)
        if not is_visible:
            self.search_input.setFocus()
            self.search_input.selectAll()
            
    def hide_search(self):
        """Скрыть поиск"""
        self.search_widget.setVisible(False)
        
    def search_logs(self, text):
        """Поиск по логам"""
        if not text:
            # Снимаем выделение
            cursor = self.log_text.textCursor()
            cursor.clearSelection()
            self.log_text.setTextCursor(cursor)
            return
            
        # Поиск и выделение
        self.log_text.moveCursor(QTextCursor.Start)
        
        found = self.log_text.find(text)
        count = 0
        
        while found:
            count += 1
            found = self.log_text.find(text)
            
        # Возвращаемся к первому найденному
        self.log_text.moveCursor(QTextCursor.Start)
        self.log_text.find(text)
        
        self.status_label.setText(f"Найдено совпадений: {count}")
        
    def find_next(self):
        """Найти следующее совпадение"""
        text = self.search_input.text()
        if text:
            found = self.log_text.find(text)
            if not found:
                # Начинаем сначала
                self.log_text.moveCursor(QTextCursor.Start)
                self.log_text.find(text)
                
    def find_previous(self):
        """Найти предыдущее совпадение"""
        text = self.search_input.text()
        if text:
            found = self.log_text.find(text, QTextDocument.FindBackward)
            if not found:
                # Идем с конца
                self.log_text.moveCursor(QTextCursor.End)
                self.log_text.find(text, QTextDocument.FindBackward)


class FloatingLogWindow(QDockWidget):
    """Плавающее окно логов (док-виджет)"""
    
    def __init__(self, parent=None):
        super().__init__("[INFO] Плавающие логи", parent)
        self.parent_window = parent
        self.init_ui()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        # Настройки док-виджета
        self.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetClosable |
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable
        )
        
        # Контейнер для содержимого
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Панель инструментов
        toolbar_layout = QHBoxLayout()
        
        # Кнопки управления
        self.clear_btn = QPushButton("[DELETE]")
        self.clear_btn.setToolTip("Очистить логи")
        self.clear_btn.clicked.connect(self.clear_logs)
        self.clear_btn.setMaximumWidth(30)
        toolbar_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("[SAVE]")
        self.export_btn.setToolTip("Экспорт логов")
        self.export_btn.clicked.connect(self.export_logs)
        self.export_btn.setMaximumWidth(30)
        toolbar_layout.addWidget(self.export_btn)
        
        self.copy_btn = QPushButton("[INFO]")
        self.copy_btn.setToolTip("Копировать всё")
        self.copy_btn.clicked.connect(self.copy_all)
        self.copy_btn.setMaximumWidth(30)
        toolbar_layout.addWidget(self.copy_btn)
        
        # Чекбоксы
        self.autoscroll_cb = QCheckBox("Авто")
        self.autoscroll_cb.setToolTip("Автопрокрутка")
        self.autoscroll_cb.setChecked(True)
        toolbar_layout.addWidget(self.autoscroll_cb)
        
        self.sync_cb = QCheckBox("Синхр")
        self.sync_cb.setToolTip("Синхронизация с главным окном")
        self.sync_cb.setChecked(True)
        toolbar_layout.addWidget(self.sync_cb)
        
        # Прозрачность
        toolbar_layout.addWidget(QLabel("Прозрачность:"))
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setMaximumWidth(100)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        self.opacity_slider.setToolTip("Настройка прозрачности окна")
        toolbar_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel("100%")
        toolbar_layout.addWidget(self.opacity_label)
        
        toolbar_layout.addStretch()
        
        # Кнопка закрепления
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setToolTip("Закрепить поверх окон")
        self.pin_btn.setCheckable(True)
        self.pin_btn.clicked.connect(self.toggle_stay_on_top)
        self.pin_btn.setMaximumWidth(30)
        toolbar_layout.addWidget(self.pin_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Текстовое поле для логов
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        
        # Стиль для плавающего окна
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(30, 30, 30, 230);
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 3px;
            }
            QTextEdit::selection {
                background-color: #264f78;
            }
        """)
        
        layout.addWidget(self.log_text)
        
        # Устанавливаем виджет
        self.setWidget(container)
        
        # Минимальный размер
        self.setMinimumSize(300, 200)
        
        # Подключаемся к единому менеджеру логирования
        if self.parent_window:
            try:
                from ..utils.unified_logger import get_log_manager
                self.log_manager = get_log_manager()
                # Подписываемся на получение логов
                self.log_manager.subscribe(self.add_log)
                
                # Загружаем историю логов
                history = self.log_manager.get_history()
                for timestamp, message, level in history:
                    self.add_log(message, level)
            except ImportError:
                # Fallback на старую синхронизацию
                self.sync_timer = QTimer()
                self.sync_timer.timeout.connect(self.sync_with_parent)
                self.sync_timer.start(500)  # Обновление каждые 500мс
            
    def add_log(self, message: str, level: str = "INFO"):
        """Добавление лога в окно"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Цветовая схема
        colors = {
            "DEBUG": "#888",
            "INFO": "#ff8c00",
            "SUCCESS": "#0a0",
            "WARNING": "#f90",
            "ERROR": "#f00",
            "SALE": "#00ff88",
            "PROFIT": "#00ffff"
        }
        
        color = colors.get(level, "#ff8c00")
        formatted_message = f'<span style="color: {color}">[{timestamp}] {message}</span>'
        
        # Сохраняем позицию курсора
        scrollbar = self.log_text.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
        
        # Добавляем текст
        self.log_text.append(formatted_message)
        
        # Прокручиваем вниз если нужно
        if self.autoscroll_cb.isChecked() and was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
            
    def change_opacity(self, value):
        """Изменение прозрачности окна"""
        self.opacity_label.setText(f"{value}%")
        if self.isFloating():
            self.setWindowOpacity(value / 100.0)
            
    def toggle_stay_on_top(self):
        """Переключение режима поверх всех окон"""
        if self.pin_btn.isChecked():
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.pin_btn.setStyleSheet("background-color: #4CAF50;")
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.pin_btn.setStyleSheet("")
        self.show()
        
    def sync_with_parent(self):
        """Синхронизация с логами главного окна"""
        if not self.sync_cb.isChecked() or not self.parent_window:
            return
            
        try:
            parent_logs = self.parent_window.log_area.toHtml()
            current_logs = self.log_text.toHtml()
            
            if parent_logs != current_logs:
                scrollbar = self.log_text.verticalScrollBar()
                was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
                
                self.log_text.setHtml(parent_logs)
                
                if self.autoscroll_cb.isChecked() and was_at_bottom:
                    scrollbar.setValue(scrollbar.maximum())
        except:
            pass
            
    def clear_logs(self):
        """Очистка логов"""
        self.log_text.clear()
        
    def export_logs(self):
        """Экспорт логов"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить логи",
            f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                QMessageBox.information(self, "Успех", "Логи экспортированы")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {e}")
                
    def copy_all(self):
        """Копирование всех логов"""
        self.log_text.selectAll()
        self.log_text.copy()


# Импорты перенесены в начало файла
