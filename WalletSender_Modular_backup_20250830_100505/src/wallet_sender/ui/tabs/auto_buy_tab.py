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

logger = get_logger(__name__)

try:
    from mnemonic import Mnemonic
except ImportError:
    Mnemonic = None
    logger.warning("Библиотека mnemonic не установлена. Установите через: pip install mnemonic")

# Адреса токенов и контрактов BSC
CONTRACTS = {
    'PLEX_ONE': '0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1',
    'USDT': '0x55d398326f99059ff775485246999027b3197955',
    'PANCAKE_ROUTER': '0x10ED43C718714eb63d5aA57B78B54704E256024E',
    'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
}

# ABI для ERC20 токенов
ERC20_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}]')

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
        self.refresh_btn.clicked.connect(self.update_balances)
        self.refresh_btn.setEnabled(False)
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
            if self.seed_radio.isChecked():
                # Обработка SEED фразы
                if Mnemonic is None:
                    QMessageBox.critical(self, "Ошибка", "Библиотека mnemonic не установлена!\nУстановите: pip install mnemonic")
                    return
                    
                words = wallet_data.split()
                if len(words) not in [12, 24]:
                    QMessageBox.warning(self, "Ошибка", "SEED фраза должна содержать 12 или 24 слова!")
                    return
                    
                mnemo = Mnemonic("english")
                if not mnemo.check(wallet_data):
                    QMessageBox.warning(self, "Ошибка", "Неверная SEED фраза!")
                    return
                    
                seed = mnemo.to_seed(wallet_data)
                private_key = seed[:32].hex()
                self.account = Account.from_key(private_key)
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
        self.start_btn.setEnabled(False)
        
        # Очищаем балансы
        self.bnb_balance_label.setText("0.0")
        self.plex_balance_label.setText("0.0")
        self.usdt_balance_label.setText("0.0")
        
        # Останавливаем авто-обновление
        self.balance_timer.stop()
        self.auto_refresh_cb.setChecked(False)
        
        self.log("🔌 Кошелек отключен", "INFO")
        
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
                    address=Web3.to_checksum_address(CONTRACTS['PLEX_ONE']),
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
                    address=Web3.to_checksum_address(CONTRACTS['USDT']),
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
            
            # Отправляем сигнал для обновления UI
            self.balance_updated.emit(self.balances)
            
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
                self.log(f"❌ Ошибка в процессе покупки: {str(e)}", "ERROR")
                time.sleep(interval)
                
        # Покупки завершены
        if self.is_buying:
            self.is_buying = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.log(f"🏁 Автоматические покупки завершены. Выполнено: {completed_buys}/{max_buys}", "SUCCESS")
            
    def _execute_buy(self) -> Dict[str, Any]:
        """Выполнение одной покупки через PancakeSwap"""
        try:
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
            
            self.log(f"🛒 Выполняется реальная покупка {selected_token} за {buy_with} через PancakeSwap...", "INFO")
            
            # Создаем контракт PancakeSwap Router
            router_address = Web3.to_checksum_address('0x10ED43C718714eb63d5aA57B78B54704E256024E')
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
                path = [
                    Web3.to_checksum_address('0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'),  # WBNB
                    Web3.to_checksum_address(token_address)
                ]
                self.log(f"🔄 Путь обмена: WBNB -> {selected_token}", "INFO")
                
                amount_wei = self.web3.to_wei(buy_amount, 'ether')
                self.log(f"💰 Сумма в wei: {amount_wei} ({buy_amount} BNB)", "INFO")
                
                # Создаем транзакцию
                transaction = router_contract.functions.swapExactETHForTokens(
                    0,  # amountOutMin = 0 (принимаем любое количество)
                    path,
                    self.account.address,
                    deadline
                ).build_transaction({
                    'from': self.account.address,
                    'value': amount_wei,
                    'gas': self.get_gas_limit(),  # Используем настройки из UI
                    'gasPrice': self.get_gas_price_wei(),
                    'nonce': self.web3.eth.get_transaction_count(self.account.address)
                })
                
            else:  # buy_with == 'USDT'
                self.log("💵 Режим покупки: USDT -> Token (approve + swapExactTokensForTokens)", "INFO")
                # Покупка за USDT (Token -> Token)
                
                # Сначала нужно сделать approve для USDT
                usdt_address = Web3.to_checksum_address(CONTRACTS['USDT'])
                self.log(f"📋 USDT адрес: {usdt_address}", "INFO")
                erc20_abi = json.loads('[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]')
                
                usdt_contract = self.web3.eth.contract(address=usdt_address, abi=erc20_abi)
                amount_in_units = int(buy_amount * (10 ** 18))
                
                # Approve транзакция
                self.log("📝 Делаем approve для USDT...", "INFO")
                approve_tx = usdt_contract.functions.approve(
                    router_address,
                    amount_in_units
                ).build_transaction({
                    'from': self.account.address,
                    'gas': self.get_gas_limit(),  # Используем настройки из UI
                    'gasPrice': self.get_gas_price_wei(),
                    'nonce': self.web3.eth.get_transaction_count(self.account.address)
                })
                
                # Подписываем и отправляем approve
                signed_approve = self.web3.eth.account.sign_transaction(approve_tx, self.account.key)
                approve_hash = self.web3.eth.send_raw_transaction(signed_approve.rawTransaction)
                approve_receipt = self.web3.eth.wait_for_transaction_receipt(approve_hash, timeout=120)
                self.log("✅ Approve успешно завершен", "INFO")
                
                # Небольшая пауза для обновления nonce в сети
                time.sleep(1)
                
                # Получаем актуальный nonce после approve (должен быть +1)
                current_nonce = self.web3.eth.get_transaction_count(self.account.address)
                self.log(f"📊 Актуальный nonce после approve: {current_nonce}", "INFO")
                
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
                
                # Создаем путь обмена: USDT -> Token
                path = [
                    usdt_address,  # USDT
                    Web3.to_checksum_address(token_address)
                ]
                
                # Создаем транзакцию (с обновленным nonce после approve)
                transaction = router_contract.functions.swapExactTokensForTokens(
                    amount_in_units,
                    0,  # amountOutMin = 0 (принимаем любое количество)
                    path,
                    self.account.address,
                    deadline
                ).build_transaction({
                    'from': self.account.address,
                    'gas': self.get_gas_limit(),  # Используем настройки из UI
                    'gasPrice': self.get_gas_price_wei(),
                    'nonce': current_nonce  # Используем полученный актуальный nonce
                })
            
            # Подписываем и отправляем транзакцию
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Ждем подтверждения
            self.log(f"⏳ Ожидание подтверждения транзакции: {tx_hash.hex()}", "INFO")
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if tx_receipt['status'] == 1:
                self.log(f"✅ Покупка успешно завершена! Tx: {tx_hash.hex()}", "SUCCESS")
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'amount_spent': buy_amount,
                    'gas_used': tx_receipt['gasUsed']
                }
            else:
                self.log("❌ Транзакция отклонена сетью", "ERROR")
                return {
                    'success': False,
                    'error': 'Транзакция отклонена'
                }
            
        except Exception as e:
            self.log(f"❌ Ошибка выполнения покупки: {str(e)}", "ERROR")
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
        self.log(f"✅ Покупка #{buy_number} завершена. Tx: {tx_hash[:20]}...", "SUCCESS")
        
        # Обновляем балансы
        self.update_balances()
        
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
