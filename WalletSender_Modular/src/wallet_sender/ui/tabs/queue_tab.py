"""
Вкладка управления очередью задач с полным функционалом
"""

import threading
import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QProgressBar,
    QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QHeaderView,
    QAbstractItemView, QMessageBox, QMenu, QApplication,
    QFileDialog, QCheckBox, QSplitter
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt5.QtGui import QColor

from .base_tab import BaseTab
from ...database.database import DatabaseManager
from ...utils.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Статусы задач"""
    PENDING = "В ожидании"
    RUNNING = "Выполняется"
    PAUSED = "Приостановлено"
    COMPLETED = "Завершено"
    FAILED = "Ошибка"
    CANCELLED = "Отменено"


class TaskType(Enum):
    """Типы задач"""
    SEND_TOKEN = "Отправка токенов"
    SEND_BNB = "Отправка BNB"
    MASS_DISTRIBUTION = "Массовая рассылка"
    REWARD = "Отправка награды"
    SWAP = "Обмен токенов"
    CHECK_BALANCE = "Проверка баланса"
    OTHER = "Другое"


class QueueTab(BaseTab):
    """Вкладка управления очередью операций"""
    
    # Сигналы
    task_added_signal = pyqtSignal(dict)
    task_updated_signal = pyqtSignal(str, str, str)  # task_id, status, message
    task_completed_signal = pyqtSignal(str, bool)  # task_id, success
    queue_updated_signal = pyqtSignal()
    
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        
        # Инициализация
        self.database = DatabaseManager()
        self.task_queue = []
        self.current_task = None
        self.is_processing = False
        self.stop_processing_event = threading.Event()
        self.pause_processing_event = threading.Event()
        self.processing_thread = None
        
        # Подключение сигналов
        self.task_added_signal.connect(self._on_task_added)
        self.task_updated_signal.connect(self._on_task_updated)
        self.task_completed_signal.connect(self._on_task_completed)
        self.queue_updated_signal.connect(self._update_queue_display)
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QGroupBox("Очередь задач")
        header_layout = QVBoxLayout(header)
        header_label = QLabel("📋 Управление очередью операций")
        header_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        header_layout.addWidget(header_label)
        layout.addWidget(header)
        
        # Splitter для основного контента
        splitter = QSplitter(Qt.Vertical)
        
        # Верхняя часть - активная очередь
        active_widget = self._create_active_queue_panel()
        splitter.addWidget(active_widget)
        
        # Нижняя часть - завершенные задачи
        completed_widget = self._create_completed_tasks_panel()
        splitter.addWidget(completed_widget)
        
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)
        
        # Панель управления
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
        
        # Статистика
        stats_panel = self._create_statistics_panel()
        layout.addWidget(stats_panel)
        
        # Лог выполнения
        log_group = QGroupBox("Лог выполнения")
        log_layout = QVBoxLayout(log_group)
        
        self.execution_log = QTextEdit()
        self.execution_log.setReadOnly(True)
        self.execution_log.setMaximumHeight(100)
        log_layout.addWidget(self.execution_log)
        
        layout.addWidget(log_group)
        
        # Загружаем задачи из базы данных
        self._load_tasks_from_database()
        
    def _create_active_queue_panel(self) -> QWidget:
        """Создание панели активной очереди"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("🔄 Активная очередь"))
        
        # Кнопки фильтрации
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['Все', 'В ожидании', 'Выполняется', 'Приостановлено', 'Ошибка'])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        header_layout.addWidget(QLabel("Фильтр:"))
        header_layout.addWidget(self.filter_combo)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Таблица активных задач
        self.active_table = QTableWidget(0, 9)
        self.active_table.setHorizontalHeaderLabels([
            'ID', 'Тип', 'Описание', 'Статус', 'Прогресс',
            'Приоритет', 'Создано', 'Начато', 'Действия'
        ])
        
        header = self.active_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.resizeSection(0, 50)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            header.setSectionResizeMode(8, QHeaderView.Fixed)
            header.resizeSection(8, 100)
        
        self.active_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.active_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.active_table.customContextMenuRequested.connect(self._show_active_context_menu)
        
        layout.addWidget(self.active_table)
        
        # Кнопки управления очередью
        buttons_layout = QHBoxLayout()
        
        self.add_task_btn = QPushButton("➕ Добавить задачу")
        self.add_task_btn.clicked.connect(self.add_task_dialog)
        buttons_layout.addWidget(self.add_task_btn)
        
        self.clear_queue_btn = QPushButton("🗑 Очистить очередь")
        self.clear_queue_btn.clicked.connect(self.clear_queue)
        buttons_layout.addWidget(self.clear_queue_btn)
        
        self.export_queue_btn = QPushButton("📤 Экспорт очереди")
        self.export_queue_btn.clicked.connect(self.export_queue)
        buttons_layout.addWidget(self.export_queue_btn)
        
        self.import_queue_btn = QPushButton("📥 Импорт очереди")
        self.import_queue_btn.clicked.connect(self.import_queue)
        buttons_layout.addWidget(self.import_queue_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return widget
        
    def _create_completed_tasks_panel(self) -> QWidget:
        """Создание панели завершенных задач"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("✅ Завершенные задачи"))
        
        self.auto_clear_completed = QCheckBox("Автоочистка через:")
        header_layout.addWidget(self.auto_clear_completed)
        
        self.clear_after_hours = QSpinBox()
        self.clear_after_hours.setRange(1, 168)
        self.clear_after_hours.setValue(24)
        self.clear_after_hours.setSuffix(" ч")
        self.clear_after_hours.setEnabled(False)
        header_layout.addWidget(self.clear_after_hours)
        
        self.auto_clear_completed.toggled.connect(self.clear_after_hours.setEnabled)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Таблица завершенных задач
        self.completed_table = QTableWidget(0, 8)
        self.completed_table.setHorizontalHeaderLabels([
            'ID', 'Тип', 'Описание', 'Статус', 
            'Начато', 'Завершено', 'Длительность', 'Результат'
        ])
        
        header = self.completed_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.resizeSection(0, 50)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        self.completed_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.completed_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.completed_table.customContextMenuRequested.connect(self._show_completed_context_menu)
        
        layout.addWidget(self.completed_table)
        
        # Кнопки управления завершенными
        completed_buttons_layout = QHBoxLayout()
        
        self.clear_completed_btn = QPushButton("🗑 Очистить завершенные")
        self.clear_completed_btn.clicked.connect(self.clear_completed_tasks)
        completed_buttons_layout.addWidget(self.clear_completed_btn)
        
        self.export_completed_btn = QPushButton("📊 Экспорт отчета")
        self.export_completed_btn.clicked.connect(self.export_completed_report)
        completed_buttons_layout.addWidget(self.export_completed_btn)
        
        completed_buttons_layout.addStretch()
        layout.addLayout(completed_buttons_layout)
        
        return widget
        
    def _create_control_panel(self) -> QGroupBox:
        """Создание панели управления"""
        group = QGroupBox("Управление выполнением")
        layout = QHBoxLayout(group)
        
        # Кнопки управления
        self.start_btn = QPushButton("▶️ Запустить обработку")
        self.start_btn.clicked.connect(self.start_processing)
        layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸ Приостановить")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_processing)
        layout.addWidget(self.pause_btn)
        
        self.resume_btn = QPushButton("▶️ Продолжить")
        self.resume_btn.setEnabled(False)
        self.resume_btn.clicked.connect(self.resume_processing)
        layout.addWidget(self.resume_btn)
        
        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_processing)
        layout.addWidget(self.stop_btn)
        
        layout.addStretch()
        
        # Настройки обработки
        layout.addWidget(QLabel("Задержка между задачами:"))
        
        self.task_delay = QDoubleSpinBox()
        self.task_delay.setRange(0, 60)
        self.task_delay.setValue(1)
        self.task_delay.setSingleStep(0.5)
        self.task_delay.setSuffix(" сек")
        layout.addWidget(self.task_delay)
        
        self.auto_retry = QCheckBox("Автоповтор при ошибке")
        self.auto_retry.setChecked(True)
        layout.addWidget(self.auto_retry)
        
        self.max_retries = QSpinBox()
        self.max_retries.setRange(1, 10)
        self.max_retries.setValue(3)
        self.max_retries.setPrefix("Макс: ")
        self.max_retries.setEnabled(self.auto_retry.isChecked())
        layout.addWidget(self.max_retries)
        
        self.auto_retry.toggled.connect(self.max_retries.setEnabled)
        
        return group
        
    def _create_statistics_panel(self) -> QGroupBox:
        """Создание панели статистики"""
        group = QGroupBox("Статистика")
        layout = QHBoxLayout(group)
        
        # Счетчики
        self.total_tasks_label = QLabel("Всего задач: 0")
        layout.addWidget(self.total_tasks_label)
        
        self.pending_tasks_label = QLabel("В ожидании: 0")
        layout.addWidget(self.pending_tasks_label)
        
        self.running_tasks_label = QLabel("Выполняется: 0")
        layout.addWidget(self.running_tasks_label)
        
        self.completed_tasks_label = QLabel("Завершено: 0")
        layout.addWidget(self.completed_tasks_label)
        
        self.failed_tasks_label = QLabel("Ошибок: 0")
        layout.addWidget(self.failed_tasks_label)
        
        layout.addStretch()
        
        # Прогресс
        self.overall_progress = QProgressBar()
        self.overall_progress.setMaximumWidth(200)
        layout.addWidget(QLabel("Общий прогресс:"))
        layout.addWidget(self.overall_progress)
        
        return group
        
    def add_task(self, task_type: TaskType, description: str, 
                 params: Dict[str, Any], priority: int = 5) -> str:
        """Добавление задачи в очередь"""
        task = {
            'id': f"TASK_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.task_queue)}",
            'type': task_type.value,
            'description': description,
            'params': params,
            'priority': priority,
            'status': TaskStatus.PENDING.value,
            'progress': 0,
            'created_at': datetime.now(),
            'started_at': None,
            'completed_at': None,
            'result': None,
            'error': None,
            'retries': 0
        }
        
        # Добавляем в очередь с учетом приоритета
        inserted = False
        for i, existing_task in enumerate(self.task_queue):
            if existing_task['priority'] < priority:
                self.task_queue.insert(i, task)
                inserted = True
                break
                
        if not inserted:
            self.task_queue.append(task)
            
        # Сохраняем в базу данных
        self._save_task_to_database(task)
        
        # Отправляем сигнал
        self.task_added_signal.emit(task)
        
        self._log_execution(f"➕ Добавлена задача: {task['id']} - {description}")
        
        return task['id']
        
    def add_task_dialog(self):
        """Диалог добавления задачи"""
        from PyQt5.QtWidgets import QDialog, QFormLayout, QDialogButtonBox, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить задачу")
        dialog.resize(500, 400)
        
        layout = QFormLayout(dialog)
        
        # Тип задачи
        type_combo = QComboBox()
        type_combo.addItems([t.value for t in TaskType])
        layout.addRow("Тип задачи:", type_combo)
        
        # Описание
        description_input = QLineEdit()
        layout.addRow("Описание:", description_input)
        
        # Приоритет
        priority_spin = QSpinBox()
        priority_spin.setRange(1, 10)
        priority_spin.setValue(5)
        layout.addRow("Приоритет:", priority_spin)
        
        # Параметры (JSON)
        layout.addRow(QLabel("Параметры (JSON):"))
        params_input = QTextEdit()
        params_input.setPlainText('{\n  \n}')
        layout.addRow(params_input)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            try:
                # Парсим параметры
                params_text = params_input.toPlainText()
                params = json.loads(params_text) if params_text.strip() else {}
                
                # Создаем задачу
                task_type = TaskType(type_combo.currentText())
                description = description_input.text() or f"Задача {task_type.value}"
                priority = priority_spin.value()
                
                task_id = self.add_task(task_type, description, params, priority)
                
                self.log(f"Добавлена задача: {task_id}", "SUCCESS")
                QMessageBox.information(self, "Успех", f"Задача добавлена в очередь:\n{task_id}")
                
            except json.JSONDecodeError as e:
                QMessageBox.critical(self, "Ошибка", f"Неверный формат JSON параметров:\n{str(e)}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка добавления задачи:\n{str(e)}")
                
    def start_processing(self):
        """Запуск обработки очереди"""
        if self.is_processing:
            QMessageBox.warning(self, "Предупреждение", "Обработка уже запущена!")
            return
            
        if not self.task_queue:
            QMessageBox.information(self, "Информация", "Очередь задач пуста!")
            return
            
        self.is_processing = True
        self.stop_processing_event.clear()
        self.pause_processing_event.clear()
        
        # Обновляем UI
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        # Запускаем поток обработки
        self.processing_thread = threading.Thread(
            target=self._processing_worker,
            daemon=True
        )
        self.processing_thread.start()
        
        self.log("▶️ Запущена обработка очереди", "SUCCESS")
        
    def pause_processing(self):
        """Приостановка обработки"""
        if self.is_processing:
            self.pause_processing_event.set()
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(True)
            self.log("⏸ Обработка приостановлена", "WARNING")
            
    def resume_processing(self):
        """Возобновление обработки"""
        if self.is_processing:
            self.pause_processing_event.clear()
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(False)
            self.log("▶️ Обработка возобновлена", "SUCCESS")
            
    def stop_processing(self):
        """Остановка обработки"""
        if self.is_processing:
            self.stop_processing_event.set()
            self.pause_processing_event.clear()
            self.log("⏹ Остановка обработки...", "WARNING")
            
    def _processing_worker(self):
        """Рабочий поток обработки задач"""
        try:
            while self.task_queue and not self.stop_processing_event.is_set():
                # Проверяем паузу
                while self.pause_processing_event.is_set():
                    if self.stop_processing_event.is_set():
                        break
                    time.sleep(0.1)
                    
                if self.stop_processing_event.is_set():
                    break
                    
                # Получаем следующую задачу с статусом PENDING
                next_task = None
                for task in self.task_queue:
                    if task['status'] == TaskStatus.PENDING.value:
                        next_task = task
                        break
                        
                if not next_task:
                    self._log_execution("Нет задач для выполнения")
                    break
                    
                # Выполняем задачу
                self.current_task = next_task
                self._execute_task(next_task)
                
                # Задержка между задачами
                time.sleep(self.task_delay.value())
                
        except Exception as e:
            logger.error(f"Ошибка в потоке обработки: {e}")
            self._log_execution(f"❌ Критическая ошибка: {str(e)}")
            
        finally:
            self.is_processing = False
            self.current_task = None
            QTimer.singleShot(0, self._on_processing_finished)
            
    def _execute_task(self, task: Dict):
        """Выполнение задачи"""
        try:
            # Обновляем статус
            task['status'] = TaskStatus.RUNNING.value
            task['started_at'] = datetime.now()
            self.task_updated_signal.emit(task['id'], TaskStatus.RUNNING.value, "Выполняется")
            
            # Имитация выполнения задачи (здесь должна быть реальная логика)
            # В реальной реализации здесь вызываются соответствующие методы
            # в зависимости от типа задачи
            
            self._log_execution(f"🔄 Выполнение задачи: {task['id']}")
            
            # Имитация прогресса
            for i in range(0, 101, 20):
                if self.stop_processing_event.is_set():
                    task['status'] = TaskStatus.CANCELLED.value
                    self.task_updated_signal.emit(task['id'], TaskStatus.CANCELLED.value, "Отменено")
                    return
                    
                task['progress'] = i
                self.task_updated_signal.emit(task['id'], TaskStatus.RUNNING.value, f"Прогресс: {i}%")
                time.sleep(0.5)
                
            # Задача выполнена успешно
            task['status'] = TaskStatus.COMPLETED.value
            task['completed_at'] = datetime.now()
            task['progress'] = 100
            task['result'] = "Успешно выполнено"
            
            self.task_completed_signal.emit(task['id'], True)
            self._log_execution(f"✅ Задача выполнена: {task['id']}")
            
        except Exception as e:
            logger.error(f"Ошибка выполнения задачи {task['id']}: {e}")
            
            task['status'] = TaskStatus.FAILED.value
            task['error'] = str(e)
            task['retries'] += 1
            
            # Проверяем автоповтор
            if self.auto_retry.isChecked() and task['retries'] < self.max_retries.value():
                task['status'] = TaskStatus.PENDING.value
                self._log_execution(f"🔄 Повтор задачи {task['id']} (попытка {task['retries']})")
            else:
                self.task_completed_signal.emit(task['id'], False)
                self._log_execution(f"❌ Ошибка задачи {task['id']}: {str(e)}")
                
    def _on_processing_finished(self):
        """Обработка завершения обработки"""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        self.log("Обработка очереди завершена", "SUCCESS")
        self._update_statistics()
        
    @pyqtSlot(dict)
    def _on_task_added(self, task: Dict):
        """Обработка добавления задачи"""
        # Добавляем в таблицу активных
        row = self.active_table.rowCount()
        self.active_table.insertRow(row)
        
        self.active_table.setItem(row, 0, QTableWidgetItem(task['id']))
        self.active_table.setItem(row, 1, QTableWidgetItem(task['type']))
        self.active_table.setItem(row, 2, QTableWidgetItem(task['description']))
        
        status_item = QTableWidgetItem(task['status'])
        self._set_status_color(status_item, task['status'])
        self.active_table.setItem(row, 3, status_item)
        
        self.active_table.setItem(row, 4, QTableWidgetItem(f"{task['progress']}%"))
        self.active_table.setItem(row, 5, QTableWidgetItem(str(task['priority'])))
        
        created_str = task['created_at'].strftime('%H:%M:%S')
        self.active_table.setItem(row, 6, QTableWidgetItem(created_str))
        
        self.active_table.setItem(row, 7, QTableWidgetItem("-"))
        
        # Добавляем кнопки действий
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        cancel_btn = QPushButton("❌")
        cancel_btn.setMaximumSize(25, 25)
        cancel_btn.clicked.connect(lambda: self._cancel_task(task['id']))
        actions_layout.addWidget(cancel_btn)
        
        self.active_table.setCellWidget(row, 8, actions_widget)
        
        self._update_statistics()
        
    @pyqtSlot(str, str, str)
    def _on_task_updated(self, task_id: str, status: str, message: str):
        """Обработка обновления задачи"""
        # Находим задачу в таблице
        for row in range(self.active_table.rowCount()):
            if self.active_table.item(row, 0).text() == task_id:
                # Обновляем статус
                status_item = self.active_table.item(row, 3)
                status_item.setText(status)
                self._set_status_color(status_item, status)
                
                # Обновляем прогресс
                task = next((t for t in self.task_queue if t['id'] == task_id), None)
                if task:
                    self.active_table.item(row, 4).setText(f"{task['progress']}%")
                    
                    # Обновляем время начала
                    if task['started_at']:
                        started_str = task['started_at'].strftime('%H:%M:%S')
                        self.active_table.item(row, 7).setText(started_str)
                        
                break
                
        self._update_statistics()
        
    @pyqtSlot(str, bool)
    def _on_task_completed(self, task_id: str, success: bool):
        """Обработка завершения задачи"""
        # Находим задачу
        task = next((t for t in self.task_queue if t['id'] == task_id), None)
        if not task:
            return
            
        # Перемещаем в завершенные
        self._move_to_completed(task)
        
        # Удаляем из активной таблицы
        for row in range(self.active_table.rowCount()):
            if self.active_table.item(row, 0).text() == task_id:
                self.active_table.removeRow(row)
                break
                
        # Удаляем из очереди
        self.task_queue.remove(task)
        
        self._update_statistics()
        
    def _move_to_completed(self, task: Dict):
        """Перемещение задачи в завершенные"""
        row = self.completed_table.rowCount()
        self.completed_table.insertRow(row)
        
        self.completed_table.setItem(row, 0, QTableWidgetItem(task['id']))
        self.completed_table.setItem(row, 1, QTableWidgetItem(task['type']))
        self.completed_table.setItem(row, 2, QTableWidgetItem(task['description']))
        
        status_item = QTableWidgetItem(task['status'])
        self._set_status_color(status_item, task['status'])
        self.completed_table.setItem(row, 3, status_item)
        
        # Время начала
        started_str = task['started_at'].strftime('%H:%M:%S') if task['started_at'] else "-"
        self.completed_table.setItem(row, 4, QTableWidgetItem(started_str))
        
        # Время завершения
        completed_str = task['completed_at'].strftime('%H:%M:%S') if task['completed_at'] else "-"
        self.completed_table.setItem(row, 5, QTableWidgetItem(completed_str))
        
        # Длительность
        if task['started_at'] and task['completed_at']:
            duration = task['completed_at'] - task['started_at']
            duration_str = str(duration).split('.')[0]
        else:
            duration_str = "-"
        self.completed_table.setItem(row, 6, QTableWidgetItem(duration_str))
        
        # Результат
        result_str = task.get('result', task.get('error', '-'))
        self.completed_table.setItem(row, 7, QTableWidgetItem(result_str))
        
    def _set_status_color(self, item: QTableWidgetItem, status: str):
        """Установка цвета для статуса"""
        colors = {
            TaskStatus.PENDING.value: QColor('#444444'),
            TaskStatus.RUNNING.value: QColor('#004444'),
            TaskStatus.PAUSED.value: QColor('#444400'),
            TaskStatus.COMPLETED.value: QColor('#004400'),
            TaskStatus.FAILED.value: QColor('#440000'),
            TaskStatus.CANCELLED.value: QColor('#440044')
        }
        
        if status in colors:
            item.setBackground(colors[status])
            
    def _update_statistics(self):
        """Обновление статистики"""
        total = len(self.task_queue) + self.completed_table.rowCount()
        pending = sum(1 for t in self.task_queue if t['status'] == TaskStatus.PENDING.value)
        running = sum(1 for t in self.task_queue if t['status'] == TaskStatus.RUNNING.value)
        
        completed = 0
        failed = 0
        
        for row in range(self.completed_table.rowCount()):
            status = self.completed_table.item(row, 3).text()
            if status == TaskStatus.COMPLETED.value:
                completed += 1
            elif status == TaskStatus.FAILED.value:
                failed += 1
                
        self.total_tasks_label.setText(f"Всего задач: {total}")
        self.pending_tasks_label.setText(f"В ожидании: {pending}")
        self.running_tasks_label.setText(f"Выполняется: {running}")
        self.completed_tasks_label.setText(f"Завершено: {completed}")
        self.failed_tasks_label.setText(f"Ошибок: {failed}")
        
        # Обновляем прогресс
        if total > 0:
            progress = int((completed / total) * 100)
            self.overall_progress.setValue(progress)
            
    def _update_queue_display(self):
        """Обновление отображения очереди"""
        self._update_statistics()
        
    def _apply_filter(self, filter_text: str):
        """Применение фильтра к таблице"""
        for row in range(self.active_table.rowCount()):
            status = self.active_table.item(row, 3).text()
            
            if filter_text == "Все":
                self.active_table.setRowHidden(row, False)
            else:
                self.active_table.setRowHidden(row, status != filter_text)
                
    def _cancel_task(self, task_id: str):
        """Отмена задачи"""
        task = next((t for t in self.task_queue if t['id'] == task_id), None)
        if task:
            if task['status'] == TaskStatus.RUNNING.value:
                QMessageBox.warning(self, "Предупреждение", "Нельзя отменить выполняющуюся задачу!")
                return
                
            task['status'] = TaskStatus.CANCELLED.value
            self.task_completed_signal.emit(task_id, False)
            self.log(f"Задача {task_id} отменена", "WARNING")
            
    def _show_active_context_menu(self, position):
        """Контекстное меню для активных задач"""
        if self.active_table.currentRow() < 0:
            return
            
        menu = QMenu()
        
        view_details = menu.addAction("🔍 Подробности")
        edit_task = menu.addAction("✏️ Редактировать")
        menu.addSeparator()
        move_up = menu.addAction("⬆️ Повысить приоритет")
        move_down = menu.addAction("⬇️ Понизить приоритет")
        menu.addSeparator()
        cancel_task = menu.addAction("❌ Отменить задачу")
        
        action = menu.exec_(self.active_table.viewport().mapToGlobal(position))
        
        if action:
            row = self.active_table.currentRow()
            task_id = self.active_table.item(row, 0).text()
            
            if action == view_details:
                self._show_task_details(task_id)
            elif action == edit_task:
                self._edit_task(task_id)
            elif action == move_up:
                self._change_task_priority(task_id, 1)
            elif action == move_down:
                self._change_task_priority(task_id, -1)
            elif action == cancel_task:
                self._cancel_task(task_id)
                
    def _show_completed_context_menu(self, position):
        """Контекстное меню для завершенных задач"""
        if self.completed_table.currentRow() < 0:
            return
            
        menu = QMenu()
        
        view_details = menu.addAction("🔍 Подробности")
        retry_task = menu.addAction("🔄 Повторить задачу")
        menu.addSeparator()
        remove_task = menu.addAction("🗑 Удалить")
        
        action = menu.exec_(self.completed_table.viewport().mapToGlobal(position))
        
        if action:
            row = self.completed_table.currentRow()
            # Здесь можно добавить соответствующие действия
            
    def _show_task_details(self, task_id: str):
        """Показ подробностей задачи"""
        task = next((t for t in self.task_queue if t['id'] == task_id), None)
        if not task:
            return
            
        details = f"""
ID задачи: {task['id']}
Тип: {task['type']}
Описание: {task['description']}
Статус: {task['status']}
Прогресс: {task['progress']}%
Приоритет: {task['priority']}
Создано: {task['created_at']}
Начато: {task['started_at'] or 'Не начато'}
Завершено: {task['completed_at'] or 'Не завершено'}
Попыток: {task['retries']}

Параметры:
{json.dumps(task['params'], indent=2, ensure_ascii=False)}
        """
        
        QMessageBox.information(self, "Подробности задачи", details)
        
    def _edit_task(self, task_id: str):
        """Редактирование задачи"""
        task = next((t for t in self.task_queue if t['id'] == task_id), None)
        if not task:
            return
            
        if task['status'] != TaskStatus.PENDING.value:
            QMessageBox.warning(self, "Предупреждение", "Можно редактировать только задачи в ожидании!")
            return
            
        # Здесь можно добавить диалог редактирования
        
    def _change_task_priority(self, task_id: str, delta: int):
        """Изменение приоритета задачи"""
        task = next((t for t in self.task_queue if t['id'] == task_id), None)
        if task:
            task['priority'] = max(1, min(10, task['priority'] + delta))
            
            # Пересортировка очереди
            self.task_queue.sort(key=lambda t: t['priority'], reverse=True)
            
            # Обновление отображения
            self._refresh_active_table()
            
            self.log(f"Приоритет задачи {task_id} изменен на {task['priority']}", "INFO")
            
    def _refresh_active_table(self):
        """Обновление таблицы активных задач"""
        self.active_table.setRowCount(0)
        
        for task in self.task_queue:
            self._on_task_added(task)
            
    def clear_queue(self):
        """Очистка очереди"""
        if not self.task_queue:
            return
            
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Очистить очередь ({len(self.task_queue)} задач)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Очищаем только задачи не в процессе выполнения
            tasks_to_remove = [t for t in self.task_queue 
                             if t['status'] != TaskStatus.RUNNING.value]
            
            for task in tasks_to_remove:
                self.task_queue.remove(task)
                
            self.active_table.setRowCount(0)
            self._refresh_active_table()
            
            self.log(f"Очередь очищена ({len(tasks_to_remove)} задач)", "INFO")
            
    def clear_completed_tasks(self):
        """Очистка завершенных задач"""
        if self.completed_table.rowCount() == 0:
            return
            
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Очистить завершенные задачи ({self.completed_table.rowCount()})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.completed_table.setRowCount(0)
            self.log("Завершенные задачи очищены", "INFO")
            self._update_statistics()
            
    def export_queue(self):
        """Экспорт очереди в файл"""
        if not self.task_queue:
            QMessageBox.warning(self, "Предупреждение", "Очередь пуста!")
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт очереди",
            f"queue_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if path:
            try:
                # Подготавливаем данные для экспорта
                export_data = []
                for task in self.task_queue:
                    task_copy = task.copy()
                    # Конвертируем datetime в строки
                    for key in ['created_at', 'started_at', 'completed_at']:
                        if task_copy[key]:
                            task_copy[key] = task_copy[key].isoformat()
                    export_data.append(task_copy)
                    
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                    
                self.log(f"✅ Экспортировано {len(export_data)} задач", "SUCCESS")
                QMessageBox.information(self, "Успех", f"Очередь экспортирована в:\n{path}")
                
            except Exception as e:
                logger.error(f"Ошибка экспорта очереди: {e}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта:\n{str(e)}")
                
    def import_queue(self):
        """Импорт очереди из файла"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт очереди",
            "",
            "JSON Files (*.json)"
        )
        
        if not path:
            return
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
                
            imported = 0
            for task_data in import_data:
                # Конвертируем строки обратно в datetime
                for key in ['created_at', 'started_at', 'completed_at']:
                    if task_data[key]:
                        task_data[key] = datetime.fromisoformat(task_data[key])
                        
                # Генерируем новый ID чтобы избежать конфликтов
                task_data['id'] = f"IMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{imported}"
                
                # Сбрасываем статус на PENDING
                task_data['status'] = TaskStatus.PENDING.value
                task_data['progress'] = 0
                
                self.task_queue.append(task_data)
                self._on_task_added(task_data)
                imported += 1
                
            self.log(f"✅ Импортировано {imported} задач", "SUCCESS")
            QMessageBox.information(self, "Успех", f"Импортировано {imported} задач")
            
        except Exception as e:
            logger.error(f"Ошибка импорта очереди: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка импорта:\n{str(e)}")
            
    def export_completed_report(self):
        """Экспорт отчета по завершенным задачам"""
        if self.completed_table.rowCount() == 0:
            QMessageBox.warning(self, "Предупреждение", "Нет завершенных задач!")
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт отчета",
            f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if path:
            try:
                import csv
                
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Заголовки
                    headers = []
                    for col in range(self.completed_table.columnCount()):
                        headers.append(self.completed_table.horizontalHeaderItem(col).text())
                    writer.writerow(headers)
                    
                    # Данные
                    for row in range(self.completed_table.rowCount()):
                        row_data = []
                        for col in range(self.completed_table.columnCount()):
                            item = self.completed_table.item(row, col)
                            row_data.append(item.text() if item else '')
                        writer.writerow(row_data)
                        
                self.log(f"✅ Экспортирован отчет по {self.completed_table.rowCount()} задачам", "SUCCESS")
                QMessageBox.information(self, "Успех", f"Отчет экспортирован в:\n{path}")
                
            except Exception as e:
                logger.error(f"Ошибка экспорта отчета: {e}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта:\n{str(e)}")
                
    def _log_execution(self, message: str):
        """Логирование выполнения"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        QTimer.singleShot(0, lambda: self.execution_log.append(f"[{timestamp}] {message}"))
        
    def _save_task_to_database(self, task: Dict):
        """Сохранение задачи в базу данных"""
        try:
            # Здесь должна быть логика сохранения в БД
            pass
        except Exception as e:
            logger.error(f"Ошибка сохранения задачи в БД: {e}")
            
    def _load_tasks_from_database(self):
        """Загрузка задач из базы данных"""
        try:
            # Здесь должна быть логика загрузки из БД
            # Пока загружаем пустой список
            self.task_queue = []
        except Exception as e:
            logger.error(f"Ошибка загрузки задач из БД: {e}")
