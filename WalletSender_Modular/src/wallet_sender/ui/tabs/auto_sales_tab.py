"""
Вкладка автоматических продаж токенов через PancakeSwap
"""

import threading
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QProgressBar,
    QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QFormLayout,
    QCheckBox, QRadioButton, QButtonGroup, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt5.QtGui import QFont, QColor

from web3 import Web3
from eth_account import Account

from .base_tab import BaseTab
from ...constants import CONTRACTS
from ...utils.logger import get_logger

logger = get_logger(__name__)

try:
    from mnemonic import Mnemonic
except ImportError:
    Mnemonic = None
    logger.warning("Библиотека mnemonic не установлена")

# PancakeSwap Router V2 ABI (упрощенный)
PANCAKE_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
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

# ERC20 ABI для approve и balanceOf
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
]


class AutoSalesTab(BaseTab):
    """Вкладка автоматических продаж токенов"""
    
    transaction_completed = pyqtSignal(dict)
    balance_updated = pyqtSignal(dict)
    
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        
        # Состояние продаж
        self.is_selling = False
        self.stop_selling = False
        self.selling_thread = None
        
        # Web3 и аккаунт
        self.web3 = None
        self.account = None
        self.balances = {}
        
        # Инициализация Web3
        self._init_web3()
        
        # Таймер для обновления балансов
        self.balance_timer = QTimer()
        self.balance_timer.timeout.connect(self.update_balances)
        
    def _init_web3(self):
        """Инициализация Web3 подключения"""
        try:
            # BSC Mainnet RPC
            rpc_url = 'https://bsc-dataseed.binance.org/'
            self.web3 = Web3(Web3.HTTPProvider(rpc_url))
            
            if self.web3.is_connected():
                self.log("✅ Подключение к BSC установлено", "SUCCESS")
            else:
                self.log("❌ Не удалось подключиться к BSC", "ERROR")
                
        except Exception as e:
            self.log(f"❌ Ошибка инициализации Web3: {str(e)}", "ERROR")
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QGroupBox("💰 Автоматические продажи токенов")
        header_layout = QVBoxLayout(header)
        header_label = QLabel("Автоматическая продажа токенов через PancakeSwap DEX")
        header_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        header_layout.addWidget(header_label)
        layout.addWidget(header)
        
        # Группа подключения кошелька
        wallet_group = self._create_wallet_group()
        layout.addWidget(wallet_group)
        
        # Группа отображения балансов
        balance_group = self._create_balance_group()
        layout.addWidget(balance_group)
        
        # Настройки продажи
        sales_group = self._create_sales_settings_group()
        layout.addWidget(sales_group)
        
        # Группа настроек газа
        gas_group = self.create_gas_settings_group()
        layout.addWidget(gas_group)
        
        # Кнопки управления
        control_layout = QHBoxLayout()
        
        self.start_sales_btn = QPushButton("🚀 Начать автопродажи")
        self.start_sales_btn.clicked.connect(self.start_auto_sales)
        self.start_sales_btn.setEnabled(False)
        control_layout.addWidget(self.start_sales_btn)
        
        self.stop_sales_btn = QPushButton("⏹️ Остановить")
        self.stop_sales_btn.clicked.connect(self.stop_auto_sales)
        self.stop_sales_btn.setEnabled(False)
        control_layout.addWidget(self.stop_sales_btn)
        
        layout.addLayout(control_layout)
        
        # Прогресс и статистика
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # История продаж
        history_group = self._create_history_group()
        layout.addWidget(history_group)
        
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
        
        # Поле ввода
        self.wallet_input = QTextEdit()
        self.wallet_input.setPlaceholderText("Введите SEED фразу или приватный ключ...")
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
        layout = QFormLayout()
        
        # Метки для балансов
        self.bnb_balance_label = QLabel("0.0")
        self.bnb_balance_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addRow("BNB:", self.bnb_balance_label)
        
        self.plex_balance_label = QLabel("0.0")
        self.plex_balance_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addRow("PLEX ONE:", self.plex_balance_label)
        
        self.usdt_balance_label = QLabel("0.0")
        self.usdt_balance_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addRow("USDT:", self.usdt_balance_label)
        
        # Кнопка обновления балансов
        self.refresh_btn = QPushButton("🔄 Обновить балансы")
        self.refresh_btn.clicked.connect(self.update_balances)
        self.refresh_btn.setEnabled(False)
        layout.addRow(self.refresh_btn)
        
        group.setLayout(layout)
        return group
        
    def _create_sales_settings_group(self) -> QGroupBox:
        """Создание группы настроек продажи"""
        group = QGroupBox("Настройки автопродаж")
        layout = QFormLayout()
        
        # Выбор токена для продажи
        self.sell_token_combo = QComboBox()
        self.sell_token_combo.addItems(["PLEX ONE", "USDT", "Другой токен..."])
        self.sell_token_combo.currentTextChanged.connect(self._on_sell_token_changed)
        layout.addRow("Продавать токен:", self.sell_token_combo)
        
        # Поле для пользовательского токена
        self.custom_sell_token_input = QLineEdit()
        self.custom_sell_token_input.setPlaceholderText("Введите адрес токена для продажи...")
        self.custom_sell_token_input.setVisible(False)
        layout.addRow("Адрес токена:", self.custom_sell_token_input)
        
        # Выбор валюты покупки
        self.buy_currency_combo = QComboBox()
        self.buy_currency_combo.addItems(["BNB", "USDT", "PLEX ONE", "Другая валюта..."])
        self.buy_currency_combo.currentTextChanged.connect(self._on_buy_currency_changed)
        layout.addRow("Получать валюту:", self.buy_currency_combo)
        
        # Поле для пользовательской валюты
        self.custom_buy_currency_input = QLineEdit()
        self.custom_buy_currency_input.setPlaceholderText("Введите адрес валюты для получения...")
        self.custom_buy_currency_input.setVisible(False)
        layout.addRow("Адрес валюты:", self.custom_buy_currency_input)
        
        # Сумма продажи
        self.sell_amount_input = QDoubleSpinBox()
        self.sell_amount_input.setRange(0.00000001, 1000000)
        self.sell_amount_input.setDecimals(8)
        self.sell_amount_input.setValue(10.0)
        layout.addRow("Сумма для продажи:", self.sell_amount_input)
        
        # Интервал между продажами
        self.sell_interval_input = QSpinBox()
        self.sell_interval_input.setRange(5, 3600)
        self.sell_interval_input.setValue(60)
        self.sell_interval_input.setSuffix(" сек")
        layout.addRow("Интервал между продажами:", self.sell_interval_input)
        
        # Максимальное количество продаж
        self.max_sales_input = QSpinBox()
        self.max_sales_input.setRange(1, 1000)
        self.max_sales_input.setValue(10)
        layout.addRow("Максимум продаж:", self.max_sales_input)
        
        # Slippage tolerance
        self.slippage_input = QDoubleSpinBox()
        self.slippage_input.setRange(0.1, 50.0)
        self.slippage_input.setValue(2.0)
        self.slippage_input.setSuffix(" %")
        layout.addRow("Slippage tolerance:", self.slippage_input)
        
        group.setLayout(layout)
        return group
        
    def _create_history_group(self) -> QGroupBox:
        """Создание группы истории продаж"""
        group = QGroupBox("История автопродаж")
        layout = QVBoxLayout()
        
        # Таблица истории
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Время", "Продано", "Получено", "Сумма", "Tx Hash", "Статус"
        ])
        
        # Настройка таблицы
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(True)
        
        layout.addWidget(self.history_table)
        
        group.setLayout(layout)
        return group
        
    def _on_sell_token_changed(self, token: str):
        """Обработка изменения токена для продажи"""
        is_custom = token == "Другой токен..."
        self.custom_sell_token_input.setVisible(is_custom)
        
    def _on_buy_currency_changed(self, currency: str):
        """Обработка изменения валюты покупки"""
        is_custom = currency == "Другая валюта..."
        self.custom_buy_currency_input.setVisible(is_custom)
        
    def connect_wallet(self):
        """Подключение кошелька"""
        if not self.web3 or not self.web3.is_connected():
            self.log("❌ Нет подключения к BSC", "ERROR")
            return
            
        wallet_input = self.wallet_input.toPlainText().strip()
        
        if not wallet_input:
            self.log("❌ Введите SEED фразу или приватный ключ", "ERROR")
            return
            
        try:
            if self.seed_radio.isChecked():
                # Подключение через SEED фразу
                if not Mnemonic:
                    self.log("❌ Библиотека mnemonic не установлена", "ERROR")
                    return
                    
                mnemo = Mnemonic("english")
                if not mnemo.check(wallet_input):
                    self.log("❌ Неверная SEED фраза", "ERROR")
                    return
                    
                # Получение приватного ключа из seed
                seed = mnemo.to_seed(wallet_input)
                private_key = seed[:32].hex()
                
            else:
                # Подключение через приватный ключ
                private_key = wallet_input
                if private_key.startswith('0x'):
                    private_key = private_key[2:]
                    
            # Создание аккаунта
            self.account = Account.from_key(private_key)
            
            # Обновление интерфейса
            self.wallet_address_label.setText(f"Адрес: {self.account.address}")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.start_sales_btn.setEnabled(True)
            
            self.log(f"✅ Кошелек подключен: {self.account.address}", "SUCCESS")
            
            # Обновление балансов
            self.update_balances()
            
        except Exception as e:
            logger.error(f"Ошибка подключения кошелька: {e}")
            self.log(f"❌ Ошибка подключения: {str(e)}", "ERROR")

    def disconnect_wallet(self):
        """Отключение кошелька"""
        # Остановка продаж если активны
        if self.is_selling:
            self.stop_auto_sales()
            
        self.account = None
        self.balances = {}
        
        # Остановка таймера
        self.balance_timer.stop()
        
        # Очистка поля ввода
        self.wallet_input.clear()
        
        # Обновление интерфейса
        self.wallet_address_label.setText("Адрес: Не подключен")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.start_sales_btn.setEnabled(False)
        
        # Сброс балансов
        self.bnb_balance_label.setText("0.0")
        self.plex_balance_label.setText("0.0")
        self.usdt_balance_label.setText("0.0")
        
        self.log("🔌 Кошелек отключен", "INFO")

    def update_balances(self):
        """Обновление балансов токенов"""
        if not self.account or not self.web3:
            return
            
        try:
            address = self.account.address
            
            # Получение баланса BNB
            bnb_balance = self.web3.eth.get_balance(address)
            bnb_formatted = self.web3.from_wei(bnb_balance, 'ether')
            
            # Получение баланса PLEX ONE
            plex_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(CONTRACTS['PLEX_ONE']),
                abi=ERC20_ABI
            )
            plex_balance = plex_contract.functions.balanceOf(address).call()
            plex_decimals = plex_contract.functions.decimals().call()
            plex_formatted = plex_balance / (10 ** plex_decimals)
            
            # Получение баланса USDT
            usdt_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(CONTRACTS['USDT']),
                abi=ERC20_ABI
            )
            usdt_balance = usdt_contract.functions.balanceOf(address).call()
            usdt_decimals = usdt_contract.functions.decimals().call()
            usdt_formatted = usdt_balance / (10 ** usdt_decimals)
            
            # Обновление интерфейса
            self.bnb_balance_label.setText(f"{float(bnb_formatted):.6f}")
            self.plex_balance_label.setText(f"{float(plex_formatted):.2f}")
            self.usdt_balance_label.setText(f"{float(usdt_formatted):.2f}")
            
            # Сохранение балансов
            self.balances = {
                'bnb': float(bnb_formatted),
                'plex': float(plex_formatted),
                'usdt': float(usdt_formatted)
            }
            
        except Exception as e:
            logger.error(f"Ошибка обновления балансов: {e}")
            self.log(f"❌ Ошибка обновления балансов: {str(e)}", "ERROR")

    def start_auto_sales(self):
        """Начать автоматические продажи"""
        if self.is_selling:
            self.log("⚠️ Автопродажи уже запущены!", "WARNING")
            return
            
        if not self.account:
            self.log("❌ Кошелек не подключен!", "ERROR")
            return
            
        # Валидация настроек
        if not self._validate_sales_settings():
            return
            
        # Получение настроек
        sell_token = self._get_sell_token_address()
        buy_currency = self._get_buy_currency_address()
        amount = self.sell_amount_input.value()
        interval = self.sell_interval_input.value()
        max_sales = self.max_sales_input.value()
        
        # Проверка на продажу токена самого в себя
        if sell_token.lower() == buy_currency.lower():
            self.log("❌ Нельзя продавать токен сам в себя!", "ERROR")
            return
            
        self.log(f"🚀 Начинаем автопродажи", "SUCCESS")
        self.log(f"📊 Продаем: {self.sell_token_combo.currentText()}", "INFO")
        self.log(f"📊 Получаем: {self.buy_currency_combo.currentText()}", "INFO")
        self.log(f"📊 Сумма: {amount}, интервал: {interval}с, макс: {max_sales}", "INFO")
        
        # Настройка UI
        self.is_selling = True
        self.stop_selling = False
        self.start_sales_btn.setEnabled(False)
        self.stop_sales_btn.setEnabled(True)
        
        # Запуск потока продаж
        self.selling_thread = threading.Thread(
            target=self._auto_sales_worker,
            args=(sell_token, buy_currency, amount, interval, max_sales),
            daemon=False
        )
        self.selling_thread.start()
        
    def _auto_sales_worker(self, sell_token: str, buy_currency: str, amount: float, interval: int, max_sales: int):
        """Рабочий поток автоматических продаж"""
        sales_count = 0
        
        try:
            self.log(f"💼 Запущен поток автопродаж", "INFO")
            
            while sales_count < max_sales and not self.stop_selling:
                try:
                    # Выполнение продажи
                    self.log(f"🛒 Выполняется продажа #{sales_count + 1}/{max_sales}", "INFO")
                    
                    # Определяем тип обмена
                    if buy_currency.lower() == Web3.to_checksum_address(CONTRACTS['WBNB']).lower():
                        # Продажа токена за BNB
                        result = self._sell_token_for_bnb(sell_token, amount)
                    else:
                        # Продажа токена за другой токен
                        result = self._sell_token_for_token(sell_token, buy_currency, amount)
                        
                    if result and result.get('success'):
                        sales_count += 1
                        tx_hash = result.get('tx_hash', '')
                        
                        # Добавление в историю
                        self._add_to_history(
                            self.sell_token_combo.currentText(),
                            self.buy_currency_combo.currentText(),
                            amount,
                            tx_hash,
                            "Успешно"
                        )
                        
                        self.log(f"✅ Продажа #{sales_count} успешна: {tx_hash[:20]}...", "SUCCESS")
                    else:
                        error = result.get('error', 'Неизвестная ошибка') if result else 'Нет результата'
                        self._add_to_history(
                            self.sell_token_combo.currentText(),
                            self.buy_currency_combo.currentText(),
                            amount,
                            "",
                            f"Ошибка: {error}"
                        )
                        self.log(f"❌ Ошибка продажи: {error}", "ERROR")
                        
                except Exception as e:
                    self.log(f"❌ Исключение в продаже: {str(e)}", "ERROR")
                    logger.exception("Ошибка в _auto_sales_worker")
                    
                # Ожидание до следующей продажи
                if sales_count < max_sales and not self.stop_selling:
                    self.log(f"⏳ Ожидание {interval} секунд до следующей продажи", "INFO")
                    time.sleep(interval)
                    
            self.log(f"🏁 Автопродажи завершены! Выполнено: {sales_count}/{max_sales}", "SUCCESS")
            
        except Exception as e:
            self.log(f"💥 Критическая ошибка в автопродажах: {str(e)}", "ERROR")
            logger.exception("Критическая ошибка в _auto_sales_worker")
            
        finally:
            # Завершение работы
            self.is_selling = False
            QTimer.singleShot(0, lambda: self._finish_auto_sales())
            
    def _finish_auto_sales(self):
        """Завершение автопродаж (в главном потоке)"""
        self.start_sales_btn.setEnabled(True)
        self.stop_sales_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
    def stop_auto_sales(self):
        """Остановить автоматические продажи"""
        if not self.is_selling:
            self.log("⚠️ Автопродажи не запущены", "WARNING")
            return
            
        self.stop_selling = True
        self.log("🛑 Остановка автопродаж...", "WARNING")
        
    def _validate_sales_settings(self) -> bool:
        """Валидация настроек продаж"""
        # Проверка токена для продажи
        if self.sell_token_combo.currentText() == "Другой токен...":
            sell_token = self.custom_sell_token_input.text().strip()
            if not sell_token or not Web3.is_address(sell_token):
                self.log("❌ Неверный адрес токена для продажи", "ERROR")
                return False
                
        # Проверка валюты покупки
        if self.buy_currency_combo.currentText() == "Другая валюта...":
            buy_currency = self.custom_buy_currency_input.text().strip()
            if not buy_currency or not Web3.is_address(buy_currency):
                self.log("❌ Неверный адрес валюты для получения", "ERROR")
                return False
                
        return True
        
    def _get_sell_token_address(self) -> str:
        """Получение адреса токена для продажи"""
        token = self.sell_token_combo.currentText()
        
        if token == "PLEX ONE":
            return Web3.to_checksum_address(CONTRACTS['PLEX_ONE'])
        elif token == "USDT":
            return Web3.to_checksum_address(CONTRACTS['USDT'])
        else:
            return Web3.to_checksum_address(self.custom_sell_token_input.text().strip())
            
    def _get_buy_currency_address(self) -> str:
        """Получение адреса валюты для покупки"""
        currency = self.buy_currency_combo.currentText()
        
        if currency == "BNB":
            return Web3.to_checksum_address(CONTRACTS['WBNB'])  # WBNB для PancakeSwap
        elif currency == "USDT":
            return Web3.to_checksum_address(CONTRACTS['USDT'])
        elif currency == "PLEX ONE":
            return Web3.to_checksum_address(CONTRACTS['PLEX_ONE'])
        else:
            return Web3.to_checksum_address(self.custom_buy_currency_input.text().strip())
            
    def _sell_token_for_bnb(self, token_address: str, amount: float) -> Dict[str, Any]:
        """Продажа токена за BNB через PancakeSwap"""
        try:
            # Создание контракта роутера
            router_address = "0x10ED43C718714eb63d5aA57B78B54704E256024E"  # PancakeSwap V2 Router
            router_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(router_address),
                abi=PANCAKE_ROUTER_ABI
            )
            
            # Получение decimals токена
            token_contract = self.web3.eth.contract(
                address=token_address,
                abi=ERC20_ABI
            )
            decimals = token_contract.functions.decimals().call()
            amount_in = int(amount * (10 ** decimals))
            
            # Approve токенов для роутера
            self._approve_token(token_address, router_address, amount_in)
            
            # Путь обмена: Token -> WBNB
            path = [token_address, Web3.to_checksum_address(CONTRACTS['WBNB'])]
            
            # Deadline (10 минут)
            deadline = int(time.time()) + 600
            
            # Минимальная сумма с учетом slippage
            slippage = self.slippage_input.value()
            amount_out_min = 0  # Упрощенно, в реальности нужно рассчитывать
            
            # Создание транзакции
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            
            transaction = router_contract.functions.swapExactTokensForETH(
                amount_in,
                amount_out_min,
                path,
                self.account.address,
                deadline
            ).build_transaction({
                'from': self.account.address,
                'gas': 300000,
                'gasPrice': self.get_gas_price_wei(),
                'nonce': nonce,
            })
            
            # Подпись и отправка
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Ожидание подтверждения
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'success': True,
                'tx_hash': tx_hash.hex(),
                'gas_used': tx_receipt['gasUsed']
            }
            
        except Exception as e:
            logger.exception(f"Ошибка продажи токена за BNB")
            return {'success': False, 'error': str(e)}
            
    def _sell_token_for_token(self, sell_token: str, buy_token: str, amount: float) -> Dict[str, Any]:
        """Продажа токена за другой токен через PancakeSwap"""
        try:
            # Аналогично _sell_token_for_bnb, но используем swapExactTokensForTokens
            router_address = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
            router_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(router_address),
                abi=PANCAKE_ROUTER_ABI
            )
            
            # Получение decimals токена
            token_contract = self.web3.eth.contract(
                address=sell_token,
                abi=ERC20_ABI
            )
            decimals = token_contract.functions.decimals().call()
            amount_in = int(amount * (10 ** decimals))
            
            # Approve токенов
            self._approve_token(sell_token, router_address, amount_in)
            
            # Путь обмена
            path = [sell_token, buy_token]
            
            # Транзакция
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            deadline = int(time.time()) + 600
            
            transaction = router_contract.functions.swapExactTokensForTokens(
                amount_in,
                0,  # amount_out_min
                path,
                self.account.address,
                deadline
            ).build_transaction({
                'from': self.account.address,
                'gas': 300000,
                'gasPrice': self.get_gas_price_wei(),
                'nonce': nonce,
            })
            
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'success': True,
                'tx_hash': tx_hash.hex(),
                'gas_used': tx_receipt['gasUsed']
            }
            
        except Exception as e:
            logger.exception(f"Ошибка продажи токена за токен")
            return {'success': False, 'error': str(e)}
            
    def _approve_token(self, token_address: str, spender: str, amount: int):
        """Разрешение трат токена"""
        token_contract = self.web3.eth.contract(
            address=token_address,
            abi=ERC20_ABI
        )
        
        nonce = self.web3.eth.get_transaction_count(self.account.address)
        
        transaction = token_contract.functions.approve(
            spender,
            amount
        ).build_transaction({
            'from': self.account.address,
            'gas': 100000,
            'gasPrice': self.get_gas_price_wei(),
            'nonce': nonce,
        })
        
        signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        self.web3.eth.wait_for_transaction_receipt(tx_hash)
        
    def _add_to_history(self, sell_token: str, buy_currency: str, amount: float, tx_hash: str, status: str):
        """Добавление записи в историю продаж"""
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        
        # Заполнение данных
        self.history_table.setItem(row, 0, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        self.history_table.setItem(row, 1, QTableWidgetItem(sell_token))
        self.history_table.setItem(row, 2, QTableWidgetItem(buy_currency))
        self.history_table.setItem(row, 3, QTableWidgetItem(f"{amount:.6f}"))
        self.history_table.setItem(row, 4, QTableWidgetItem(tx_hash[:10] + "..." if tx_hash else ""))
        
        status_item = QTableWidgetItem(status)
        if "Успешно" in status:
            status_item.setBackground(QColor(0, 100, 0))
        elif "Ошибка" in status:
            status_item.setBackground(QColor(100, 0, 0))
        self.history_table.setItem(row, 5, status_item)
        
        # Прокрутка к новой записи
        self.history_table.scrollToBottom()
