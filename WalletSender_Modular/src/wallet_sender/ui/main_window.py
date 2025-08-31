#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главное окно WalletSender Modular
"""

# Всегда используем слой совместимости Qt
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QStatusBar,
    QMenuBar,
    QAction,
    QMenu,
    QMessageBox,
    QProgressBar,
    QTextEdit,
    QScrollBar,
    QSplitter,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QCloseEvent

from ..utils.logger import get_logger
from .. import __version__
from ..config import Config
from ..core.web3_provider import Web3Provider

# Импорт вкладок
# Вкладки импортируем лениво внутри _load_tabs, чтобы избежать создания QWidget до QApplication

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Главное окно приложения WalletSender"""
    
    # Сигналы для логирования
    log_message = pyqtSignal(str, str)  # message, level
    
    def __init__(self):
        super().__init__()
        
        # Инициализация конфигурации
        self.config = Config()
        
        # Инициализация Web3 провайдера
        self.web3_provider = Web3Provider()
        
        # Инициализация UI
        self.init_ui()
        
        # Подключение сигналов
        self.connect_signals()
        
        logger.info(f"🚀 WalletSender Modular v{__version__} запущен")
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Настройка окна
        self.setWindowTitle(f"WalletSender Modular v{__version__} - Production")
        self.setGeometry(100, 100, 1400, 900)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        
        # Заголовок
        self._create_header(main_layout)
        
        # Splitter для вкладок и логов
        try:
            # PyQt6
            splitter = QSplitter(Qt.Orientation.Vertical)  # type: ignore[attr-defined]
        except AttributeError:
            # PyQt5
            splitter = QSplitter(Qt.Vertical)  # type: ignore[attr-defined]
        main_layout.addWidget(splitter)
        
        # Вкладки
        self.tab_widget = QTabWidget()
        splitter.addWidget(self.tab_widget)
        
        # Область логов
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(200)
        splitter.addWidget(self.log_area)
        
        # Установка размеров splitter (70% вкладки, 30% логи)
        splitter.setSizes([700, 200])
        
        # Статус бар
        self._create_status_bar()
        
        # Загрузка вкладок
        self._load_tabs()
        
        # Меню
        self._create_menu()
        
        # Подключение сигналов после создания UI
        self.connect_signals()
        
        logger.info("✅ Пользовательский интерфейс инициализирован")
        
    def _create_header(self, layout):
        """Создание заголовка приложения"""
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        
        # Главный заголовок
        title_label = QLabel(f"🚀 WalletSender Modular v{__version__}")
        # PyQt6: QFont.Weight.Bold, PyQt5: QFont.Bold — используем безопасный доступ
        try:
            # Для PyQt6
            weight = QFont.Weight.Bold  # type: ignore[attr-defined]
        except AttributeError:
            # Для PyQt5
            try:
                weight = QFont.Bold  # type: ignore[attr-defined]
            except AttributeError:
                # Fallback на числовое значение
                weight = 75
        title_font = QFont("Arial", 18)
        title_font.setWeight(weight)
        title_label.setFont(title_font)
        try:
            # PyQt6
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore[attr-defined]
        except AttributeError:
            # PyQt5
            title_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        title_label.setStyleSheet("color: #4CAF50; padding: 10px;")
        header_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Production Edition - Профессиональное решение для BSC")
        try:
            # PyQt6
            subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore[attr-defined]
        except AttributeError:
            # PyQt5
            subtitle_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        subtitle_label.setStyleSheet("color: #666; font-size: 12px;")
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header_widget)
        
    def _create_status_bar(self):
        """Создание статус бара"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Статус подключения к сети
        self.network_status_label = QLabel("🌐 Проверка сети...")
        self.status_bar.addPermanentWidget(self.network_status_label)
        
        # Таймер для проверки сети
        self.network_check_timer = QTimer()
        self.network_check_timer.timeout.connect(self._check_network_connection)
        self.network_check_timer.start(10000)  # Каждые 10 секунд
        
        self.status_bar.showMessage("✅ Готов к работе")
        
    def _check_network_connection(self):
        """Проверка подключения к сети"""
        try:
            if self.web3_provider and self.web3_provider.w3.is_connected():
                self.network_status_label.setText("🟢 BSC подключена")
            else:
                self.network_status_label.setText("🔴 BSC отключена")
        except Exception:
            self.network_status_label.setText("🟡 BSC неизвестно")
    
    def _load_tabs(self):
        """Загрузка вкладок приложения"""
        # Ленивая загрузка модулей вкладок (после создания QApplication)
        from .tabs import (
            AutoBuyTab,
            AutoSalesTab,
            DirectSendTab,
            MassDistributionTab,
            AnalysisTab,
            SearchTab,
            RewardsTab,
            QueueTab,
            HistoryTab,
            SettingsTab,
            FoundTxTab,
        )
        # Массовая рассылка (основная)
        self.mass_distribution_tab = MassDistributionTab(self, slot_number=1)
        self.tab_widget.addTab(self.mass_distribution_tab, "⚽ Массовая рассылка")
        
        # Массовая рассылка 2
        self.mass_distribution_tab2 = MassDistributionTab(self, slot_number=2)
        self.tab_widget.addTab(self.mass_distribution_tab2, "⚽ Массовая рассылка 2")
        
        # Массовая рассылка 3
        self.mass_distribution_tab3 = MassDistributionTab(self, slot_number=3)
        self.tab_widget.addTab(self.mass_distribution_tab3, "⚽ Массовая рассылка 3")
        
        # Прямая отправка
        self.direct_send_tab = DirectSendTab(self)
        self.tab_widget.addTab(self.direct_send_tab, "📫 Прямая отправка")
        
        # Автопокупки
        self.auto_buy_tab = AutoBuyTab(self)
        self.tab_widget.addTab(self.auto_buy_tab, "🛌 Автопокупки")
        
        # Автопродажи
        self.auto_sales_tab = AutoSalesTab(self)
        self.tab_widget.addTab(self.auto_sales_tab, "💰 Автопродажи")
        
        # Анализ
        self.analysis_tab = AnalysisTab(self)
        self.tab_widget.addTab(self.analysis_tab, "🔍 Анализ")
        
        # Поиск
        self.search_tab = SearchTab(self)
        self.tab_widget.addTab(self.search_tab, "🔎 Поиск")
        
        # Награды
        self.rewards_tab = RewardsTab(self)
        self.tab_widget.addTab(self.rewards_tab, "🎁 Награды")
        
        # Очередь
        self.queue_tab = QueueTab(self)
        self.tab_widget.addTab(self.queue_tab, "📋 Очередь")
        
        # История
        self.history_tab = HistoryTab(self)
        self.tab_widget.addTab(self.history_tab, "📜 История")
        
        # Найденные транзакции
        self.found_tx_tab = FoundTxTab(self)
        self.tab_widget.addTab(self.found_tx_tab, "🔍 Найденные TX")
        
        # Настройки
        self.settings_tab = SettingsTab(self)
        self.tab_widget.addTab(self.settings_tab, "⚙️ Настройки")
        
        logger.info(f"📋 Загружено {self.tab_widget.count()} вкладок")
        
    def _create_menu(self) -> None:
        """Создание меню приложения"""
        menubar: QMenuBar = self.menuBar()

        # Меню Файл
        file_menu: QMenu = menubar.addMenu('Файл')

        # Экспорт логов
        export_logs_action = QAction('Экспорт логов', self)
        export_logs_action.triggered.connect(self.export_logs)
        file_menu.addAction(export_logs_action)

        file_menu.addSeparator()

        # Выход
        exit_action = QAction('Выход', self)
        exit_action.triggered.connect(self._on_exit)
        file_menu.addAction(exit_action)

        # Меню Инструменты
        tools_menu: QMenu = menubar.addMenu('Инструменты')

        # Очистить логи
        clear_logs_action = QAction('Очистить логи', self)
        clear_logs_action.triggered.connect(self.clear_logs)
        tools_menu.addAction(clear_logs_action)

        # Меню Помощь
        help_menu: QMenu = menubar.addMenu('Помощь')

        # О программе
        about_action = QAction('О программе', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _on_exit(self) -> None:
        """Аккуратно закрыть окно через QAction without returning bool"""
        self.close()
        
    def connect_signals(self):
        """Подключение сигналов"""
        self.log_message.connect(self.add_log)
        
    @pyqtSlot(str, str)
    def add_log(self, message: str, level: str = "INFO") -> None:
        """Добавление сообщения в лог"""
        QTimer().singleShot(0, lambda: self._add_log_impl(message, level))
        
    def _add_log_impl(self, message: str, level: str) -> None:
        """Реализация добавления лога"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Цветовая схема для уровней
        colors = {
            "DEBUG": "#888",
            "INFO": "#000",
            "SUCCESS": "#0a0",
            "WARNING": "#f90",
            "ERROR": "#f00"
        }
        
        color = colors.get(level, "#000")
        formatted_message = f'<span style="color: {color}">[{timestamp}] {message}</span>'
        
        self.log_area.append(formatted_message)
        
        # Прокрутка вниз
        scrollbar: QScrollBar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def export_logs(self):
        """Экспорт логов в файл"""
        try:
            from PyQt6.QtWidgets import QFileDialog
        except ImportError:
            try:
                from PyQt5.QtWidgets import QFileDialog
            except ImportError:
                from PySide6.QtWidgets import QFileDialog
        from datetime import datetime
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить логи",
            f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_area.toPlainText())
                QMessageBox.information(self, "Успех", "Логи успешно экспортированы")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта логов: {e}")
                
    def clear_logs(self):
        """Очистка логов"""
        self.log_area.clear()
        self.add_log("Логи очищены", "INFO")
        
    def show_about(self):
        """Показать информацию о программе"""
        about_text = f"""
        <h2>WalletSender Modular v{__version__}</h2>
        <p><b>Production Edition</b></p>
        <p>Профессиональный инструмент для работы с блокчейном BSC</p>
        <br>
        <p><b>Возможности:</b></p>
        <ul>
            <li>Массовая рассылка токенов (3 независимых слота)</li>
            <li>Прямая отправка токенов</li>
            <li>Автоматические покупки</li>
            <li>Автоматические продажи</li>
            <li>Анализ транзакций</li>
            <li>Поиск и фильтрация</li>
            <li>Система наград</li>
            <li>Управление очередью</li>
            <li>История операций</li>
            <li>Гибкие настройки</li>
        </ul>
        <br>
        <p><b>Технологии:</b></p>
        <ul>
            <li>Python 3.12+</li>
            <li>PyQt5</li>
            <li>Web3.py</li>
            <li>SQLAlchemy</li>
            <li>Etherscan V2 API</li>
        </ul>
        <br>
        <p><b>Разработка:</b> 2025</p>
        <p><b>Версия:</b> {__version__} Production</p>
        """
        
        QMessageBox.about(self, "О программе", about_text)
        
    def show_progress(self, value: int = 0, maximum: int = 100):
        """Показать прогресс в статус баре"""
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
        self.progress_bar.setVisible(value > 0 and value < maximum)
        
    def closeEvent(self, event: QCloseEvent) -> None:
        """Обработка закрытия окна"""
        try:
            # PyQt6
            reply = QMessageBox.question(
                self,
                'Подтверждение',
                'Вы уверены, что хотите выйти?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,  # type: ignore[attr-defined]
                QMessageBox.StandardButton.No  # type: ignore[attr-defined]
            )
            yes_button = QMessageBox.StandardButton.Yes  # type: ignore[attr-defined]
        except AttributeError:
            # PyQt5
            reply = QMessageBox.question(
                self,
                'Подтверждение',
                'Вы уверены, что хотите выйти?',
                QMessageBox.Yes | QMessageBox.No,  # type: ignore[attr-defined]
                QMessageBox.No  # type: ignore[attr-defined]
            )
            yes_button = QMessageBox.Yes  # type: ignore[attr-defined]

        if reply == yes_button:
            # Остановка таймеров
            if hasattr(self, 'network_check_timer'):
                self.network_check_timer.stop()
                
            logger.info("👋 Приложение закрыто")
            event.accept()
        else:
            event.ignore()
