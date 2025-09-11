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
    QPushButton,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QCloseEvent

from ..utils.logger import get_logger
from ..utils.unified_logger import get_log_manager, unified_log
from ..utils.logger_enhanced import set_ui_log_handler, log_action, log_click, log_window_action, log_tab_change
from .log_windows import LogWindow, FloatingLogWindow
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
        
        # Настраиваем улучшенное логирование
        set_ui_log_handler(self._enhanced_log_handler)
        
        # Подключаемся к единому менеджеру логирования
        self.log_manager = get_log_manager()
        self.log_manager.subscribe(self._unified_log_handler)
        
        # Инициализация UI
        self.init_ui()
        
        # Подключение сигналов
        self.connect_signals()
        
        logger.info(f"[START] WalletSender Modular v{__version__} запущен")
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Настройка окна
        self.setWindowTitle(f"WalletSender Modular v{__version__} - Production Edition")
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
        # Подключаем логирование переключения вкладок
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        splitter.addWidget(self.tab_widget)
        
        # Контейнер для логов с кнопками
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        # Панель с кнопками для логов
        log_buttons_layout = QHBoxLayout()
        
        # Метка
        log_label = QLabel("[INFO] Логи операций")
        log_label.setFont(QFont("Arial", 10, QFont.Bold))
        log_buttons_layout.addWidget(log_label)
        
        log_buttons_layout.addStretch()
        
        # Кнопка для отдельного окна логов
        self.open_log_window_btn = QPushButton("🗔 Отдельное окно")
        self.open_log_window_btn.setToolTip("Открыть логи в отдельном окне")
        self.open_log_window_btn.clicked.connect(self.open_log_window)
        self.open_log_window_btn.setMaximumWidth(150)
        log_buttons_layout.addWidget(self.open_log_window_btn)
        
        # Кнопка для плавающего окна логов
        self.open_floating_log_btn = QPushButton("🎈 Плавающее окно")
        self.open_floating_log_btn.setToolTip("Открыть логи в плавающем окне")
        self.open_floating_log_btn.clicked.connect(self.open_floating_log)
        self.open_floating_log_btn.setMaximumWidth(150)
        log_buttons_layout.addWidget(self.open_floating_log_btn)
        
        # Кнопка минимизации/развертывания логов
        self.toggle_logs_btn = QPushButton("⬇ Свернуть")
        self.toggle_logs_btn.setToolTip("Свернуть/развернуть область логов")
        self.toggle_logs_btn.clicked.connect(self.toggle_logs)
        self.toggle_logs_btn.setMaximumWidth(100)
        log_buttons_layout.addWidget(self.toggle_logs_btn)
        
        log_layout.addLayout(log_buttons_layout)
        
        # Область логов
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(200)
        log_layout.addWidget(self.log_area)
        
        splitter.addWidget(log_container)
        
        # Инициализация окон логов
        self.log_window = None
        self.floating_log = None
        self.logs_minimized = False
        
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
        
        logger.info("[OK] Пользовательский интерфейс инициализирован")
        
    def _create_header(self, layout):
        """Создание заголовка приложения"""
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        
        # Главный заголовок
        title_label = QLabel(f"[START] WalletSender Modular v{__version__}")
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
        
        # Статус очереди задач
        self.queue_status_label = QLabel("[INFO] Queue: 0/0/0")
        self.queue_status_label.setToolTip("Очередь: в очереди/выполняется/ошибки")
        self.status_bar.addPermanentWidget(self.queue_status_label)
        
        # Статус RPC
        self.rpc_status_label = QLabel("[WEB] RPC: -")
        self.rpc_status_label.setToolTip("RPC узел и задержка")
        self.status_bar.addPermanentWidget(self.rpc_status_label)
        
        # Статус API Rate Limiter
        self.api_status_label = QLabel("[SECURE] API: -")
        self.api_status_label.setToolTip("API Rate Limiter")
        self.status_bar.addPermanentWidget(self.api_status_label)
        
        # Статус подключения к сети
        self.network_status_label = QLabel("[WEB] Проверка сети...")
        self.status_bar.addPermanentWidget(self.network_status_label)
        
        # Таймер для обновления статусов
        self.status_update_timer = QTimer()
        self.status_update_timer.timeout.connect(self._update_status_indicators)
        self.status_update_timer.start(1000)  # Каждую секунду
        
        # Таймер для проверки сети
        self.network_check_timer = QTimer()
        self.network_check_timer.timeout.connect(self._check_network_connection)
        self.network_check_timer.start(10000)  # Каждые 10 секунд
        
        self.status_bar.showMessage("[OK] Готов к работе")
        
    def _check_network_connection(self):
        """Проверка подключения к сети"""
        try:
            if self.web3_provider and self.web3_provider.w3.is_connected():
                self.network_status_label.setText("🟢 BSC подключена")
            else:
                self.network_status_label.setText("🔴 BSC отключена")
        except Exception:
            self.network_status_label.setText("🟡 BSC неизвестно")
    
    def _update_status_indicators(self):
        """Обновление индикаторов статуса"""
        try:
            # Обновляем статус очереди
            from ..services.job_router import get_job_router
            router = get_job_router()
            stats = router.stats()
            
            queued = stats['states'].get('queued', 0)
            running = stats['states'].get('running', 0)
            failed = stats['states'].get('failed', 0)
            
            self.queue_status_label.setText(f"[INFO] Queue: {queued}/{running}/{failed}")
            
            # Обновляем статус RPC
            from ..core.rpc import get_rpc_pool
            rpc_pool = get_rpc_pool()
            endpoint = rpc_pool.current_primary()
            if endpoint:
                # Показываем только домен RPC
                import re
                match = re.search(r'//([^/]+)', endpoint)
                if match:
                    rpc_short = match.group(1)[:20]  # Первые 20 символов
                else:
                    rpc_short = endpoint[:20]
                self.rpc_status_label.setText(f"[WEB] RPC: {rpc_short}")
            else:
                self.rpc_status_label.setText("[WEB] RPC: No healthy endpoints")
            
            # Обновляем статус API Rate Limiter
            from ..core.limiter import get_rate_limiter
            limiter = get_rate_limiter()
            limiter_stats = limiter.get_stats()
            
            rps = limiter_stats.get('recent_rps', 0)
            blocked = limiter_stats.get('blocked_requests', 0)
            
            if blocked > 0:
                self.api_status_label.setText(f"[SECURE] API: {rps:.1f}rps [WARN]{blocked}")
            else:
                self.api_status_label.setText(f"[SECURE] API: {rps:.1f}rps")
                
        except Exception as e:
            # Не логируем ошибки обновления статусов
            pass
    
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
        self.tab_widget.addTab(self.mass_distribution_tab, "[MASS] Массовая рассылка")
        
        # Массовая рассылка 2
        self.mass_distribution_tab2 = MassDistributionTab(self, slot_number=2)
        self.tab_widget.addTab(self.mass_distribution_tab2, "[MASS] Массовая рассылка 2")
        
        # Массовая рассылка 3
        self.mass_distribution_tab3 = MassDistributionTab(self, slot_number=3)
        self.tab_widget.addTab(self.mass_distribution_tab3, "[MASS] Массовая рассылка 3")
        
        # Прямая отправка
        self.direct_send_tab = DirectSendTab(self)
        self.tab_widget.addTab(self.direct_send_tab, "📫 Прямая отправка")
        
        # Автопокупки
        self.auto_buy_tab = AutoBuyTab(self)
        self.tab_widget.addTab(self.auto_buy_tab, "🛌 Автопокупки")
        
        # Автопродажи
        self.auto_sales_tab = AutoSalesTab(self)
        self.tab_widget.addTab(self.auto_sales_tab, "[MONEY] Автопродажи")
        
        # Анализ
        self.analysis_tab = AnalysisTab(self)
        self.tab_widget.addTab(self.analysis_tab, "[SEARCH] Анализ")
        
        # Поиск
        self.search_tab = SearchTab(self)
        self.tab_widget.addTab(self.search_tab, "🔎 Поиск")
        
        # Награды
        self.rewards_tab = RewardsTab(self)
        self.tab_widget.addTab(self.rewards_tab, "🎁 Награды")
        
        # Очередь
        self.queue_tab = QueueTab(self)
        self.tab_widget.addTab(self.queue_tab, "[INFO] Очередь")
        
        # История
        self.history_tab = HistoryTab(self)
        self.tab_widget.addTab(self.history_tab, "[HISTORY] История")
        
        # Найденные транзакции
        self.found_tx_tab = FoundTxTab(self)
        self.tab_widget.addTab(self.found_tx_tab, "[SEARCH] Найденные TX")
        
        # Настройки
        self.settings_tab = SettingsTab(self)
        self.tab_widget.addTab(self.settings_tab, "[SETTINGS] Настройки")
        
        logger.info(f"[INFO] Загружено {self.tab_widget.count()} вкладок")
        
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
        
        tools_menu.addSeparator()
        
        # Открыть отдельное окно логов
        open_log_window_action = QAction('Логи в отдельном окне', self)
        open_log_window_action.triggered.connect(self.open_log_window)
        tools_menu.addAction(open_log_window_action)
        
        # Открыть плавающее окно логов
        open_floating_log_action = QAction('Логи в плавающем окне', self)
        open_floating_log_action.triggered.connect(self.open_floating_log)
        tools_menu.addAction(open_floating_log_action)

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
    
    def _unified_log_handler(self, message: str, level: str = "INFO"):
        """Обработчик для единого логгера"""
        # Добавляем лог в основное окно через внутренний метод
        # чтобы избежать повторной отправки в менеджер
        self._add_log_impl(message, level)
    
    def _enhanced_log_handler(self, message: str, level: str = "INFO"):
        """Обработчик для улучшенного логирования"""
        # Отправляем лог в единый менеджер, который уведомит всех подписчиков
        if hasattr(self, 'log_manager'):
            self.log_manager.add_log(message, level)
        else:
            # Fallback если менеджер еще не инициализирован
            self.log_message.emit(message, level)
    
    @log_tab_change
    def _on_tab_changed(self, index: int):
        """Обработка переключения вкладок"""
        pass  # Логирование выполняется через декоратор
        
    @pyqtSlot(str, str)
    def add_log(self, message: str, level: str = "INFO") -> None:
        """Добавление сообщения в лог"""
        # Отправляем лог в единый менеджер, который уведомит всех подписчиков
        # включая это основное окно через _unified_log_handler
        if hasattr(self, 'log_manager'):
            self.log_manager.add_log(message, level)
        else:
            # Fallback если менеджер еще не инициализирован
            self._add_log_impl(message, level)
        
    def _add_log_impl(self, message: str, level: str) -> None:
        """Реализация добавления лога"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Цветовая схема для уровней
        colors = {
            "DEBUG": "#888",
            "INFO": "#ff8c00",  # Темно-оранжевый вместо черного
            "SUCCESS": "#0a0",
            "WARNING": "#f90",
            "ERROR": "#f00",
            "SALE": "#00ff88",  # Яркий зеленый для продаж
            "PROFIT": "#00ffff"  # Голубой для прибыли
        }
        
        color = colors.get(level, "#ff8c00")  # Оранжевый для неизвестных уровней
        formatted_message = f'<span style="color: {color}">[{timestamp}] {message}</span>'
        
        self.log_area.append(formatted_message)
        
        # Прокрутка вниз
        scrollbar: QScrollBar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    @log_action("Экспорт логов")
    def export_logs(self, checked=False):
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
                
    @log_action("Очистка логов")
    def clear_logs(self, checked=False):
        """Очистка логов"""
        self.log_area.clear()
        self.add_log("Логи очищены", "INFO")
        
    @log_window_action("Открытие отдельного окна логов")
    def open_log_window(self, checked=False):
        """Открыть отдельное окно логов"""
        if self.log_window is None:
            self.log_window = LogWindow(self)
        
        # Показываем окно
        self.log_window.show()
        self.log_window.raise_()
        self.log_window.activateWindow()
        
    @log_window_action("Открытие плавающего окна логов")
    def open_floating_log(self, checked=False):
        """Открыть плавающее окно логов"""
        if self.floating_log is None:
            self.floating_log = FloatingLogWindow(self)
            # Добавляем в главное окно как док-виджет
            self.addDockWidget(Qt.RightDockWidgetArea, self.floating_log)
        
        # Показываем и делаем плавающим
        self.floating_log.show()
        self.floating_log.setFloating(True)
        
        # Устанавливаем размер и позицию
        self.floating_log.resize(500, 400)
        
        # Позиционируем справа от главного окна
        main_geometry = self.geometry()
        self.floating_log.move(
            main_geometry.x() + main_geometry.width() + 10,
            main_geometry.y()
        )
        
    @log_click("Свернуть/Развернуть логи")
    def toggle_logs(self, checked=False):
        """Переключить видимость области логов"""
        if self.logs_minimized:
            self.log_area.setMaximumHeight(200)
            self.log_area.setVisible(True)
            self.toggle_logs_btn.setText("⬇ Свернуть")
            self.logs_minimized = False
        else:
            self.log_area.setMaximumHeight(0)
            self.log_area.setVisible(False)
            self.toggle_logs_btn.setText("⬆ Развернуть")
            self.logs_minimized = True
            
    def show_about(self, checked=False):
        """Показать информацию о программе"""
        about_text = f"""
        <h2>WalletSender Modular v{__version__}</h2>
        <p><b>Production Edition</b></p>
        <p>Профессиональный инструмент для работы с блокчейном BSC</p>
        <p><i>Обновлено: 8 сентября 2025</i></p>
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
            <li><b>🆕 Отдельные и плавающие окна логов</b></li>
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
        <p><b>Разработка:</b> 2025 © Avertenandor</p>
        <p><b>Версия:</b> {__version__} Production Edition</p>
        <br>
        <p><b>🆕 Новое в версии {__version__}:</b></p>
        <ul>
            <li>Отдельное окно логов с поиском и экспортом</li>
            <li>Плавающее окно логов с регулировкой прозрачности</li>
            <li>Управление видимостью области логов</li>
            <li>Исправлены критические ошибки</li>
        </ul>
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
            if hasattr(self, 'status_update_timer'):
                self.status_update_timer.stop()
            
            # Закрытие окон логов если открыты
            if self.log_window is not None:
                self.log_window.close()
            if self.floating_log is not None:
                self.floating_log.close()
            
            # Закрытие BscScanService (graceful shutdown)
            try:
                from ..services.bscscan_service import close_bscscan_service
                import asyncio
                
                # Создаем event loop если его нет или используем существующий
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Закрываем сервис
                if not loop.is_running():
                    loop.run_until_complete(close_bscscan_service())
                else:
                    # Если loop уже запущен, планируем закрытие
                    asyncio.ensure_future(close_bscscan_service())
                    
                logger.info("[OK] BscScanService закрыт")
            except Exception as e:
                logger.warning(f"Не удалось закрыть BscScanService: {e}")
                
            logger.info("[BYE] Приложение закрыто")
            event.accept()
        else:
            event.ignore()
