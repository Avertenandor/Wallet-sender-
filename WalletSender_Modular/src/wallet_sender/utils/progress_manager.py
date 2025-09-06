"""
Менеджер прогресса и уведомлений
"""

import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QProgressBar, QLabel, QWidget, QVBoxLayout, QHBoxLayout

class ProgressStatus(Enum):
    """Статусы прогресса"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ProgressTask:
    """Задача с прогрессом"""
    task_id: str
    title: str
    description: str
    status: ProgressStatus
    progress: int  # 0-100
    start_time: float
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class ProgressManager(QObject):
    """Менеджер прогресса операций"""
    
    # Сигналы для обновления UI
    task_started = pyqtSignal(str, str, str)  # task_id, title, description
    task_progress = pyqtSignal(str, int)  # task_id, progress
    task_completed = pyqtSignal(str, bool, str)  # task_id, success, message
    task_cancelled = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, ProgressTask] = {}
        self._lock = threading.RLock()
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_progress)
        self._update_timer.start(100)  # Обновляем каждые 100мс
        
        # Callbacks для уведомлений
        self.notification_callbacks: List[Callable] = []
    
    def start_task(self, task_id: str, title: str, description: str = "") -> None:
        """Начинает новую задачу"""
        with self._lock:
            task = ProgressTask(
                task_id=task_id,
                title=title,
                description=description,
                status=ProgressStatus.RUNNING,
                progress=0,
                start_time=time.time()
            )
            self.tasks[task_id] = task
        
        self.task_started.emit(task_id, title, description)
        self._notify(f"Начата задача: {title}")
    
    def update_progress(self, task_id: str, progress: int, description: str = "") -> None:
        """Обновляет прогресс задачи"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.progress = max(0, min(100, progress))
                if description:
                    task.description = description
        
        self.task_progress.emit(task_id, progress)
    
    def complete_task(self, task_id: str, success: bool = True, message: str = "") -> None:
        """Завершает задачу"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
                task.progress = 100 if success else task.progress
                task.end_time = time.time()
                if message:
                    task.error_message = message
        
        self.task_completed.emit(task_id, success, message)
        
        if success:
            self._notify(f"Задача завершена: {self.tasks.get(task_id, {}).get('title', task_id)}")
        else:
            self._notify(f"Ошибка в задаче: {message}", "error")
    
    def cancel_task(self, task_id: str) -> None:
        """Отменяет задачу"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = ProgressStatus.CANCELLED
                task.end_time = time.time()
        
        self.task_cancelled.emit(task_id)
        self._notify(f"Задача отменена: {self.tasks.get(task_id, {}).get('title', task_id)}", "warning")
    
    def get_task(self, task_id: str) -> Optional[ProgressTask]:
        """Получает задачу по ID"""
        with self._lock:
            return self.tasks.get(task_id)
    
    def get_active_tasks(self) -> List[ProgressTask]:
        """Получает активные задачи"""
        with self._lock:
            return [task for task in self.tasks.values() 
                   if task.status == ProgressStatus.RUNNING]
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Получает статистику задач"""
        with self._lock:
            total = len(self.tasks)
            active = len([t for t in self.tasks.values() if t.status == ProgressStatus.RUNNING])
            completed = len([t for t in self.tasks.values() if t.status == ProgressStatus.COMPLETED])
            failed = len([t for t in self.tasks.values() if t.status == ProgressStatus.FAILED])
            cancelled = len([t for t in self.tasks.values() if t.status == ProgressStatus.CANCELLED])
            
            return {
                'total': total,
                'active': active,
                'completed': completed,
                'failed': failed,
                'cancelled': cancelled
            }
    
    def clear_completed_tasks(self) -> None:
        """Очищает завершенные задачи"""
        with self._lock:
            completed_ids = [task_id for task_id, task in self.tasks.items()
                           if task.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]]
            
            for task_id in completed_ids:
                del self.tasks[task_id]
    
    def _update_progress(self) -> None:
        """Обновляет прогресс (вызывается таймером)"""
        # Здесь можно добавить логику автоматического обновления прогресса
        pass
    
    def _notify(self, message: str, level: str = "info") -> None:
        """Отправляет уведомление"""
        for callback in self.notification_callbacks:
            try:
                callback(message, level)
            except Exception:
                pass
    
    def add_notification_callback(self, callback: Callable[[str, str], None]) -> None:
        """Добавляет callback для уведомлений"""
        self.notification_callbacks.append(callback)
    
    def remove_notification_callback(self, callback: Callable[[str, str], None]) -> None:
        """Удаляет callback для уведомлений"""
        if callback in self.notification_callbacks:
            self.notification_callbacks.remove(callback)

class ProgressWidget(QWidget):
    """Виджет для отображения прогресса"""
    
    def __init__(self, progress_manager: ProgressManager, parent=None):
        super().__init__(parent)
        self.progress_manager = progress_manager
        self.progress_bars: Dict[str, QProgressBar] = {}
        self.progress_labels: Dict[str, QLabel] = {}
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Настраивает UI"""
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        
        # Заголовок
        self.title_label = QLabel("Прогресс операций")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.layout.addWidget(self.title_label)
        
        # Контейнер для прогресс-баров
        self.progress_container = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_container)
        self.layout.addWidget(self.progress_container)
    
    def connect_signals(self):
        """Подключает сигналы"""
        self.progress_manager.task_started.connect(self.on_task_started)
        self.progress_manager.task_progress.connect(self.on_task_progress)
        self.progress_manager.task_completed.connect(self.on_task_completed)
        self.progress_manager.task_cancelled.connect(self.on_task_cancelled)
    
    def on_task_started(self, task_id: str, title: str, description: str):
        """Обработчик начала задачи"""
        # Создаем прогресс-бар
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        
        # Создаем лейбл
        label = QLabel(f"{title}: {description}")
        label.setStyleSheet("font-size: 12px;")
        
        # Добавляем в layout
        self.progress_layout.addWidget(label)
        self.progress_layout.addWidget(progress_bar)
        
        # Сохраняем ссылки
        self.progress_bars[task_id] = progress_bar
        self.progress_labels[task_id] = label
    
    def on_task_progress(self, task_id: str, progress: int):
        """Обработчик обновления прогресса"""
        if task_id in self.progress_bars:
            self.progress_bars[task_id].setValue(progress)
    
    def on_task_completed(self, task_id: str, success: bool, message: str):
        """Обработчик завершения задачи"""
        if task_id in self.progress_bars:
            progress_bar = self.progress_bars[task_id]
            label = self.progress_labels[task_id]
            
            if success:
                progress_bar.setValue(100)
                progress_bar.setStyleSheet("QProgressBar::chunk { background-color: green; }")
                label.setText(f"✅ {label.text()}")
            else:
                progress_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
                label.setText(f"❌ {label.text()}: {message}")
    
    def on_task_cancelled(self, task_id: str):
        """Обработчик отмены задачи"""
        if task_id in self.progress_bars:
            progress_bar = self.progress_bars[task_id]
            label = self.progress_labels[task_id]
            
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
            label.setText(f"⏹️ {label.text()}")
    
    def clear_completed(self):
        """Очищает завершенные задачи"""
        completed_tasks = []
        
        for task_id, progress_bar in self.progress_bars.items():
            if progress_bar.value() == 100 or "❌" in self.progress_labels[task_id].text():
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            if task_id in self.progress_bars:
                self.progress_layout.removeWidget(self.progress_bars[task_id])
                self.progress_layout.removeWidget(self.progress_labels[task_id])
                self.progress_bars[task_id].deleteLater()
                self.progress_labels[task_id].deleteLater()
                del self.progress_bars[task_id]
                del self.progress_labels[task_id]

class NotificationManager:
    """Менеджер уведомлений"""
    
    def __init__(self):
        self.notifications: List[Dict[str, Any]] = []
        self.max_notifications = 100
        self._lock = threading.RLock()
    
    def add_notification(self, message: str, level: str = "info", 
                        title: str = "", details: str = "") -> None:
        """Добавляет уведомление"""
        with self._lock:
            notification = {
                'id': f"notif_{int(time.time() * 1000)}",
                'timestamp': time.time(),
                'title': title,
                'message': message,
                'level': level,
                'details': details,
                'read': False
            }
            
            self.notifications.append(notification)
            
            # Ограничиваем количество уведомлений
            if len(self.notifications) > self.max_notifications:
                self.notifications = self.notifications[-self.max_notifications:]
    
    def get_notifications(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Получает уведомления"""
        with self._lock:
            if unread_only:
                return [n for n in self.notifications if not n['read']]
            return self.notifications.copy()
    
    def mark_as_read(self, notification_id: str) -> None:
        """Отмечает уведомление как прочитанное"""
        with self._lock:
            for notification in self.notifications:
                if notification['id'] == notification_id:
                    notification['read'] = True
                    break
    
    def mark_all_as_read(self) -> None:
        """Отмечает все уведомления как прочитанные"""
        with self._lock:
            for notification in self.notifications:
                notification['read'] = True
    
    def clear_notifications(self) -> None:
        """Очищает все уведомления"""
        with self._lock:
            self.notifications.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику уведомлений"""
        with self._lock:
            total = len(self.notifications)
            unread = len([n for n in self.notifications if not n['read']])
            
            levels = {}
            for notification in self.notifications:
                level = notification['level']
                levels[level] = levels.get(level, 0) + 1
            
            return {
                'total': total,
                'unread': unread,
                'by_level': levels
            }

# Глобальные экземпляры
progress_manager = ProgressManager()
notification_manager = NotificationManager()
