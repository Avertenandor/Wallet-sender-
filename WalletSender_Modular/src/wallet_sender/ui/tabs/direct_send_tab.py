"""
Вкладка прямой отправки токенов
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel,
    QLineEdit, QTextEdit, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QFormLayout, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

from web3 import Web3
from eth_account import Account

from .base_tab import BaseTab
from ...utils.logger import get_logger

logger = get_logger(__name__)

try:
    from mnemonic import Mnemonic
except ImportError:
    Mnemonic = None
    logger.warning("Библиотека mnemonic не установлена")

# Адреса токенов BSC
CONTRACTS = {
    'PLEX_ONE': '0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1',
    'USDT': '0x55d398326f99059ff775485246999027b3197955'
}

# ABI для ERC20 токенов
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]


class DirectSendTab(BaseTab):
    """Вкладка для прямой отправки токенов"""
    
    transaction_completed = pyqtSignal(dict)
    
    def __init__(self, main_window, parent=None):
        # Собственный кошелек
        self.account = None
        self.web3 = None
        self.is_sending = False
        
        # Вызываем родительский конструктор
        super().__init__(main_window, parent)
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Группа подключения кошелька
        wallet_group = self._create_wallet_group()
        layout.addWidget(wallet_group)
        
        # Группа настроек отправки
        send_group = self._create_send_group()
        layout.addWidget(send_group)
        
        # Группа настроек газа
        gas_group = self.create_gas_settings_group()
        layout.addWidget(gas_group)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("🚀 Отправить")
        self.send_btn.clicked.connect(self.send_transaction)
        self.send_btn.setEnabled(False)
        buttons_layout.addWidget(self.send_btn)
        
        self.refresh_balance_btn = QPushButton("🔄 Обновить баланс")
        self.refresh_balance_btn.clicked.connect(self.refresh_balance)
        self.refresh_balance_btn.setEnabled(False)
        buttons_layout.addWidget(self.refresh_balance_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Отображение баланса
        self.balance_label = QLabel("Баланс: Кошелек не подключен")
        self.balance_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.balance_label)
        
        # История отправок
        history_group = self._create_history_group()
        layout.addWidget(history_group)
        
    def _create_wallet_group(self):
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
        
    def _create_send_group(self):
        """Создание группы настроек отправки"""
        group = QGroupBox("Настройки отправки")
        layout = QFormLayout()
        
        # Выбор токена
        self.token_combo = QComboBox()
        self.token_combo.addItems(["BNB", "PLEX ONE", "USDT", "Другой..."])
        self.token_combo.currentTextChanged.connect(self._on_token_changed)
        layout.addRow("Токен:", self.token_combo)
        
        # Поле для пользовательского токена
        self.custom_token_input = QLineEdit()
        self.custom_token_input.setPlaceholderText("Введите адрес токена...")
        self.custom_token_input.setVisible(False)
        layout.addRow("Адрес токена:", self.custom_token_input)
        
        # Адрес получателя
        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("0x...")
        layout.addRow("Адрес получателя:", self.recipient_input)
        
        # Сумма
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setDecimals(6)
        self.amount_input.setMaximum(999999999.0)
        self.amount_input.setSuffix(" токенов")
        layout.addRow("Сумма:", self.amount_input)
        
        group.setLayout(layout)
        return group
        
    def _create_history_group(self):
        """Создание группы истории отправок"""
        group = QGroupBox("История отправок")
        layout = QVBoxLayout()
        
        # Таблица истории
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Время", "Токен", "Получатель", "Сумма", "Статус"
        ])
        
        # Настройка таблицы
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(True)
        
        layout.addWidget(self.history_table)
        
        group.setLayout(layout)
        return group
        
    def _on_token_changed(self, token):
        """Обработка изменения выбранного токена"""
        is_custom = token == "Другой..."
        self.custom_token_input.setVisible(is_custom)
        
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
                    QMessageBox.critical(self, "Ошибка", "Библиотека mnemonic не установлена!")
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
                
            # Инициализируем Web3
            from ...core.web3_provider import Web3Provider
            web3_provider = Web3Provider()
            self.web3 = web3_provider.w3
            
            # Обновляем UI
            self.wallet_address_label.setText(f"Адрес: {self.account.address}")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.refresh_balance_btn.setEnabled(True)
            self.send_btn.setEnabled(True)
            
            QMessageBox.information(self, "Успех", f"Кошелек подключен!\nАдрес: {self.account.address}")
            self.log(f"Кошелек подключен: {self.account.address}")
            
            # Обновляем баланс
            self.refresh_balance()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключить кошелек:\n{str(e)}")
            self.log(f"Ошибка подключения кошелька: {e}", "ERROR")
            
    def disconnect_wallet(self):
        """Отключение кошелька"""
        self.account = None
        self.web3 = None
        
        # Очищаем поле ввода
        self.wallet_input.clear()
            
        # Обновляем UI
        self.wallet_address_label.setText("Адрес: Не подключен")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.refresh_balance_btn.setEnabled(False)
        self.send_btn.setEnabled(False)
        
        # Очищаем баланс
        self.balance_label.setText("Баланс: Кошелек не подключен")
        
        self.log("Кошелек отключен")
        
    def refresh_balance(self):
        """Обновление баланса"""
        if not self.account or not self.web3:
            return
            
        try:
            # Получаем баланс BNB
            balance_wei = self.web3.eth.get_balance(self.account.address)
            balance_bnb = self.web3.from_wei(balance_wei, 'ether')
            
            self.balance_label.setText(f"Баланс: {balance_bnb:.6f} BNB")
            self.log(f"Баланс обновлен: {balance_bnb:.6f} BNB")
            
        except Exception as e:
            self.log(f"Ошибка обновления баланса: {e}", "ERROR")
            self.balance_label.setText("Баланс: Ошибка получения")
            
    def send_transaction(self):
        """Отправка транзакции"""
        if not self.account or not self.web3:
            QMessageBox.warning(self, "Ошибка", "Кошелек не подключен!")
            return
        
        # Проверка, что отправка еще не идет
        if self.is_sending:
            QMessageBox.warning(self, "Предупреждение", "Отправка уже выполняется!")
            return
            
        # Получаем параметры
        token_name = self.token_combo.currentText()
        recipient = self.recipient_input.text().strip()
        amount = self.amount_input.value()
        
        # Валидация адреса получателя
        if not recipient:
            QMessageBox.warning(self, "Ошибка", "Введите адрес получателя!")
            return
            
        if not Web3.is_address(recipient):
            QMessageBox.warning(self, "Ошибка", "Неверный адрес получателя!")
            return
            
        # Валидация суммы
        if amount <= 0:
            QMessageBox.warning(self, "Ошибка", "Введите корректную сумму!")
            return
            
        # Получаем настройки газа
        gas_price = self.get_gas_price_wei() if hasattr(self, 'get_gas_price_wei') else Web3.to_wei(5, 'gwei')
        gas_limit = self.get_gas_limit() if hasattr(self, 'get_gas_limit') else 100000
        
        # Блокируем кнопку
        self.is_sending = True
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳ Отправка...")
        
        try:
            tx_hash = None
            status = "Ошибка"
            
            if token_name == "BNB":
                # Отправка BNB
                tx_hash = self._send_bnb(recipient, amount, gas_price)
                status = "Успешно" if tx_hash else "Ошибка"
                
            elif token_name in ["PLEX ONE", "USDT"]:
                # Отправка токенов PLEX ONE или USDT
                token_address = CONTRACTS['PLEX_ONE'] if token_name == "PLEX ONE" else CONTRACTS['USDT']
                tx_hash = self._send_token(recipient, amount, token_address, gas_price, gas_limit)
                status = "Успешно" if tx_hash else "Ошибка"
                
            elif token_name == "Другой...":
                # Отправка пользовательского токена
                token_address = self.custom_token_input.text().strip()
                if not token_address:
                    QMessageBox.warning(self, "Ошибка", "Введите адрес токена!")
                    return
                if not Web3.is_address(token_address):
                    QMessageBox.warning(self, "Ошибка", "Неверный адрес токена!")
                    return
                    
                tx_hash = self._send_token(recipient, amount, token_address, gas_price, gas_limit)
                status = "Успешно" if tx_hash else "Ошибка"
                
            # Добавляем в историю
            self._add_to_history(token_name, recipient, amount, status, tx_hash or "")
            
            # Показываем результат
            if tx_hash:
                msg = f"Транзакция отправлена!\n\nHash: {tx_hash}\n\nСсылка на BscScan:\nhttps://bscscan.com/tx/{tx_hash}"
                QMessageBox.information(self, "Успех", msg)
                self.log(f"✅ Транзакция отправлена: {tx_hash}")
                
                # Обновляем баланс
                self.refresh_balance()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось отправить транзакцию!")
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при отправке: {str(e)}")
            self.log(f"❌ Ошибка отправки: {e}", "ERROR")
            self._add_to_history(token_name, recipient, amount, "Ошибка", "")
            
        finally:
            # Разблокируем кнопку
            self.is_sending = False
            self.send_btn.setEnabled(True)
            self.send_btn.setText("🚀 Отправить")
        
    def _send_bnb(self, to_address: str, amount: float, gas_price: int) -> Optional[str]:
        """Отправка BNB"""
        try:
            # Конвертируем сумму в wei
            amount_wei = self.web3.to_wei(amount, 'ether')
            
            # Проверяем баланс
            balance = self.web3.eth.get_balance(self.account.address)
            if balance < amount_wei + gas_price * 21000:
                self.log("Недостаточно BNB для отправки (учитывая газ)", "ERROR")
                return None
            
            # Получаем nonce
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            
            # Создаем транзакцию
            transaction = {
                'nonce': nonce,
                'to': Web3.to_checksum_address(to_address),
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': gas_price,
                'chainId': 56  # BSC Mainnet
            }
            
            # Подписываем транзакцию
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            
            # Отправляем транзакцию
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Ждем подтверждения
            self.log(f"Ожидание подтверждения транзакции...")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                self.log(f"✅ BNB успешно отправлен: {amount} BNB на {to_address[:10]}...")
                return tx_hash.hex()
            else:
                self.log(f"❌ Транзакция отклонена сетью", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Ошибка при отправке BNB: {str(e)}", "ERROR")
            return None
    
    def _send_token(self, to_address: str, amount: float, token_address: str, gas_price: int, gas_limit: int) -> Optional[str]:
        """Отправка ERC20 токена"""
        try:
            # Преобразуем адреса в checksum формат
            to_address = Web3.to_checksum_address(to_address)
            token_address = Web3.to_checksum_address(token_address)
            
            # Создаем контракт токена
            token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
            
            # Получаем decimals токена
            decimals = token_contract.functions.decimals().call()
            amount_in_units = int(amount * (10 ** decimals))
            
            # Проверяем баланс токенов
            token_balance = token_contract.functions.balanceOf(self.account.address).call()
            if token_balance < amount_in_units:
                self.log(f"Недостаточно токенов для отправки", "ERROR")
                return None
            
            # Получаем nonce
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            
            # Создаем транзакцию transfer
            transaction = token_contract.functions.transfer(
                to_address,
                amount_in_units
            ).build_transaction({
                'from': self.account.address,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': 56  # BSC Mainnet
            })
            
            # Подписываем транзакцию
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            
            # Отправляем транзакцию
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Ждем подтверждения
            self.log(f"Ожидание подтверждения транзакции...")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                self.log(f"✅ Токены успешно отправлены: {amount} на {to_address[:10]}...")
                return tx_hash.hex()
            else:
                self.log(f"❌ Транзакция отклонена сетью", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Ошибка при отправке токена: {str(e)}", "ERROR")
            return None
        
    def _add_to_history(self, token: str, recipient: str, amount: float, status: str, tx_hash: str = ""):
        """Добавление записи в историю"""
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        
        # Заполняем данные
        self.history_table.setItem(row, 0, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        self.history_table.setItem(row, 1, QTableWidgetItem(token))
        self.history_table.setItem(row, 2, QTableWidgetItem(recipient[:10] + "..."))
        self.history_table.setItem(row, 3, QTableWidgetItem(f"{amount:.6f}"))
        self.history_table.setItem(row, 4, QTableWidgetItem(status))
        
        # Прокручиваем к новой записи
        self.history_table.scrollToBottom()