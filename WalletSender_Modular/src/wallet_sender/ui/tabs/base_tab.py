"""
Базовый класс для всех вкладок приложения
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel,
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QFormLayout,
    QMessageBox, QComboBox, QCheckBox
)
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot
from PyQt5.QtGui import QFont

from ...utils.logger import get_logger

logger = get_logger(__name__)

class BaseTab(QWidget):
    """Базовый класс для всех вкладок"""
    
    # Сигналы
    status_updated = pyqtSignal(str)  # Обновление статуса
    progress_updated = pyqtSignal(int)  # Обновление прогресса
    operation_finished = pyqtSignal(str)  # Завершение операции
    
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.shared_db = getattr(main_window, 'shared_db', None) if main_window else None
        self.shared_bsc_api = getattr(main_window, 'shared_bsc_api', None) if main_window else None
        
        # Инициализация UI должна быть в дочерних классах
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Должно быть переопределено в дочерних классах
        pass
    
    def setup_connections(self):
        """Настройка соединений сигналов и слотов"""
        # Должно быть переопределено в дочерних классах
        pass
    
    def create_gas_settings_group(self) -> QGroupBox:
        """Создает группу настроек газа"""
        group = QGroupBox("⛽ Настройки газа")
        layout = QFormLayout()
        
        # Gas Price в Gwei (по умолчанию 0.1)
        self.gas_price_spin = QDoubleSpinBox()
        self.gas_price_spin.setMinimum(0.001)
        self.gas_price_spin.setMaximum(1000.0)
        self.gas_price_spin.setDecimals(3)
        self.gas_price_spin.setValue(0.1)  # По умолчанию 0.1 Gwei
        self.gas_price_spin.setSuffix(" Gwei")
        
        layout.addRow("Gas Price:", self.gas_price_spin)
        group.setLayout(layout)
        
        return group
    
    def get_gas_price_wei(self) -> int:
        """Получает Gas Price в Wei"""
        try:
            gwei = self.gas_price_spin.value()
            # 1 Gwei = 10^9 Wei
            return int(gwei * 10**9)
        except:
            # Фаллбек на 0.1 Gwei
            return 100000000  # 0.1 Gwei в Wei
    
    def get_gas_price_gwei(self) -> float:
        """Получает Gas Price в Gwei"""
        try:
            return self.gas_price_spin.value()
        except:
            return 0.1
    
    def log(self, message: str, level: str = "INFO"):
        """Логирование с предотвращением дублирования"""
        if hasattr(self, '_last_log_message') and self._last_log_message == message:
            return
        
        self._last_log_message = message
        
        # Отправка в главное окно если доступно
        if self.main_window and hasattr(self.main_window, 'add_log'):
            self.main_window.add_log(message, level)
        
        # Локальное логирование
        if level.upper() == "INFO":
            logger.info(f"[{self.__class__.__name__}] {message}")
        elif level.upper() == "WARNING":
            logger.warning(f"[{self.__class__.__name__}] {message}")
        elif level.upper() == "ERROR":
            logger.error(f"[{self.__class__.__name__}] {message}")
        elif level.upper() == "SUCCESS":
            logger.info(f"[{self.__class__.__name__}] ✅ {message}")
    
    def show_success(self, title: str, message: str):
        """Показывает сообщение об успехе"""
        self.log_message(f"SUCCESS: {message}")
        QMessageBox.information(self, title, message)
    
    def show_error(self, title: str, message: str):
        """Показывает сообщение об ошибке"""
        self.log_message(f"ERROR: {message}", "error")
        QMessageBox.critical(self, title, message)
    
    def show_warning(self, title: str, message: str):
        """Показывает предупреждение"""
        self.log_message(f"WARNING: {message}", "warning")
        QMessageBox.warning(self, title, message)
    
    @pyqtSlot(str)
    def update_status(self, status: str):
        """Обновляет статус вкладки"""
        self.status_updated.emit(status)
    
    @pyqtSlot(int)
    def update_progress(self, progress: int):
        """Обновляет прогресс вкладки"""
        self.progress_updated.emit(progress)
    
    @pyqtSlot(str)
    def finish_operation(self, result: str):
        """Завершает операцию"""
        self.operation_finished.emit(result)
    
    def cleanup(self):
        """Очистка ресурсов при закрытии вкладки"""
        # Должно быть переопределено в дочерних классах при необходимости
        pass
