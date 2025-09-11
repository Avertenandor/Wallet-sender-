"""
Вкладка автоматических покупок токенов
"""

import json
import time
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
import threading
from ...core.nonce_manager import get_nonce_manager, NonceTicket, NonceStatus

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel,
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QCheckBox, QWidget,
    QFormLayout, QGridLayout, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor
import threading

from web3 import Web3
from ...services.dex_swap_service import DexSwapService
from eth_account import Account
from eth_typing import HexStr, HexAddress

from .base_tab import BaseTab
from ...utils.logger import get_logger
from ...utils.logger_enhanced import (
    log_action, log_click, log_dropdown_change, log_checkbox_change,
    log_spinbox_change, log_input_change, log_validation, log_api_call,
    log_currency_change, log_time_change, log_radio_change
)

logger = get_logger(__name__)

try:
    from mnemonic import Mnemonic
except ImportError:
    Mnemonic = None
    logger.warning("Библиотека mnemonic не установлена. Установите через: pip install mnemonic")

# Адреса токенов и контрактов BSC (checksum)
CONTRACTS = {
    'PLEX_ONE': Web3.to_checksum_address('0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1'),
    'USDT': Web3.to_checksum_address('0x55d398326f99059ff775485246999027b3197955'),
    'PANCAKE_ROUTER': Web3.to_checksum_address('0x10ED43C718714eb63d5aA57B78B54704E256024E'),
    'WBNB': Web3.to_checksum_address('0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'),
    'BUSD': Web3.to_checksum_address('0xe9e7cea3dedca5984780bafc599bd69add087d56'),  # Доп. стейбл
    'CAKE': Web3.to_checksum_address('0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82'),  # Популярный маршрут
    'PANCAKE_FACTORY': Web3.to_checksum_address('0xCA143Ce32Fe78f1f7019d7d551a6402fC5350c73')
}

# ABI для ERC20 токенов
ERC20_ABI = '''[
    {
        "constant": true,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    }
]'''

# Минимальный ABI для PancakeSwap Router
PANCAKE_ROUTER_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}]')


class AutoBuyTab(BaseTab):
    """Вкладка для автоматических покупок токенов"""
    
    # Сигналы для обновления UI
    balance_updated = pyqtSignal(dict)
    purchase_completed = pyqtSignal(dict)
    log_message_signal = pyqtSignal(str)  # потокобезопасный лог
    
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)

        # Инициализация переменных
        self.web3 = None
        self.account = None
        self.is_buying = False
        self.buy_thread = None
        self.balances = {}
        self._nonce_lock = threading.Lock()
        self._local_nonce = None  # локальный трекер nonce
        # NonceManager (глобальный, переиспользуемый) — мягкая интеграция
        try:
            self.nonce_manager = get_nonce_manager(getattr(self, 'web3', None))
        except Exception:  # noqa: BLE001
            self.nonce_manager = None

        # Настройка таймера для обновления балансов
        self.balance_timer = QTimer()
        self.balance_timer.timeout.connect(self.update_balances)

        # Подключение сигналов
        self.balance_updated.connect(self._update_balance_display)
        self.purchase_completed.connect(self._handle_purchase_completed)
        self.log_message_signal.connect(self._append_log_line)

        # Альтернативная регистрация Qt типов для межпоточного использования
        try:
            # Пытаемся использовать современный способ регистрации
            from PyQt5.QtCore import QMetaType
            QMetaType.type('QTextCursor')
            logger.info("Qt типы доступны для межпоточного использования")
        except Exception:
            try:
                # Fallback на старый способ если доступен
                from PyQt5.QtCore import qRegisterMetaType
                from PyQt5.QtGui import QTextCursor
                qRegisterMetaType('QTextCursor')
                logger.info("QTextCursor зарегистрирован для межпоточного использования")
            except Exception as e:
                logger.warning(f"Не удалось зарегистрировать QTextCursor: {e}")
                logger.info("Используем прямую передачу логов без Qt сигналов")

        # Инициализация Web3
        self._init_web3()

        logger.info("Вкладка автоматических покупок инициализирована")
        
    def _init_web3(self):
        """Инициализация Web3 подключения с множественными RPC endpoints"""
        # Список RPC endpoints для надежности
        rpc_urls = [
            'https://bsc-dataseed.binance.org/',
            'https://bsc-dataseed1.defibit.io/',
            'https://bsc-dataseed1.ninicoin.io/',
            'https://bsc-dataseed2.defibit.io/',
            'https://bsc-dataseed3.defibit.io/',
            'https://bsc-dataseed4.defibit.io/',
            'https://bsc-dataseed1.binance.org/',
            'https://bsc-dataseed2.binance.org/',
            'https://bsc-dataseed3.binance.org/',
            'https://bsc-dataseed4.binance.org/'
        ]
        
        for rpc_url in rpc_urls:
            try:
                self.log(f"[CONNECT] Пробуем подключиться к {rpc_url}", "INFO")
                self.web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
                
                if self.web3.is_connected():
                    # Проверяем что можем получить блок
                    latest_block = self.web3.eth.block_number
                    self.log(f"[OK] Подключен к BSC через {rpc_url} (блок: {latest_block})", "SUCCESS")
                    
                    # Инициализируем менеджеры
                    try:
                        from ...utils.gas_manager import GasManager
                        from ...utils.token_safety import TokenSafetyChecker
                        from ...utils.async_manager import get_async_manager
                        
                        self.gas_manager = GasManager(self.web3)
                        self.safety_checker = TokenSafetyChecker(self.web3)
                        self.async_manager = get_async_manager(self.web3)
                        
                        self.log("[OK] Менеджеры инициализированы", "SUCCESS")
                    except Exception as e:
                        self.log(f"[WARN] Ошибка инициализации менеджеров: {str(e)}", "WARNING")
                    
                    return
                else:
                    self.log(f"[ERROR] Не удалось подключиться к {rpc_url}", "ERROR")
                    
            except Exception as e:
                self.log(f"[ERROR] Ошибка подключения к {rpc_url}: {str(e)}", "ERROR")
                continue
        
        # Если ни один RPC не сработал
        self.log("[ERROR] Не удалось подключиться ни к одному RPC endpoint", "ERROR")
        # Создаем fallback подключение
        try:
            self.web3 = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
            self.log("[WARN] Создано fallback подключение", "WARNING")
        except Exception as e:
            self.log(f"[ERROR] Ошибка создания fallback подключения: {str(e)}", "ERROR")
            self.web3 = None
            
    def init_ui(self):
        """Инициализация интерфейса вкладки"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        title = QLabel("[BUY] Автоматические покупки токенов")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # Группа подключения кошелька
        wallet_group = self._create_wallet_group()
        layout.addWidget(wallet_group)
        
        # Группа отображения балансов
        balance_group = self._create_balance_group()
        layout.addWidget(balance_group)
        
        # Группа настроек покупки
        buy_settings_group = self._create_buy_settings_group()
        layout.addWidget(buy_settings_group)
        
        # Настройки газа (временно закомментировано)
        # gas_group = self.create_gas_settings_group()
        # layout.addWidget(gas_group)
        
        # Группа управления покупками
        control_group = self._create_control_group()
        layout.addWidget(control_group)
        
        # Лог операций
        log_group = self._create_log_group()
        layout.addWidget(log_group)
        
    def _create_wallet_group(self) -> QGroupBox:
        """Создание группы подключения кошелька"""
        group = QGroupBox("Подключение кошелька")
        layout = QVBoxLayout()
        
        # Выбор типа подключения
        connect_type_layout = QHBoxLayout()
        self.seed_radio = QRadioButton("SEED фраза")
        self.private_key_radio = QRadioButton("Приватный ключ")
        self.seed_radio.setChecked(True)
        
        # Логирование выбора типа подключения
        self.seed_radio.toggled.connect(
            lambda checked: log_radio_change("Тип подключения")(lambda: None)() if checked else None
        )
        self.private_key_radio.toggled.connect(
            lambda checked: log_radio_change("Тип подключения")(lambda: None)() if checked else None
        )
        
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.seed_radio)
        self.button_group.addButton(self.private_key_radio)
        
        connect_type_layout.addWidget(self.seed_radio)
        connect_type_layout.addWidget(self.private_key_radio)
        connect_type_layout.addStretch()
        layout.addLayout(connect_type_layout)
        
        # Поле ввода seed/private key
        self.wallet_input = QTextEdit()
        self.wallet_input.setPlaceholderText("Введите SEED фразу (12 или 24 слова) или приватный ключ...")
        self.wallet_input.setMaximumHeight(60)
        layout.addWidget(self.wallet_input)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("[CONNECT] Подключить кошелек")
        self.connect_btn.clicked.connect(self.connect_wallet)
        button_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("[DISCONNECT] Отключить")
        self.disconnect_btn.clicked.connect(self.disconnect_wallet)
        self.disconnect_btn.setEnabled(False)
        button_layout.addWidget(self.disconnect_btn)
        
        # Кнопка диагностики баланса
        self.debug_balance_btn = QPushButton("[SEARCH] Диагностика баланса")
        self.debug_balance_btn.clicked.connect(self.debug_balance)
        self.debug_balance_btn.setEnabled(False)
        button_layout.addWidget(self.debug_balance_btn)
        
        layout.addLayout(button_layout)
        
        # Отображение адреса кошелька
        self.wallet_address_label = QLabel("Адрес: Не подключен")
        self.wallet_address_label.setFont(QFont("Consolas", 10))
        layout.addWidget(self.wallet_address_label)
        
        group.setLayout(layout)
        return group
        
    def _create_balance_group(self) -> QGroupBox:
        """Создание группы отображения балансов"""
        group = QGroupBox("Балансы токенов")
        layout = QGridLayout()
        
        # Метки для балансов
        layout.addWidget(QLabel("BNB:"), 0, 0)
        self.bnb_balance_label = QLabel("0.0")
        self.bnb_balance_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.bnb_balance_label, 0, 1)
        
        layout.addWidget(QLabel("PLEX ONE:"), 1, 0)
        self.plex_balance_label = QLabel("0.0")
        self.plex_balance_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.plex_balance_label, 1, 1)
        
        layout.addWidget(QLabel("USDT:"), 2, 0)
        self.usdt_balance_label = QLabel("0.0")
        self.usdt_balance_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.usdt_balance_label, 2, 1)
        
        # Кнопка обновления балансов
        self.refresh_btn = QPushButton("🔄 Обновить балансы")
        self.refresh_btn.clicked.connect(self.refresh_all_balances)
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e3a8a;
                border: 1px solid #3b82f6;
                border-radius: 5px;
                padding: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1e40af;
                border-color: #60a5fa;
            }
            QPushButton:pressed {
                background-color: #1e3a8a;
            }
        """)
        layout.addWidget(self.refresh_btn, 3, 0, 1, 2)
        
        # Авто-обновление
        self.auto_refresh_cb = QCheckBox("Авто-обновление каждые 30 сек")
        self.auto_refresh_cb.toggled.connect(self._toggle_auto_refresh)
        self.auto_refresh_cb.toggled.connect(
            lambda c: log_checkbox_change("Авто-обновление балансов")(lambda: None)()
        )
        layout.addWidget(self.auto_refresh_cb, 4, 0, 1, 2)
        
        group.setLayout(layout)
        return group
        
    def _create_buy_settings_group(self) -> QGroupBox:
        """Создание группы настроек покупки"""
        group = QGroupBox("Настройки автоматических покупок")
        layout = QFormLayout()
        
        # Выбор токена для покупки
        self.token_combo = QComboBox()
        self.token_combo.addItems(['PLEX ONE', 'USDT', 'Другой токен'])
        self.token_combo.currentTextChanged.connect(
            lambda t: log_currency_change(lambda: None)()
        )
        layout.addRow("Токен для покупки:", self.token_combo)
        
        # Поле для пользовательского токена
        self.custom_token_input = QLineEdit()
        self.custom_token_input.setPlaceholderText("Адрес контракта токена (0x...)")
        self.custom_token_input.setEnabled(False)
        layout.addRow("Адрес токена:", self.custom_token_input)
        
        # Валюта для покупки (чем покупаем)
        self.buy_with_combo = QComboBox()
        self.buy_with_combo.addItems(['BNB', 'USDT'])
        self.buy_with_combo.currentTextChanged.connect(
            lambda t: log_currency_change(lambda: None)()
        )
        layout.addRow("Покупать за:", self.buy_with_combo)
        
        # Сумма для покупки
        self.buy_amount_input = QDoubleSpinBox()
        self.buy_amount_input.setRange(0.001, 10000)
        self.buy_amount_input.setDecimals(6)
        self.buy_amount_input.setValue(0.01)  # Снижено с 0.1 до 0.01 BNB для достаточности средств
        self.buy_amount_input.valueChanged.connect(
            lambda v: log_spinbox_change("Сумма покупки")(lambda: None)()
        )
        layout.addRow("Сумма на покупку:", self.buy_amount_input)
        
        # Интервал между покупками
        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 86400)  # от 1 секунды до 24 часов
        self.interval_input.setValue(60)  # 1 минута по умолчанию
        self.interval_input.valueChanged.connect(
            lambda v: log_time_change(lambda: None)()
        )
        layout.addRow("Интервал (сек):", self.interval_input)
        
        # Максимальное количество покупок
        self.max_buys_input = QSpinBox()
        self.max_buys_input.setRange(1, 1000)
        self.max_buys_input.setValue(10)
        self.max_buys_input.valueChanged.connect(
            lambda v: log_spinbox_change("Максимум покупок")(lambda: None)()
        )
        layout.addRow("Максимум покупок:", self.max_buys_input)
        
        # Slippage tolerance
        self.slippage_input = QDoubleSpinBox()
        self.slippage_input.setRange(0.1, 50.0)
        self.slippage_input.setDecimals(1)
        self.slippage_input.setValue(5.0)
        self.slippage_input.valueChanged.connect(
            lambda v: log_spinbox_change("Slippage")(lambda: None)()
        )
        layout.addRow("Slippage (%):", self.slippage_input)
        
        # Цена газа (gwei)
        self.gas_price_input = QDoubleSpinBox()
        self.gas_price_input.setRange(0.01, 100.0)
        self.gas_price_input.setDecimals(2)
        self.gas_price_input.setValue(0.1)  # По умолчанию 0.1 gwei
        self.gas_price_input.setSuffix(" gwei")
        self.gas_price_input.setToolTip("Цена газа за транзакцию (0.1 gwei = экономично)")
        self.gas_price_input.valueChanged.connect(
            lambda v: log_spinbox_change("Цена газа")(lambda: None)()
        )
        layout.addRow("Цена газа:", self.gas_price_input)
        
        # Обработка изменения типа токена
        self.token_combo.currentTextChanged.connect(self._on_token_changed)
        
        group.setLayout(layout)
        return group
        
    def _create_control_group(self) -> QGroupBox:
        """Создание группы управления покупками"""
        group = QGroupBox("Управление покупками")
        layout = QVBoxLayout()
        
        # Статистика
        stats_layout = QGridLayout()
        
        stats_layout.addWidget(QLabel("Выполнено покупок:"), 0, 0)
        self.completed_buys_label = QLabel("0")
        self.completed_buys_label.setFont(QFont("Arial", 11, QFont.Bold))
        stats_layout.addWidget(self.completed_buys_label, 0, 1)
        
        stats_layout.addWidget(QLabel("Потрачено:"), 1, 0)
        self.spent_amount_label = QLabel("0.0")
        self.spent_amount_label.setFont(QFont("Arial", 11, QFont.Bold))
        stats_layout.addWidget(self.spent_amount_label, 1, 1)
        
        stats_layout.addWidget(QLabel("Куплено токенов:"), 2, 0)
        self.bought_tokens_label = QLabel("0.0")
        self.bought_tokens_label.setFont(QFont("Arial", 11, QFont.Bold))
        stats_layout.addWidget(self.bought_tokens_label, 2, 1)
        
        layout.addLayout(stats_layout)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("[BUY] Начать покупки")
        self.start_btn.clicked.connect(self.start_auto_buy)
        self.start_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Остановить")
        self.stop_btn.clicked.connect(self.stop_auto_buy)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        self.reset_btn = QPushButton("🔄 Сбросить статистику")
        self.reset_btn.clicked.connect(self.reset_stats)
        button_layout.addWidget(self.reset_btn)
        
        layout.addLayout(button_layout)
        
        group.setLayout(layout)
        return group
        
    def _create_log_group(self) -> QGroupBox:
        """Создание группы логов операций"""
        group = QGroupBox("Лог операций")
        layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)
        
        # Кнопка очистки лога
        clear_btn = QPushButton("[DELETE] Очистить лог")
        clear_btn.clicked.connect(self.clear_log)
        layout.addWidget(clear_btn)
        
        group.setLayout(layout)
        return group
        
    @log_dropdown_change("Тип токена")
    def _on_token_changed(self, token: str):
        """Обработка изменения выбранного токена"""
        self.custom_token_input.setEnabled(token == "Другой токен")
        
    @log_click("Подключить кошелек")
    def connect_wallet(self, checked=False):
        """Подключение кошелька"""
        wallet_data = self.wallet_input.toPlainText().strip()
        
        if not wallet_data:
            QMessageBox.warning(self, "Ошибка", "Введите приватный ключ или SEED фразу!")
            return
            
        # Принудительная очистка предыдущего состояния
        if self.account:
            self.log("🔄 Смена кошелька - очистка предыдущего состояния", "INFO")
            self.disconnect_wallet()
            
        try:
            # Определяем тип входных данных
            if ' ' in wallet_data:  # SEED фраза
                    
                # Предпочитаем корректную деривацию по BIP44: m/44'/60'/0'/0/0
                account_path = "m/44'/60'/0'/0/0"
                created = False
                # 1) Пытаемся через eth_account (предпочтительно, без доп. зависимостей)
                if hasattr(Account, 'from_mnemonic'):
                    try:
                        self.account = Account.from_mnemonic(wallet_data, account_path=account_path)  # type: ignore[arg-type]
                        created = True
                    except Exception:
                        created = False
                # 2) Фолбэк через библиотеку mnemonic + bip_utils (если установлена)
                if not created:
                    try:
                        from mnemonic import Mnemonic
                        from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes  # type: ignore[import]
                        mnemo = Mnemonic("english")
                        if not mnemo.check(wallet_data):
                            raise ValueError("Неверная SEED фраза")
                        seed_bytes = Bip39SeedGenerator(wallet_data).Generate()
                        bip44_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                        private_key = bip44_ctx.PrivateKey().Raw().ToHex()
                        self.account = Account.from_key(private_key)
                        created = True
                    except Exception:
                        created = False
                # 3) Если ничего не вышло — просим ввести приватный ключ, чтобы избежать неверного адреса
                if not created:
                    QMessageBox.critical(
                        self,
                        "Ошибка",
                        "Не удалось создать кошелек из SEED фразы. Введите приватный ключ или установите зависимости: mnemonic, bip_utils."
                    )
                    return
            else:
                # Обработка приватного ключа
                private_key = wallet_data
                if private_key.startswith('0x'):
                    private_key = private_key[2:]
                    
                self.account = Account.from_key(private_key)
            
            # Обновляем UI
            self.wallet_address_label.setText(f"Адрес: {self.account.address}")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.debug_balance_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
            
            self.log(f"[OK] Кошелек подключен: {self.account.address}", "SUCCESS")
            
            # Обновляем балансы
            self.update_balances()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключить кошелек: {str(e)}")
            self.log(f"[ERROR] Ошибка подключения кошелька: {str(e)}", "ERROR")
            
    @log_click("Отключить кошелек")
    def disconnect_wallet(self, checked=False):
        """Отключение кошелька"""
        self.log("[DISCONNECT] Отключение кошелька...", "INFO")
        
        # Принудительная остановка всех процессов
        if self.is_buying:
            self.log("⏹️ Принудительная остановка автопокупок", "WARNING")
            self.stop_auto_buy()
            # Ждем завершения потока
            if hasattr(self, 'buy_thread') and self.buy_thread and self.buy_thread.is_alive():
                self.log("⏳ Ожидание завершения рабочего потока...", "INFO")
                self.buy_thread.join(timeout=3.0)
                if self.buy_thread.is_alive():
                    self.log("[WARN] Рабочий поток не завершился в срок", "WARNING")
        
        # Очищаем аккаунт и nonce manager
        self.account = None
        if hasattr(self, 'nonce_manager') and self.nonce_manager:
            self.nonce_manager = None
            
        # Очищаем поле ввода
        self.wallet_input.clear()
            
        # Обновляем UI
        self.wallet_address_label.setText("Адрес: Не подключен")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.debug_balance_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        
        # Очищаем балансы
        self.bnb_balance_label.setText("0.0")
        self.plex_balance_label.setText("0.0")
        self.usdt_balance_label.setText("0.0")
        
        # Останавливаем авто-обновление
        self.balance_timer.stop()
        self.auto_refresh_cb.setChecked(False)
        
        self.log("[DISCONNECT] Кошелек отключен", "INFO")
        
    @log_click("Обновить балансы")
    def refresh_all_balances(self, checked=False):
        """Обновляет все балансы токенов с детальным логированием"""
        self.log("🔄 Обновляем балансы всех токенов...", "INFO")
        
        if not self.account:
            self.log("[ERROR] Кошелек не подключен", "ERROR")
            return
            
        try:
            # Проверяем и обновляем Web3 подключение
            if not self.web3 or not self.web3.is_connected():
                self.log("[WARN] Web3 не подключен, переподключаемся...", "WARNING")
                self._init_web3()
            
            # Обновляем BNB баланс
            try:
                checksum_address = Web3.to_checksum_address(self.account.address)
                bnb_balance = self.web3.eth.get_balance(checksum_address)
                bnb_formatted = self.web3.from_wei(bnb_balance, 'ether')
                self.bnb_balance_label.setText(f"{bnb_formatted:.6f}")
                self.log(f"[MONEY] BNB баланс: {bnb_formatted:.6f}", "SUCCESS")
            except Exception as e:
                self.bnb_balance_label.setText("Ошибка")
                self.log(f"[ERROR] Ошибка получения BNB баланса: {e}", "ERROR")
            
            # Обновляем PLEX ONE баланс
            try:
                plex_balance = self._get_token_balance(CONTRACTS['PLEX_ONE'])
                self.plex_balance_label.setText(f"{plex_balance:.6f}")
                if plex_balance > 0:
                    self.log(f"[MONEY] PLEX ONE баланс: {plex_balance:.6f}", "SUCCESS")
            except Exception as e:
                self.plex_balance_label.setText("Ошибка")
                self.log(f"[ERROR] Ошибка получения PLEX ONE баланса: {e}", "ERROR")
            
            # Обновляем USDT баланс
            try:
                usdt_balance = self._get_token_balance(CONTRACTS['USDT'])
                self.usdt_balance_label.setText(f"{usdt_balance:.6f}")
                if usdt_balance > 0:
                    self.log(f"[MONEY] USDT баланс: {usdt_balance:.6f}", "SUCCESS")
            except Exception as e:
                self.usdt_balance_label.setText("Ошибка")
                self.log(f"[ERROR] Ошибка получения USDT баланса: {e}", "ERROR")
            
            self.log("[OK] Обновление балансов завершено", "SUCCESS")
            
        except Exception as e:
            self.log(f"[ERROR] Критическая ошибка обновления балансов: {str(e)}", "ERROR")
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить балансы:\n{str(e)}")

    @log_click("Диагностика баланса")
    def debug_balance(self, checked=False):
        """Диагностика баланса токенов"""
        self.log("[SEARCH] === ДИАГНОСТИКА БАЛАНСА ===", "INFO")
        
        if not self.account:
            self.log("[ERROR] Кошелек не подключен", "ERROR")
            return
            
        self.log(f"[OK] Кошелек подключен: {self.account.address}", "SUCCESS")
        
        if not self.web3:
            self.log("[ERROR] Web3 не подключен", "ERROR")
            return
            
        self.log("[OK] Web3 подключен к BSC", "SUCCESS")
        
        # BNB баланс
        try:
            checksum_address = Web3.to_checksum_address(self.account.address)
            bnb_balance = self.web3.eth.get_balance(checksum_address)
            bnb_formatted = self.web3.from_wei(bnb_balance, 'ether')
            self.log(f"[MONEY] BNB баланс: {bnb_formatted:.6f}", "SUCCESS")
        except Exception as e:
            self.log(f"[ERROR] Ошибка получения BNB баланса: {e}", "ERROR")
        
        # PLEX ONE баланс
        try:
            self.log(f"[SEARCH] Проверяем токен: PLEX ONE ({CONTRACTS['PLEX_ONE']})", "INFO")
            plex_checksum = Web3.to_checksum_address(CONTRACTS['PLEX_ONE'])
            contract_code = self.web3.eth.get_code(plex_checksum)
            if contract_code and contract_code != b'':
                plex_contract = self.web3.eth.contract(address=plex_checksum, abi=ERC20_ABI)
                plex_balance_raw = plex_contract.functions.balanceOf(checksum_address).call()
                plex_decimals = plex_contract.functions.decimals().call()
                plex_balance = plex_balance_raw / (10 ** plex_decimals)
                self.log(f"[OK] Баланс PLEX ONE: {plex_balance:.6f}", "SUCCESS")
            else:
                self.log(f"[ERROR] Контракт PLEX ONE не найден", "ERROR")
        except Exception as e:
            self.log(f"[ERROR] Ошибка получения PLEX ONE баланса: {e}", "ERROR")
        
        # USDT баланс
        try:
            self.log(f"[SEARCH] Проверяем токен: USDT ({CONTRACTS['USDT']})", "INFO")
            usdt_checksum = Web3.to_checksum_address(CONTRACTS['USDT'])
            contract_code = self.web3.eth.get_code(usdt_checksum)
            if contract_code and contract_code != b'':
                usdt_contract = self.web3.eth.contract(address=usdt_checksum, abi=ERC20_ABI)
                usdt_balance_raw = usdt_contract.functions.balanceOf(checksum_address).call()
                usdt_decimals = usdt_contract.functions.decimals().call()
                usdt_balance = usdt_balance_raw / (10 ** usdt_decimals)
                self.log(f"[OK] Баланс USDT: {usdt_balance:.6f}", "SUCCESS")
            else:
                self.log(f"[ERROR] Контракт USDT не найден", "ERROR")
        except Exception as e:
            self.log(f"[ERROR] Ошибка получения USDT баланса: {e}", "ERROR")
        
        self.log("[SEARCH] === КОНЕЦ ДИАГНОСТИКИ ===", "INFO")

    def _get_token_balance(self, token_address: str) -> float:
        """Получение баланса токена с полной проверкой"""
        try:
            if not self.account or not self.web3:
                self.log("[ERROR] Кошелек или Web3 не подключен", "ERROR")
                return 0
            
            # Проверяем подключение к сети
            if not self.web3.is_connected():
                self.log("[ERROR] Нет подключения к BSC сети", "ERROR")
                return 0
            
            # Проверяем адрес токена
            if not Web3.is_address(token_address):
                self.log(f"[ERROR] Неверный адрес токена: {token_address}", "ERROR")
                return 0
            
            # Проверяем, что адрес токена валидный
            checksum_address = Web3.to_checksum_address(token_address)
            
            # Проверяем, что контракт существует
            try:
                code = self.web3.eth.get_code(checksum_address)
                if code == b'':
                    self.log(f"[ERROR] Контракт не найден по адресу: {checksum_address}", "ERROR")
                    return 0
            except Exception as e:
                self.log(f"[ERROR] Ошибка проверки контракта: {str(e)}", "ERROR")
                return 0
            
            # Создаем контракт
            token_contract = self.web3.eth.contract(
                address=checksum_address,
                abi=ERC20_ABI
            )
            
            # Получаем decimals
            try:
                decimals = token_contract.functions.decimals().call()
            except Exception as e:
                self.log(f"[ERROR] Ошибка получения decimals: {str(e)}", "ERROR")
                decimals = 18  # Fallback на стандартные 18 decimals
            
            # Получаем баланс
            wallet_address = Web3.to_checksum_address(self.account.address)
            try:
                balance = token_contract.functions.balanceOf(wallet_address).call()
            except Exception as e:
                self.log(f"[ERROR] Ошибка получения баланса: {str(e)}", "ERROR")
                return 0
            
            # Конвертируем в читаемый формат
            formatted_balance = balance / (10 ** decimals)
            
            # Логируем только если баланс больше 0 или есть ошибки
            if formatted_balance > 0:
                self.log(f"[OK] Баланс {checksum_address[:10]}...: {formatted_balance:.6f}", "SUCCESS")
            
            return formatted_balance
            
        except Exception as e:
            self.log(f"[ERROR] Критическая ошибка получения баланса токена: {str(e)}", "ERROR")
            return 0

    def update_balances(self):
        """Обновление балансов токенов"""
        if not self.account or not self.web3:
            return
            
        try:
            address = self.account.address
            
            # Получаем баланс BNB
            bnb_balance_wei = self.web3.eth.get_balance(address)
            bnb_balance = self.web3.from_wei(bnb_balance_wei, 'ether')
            
            # Получаем баланс PLEX ONE
            try:
                plex_contract = self.web3.eth.contract(
                    address=CONTRACTS['PLEX_ONE'],
                    abi=ERC20_ABI
                )
                plex_balance_raw = plex_contract.functions.balanceOf(address).call()
                plex_decimals = plex_contract.functions.decimals().call()
                plex_balance = plex_balance_raw / (10 ** plex_decimals)
            except Exception as e:
                plex_balance = 0.0
                self.log(f"[WARN] Ошибка получения баланса PLEX: {str(e)}", "WARNING")
                
            # Получаем баланс USDT
            try:
                usdt_contract = self.web3.eth.contract(
                    address=CONTRACTS['USDT'],
                    abi=ERC20_ABI
                )
                usdt_balance_raw = usdt_contract.functions.balanceOf(address).call()
                usdt_decimals = usdt_contract.functions.decimals().call()
                usdt_balance = usdt_balance_raw / (10 ** usdt_decimals)
            except Exception as e:
                usdt_balance = 0.0
                self.log(f"[WARN] Ошибка получения баланса USDT: {str(e)}", "WARNING")
                
            # Сохраняем балансы
            self.balances = {
                'bnb': float(bnb_balance),
                'plex': float(plex_balance),
                'usdt': float(usdt_balance)
            }
            
            # Отправляем сигнал для обновления UI
            self.balance_updated.emit(self.balances)
            
        except Exception as e:
            self.log(f"[ERROR] Ошибка обновления балансов: {str(e)}", "ERROR")
            
    def _update_balance_display(self, balances: dict):
        """Обновление отображения балансов"""
        self.bnb_balance_label.setText(f"{balances.get('bnb', 0):.6f}")
        self.plex_balance_label.setText(f"{balances.get('plex', 0):.2f}")
        self.usdt_balance_label.setText(f"{balances.get('usdt', 0):.2f}")
        
    def _toggle_auto_refresh(self, enabled: bool):
        """Переключение авто-обновления балансов"""
        if enabled and self.account:
            self.balance_timer.start(30000)  # 30 секунд
            self.log("[OK] Авто-обновление балансов включено", "INFO")
        else:
            self.balance_timer.stop()
            self.log("🔄 Авто-обновление балансов отключено", "INFO")
            
    @log_click("Начать покупки")
    def start_auto_buy(self, checked=False):
        """Запуск автоматических покупок"""
        if not self.account:
            QMessageBox.warning(self, "Ошибка", "Сначала подключите кошелек!")
            return
            
        if self.is_buying:
            QMessageBox.warning(self, "Ошибка", "Покупки уже запущены!")
            return
            
        # Валидация настроек
        if not self._validate_buy_settings():
            return
            
        self.is_buying = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Запускаем поток покупок с обработкой исключений
        try:
            self.buy_thread = threading.Thread(target=self._buy_worker, daemon=True)
            self.buy_thread.start()
            self.log("🧵 Рабочий поток покупок запущен", "INFO")
        except Exception as e:
            self.log(f"[ERROR] Ошибка запуска потока покупок: {str(e)}", "ERROR")
            self.is_buying = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
        
        self.log("[BUY] Автоматические покупки запущены", "SUCCESS")
        
    @log_click("Остановить покупки")
    def stop_auto_buy(self, checked=False):
        """Остановка автоматических покупок"""
        self.is_buying = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.log("⏹️ Автоматические покупки остановлены", "WARNING")
        
    def _validate_buy_settings(self) -> bool:
        """Валидация настроек покупки"""
        # Проверяем токен
        if self.token_combo.currentText() == "Другой токен":
            custom_token = self.custom_token_input.text().strip()
            if not custom_token or not Web3.is_address(custom_token):
                QMessageBox.warning(self, "Ошибка", "Введите корректный адрес токена!")
                return False
                
        # Проверяем баланс
        buy_with = self.buy_with_combo.currentText()
        amount = self.buy_amount_input.value()
        
        if buy_with == "BNB" and self.balances.get('bnb', 0) < amount:
            QMessageBox.warning(self, "Ошибка", "Недостаточно BNB для покупки!")
            return False
        elif buy_with == "USDT" and self.balances.get('usdt', 0) < amount:
            QMessageBox.warning(self, "Ошибка", "Недостаточно USDT для покупки!")
            return False
            
        return True
        
    def _buy_worker(self):
        """Рабочий поток для автоматических покупок"""
        completed_buys = 0
        failed_attempts = 0
        max_failed_attempts = 5
        
        try:
            max_buys = self.max_buys_input.value()
            interval = self.interval_input.value()
            
            self.log(f"[START] Запуск рабочего потока покупок: {max_buys} покупок с интервалом {interval}с", "INFO")
            
            while self.is_buying and completed_buys < max_buys and failed_attempts < max_failed_attempts:
                try:
                    self.log(f"[BUY] Попытка покупки #{completed_buys + 1}/{max_buys}", "INFO")
                    
                    # Выполняем покупку
                    result = self._execute_buy()
                    
                    if result['success']:
                        completed_buys += 1
                        failed_attempts = 0  # Сбрасываем счетчик неудач
                        
                        self.purchase_completed.emit({
                            'buy_number': completed_buys,
                            'tx_hash': result.get('tx_hash', ''),
                            'amount_spent': result.get('amount_spent', 0),
                            'tokens_bought': result.get('tokens_bought', 0)
                        })
                        
                        self.log(f"[OK] Покупка #{completed_buys} завершена успешно", "SUCCESS")
                    else:
                        failed_attempts += 1
                        error_msg = result.get('error', 'Неизвестная ошибка')
                        self.log(f"[ERROR] Покупка не удалась ({failed_attempts}/{max_failed_attempts}): {error_msg}", "ERROR")
                        
                    # Ждем интервал перед следующей покупкой
                    if self.is_buying and completed_buys < max_buys and failed_attempts < max_failed_attempts:
                        self.log(f"⏳ Ожидание {interval} секунд до следующей покупки...", "INFO")
                        # Используем более эффективное ожидание с проверкой остановки
                        sleep_chunks = max(1, interval // 10)  # Проверяем остановку каждые 0.1 * interval секунд
                        for i in range(interval * 10):  # 10 проверок в секунду
                            if not self.is_buying:
                                break
                            time.sleep(0.1)
                        
                except Exception as e:
                    failed_attempts += 1
                    self.log(f"[ERROR] Критическая ошибка в процессе покупки ({failed_attempts}/{max_failed_attempts}): {str(e)}", "ERROR")
                    
                    # Если слишком много ошибок подряд - останавливаемся
                    if failed_attempts >= max_failed_attempts:
                        self.log(f"🛑 Слишком много неудачных попыток ({failed_attempts}). Остановка автопокупок.", "ERROR")
                        break
                        
                    # Ждем перед повторной попыткой
                    time.sleep(min(interval, 30))  # Максимум 30 секунд между попытками
                    
        except Exception as e:
            self.log(f"💥 Фатальная ошибка в рабочем потоке: {str(e)}", "ERROR")
            logger.error(f"Fatal error in buy worker thread: {e}", exc_info=True)
        finally:
            # Безопасно завершаем поток
            try:
                self.is_buying = False
                
                # Получаем значения безопасно
                try:
                    max_buys_final = max_buys if 'max_buys' in locals() else 0
                except:
                    max_buys_final = 0
                
                # Обновляем UI безопасно
                try:
                    self.start_btn.setEnabled(True)
                    self.stop_btn.setEnabled(False)
                except Exception as e:
                    self.log(f"[WARN] Ошибка обновления UI: {e}", "WARNING")
                
                if failed_attempts >= max_failed_attempts:
                    self.log(f"[FINISH] Автопокупки остановлены из-за ошибок. Выполнено: {completed_buys}/{max_buys_final}", "ERROR")
                elif max_buys_final > 0 and completed_buys >= max_buys_final:
                    self.log(f"[FINISH] Автопокупки завершены успешно. Выполнено: {completed_buys}/{max_buys_final}", "SUCCESS")
                else:
                    self.log(f"[FINISH] Автопокупки остановлены. Выполнено: {completed_buys}/{max_buys_final}", "WARNING")
                    
            except Exception as e:
                self.log(f"[WARN] Ошибка при завершении потока: {str(e)}", "WARNING")
            
    def _retry_call(self, func, max_retries: int = 3, delay: float = 2.0):
        """Универсальная функция retry для вызовов"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    self.log(f"[WARN] Попытка {attempt + 1}/{max_retries} не удалась: {e}", "WARNING")
                    self.log(f"🔄 Повторная попытка через {delay} секунд...", "INFO")
                    time.sleep(delay * (attempt + 1))  # Экспоненциальная задержка
                    
        raise last_error

    def _get_amounts_out_with_retry(self, amount_in: int, path: List[str]) -> List[int]:
        """Получает ожидаемое количество токенов на выходе с retry"""
        def _get():
            path_checksum = [Web3.to_checksum_address(addr) for addr in path]
            router_contract = self.web3.eth.contract(
                address=CONTRACTS['PANCAKE_ROUTER'],
                abi=PANCAKE_ROUTER_ABI
            )
            return router_contract.functions.getAmountsOut(amount_in, path_checksum).call()
        
        try:
            result = self._retry_call(_get, max_retries=3, delay=2.0)
            # Проверяем валидность результата
            if not result or not isinstance(result, list) or len(result) < 2:
                self.log(f"[WARN] Некорректный результат getAmountsOut: {result}", "WARNING")
                return []
            return result
        except Exception as e:
            self.log(f"[ERROR] Ошибка getAmountsOut: {str(e)}", "ERROR")
            return []

    def _get_token_symbol(self, address: str) -> str:
        """Получает символ токена по адресу для отображения"""
        address_lower = address.lower()
        if address_lower == CONTRACTS['WBNB'].lower():
            return 'WBNB'
        elif address_lower == CONTRACTS['USDT'].lower():
            return 'USDT'
        elif address_lower == CONTRACTS['PLEX_ONE'].lower():
            return 'PLEX ONE'
        elif address_lower == CONTRACTS.get('BUSD', '').lower():
            return 'BUSD'
        elif address_lower == CONTRACTS.get('CAKE', '').lower():
            return 'CAKE'
        else:
            return address[:10] + '...'
    
    def _determine_decimals(self, token_symbol: str, token_address: str) -> int:
        """Определяет decimals токена."""
        # Кэш для известных токенов
        known_decimals = {
            CONTRACTS['USDT'].lower(): 18,  # USDT на BSC имеет 18 decimals
            CONTRACTS['PLEX_ONE'].lower(): 9,  # PLEX ONE имеет 9 decimals
            CONTRACTS['WBNB'].lower(): 18,  # WBNB имеет 18 decimals
        }
        
        # Проверяем в кэше
        address_lower = token_address.lower()
        if address_lower in known_decimals:
            return known_decimals[address_lower]
        
        # Пытаемся запросить из контракта
        try:
            erc20 = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address), 
                abi=json.loads('[{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"stateMutability":"view","type":"function"}]')
            )
            decimals = erc20.functions.decimals().call()
            self.log(f"[STATS] Decimals для {token_address[:10]}...: {decimals}", "INFO")
            return decimals
        except Exception as e:
            self.log(f"[WARN] Не удалось получить decimals для {token_address[:10]}...: {e}", "WARNING")
            return 18  # по умолчанию

    def _get_best_path_and_quote(self, amount_in_wei: int, token_address: str, pay_with: str) -> Dict[str, Any]:
        """Проверка ликвидности и получение правильного пути для покупки."""
        try:
            token = Web3.to_checksum_address(token_address)
            wbnb = CONTRACTS['WBNB']
            usdt = CONTRACTS['USDT']
            
            # Список путей для проверки (от простого к сложному)
            paths_to_try = []
            
            if pay_with == 'USDT':
                # Для покупки за USDT пробуем разные пути
                paths_to_try = [
                    [usdt, token],  # Прямой путь USDT -> Token
                    [usdt, wbnb, token],  # Через WBNB: USDT -> WBNB -> Token
                ]
                test_amount = amount_in_wei
            else:  # pay_with == 'BNB'
                # Для покупки за BNB
                paths_to_try = [
                    [wbnb, token],  # Прямой путь WBNB -> Token
                    [wbnb, usdt, token],  # Через USDT: WBNB -> USDT -> Token
                ]
                test_amount = amount_in_wei
            
            # Специальная обработка для PLEX ONE
            if token.lower() == CONTRACTS['PLEX_ONE'].lower():
                if pay_with == 'USDT':
                    # Для PLEX ONE есть прямой пул с USDT
                    paths_to_try = [[usdt, token]]
                else:
                    # Для BNB используем путь через USDT так как это основной пул
                    paths_to_try = [
                        [wbnb, token],  # Пробуем прямой
                        [wbnb, usdt, token]  # Через USDT
                    ]
            
            # Пробуем каждый путь
            best_result = None
            best_amount = 0
            
            for path in paths_to_try:
                try:
                    path_display = ' -> '.join([self._get_token_symbol(p) for p in path])
                    self.log(f"[SEARCH] Проверяем путь: {path_display}", "INFO")
                    
                    amounts = self._get_amounts_out_with_retry(test_amount, path)
                    
                    if amounts and len(amounts) > 1 and amounts[-1] > 0:
                        output_amount = amounts[-1]
                        self.log(f"[OK] Путь {path_display}: выход {output_amount}", "SUCCESS")
                        
                        # Выбираем путь с лучшим выходом
                        if output_amount > best_amount:
                            best_amount = output_amount
                            best_result = {'success': True, 'path': path, 'amounts': amounts}
                    else:
                        self.log(f"[ERROR] Путь {path_display}: нет ликвидности", "WARNING")
                        
                except Exception as e:
                    self.log(f"[WARN] Ошибка проверки пути: {e}", "WARNING")
                    continue
            
            if best_result:
                return best_result
            else:
                return {'success': False, 'error': 'Не найден путь с достаточной ликвидностью', 'path': paths_to_try[0]}
                
        except Exception as e:  # noqa: BLE001
            return {'success': False, 'error': str(e)}

    def _validate_buy_params(self, token_address: str, amount: float, buy_with: str) -> Dict[str, Any]:
        """Валидирует параметры покупки перед выполнением"""
        try:
            # Проверка подключения
            if not self.web3 or not self.web3.is_connected():
                raise Exception("Нет подключения к блокчейну")
                
            # Проверка кошелька
            if not self.account:
                raise Exception("Кошелек не подключен")
                
            # Проверка адреса токена
            if not token_address or not token_address.startswith('0x'):
                raise ValueError("Неверный адрес токена")
                
            # Проверка суммы
            if amount <= 0:
                raise ValueError("Сумма должна быть больше 0")
                
            # Проверка баланса для покупки
            if buy_with == 'BNB':
                bnb_balance = self.web3.eth.get_balance(self.account.address)
                bnb_balance_eth = self.web3.from_wei(bnb_balance, 'ether')
                if bnb_balance_eth < amount:
                    raise ValueError(f"Недостаточно BNB. Баланс: {bnb_balance_eth:.6f}, требуется: {amount}")
            else:  # USDT
                usdt_contract = self.web3.eth.contract(address=CONTRACTS['USDT'], abi=ERC20_ABI)
                usdt_balance_wei = usdt_contract.functions.balanceOf(self.account.address).call()
                usdt_balance = self.web3.from_wei(usdt_balance_wei, 'ether')  # USDT на BSC имеет 18 decimals
                if usdt_balance < amount:
                    raise ValueError(f"Недостаточно USDT. Баланс: {usdt_balance:.4f}, требуется: {amount}")
                
            return {
                'valid': True,
                'bnb_balance': bnb_balance_eth if buy_with == 'BNB' else None,
                'usdt_balance': usdt_balance if buy_with == 'USDT' else None
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    def _execute_buy(self) -> Dict[str, Any]:
        """Выполнение одной покупки через PancakeSwap с улучшенной обработкой ошибок"""
        try:
            self.log("=== Начало операции покупки ===", "INFO")
            
            if not self.account or not self.web3:
                return {
                    'success': False,
                    'error': 'Кошелек не подключен'
                }
            
            # Получаем параметры покупки
            buy_amount = self.buy_amount_input.value()
            buy_with = self.buy_with_combo.currentText()  # Валюта для покупки (BNB или USDT)
            
            # Детальное логирование параметров
            self.log(f"[TARGET] Начинаем покупку: Сумма {buy_amount}, Валюта оплаты: {buy_with}", "INFO")
            
            # Определяем токен для покупки
            selected_token = self.token_combo.currentText()
            self.log(f"[BUY] Выбранный токен для покупки: {selected_token}", "INFO")
            
            if selected_token == 'PLEX ONE':
                token_address = CONTRACTS['PLEX_ONE']
                self.log(f"[INFO] Адрес PLEX ONE: {token_address}", "INFO")
            elif selected_token == 'USDT':
                token_address = CONTRACTS['USDT']
                self.log(f"[INFO] Адрес USDT: {token_address}", "INFO")
            else:
                # Пользовательский токен
                token_address = self.custom_token_input.text().strip()
                self.log(f"[INFO] Пользовательский адрес токена: {token_address}", "INFO")
                if not token_address or not Web3.is_address(token_address):
                    self.log("[ERROR] Неверный адрес пользовательского токена", "ERROR")
                    return {'success': False, 'error': 'Неверный адрес токена'}
            
            # Проверяем что не покупаем тот же токен, которым платим
            if buy_with == 'USDT' and selected_token == 'USDT':
                self.log("[ERROR] Нельзя покупать USDT за USDT", "ERROR")
                return {'success': False, 'error': 'Нельзя покупать тот же токен которым платите'}
            
            # Валидация параметров покупки
            validation = self._validate_buy_params(token_address, buy_amount, buy_with)
            if not validation['valid']:
                self.log(f"[ERROR] Ошибка валидации: {validation['error']}", "ERROR")
                return {'success': False, 'error': validation['error']}
            
            # Проверяем ликвидность с правильным путем для покупки
            self.log("[SEARCH] Проверяем ликвидность для покупки...", "INFO")
            if buy_with == 'BNB':
                amount_wei = self.web3.to_wei(buy_amount, 'ether')
            else:
                # USDT на BSC имеет 18 decimals
                amount_wei = self.web3.to_wei(buy_amount, 'ether')
            
            self.log(f"[MONEY] Сумма для обмена: {buy_amount} {buy_with} = {amount_wei} wei", "INFO")
            
            quote = self._get_best_path_and_quote(amount_wei, token_address, buy_with)
            if not quote['success']:
                self.log(f"[ERROR] Ликвидность недоступна: {quote['error']}", "ERROR")
                return {'success': False, 'error': quote['error']}
            
            path = quote['path']  # правильный путь для покупки
            amounts_out = quote['amounts']
            
            # Получаем правильные decimals для целевого токена
            token_decimals = self._determine_decimals(selected_token, token_address)
            expected_tokens = amounts_out[-1] / (10 ** token_decimals)
            
            self.log(f"[STATS] Decimals целевого токена {selected_token}: {token_decimals}", "INFO")
            self.log(f"[STATS] Ожидаемый выход в wei: {amounts_out[-1]}", "INFO")
            
            # Показываем корректные адреса в логе
            path_display = []
            for addr in path:
                if addr == CONTRACTS['USDT']:
                    path_display.append('USDT')
                elif addr == CONTRACTS['WBNB']:
                    path_display.append('WBNB')
                elif addr == CONTRACTS['PLEX_ONE']:
                    path_display.append('PLEX ONE')
                else:
                    path_display.append(addr[:10] + '...')
            
            self.log(f"[SEARCH] Путь покупки: {' -> '.join(path_display)}", "INFO")
            self.log(f"[SEARCH] Ожидается получить: {expected_tokens:.6f} {selected_token} (decimals={token_decimals})", "INFO")
            
            self.log(f"[BUY] Выполняется реальная покупка {selected_token} за {buy_with} через PancakeSwap...", "INFO")
            
            # Создаем контракт PancakeSwap Router
            router_address = CONTRACTS['PANCAKE_ROUTER']
            self.log(f"[INFO] PancakeSwap Router: {router_address}", "INFO")
            
            # Параметры транзакции
            deadline = int(time.time()) + 300  # 5 минут
            
            if buy_with == 'BNB':
                self.log("[MONEY] Режим покупки: BNB -> Token (swapExactETHForTokens)", "INFO")
                # Покупка за BNB через DexSwapService
                if 'path' not in locals() or not path:
                    path = [CONTRACTS['WBNB'], Web3.to_checksum_address(token_address)]
                self.log(f"🔄 Итоговый путь обмена: {' -> '.join(path)}", "INFO")
                amount_wei = self.web3.to_wei(buy_amount, 'ether')
                self.log(f"[MONEY] Сумма BNB в wei: {amount_wei} ({buy_amount} BNB)", "INFO")
                # Инициализация сервиса (ленивая)
                if not hasattr(self, '_dex_service'):
                    try:
                        # Получаем кастомную цену газа из интерфейса
                        custom_gas_price = self.gas_price_input.value()
                        self._dex_service = DexSwapService(self.web3, router_address, self.account.key, custom_gas_price_gwei=custom_gas_price)  # type: ignore[attr-defined]
                        self.log(f"[CONFIG] DexSwapService инициализирован с ценой газа {custom_gas_price} gwei", "INFO")
                    except Exception as e:  # noqa: BLE001
                        self.log(f"[WARN] DexSwapService init fail: {e}", "WARNING")
                        self._dex_service = None
                else:
                    # Обновляем цену газа в существующем DexSwapService
                    custom_gas_price = self.gas_price_input.value()
                    if hasattr(self._dex_service, 'set_custom_gas_price'):
                        self._dex_service.set_custom_gas_price(custom_gas_price)
                        self.log(f"[SETTINGS] Обновлена цена газа до {custom_gas_price} gwei", "INFO")
                if self._dex_service:
                    try:
                        swap_hash = self._dex_service.swap_exact_eth_for_tokens(
                            amount_in_wei=amount_wei,
                            amount_out_min=0,
                            path=path,
                            deadline=deadline
                        )
                        self._mark_nonce_pending(swap_hash)
                        self.log(f"[SEND] Swap отправлен: {swap_hash}", "INFO")
                        self.log(f"[CONNECT] https://bscscan.com/tx/{swap_hash}", "INFO")
                    except Exception as e:  # noqa: BLE001
                        self.log(f"[ERROR] Ошибка swapExactETHForTokens (service): {e}", "ERROR")
                        raise
                
            else:  # buy_with == 'USDT'
                self.log("💵 Режим покупки: USDT -> Token (approve + swapExactTokensForTokens)", "INFO")
                # Покупка за USDT (Token -> Token)
                
                # Сначала нужно сделать approve для USDT
                usdt_address = CONTRACTS['USDT']
                self.log(f"[INFO] USDT адрес: {usdt_address}", "INFO")
                erc20_abi = json.loads('[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]')
                
                usdt_contract = self.web3.eth.contract(address=usdt_address, abi=erc20_abi)
                # USDT на BSC имеет 18 decimals
                amount_in_units = self.web3.to_wei(buy_amount, 'ether')
                self.log(f"💵 Сумма USDT в wei: {amount_in_units}", "INFO")
                
                # Approve транзакция
                self.log("📝 Делаем approve для USDT...", "INFO")
                if not hasattr(self, '_dex_service'):
                    try:
                        # Получаем кастомную цену газа из интерфейса
                        custom_gas_price = self.gas_price_input.value()
                        self._dex_service = DexSwapService(self.web3, router_address, self.account.key, custom_gas_price_gwei=custom_gas_price)  # type: ignore[attr-defined]
                        self.log(f"[CONFIG] DexSwapService инициализирован с ценой газа {custom_gas_price} gwei", "INFO")
                    except Exception as e:  # noqa: BLE001
                        self.log(f"[WARN] DexSwapService init fail: {e}", "WARNING")
                        self._dex_service = None
                # Approve через сервис (или fallback)
                approve_hash = None
                if self._dex_service:
                    try:
                        approve_hash = self._dex_service.approve(usdt_address, amount_wei=amount_in_units)
                        self.log(f"[SEND] Approve отправлен: {approve_hash}", "INFO")
                    except Exception as e:  # noqa: BLE001
                        self.log(f"[ERROR] Ошибка approve через сервис: {e}", "ERROR")
                        raise
                else:
                    approve_tx = usdt_contract.functions.approve(
                        router_address,
                        amount_in_units
                    ).build_transaction({
                        'from': self.account.address,
                        'gas': self.get_gas_limit(),
                        'gasPrice': self.get_gas_price_wei(),
                        'nonce': self._next_nonce()
                    })
                    signed_approve = self.web3.eth.account.sign_transaction(approve_tx, self.account.key)
                    raw_hash = self.web3.eth.send_raw_transaction(signed_approve.rawTransaction)
                    if raw_hash:
                        self._mark_nonce_pending(raw_hash.hex())
                        approve_hash = raw_hash.hex()
                if not approve_hash:
                    raise Exception("Не удалось отправить approve транзакцию")
                self.log(f" https://bscscan.com/tx/{approve_hash}", "INFO")
                self.log("⏳ Ожидание подтверждения approve...", "INFO")
                approve_receipt = self.web3.eth.wait_for_transaction_receipt(approve_hash, timeout=180)
                if not (approve_receipt and approve_receipt['status'] == 1):
                    raise Exception("Approve транзакция провалилась")
                self.log(f"[OK] Approve завершен. Gas used: {approve_receipt['gasUsed']}", "SUCCESS")
                time.sleep(1)
                self.log(f"[STATS] Pending nonce после approve: {self.web3.eth.get_transaction_count(self.account.address,'pending')}", "INFO")
                
                # Теперь основная транзакция
                router_abi = [
                    {
                        "inputs": [
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                            {"internalType": "address[]", "name": "path", "type": "address[]"},
                            {"internalType": "address", "name": "to", "type": "address"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                        ],
                        "name": "swapExactTokensForTokens",
                        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                        "stateMutability": "nonpayable",
                        "type": "function"
                    }
                ]
                
                router_contract = self.web3.eth.contract(
                    address=router_address,
                    abi=router_abi
                )
                
                # Создаем путь обмена - используем тот же путь, что был найден при проверке
                if 'path' in locals() and path:
                    self.log(f"🔄 Используем найденный путь: {' -> '.join([self._get_token_symbol(p) for p in path])}", "INFO")
                else:
                    # Fallback если path не определен
                    if token_address.lower() == CONTRACTS['PLEX_ONE'].lower():
                        path = [CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']]
                        self.log(f"🔄 Путь обмена: USDT -> PLEX ONE (прямой)", "INFO")
                    else:
                        path = [usdt_address, Web3.to_checksum_address(token_address)]
                        self.log(f"🔄 Путь обмена: USDT -> {selected_token}", "INFO")
                
                # Выполняем swap через сервис
                swap_hash = None
                if hasattr(self, '_dex_service') and self._dex_service:
                    try:
                        swap_hash = self._dex_service.swap_exact_tokens_for_tokens(
                            amount_in=amount_in_units,
                            amount_out_min=0,
                            path=path,
                            deadline=deadline
                        )
                        self._mark_nonce_pending(swap_hash)
                        self.log(f"[SEND] Swap отправлен: {swap_hash}", "INFO")
                        self.log(f"� https://bscscan.com/tx/{swap_hash}", "INFO")
                    except Exception as e:  # noqa: BLE001
                        self.log(f"[ERROR] Ошибка swapExactTokensForTokens через сервис: {e}", "ERROR")
                        raise
                else:
                    raise Exception("DexSwapService не инициализирован для USDT swap")
                self.log("⏳ Ожидание подтверждения транзакции...", "INFO")
                receipt = self.web3.eth.wait_for_transaction_receipt(swap_hash, timeout=300)
                if not (receipt and receipt.get('status') == 1):
                    raise Exception("Swap транзакция не подтверждена")
                gas_used = receipt['gasUsed']
                # gasPrice можно получить из receipt не всегда, fallback на текущий
                try:
                    gas_price_used = receipt.get('effectiveGasPrice') or self.get_gas_price_wei()
                except Exception:
                    gas_price_used = self.get_gas_price_wei()
                gas_cost_bnb = self.web3.from_wei(gas_used * gas_price_used, 'ether')
                self._mark_nonce_confirmed()
                self.log(f"[OK] Покупка успешно завершена!", "SALE")
                self.log(f"[SEARCH] Gas used: {gas_used}", "INFO")
                self.log(f"[MONEY] Стоимость газа: {gas_cost_bnb:.6f} BNB", "INFO")
                time.sleep(3)
                return {'success': True, 'tx_hash': swap_hash, 'token': selected_token}
            
        except Exception as e:
            self.log(f"[ERROR] Критическая ошибка при покупке: {str(e)}", "ERROR")
            self._mark_nonce_failed(str(e))
            return {
                'success': False,
                'error': str(e)
            }
            
    def _handle_purchase_completed(self, purchase_info: dict):
        """Обработка завершенной покупки"""
        buy_number = purchase_info['buy_number']
        tx_hash = purchase_info['tx_hash']
        amount_spent = purchase_info['amount_spent']
        tokens_bought = purchase_info['tokens_bought']
        
        # Обновляем статистику
        self.completed_buys_label.setText(str(buy_number))
        
        # Обновляем общие суммы (это можно было бы делать через накопление)
        current_spent = float(self.spent_amount_label.text() or "0")
        current_bought = float(self.bought_tokens_label.text() or "0")
        
        self.spent_amount_label.setText(f"{current_spent + amount_spent:.6f}")
        self.bought_tokens_label.setText(f"{current_bought + tokens_bought:.2f}")
        
        # Логируем результат
        self.log(f"[OK] Покупка #{buy_number} завершена. Tx: {tx_hash[:20]}...", "SUCCESS")
        
        # Обновляем балансы
        self.update_balances()
        
    @log_click("Сбросить статистику")
    def reset_stats(self, checked=False):
        """Сброс статистики"""
        self.completed_buys_label.setText("0")
        self.spent_amount_label.setText("0.0")
        self.bought_tokens_label.setText("0.0")
        self.log("🔄 Статистика сброшена", "INFO")
        
    @log_click("Очистить лог")
    def clear_log(self, checked=False):
        """Очистка лога"""
        self.log_text.clear()
        
    def log(self, message: str, level: str = 'INFO'):
        """Потокобезопасное логирование с выводом в главное окно."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Выводим в локальный лог вкладки
        try:
            from PyQt5.QtCore import QThread
            if QThread.currentThread() != self.thread():
                self.log_message_signal.emit(formatted_message)
            else:
                self._append_log_line(formatted_message)
        except Exception:
            self._append_log_line(formatted_message)
        
        # Также выводим в главное окно для синхронизации
        if hasattr(self, 'main_window') and self.main_window:
            try:
                self.main_window.add_log(message, level)
            except Exception:
                pass

    def _append_log_line(self, line: str):
        """Добавление строки в QTextEdit (только из GUI-потока)."""
        try:
            self.log_text.append(line)
            # Безопасная прокрутка без QTextCursor между потоками
            scrollbar = self.log_text.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            # Fallback на печать в консоль если UI недоступен
            print(f"[LOG] {line} (UI error: {e})")

    # ===== Nonce helper =====
    def _next_nonce(self) -> int:
        """Получение nonce: сначала пытаемся через NonceManager, иначе fallback на локальный счётчик.
        Возврат только значения nonce (для совместимости с текущим кодом). Ticket сохраняем при необходимости отдельно.
        """
        if not self.account or not self.web3:
            raise RuntimeError("Account/Web3 не инициализированы")
        # Пытаемся через NonceManager
        if getattr(self, 'nonce_manager', None):
            try:
                ticket = self.nonce_manager.reserve(self.account.address)
                # Сохраняем последний ticket для возможной маркировки/подтверждения
                self._last_nonce_ticket = ticket  # type: ignore[attr-defined]
                return ticket.nonce
            except Exception as e:  # noqa: BLE001
                self.log(f"[WARN] NonceManager reserve fallback: {e}", "WARNING")
        # Fallback старый локальный подход
        with self._nonce_lock:
            chain_nonce = self.web3.eth.get_transaction_count(self.account.address, 'pending')
            if self._local_nonce is None or chain_nonce > self._local_nonce:
                self._local_nonce = chain_nonce
            else:
                self._local_nonce += 1
            return self._local_nonce

    def _mark_nonce_pending(self, tx_hash: str):
        """Отмечает ticket как pending (одноразово)."""
        ticket: Optional[NonceTicket] = getattr(self, '_last_nonce_ticket', None)  # type: ignore[name-defined]
        if not ticket or not getattr(self, 'nonce_manager', None):
            return
        if ticket.status not in (NonceStatus.RESERVED,):  # уже обработан
            return
        try:
            self.nonce_manager.complete(ticket, tx_hash)
        except Exception as e:  # noqa: BLE001
            self.log(f"[WARN] Не удалось complete nonce ticket: {e}", "WARNING")

    def _mark_nonce_failed(self, reason: str):
        ticket: Optional[NonceTicket] = getattr(self, '_last_nonce_ticket', None)  # type: ignore[name-defined]
        if not ticket or not getattr(self, 'nonce_manager', None):
            return
        if ticket.status in (NonceStatus.CONFIRMED, NonceStatus.FAILED):
            return
        try:
            self.nonce_manager.fail(ticket, reason)
        except Exception as e:  # noqa: BLE001
            self.log(f"[WARN] Не удалось fail nonce ticket: {e}", "WARNING")
        finally:
            # очищаем ссылку чтобы не переиспользовать
            try:
                del self._last_nonce_ticket  # type: ignore[attr-defined]
            except Exception:
                pass

    def _mark_nonce_confirmed(self):
        ticket: Optional[NonceTicket] = getattr(self, '_last_nonce_ticket', None)  # type: ignore[name-defined]
        if not ticket or not getattr(self, 'nonce_manager', None):
            return
        if ticket.status in (NonceStatus.CONFIRMED, NonceStatus.FAILED):
            return
        try:
            self.nonce_manager.confirm(ticket)
        except Exception as e:  # noqa: BLE001
            self.log(f"[WARN] Не удалось confirm nonce ticket: {e}", "WARNING")
        finally:
            try:
                del self._last_nonce_ticket  # type: ignore[attr-defined]
            except Exception:
                pass

    def _reset_nonce_tracker(self):
        with self._nonce_lock:
            self._local_nonce = None

    # ===== Gas helpers =====
    def get_gas_price_wei(self) -> int:
        """Определяет gas price в wei.
        Приоритет:
        1) Пользовательский ввод (widget gas_price_input) если > 0
        2) GasManager (standard swap) если доступен
        3) Fallback 0.1 Gwei
        Лог включает источник.
        """
        user_gwei = None
        widget = getattr(self, 'gas_price_input', None)
        if widget is not None:
            try:
                if hasattr(widget, 'value'):
                    v = float(widget.value())
                    if v > 0:
                        user_gwei = v
                elif hasattr(widget, 'text'):
                    txt = widget.text().strip().replace(',', '.')
                    if txt:
                        v = float(txt)
                        if v > 0:
                            user_gwei = v
            except Exception:  # noqa: BLE001
                user_gwei = None

        if user_gwei is not None:
            wei = int(user_gwei * 1_000_000_000)
            self.log(f"[SETTINGS] Gas price: {user_gwei:.4f} Gwei (source=user)", "INFO")
            return wei

        # GasManager путь
        if hasattr(self, 'gas_manager') and getattr(self, 'gas_manager', None):
            try:
                from ...utils.gas_manager import GasPriority
                gas_wei = self.gas_manager.get_optimal_gas_price(GasPriority.STANDARD, operation_type='swap')
                gwei = self.web3.from_wei(gas_wei, 'gwei') if self.web3 else 0
                self.log(f"[SETTINGS] Gas price: {gwei:.4f} Gwei (source=manager)", "INFO")
                return gas_wei
            except Exception as e:  # noqa: BLE001
                self.log(f"[WARN] GasManager fallback: {e}", "WARNING")

        # Fallback 0.1 gwei
        fallback_gwei = 0.1
        wei = int(fallback_gwei * 1_000_000_000)
        self.log(f"[SETTINGS] Gas price: {fallback_gwei:.4f} Gwei (source=fallback)", "INFO")
        return wei
