"""
Вкладка настроек приложения
"""

import json
from typing import Optional, Dict, Any, List
from pathlib import Path

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel,
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QFormLayout,
    QMessageBox, QComboBox, QCheckBox, QTabWidget, QWidget,
    QListWidget, QListWidgetItem, QFileDialog, QDialog,
    QDialogButtonBox, QGridLayout, QScrollArea
)
from PyQt5.QtCore import pyqtSignal, Qt, QSettings
from PyQt5.QtGui import QFont, QIcon

from .base_tab import BaseTab
from ...config import get_config
from ...constants import CONTRACTS, BSC_MAINNET, DEFAULT_GAS_PRICE, DEFAULT_GAS_LIMIT
from ...utils.logger import get_logger

logger = get_logger(__name__)

class SettingsTab(BaseTab):
    """Вкладка для управления настройками приложения"""
    
    # Сигналы
    settings_changed = pyqtSignal(str, object)  # key, value
    theme_changed = pyqtSignal(str)  # theme name
    language_changed = pyqtSignal(str)  # language code
    
    def __init__(self, main_window, parent=None):
        self.config = get_config()
        super().__init__(main_window, parent)
        
    def init_ui(self):
        """Инициализация интерфейса настроек"""
        layout = QVBoxLayout(self)
        
        # Создаем табы для разных категорий настроек
        self.tabs = QTabWidget()
        
        # Основные настройки
        self.tabs.addTab(self._create_general_settings(), "🏠 Основные")
        
        # Настройки сети
        self.tabs.addTab(self._create_network_settings(), "🌐 Сеть")
        
        # Настройки газа
        self.tabs.addTab(self._create_gas_settings(), "⛽ Газ")
        
        # Настройки токенов
        self.tabs.addTab(self._create_tokens_settings(), "💰 Токены")
        
        # API ключи
        self.tabs.addTab(self._create_api_settings(), "🔑 API")
        
        # Настройки интерфейса
        self.tabs.addTab(self._create_ui_settings(), "🎨 Интерфейс")
        
        # Настройки безопасности
        self.tabs.addTab(self._create_security_settings(), "🔒 Безопасность")
        
        # Настройки логирования
        self.tabs.addTab(self._create_logging_settings(), "📝 Логирование")
        
        # Импорт/Экспорт
        self.tabs.addTab(self._create_import_export_settings(), "💾 Импорт/Экспорт")
        
        layout.addWidget(self.tabs)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Сохранить изменения")
        self.save_btn.clicked.connect(self.save_settings)
        buttons_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("🔄 Сбросить к умолчаниям")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        buttons_layout.addWidget(self.reset_btn)
        
        self.reload_btn = QPushButton("♻️ Перезагрузить")
        self.reload_btn.clicked.connect(self.reload_settings)
        buttons_layout.addWidget(self.reload_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
    def _create_general_settings(self) -> QWidget:
        """Создание вкладки основных настроек"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Группа общих настроек
        general_group = QGroupBox("Общие настройки")
        general_layout = QFormLayout(general_group)
        
        # Выбор сети
        self.network_combo = QComboBox()
        self.network_combo.addItems(["bsc_mainnet", "bsc_testnet"])
        current_network = self.config.get("network", "bsc_mainnet")
        self.network_combo.setCurrentText(current_network)
        general_layout.addRow("Сеть:", self.network_combo)
        
        # Автосохранение
        self.autosave_check = QCheckBox("Автосохранение настроек")
        self.autosave_check.setChecked(self.config.get("autosave", True))
        general_layout.addRow(self.autosave_check)
        
        # Подтверждение операций
        self.confirm_operations_check = QCheckBox("Запрашивать подтверждение операций")
        self.confirm_operations_check.setChecked(self.config.get("confirm_operations", True))
        general_layout.addRow(self.confirm_operations_check)
        
        # Звуковые уведомления
        self.sound_notifications_check = QCheckBox("Звуковые уведомления")
        self.sound_notifications_check.setChecked(self.config.get("sound_notifications", False))
        general_layout.addRow(self.sound_notifications_check)
        
        layout.addWidget(general_group)
        
        # Группа наград
        rewards_group = QGroupBox("Настройки наград")
        rewards_layout = QFormLayout(rewards_group)
        
        # Включение наград
        self.rewards_enabled_check = QCheckBox("Включить систему наград")
        rewards_settings = self.config.get("rewards", {})
        self.rewards_enabled_check.setChecked(rewards_settings.get("enabled", False))
        rewards_layout.addRow(self.rewards_enabled_check)
        
        # Минимальная сумма
        self.min_reward_amount = QDoubleSpinBox()
        self.min_reward_amount.setRange(0.00001, 1000000)
        self.min_reward_amount.setDecimals(5)
        self.min_reward_amount.setValue(rewards_settings.get("min_amount", 0.01))
        rewards_layout.addRow("Мин. сумма:", self.min_reward_amount)
        
        # Процент награды
        self.reward_percentage = QDoubleSpinBox()
        self.reward_percentage.setRange(0.01, 100)
        self.reward_percentage.setDecimals(2)
        self.reward_percentage.setValue(rewards_settings.get("reward_percentage", 1.0))
        self.reward_percentage.setSuffix(" %")
        rewards_layout.addRow("Процент награды:", self.reward_percentage)
        
        layout.addWidget(rewards_group)
        layout.addStretch()
        
        return widget
        
    def _create_network_settings(self) -> QWidget:
        """Создание вкладки настроек сети"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # RPC URLs
        rpc_group = QGroupBox("RPC узлы")
        rpc_layout = QVBoxLayout(rpc_group)
        
        # BSC Mainnet
        mainnet_layout = QHBoxLayout()
        mainnet_layout.addWidget(QLabel("BSC Mainnet:"))
        self.mainnet_rpc_input = QLineEdit()
        rpc_urls = self.config.get("rpc_urls", {})
        self.mainnet_rpc_input.setText(rpc_urls.get("bsc_mainnet", BSC_MAINNET['rpc_url']))
        mainnet_layout.addWidget(self.mainnet_rpc_input)
        
        self.test_mainnet_btn = QPushButton("Тест")
        self.test_mainnet_btn.clicked.connect(lambda: self.test_rpc(self.mainnet_rpc_input.text()))
        mainnet_layout.addWidget(self.test_mainnet_btn)
        
        rpc_layout.addLayout(mainnet_layout)
        
        # BSC Testnet
        testnet_layout = QHBoxLayout()
        testnet_layout.addWidget(QLabel("BSC Testnet:"))
        self.testnet_rpc_input = QLineEdit()
        self.testnet_rpc_input.setText(rpc_urls.get("bsc_testnet", "https://data-seed-prebsc-1-s1.binance.org:8545/"))
        testnet_layout.addWidget(self.testnet_rpc_input)
        
        self.test_testnet_btn = QPushButton("Тест")
        self.test_testnet_btn.clicked.connect(lambda: self.test_rpc(self.testnet_rpc_input.text()))
        testnet_layout.addWidget(self.test_testnet_btn)
        
        rpc_layout.addLayout(testnet_layout)
        
        # Список дополнительных RPC
        rpc_layout.addWidget(QLabel("Дополнительные RPC узлы:"))
        self.rpc_list = QListWidget()
        self.rpc_list.setMaximumHeight(150)
        
        # Загружаем дополнительные RPC
        additional_rpcs = self.config.get("additional_rpcs", [])
        for rpc in additional_rpcs:
            self.rpc_list.addItem(rpc)
            
        rpc_layout.addWidget(self.rpc_list)
        
        # Кнопки управления RPC
        rpc_buttons_layout = QHBoxLayout()
        
        self.add_rpc_btn = QPushButton("➕ Добавить")
        self.add_rpc_btn.clicked.connect(self.add_rpc)
        rpc_buttons_layout.addWidget(self.add_rpc_btn)
        
        self.remove_rpc_btn = QPushButton("➖ Удалить")
        self.remove_rpc_btn.clicked.connect(self.remove_rpc)
        rpc_buttons_layout.addWidget(self.remove_rpc_btn)
        
        self.test_all_rpc_btn = QPushButton("🔍 Тест всех")
        self.test_all_rpc_btn.clicked.connect(self.test_all_rpcs)
        rpc_buttons_layout.addWidget(self.test_all_rpc_btn)
        
        rpc_layout.addLayout(rpc_buttons_layout)
        
        layout.addWidget(rpc_group)
        
        # Настройки подключения
        connection_group = QGroupBox("Настройки подключения")
        connection_layout = QFormLayout(connection_group)
        
        # Таймаут
        self.connection_timeout = QSpinBox()
        self.connection_timeout.setRange(5, 60)
        self.connection_timeout.setValue(self.config.get("connection_timeout", 30))
        self.connection_timeout.setSuffix(" сек")
        connection_layout.addRow("Таймаут подключения:", self.connection_timeout)
        
        # Количество попыток
        self.retry_count = QSpinBox()
        self.retry_count.setRange(1, 10)
        self.retry_count.setValue(self.config.get("retry_count", 3))
        connection_layout.addRow("Количество попыток:", self.retry_count)
        
        # Автоматическая смена RPC
        self.auto_switch_rpc = QCheckBox("Автоматически переключать RPC при ошибке")
        self.auto_switch_rpc.setChecked(self.config.get("auto_switch_rpc", True))
        connection_layout.addRow(self.auto_switch_rpc)
        
        layout.addWidget(connection_group)
        layout.addStretch()
        
        return widget
        
    def _create_gas_settings(self) -> QWidget:
        """Создание вкладки настроек газа"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        gas_group = QGroupBox("Настройки газа")
        gas_layout = QFormLayout(gas_group)
        
        gas_settings = self.config.get("gas_settings", {})
        
        # Цена газа по умолчанию
        self.default_gas_price = QDoubleSpinBox()
        self.default_gas_price.setRange(0.1, 1000)
        self.default_gas_price.setDecimals(1)
        self.default_gas_price.setValue(gas_settings.get("default_gas_price", DEFAULT_GAS_PRICE))
        self.default_gas_price.setSuffix(" Gwei")
        gas_layout.addRow("Цена газа по умолчанию:", self.default_gas_price)
        
        # Лимит газа по умолчанию
        self.default_gas_limit = QSpinBox()
        self.default_gas_limit.setRange(21000, 1000000)
        self.default_gas_limit.setValue(gas_settings.get("default_gas_limit", DEFAULT_GAS_LIMIT))
        gas_layout.addRow("Лимит газа по умолчанию:", self.default_gas_limit)
        
        # Максимальная цена газа
        self.max_gas_price = QDoubleSpinBox()
        self.max_gas_price.setRange(1, 1000)
        self.max_gas_price.setDecimals(1)
        self.max_gas_price.setValue(gas_settings.get("max_gas_price", 50))
        self.max_gas_price.setSuffix(" Gwei")
        gas_layout.addRow("Макс. цена газа:", self.max_gas_price)
        
        # Автоматическая оценка газа
        self.auto_estimate_gas = QCheckBox("Автоматически оценивать газ")
        self.auto_estimate_gas.setChecked(gas_settings.get("auto_estimate", False))
        gas_layout.addRow(self.auto_estimate_gas)
        
        # Использовать EIP-1559
        self.use_eip1559 = QCheckBox("Использовать EIP-1559 (если поддерживается)")
        self.use_eip1559.setChecked(gas_settings.get("use_eip1559", False))
        gas_layout.addRow(self.use_eip1559)
        
        layout.addWidget(gas_group)
        
        # Предустановки газа
        presets_group = QGroupBox("Предустановки")
        presets_layout = QVBoxLayout(presets_group)
        
        presets_buttons_layout = QHBoxLayout()
        
        self.gas_slow_btn = QPushButton("🐢 Медленно (3 Gwei)")
        self.gas_slow_btn.clicked.connect(lambda: self.set_gas_preset(3))
        presets_buttons_layout.addWidget(self.gas_slow_btn)
        
        self.gas_normal_btn = QPushButton("🚶 Обычно (5 Gwei)")
        self.gas_normal_btn.clicked.connect(lambda: self.set_gas_preset(5))
        presets_buttons_layout.addWidget(self.gas_normal_btn)
        
        self.gas_fast_btn = QPushButton("🏃 Быстро (10 Gwei)")
        self.gas_fast_btn.clicked.connect(lambda: self.set_gas_preset(10))
        presets_buttons_layout.addWidget(self.gas_fast_btn)
        
        self.gas_instant_btn = QPushButton("⚡ Мгновенно (20 Gwei)")
        self.gas_instant_btn.clicked.connect(lambda: self.set_gas_preset(20))
        presets_buttons_layout.addWidget(self.gas_instant_btn)
        
        presets_layout.addLayout(presets_buttons_layout)
        
        layout.addWidget(presets_group)
        layout.addStretch()
        
        return widget
        
    def _create_tokens_settings(self) -> QWidget:
        """Создание вкладки настроек токенов"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        tokens_group = QGroupBox("Управление токенами")
        tokens_layout = QVBoxLayout(tokens_group)
        
        # Список токенов
        tokens_layout.addWidget(QLabel("Токены:"))
        self.tokens_list = QListWidget()
        self.tokens_list.setMaximumHeight(200)
        
        # Загружаем токены
        tokens = self.config.get("tokens", CONTRACTS)
        for name, address in tokens.items():
            item_text = f"{name}: {address}"
            self.tokens_list.addItem(item_text)
            
        tokens_layout.addWidget(self.tokens_list)
        
        # Кнопки управления токенами
        tokens_buttons_layout = QHBoxLayout()
        
        self.add_token_btn = QPushButton("➕ Добавить токен")
        self.add_token_btn.clicked.connect(self.add_token)
        tokens_buttons_layout.addWidget(self.add_token_btn)
        
        self.edit_token_btn = QPushButton("✏️ Редактировать")
        self.edit_token_btn.clicked.connect(self.edit_token)
        tokens_buttons_layout.addWidget(self.edit_token_btn)
        
        self.remove_token_btn = QPushButton("➖ Удалить")
        self.remove_token_btn.clicked.connect(self.remove_token)
        tokens_buttons_layout.addWidget(self.remove_token_btn)
        
        tokens_layout.addLayout(tokens_buttons_layout)
        
        layout.addWidget(tokens_group)
        
        # Настройки PancakeSwap
        pancake_group = QGroupBox("PancakeSwap")
        pancake_layout = QFormLayout(pancake_group)
        
        # Router address
        self.pancake_router_input = QLineEdit()
        self.pancake_router_input.setText(
            self.config.get("pancakeswap_router", CONTRACTS['PANCAKESWAP_ROUTER'])
        )
        pancake_layout.addRow("Router адрес:", self.pancake_router_input)
        
        # Slippage
        self.slippage_input = QDoubleSpinBox()
        self.slippage_input.setRange(0.1, 50)
        self.slippage_input.setDecimals(1)
        self.slippage_input.setValue(self.config.get("slippage", 2.0))
        self.slippage_input.setSuffix(" %")
        pancake_layout.addRow("Slippage:", self.slippage_input)
        
        layout.addWidget(pancake_group)
        layout.addStretch()
        
        return widget
        
    def _create_api_settings(self) -> QWidget:
        """Создание вкладки настроек API"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        api_group = QGroupBox("BSCScan API")
        api_layout = QVBoxLayout(api_group)
        
        api_layout.addWidget(QLabel("API ключи:"))
        self.api_keys_list = QListWidget()
        self.api_keys_list.setMaximumHeight(150)
        
        # Загружаем API ключи
        api_keys = self.config.get("bscscan_api_keys", [])
        for key in api_keys:
            # Скрываем часть ключа для безопасности
            masked_key = key[:8] + "..." + key[-8:] if len(key) > 16 else key
            self.api_keys_list.addItem(masked_key)
            
        api_layout.addWidget(self.api_keys_list)
        
        # Кнопки управления API ключами
        api_buttons_layout = QHBoxLayout()
        
        self.add_api_key_btn = QPushButton("➕ Добавить ключ")
        self.add_api_key_btn.clicked.connect(self.add_api_key)
        api_buttons_layout.addWidget(self.add_api_key_btn)
        
        self.remove_api_key_btn = QPushButton("➖ Удалить")
        self.remove_api_key_btn.clicked.connect(self.remove_api_key)
        api_buttons_layout.addWidget(self.remove_api_key_btn)
        
        self.test_api_key_btn = QPushButton("🔍 Тест")
        self.test_api_key_btn.clicked.connect(self.test_api_key)
        api_buttons_layout.addWidget(self.test_api_key_btn)
        
        api_layout.addLayout(api_buttons_layout)
        
        # Настройки API
        api_settings_layout = QFormLayout()
        
        # Rate limit
        self.api_rate_limit = QSpinBox()
        self.api_rate_limit.setRange(1, 10)
        self.api_rate_limit.setValue(self.config.get("api_rate_limit", 5))
        self.api_rate_limit.setSuffix(" запросов/сек")
        api_settings_layout.addRow("Rate limit:", self.api_rate_limit)
        
        # Использовать ротацию ключей
        self.rotate_api_keys = QCheckBox("Ротация API ключей")
        self.rotate_api_keys.setChecked(self.config.get("rotate_api_keys", True))
        api_settings_layout.addRow(self.rotate_api_keys)
        
        api_layout.addLayout(api_settings_layout)
        
        layout.addWidget(api_group)
        layout.addStretch()
        
        return widget
        
    def _create_ui_settings(self) -> QWidget:
        """Создание вкладки настроек интерфейса"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        ui_group = QGroupBox("Настройки интерфейса")
        ui_layout = QFormLayout(ui_group)
        
        ui_settings = self.config.get("ui", {})
        
        # Тема
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light", "auto"])
        self.theme_combo.setCurrentText(ui_settings.get("theme", "dark"))
        ui_layout.addRow("Тема:", self.theme_combo)
        
        # Язык
        self.language_combo = QComboBox()
        self.language_combo.addItems(["ru", "en"])
        self.language_combo.setCurrentText(ui_settings.get("language", "ru"))
        ui_layout.addRow("Язык:", self.language_combo)
        
        # Размер окна
        self.window_width = QSpinBox()
        self.window_width.setRange(800, 3840)
        self.window_width.setValue(ui_settings.get("window_width", 1400))
        ui_layout.addRow("Ширина окна:", self.window_width)
        
        self.window_height = QSpinBox()
        self.window_height.setRange(600, 2160)
        self.window_height.setValue(ui_settings.get("window_height", 900))
        ui_layout.addRow("Высота окна:", self.window_height)
        
        # Дополнительные настройки
        self.show_tooltips = QCheckBox("Показывать подсказки")
        self.show_tooltips.setChecked(ui_settings.get("show_tooltips", True))
        ui_layout.addRow(self.show_tooltips)
        
        self.minimize_to_tray = QCheckBox("Сворачивать в трей")
        self.minimize_to_tray.setChecked(ui_settings.get("minimize_to_tray", False))
        ui_layout.addRow(self.minimize_to_tray)
        
        self.start_minimized = QCheckBox("Запускать свернутым")
        self.start_minimized.setChecked(ui_settings.get("start_minimized", False))
        ui_layout.addRow(self.start_minimized)
        
        layout.addWidget(ui_group)
        
        # Настройки таблиц
        tables_group = QGroupBox("Настройки таблиц")
        tables_layout = QFormLayout(tables_group)
        
        self.table_row_height = QSpinBox()
        self.table_row_height.setRange(20, 100)
        self.table_row_height.setValue(ui_settings.get("table_row_height", 30))
        tables_layout.addRow("Высота строк:", self.table_row_height)
        
        self.alternating_row_colors = QCheckBox("Чередующиеся цвета строк")
        self.alternating_row_colors.setChecked(ui_settings.get("alternating_row_colors", True))
        tables_layout.addRow(self.alternating_row_colors)
        
        layout.addWidget(tables_group)
        layout.addStretch()
        
        return widget
        
    def _create_security_settings(self) -> QWidget:
        """Создание вкладки настроек безопасности"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        security_group = QGroupBox("Безопасность")
        security_layout = QFormLayout(security_group)
        
        security_settings = self.config.get("security", {})
        
        # Шифрование ключей
        self.encrypt_keys = QCheckBox("Шифровать приватные ключи")
        self.encrypt_keys.setChecked(security_settings.get("encrypt_keys", True))
        security_layout.addRow(self.encrypt_keys)
        
        # Автоблокировка
        self.auto_lock = QCheckBox("Автоматическая блокировка")
        self.auto_lock.setChecked(security_settings.get("auto_lock", False))
        security_layout.addRow(self.auto_lock)
        
        self.auto_lock_minutes = QSpinBox()
        self.auto_lock_minutes.setRange(1, 60)
        self.auto_lock_minutes.setValue(security_settings.get("auto_lock_minutes", 30))
        self.auto_lock_minutes.setSuffix(" минут")
        self.auto_lock_minutes.setEnabled(self.auto_lock.isChecked())
        security_layout.addRow("Блокировка через:", self.auto_lock_minutes)
        
        # Связываем чекбокс с полем ввода
        self.auto_lock.toggled.connect(self.auto_lock_minutes.setEnabled)
        
        # Очистка буфера обмена
        self.clear_clipboard = QCheckBox("Очищать буфер обмена после копирования ключей")
        self.clear_clipboard.setChecked(security_settings.get("clear_clipboard", True))
        security_layout.addRow(self.clear_clipboard)
        
        # Проверка адресов
        self.verify_addresses = QCheckBox("Проверять контрольную сумму адресов")
        self.verify_addresses.setChecked(security_settings.get("verify_addresses", True))
        security_layout.addRow(self.verify_addresses)
        
        # Ограничение транзакций
        self.tx_limit_enabled = QCheckBox("Ограничение суммы транзакций")
        self.tx_limit_enabled.setChecked(security_settings.get("tx_limit_enabled", False))
        security_layout.addRow(self.tx_limit_enabled)
        
        self.tx_limit_amount = QDoubleSpinBox()
        self.tx_limit_amount.setRange(0.001, 10000)
        self.tx_limit_amount.setDecimals(3)
        self.tx_limit_amount.setValue(security_settings.get("tx_limit_amount", 100))
        self.tx_limit_amount.setSuffix(" BNB")
        self.tx_limit_amount.setEnabled(self.tx_limit_enabled.isChecked())
        security_layout.addRow("Макс. сумма транзакции:", self.tx_limit_amount)
        
        self.tx_limit_enabled.toggled.connect(self.tx_limit_amount.setEnabled)
        
        layout.addWidget(security_group)
        
        # Резервное копирование
        backup_group = QGroupBox("Резервное копирование")
        backup_layout = QFormLayout(backup_group)
        
        self.auto_backup = QCheckBox("Автоматическое резервное копирование")
        self.auto_backup.setChecked(security_settings.get("auto_backup", False))
        backup_layout.addRow(self.auto_backup)
        
        backup_path_layout = QHBoxLayout()
        self.backup_path = QLineEdit()
        self.backup_path.setText(security_settings.get("backup_path", "./backups"))
        backup_path_layout.addWidget(self.backup_path)
        
        self.browse_backup_btn = QPushButton("📁")
        self.browse_backup_btn.clicked.connect(self.browse_backup_path)
        backup_path_layout.addWidget(self.browse_backup_btn)
        
        backup_layout.addRow("Путь для резервных копий:", backup_path_layout)
        
        layout.addWidget(backup_group)
        layout.addStretch()
        
        return widget
        
    def _create_logging_settings(self) -> QWidget:
        """Создание вкладки настроек логирования"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        logging_group = QGroupBox("Логирование")
        logging_layout = QFormLayout(logging_group)
        
        logging_settings = self.config.get("logging", {})
        
        # Уровень логирования
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText(logging_settings.get("level", "INFO"))
        logging_layout.addRow("Уровень логирования:", self.log_level_combo)
        
        # Файл логов
        log_file_layout = QHBoxLayout()
        self.log_file_input = QLineEdit()
        self.log_file_input.setText(logging_settings.get("file", "wallet_sender.log"))
        log_file_layout.addWidget(self.log_file_input)
        
        self.browse_log_btn = QPushButton("📁")
        self.browse_log_btn.clicked.connect(self.browse_log_file)
        log_file_layout.addWidget(self.browse_log_btn)
        
        logging_layout.addRow("Файл логов:", log_file_layout)
        
        # Максимальный размер файла
        self.max_log_size = QSpinBox()
        self.max_log_size.setRange(1, 100)
        self.max_log_size.setValue(logging_settings.get("max_size", 10485760) // 1048576)  # В MB
        self.max_log_size.setSuffix(" MB")
        logging_layout.addRow("Макс. размер файла:", self.max_log_size)
        
        # Количество резервных копий
        self.backup_count = QSpinBox()
        self.backup_count.setRange(1, 10)
        self.backup_count.setValue(logging_settings.get("backup_count", 5))
        logging_layout.addRow("Кол-во резервных копий:", self.backup_count)
        
        # Дополнительные опции
        self.log_to_console = QCheckBox("Вывод в консоль")
        self.log_to_console.setChecked(logging_settings.get("log_to_console", True))
        logging_layout.addRow(self.log_to_console)
        
        self.log_transactions = QCheckBox("Логировать транзакции")
        self.log_transactions.setChecked(logging_settings.get("log_transactions", True))
        logging_layout.addRow(self.log_transactions)
        
        self.log_api_calls = QCheckBox("Логировать API вызовы")
        self.log_api_calls.setChecked(logging_settings.get("log_api_calls", False))
        logging_layout.addRow(self.log_api_calls)
        
        layout.addWidget(logging_group)
        
        # Кнопки управления логами
        log_buttons_layout = QHBoxLayout()
        
        self.open_log_btn = QPushButton("📖 Открыть лог файл")
        self.open_log_btn.clicked.connect(self.open_log_file)
        log_buttons_layout.addWidget(self.open_log_btn)
        
        self.clear_logs_btn = QPushButton("🗑️ Очистить логи")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        log_buttons_layout.addWidget(self.clear_logs_btn)
        
        layout.addLayout(log_buttons_layout)
        layout.addStretch()
        
        return widget
        
    def _create_import_export_settings(self) -> QWidget:
        """Создание вкладки импорта/экспорта настроек"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Экспорт
        export_group = QGroupBox("Экспорт настроек")
        export_layout = QVBoxLayout(export_group)
        
        export_layout.addWidget(QLabel("Экспортировать текущие настройки в файл:"))
        
        export_buttons_layout = QHBoxLayout()
        
        self.export_all_btn = QPushButton("📤 Экспорт всех настроек")
        self.export_all_btn.clicked.connect(self.export_all_settings)
        export_buttons_layout.addWidget(self.export_all_btn)
        
        self.export_selected_btn = QPushButton("📋 Экспорт выбранных")
        self.export_selected_btn.clicked.connect(self.export_selected_settings)
        export_buttons_layout.addWidget(self.export_selected_btn)
        
        export_layout.addLayout(export_buttons_layout)
        
        layout.addWidget(export_group)
        
        # Импорт
        import_group = QGroupBox("Импорт настроек")
        import_layout = QVBoxLayout(import_group)
        
        import_layout.addWidget(QLabel("Импортировать настройки из файла:"))
        
        import_buttons_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("📥 Импорт настроек")
        self.import_btn.clicked.connect(self.import_settings)
        import_buttons_layout.addWidget(self.import_btn)
        
        self.import_merge_btn = QPushButton("🔀 Импорт с объединением")
        self.import_merge_btn.clicked.connect(self.import_merge_settings)
        import_buttons_layout.addWidget(self.import_merge_btn)
        
        import_layout.addLayout(import_buttons_layout)
        
        layout.addWidget(import_group)
        
        # Профили настроек
        profiles_group = QGroupBox("Профили настроек")
        profiles_layout = QVBoxLayout(profiles_group)
        
        profiles_layout.addWidget(QLabel("Сохраненные профили:"))
        
        self.profiles_list = QListWidget()
        self.profiles_list.setMaximumHeight(150)
        
        # Загружаем профили
        profiles = self.config.get("profiles", {})
        for profile_name in profiles.keys():
            self.profiles_list.addItem(profile_name)
            
        profiles_layout.addWidget(self.profiles_list)
        
        profiles_buttons_layout = QHBoxLayout()
        
        self.save_profile_btn = QPushButton("💾 Сохранить профиль")
        self.save_profile_btn.clicked.connect(self.save_profile)
        profiles_buttons_layout.addWidget(self.save_profile_btn)
        
        self.load_profile_btn = QPushButton("📂 Загрузить профиль")
        self.load_profile_btn.clicked.connect(self.load_profile)
        profiles_buttons_layout.addWidget(self.load_profile_btn)
        
        self.delete_profile_btn = QPushButton("🗑️ Удалить профиль")
        self.delete_profile_btn.clicked.connect(self.delete_profile)
        profiles_buttons_layout.addWidget(self.delete_profile_btn)
        
        profiles_layout.addLayout(profiles_buttons_layout)
        
        layout.addWidget(profiles_group)
        layout.addStretch()
        
        return widget
        
    # Методы для работы с настройками
    def save_settings(self):
        """Сохранение всех настроек"""
        try:
            # Основные настройки
            self.config.set("network", self.network_combo.currentText())
            self.config.set("autosave", self.autosave_check.isChecked())
            self.config.set("confirm_operations", self.confirm_operations_check.isChecked())
            self.config.set("sound_notifications", self.sound_notifications_check.isChecked())
            
            # Настройки наград
            self.config.set("rewards.enabled", self.rewards_enabled_check.isChecked())
            self.config.set("rewards.min_amount", self.min_reward_amount.value())
            self.config.set("rewards.reward_percentage", self.reward_percentage.value())
            
            # RPC URLs
            self.config.set("rpc_urls.bsc_mainnet", self.mainnet_rpc_input.text())
            self.config.set("rpc_urls.bsc_testnet", self.testnet_rpc_input.text())
            
            # Настройки подключения
            self.config.set("connection_timeout", self.connection_timeout.value())
            self.config.set("retry_count", self.retry_count.value())
            self.config.set("auto_switch_rpc", self.auto_switch_rpc.isChecked())
            
            # Настройки газа
            self.config.set("gas_settings.default_gas_price", self.default_gas_price.value())
            self.config.set("gas_settings.default_gas_limit", self.default_gas_limit.value())
            self.config.set("gas_settings.max_gas_price", self.max_gas_price.value())
            self.config.set("gas_settings.auto_estimate", self.auto_estimate_gas.isChecked())
            self.config.set("gas_settings.use_eip1559", self.use_eip1559.isChecked())
            
            # UI настройки
            self.config.set("ui.theme", self.theme_combo.currentText())
            self.config.set("ui.language", self.language_combo.currentText())
            self.config.set("ui.window_width", self.window_width.value())
            self.config.set("ui.window_height", self.window_height.value())
            self.config.set("ui.show_tooltips", self.show_tooltips.isChecked())
            self.config.set("ui.minimize_to_tray", self.minimize_to_tray.isChecked())
            self.config.set("ui.start_minimized", self.start_minimized.isChecked())
            self.config.set("ui.table_row_height", self.table_row_height.value())
            self.config.set("ui.alternating_row_colors", self.alternating_row_colors.isChecked())
            
            # Настройки безопасности
            self.config.set("security.encrypt_keys", self.encrypt_keys.isChecked())
            self.config.set("security.auto_lock", self.auto_lock.isChecked())
            self.config.set("security.auto_lock_minutes", self.auto_lock_minutes.value())
            self.config.set("security.clear_clipboard", self.clear_clipboard.isChecked())
            self.config.set("security.verify_addresses", self.verify_addresses.isChecked())
            self.config.set("security.tx_limit_enabled", self.tx_limit_enabled.isChecked())
            self.config.set("security.tx_limit_amount", self.tx_limit_amount.value())
            self.config.set("security.auto_backup", self.auto_backup.isChecked())
            self.config.set("security.backup_path", self.backup_path.text())
            
            # Настройки логирования
            self.config.set("logging.level", self.log_level_combo.currentText())
            self.config.set("logging.file", self.log_file_input.text())
            self.config.set("logging.max_size", self.max_log_size.value() * 1048576)  # В байтах
            self.config.set("logging.backup_count", self.backup_count.value())
            self.config.set("logging.log_to_console", self.log_to_console.isChecked())
            self.config.set("logging.log_transactions", self.log_transactions.isChecked())
            self.config.set("logging.log_api_calls", self.log_api_calls.isChecked())
            
            # Другие настройки
            self.config.set("pancakeswap_router", self.pancake_router_input.text())
            self.config.set("slippage", self.slippage_input.value())
            self.config.set("api_rate_limit", self.api_rate_limit.value())
            self.config.set("rotate_api_keys", self.rotate_api_keys.isChecked())
            
            # Сохраняем в файл
            self.config.save()
            
            self.log("✅ Настройки успешно сохранены", "SUCCESS")
            QMessageBox.information(self, "Успех", "Настройки успешно сохранены!")
            
            # Отправляем сигналы об изменении настроек
            self.theme_changed.emit(self.theme_combo.currentText())
            self.language_changed.emit(self.language_combo.currentText())
            
        except Exception as e:
            self.log(f"❌ Ошибка сохранения настроек: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки:\n{str(e)}")
            
    def reset_to_defaults(self):
        """Сброс настроек к значениям по умолчанию"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.config.reset_to_defaults()
            self.reload_settings()
            self.log("🔄 Настройки сброшены к значениям по умолчанию", "INFO")
            QMessageBox.information(self, "Успех", "Настройки сброшены к значениям по умолчанию!")
            
    def reload_settings(self):
        """Перезагрузка настроек из файла"""
        self.config.load()
        self.init_ui()  # Переинициализируем UI с новыми настройками
        self.log("♻️ Настройки перезагружены", "INFO")
        
    def test_rpc(self, rpc_url: str):
        """Тестирование RPC соединения"""
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            if w3.is_connected():
                block_number = w3.eth.block_number
                QMessageBox.information(
                    self, 
                    "Успех", 
                    f"✅ Соединение успешно!\nТекущий блок: {block_number}"
                )
            else:
                QMessageBox.warning(self, "Ошибка", "❌ Не удалось подключиться к RPC")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения:\n{str(e)}")
            
    def test_all_rpcs(self):
        """Тестирование всех RPC узлов"""
        # TODO: Реализовать тестирование всех RPC
        QMessageBox.information(self, "В разработке", "Функция в разработке")
        
    def add_rpc(self):
        """Добавление нового RPC узла"""
        text, ok = QInputDialog.getText(
            self, 
            "Добавить RPC", 
            "Введите URL RPC узла:"
        )
        if ok and text:
            self.rpc_list.addItem(text)
            
    def remove_rpc(self):
        """Удаление выбранного RPC узла"""
        current_item = self.rpc_list.currentItem()
        if current_item:
            self.rpc_list.takeItem(self.rpc_list.row(current_item))
            
    def add_token(self):
        """Добавление нового токена"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить токен")
        layout = QFormLayout(dialog)
        
        name_input = QLineEdit()
        address_input = QLineEdit()
        
        layout.addRow("Название:", name_input)
        layout.addRow("Адрес:", address_input)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            name = name_input.text()
            address = address_input.text()
            if name and address:
                self.tokens_list.addItem(f"{name}: {address}")
                
    def edit_token(self):
        """Редактирование выбранного токена"""
        # TODO: Реализовать редактирование токена
        QMessageBox.information(self, "В разработке", "Функция в разработке")
        
    def remove_token(self):
        """Удаление выбранного токена"""
        current_item = self.tokens_list.currentItem()
        if current_item:
            self.tokens_list.takeItem(self.tokens_list.row(current_item))
            
    def add_api_key(self):
        """Добавление нового API ключа"""
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self, 
            "Добавить API ключ", 
            "Введите BSCScan API ключ:"
        )
        if ok and text:
            masked_key = text[:8] + "..." + text[-8:] if len(text) > 16 else text
            self.api_keys_list.addItem(masked_key)
            # Сохраняем полный ключ в конфиг
            api_keys = self.config.get("bscscan_api_keys", [])
            api_keys.append(text)
            self.config.set("bscscan_api_keys", api_keys)
            
    def remove_api_key(self):
        """Удаление выбранного API ключа"""
        current_item = self.api_keys_list.currentItem()
        if current_item:
            self.api_keys_list.takeItem(self.api_keys_list.row(current_item))
            
    def test_api_key(self):
        """Тестирование выбранного API ключа"""
        # TODO: Реализовать тестирование API ключа
        QMessageBox.information(self, "В разработке", "Функция в разработке")
        
    def set_gas_preset(self, gwei: float):
        """Установка предустановленного значения газа"""
        self.default_gas_price.setValue(gwei)
        
    def browse_backup_path(self):
        """Выбор пути для резервных копий"""
        path = QFileDialog.getExistingDirectory(self, "Выберите папку для резервных копий")
        if path:
            self.backup_path.setText(path)
            
    def browse_log_file(self):
        """Выбор файла логов"""
        path, _ = QFileDialog.getSaveFileName(
            self, 
            "Выберите файл логов",
            "",
            "Log Files (*.log);;All Files (*.*)"
        )
        if path:
            self.log_file_input.setText(path)
            
    def open_log_file(self):
        """Открытие файла логов"""
        log_file = self.log_file_input.text()
        if Path(log_file).exists():
            import os
            os.startfile(log_file)
        else:
            QMessageBox.warning(self, "Ошибка", "Файл логов не найден")
            
    def clear_logs(self):
        """Очистка файла логов"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите очистить файл логов?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            log_file = self.log_file_input.text()
            try:
                open(log_file, 'w').close()
                QMessageBox.information(self, "Успех", "Файл логов очищен")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось очистить файл логов:\n{str(e)}")
                
    def export_all_settings(self):
        """Экспорт всех настроек"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт настроек",
            "wallet_sender_settings.json",
            "JSON Files (*.json)"
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.config.config, f, indent=4, ensure_ascii=False)
                QMessageBox.information(self, "Успех", f"Настройки экспортированы в:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта:\n{str(e)}")
                
    def export_selected_settings(self):
        """Экспорт выбранных настроек"""
        # TODO: Реализовать выбор настроек для экспорта
        QMessageBox.information(self, "В разработке", "Функция в разработке")
        
    def import_settings(self):
        """Импорт настроек"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт настроек",
            "",
            "JSON Files (*.json)"
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    imported_config = json.load(f)
                self.config.config = imported_config
                self.config.save()
                self.reload_settings()
                QMessageBox.information(self, "Успех", "Настройки успешно импортированы!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка импорта:\n{str(e)}")
                
    def import_merge_settings(self):
        """Импорт настроек с объединением"""
        # TODO: Реализовать объединение настроек
        QMessageBox.information(self, "В разработке", "Функция в разработке")
        
    def save_profile(self):
        """Сохранение профиля настроек"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self,
            "Сохранить профиль",
            "Введите название профиля:"
        )
        if ok and name:
            profiles = self.config.get("profiles", {})
            profiles[name] = self.config.config.copy()
            self.config.set("profiles", profiles)
            self.profiles_list.addItem(name)
            QMessageBox.information(self, "Успех", f"Профиль '{name}' сохранен!")
            
    def load_profile(self):
        """Загрузка профиля настроек"""
        current_item = self.profiles_list.currentItem()
        if current_item:
            profile_name = current_item.text()
            profiles = self.config.get("profiles", {})
            if profile_name in profiles:
                self.config.config = profiles[profile_name].copy()
                self.config.save()
                self.reload_settings()
                QMessageBox.information(self, "Успех", f"Профиль '{profile_name}' загружен!")
                
    def delete_profile(self):
        """Удаление профиля настроек"""
        current_item = self.profiles_list.currentItem()
        if current_item:
            profile_name = current_item.text()
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                f"Удалить профиль '{profile_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                profiles = self.config.get("profiles", {})
                if profile_name in profiles:
                    del profiles[profile_name]
                    self.config.set("profiles", profiles)
                    self.profiles_list.takeItem(self.profiles_list.row(current_item))
                    QMessageBox.information(self, "Успех", f"Профиль '{profile_name}' удален!")
