"""Auto Sales Tab - автоматическая продажа токенов через PancakeSwap"""

import json
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit, QCheckBox,
    QMessageBox, QSplitter, QFormLayout
)
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QFont, QColor

from web3 import Web3
from eth_account import Account
from .base_tab import BaseTab

# ABI для ERC20 токенов
ERC20_ABI = json.loads('[{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}]')

# Минимальный ABI для PancakeSwap Router
PANCAKE_ROUTER_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}]')


class AutoSalesTab(BaseTab):
    """Вкладка автоматических продаж токенов через PancakeSwap"""
    
    # Сигналы
    balance_updated = pyqtSignal(dict)
    sale_completed = pyqtSignal(dict)
    
    def __init__(self, main_window, parent=None):
        # Инициализация переменных
        self.web3 = None
        self.account = None
        self.monitoring_thread = None
        self.is_monitoring = False
        self.stop_monitoring = threading.Event()
        self.monitored_tokens = {}
        self.sales_history = []
        
        # Адреса контрактов
        self.PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
        self.WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
        self.USDT = "0x55d398326f99059ff775485246999027b3197955"
        self.PLEX_ONE = "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1"
        
        super().__init__(main_window, parent)
        
        # Инициализация Web3
        self._init_web3()
        
    def _init_web3(self):
        """Инициализация Web3 подключения"""
        try:
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
        title_label = QLabel("💰 Автоматические продажи токенов")
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
        token_layout.addRow("Адрес токена:", self.custom_token_input)
        
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
        
        # Процент от баланса для продажи
        self.sell_percentage = QSpinBox()
        self.sell_percentage.setRange(1, 100)
        self.sell_percentage.setValue(100)
        self.sell_percentage.setSuffix(" %")
        token_layout.addRow("Продавать %:", self.sell_percentage)
        
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
        
        # Интервал проверки
        self.check_interval = QSpinBox()
        self.check_interval.setRange(5, 3600)
        self.check_interval.setValue(30)
        self.check_interval.setSuffix(" сек")
        token_layout.addRow("Интервал проверки:", self.check_interval)
        
        left_layout.addLayout(token_layout)
        
        # Настройки газа
        gas_group = self.create_gas_settings_group()
        left_layout.addWidget(gas_group)
        
        # Кнопки управления
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Начать мониторинг")
        self.start_btn.clicked.connect(self.start_monitoring)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Остановить")
        self.stop_btn.clicked.connect(self.stop_monitoring_func)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        self.test_sell_btn = QPushButton("🧪 Тест продажи")
        self.test_sell_btn.clicked.connect(self.test_sell)
        control_layout.addWidget(self.test_sell_btn)
        
        left_layout.addLayout(control_layout)
        
        # Добавить в список мониторинга
        self.add_monitor_btn = QPushButton("➕ Добавить в мониторинг")
        self.add_monitor_btn.clicked.connect(self.add_to_monitoring)
        left_layout.addWidget(self.add_monitor_btn)
        
        left_layout.addStretch()
        
        # Правая панель - мониторинг и история
        right_panel = QGroupBox("Мониторинг и история")
        right_layout = QVBoxLayout(right_panel)
        
        # Статус мониторинга
        self.status_label = QLabel("⏸️ Мониторинг не запущен")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
        right_layout.addWidget(self.status_label)
        
        # Текущий баланс
        self.balance_info = QTextEdit()
        self.balance_info.setReadOnly(True)
        self.balance_info.setMaximumHeight(100)
        self.balance_info.setPlaceholderText("Информация о балансах...")
        right_layout.addWidget(self.balance_info)
        
        # Список отслеживаемых токенов
        tokens_label = QLabel("📊 Отслеживаемые токены:")
        right_layout.addWidget(tokens_label)
        
        self.monitored_table = QTableWidget()
        self.monitored_table.setColumnCount(5)
        self.monitored_table.setHorizontalHeaderLabels([
            "Токен", "Порог", "Продавать в", "Текущий баланс", "Действия"
        ])
        header = self.monitored_table.horizontalHeader()
        header.setStretchLastSection(True)
        right_layout.addWidget(self.monitored_table)
        
        # История продаж
        history_label = QLabel("📜 История продаж:")
        right_layout.addWidget(history_label)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Время", "Токен", "Количество", "Получено", "Tx Hash", "Статус"
        ])
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(True)
        right_layout.addWidget(self.history_table)
        
        # Добавляем панели в splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([500, 700])
        
        layout.addWidget(splitter)
        
        # Таймер для обновления балансов
        self.balance_timer = QTimer()
        self.balance_timer.timeout.connect(self.update_balance_display)
        self.balance_timer.start(10000)  # Каждые 10 секунд
        
    def _on_token_changed(self, token):
        """Обработка изменения выбранного токена"""
        is_custom = token == "Другой токен"
        self.custom_token_input.setVisible(is_custom)
    
    def connect_wallet(self):
        """Переопределенное подключение кошелька"""
        wallet_data = self.wallet_input.toPlainText().strip()
        
        if not wallet_data:
            QMessageBox.warning(self, "Ошибка", "Введите приватный ключ или SEED фразу!")
            return
            
        try:
            # Определяем тип входных данных
            if ' ' in wallet_data:  # SEED фраза
                try:
                    from mnemonic import Mnemonic
                    mnemo = Mnemonic("english")
                    if not mnemo.check(wallet_data):
                        raise ValueError("Неверная SEED фраза")
                    seed = mnemo.to_seed(wallet_data)
                    private_key = seed[:32].hex()
                except ImportError:
                    QMessageBox.critical(self, "Ошибка", "Библиотека mnemonic не установлена!")
                    return
            else:  # Приватный ключ
                private_key = wallet_data
                if private_key.startswith('0x'):
                    private_key = private_key[2:]
            
            # Создаем аккаунт
            self.account = Account.from_key(private_key)
            
            # Обновляем UI
            self.wallet_address_label.setText(f"Адрес: {self.account.address}")
            self.disconnect_btn.setEnabled(True)
            
            self.log(f"✅ Кошелек подключен: {self.account.address}", "SUCCESS")
            
            # Обновляем баланс
            self.update_balance_display()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключить кошелек:\n{str(e)}")
            self.log(f"❌ Ошибка подключения кошелька: {e}", "ERROR")
    
    def disconnect_wallet(self):
        """Отключение кошелька"""
        self.account = None
        self.wallet_address_label.setText("Адрес: Не подключен")
        self.disconnect_btn.setEnabled(False)
        self.balance_info.clear()
        self.log("🔌 Кошелек отключен", "INFO")
    
    def add_to_monitoring(self):
        """Добавление токена в список мониторинга"""
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
        
        # Добавляем в словарь мониторинга
        self.monitored_tokens[token_address] = {
            'name': token_name,
            'threshold': self.threshold_input.value(),
            'target': self.target_combo.currentText(),
            'percentage': self.sell_percentage.value(),
            'min_price': self.min_price_input.value(),
            'slippage': self.slippage_input.value()
        }
        
        # Добавляем в таблицу
        row = self.monitored_table.rowCount()
        self.monitored_table.insertRow(row)
        self.monitored_table.setItem(row, 0, QTableWidgetItem(token_name))
        self.monitored_table.setItem(row, 1, QTableWidgetItem(f"{self.threshold_input.value():.2f}"))
        self.monitored_table.setItem(row, 2, QTableWidgetItem(self.target_combo.currentText()))
        self.monitored_table.setItem(row, 3, QTableWidgetItem("0"))
        
        # Кнопка удаления
        remove_btn = QPushButton("❌")
        remove_btn.clicked.connect(lambda: self.remove_from_monitoring(token_address))
        self.monitored_table.setCellWidget(row, 4, remove_btn)
        
        self.log(f"✅ {token_name} добавлен в мониторинг", "SUCCESS")
    
    def remove_from_monitoring(self, token_address):
        """Удаление токена из мониторинга"""
        if token_address in self.monitored_tokens:
            del self.monitored_tokens[token_address]
            
            # Обновляем таблицу
            self._refresh_monitored_table()
            self.log(f"❌ Токен удален из мониторинга", "INFO")
    
    def _refresh_monitored_table(self):
        """Обновление таблицы отслеживаемых токенов"""
        self.monitored_table.setRowCount(0)
        
        for token_address, settings in self.monitored_tokens.items():
            row = self.monitored_table.rowCount()
            self.monitored_table.insertRow(row)
            self.monitored_table.setItem(row, 0, QTableWidgetItem(settings['name']))
            self.monitored_table.setItem(row, 1, QTableWidgetItem(f"{settings['threshold']:.2f}"))
            self.monitored_table.setItem(row, 2, QTableWidgetItem(settings['target']))
            
            # Получаем текущий баланс
            balance = self._get_token_balance(token_address)
            self.monitored_table.setItem(row, 3, QTableWidgetItem(f"{balance:.4f}"))
            
            # Кнопка удаления
            remove_btn = QPushButton("❌")
            remove_btn.clicked.connect(lambda addr=token_address: self.remove_from_monitoring(addr))
            self.monitored_table.setCellWidget(row, 4, remove_btn)
    
    def start_monitoring(self):
        """Запуск мониторинга"""
        if not self.account:
            QMessageBox.warning(self, "Ошибка", "Сначала подключите кошелек!")
            return
        
        if not self.monitored_tokens:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы один токен для мониторинга!")
            return
        
        if self.is_monitoring:
            self.log("⚠️ Мониторинг уже запущен", "WARNING")
            return
        
        self.is_monitoring = True
        self.stop_monitoring.clear()
        
        # Обновляем UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("✅ Мониторинг активен")
        self.status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
        
        # Запускаем поток мониторинга
        self.monitoring_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.monitoring_thread.start()
        
        self.log("🚀 Мониторинг запущен", "SUCCESS")
    
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
        """Рабочий поток мониторинга"""
        interval = self.check_interval.value()
        
        while not self.stop_monitoring.is_set():
            try:
                for token_address, settings in self.monitored_tokens.items():
                    if self.stop_monitoring.is_set():
                        break
                    
                    # Получаем баланс токена
                    balance = self._get_token_balance(token_address)
                    
                    # Проверяем порог
                    if balance >= settings['threshold']:
                        self.log(f"🎯 Достигнут порог для {settings['name']}: {balance:.4f} >= {settings['threshold']}", "INFO")
                        
                        # Рассчитываем количество для продажи
                        sell_amount = balance * (settings['percentage'] / 100)
                        
                        # Проверяем цену если установлен минимум
                        if settings['min_price'] > 0:
                            price = self._get_token_price(token_address, settings['target'])
                            if price < settings['min_price']:
                                self.log(f"⚠️ Цена {price:.8f} ниже минимальной {settings['min_price']}", "WARNING")
                                continue
                        
                        # Выполняем продажу
                        self._execute_sell(token_address, sell_amount, settings)
                
                # Ждем перед следующей проверкой
                self.stop_monitoring.wait(interval)
                
            except Exception as e:
                self.log(f"❌ Ошибка в мониторинге: {str(e)}", "ERROR")
                time.sleep(5)
    
    def _execute_sell(self, token_address: str, amount: float, settings: dict):
        """Выполнение продажи токена"""
        try:
            if not self.account or not self.web3:
                raise Exception("Кошелек не подключен")
            
            # Получаем контракт токена
            token_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            # Получаем decimals
            decimals = token_contract.functions.decimals().call()
            amount_wei = int(amount * (10 ** decimals))
            
            # Проверяем баланс
            balance = token_contract.functions.balanceOf(self.account.address).call()
            if balance < amount_wei:
                self.log(f"⚠️ Недостаточный баланс: {balance / (10 ** decimals):.4f} < {amount:.4f}", "WARNING")
                return
            
            # Определяем путь обмена
            if settings['target'] == 'BNB':
                path = [token_address, self.WBNB]
                swap_method = 'swapExactTokensForETH'
            else:  # USDT
                path = [token_address, self.WBNB, self.USDT]
                swap_method = 'swapExactTokensForTokens'
            
            # Получаем Router контракт
            router_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.PANCAKE_ROUTER),
                abi=PANCAKE_ROUTER_ABI
            )
            
            # Проверяем и устанавливаем approve если нужно
            allowance = token_contract.functions.allowance(
                self.account.address,
                self.PANCAKE_ROUTER
            ).call()
            
            if allowance < amount_wei:
                self.log(f"📝 Устанавливаем Approve для {settings['name']}...", "INFO")
                
                # Approve транзакция
                approve_tx = token_contract.functions.approve(
                    self.PANCAKE_ROUTER,
                    amount_wei
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 100000,
                    'gasPrice': self.get_gas_price_wei(),
                    'nonce': self.web3.eth.get_transaction_count(self.account.address),
                })
                
                # Подписываем и отправляем
                signed_approve = self.web3.eth.account.sign_transaction(approve_tx, self.account.key)
                approve_hash = self.web3.eth.send_raw_transaction(signed_approve.rawTransaction)
                
                # Ждем подтверждения
                self.web3.eth.wait_for_transaction_receipt(approve_hash)
                self.log(f"✅ Approve установлен: {approve_hash.hex()}", "SUCCESS")
            
            # Получаем ожидаемый выход
            amounts_out = router_contract.functions.getAmountsOut(amount_wei, path).call()
            min_amount_out = int(amounts_out[-1] * (1 - settings['slippage'] / 100))
            
            # Deadline через 20 минут
            deadline = int(time.time()) + 1200
            
            # Создаем транзакцию обмена
            if swap_method == 'swapExactTokensForETH':
                swap_tx = router_contract.functions.swapExactTokensForETH(
                    amount_wei,
                    min_amount_out,
                    path,
                    self.account.address,
                    deadline
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 300000,
                    'gasPrice': self.get_gas_price_wei(),
                    'nonce': self.web3.eth.get_transaction_count(self.account.address),
                })
            else:
                swap_tx = router_contract.functions.swapExactTokensForTokens(
                    amount_wei,
                    min_amount_out,
                    path,
                    self.account.address,
                    deadline
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 300000,
                    'gasPrice': self.get_gas_price_wei(),
                    'nonce': self.web3.eth.get_transaction_count(self.account.address),
                })
            
            # Подписываем и отправляем
            signed_swap = self.web3.eth.account.sign_transaction(swap_tx, self.account.key)
            swap_hash = self.web3.eth.send_raw_transaction(signed_swap.rawTransaction)
            
            self.log(f"📤 Транзакция отправлена: {swap_hash.hex()}", "INFO")
            
            # Ждем подтверждения
            receipt = self.web3.eth.wait_for_transaction_receipt(swap_hash)
            
            if receipt['status'] == 1:
                # Добавляем в историю
                self._add_to_history({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'token': settings['name'],
                    'amount': amount,
                    'received': amounts_out[-1] / (10 ** (18 if settings['target'] == 'BNB' else 18)),
                    'target': settings['target'],
                    'tx_hash': swap_hash.hex(),
                    'status': 'Успешно'
                })
                
                self.log(f"✅ Продажа выполнена: {amount:.4f} {settings['name']} -> {amounts_out[-1] / (10 ** 18):.4f} {settings['target']}", "SUCCESS")
                
                # Сигнал о завершении продажи
                self.sale_completed.emit({
                    'token': settings['name'],
                    'amount': amount,
                    'received': amounts_out[-1] / (10 ** 18),
                    'tx_hash': swap_hash.hex()
                })
            else:
                self.log(f"❌ Транзакция не удалась: {swap_hash.hex()}", "ERROR")
                self._add_to_history({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'token': settings['name'],
                    'amount': amount,
                    'received': 0,
                    'target': settings['target'],
                    'tx_hash': swap_hash.hex(),
                    'status': 'Ошибка'
                })
                
        except Exception as e:
            self.log(f"❌ Ошибка продажи {settings['name']}: {str(e)}", "ERROR")
            self._add_to_history({
                'time': datetime.now().strftime("%H:%M:%S"),
                'token': settings['name'],
                'amount': amount,
                'received': 0,
                'target': settings['target'],
                'tx_hash': '',
                'status': f'Ошибка: {str(e)[:50]}'
            })
    
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
        """Получение баланса токена"""
        try:
            if not self.account or not self.web3:
                return 0
            
            token_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            balance = token_contract.functions.balanceOf(self.account.address).call()
            decimals = token_contract.functions.decimals().call()
            
            return balance / (10 ** decimals)
            
        except Exception as e:
            self.log(f"Ошибка получения баланса: {str(e)}", "ERROR")
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
            
            info_text = f"💰 BNB: {bnb_formatted:.6f}\n"
            
            # Обновляем балансы отслеживаемых токенов
            for token_address, settings in self.monitored_tokens.items():
                balance = self._get_token_balance(token_address)
                info_text += f"🪙 {settings['name']}: {balance:.4f}\n"
                
                # Обновляем в таблице
                for row in range(self.monitored_table.rowCount()):
                    if self.monitored_table.item(row, 0).text() == settings['name']:
                        self.monitored_table.setItem(row, 3, QTableWidgetItem(f"{balance:.4f}"))
                        break
            
            self.balance_info.setText(info_text)
            
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
        
        # Спрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Выполнить тестовую продажу?\n\n"
            f"Токен: {token_name}\n"
            f"Баланс: {balance:.4f}\n"
            f"Продать: {balance * (self.sell_percentage.value() / 100):.4f}\n"
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
                'percentage': self.sell_percentage.value(),
                'min_price': 0,
                'slippage': self.slippage_input.value()
            }
            
            sell_amount = balance * (self.sell_percentage.value() / 100)
            self._execute_sell(token_address, sell_amount, settings)
