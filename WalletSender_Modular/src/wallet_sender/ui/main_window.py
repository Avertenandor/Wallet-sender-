#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главное окно WalletSender Modular
"""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QLabel, QStatusBar, QMenuBar, QAction,
                             QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from wallet_sender.utils.logger import get_logger

class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("MainWindow")
        self.logger.info("🏗️ Инициализация главного окна")
        
        self.init_ui()
        self.init_services()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Настройка окна
        self.setWindowTitle("WalletSender Modular v2.0")
        self.setGeometry(100, 100, 1200, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        layout = QVBoxLayout(central_widget)
        
        # Заголовок
        title_label = QLabel("🚀 WalletSender Modular v2.0")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Вкладки
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✅ Готов к работе")
        
        # Загрузка вкладок
        self.load_tabs()
        
        self.logger.info("✅ Пользовательский интерфейс инициализирован")
        
    def init_services(self):
        """Инициализация общих сервисов"""
        # TODO: Инициализация БД, API и других сервисов
        self.logger.info("⚙️ Сервисы инициализированы")
        
    def load_tabs(self):
        """Загрузка вкладок приложения"""
        # Пока добавим базовые вкладки
        
        # Заглушка для анализа
        analyze_widget = QWidget()
        analyze_layout = QVBoxLayout(analyze_widget)
        analyze_layout.addWidget(QLabel("📊 Анализ токенов"))
        self.tab_widget.addTab(analyze_widget, "📊 Анализ")
        
        # Заглушка для рассылки
        distribution_widget = QWidget()
        distribution_layout = QVBoxLayout(distribution_widget)
        distribution_layout.addWidget(QLabel("📨 Массовая рассылка"))
        self.tab_widget.addTab(distribution_widget, "📨 Рассылка")
        
        # Заглушка для настроек
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.addWidget(QLabel("⚙️ Настройки"))
        self.tab_widget.addTab(settings_widget, "⚙️ Настройки")
        
        self.logger.info("📋 Вкладки загружены")
        
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.logger.info("👋 Закрытие приложения")
        event.accept()
