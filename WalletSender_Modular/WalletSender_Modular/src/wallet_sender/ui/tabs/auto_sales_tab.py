"""Auto Sales Tab - автоматическая продажа токенов через PancakeSwap"""

import json
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from ...core.nonce_manager import get_nonce_manager, NonceTicket, NonceStatus

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit, QCheckBox,
    QMessageBox, QSplitter, QFormLayout
)
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QColor

from web3 import Web3
from .base_tab import BaseTab
from ...utils.gas_manager import GasManager

# Условный импорт сервисов
try:
    from ...services.dex_swap_service import DexSwapService
except ImportError:
    DexSwapService = None

# Условный импорт eth_account
try:
    from eth_account import Account
except ImportError:
    Account = None

# ABI для ERC20 токенов (минимальный, но с allowance)
ERC20_ABI = json.loads("""
[
  {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},
  {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
  {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
  {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
  {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
  {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
  {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}
]
""")

# Минимальный ABI для PancakeSwap Router
PANCAKE_ROUTER_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}]')


class AutoSalesTab(BaseTab):
    """Вкладка автоматических продаж токенов через PancakeSwap"""
    
    # Сигналы
    balance_updated = pyqtSignal(dict)
    sale_completed = pyqtSignal(dict)
    
    def __init__(self, main_window: Any, parent: Optional[Any] = None):
        # Инициализация переменных
        self.web3: Optional[Web3] = None
        self.account: Optional[Any] = None
        self.monitoring_thread: Optional[threading.Thread] = None
        self.is_monitoring: bool = False
        self.stop_monitoring: threading.Event = threading.Event()
        self.monitored_tokens: Dict[str, Dict[str, Any]] = {}
        self.sales_history: List[Dict[str, Any]] = []
        try:
            self.nonce_manager = get_nonce_manager(getattr(self, 'web3', None))
        except Exception:  # noqa: BLE001
            self.nonce_manager = None
        self._last_nonce_ticket: Optional[NonceTicket] = None
        
        # Адреса контрактов (в checksum формате)
        self.PANCAKE_ROUTER = Web3.to_checksum_address("0x10ED43C718714eb63d5aA57B78B54704E256024E")
        self.WBNB = Web3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
        self.USDT = Web3.to_checksum_address("0x55d398326f99059ff775485246999027b3197955")
        self.PLEX_ONE = Web3.to_checksum_address("0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1")
        
        # Инициализация менеджеров
        self.gas_manager = None
        self.safety_checker = None
        self.async_manager = None
        
        super().__init__(main_window, parent)
        
        # Инициализация Web3
        self._init_web3()
        
    def log(self, message: str, level: str = "INFO"):
        """Простая функция логирования для совместимости"""
        try:
            if hasattr(self, 'main_window') and self.main_window:
                # Пытаемся логировать через главное окно
                if hasattr(self.main_window, 'add_log'):
                    self.main_window.add_log(message, level)
                    return
        except Exception:
            pass
        # Fallback на стандартный вывод
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] AutoSalesTab: {message}")
        
    def _init_web3(self):
        """Инициализация Web3 подключения"""
        try:
            # Всегда создаем собственный Web3 провайдер для надежности
            rpc_urls = [
                'https://bsc-dataseed.binance.org/',
                'https://bsc-dataseed1.binance.org/',
                'https://bsc-dataseed2.binance.org/',
                'https://bsc-dataseed3.binance.org/',
                'https://bsc-dataseed4.binance.org/',
                'https://bsc-dataseed1.defibit.io/',
                'https://bsc-dataseed1.ninicoin.io/'
            ]
            
            self.web3 = None
            for rpc_url in rpc_urls:
                try:
                    self.web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
                    if self.web3.is_connected():
                        # Тестируем подключение получением последнего блока
                        latest_block = self.web3.eth.block_number
                        self.log(f"[OK] Подключен к BSC через {rpc_url} (блок: {latest_block})", "SUCCESS")
                        
                        # Инициализируем менеджеры
                        self.gas_manager = GasManager(self.web3)
                        self.safety_checker = None  # TokenSafetyChecker отключен
                        self.async_manager = None  # get_async_manager отключен
                        
                        self.log("[OK] Менеджеры инициализированы", "SUCCESS")
                        break
                except Exception as e:
                    self.log(f"[ERROR] Ошибка подключения к {rpc_url}: {str(e)}", "ERROR")
                    continue
            
            if not self.web3 or not self.web3.is_connected():
                self.log("[ERROR] Не удалось подключиться ни к одному RPC", "ERROR")
                # Создаем fallback подключение
                self.web3 = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
                
        except Exception as e:
            self.log(f"[ERROR] Ошибка инициализации Web3: {str(e)}", "ERROR")
            # Создаем базовое подключение
            self.web3 = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        title_label = QLabel("[MONEY] Автоматические продажи токенов")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # Группа подключения кошелька
        wallet_group = self._create_wallet_group()
        layout.addWidget(wallet_group)
        
        # Разделитель для настроек и мониторинга
        splitter = QSplitter(Qt.Horizontal)
        
        # Левая панель - настройки продажи
        left_panel = QGroupBox("Настройки автопродажи")
        left_layout = QVBoxLayout(left_panel)
        
        # Выбор токена для продажи
        token_layout = QFormLayout()
        
        self.token_combo = QComboBox()
        self.token_combo.addItems(['PLEX ONE', 'Другой токен'])
        self.token_combo.currentTextChanged.connect(self._on_token_changed)
        token_layout.addRow("Токен для продажи:", self.token_combo)
        
        self.custom_token_input = QLineEdit()
        self.custom_token_input.setPlaceholderText("Адрес токена (0x...)")
        self.custom_token_input.setVisible(False)
        self.custom_token_input.textChanged.connect(self._update_current_balance)
        token_layout.addRow("Адрес токена:", self.custom_token_input)
        
        # Текущий баланс выбранного токена
        self.current_balance_label = QLabel("0.0000")
        self.current_balance_label.setStyleSheet("font-weight: bold; color: #2E8B57;")
        token_layout.addRow("Текущий баланс:", self.current_balance_label)
        
        # Кнопка обновления балансов
        self.refresh_balances_btn = QPushButton("🔄 Обновить все балансы")
        self.refresh_balances_btn.clicked.connect(self.refresh_all_balances)
        self.refresh_balances_btn.setToolTip("Обновить балансы всех основных токенов")
        token_layout.addRow("", self.refresh_balances_btn)
        
        # Целевая валюта
        self.target_combo = QComboBox()
        self.target_combo.addItems(['BNB', 'USDT'])
        token_layout.addRow("Продавать в:", self.target_combo)
        
        # Порог для продажи
        self.threshold_input = QDoubleSpinBox()
        self.threshold_input.setRange(0.00000001, 1000000000)
        self.threshold_input.setDecimals(8)
        self.threshold_input.setValue(100.0)
        self.threshold_input.setSuffix(" токенов")
        token_layout.addRow("Порог для продажи:", self.threshold_input)
        
        # Режим продажи - процент или количество
        self.sell_mode_combo = QComboBox()
        self.sell_mode_combo.addItems(['Процент от баланса', 'Фиксированное количество'])
        self.sell_mode_combo.currentTextChanged.connect(self._on_sell_mode_changed)
        token_layout.addRow("Режим продажи:", self.sell_mode_combo)
        
        # Процент от баланса для продажи
        self.sell_percentage = QSpinBox()
        self.sell_percentage.setRange(1, 100)
        self.sell_percentage.setValue(100)
        self.sell_percentage.setSuffix(" %")
        token_layout.addRow("Продавать %:", self.sell_percentage)
        
        # Фиксированное количество для продажи
        self.sell_quantity = QDoubleSpinBox()
        self.sell_quantity.setRange(0.00000001, 1000000000)
        self.sell_quantity.setDecimals(8)
        self.sell_quantity.setValue(100.0)
        self.sell_quantity.setSuffix(" токенов")
        self.sell_quantity.setVisible(False)
        token_layout.addRow("Количество токенов:", self.sell_quantity)
        
        # Минимальная цена
        self.min_price_input = QDoubleSpinBox()
        self.min_price_input.setRange(0, 1000000)
        self.min_price_input.setDecimals(8)
        self.min_price_input.setValue(0)
        self.min_price_input.setPrefix("$")
        token_layout.addRow("Мин. цена (0=любая):", self.min_price_input)
        
        # Slippage
        self.slippage_input = QSpinBox()
        self.slippage_input.setRange(1, 50)
        self.slippage_input.setValue(12)
        self.slippage_input.setSuffix(" %")
        token_layout.addRow("Slippage:", self.slippage_input)
        
        # Цена газа (gwei)
        self.gas_price_input = QDoubleSpinBox()
        self.gas_price_input.setRange(0.01, 100.0)
        self.gas_price_input.setDecimals(2)
        self.gas_price_input.setValue(0.1)  # По умолчанию 0.1 gwei
        self.gas_price_input.setSuffix(" gwei")
        self.gas_price_input.setToolTip("Цена газа за транзакцию (0.1 gwei = экономично)")
        token_layout.addRow("Цена газа:", self.gas_price_input)
        
        # Интервал проверки
        self.check_interval = QSpinBox()
        self.check_interval.setRange(5, 3600)
        self.check_interval.setValue(30)
        self.check_interval.setSuffix(" сек")
        token_layout.addRow("Интервал проверки:", self.check_interval)
        
        # Циклические продажи
        self.cyclic_sales_checkbox = QCheckBox("Циклические продажи")
        self.cyclic_sales_checkbox.setToolTip("Продавать по интервалу независимо от порога")
        self.cyclic_sales_checkbox.setChecked(False)
        token_layout.addRow("", self.cyclic_sales_checkbox)
        
        left_layout.addLayout(token_layout)
        
        # Кнопки управления
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("[PLAY] Начать мониторинг")
        self.start_btn.clicked.connect(self.start_monitoring)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Остановить")
        self.stop_btn.clicked.connect(self.stop_monitoring_func)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        self.test_sell_btn = QPushButton("[TEST] Тест продажи")
        self.test_sell_btn.clicked.connect(self.test_sell)
        control_layout.addWidget(self.test_sell_btn)
        
        left_layout.addLayout(control_layout)
        
        # Кнопки управления мониторингом
        monitor_buttons_layout = QHBoxLayout()
        
        self.add_monitor_btn = QPushButton("➕ Добавить в мониторинг")
        self.add_monitor_btn.clicked.connect(self.add_to_monitoring)
        monitor_buttons_layout.addWidget(self.add_monitor_btn)
        
        self.update_quantity_btn = QPushButton("🔄 Обновить количество")
        self.update_quantity_btn.clicked.connect(self.update_sell_quantity)
        self.update_quantity_btn.setToolTip("Обновить количество токенов для продажи на основе текущего баланса")
        monitor_buttons_layout.addWidget(self.update_quantity_btn)
        
        self.debug_balance_btn = QPushButton("[SEARCH] Диагностика баланса")
        self.debug_balance_btn.clicked.connect(self.debug_balance)
        self.debug_balance_btn.setToolTip("Проверить подключение и получить детальную информацию о балансе")
        monitor_buttons_layout.addWidget(self.debug_balance_btn)
        
        self.reconnect_btn = QPushButton("🔄 Переподключить сеть")
        self.reconnect_btn.clicked.connect(self.reconnect_network)
        self.reconnect_btn.setToolTip("Принудительно переподключиться к BSC сети")
        monitor_buttons_layout.addWidget(self.reconnect_btn)
        
        self.reset_nonce_btn = QPushButton("🧿 Сбросить Nonce")
        self.reset_nonce_btn.clicked.connect(self.reset_nonce)
        self.reset_nonce_btn.setToolTip("Очистить застрявшие nonce и сбросить счетчик")
        monitor_buttons_layout.addWidget(self.reset_nonce_btn)
        
        left_layout.addLayout(monitor_buttons_layout)
        
        left_layout.addStretch()
        
        # Правая панель - мониторинг и история
        right_panel = QGroupBox("Мониторинг и история")
        right_layout = QVBoxLayout(right_panel)
        
        # Статус мониторинга
        self.status_label = QLabel("⏸️ Мониторинг не запущен")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
        right_layout.addWidget(self.status_label)
        
        # Текущие балансы основных токенов
        self.balance_info = QTextEdit()
        self.balance_info.setReadOnly(True)
        self.balance_info.setMaximumHeight(150)
        self.balance_info.setPlaceholderText("Информация о балансах...")
        right_layout.addWidget(self.balance_info)
        
        # Отображение балансов основных токенов
        balances_group = QGroupBox("[MONEY] Балансы основных токенов")
        balances_layout = QVBoxLayout(balances_group)
        
        # BNB баланс
        self.bnb_balance_label = QLabel("BNB: 0.000000")
        self.bnb_balance_label.setStyleSheet("font-weight: bold; color: #F0B90B; padding: 5px;")
        balances_layout.addWidget(self.bnb_balance_label)
        
        # USDT баланс
        self.usdt_balance_label = QLabel("USDT: 0.000000")
        self.usdt_balance_label.setStyleSheet("font-weight: bold; color: #26A17B; padding: 5px;")
        balances_layout.addWidget(self.usdt_balance_label)
        
        # PLEX ONE баланс
        self.plex_balance_label = QLabel("PLEX ONE: 0.000000")
        self.plex_balance_label.setStyleSheet("font-weight: bold; color: #FF6B35; padding: 5px;")
        balances_layout.addWidget(self.plex_balance_label)
        
        # Кнопка обновления балансов
        self.refresh_balances_btn = QPushButton("🔄 Обновить балансы")
        self.refresh_balances_btn.clicked.connect(self.refresh_all_balances)
        self.refresh_balances_btn.setStyleSheet("""
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
        balances_layout.addWidget(self.refresh_balances_btn)
        
        right_layout.addWidget(balances_group)
        
        # Список отслеживаемых токенов
        tokens_label = QLabel("[STATS] Отслеживаемые токены:")
        right_layout.addWidget(tokens_label)
        
        self.monitored_table = QTableWidget()
        self.monitored_table.setColumnCount(6)
        self.monitored_table.setHorizontalHeaderLabels([
            "Токен", "Порог", "Режим продажи", "Продавать в", "Текущий баланс", "Действия"
        ])
        header = self.monitored_table.horizontalHeader()
        header.setStretchLastSection(True)  # type: ignore[misc]
        right_layout.addWidget(self.monitored_table)
        
        # История продаж
        history_label = QLabel("[HISTORY] История продаж:")
        right_layout.addWidget(history_label)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Время", "Токен", "Количество", "Получено", "Tx Hash", "Статус"
        ])
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(True)  # type: ignore[misc]
        right_layout.addWidget(self.history_table)
        
        # Добавляем панели в splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([500, 700])
        
        layout.addWidget(splitter)
        
        # Инициализация таймера (будет запущен после подключения кошелька)
        self.balance_timer = None
        
        # Инициализируем видимость элементов
        self._on_sell_mode_changed(self.sell_mode_combo.currentText())
        
    def _on_token_changed(self, token: str):
        """Обработка изменения выбранного токена"""
        self.log(f"🔽 Изменён токен для продажи: {token}", "INFO")
        is_custom = token == "Другой токен"
        self.custom_token_input.setVisible(is_custom)
        
        # Обновляем баланс при смене токена
        self._update_current_balance()
    
    def _on_sell_mode_changed(self, mode: str):
        """Обработка изменения режима продажи"""
        self.log(f"🔽 Изменён режим продажи: {mode}", "INFO")
        is_percentage = mode == "Процент от баланса"
        self.sell_percentage.setVisible(is_percentage)
        self.sell_quantity.setVisible(not is_percentage)
    
    def _update_current_balance(self):
        """Обновление отображения текущего баланса выбранного токена"""
        if not self.account or not self.web3:
            self.current_balance_label.setText("0.0000")
            return
        
        try:
            # Получаем адрес токена
            if self.token_combo.currentText() == "PLEX ONE":
                token_address = self.PLEX_ONE
            else:
                token_address = self.custom_token_input.text().strip()
                if not Web3.is_address(token_address):
                    self.current_balance_label.setText("Неверный адрес")
                    return
            
            # Получаем баланс
            balance = self._get_token_balance(token_address)
            self.current_balance_label.setText(f"{balance:.4f}")
            
        except Exception as e:
            self.current_balance_label.setText("Ошибка")
            self.log(f"Ошибка обновления баланса: {str(e)}", "ERROR")
    
    def connect_wallet(self):
        """Переопределенное подключение кошелька"""
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
                        seed_bytes: bytes = Bip39SeedGenerator(wallet_data).Generate()  # type: ignore[misc]
                        bip44_ctx: Any = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)  # type: ignore[misc]
                        private_key = bip44_ctx.PrivateKey().Raw().ToHex()  # type: ignore[misc]
                        self.account = Account.from_key(private_key)  # type: ignore[misc]
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
            else:  # Приватный ключ
                private_key = wallet_data
                if private_key.startswith('0x'):
                    private_key = private_key[2:]
                # Создаем аккаунт из приватного ключа
                self.account = Account.from_key(private_key)  # type: ignore[misc]
            
            # Обновляем UI
            self.wallet_address_label.setText(f"Адрес: {self.account.address}")  # type: ignore[misc]
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            
            self.log(f"[OK] Кошелек подключен: {self.account.address}", "SUCCESS")  # type: ignore[misc]
            
            # Обновляем все балансы
            self.refresh_all_balances()
            
            # Безопасно инициализируем таймер обновления балансов
            self._init_balance_timer()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключить кошелек:\n{str(e)}")
            self.log(f"[ERROR] Ошибка подключения кошелька: {e}", "ERROR")
    
    def _init_balance_timer(self):
        """Безопасная инициализация таймера обновления балансов"""
        try:
            if self.balance_timer is None:
                self.balance_timer = QTimer(self)  # Указываем parent для корректной работы
                self.balance_timer.timeout.connect(self.update_balance_display)
                self.balance_timer.start(10000)  # Каждые 10 секунд
                self.log("[OK] Таймер обновления балансов запущен", "INFO")
        except Exception as e:
            self.log(f"[WARN] Ошибка инициализации таймера: {e}", "WARNING")
    
    def disconnect_wallet(self):
        """Отключение кошелька"""
        # Останавливаем таймер
        if self.balance_timer:
            self.balance_timer.stop()
            self.balance_timer = None
            self.log("⏹️ Таймер обновления балансов остановлен", "INFO")
            
        self.account = None
        self.wallet_address_label.setText("Адрес: Не подключен")
        self.disconnect_btn.setEnabled(False)
        self.balance_info.clear()
        
        # Очищаем балансы
        self.bnb_balance_label.setText("BNB: 0.000000")
        self.usdt_balance_label.setText("USDT: 0.000000")
        self.plex_balance_label.setText("PLEX ONE: 0.000000")
        self.current_balance_label.setText("0.0000")
        
        self.log("[DISCONNECT] Кошелек отключен", "INFO")
    
    def add_to_monitoring(self):
        """Добавление токена в список мониторинга"""
        self.log("🖱️ Нажата кнопка: Добавить в мониторинг", "INFO")
        if not self.account:
            QMessageBox.warning(self, "Ошибка", "Сначала подключите кошелек!")
            return
        
        # Получаем настройки
        if self.token_combo.currentText() == "PLEX ONE":
            token_address = self.PLEX_ONE
            token_name = "PLEX ONE"
        else:
            token_address = self.custom_token_input.text().strip()
            if not Web3.is_address(token_address):
                QMessageBox.warning(self, "Ошибка", "Неверный адрес токена!")
                return
            token_name = self._get_token_name(token_address)
        
        # Определяем режим продажи и количество
        sell_mode = self.sell_mode_combo.currentText()
        if sell_mode == "Процент от баланса":
            sell_amount = self.sell_percentage.value()
            sell_type = "percentage"
        else:
            sell_amount = self.sell_quantity.value()
            sell_type = "quantity"
        
        # Добавляем в словарь мониторинга
        self.monitored_tokens[token_address] = {
            'name': token_name,
            'threshold': self.threshold_input.value(),
            'target': self.target_combo.currentText(),
            'sell_mode': sell_mode,
            'sell_type': sell_type,
            'sell_amount': sell_amount,
            'percentage': self.sell_percentage.value(),
            'quantity': self.sell_quantity.value(),
            'min_price': self.min_price_input.value(),
            'slippage': self.slippage_input.value(),
            'cyclic_sales': self.cyclic_sales_checkbox.isChecked(),
            'last_sale_time': 0  # Время последней продажи
        }
        
        # Добавляем в таблицу
        row = self.monitored_table.rowCount()
        self.monitored_table.insertRow(row)
        self.monitored_table.setItem(row, 0, QTableWidgetItem(token_name))
        self.monitored_table.setItem(row, 1, QTableWidgetItem(f"{self.threshold_input.value():.2f}"))
        
        # Отображаем режим продажи
        sell_display = f"{sell_mode}: {sell_amount}"
        if sell_type == "percentage":
            sell_display += "%"
        else:
            sell_display += " токенов"
        
        # Добавляем информацию о циклических продажах
        if self.cyclic_sales_checkbox.isChecked():
            sell_display += " (цикл)"
        
        self.monitored_table.setItem(row, 2, QTableWidgetItem(sell_display))
        
        self.monitored_table.setItem(row, 3, QTableWidgetItem(self.target_combo.currentText()))
        self.monitored_table.setItem(row, 4, QTableWidgetItem("0"))
        
        # Кнопка удаления
        remove_btn = QPushButton("[ERROR]")
        remove_btn.clicked.connect(lambda: self.remove_from_monitoring(token_address))
        self.monitored_table.setCellWidget(row, 5, remove_btn)
        
        self.log(f"[OK] {token_name} добавлен в мониторинг", "SUCCESS")
    
    def update_sell_quantity(self):
        """Обновление количества токенов для продажи на основе текущего баланса"""
        if not self.account:
            QMessageBox.warning(self, "Ошибка", "Сначала подключите кошелек!")
            return
        
        # Получаем адрес токена
        if self.token_combo.currentText() == "PLEX ONE":
            token_address = self.PLEX_ONE
            token_name = "PLEX ONE"
        else:
            token_address = self.custom_token_input.text().strip()
            if not Web3.is_address(token_address):
                QMessageBox.warning(self, "Ошибка", "Неверный адрес токена!")
                return
            token_name = self._get_token_name(token_address)
        
        # Получаем текущий баланс
        balance = self._get_token_balance(token_address)
        
        if balance <= 0:
            QMessageBox.warning(self, "Ошибка", f"Нет баланса {token_name}!")
            return
        
        # Обновляем поле количества
        self.sell_quantity.setValue(balance)
        
        # Показываем информацию
        QMessageBox.information(
            self,
            "Количество обновлено",
            f"Количество токенов для продажи обновлено на {balance:.4f} {token_name}"
        )
        
        self.log(f"🔄 Количество обновлено: {balance:.4f} {token_name}", "INFO")
    
    def refresh_all_balances(self):
        """Обновление балансов всех основных токенов"""
        if not self.account:
            QMessageBox.warning(self, "Ошибка", "Сначала подключите кошелек!")
            return
        
        self.log("🔄 Обновляем балансы всех токенов...", "INFO")
        
        try:
            # Проверяем и обновляем Web3 подключение
            if not self.web3 or not self.web3.is_connected():
                self.log("[WARN] Web3 не подключен, переподключаемся...", "WARNING")
                self._init_web3()
            
            # Обновляем BNB баланс
            try:
                bnb_balance = self.web3.eth.get_balance(self.account.address)
                bnb_formatted = self.web3.from_wei(bnb_balance, 'ether')
                self.bnb_balance_label.setText(f"BNB: {bnb_formatted:.6f}")
                self.log(f"[MONEY] BNB баланс: {bnb_formatted:.6f}", "SUCCESS")
            except Exception as e:
                self.log(f"[ERROR] Ошибка получения BNB баланса: {str(e)}", "ERROR")
                self.bnb_balance_label.setText("BNB: Ошибка")
            
            # Обновляем USDT баланс
            try:
                usdt_balance = self._get_token_balance(self.USDT)
                self.usdt_balance_label.setText(f"USDT: {usdt_balance:.6f}")
                if usdt_balance > 0:
                    self.log(f"[MONEY] USDT баланс: {usdt_balance:.6f}", "SUCCESS")
            except Exception as e:
                self.log(f"[ERROR] Ошибка получения USDT баланса: {str(e)}", "ERROR")
                self.usdt_balance_label.setText("USDT: Ошибка")
            
            # Обновляем PLEX ONE баланс
            try:
                plex_balance = self._get_token_balance(self.PLEX_ONE)
                self.plex_balance_label.setText(f"PLEX ONE: {plex_balance:.6f}")
                if plex_balance > 0:
                    self.log(f"[MONEY] PLEX ONE баланс: {plex_balance:.6f}", "SUCCESS")
            except Exception as e:
                self.log(f"[ERROR] Ошибка получения PLEX ONE баланса: {str(e)}", "ERROR")
                self.plex_balance_label.setText("PLEX ONE: Ошибка")
            
            # Обновляем текущий баланс выбранного токена
            self._update_current_balance()
            
            # Обновляем общую информацию
            self.update_balance_display()
            
            self.log("[OK] Обновление балансов завершено", "SUCCESS")
            
        except Exception as e:
            self.log(f"[ERROR] Критическая ошибка обновления балансов: {str(e)}", "ERROR")
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить балансы:\n{str(e)}")
    


    def debug_balance(self):
        """Диагностика баланса и подключения"""
        self.log("[SEARCH] === ДИАГНОСТИКА БАЛАНСА ===", "INFO")
        
        # Проверяем подключение кошелька
        if not self.account:
            self.log("[ERROR] Кошелек не подключен", "ERROR")
            QMessageBox.warning(self, "Диагностика", "Кошелек не подключен!")
            return
        
        self.log(f"[OK] Кошелек подключен: {self.account.address}", "SUCCESS")
        
        # Проверяем Web3 подключение
        if not self.web3:
            self.log("[ERROR] Web3 не инициализирован", "ERROR")
            QMessageBox.warning(self, "Диагностика", "Web3 не инициализирован!")
            return
        
        if not self.web3.is_connected():
            self.log("[ERROR] Нет подключения к BSC сети", "ERROR")
            QMessageBox.warning(self, "Диагностика", "Нет подключения к BSC сети!")
            return
        
        self.log("[OK] Web3 подключен к BSC", "SUCCESS")
        
        # Проверяем BNB баланс
        try:
            bnb_balance = self.web3.eth.get_balance(self.account.address)
            bnb_formatted = self.web3.from_wei(bnb_balance, 'ether')
            self.log(f"[MONEY] BNB баланс: {bnb_formatted:.6f}", "SUCCESS")
        except Exception as e:
            self.log(f"[ERROR] Ошибка получения BNB баланса: {str(e)}", "ERROR")
        
        # Проверяем выбранный токен
        if self.token_combo.currentText() == "PLEX ONE":
            token_address = self.PLEX_ONE
            token_name = "PLEX ONE"
        else:
            token_address = self.custom_token_input.text().strip()
            if not Web3.is_address(token_address):
                self.log("[ERROR] Неверный адрес токена", "ERROR")
                QMessageBox.warning(self, "Диагностика", "Неверный адрес токена!")
                return
            token_name = self._get_token_name(token_address)
        
        self.log(f"[SEARCH] Проверяем токен: {token_name} ({token_address})", "INFO")
        
        # Получаем баланс токена
        balance = self._get_token_balance(token_address)
        
        # Обновляем отображение
        self._update_current_balance()
        
        # Показываем результат
        if balance > 0:
            QMessageBox.information(
                self,
                "Диагностика",
                f"[OK] Баланс найден!\n\n"
                f"Токен: {token_name}\n"
                f"Адрес: {token_address}\n"
                f"Баланс: {balance:.6f}\n"
                f"Кошелек: {self.account.address}"
            )
        else:
            QMessageBox.warning(
                self,
                "Диагностика",
                f"[WARN] Баланс не найден\n\n"
                f"Токен: {token_name}\n"
                f"Адрес: {token_address}\n"
                f"Кошелек: {self.account.address}\n\n"
                f"Возможные причины:\n"
                f"• Токен не существует\n"
                f"• Неверный адрес токена\n"
                f"• На кошельке нет этого токена\n"
                f"• Проблемы с сетью"
            )
        
        self.log("[SEARCH] === КОНЕЦ ДИАГНОСТИКИ ===", "INFO")
    
    def reset_nonce(self):
        """Сброс и очистка застрявших nonce"""
        self.log("🧿 Сбрасываем nonce...", "INFO")
        
        if not self.account:
            QMessageBox.warning(self, "Ошибка", "Сначала подключите кошелек!")
            return
        
        try:
            if self.nonce_manager:
                # Получаем статистику до сброса
                stats_before = self.nonce_manager.get_stats(self.account.address)
                pending_before = stats_before.get('pending_count', 0) if stats_before else 0
                
                self.log(f"[SEARCH] Pending nonce до сброса: {pending_before}", "INFO")
                
                # Полный сброс состояния для адреса
                self.nonce_manager.reset_address(self.account.address)
                
                # Очищаем локальный билет
                self._last_nonce_ticket = None
                
                # Пересоздаем DexSwapService если он существует
                if hasattr(self, '_dex_service') and self._dex_service:
                    self._dex_service = None
                    self.log("[OK] DexSwapService сброшен", "SUCCESS")
                
                # Получаем статистику после сброса
                stats_after = self.nonce_manager.get_stats(self.account.address)
                pending_after = stats_after.get('pending_count', 0) if stats_after else 0
                
                self.log(f"[OK] Nonce сброшены! Pending: {pending_before} -> {pending_after}", "SUCCESS")
                
                QMessageBox.information(
                    self,
                    "Сброс Nonce",
                    f"[OK] Nonce успешно сброшены!\n\n"
                    f"Pending до: {pending_before}\n"
                    f"Pending после: {pending_after}\n\n"
                    f"Можно продолжать работу."
                )
                
            else:
                self.log("[WARN] Nonce Manager не инициализирован", "WARNING")
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Nonce Manager не инициализирован.\nПереподключитесь к сети."
                )
                
        except Exception as e:
            self.log(f"[ERROR] Ошибка сброса nonce: {str(e)}", "ERROR")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сбросить nonce:\n{str(e)}"
            )
    
    def reconnect_network(self):
        """Принудительное переподключение к сети"""
        self.log("🔄 Переподключаемся к BSC сети...", "INFO")
        
        try:
            # Переинициализируем Web3
            self._init_web3()
            
            if self.web3 and self.web3.is_connected():
                self.log("[OK] Переподключение к сети успешно", "SUCCESS")
                
                # Обновляем балансы после переподключения
                if self.account:
                    self.refresh_all_balances()
                
                QMessageBox.information(
                    self,
                    "Переподключение",
                    "[OK] Успешно переподключились к BSC сети!\n\nБалансы обновлены."
                )
            else:
                self.log("[ERROR] Не удалось переподключиться к сети", "ERROR")
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "[ERROR] Не удалось переподключиться к BSC сети.\n\nПроверьте интернет-соединение."
                )
                
        except Exception as e:
            self.log(f"[ERROR] Ошибка переподключения: {str(e)}", "ERROR")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"[ERROR] Критическая ошибка переподключения:\n{str(e)}"
            )
    
    def remove_from_monitoring(self, token_address: str):
        """Удаление токена из мониторинга"""
        if token_address in self.monitored_tokens:
            del self.monitored_tokens[token_address]
            
            # Обновляем таблицу
            self._refresh_monitored_table()
            self.log(f"[ERROR] Токен удален из мониторинга", "INFO")
    
    def _refresh_monitored_table(self):
        """Обновление таблицы отслеживаемых токенов"""
        self.monitored_table.setRowCount(0)
        
        for token_address, settings in self.monitored_tokens.items():
            row = self.monitored_table.rowCount()
            self.monitored_table.insertRow(row)
            self.monitored_table.setItem(row, 0, QTableWidgetItem(settings['name']))
            self.monitored_table.setItem(row, 1, QTableWidgetItem(f"{settings['threshold']:.2f}"))
            
            # Отображаем режим продажи
            sell_display = f"{settings.get('sell_mode', 'Процент от баланса')}: {settings.get('sell_amount', settings.get('percentage', 100))}"
            if settings.get('sell_type', 'percentage') == "percentage":
                sell_display += "%"
            else:
                sell_display += " токенов"
            
            # Добавляем информацию о циклических продажах
            if settings.get('cyclic_sales', False):
                sell_display += " (цикл)"
            
            self.monitored_table.setItem(row, 2, QTableWidgetItem(sell_display))
            
            self.monitored_table.setItem(row, 3, QTableWidgetItem(settings['target']))
            
            # Получаем текущий баланс
            balance = self._get_token_balance(token_address)
            self.monitored_table.setItem(row, 4, QTableWidgetItem(f"{balance:.4f}"))
            
            # Кнопка удаления
            remove_btn = QPushButton("[ERROR]")
            remove_btn.clicked.connect(lambda addr=token_address: self.remove_from_monitoring(addr))
            self.monitored_table.setCellWidget(row, 5, remove_btn)
    
    def start_monitoring(self):
        """Запуск мониторинга"""
        if not self.account:
            QMessageBox.warning(self, "Ошибка", "Сначала подключите кошелек!")
            return
        
        if not self.monitored_tokens:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы один токен для мониторинга!")
            return
        
        if self.is_monitoring:
            self.log("[WARN] Мониторинг уже запущен", "WARNING")
            return
            
        # Проверяем баланс BNB перед запуском
        try:
            bnb_balance = self.web3.eth.get_balance(self.account.address)
            bnb_balance_ether = self.web3.from_wei(bnb_balance, 'ether')
            min_required_bnb = 0.00001  # Минимум 0.00001 BNB (примерно на 1-2 транзакции)
            
            if bnb_balance_ether < min_required_bnb:
                self.log(f"⛽ Критически низкий баланс BNB: {bnb_balance_ether:.8f} < {min_required_bnb}", "ERROR")
                QMessageBox.warning(
                    self, 
                    "Критически низкий баланс BNB", 
                    f"Баланс BNB слишком мал для любых операций: {bnb_balance_ether:.8f} BNB\n"
                    f"Минимум для работы: {min_required_bnb} BNB\n\n"
                    f"Пополните баланс BNB и попробуйте снова."
                )
                return
            elif bnb_balance_ether < 0.0001:
                self.log(f"[WARN] Очень низкий баланс BNB: {bnb_balance_ether:.8f}. Хватит только на несколько операций.", "WARNING")
            elif bnb_balance_ether < 0.001:
                self.log(f"[WARN] Низкий баланс BNB: {bnb_balance_ether:.6f}. Может не хватить на много операций.", "WARNING")
            else:
                self.log(f"[OK] BNB баланс достаточен: {bnb_balance_ether:.6f}", "INFO")
                
        except Exception as e:
            self.log(f"[ERROR] Ошибка проверки BNB баланса: {e}", "ERROR")
            QMessageBox.warning(self, "Ошибка", f"Не удалось проверить баланс BNB: {e}")
            return
        
        self.is_monitoring = True
        self.stop_monitoring.clear()
        
        # Обновляем UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("[OK] Мониторинг активен")
        self.status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
        
        # Запускаем поток мониторинга
        self.monitoring_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.monitoring_thread.start()
        
        self.log("[START] Мониторинг запущен", "SUCCESS")
    
    def stop_monitoring_func(self):
        """Остановка мониторинга"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.stop_monitoring.set()
        
        # Обновляем UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("⏸️ Мониторинг остановлен")
        self.status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
        
        self.log("⏹️ Мониторинг остановлен", "INFO")
    
    def _monitoring_worker(self):
        """Рабочий поток мониторинга с усиленной защитой от ошибок"""
        self.log("🔄 Поток мониторинга запущен", "INFO")
        
        try:
            interval = self.check_interval.value()
            consecutive_errors = 0
            max_consecutive_errors = 10
            
            while not self.stop_monitoring.is_set():
                try:
                    current_time = time.time()
                    
                    # Проверяем базовые условия перед началом цикла
                    if not self.account:
                        self.log("[ERROR] Кошелек не подключен - остановка мониторинга", "ERROR")
                        break
                        
                    if not self.web3:
                        self.log("[ERROR] Web3 не инициализирован - остановка мониторинга", "ERROR")
                        break
                        
                    if not self.monitored_tokens:
                        self.log("[WARN] Нет токенов для мониторинга - ожидание", "WARNING")
                        self.stop_monitoring.wait(interval)
                        continue
                    
                    # Проверяем подключение к сети
                    try:
                        if not self.web3.is_connected():
                            self.log("[WARN] Потеряно подключение к BSC - переподключение", "WARNING")
                            time.sleep(5)
                            continue
                    except Exception as conn_error:
                        self.log(f"[WARN] Ошибка проверки подключения: {conn_error}", "WARNING")
                        time.sleep(5)
                        continue
                    
                    # Основной цикл мониторинга
                    for token_address, settings in self.monitored_tokens.items():
                        if self.stop_monitoring.is_set():
                            break
                        
                        # Получаем баланс токена
                        balance = self._get_token_balance(token_address)
                        
                        should_sell = False
                        should_sell = False
                        sell_reason = ""
                        
                        # Проверяем условия для продажи
                        if settings.get('cyclic_sales', False):
                            # Циклические продажи - проверяем интервал
                            time_since_last_sale = current_time - settings.get('last_sale_time', 0)
                            if time_since_last_sale >= interval:
                                should_sell = True
                                sell_reason = f"Циклическая продажа (интервал: {interval}с)"
                        else:
                            # Обычные продажи - проверяем порог
                            if balance >= settings['threshold']:
                                should_sell = True
                                sell_reason = f"Достигнут порог: {balance:.4f} >= {settings['threshold']}"
                        
                        if should_sell and balance > 0:
                            self.log(f"[TARGET] {sell_reason} для {settings['name']}", "INFO")
                            
                            # Рассчитываем количество для продажи в зависимости от режима
                            if settings.get('sell_type', 'percentage') == 'percentage':
                                sell_amount = balance * (settings.get('sell_amount', settings.get('percentage', 100)) / 100)
                            else:
                                # Фиксированное количество
                                sell_amount = min(settings.get('sell_amount', settings.get('quantity', 100)), balance)
                            
                            # Проверяем, что есть что продавать
                            if sell_amount <= 0:
                                self.log(f"[WARN] Нет токенов для продажи {settings['name']}", "WARNING")
                                continue
                            
                            # Проверяем цену если установлен минимум
                            if settings['min_price'] > 0:
                                price = self._get_token_price(token_address, settings['target'])
                                if price < settings['min_price']:
                                    self.log(f"[WARN] Цена {price:.8f} ниже минимальной {settings['min_price']}", "WARNING")
                                    continue
                            
                            # Выполняем продажу с защитой от зависания
                            try:
                                # Устанавливаем максимальное время выполнения операции - 120 секунд
                                sell_start_time = time.time()
                                self.log(f"[START] Начинаем продажу {settings['name']}: {sell_amount:.4f}", "INFO")
                                
                                self._execute_sell(token_address, sell_amount, settings)
                                
                                # Проверяем время выполнения
                                execution_time = time.time() - sell_start_time
                                self.log(f"[OK] Продажа {settings['name']} завершена за {execution_time:.2f}с", "INFO")
                                
                                # КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ если операция была слишком долгой
                                if execution_time > 60:
                                    self.log(f"[WARN] ДОЛГАЯ ОПЕРАЦИЯ: {execution_time:.2f}с - проверьте сеть!", "WARNING")
                                
                            except Exception as e:
                                self.log(f"[ERROR] КРИТИЧЕСКАЯ ОШИБКА продажи {settings['name']}: {str(e)}", "ERROR")
                                # Продолжаем мониторинг других токенов даже если один упал
                            
                            # Обновляем время последней продажи
                            self.monitored_tokens[token_address]['last_sale_time'] = current_time
                    
                    # Ждем перед следующей проверкой
                    self.stop_monitoring.wait(interval)
                    
                    # Сбрасываем счетчик ошибок при успешной итерации
                    consecutive_errors = 0
                    
                except Exception as e:
                    consecutive_errors += 1
                    error_str = str(e)
                    
                    self.log(f"[ERROR] Ошибка в мониторинге (#{consecutive_errors}): {error_str}", "ERROR")
                    
                    # Если слишком много ошибок подряд - останавливаем мониторинг
                    if consecutive_errors >= max_consecutive_errors:
                        self.log(f"🚨 Критично: {consecutive_errors} ошибок подряд - остановка мониторинга", "ERROR")
                        self.log("💡 Проверьте подключение к интернету и настройки RPC", "INFO")
                        self.is_monitoring = False
                        return
                    
                    # Специальная обработка ошибки недостатка газа
                    if 'insufficient funds' in error_str or 'Недостаточно BNB для газа' in error_str:
                        self.log(f"⛽ Критическая ошибка - недостаток BNB для газа: {error_str}", "ERROR")
                        self.log("⏸️ Приостанавливаем мониторинг на 60 секунд из-за нехватки газа", "WARNING")
                        self.log("💡 Пополните баланс BNB для продолжения работы", "INFO")
                        
                        # Делаем длительную паузу, но не останавливаем полностью
                        for _ in range(60):
                            if self.stop_monitoring.is_set():
                                break
                            time.sleep(1)
                    else:
                        # Экспоненциальная задержка при ошибках
                        delay = min(5 * consecutive_errors, 30)  # Максимум 30 секунд
                        self.log(f"🔄 Повторная попытка через {delay} секунд...", "INFO")
                        time.sleep(delay)
                    
        except Exception as critical_error:
            self.log(f"🚨 КРИТИЧЕСКАЯ ОШИБКА потока мониторинга: {critical_error}", "ERROR")
            import traceback
            self.log(f"[INFO] Полная трассировка: {traceback.format_exc()}", "ERROR")
        finally:
            # Гарантированная очистка при завершении потока
            self.log("🔄 Поток мониторинга завершен", "INFO")
            try:
                self.is_monitoring = False
                # Обновляем UI в главном потоке
                if hasattr(self, 'start_btn'):
                    self.start_btn.setEnabled(True)
                if hasattr(self, 'stop_btn'):
                    self.stop_btn.setEnabled(False)
                if hasattr(self, 'status_label'):
                    self.status_label.setText("⏹️ Мониторинг остановлен")
            except Exception as cleanup_error:
                self.log(f"[WARN] Ошибка при очистке UI: {cleanup_error}", "WARNING")
    
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

    def _check_liquidity(self, token_address: str, min_liquidity_bnb: float = 0.1) -> bool:
        """Проверяет наличие достаточной ликвидности"""
        try:
            # Для PLEX ONE проверяем ликвидность с USDT
            if token_address.lower() == self.PLEX_ONE.lower():
                # Проверяем ликвидность PLEX ONE -> USDT
                test_amount = self.web3.to_wei(1000, 'ether')  # 1000 PLEX ONE (9 decimals)
                path = [token_address, self.USDT]
            else:
                # Для других токенов проверяем через WBNB
                test_amount = self.web3.to_wei(0.001, 'ether')  # 0.001 BNB
                path = [self.WBNB, token_address]
            
            amounts = self._get_amounts_out_with_retry(test_amount, path)
            if amounts and len(amounts) > 0 and amounts[-1] > 0:
                self.log("[OK] Ликвидность токена подтверждена", "SUCCESS")
                return True
            else:
                self.log("[WARN] Недостаточная ликвидность токена", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"[ERROR] Ошибка проверки ликвидности: {e}", "ERROR")
            return False

    def _get_amounts_out_with_retry(self, amount_in: int, path: List[str]) -> List[int]:
        """Получает ожидаемое количество токенов на выходе с retry"""
        def _get():
            path_checksum = [Web3.to_checksum_address(addr) for addr in path]
            router_contract = self.web3.eth.contract(
                address=self.PANCAKE_ROUTER,
                abi=PANCAKE_ROUTER_ABI
            )
            return router_contract.functions.getAmountsOut(amount_in, path_checksum).call()
            
        try:
            amounts = self._retry_call(_get)
            
            # Проверка на корректность
            if not amounts or len(amounts) < 2:
                raise ValueError("Некорректный ответ от роутера")
                
            if amounts[-1] == 0:
                raise ValueError("Нулевое количество токенов на выходе - проверьте ликвидность")
                
            return amounts
            
        except Exception as e:
            self.log(f"[ERROR] Ошибка расчета выходного количества: {e}", "ERROR")
            return [0, 0]

    def _validate_swap_params(self, token_address: str, amount: float, is_buy: bool) -> Dict[str, Any]:
        """Валидирует параметры свапа перед выполнением"""
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
                
            # Проверка баланса BNB для газа
            bnb_balance = self.web3.eth.get_balance(self.account.address)
            bnb_balance_eth = self.web3.from_wei(bnb_balance, 'ether')
            estimated_gas_cost = 0.003  # Примерно 0.003 BNB на транзакцию
            
            if bnb_balance_eth < estimated_gas_cost:
                self.log(f"[WARN] Низкий баланс BNB: {bnb_balance_eth:.6f}. Может не хватить на газ.", "WARNING")
                
            # Проверка ликвидности
            if not self._check_liquidity(token_address):
                self.log("[WARN] Низкая ликвидность пула. Транзакция может не пройти.", "WARNING")
                
            return {
                'valid': True,
                'bnb_balance': bnb_balance_eth,
                'estimated_gas': estimated_gas_cost
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    def _check_and_approve(self, token_address: str, amount: int) -> bool:
        """Проверяет и выполняет approve с retry и валидацией"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                token_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(token_address),
                    abi=ERC20_ABI
                )
                
                current_allowance = token_contract.functions.allowance(
                    self.account.address,
                    self.PANCAKE_ROUTER
                ).call()
                
                if current_allowance >= amount:
                    self.log(f"[OK] Approve не требуется, текущий allowance: {current_allowance}", "SUCCESS")
                    return True
                    
                self.log(f"📝 Требуется approve (попытка {attempt + 1}/{max_retries})", "INFO")
                
                # Проверяем баланс перед approve
                token_balance_wei = token_contract.functions.balanceOf(self.account.address).call()
                if token_balance_wei < amount:
                    raise ValueError(f"Недостаточно токенов для approve. Баланс: {token_balance_wei}, требуется: {amount}")
                
                # Проверяем nonce
                nonce = self.web3.eth.get_transaction_count(self.account.address)
                self.log(f"[SEARCH] Текущий nonce: {nonce}", "INFO")
                
                # Строим транзакцию approve
                approve_tx = token_contract.functions.approve(
                    self.PANCAKE_ROUTER,
                    amount
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 100000,
                    'gasPrice': self.get_gas_price_wei(),
                    'nonce': nonce,
                })
                
                self.log(f"[SEND] Отправка approve транзакции...", "INFO")
                
                # Подписываем и отправляем
                signed_approve = self.web3.eth.account.sign_transaction(approve_tx, self.account.key)
                approve_hash = self.web3.eth.send_raw_transaction(signed_approve.rawTransaction)
                
                if not approve_hash:
                    raise Exception("Не удалось отправить approve транзакцию")
                    
                self.log(f"[SEND] Approve транзакция отправлена: {approve_hash.hex()}", "INFO")
                
                # Ждем подтверждения с таймаутом
                self.log("⏳ Ожидание подтверждения approve...", "INFO")
                receipt = self.web3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
                
                if receipt and receipt['status'] == 1:
                    self.log(f"[OK] Approve успешно выполнен. Gas used: {receipt['gasUsed']}", "SUCCESS")
                    
                    # Проверяем, что approve действительно прошел
                    time.sleep(2)  # Даем время на обновление состояния
                    new_allowance = token_contract.functions.allowance(
                        self.account.address,
                        self.PANCAKE_ROUTER
                    ).call()
                    if new_allowance > 0:
                        return True
                    else:
                        self.log("[WARN] Allowance не обновился после approve", "WARNING")
                        
                else:
                    if receipt:
                        self.log(f"[ERROR] Approve транзакция провалилась. Status: {receipt.get('status')}", "ERROR")
                    else:
                        self.log("[ERROR] Не удалось получить receipt транзакции", "ERROR")
                        
            except Exception as e:
                self.log(f"[ERROR] Ошибка при approve (попытка {attempt + 1}/{max_retries}): {e}", "ERROR")
                
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    self.log(f"🔄 Повторная попытка через {wait_time} секунд...", "INFO")
                    time.sleep(wait_time)
                else:
                    return False
                    
        return False

    def _check_liquidity_pool(self, token_address: str, target_token: str):
        """Проверка существования пула ликвидности"""
        try:
            # Известные пулы для PLEX ONE (в checksum формате)
            known_pools = {
                "0xdf179b6cAdBC61FFD86A3D2e55f6d6e083ade6c1": {  # PLEX ONE
                    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c": "0x41d9650faf3341cbf8947fd8063a1fc88dbf1889",  # WBNB
                    "0x55d398326f99059fF775485246999027B3197955": "0xc7961e1e762d4b1975a3fcd07b8f70e34726c04e"   # USDT
                }
            }
            
            # Проверяем известные пулы
            token_checksum = Web3.to_checksum_address(token_address)
            target_checksum = Web3.to_checksum_address(target_token)
            
            self.log(f"[SEARCH] Ищем пул для: {token_checksum} -> {target_checksum}", "INFO")
            self.log(f"[SEARCH] Доступные пулы для токена: {list(known_pools.keys())}", "INFO")
            
            if token_checksum in known_pools:
                self.log(f"[SEARCH] Найден токен в известных пулах", "INFO")
                if target_checksum in known_pools[token_checksum]:
                    self.log(f"[SEARCH] Найден целевой токен в пулах", "INFO")
                else:
                    self.log(f"[SEARCH] Целевой токен не найден в пулах: {list(known_pools[token_checksum].keys())}", "INFO")
            else:
                self.log(f"[SEARCH] Токен не найден в известных пулах", "INFO")
            
            if token_checksum in known_pools and target_checksum in known_pools[token_checksum]:
                pool_address = known_pools[token_checksum][target_checksum]
                self.log(f"[SEARCH] Используем известный пул: {pool_address}", "INFO")
                
                # Просто возвращаем известный пул без проверки (так как вы подтвердили, что он существует)
                return True, pool_address
            
            # Если известный пул не найден, пробуем через Factory
            try:
                factory_address = "0xcA143Ce0Fe65960E6Aa4D42C8d3cE161c2B6604c"  # PancakeSwap Factory
                factory_abi = [{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"}],"name":"getPair","outputs":[{"internalType":"address","name":"pair","type":"address"}],"stateMutability":"view","type":"function"}]
                
                factory_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(factory_address),
                    abi=factory_abi
                )
                
                pair_address = factory_contract.functions.getPair(
                    token_checksum,
                    target_checksum
                ).call()
                
                if pair_address != "0x0000000000000000000000000000000000000000":
                    # Проверяем, что контракт пары существует
                    code = self.web3.eth.get_code(pair_address)
                    if len(code) > 0:
                        return True, pair_address
                        
            except Exception as factory_error:
                self.log(f"[SEARCH] Ошибка Factory: {str(factory_error)}", "WARNING")
            
            return False, None
            
        except Exception as e:
            self.log(f"[SEARCH] Ошибка проверки пула: {str(e)}", "WARNING")
            return False, None

    def _execute_sell(self, token_address: str, amount: float, settings: Dict[str, Any]):
        """Выполнение продажи токена с улучшенной обработкой ошибок и защитой от зависания"""
        start_time = time.time()
        
        # ДИАГНОСТИКА NONCE: Проверяем состояние перед началом
        if self.nonce_manager and self.account:
            try:
                nonce_stats = self.nonce_manager.get_stats(self.account.address)
                if nonce_stats:
                    pending_count = nonce_stats.get('pending_count', 0)
                    self.log(f"[SEARCH] Nonce статистика: pending={pending_count}, reserved={nonce_stats.get('total_reserved', 0)}", "INFO")
                    
                    # КРИТИЧЕСКАЯ ПРОВЕРКА: Если слишком много pending, ждем или очищаем
                    if pending_count > 10:
                        self.log(f"[WARN] КРИТИЧНО: Слишком много pending nonce ({pending_count})!", "ERROR")
                        self.log("🔄 Пытаемся очистить застрявшие nonce...", "INFO")
                        
                        # Принудительная ресинхронизация
                        self.nonce_manager.resync(self.account.address)
                        time.sleep(2)  # Даем время на очистку
                        
                        # Проверяем снова
                        nonce_stats = self.nonce_manager.get_stats(self.account.address)
                        new_pending_count = nonce_stats.get('pending_count', 0)
                        
                        if new_pending_count > 5:
                            self.log(f"[ERROR] Не удалось очистить pending nonce. Отменяем продажу.", "ERROR")
                            return  # Выходим без продажи
                        
                        self.log(f"[OK] Pending nonce очищены: {pending_count} -> {new_pending_count}", "SUCCESS")
            except Exception as e:
                self.log(f"[WARN] Не удалось получить nonce статистику: {e}", "WARNING")
        
        # Инициализируем nonce билет как None
        self._last_nonce_ticket = None
        
        try:
            self.log(f"=== [START] Начало операции продажи {settings['name']}: {amount:.4f} ===", "INFO")

            # Ленивая инициализация DexSwapService (если приватный ключ / account уже установлен)
            if not hasattr(self, '_dex_service') or getattr(self, '_dex_service') is None:
                if self.account and self.web3:
                    try:
                        # Получаем кастомную цену газа из интерфейса
                        custom_gas_price = self.gas_price_input.value()
                        self._dex_service = DexSwapService(self.web3, self.PANCAKE_ROUTER, self.account.key, custom_gas_price_gwei=custom_gas_price)  # type: ignore[attr-defined]
                        self.log(f"[CONFIG] DexSwapService инициализирован с ценой газа {custom_gas_price} gwei", "INFO")
                    except Exception as e:  # noqa: BLE001
                        self._dex_service = None
                        self.log(f"[WARN] DexSwapService init fail: {e}", "WARNING")
                else:
                    self._dex_service = None
            else:
                # Обновляем цену газа в существующем DexSwapService
                custom_gas_price = self.gas_price_input.value()
                if hasattr(self._dex_service, 'set_custom_gas_price'):
                    self._dex_service.set_custom_gas_price(custom_gas_price)
                    self.log(f"[SETTINGS] Обновлена цена газа до {custom_gas_price} gwei", "INFO")
            
            # Валидация параметров
            validation = self._validate_swap_params(token_address, amount, is_buy=False)
            if not validation['valid']:
                raise Exception(validation['error'])
            
            # Получаем контракт токена
            token_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            # Получаем decimals
            decimals = token_contract.functions.decimals().call()
            amount_wei = int(amount * (10 ** decimals))
            self.log(f"[SEARCH] Количество в wei: {amount_wei} (decimals: {decimals})", "INFO")
            
            # Проверяем баланс
            balance = token_contract.functions.balanceOf(self.account.address).call()
            if balance < amount_wei:
                self.log(f"[WARN] Недостаточный баланс: {balance / (10 ** decimals):.4f} < {amount:.4f}", "WARNING")
                return
            
            # Определяем путь обмена
            if settings['target'] == 'BNB':
                target_token = self.WBNB
                # Для PLEX ONE используем прямой путь к WBNB
                if token_address.lower() == self.PLEX_ONE.lower():
                    path = [Web3.to_checksum_address(token_address), self.WBNB]
                else:
                    path = [Web3.to_checksum_address(token_address), self.WBNB]
                swap_method = 'swapExactTokensForETH'
            else:  # USDT
                target_token = self.USDT
                # Для PLEX ONE используем прямой путь к USDT
                if token_address.lower() == self.PLEX_ONE.lower():
                    path = [Web3.to_checksum_address(token_address), self.USDT]
                else:
                    path = [Web3.to_checksum_address(token_address), self.WBNB, self.USDT]
                swap_method = 'swapExactTokensForTokens'
            
            # Проверяем существование пула ликвидности
            has_pool, pair_address = self._check_liquidity_pool(token_address, target_token)
            if not has_pool:
                self.log(f"[ERROR] Пул ликвидности для {settings['name']} -> {settings['target']} не найден", "ERROR")
                self.log(f"💡 Токен не торгуется на PancakeSwap или пул не создан", "INFO")
                return
            
            self.log(f"[OK] Пул ликвидности найден: {pair_address}", "SUCCESS")
            
            # Получаем Router контракт
            router_contract = self.web3.eth.contract(
                address=self.PANCAKE_ROUTER,
                abi=PANCAKE_ROUTER_ABI
            )
            
            # Проверяем и выполняем approve через сервис при наличии
            self.log(f"📝 Проверка approve для {settings['name']}...", "INFO")
            if hasattr(self, '_dex_service') and self._dex_service:
                try:
                    # Быстрая проверка allowance
                    token_contract = self.web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
                    current_allowance = token_contract.functions.allowance(self.account.address, self.PANCAKE_ROUTER).call()
                    if current_allowance < amount_wei:
                        self.log("🔑 Выполняем approve через сервис", "INFO")
                        approve_hash = self._dex_service.approve(token_address)
                        self.log(f"[SEND] Approve tx: {approve_hash}", "INFO")
                        receipt = self.web3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
                        if not (receipt and receipt.get('status') == 1):
                            raise Exception("Approve транзакция не подтверждена")
                except Exception as e:  # noqa: BLE001
                    self.log(f"[WARN] Ошибка approve через сервис, fallback к локальному: {e}", "WARNING")
                    if not self._check_and_approve(token_address, amount_wei):
                        raise Exception(f"Не удалось выполнить approve (fallback) для {settings['name']}")
            else:
                if not self._check_and_approve(token_address, amount_wei):
                    raise Exception(f"Не удалось выполнить approve для {settings['name']}")
            
            # Получаем ожидаемый выход с retry
            self.log("[SEARCH] Расчет выходного количества...", "INFO")
            self.log(f"[SEARCH] Путь обмена: {' -> '.join(path)}", "INFO")
            self.log(f"[SEARCH] Количество для обмена: {amount_wei}", "INFO")
            amounts_out = self._get_amounts_out_with_retry(amount_wei, path)
            
            if not amounts_out or amounts_out[-1] == 0:
                raise Exception("Не удалось рассчитать выходное количество. Проверьте ликвидность пула.")
                
            expected_out = amounts_out[-1]
            
            # Правильно рассчитываем количество токенов в зависимости от целевого токена
            if settings['target'] == 'BNB':
                expected_tokens = expected_out / (10 ** 18)  # BNB имеет 18 decimals
            else:  # USDT
                expected_tokens = expected_out / (10 ** 6)   # USDT имеет 6 decimals
            
            self.log(f"[SEARCH] Ожидается получить: {expected_tokens:.6f} {settings['target']}", "INFO")
            
            # Расчет slippage
            slippage = settings.get('slippage', 1) / 100
            min_amount_out = int(expected_out * (1 - slippage))
            self.log(f"[SEARCH] Минимальный выход (slippage {slippage*100}%): {min_amount_out}", "INFO")
            
            # Проверяем, что минимальный выход больше 0
            if min_amount_out <= 0:
                raise Exception(f"Минимальный выход слишком мал: {min_amount_out}")
            
            # Deadline через 20 минут
            deadline = int(time.time()) + 1200
            self.log(f"[SEARCH] Deadline: {deadline}", "INFO")
            
            # Выполняем swap через сервис если доступен
            self.log(f"[SEND] Отправка swap: {amount} {settings['name']} -> {settings['target']}", "INFO")
            swap_hash = None
            if hasattr(self, '_dex_service') and self._dex_service:
                try:
                    if swap_method == 'swapExactTokensForETH':
                        swap_hash = self._dex_service.swap_exact_tokens_for_eth(amount_wei, min_amount_out, path)
                    else:
                        swap_hash = self._dex_service.swap_exact_tokens_for_tokens(amount_wei, min_amount_out, path)
                    self.log(f"[SEND] Swap tx: {swap_hash}", "INFO")
                except Exception as e:  # noqa: BLE001
                    error_str = str(e)
                    # Специальная обработка ошибки недостатка газа
                    if 'insufficient funds' in error_str:
                        self.log(f"⛽ Недостаточно BNB для газа: {error_str}", "ERROR")
                        self.log("⏸️ Приостанавливаем мониторинг из-за нехватки газа", "WARNING")
                        # Не останавливаем полностью, но логируем критическую ошибку
                        raise Exception(f"Недостаточно BNB для газа: {error_str}")
                    else:
                        self.log(f"[WARN] Ошибка swap через сервис: {e}. Fallback к локальному пути", "WARNING")
            if not swap_hash:
                # Fallback локальная отправка - используем обычный механизм получения nonce
                reserved_nonce = None
                try:
                    # Получаем текущий nonce без резервирования через менеджер
                    reserved_nonce = self.web3.eth.get_transaction_count(self.account.address, 'pending')
                    self.log(f"[SEARCH] Используем nonce из сети: {reserved_nonce}", "INFO")
                except Exception as e:  # noqa: BLE001
                    self.log(f"[WARN] Не удалось получить nonce: {e}", "WARNING")
                    # КРИТИЧЕСКОЕ: Если не можем получить nonce, не продолжаем
                    raise Exception(f"Критическая ошибка nonce: {e}")
                if swap_method == 'swapExactTokensForETH':
                    swap_tx = router_contract.functions.swapExactTokensForETH(
                        amount_wei, min_amount_out, path, self.account.address, deadline
                    ).build_transaction({
                        'from': self.account.address,
                        'gas': 300000,
                        'gasPrice': 5000000000,  # 5 gwei
                        'nonce': reserved_nonce if reserved_nonce is not None else self.web3.eth.get_transaction_count(self.account.address, 'pending'),
                    })
                else:
                    swap_tx = router_contract.functions.swapExactTokensForTokens(
                        amount_wei, min_amount_out, path, self.account.address, deadline
                    ).build_transaction({
                        'from': self.account.address,
                        'gas': 300000,
                        'gasPrice': 5000000000,  # 5 gwei
                        'nonce': reserved_nonce if reserved_nonce is not None else self.web3.eth.get_transaction_count(self.account.address, 'pending'),
                    })
                self.log(f"[SEARCH] Gas: {swap_tx['gas']}, GasPrice: {swap_tx['gasPrice']}", "INFO")
                self.log(f"[SEARCH] Nonce: {swap_tx['nonce']}", "INFO")
                signed_swap = self.web3.eth.account.sign_transaction(swap_tx, self.account.key)
                raw_hash = self.web3.eth.send_raw_transaction(signed_swap.rawTransaction)
                swap_hash = raw_hash.hex()
            # Убеждаемся что swap_hash - строка
            if not swap_hash:
                raise Exception("Не удалось выполнить swap")
            if isinstance(swap_hash, bytes):
                swap_hash = swap_hash.hex()
            
            self.log(f"[SEND] Swap транзакция отправлена: {swap_hash}", "INFO")
            self.log(f"[CONNECT] Ссылка: https://bscscan.com/tx/{swap_hash}", "INFO")
            
            # Ждем подтверждения
            self.log("⏳ Ожидание подтверждения транзакции...", "INFO")
            # Конвертируем hex строку обратно в bytes если нужно
            if isinstance(swap_hash, str):
                receipt = self.web3.eth.wait_for_transaction_receipt(swap_hash, timeout=60)
            else:
                receipt = self.web3.eth.wait_for_transaction_receipt(swap_hash, timeout=60)
            
            if receipt and receipt['status'] == 1:
                gas_used = receipt['gasUsed']
                # Получаем газ цену из receipt или используем текущую
                try:
                    gas_price_used = receipt.get('effectiveGasPrice') or 5000000000  # 5 gwei default
                except Exception:
                    gas_price_used = 5000000000  # 5 gwei default
                gas_cost_bnb = self.web3.from_wei(gas_used * gas_price_used, 'ether')
                
                self.log(f"[OK] Продажа успешна!", "SALE")
                if self.nonce_manager and self._last_nonce_ticket:
                    try:
                        self.nonce_manager.confirm(self._last_nonce_ticket)
                    except Exception as e:  # noqa: BLE001
                        self.log(f"[WARN] Не удалось confirm nonce ticket: {e}", "WARNING")
                self.log(f"[SEARCH] Gas used: {gas_used}", "INFO")
                self.log(f"[MONEY] Стоимость газа: {gas_cost_bnb:.6f} BNB", "INFO")
                
                # Проверяем новый баланс с задержкой
                time.sleep(3)
                if settings['target'] == 'BNB':
                    new_balance = self.web3.from_wei(self.web3.eth.get_balance(self.account.address), 'ether')
                    self.log(f"[MONEY] Новый баланс BNB: {new_balance:.6f}", "PROFIT")
                else:  # USDT
                    usdt_contract = self.web3.eth.contract(address=self.USDT, abi=ERC20_ABI)
                    new_balance_wei = usdt_contract.functions.balanceOf(self.account.address).call()
                    new_balance = new_balance_wei / (10 ** 6)  # USDT decimals
                    self.log(f"[MONEY] Новый баланс USDT: {new_balance:.4f}", "PROFIT")
                
                # Проверяем сколько получили
                if expected_tokens > 0:
                    actual_percentage = (new_balance / expected_tokens) * 100
                    self.log(f"[STATS] Получено {actual_percentage:.1f}% от ожидаемого", "PROFIT")
            else:
                self.log("[ERROR] Swap транзакция провалилась", "ERROR")
                if self.nonce_manager and self._last_nonce_ticket:
                    try:
                        self.nonce_manager.fail(self._last_nonce_ticket, 'swap failed status')
                    except Exception as e:  # noqa: BLE001
                        self.log(f"[WARN] Не удалось fail nonce ticket: {e}", "WARNING")
                if receipt:
                    self.log(f"[ERROR] Receipt status: {receipt.get('status')}", "ERROR")
                    if 'logs' in receipt and receipt['logs']:
                        self.log(f"[ERROR] Logs: {receipt['logs']}", "ERROR")
                return
            
            if receipt and receipt['status'] == 1:
                # Добавляем в историю
                self._add_to_history({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'token': settings['name'],
                    'amount': amount,
                    'received': amounts_out[-1] / (10 ** (18 if settings['target'] == 'BNB' else 18)),
                    'target': settings['target'],
                    'tx_hash': swap_hash,
                    'status': 'Успешно'
                })
                
                self.log(f"[OK] Продажа выполнена: {amount:.4f} {settings['name']} -> {amounts_out[-1] / (10 ** 18):.4f} {settings['target']}", "SALE")
                
                # Сигнал о завершении продажи
                self.sale_completed.emit({
                    'token': settings['name'],
                    'amount': amount,
                    'received': amounts_out[-1] / (10 ** 18),
                    'tx_hash': swap_hash
                })
            else:
                self.log(f"[ERROR] Транзакция не удалась: {swap_hash}", "ERROR")
                self._add_to_history({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'token': settings['name'],
                    'amount': amount,
                    'received': 0,
                    'target': settings['target'],
                    'tx_hash': swap_hash,
                    'status': 'Ошибка'
                })
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.log(f"[ERROR] Ошибка продажи {settings['name']} через {execution_time:.2f}с: {str(e)}", "ERROR")
            
            # Проверяем на тайм-аут
            if execution_time > 120:  # 2 минуты
                self.log(f"⏰ ВНИМАНИЕ: Операция заняла {execution_time:.2f}с - возможно зависание!", "WARNING")
            
            # КРИТИЧЕСКАЯ ОЧИСТКА: Обязательно освобождаем nonce билет при ошибке
            if self.nonce_manager and self._last_nonce_ticket and self._last_nonce_ticket.status == NonceStatus.RESERVED:
                try:
                    self.nonce_manager.fail(self._last_nonce_ticket, str(e))
                    self.log(f"🔓 Nonce билет освобожден после ошибки: {self._last_nonce_ticket.nonce}", "INFO")
                except Exception as fail_error:
                    self.log(f"🚨 КРИТИЧЕСКАЯ ОШИБКА: Не удалось освободить nonce билет: {fail_error}", "ERROR")
                    # Пытаемся принудительно очистить билет
                    try:
                        self._last_nonce_ticket.status = NonceStatus.FAILED
                        self._last_nonce_ticket.error = f"Force cleanup: {str(e)}"
                    except Exception:
                        pass
            self._add_to_history({
                'time': datetime.now().strftime("%H:%M:%S"),
                'token': settings['name'],
                'amount': amount,
                'received': 0,
                'target': settings['target'],
                'tx_hash': '',
                'status': f'Ошибка: {str(e)[:50]}'
            })
        finally:
            # ФИНАЛЬНАЯ ОЧИСТКА: Обеспечиваем освобождение ресурсов
            execution_time = time.time() - start_time
            self.log(f"⏱️ Операция продажи завершена за {execution_time:.2f}с", "INFO")
            
            # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: Убеждаемся что nonce билет не висит
            if hasattr(self, '_last_nonce_ticket') and self._last_nonce_ticket:
                if self._last_nonce_ticket.status == NonceStatus.RESERVED:
                    self.log(f"[WARN] ВНИМАНИЕ: Nonce билет все еще зарезервирован! Принудительная очистка...", "WARNING")
                    try:
                        if self.nonce_manager:
                            self.nonce_manager.fail(self._last_nonce_ticket, "Force cleanup in finally")
                    except Exception:
                        pass
                # Очищаем ссылку на билет
                self._last_nonce_ticket = None
    
    def _add_to_history(self, sale_info: dict):
        """Добавление записи в историю продаж"""
        self.sales_history.append(sale_info)
        
        # Добавляем в таблицу
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        self.history_table.setItem(row, 0, QTableWidgetItem(sale_info['time']))
        self.history_table.setItem(row, 1, QTableWidgetItem(sale_info['token']))
        self.history_table.setItem(row, 2, QTableWidgetItem(f"{sale_info['amount']:.4f}"))
        self.history_table.setItem(row, 3, QTableWidgetItem(f"{sale_info['received']:.4f} {sale_info['target']}"))
        self.history_table.setItem(row, 4, QTableWidgetItem(sale_info['tx_hash'][:10] + '...'))
        
        status_item = QTableWidgetItem(sale_info['status'])
        if sale_info['status'] == 'Успешно':
            status_item.setForeground(QColor(0, 255, 0))
        else:
            status_item.setForeground(QColor(255, 0, 0))
        self.history_table.setItem(row, 5, status_item)
        
        # Прокручиваем к новой записи
        self.history_table.scrollToBottom()
    
    def _get_token_balance(self, token_address: str) -> float:
        """Получение баланса токена с усиленной защитой от ошибок"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Базовые проверки
                if not self.account or not self.web3:
                    if attempt == 0:  # Логируем только в первый раз
                        self.log("[ERROR] Кошелек или Web3 не подключен", "ERROR")
                    return 0
                
                # Проверяем подключение к сети с retry
                try:
                    if not self.web3.is_connected():
                        if attempt == 0:
                            self.log("[WARN] Нет подключения к BSC сети - попытка переподключения", "WARNING")
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                except Exception as conn_error:
                    if attempt == max_retries - 1:
                        self.log(f"[ERROR] Критическая ошибка подключения: {conn_error}", "ERROR")
                    return 0
                
                # Проверяем адрес токена
                if not Web3.is_address(token_address):
                    if attempt == 0:
                        self.log(f"[ERROR] Неверный адрес токена: {token_address}", "ERROR")
                    return 0
                
                # Проверяем, что адрес токена валидный
                checksum_address = Web3.to_checksum_address(token_address)
                
                # Проверяем, что контракт существует
                try:
                    code = self.web3.eth.get_code(checksum_address)
                    if code == b'':
                        if attempt == 0:
                            self.log(f"[ERROR] Контракт не найден по адресу: {checksum_address}", "ERROR")
                        return 0
                except Exception as e:
                    if attempt == max_retries - 1:
                        self.log(f"[ERROR] Ошибка проверки контракта: {str(e)}", "ERROR")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                
                # Создаем контракт
                token_contract = self.web3.eth.contract(
                    address=checksum_address,
                    abi=ERC20_ABI
                )
                
                # Получаем decimals
                try:
                    decimals = token_contract.functions.decimals().call()
                except Exception as e:
                    if attempt == 0:
                        self.log(f"[WARN] Ошибка получения decimals: {str(e)}, используем 18", "WARNING")
                    decimals = 18  # Fallback на стандартные 18 decimals
                
                # Получаем баланс
                wallet_address = Web3.to_checksum_address(self.account.address)
                try:
                    balance = token_contract.functions.balanceOf(wallet_address).call()
                except Exception as e:
                    if attempt == max_retries - 1:
                        self.log(f"[ERROR] Ошибка получения баланса: {str(e)}", "ERROR")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                
                # Конвертируем в читаемый формат
                formatted_balance = balance / (10 ** decimals)
                
                # Логируем только если баланс больше 0 или есть ошибки
                if formatted_balance > 0 and attempt == 0:
                    self.log(f"[OK] Баланс {checksum_address[:10]}...: {formatted_balance:.6f}", "SUCCESS")
                
                return formatted_balance
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.log(f"[ERROR] Критическая ошибка получения баланса {token_address} (попытка {attempt + 1}/{max_retries}): {str(e)}", "ERROR")
                else:
                    self.log(f"[WARN] Ошибка получения баланса (попытка {attempt + 1}/{max_retries}): {str(e)[:50]}...", "WARNING")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                
        # Если все попытки неудачны
        return 0
    
    def _get_token_name(self, token_address: str) -> str:
        """Получение имени токена"""
        try:
            if not self.web3:
                return "Unknown"
            
            token_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            return token_contract.functions.symbol().call()
            
        except Exception:
            return "Unknown"
    
    def get_gas_price_wei(self) -> int:
        """Получение цены газа в wei из настроек интерфейса"""
        try:
            # Получаем значение из интерфейса (в gwei)
            gas_price_gwei = self.gas_price_input.value()
            # Конвертируем в wei
            gas_price_wei = self.web3.to_wei(gas_price_gwei, 'gwei')
            return gas_price_wei
        except Exception:
            # Если ошибка - возвращаем дефолтное значение 5 gwei
            return self.web3.to_wei(5, 'gwei')
    
    def _get_token_price(self, token_address: str, target: str) -> float:
        """Получение цены токена (упрощенная версия)"""
        try:
            if not self.web3:
                return 0
            
            router_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.PANCAKE_ROUTER),
                abi=PANCAKE_ROUTER_ABI
            )
            
            # Получаем цену за 1 токен
            amount_in = 10 ** 18  # 1 токен
            
            if target == 'BNB':
                path = [token_address, self.WBNB]
            else:
                path = [token_address, self.WBNB, self.USDT]
            
            amounts_out = router_contract.functions.getAmountsOut(amount_in, path).call()
            
            return amounts_out[-1] / (10 ** 18)
            
        except Exception:
            return 0
    
    def update_balance_display(self):
        """Обновление отображения балансов"""
        if not self.account or not self.web3:
            return
        
        try:
            # Получаем баланс BNB
            bnb_balance = self.web3.eth.get_balance(self.account.address)
            bnb_formatted = self.web3.from_wei(bnb_balance, 'ether')
            
            # Обновляем BNB баланс в интерфейсе
            self.bnb_balance_label.setText(f"BNB: {bnb_formatted:.6f}")
            
            info_text = f"[MONEY] BNB: {bnb_formatted:.6f}\n"
            
            # Обновляем балансы отслеживаемых токенов
            for token_address, settings in self.monitored_tokens.items():
                balance = self._get_token_balance(token_address)
                info_text += f"🪙 {settings['name']}: {balance:.4f}\n"
                
                # Обновляем в таблице
                for row in range(self.monitored_table.rowCount()):
                    if self.monitored_table.item(row, 0).text() == settings['name']:
                        self.monitored_table.setItem(row, 4, QTableWidgetItem(f"{balance:.4f}"))
                        break
            
            self.balance_info.setText(info_text)
            
            # Обновляем текущий баланс выбранного токена
            self._update_current_balance()
            
        except Exception as e:
            self.log(f"Ошибка обновления баланса: {str(e)}", "ERROR")
    
    def test_sell(self):
        """Тестовая продажа (симуляция)"""
        if not self.account:
            QMessageBox.warning(self, "Ошибка", "Сначала подключите кошелек!")
            return
        
        # Получаем настройки
        if self.token_combo.currentText() == "PLEX ONE":
            token_address = self.PLEX_ONE
            token_name = "PLEX ONE"
        else:
            token_address = self.custom_token_input.text().strip()
            if not Web3.is_address(token_address):
                QMessageBox.warning(self, "Ошибка", "Неверный адрес токена!")
                return
            token_name = self._get_token_name(token_address)
        
        # Получаем баланс
        balance = self._get_token_balance(token_address)
        
        if balance <= 0:
            QMessageBox.warning(self, "Ошибка", f"Нет баланса {token_name} для продажи!")
            return
        
        # Рассчитываем количество для продажи
        sell_mode = self.sell_mode_combo.currentText()
        if sell_mode == "Процент от баланса":
            sell_amount = balance * (self.sell_percentage.value() / 100)
            sell_display = f"{self.sell_percentage.value()}% от баланса ({sell_amount:.4f})"
        else:
            sell_amount = min(self.sell_quantity.value(), balance)
            sell_display = f"{sell_amount:.4f} токенов"
        
        # Спрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Выполнить тестовую продажу?\n\n"
            f"Токен: {token_name}\n"
            f"Баланс: {balance:.4f}\n"
            f"Режим: {sell_mode}\n"
            f"Продать: {sell_display}\n"
            f"В: {self.target_combo.currentText()}\n"
            f"Slippage: {self.slippage_input.value()}%",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            settings = {
                'name': token_name,
                'threshold': 0,
                'target': self.target_combo.currentText(),
                'sell_mode': sell_mode,
                'sell_type': 'percentage' if sell_mode == "Процент от баланса" else 'quantity',
                'sell_amount': self.sell_percentage.value() if sell_mode == "Процент от баланса" else self.sell_quantity.value(),
                'percentage': self.sell_percentage.value(),
                'quantity': self.sell_quantity.value(),
                'min_price': 0,
                'slippage': self.slippage_input.value(),
                'cyclic_sales': self.cyclic_sales_checkbox.isChecked(),
                'last_sale_time': 0
            }
            
            self._execute_sell(token_address, sell_amount, settings)
