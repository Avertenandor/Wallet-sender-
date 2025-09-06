"""
Вкладка автоматических покупок токенов
"""

import json
import time
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
import threading

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel,
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QCheckBox, QWidget,
    QFormLayout, QGridLayout, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QFont

from web3 import Web3
from eth_account import Account
from eth_typing import HexStr, HexAddress

from .base_tab import BaseTab
from ...utils.logger import get_logger
from ...core.nonce_manager import NonceManager

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
    # Известные пулы PLEX ONE
    'PLEX_USDT_POOL_1': Web3.to_checksum_address('0x41d9650faf3341cbf8947fd8063a1fc88dbf1889'),
    'PLEX_USDT_POOL_2': Web3.to_checksum_address('0xc7961e1e762d4b1975a3fcd07b8f70e34726c04e')
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
    
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        
        # Инициализация переменных
        self.web3 = None
        self.account = None
        self.is_buying = False
        self.buy_thread = None
        self.balances = {}
        self.nonce_manager = None  # Будет инициализирован после подключения Web3
        
        # Настройка таймера для обновления балансов
        self.balance_timer = QTimer()
        self.balance_timer.timeout.connect(self.update_balances)
        
        # Подключение сигналов
        self.balance_updated.connect(self._update_balance_display)
        self.purchase_completed.connect(self._handle_purchase_completed)
        
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
                self.log(f"🔗 Пробуем подключиться к {rpc_url}", "INFO")
                self.web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
                
                if self.web3.is_connected():
                    # Проверяем что можем получить блок
                    latest_block = self.web3.eth.block_number
                    self.log(f"✅ Подключен к BSC через {rpc_url} (блок: {latest_block})", "SUCCESS")
                    
                    # Инициализируем менеджеры
                    self.nonce_manager = NonceManager(self.web3)
                    self.log("✅ Менеджеры инициализированы", "SUCCESS")
                    try:
                        from ...utils.gas_manager import GasManager
                        from ...utils.token_safety import TokenSafetyChecker
                        from ...utils.async_manager import get_async_manager
                        
                        self.gas_manager = GasManager(self.web3)
                        self.safety_checker = TokenSafetyChecker(self.web3)
                        self.async_manager = get_async_manager(self.web3)
                        
                        self.log("✅ Менеджеры инициализированы", "SUCCESS")
                    except Exception as e:
                        self.log(f"⚠️ Ошибка инициализации менеджеров: {str(e)}", "WARNING")
                    
                    return
                else:
                    self.log(f"❌ Не удалось подключиться к {rpc_url}", "ERROR")
                    
            except Exception as e:
                self.log(f"❌ Ошибка подключения к {rpc_url}: {str(e)}", "ERROR")
                continue
        
        # Если ни один RPC не сработал
        self.log("❌ Не удалось подключиться ни к одному RPC endpoint", "ERROR")
        # Создаем fallback подключение
        try:
            self.web3 = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
            self.log("⚠️ Создано fallback подключение", "WARNING")
        except Exception as e:
            self.log(f"❌ Ошибка создания fallback подключения: {str(e)}", "ERROR")
            self.web3 = None
            
    def init_ui(self):
        """Инициализация интерфейса вкладки"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        title = QLabel("🛒 Автоматические покупки токенов")
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
        
        # Настройки газа
        gas_group = self.create_gas_settings_group()
        layout.addWidget(gas_group)
        
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
        
        self.connect_btn = QPushButton("🔗 Подключить кошелек")
        self.connect_btn.clicked.connect(self.connect_wallet)
        button_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("🔌 Отключить")
        self.disconnect_btn.clicked.connect(self.disconnect_wallet)
        self.disconnect_btn.setEnabled(False)
        button_layout.addWidget(self.disconnect_btn)
        
        # Кнопка диагностики баланса
        self.debug_balance_btn = QPushButton("🔍 Диагностика баланса")
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
        layout.addRow("Токен для покупки:", self.token_combo)
        
        # Поле для пользовательского токена
        self.custom_token_input = QLineEdit()
        self.custom_token_input.setPlaceholderText("Адрес контракта токена (0x...)")
        self.custom_token_input.setEnabled(False)
        layout.addRow("Адрес токена:", self.custom_token_input)
        
        # Валюта для покупки (чем покупаем)
        self.buy_with_combo = QComboBox()
        self.buy_with_combo.addItems(['BNB', 'USDT'])
        layout.addRow("Покупать за:", self.buy_with_combo)
        
        # Сумма для покупки
        self.buy_amount_input = QDoubleSpinBox()
        self.buy_amount_input.setRange(0.001, 10000)
        self.buy_amount_input.setDecimals(6)
        self.buy_amount_input.setValue(0.01)  # Снижено с 0.1 до 0.01 BNB для достаточности средств
        layout.addRow("Сумма на покупку:", self.buy_amount_input)
        
        # Интервал между покупками
        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 86400)  # от 1 секунды до 24 часов
        self.interval_input.setValue(60)  # 1 минута по умолчанию
        layout.addRow("Интервал (сек):", self.interval_input)
        
        # Максимальное количество покупок
        self.max_buys_input = QSpinBox()
        self.max_buys_input.setRange(1, 1000)
        self.max_buys_input.setValue(10)
        layout.addRow("Максимум покупок:", self.max_buys_input)
        
        # Slippage tolerance
        self.slippage_input = QDoubleSpinBox()
        self.slippage_input.setRange(0.1, 50.0)
        self.slippage_input.setDecimals(1)
        self.slippage_input.setValue(5.0)
        layout.addRow("Slippage (%):", self.slippage_input)
        
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
        
        self.start_btn = QPushButton("🛒 Начать покупки")
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
        clear_btn = QPushButton("🗑️ Очистить лог")
        clear_btn.clicked.connect(self.clear_log)
        layout.addWidget(clear_btn)
        
        group.setLayout(layout)
        return group
        
    def _on_token_changed(self, token: str):
        """Обработка изменения выбранного токена"""
        self.custom_token_input.setEnabled(token == "Другой токен")
        
    def connect_wallet(self):
        """Подключение кошелька"""
        wallet_data = self.wallet_input.toPlainText().strip()
        
        if not wallet_data:
            QMessageBox.warning(self, "Ошибка", "Введите приватный ключ или SEED фразу!")
            return
            
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
            
            self.log(f"✅ Кошелек подключен: {self.account.address}", "SUCCESS")
            
            # Обновляем балансы
            self.update_balances()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключить кошелек: {str(e)}")
            self.log(f"❌ Ошибка подключения кошелька: {str(e)}", "ERROR")
            
    def disconnect_wallet(self):
        """Отключение кошелька"""
        self.account = None
        
        # Останавливаем покупки если идут
        if self.is_buying:
            self.stop_auto_buy()
            
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
        
        self.log("🔌 Кошелек отключен", "INFO")
        
    def refresh_all_balances(self):
        """Обновляет все балансы токенов с детальным логированием"""
        self.log("🔄 Обновляем балансы всех токенов...", "INFO")
        
        if not self.account:
            self.log("❌ Кошелек не подключен", "ERROR")
            return
            
        # Проверяем и обновляем Web3 подключение
        if not self.web3 or not self.web3.is_connected():
            self.log("⚠️ Web3 не подключен, переподключаемся...", "WARNING")
            self._init_web3()
        
        # Обновляем BNB баланс
        try:
            checksum_address = Web3.to_checksum_address(self.account.address)
            bnb_balance = self.web3.eth.get_balance(checksum_address)
            bnb_formatted = self.web3.from_wei(bnb_balance, 'ether')
            self.bnb_balance_label.setText(f"{bnb_formatted:.6f}")
            self.log(f"💰 BNB баланс: {bnb_formatted:.6f}", "SUCCESS")
        except Exception as e:
            self.bnb_balance_label.setText("Ошибка")
            self.log(f"❌ Ошибка получения BNB баланса: {e}", "ERROR")
        
        # Обновляем PLEX ONE баланс
        try:
            plex_balance = self._get_token_balance(CONTRACTS['PLEX_ONE'])
            self.plex_balance_label.setText(f"{plex_balance:.6f}")
            if plex_balance > 0:
                self.log(f"💰 PLEX ONE баланс: {plex_balance:.6f}", "SUCCESS")
        except Exception as e:
            self.plex_balance_label.setText("Ошибка")
            self.log(f"❌ Ошибка получения PLEX ONE баланса: {e}", "ERROR")
        
        # Обновляем USDT баланс
        try:
            usdt_balance = self._get_token_balance(CONTRACTS['USDT'])
            self.usdt_balance_label.setText(f"{usdt_balance:.6f}")
            if usdt_balance > 0:
                self.log(f"💰 USDT баланс: {usdt_balance:.6f}", "SUCCESS")
        except Exception as e:
            self.usdt_balance_label.setText("Ошибка")
            self.log(f"❌ Ошибка получения USDT баланса: {e}", "ERROR")
        
        self.log("✅ Обновление балансов завершено", "SUCCESS")

    def debug_balance(self):
        """Диагностика баланса токенов"""
        self.log("🔍 === ДИАГНОСТИКА БАЛАНСА ===", "INFO")
        
        if not self.account:
            self.log("❌ Кошелек не подключен", "ERROR")
            return
            
        self.log(f"✅ Кошелек подключен: {self.account.address}", "SUCCESS")
        
        if not self.web3:
            self.log("❌ Web3 не подключен", "ERROR")
            return
            
        self.log("✅ Web3 подключен к BSC", "SUCCESS")
        
        # BNB баланс
        try:
            checksum_address = Web3.to_checksum_address(self.account.address)
            bnb_balance = self.web3.eth.get_balance(checksum_address)
            bnb_formatted = self.web3.from_wei(bnb_balance, 'ether')
            self.log(f"💰 BNB баланс: {bnb_formatted:.6f}", "SUCCESS")
        except Exception as e:
            self.log(f"❌ Ошибка получения BNB баланса: {e}", "ERROR")
        
        # PLEX ONE баланс
        try:
            self.log(f"🔍 Проверяем токен: PLEX ONE ({CONTRACTS['PLEX_ONE']})", "INFO")
            plex_checksum = Web3.to_checksum_address(CONTRACTS['PLEX_ONE'])
            contract_code = self.web3.eth.get_code(plex_checksum)
            if contract_code and contract_code != b'':
                plex_contract = self.web3.eth.contract(address=plex_checksum, abi=ERC20_ABI)
                plex_balance_raw = plex_contract.functions.balanceOf(checksum_address).call()
                plex_decimals = plex_contract.functions.decimals().call()
                plex_balance = plex_balance_raw / (10 ** plex_decimals)
                self.log(f"✅ Баланс PLEX ONE: {plex_balance:.6f}", "SUCCESS")
            else:
                self.log(f"❌ Контракт PLEX ONE не найден", "ERROR")
        except Exception as e:
            self.log(f"❌ Ошибка получения PLEX ONE баланса: {e}", "ERROR")
        
        # USDT баланс
        try:
            self.log(f"🔍 Проверяем токен: USDT ({CONTRACTS['USDT']})", "INFO")
            usdt_checksum = Web3.to_checksum_address(CONTRACTS['USDT'])
            contract_code = self.web3.eth.get_code(usdt_checksum)
            if contract_code and contract_code != b'':
                usdt_contract = self.web3.eth.contract(address=usdt_checksum, abi=ERC20_ABI)
                usdt_balance_raw = usdt_contract.functions.balanceOf(checksum_address).call()
                usdt_decimals = usdt_contract.functions.decimals().call()
                usdt_balance = usdt_balance_raw / (10 ** usdt_decimals)
                self.log(f"✅ Баланс USDT: {usdt_balance:.6f}", "SUCCESS")
            else:
                self.log(f"❌ Контракт USDT не найден", "ERROR")
        except Exception as e:
            self.log(f"❌ Ошибка получения USDT баланса: {e}", "ERROR")
        
        self.log("🔍 === КОНЕЦ ДИАГНОСТИКИ ===", "INFO")

    def _get_token_balance(self, token_address: str) -> float:
        """Получение баланса токена с полной проверкой"""
        try:
            if not self.account or not self.web3:
                self.log("❌ Кошелек или Web3 не подключен", "ERROR")
                return 0
            
            # Проверяем подключение к сети
            if not self.web3.is_connected():
                self.log("❌ Нет подключения к BSC сети", "ERROR")
                return 0
            
            # Проверяем адрес токена
            if not Web3.is_address(token_address):
                self.log(f"❌ Неверный адрес токена: {token_address}", "ERROR")
                return 0
            
            # Проверяем, что адрес токена валидный
            checksum_address = Web3.to_checksum_address(token_address)
            
            # Проверяем, что контракт существует
            try:
                code = self.web3.eth.get_code(checksum_address)
                if code == b'':
                    self.log(f"❌ Контракт не найден по адресу: {checksum_address}", "ERROR")
                    return 0
            except Exception as e:
                self.log(f"❌ Ошибка проверки контракта: {str(e)}", "ERROR")
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
                self.log(f"❌ Ошибка получения decimals: {str(e)}", "ERROR")
                decimals = 18  # Fallback на стандартные 18 decimals
            
            # Получаем баланс
            wallet_address = Web3.to_checksum_address(self.account.address)
            try:
                balance = token_contract.functions.balanceOf(wallet_address).call()
            except Exception as e:
                self.log(f"❌ Ошибка получения баланса: {str(e)}", "ERROR")
                return 0
            
            # Конвертируем в читаемый формат
            formatted_balance = balance / (10 ** decimals)
            
            # Логируем только если баланс больше 0 или есть ошибки
            if formatted_balance > 0:
                self.log(f"✅ Баланс {checksum_address[:10]}...: {formatted_balance:.6f}", "SUCCESS")
            
            return formatted_balance
            
        except Exception as e:
            self.log(f"❌ Критическая ошибка получения баланса токена: {str(e)}", "ERROR")
            return 0

    def update_balances(self):
        """Обновление балансов токенов с улучшенной обработкой ошибок"""
        if not self.account or not self.web3:
            self.log("⚠️ Кошелек или Web3 не подключен для обновления балансов", "WARNING")
            return
            
        try:
            address = self.account.address
            
            # Получаем баланс BNB с обработкой ошибок
            try:
                bnb_balance_wei = self.web3.eth.get_balance(address)
                bnb_balance = self.web3.from_wei(bnb_balance_wei, 'ether')
            except Exception as e:
                self.log(f"⚠️ Ошибка получения BNB баланса: {e}", "WARNING")
                bnb_balance = 0.0
            
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
                self.log(f"⚠️ Ошибка получения баланса PLEX: {str(e)}", "WARNING")
                
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
                self.log(f"⚠️ Ошибка получения баланса USDT: {str(e)}", "WARNING")
                
            # Сохраняем балансы
            self.balances = {
                'bnb': float(bnb_balance),
                'plex': float(plex_balance),
                'usdt': float(usdt_balance)
            }
            
            # Отправляем сигнал для обновления UI с обработкой ошибок
            try:
                self.balance_updated.emit(self.balances)
            except Exception as signal_error:
                self.log(f"⚠️ Ошибка отправки сигнала обновления балансов: {signal_error}", "WARNING")
            
        except Exception as e:
            self.log(f"❌ Ошибка обновления балансов: {str(e)}", "ERROR")
            
    def _update_balance_display(self, balances: dict):
        """Обновление отображения балансов"""
        self.bnb_balance_label.setText(f"{balances.get('bnb', 0):.6f}")
        self.plex_balance_label.setText(f"{balances.get('plex', 0):.2f}")
        self.usdt_balance_label.setText(f"{balances.get('usdt', 0):.2f}")
        
    def _toggle_auto_refresh(self, enabled: bool):
        """Переключение авто-обновления балансов"""
        if enabled and self.account:
            self.balance_timer.start(30000)  # 30 секунд
            self.log("✅ Авто-обновление балансов включено", "INFO")
        else:
            self.balance_timer.stop()
            self.log("🔄 Авто-обновление балансов отключено", "INFO")
            
    def start_auto_buy(self):
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
        
        # Запускаем поток покупок
        self.buy_thread = threading.Thread(target=self._buy_worker, daemon=True)
        self.buy_thread.start()
        
        self.log("🛒 Автоматические покупки запущены", "SUCCESS")
        
    def stop_auto_buy(self):
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
        max_buys = self.max_buys_input.value()
        interval = self.interval_input.value()
        
        while self.is_buying and completed_buys < max_buys:
            try:
                # Выполняем покупку
                result = self._execute_buy()
                
                if result['success']:
                    completed_buys += 1
                    self.purchase_completed.emit({
                        'buy_number': completed_buys,
                        'tx_hash': result.get('tx_hash', ''),
                        'amount_spent': result.get('amount_spent', 0),
                        'tokens_bought': result.get('tokens_bought', 0)
                    })
                    
                # Ждем интервал
                if self.is_buying and completed_buys < max_buys:
                    time.sleep(interval)
                    
            except Exception as e:
                error_msg = str(e)
                self.log(f"❌ Ошибка в процессе покупки: {error_msg}", "ERROR")
                
                # Не останавливаем весь процесс из-за одной ошибки
                self.log("⚠️ Продолжаем работу несмотря на ошибку", "WARNING")
                time.sleep(interval)
                
        # Покупки завершены
        if self.is_buying:
            self.is_buying = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.log(f"🏁 Автоматические покупки завершены. Выполнено: {completed_buys}/{max_buys}", "SUCCESS")
            
    def _retry_call(self, func, max_retries: int = 3, delay: float = 2.0):
        """Универсальная функция retry для вызовов"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    self.log(f"⚠️ Попытка {attempt + 1}/{max_retries} не удалась: {e}", "WARNING")
                    self.log(f"🔄 Повторная попытка через {delay} секунд...", "INFO")
                    time.sleep(delay * (attempt + 1))  # Экспоненциальная задержка
                    
        raise last_error

    def _check_known_pools(self, amount_in: int, buy_with: str = 'USDT') -> List[int]:
        """Проверяет известные пулы PLEX ONE (только существующие пулы)"""
        if buy_with == 'USDT':
            self.log("🔍 Проверяем известные пулы PLEX ONE - USDT...", "INFO")
            
            # Проверяем прямой путь USDT -> PLEX ONE (единственный существующий)
            try:
                pool1_path = [CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']]
                result1 = self._get_amounts_out_with_retry(amount_in, pool1_path)
                if result1 and result1[-1] > 0:
                    # Получаем decimals для правильного отображения
                    try:
                        plex_contract = self.web3.eth.contract(address=CONTRACTS['PLEX_ONE'], abi=ERC20_ABI)
                        plex_decimals = plex_contract.functions.decimals().call()
                        expected_plex = result1[-1] / (10 ** plex_decimals)
                        self.log(f"✅ Найден прямой пул USDT->PLEX! Ожидается: {expected_plex:.6f} PLEX ONE", "SUCCESS")
                    except:
                        self.log(f"✅ Найден прямой пул USDT->PLEX! Результат: {result1}", "SUCCESS")
                    return result1
            except Exception as e:
                self.log(f"⚠️ Ошибка проверки прямого пула USDT: {e}", "WARNING")
                self.log("❌ Прямой пул USDT->PLEX недоступен", "ERROR")
                
        elif buy_with == 'BNB':
            self.log("🔍 Проверяем известные пулы PLEX ONE - BNB...", "INFO")
            
            # Для BNB используем только существующий путь через USDT
            # WBNB -> USDT -> PLEX ONE (прямой пул WBNB->PLEX не существует)
            try:
                bnb_path = [CONTRACTS['WBNB'], CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']]
                result = self._get_amounts_out_with_retry(amount_in, bnb_path)
                if result and result[-1] > 0:
                    # Получаем decimals для правильного отображения
                    try:
                        plex_contract = self.web3.eth.contract(address=CONTRACTS['PLEX_ONE'], abi=ERC20_ABI)
                        plex_decimals = plex_contract.functions.decimals().call()
                        expected_plex = result[-1] / (10 ** plex_decimals)
                        self.log(f"✅ Найден рабочий путь BNB->USDT->PLEX! Ожидается: {expected_plex:.6f} PLEX ONE", "SUCCESS")
                    except:
                        self.log(f"✅ Найден рабочий путь BNB->USDT->PLEX! Результат: {result}", "SUCCESS")
                    return result
            except Exception as e:
                self.log(f"⚠️ Ошибка проверки пути BNB->USDT->PLEX: {e}", "WARNING")
                self.log("❌ Путь BNB->USDT->PLEX недоступен", "ERROR")
        
        return []

    def _get_amounts_out_with_retry(self, amount_in: int, path: List[str]) -> List[int]:
        """Получает ожидаемое количество токенов на выходе с retry"""
        def _get():
            try:
                path_checksum = [Web3.to_checksum_address(addr) for addr in path]
                router_contract = self.web3.eth.contract(
                    address=CONTRACTS['PANCAKE_ROUTER'],
                    abi=PANCAKE_ROUTER_ABI
                )
                result = router_contract.functions.getAmountsOut(amount_in, path_checksum).call()
                self.log(f"🔍 getAmountsOut результат для пути {path}: {result}", "INFO")
                return result
            except Exception as e:
                self.log(f"⚠️ Ошибка getAmountsOut для пути {path}: {e}", "WARNING")
                # Возвращаем пустой список вместо исключения
                return []
        
        try:
            return self._retry_call(_get, max_retries=2, delay=1.0)
        except Exception as e:
            self.log(f"⚠️ Все попытки getAmountsOut провалились: {e}", "WARNING")
            return []

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
                usdt_decimals = usdt_contract.functions.decimals().call()
                usdt_balance = usdt_balance_wei / (10 ** usdt_decimals)
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
            self.log(f"🎯 Начинаем покупку: Сумма {buy_amount}, Валюта оплаты: {buy_with}", "INFO")
            
            # Определяем токен для покупки
            selected_token = self.token_combo.currentText()
            self.log(f"🛒 Выбранный токен для покупки: {selected_token}", "INFO")
            
            if selected_token == 'PLEX ONE':
                token_address = CONTRACTS['PLEX_ONE']
                self.log(f"📋 Адрес PLEX ONE: {token_address}", "INFO")
            elif selected_token == 'USDT':
                token_address = CONTRACTS['USDT']
                self.log(f"📋 Адрес USDT: {token_address}", "INFO")
            else:
                # Пользовательский токен
                token_address = self.custom_token_input.text().strip()
                self.log(f"📋 Пользовательский адрес токена: {token_address}", "INFO")
                if not token_address or not Web3.is_address(token_address):
                    self.log("❌ Неверный адрес пользовательского токена", "ERROR")
                    return {'success': False, 'error': 'Неверный адрес токена'}
            
            # Проверяем что не покупаем тот же токен, которым платим
            if buy_with == 'USDT' and selected_token == 'USDT':
                self.log("❌ Нельзя покупать USDT за USDT", "ERROR")
                return {'success': False, 'error': 'Нельзя покупать тот же токен которым платите'}
            
            # Валидация параметров покупки
            validation = self._validate_buy_params(token_address, buy_amount, buy_with)
            if not validation['valid']:
                self.log(f"❌ Ошибка валидации: {validation['error']}", "ERROR")
                return {'success': False, 'error': validation['error']}
            
            # Проверяем ликвидность перед покупкой (улучшенная версия)
            self.log("🔍 Проверяем ликвидность пула...", "INFO")
            try:
                if buy_with == 'BNB':
                    amount_wei = self.web3.to_wei(buy_amount, 'ether')
                    
                    if token_address.lower() == CONTRACTS['PLEX_ONE'].lower():
                        # Для PLEX ONE используем специальную проверку известных пулов
                        amounts_out = self._check_known_pools(amount_wei, 'BNB')
                        if amounts_out:
                            # Для BNB всегда используем путь через USDT (прямой пул WBNB->PLEX не существует)
                            path = [CONTRACTS['WBNB'], CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']]
                            self.log("✅ Используем путь через USDT: BNB -> USDT -> PLEX ONE", "SUCCESS")
                        else:
                            self.log("❌ Не найдено рабочих пулов для PLEX ONE с BNB", "ERROR")
                            return {'success': False, 'error': 'Нет рабочих пулов для PLEX ONE с BNB'}
                    else:
                        # Для других токенов используем прямой путь
                        path = [CONTRACTS['WBNB'], Web3.to_checksum_address(token_address)]
                        amounts_out = self._get_amounts_out_with_retry(amount_wei, path)
                        
                else:  # USDT - используем умную проверку пулов
                    # Получаем правильные decimals для USDT
                    usdt_contract = self.web3.eth.contract(address=CONTRACTS['USDT'], abi=ERC20_ABI)
                    usdt_decimals = usdt_contract.functions.decimals().call()
                    amount_wei = int(buy_amount * (10 ** usdt_decimals))
                    
                    if token_address.lower() == CONTRACTS['PLEX_ONE'].lower():
                        # Для PLEX ONE используем специальную проверку известных пулов
                        amounts_out = self._check_known_pools(amount_wei, 'USDT')
                        if amounts_out:
                            # Для USDT используем прямой путь (пул USDT->PLEX существует)
                            path = [CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']]
                            self.log("✅ Используем прямой путь: USDT -> PLEX ONE", "SUCCESS")
                        else:
                            self.log("❌ Не найдено рабочих пулов для PLEX ONE с USDT", "ERROR")
                            return {'success': False, 'error': 'Нет рабочих пулов для PLEX ONE с USDT'}
                    else:
                        # Для других токенов используем прямой путь
                        path = [CONTRACTS['USDT'], Web3.to_checksum_address(token_address)]
                        amounts_out = self._get_amounts_out_with_retry(amount_wei, path)
                
                if not amounts_out or amounts_out[-1] == 0:
                    self.log("❌ Нет ликвидности для выбранного пути", "ERROR")
                    return {'success': False, 'error': 'Нет ликвидности для обмена'}
                else:
                    # Получаем decimals для правильного расчета
                    try:
                        token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
                        decimals = token_contract.functions.decimals().call()
                        expected_tokens = amounts_out[-1] / (10 ** decimals)
                        self.log(f"🔍 Ожидается получить: {expected_tokens:.6f} {selected_token}", "INFO")
                    except Exception as e:
                        self.log(f"⚠️ Ошибка получения decimals: {e}", "WARNING")
                        # Используем стандартные decimals
                        expected_tokens = amounts_out[-1] / (10 ** 9) if selected_token == 'PLEX ONE' else amounts_out[-1] / (10 ** 18)
                        self.log(f"🔍 Ожидается получить (приблизительно): {expected_tokens:.6f} {selected_token}", "INFO")
                
            except Exception as e:
                self.log(f"⚠️ Ошибка проверки ликвидности: {e}", "WARNING")
                self.log("⚠️ Продолжаем покупку без проверки ликвидности", "WARNING")
            
            self.log(f"🛒 Выполняется реальная покупка {selected_token} за {buy_with} через PancakeSwap...", "INFO")
            
            # Создаем контракт PancakeSwap Router
            router_address = CONTRACTS['PANCAKE_ROUTER']
            self.log(f"📋 PancakeSwap Router: {router_address}", "INFO")
            
            # Параметры транзакции
            deadline = int(time.time()) + 300  # 5 минут
            
            if buy_with == 'BNB':
                self.log("💰 Режим покупки: BNB -> Token (swapExactETHForTokens)", "INFO")
                # Покупка за BNB (ETH -> Token)
                router_abi = [
                    {
                        "inputs": [
                            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                            {"internalType": "address[]", "name": "path", "type": "address[]"},
                            {"internalType": "address", "name": "to", "type": "address"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                        ],
                        "name": "swapExactETHForTokens",
                        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                        "stateMutability": "payable",
                        "type": "function"
                    }
                ]
                
                router_contract = self.web3.eth.contract(
                    address=router_address,
                    abi=router_abi
                )
                
                # Создаем путь обмена: BNB -> Token
                # Для PLEX ONE используем путь через USDT (прямой пул WBNB->PLEX не существует)
                if token_address.lower() == CONTRACTS['PLEX_ONE'].lower():
                    path = [
                        CONTRACTS['WBNB'],  # WBNB
                        CONTRACTS['USDT'],  # USDT
                        CONTRACTS['PLEX_ONE']  # PLEX ONE
                    ]
                    self.log(f"🔄 Путь обмена: WBNB -> USDT -> PLEX ONE", "INFO")
                else:
                    path = [
                        CONTRACTS['WBNB'],  # WBNB
                        Web3.to_checksum_address(token_address)
                    ]
                    self.log(f"🔄 Путь обмена: WBNB -> {selected_token}", "INFO")
                
                amount_wei = self.web3.to_wei(buy_amount, 'ether')
                self.log(f"💰 Сумма в wei: {amount_wei} ({buy_amount} BNB)", "INFO")
                
                # Рассчитываем минимальное количество токенов с учетом проскальзывания (1% как в Частокол)
                expected_amount = amounts_out[-1] if amounts_out else 0
                slippage = 0.01  # 1% проскальзывание (как в Частокол)
                min_amount_out = int(expected_amount * (1 - slippage))
                
                # Получаем decimals для правильного отображения
                try:
                    token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
                    decimals = token_contract.functions.decimals().call()
                    self.log(f"🔍 Ожидается получить: {expected_amount / (10**decimals):.6f} {selected_token}", "INFO")
                    self.log(f"🔍 Минимум с проскальзыванием: {min_amount_out / (10**decimals):.6f} {selected_token}", "INFO")
                except:
                    self.log(f"🔍 Ожидается получить: {expected_amount / (10**9):.6f} {selected_token}", "INFO")
                    self.log(f"🔍 Минимум с проскальзыванием: {min_amount_out / (10**9):.6f} {selected_token}", "INFO")
                
                # Создаем транзакцию (nonce будет установлен в _send_transaction_with_nonce_manager)
                transaction = router_contract.functions.swapExactETHForTokens(
                    min_amount_out,  # amountOutMin с защитой от проскальзывания
                    path,
                    self.account.address,
                    deadline
                ).build_transaction({
                    'from': self.account.address,
                    'value': amount_wei,
                    'gas': max(self.get_gas_limit(), 200000),  # Увеличиваем лимит газа
                    'gasPrice': self.get_gas_price_wei(),
                    'nonce': 0  # Будет заменен в _send_transaction_with_nonce_manager
                })
                
                # Оценка газа (как в Частокол)
                try:
                    self.log("🔍 Оценка газа для swap транзакции...", "INFO")
                    estimated_gas = self.web3.eth.estimate_gas(transaction)
                    self.log(f"🔍 Оценка газа: {estimated_gas}", "INFO")
                    # Добавляем 20% запас (как в Частокол)
                    transaction['gas'] = int(estimated_gas * 1.2)
                    self.log(f"🔍 Установлен лимит газа: {transaction['gas']} (+20% запас)", "INFO")
                except Exception as e:
                    self.log(f"⚠️ Не удалось оценить газ: {e}. Используем текущее значение.", "WARNING")
                
            else:  # buy_with == 'USDT'
                self.log("💵 Режим покупки: USDT -> Token (approve + swapExactTokensForTokens)", "INFO")
                # Покупка за USDT (Token -> Token)
                
                # Сначала нужно сделать approve для USDT
                usdt_address = CONTRACTS['USDT']
                self.log(f"📋 USDT адрес: {usdt_address}", "INFO")
                
                # Используем полный ERC20 ABI для получения decimals
                usdt_contract = self.web3.eth.contract(address=usdt_address, abi=ERC20_ABI)
                # Получаем правильные decimals для USDT
                usdt_decimals = usdt_contract.functions.decimals().call()
                amount_in_units = int(buy_amount * (10 ** usdt_decimals))
                
                # Approve транзакция (nonce будет установлен в _send_transaction_with_nonce_manager)
                self.log("📝 Делаем approve для USDT...", "INFO")
                approve_tx = usdt_contract.functions.approve(
                    router_address,
                    amount_in_units
                ).build_transaction({
                    'from': self.account.address,
                    'gas': self.get_gas_limit(),  # Используем настройки из UI
                    'gasPrice': self.get_gas_price_wei(),
                    'nonce': 0  # Будет заменен в _send_transaction_with_nonce_manager
                })
                
                # Отправляем approve транзакцию с использованием NonceManager
                self.log("📤 Отправка approve транзакции...", "INFO")
                approve_hash = self._send_transaction_with_nonce_manager(approve_tx)
                
                if not approve_hash:
                    raise Exception("Не удалось отправить approve транзакцию")
                    
                self.log(f"📤 Approve транзакция отправлена: {approve_hash.hex()}", "INFO")
                self.log(f"🔗 Ссылка: https://bscscan.com/tx/{approve_hash.hex()}", "INFO")
                
                # Ждем подтверждения с таймаутом
                self.log("⏳ Ожидание подтверждения approve...", "INFO")
                approve_receipt = self.web3.eth.wait_for_transaction_receipt(approve_hash, timeout=180)
                
                if approve_receipt and approve_receipt['status'] == 1:
                    self.log(f"✅ Approve успешно завершен. Gas used: {approve_receipt['gasUsed']}", "SUCCESS")
                else:
                    raise Exception("Approve транзакция провалилась")
                
                # Небольшая пауза для обновления nonce в сети
                time.sleep(2)
                
                # Получаем актуальный nonce после approve (должен быть +1)
                current_nonce = self.web3.eth.get_transaction_count(self.account.address)
                self.log(f"📊 Актуальный nonce после approve: {current_nonce}", "INFO")
                
                # Дополнительная проверка - ждем пока nonce обновится
                max_wait = 10  # максимум 10 секунд
                wait_time = 0
                while wait_time < max_wait:
                    try:
                        latest_nonce = self.web3.eth.get_transaction_count(self.account.address)
                        if latest_nonce > current_nonce:
                            current_nonce = latest_nonce
                            self.log(f"📊 Обновленный nonce: {current_nonce}", "INFO")
                            break
                        time.sleep(1)
                        wait_time += 1
                    except Exception as e:
                        self.log(f"⚠️ Ошибка получения nonce: {e}", "WARNING")
                        break
                
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
                
                # Используем уже найденный путь из проверки ликвидности
                # path уже определен в блоке проверки ликвидности выше
                if token_address.lower() == CONTRACTS['PLEX_ONE'].lower():
                    if buy_with == 'BNB':
                        # Для BNB всегда через USDT (прямой пул WBNB->PLEX не существует)
                        self.log(f"🔄 Путь обмена: BNB -> USDT -> PLEX ONE (через USDT)", "INFO")
                    else:  # USDT
                        # Для USDT прямой путь (пул USDT->PLEX существует)
                        self.log(f"🔄 Путь обмена: USDT -> PLEX ONE (прямой)", "INFO")
                else:
                    if buy_with == 'BNB':
                        self.log(f"🔄 Путь обмена: BNB -> {selected_token}", "INFO")
                    else:
                        self.log(f"🔄 Путь обмена: USDT -> {selected_token}", "INFO")
                
                # Финальная проверка nonce перед созданием транзакции
                final_nonce = self.web3.eth.get_transaction_count(self.account.address)
                if final_nonce > current_nonce:
                    current_nonce = final_nonce
                    self.log(f"📊 Финальный nonce перед транзакцией: {current_nonce}", "INFO")
                
                # Рассчитываем минимальное количество токенов с учетом проскальзывания (1% как в Частокол)
                expected_amount = amounts_out[-1] if amounts_out else 0
                slippage = 0.01  # 1% проскальзывание (как в Частокол)
                min_amount_out = int(expected_amount * (1 - slippage))
                
                # Получаем decimals для правильного отображения
                try:
                    token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
                    decimals = token_contract.functions.decimals().call()
                    self.log(f"🔍 Ожидается получить: {expected_amount / (10**decimals):.6f} {selected_token}", "INFO")
                    self.log(f"🔍 Минимум с проскальзыванием {slippage*100}%: {min_amount_out / (10**decimals):.6f} {selected_token}", "INFO")
                except:
                    self.log(f"🔍 Ожидается получить: {expected_amount / (10**9):.6f} {selected_token}", "INFO")
                    self.log(f"🔍 Минимум с проскальзыванием {slippage*100}%: {min_amount_out / (10**9):.6f} {selected_token}", "INFO")
                
                # Создаем транзакцию (nonce будет установлен в _send_transaction_with_nonce_manager)
                transaction = router_contract.functions.swapExactTokensForTokens(
                    amount_in_units,
                    min_amount_out,  # amountOutMin с защитой от проскальзывания
                    path,
                    self.account.address,
                    deadline
                ).build_transaction({
                    'from': self.account.address,
                    'gas': max(self.get_gas_limit(), 200000),  # Увеличиваем лимит газа
                    'gasPrice': self.get_gas_price_wei(),
                    'nonce': 0  # Будет заменен в _send_transaction_with_nonce_manager
                })
                
                # Оценка газа (как в Частокол)
                try:
                    self.log("🔍 Оценка газа для swap транзакции...", "INFO")
                    estimated_gas = self.web3.eth.estimate_gas(transaction)
                    self.log(f"🔍 Оценка газа: {estimated_gas}", "INFO")
                    # Добавляем 20% запас (как в Частокол)
                    transaction['gas'] = int(estimated_gas * 1.2)
                    self.log(f"🔍 Установлен лимит газа: {transaction['gas']} (+20% запас)", "INFO")
                except Exception as e:
                    self.log(f"⚠️ Не удалось оценить газ: {e}. Используем текущее значение.", "WARNING")
            
            # Подписываем и отправляем транзакцию с retry для nonce
            self.log(f"📤 Отправка swap транзакции: {buy_amount} {buy_with} -> {selected_token}", "INFO")
            self.log(f"🔍 Gas limit: {transaction['gas']}, Gas price: {transaction['gasPrice']}", "INFO")
            self.log(f"🔍 Nonce: {transaction['nonce']}", "INFO")
            self.log(f"🔍 Deadline: {deadline} (через {deadline - int(time.time())} секунд)", "INFO")
            self.log(f"🔍 Путь обмена: {' -> '.join([self._get_token_symbol(addr) for addr in path])}", "INFO")
            
            # Отправка транзакции с использованием NonceManager
            tx_hash = self._send_transaction_with_nonce_manager(transaction)
            
            if not tx_hash:
                raise Exception("Не удалось отправить swap транзакцию")
                
            self.log(f"📤 Swap транзакция отправлена: {tx_hash.hex()}", "INFO")
            self.log(f"🔗 Ссылка: https://bscscan.com/tx/{tx_hash.hex()}", "INFO")
            
            # Ждем подтверждения
            self.log("⏳ Ожидание подтверждения транзакции...", "INFO")
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if tx_receipt and tx_receipt['status'] == 1:
                gas_used = tx_receipt['gasUsed']
                gas_cost_bnb = self.web3.from_wei(gas_used * transaction['gasPrice'], 'ether')
                
                self.log(f"✅ Покупка успешно завершена!", "SALE")
                self.log(f"🔍 Gas used: {gas_used}", "INFO")
                self.log(f"💰 Стоимость газа: {gas_cost_bnb:.6f} BNB", "INFO")
                
                # Проверяем новый баланс с задержкой
                time.sleep(3)
                token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
                new_balance_wei = token_contract.functions.balanceOf(self.account.address).call()
                decimals = token_contract.functions.decimals().call()
                new_balance = new_balance_wei / (10 ** decimals)
                self.log(f"💰 Новый баланс {selected_token}: {new_balance:.6f}", "PROFIT")
                
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'amount_spent': buy_amount,
                    'gas_used': gas_used,
                    'tokens_bought': new_balance
                }
            else:
                self.log("❌ Swap транзакция провалилась", "ERROR")
                if tx_receipt:
                    self.log(f"❌ Receipt status: {tx_receipt.get('status')}", "ERROR")
                    self.log(f"❌ Gas used: {tx_receipt.get('gasUsed', 'N/A')}", "ERROR")
                    
                    # Анализируем причину провала
                    gas_used = tx_receipt.get('gasUsed', 0)
                    gas_limit = transaction.get('gas', 0)
                    
                    if gas_used >= gas_limit * 0.95:  # Использовано более 95% газа
                        self.log("⚠️ Возможная причина: Недостаточно газа (Out of Gas)", "WARNING")
                        return {
                            'success': False,
                            'error': 'Недостаточно газа. Попробуйте увеличить лимит газа.'
                        }
                    else:
                        self.log("⚠️ Возможная причина: Ошибка в контракте или проскальзывание", "WARNING")
                        return {
                            'success': False,
                            'error': 'Транзакция отклонена контрактом. Возможно, изменился курс или недостаточная ликвидность.'
                        }
                else:
                    return {
                        'success': False,
                        'error': 'Не удалось получить receipt транзакции'
                    }
            
        except Exception as e:
            error_msg = str(e)
            self.log(f"❌ Критическая ошибка при покупке: {error_msg}", "ERROR")
            
            # Специальная обработка для разных типов ошибок
            if "nonce too low" in error_msg:
                self.log("⚠️ Ошибка nonce - возможно нужно подождать", "WARNING")
            elif "insufficient funds" in error_msg.lower():
                self.log("⚠️ Недостаточно средств для покупки", "WARNING")
            elif "execution reverted" in error_msg:
                self.log("⚠️ Транзакция отклонена контрактом", "WARNING")
            elif "gas" in error_msg.lower():
                self.log("⚠️ Проблема с газом", "WARNING")
            else:
                self.log(f"⚠️ Неизвестная ошибка: {error_msg}", "WARNING")
            
            return {
                'success': False,
                'error': error_msg
            }
            
    def _handle_purchase_completed(self, purchase_info: dict):
        """Обработка завершенной покупки с обработкой ошибок"""
        try:
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
            self.log(f"✅ Покупка #{buy_number} завершена. Tx: {tx_hash[:20]}...", "SUCCESS")
            
            # Обновляем балансы с обработкой ошибок
            try:
                self.update_balances()  # Используем правильную функцию
                self.refresh_all_balances()  # И обновляем UI
            except Exception as balance_error:
                self.log(f"⚠️ Ошибка обновления балансов: {balance_error}", "WARNING")
                
        except Exception as e:
            self.log(f"❌ Ошибка обработки завершенной покупки: {e}", "ERROR")
        
    def reset_stats(self):
        """Сброс статистики"""
        self.completed_buys_label.setText("0")
        self.spent_amount_label.setText("0.0")
        self.bought_tokens_label.setText("0.0")
        self.log("🔄 Статистика сброшена", "INFO")
        
    def clear_log(self):
        """Очистка лога"""
        self.log_text.clear()
        
    def log(self, message: str, level: str = 'INFO'):
        """Логирование сообщения с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Добавляем в лог вкладки
        self.log_text.append(formatted_message)
        
        # Прокручиваем в конец
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)
        
        # Отправляем в общий лог через BaseTab
        super().log(message, level)
        
    def _get_token_symbol(self, address: str) -> str:
        """Получает символ токена по адресу"""
        try:
            if address.lower() == CONTRACTS['WBNB'].lower():
                return 'WBNB'
            elif address.lower() == CONTRACTS['USDT'].lower():
                return 'USDT'
            elif address.lower() == CONTRACTS['PLEX_ONE'].lower():
                return 'PLEX ONE'
            else:
                # Пытаемся получить символ из контракта
                try:
                    token_contract = self.web3.eth.contract(address=address, abi=ERC20_ABI)
                    symbol = token_contract.functions.symbol().call()
                    return symbol
                except:
                    return address[:8] + '...'
        except:
            return address[:8] + '...'
    
    def _send_transaction_with_nonce_manager(self, transaction: dict) -> Optional[bytes]:
        """Отправка транзакции с использованием NonceManager"""
        if not self.nonce_manager:
            self.log("⚠️ NonceManager не инициализирован, используем стандартный метод", "WARNING")
            return self._send_transaction_standard(transaction)
        
        try:
            # Резервируем nonce
            ticket = self.nonce_manager.reserve(self.account.address)
            transaction['nonce'] = ticket.nonce
            
            self.log(f"🔢 Зарезервирован nonce: {ticket.nonce}", "INFO")
            
            # Отправляем транзакцию
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Подтверждаем использование nonce
            self.nonce_manager.complete(ticket, tx_hash.hex())
            
            self.log(f"✅ Транзакция отправлена с nonce {ticket.nonce}", "SUCCESS")
            return tx_hash
            
        except Exception as e:
            error_str = str(e).lower()
            self.log(f"❌ Ошибка отправки транзакции: {e}", "ERROR")
            
            # Обработка различных типов ошибок
            if "nonce too low" in error_str:
                self.log("⚠️ Nonce слишком низкий, обновляем состояние", "WARNING")
                if 'ticket' in locals():
                    self.nonce_manager.fail(ticket, str(e))
                # Пробуем еще раз с обновленным nonce
                return self._send_transaction_standard(transaction)
                
            elif "nonce too high" in error_str:
                self.log("⚠️ Nonce слишком высокий, сбрасываем состояние", "WARNING")
                if 'ticket' in locals():
                    self.nonce_manager.fail(ticket, str(e))
                # Сбрасываем состояние nonce
                self.nonce_manager.reset_address(self.account.address)
                return self._send_transaction_standard(transaction)
                
            elif "replacement transaction underpriced" in error_str:
                self.log("⚠️ Нужно увеличить gas price", "WARNING")
                transaction['gasPrice'] = int(transaction['gasPrice'] * 1.1)
                return self._send_transaction_with_nonce_manager(transaction)
                
            else:
                if 'ticket' in locals():
                    self.nonce_manager.fail(ticket, str(e))
                raise e
    
    def _send_transaction_standard(self, transaction: dict) -> Optional[bytes]:
        """Стандартная отправка транзакции с retry для nonce ошибок"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Получаем актуальный nonce
                transaction['nonce'] = self.web3.eth.get_transaction_count(self.account.address)
                
                signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
                tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
                
                self.log(f"✅ Транзакция отправлена с nonce {transaction['nonce']}", "SUCCESS")
                return tx_hash
                
            except Exception as e:
                error_str = str(e).lower()
                
                if ("nonce too low" in error_str or "nonce too high" in error_str) and attempt < max_retries - 1:
                    self.log(f"⚠️ Nonce ошибка, попытка {attempt + 1}/{max_retries}: {e}", "WARNING")
                    time.sleep(1)
                    continue
                else:
                    raise e
        
        return None
