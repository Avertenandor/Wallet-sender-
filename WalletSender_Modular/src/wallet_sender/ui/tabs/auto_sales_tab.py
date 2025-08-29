"""Auto Sales Tab - заглушка для автопродаж"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from .base_tab import BaseTab

class AutoSalesTab(BaseTab):
    """Вкладка автоматических продаж токенов"""
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        title_label = QLabel("💰 Автоматические продажи")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 20px;")
        layout.addWidget(title_label)
        
        status_label = QLabel("🚧 Модуль в разработке")
        status_label.setStyleSheet("color: orange; font-size: 14px; padding: 20px;")
        layout.addWidget(status_label)
        
        layout.addStretch()
