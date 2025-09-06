"""
Вкладка прямой отправки токенов с поддержкой JobRouter
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
from ...services.job_router import get_job_router
from ...core.nonce_manager import get_nonce_manager

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

# ABI для ERC20 токенов (минимальный)
ERC20_ABI = json.loads('[{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]')


class DirectSendTab(BaseTab):
    """Вкладка для прямой отправки токенов"""
    
    transaction_completed = pyqtSignal(dict)
    
    def __init__(self, main_window, parent=None):
        # Собственный кошелек
        self.account = None
        self.web3 = None
        self.is_sending = False
        
        # Инициализируем JobRouter и NonceManager
        self.job_router = get_job_router()
        self.nonce_manager = get_nonce_manager()
        
        # Текущие задачи
        self.current_jobs = {}
        
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
        
        self.cancel_btn = QPushButton("❌ Отменить")
        self.cancel_btn.clicked.connect(self.cancel_current_jobs)
        self.cancel_btn.setEnabled(False)
        buttons_layout.addWidget(self.cancel_btn)
        
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
                # SEED фраза — корректная деривация по BIP44 (m/44'/60'/0'/0/0)
                account_path = "m/44'/60'/0'/0/0"
                created = False
                if hasattr(Account, 'from_mnemonic'):
                    try:
                        self.account = Account.from_mnemonic(wallet_data, account_path=account_path)  # type: ignore[arg-type]
                        created = True
                    except Exception:
                        created = False
                if not created:
                    if Mnemonic is None:
                        QMessageBox.critical(self, "Ошибка", "Для SEED требуется библиотека mnemonic. Либо введите приватный ключ.")
                        return
                    try:
                        from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes  # type: ignore[import]
                        words = wallet_data.split()
                        if len(words) not in [12, 24]:
                            QMessageBox.warning(self, "Ошибка", "SEED фраза должна содержать 12 или 24 слова!")
                            return
                        mnemo = Mnemonic("english")
                        if not mnemo.check(wallet_data):
                            QMessageBox.warning(self, "Ошибка", "Неверная SEED фраза!")
                            return
                        seed_bytes = Bip39SeedGenerator(wallet_data).Generate()
                        bip44_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                        private_key = bip44_ctx.PrivateKey().Raw().ToHex()
                        self.account = Account.from_key(private_key)
                        created = True
                    except Exception as e:
                        QMessageBox.critical(self, "Ошибка", f"Не удалось создать кошелек из SEED:\n{e}")
                        return
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
        """Отправка транзакции через JobRouter"""
        if not self.account or not self.web3:
            QMessageBox.warning(self, "Ошибка", "Кошелек не подключен!")
            return
            
        # Проверка заполнения полей
        recipient = self.recipient_input.text().strip()
        if not recipient or not self.web3.is_address(recipient):
            QMessageBox.warning(self, "Ошибка", "Введите корректный адрес получателя!")
            return
            
        amount = self.amount_input.value()
        if amount <= 0:
            QMessageBox.warning(self, "Ошибка", "Введите корректную сумму!")
            return
            
        token_type = self.token_combo.currentText()
        
        # Определяем адрес токена
        token_address = None
        if token_type == "BNB":
            token_address = None  # Нативный токен
        elif token_type == "PLEX ONE":
            token_address = CONTRACTS['PLEX_ONE']
        elif token_type == "USDT":
            token_address = CONTRACTS['USDT']
        elif token_type == "Другой...":
            token_address = self.custom_token_input.text().strip()
            if not token_address or not self.web3.is_address(token_address):
                QMessageBox.warning(self, "Ошибка", "Введите корректный адрес токена!")
                return
        
        # Блокируем кнопку на время отправки
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Отправка...")
        self.cancel_btn.setEnabled(True)
        
        # Создаем задачу для JobRouter
        job_data = {
            'type': 'send_token' if token_address else 'send_bnb',
            'from_address': self.account.address,
            'to_address': recipient,
            'amount': amount,
            'token_address': token_address,
            'private_key': self.account.key.hex(),
            'gas_price': self.get_gas_price_wei(),
            'gas_limit': self.get_gas_limit(),
            'token_name': token_type
        }
        
        # Добавляем задачу в очередь
        job_id = self.job_router.add_job(
            job_data,
            callback=self._on_transaction_complete,
            progress_callback=self._on_transaction_progress
        )
        
        # Сохраняем информацию о задаче
        self.current_jobs[job_id] = {
            'token': token_type,
            'recipient': recipient,
            'amount': amount
        }
        
        self.log(f"Задача {job_id} добавлена в очередь для отправки {amount} {token_type} на {recipient[:10]}...")
    
    def _on_transaction_progress(self, job_id: str, progress: float, message: str):
        """Обработка прогресса транзакции"""
        if job_id in self.current_jobs:
            self.send_btn.setText(f"Отправка... {int(progress*100)}%")
            self.log(f"[{job_id}] {message} ({int(progress*100)}%)")
    
    def _on_transaction_complete(self, job_id: str, success: bool, result: Any):
        """Обработка завершения транзакции"""
        if job_id not in self.current_jobs:
            return
            
        job_info = self.current_jobs[job_id]
        
        if success:
            tx_hash = result.get('tx_hash', '')
            # Добавляем в историю
            self._add_to_history(
                job_info['token'],
                job_info['recipient'],
                job_info['amount'],
                "✅ Успешно",
                tx_hash
            )
            self.log(f"✅ Транзакция завершена: {tx_hash}", "SUCCESS")
            
            # Показываем сообщение об успехе
            msg = QMessageBox(self)
            msg.setWindowTitle("Успех")
            msg.setText(f"Транзакция успешно отправлена!\n\nTx Hash: {tx_hash[:20]}...")
            msg.setDetailedText(
                f"Полный хэш: {tx_hash}\n\n"
                f"Получатель: {job_info['recipient']}\n"
                f"Сумма: {job_info['amount']} {job_info['token']}"
            )
            msg.exec_()
            
            # Обновляем баланс
            self.refresh_balance()
            
            # Очищаем поля
            self.recipient_input.clear()
            self.amount_input.setValue(0)
        else:
            error_msg = str(result)
            self._add_to_history(
                job_info['token'],
                job_info['recipient'],
                job_info['amount'],
                "❌ Ошибка",
                ""
            )
            self.log(f"❌ Ошибка отправки: {error_msg}", "ERROR")
            QMessageBox.critical(self, "Ошибка", f"Не удалось отправить транзакцию:\n\n{error_msg}")
        
        # Удаляем задачу из списка
        del self.current_jobs[job_id]
        
        # Восстанавливаем кнопку
        if not self.current_jobs:
            self.send_btn.setEnabled(True)
            self.send_btn.setText("🚀 Отправить")
            self.cancel_btn.setEnabled(False)
    
    def cancel_current_jobs(self):
        """Отмена текущих задач"""
        if not self.current_jobs:
            return
            
        # Отменяем все активные задачи
        for job_id in list(self.current_jobs.keys()):
            success = self.job_router.cancel_job(job_id)
            if success:
                job_info = self.current_jobs[job_id]
                self._add_to_history(
                    job_info['token'],
                    job_info['recipient'],
                    job_info['amount'],
                    "⚠️ Отменено",
                    ""
                )
                self.log(f"Задача {job_id} отменена")
                del self.current_jobs[job_id]
        
        # Восстанавливаем интерфейс
        self.send_btn.setEnabled(True)
        self.send_btn.setText("🚀 Отправить")
        self.cancel_btn.setEnabled(False)
    
    def _send_bnb(self, to_address: str, amount: float, gas_price: int, gas_limit: int) -> str:
        """Отправка BNB с использованием NonceManager"""
        try:
            # Конвертируем amount в Wei
            amount_wei = self.web3.to_wei(amount, 'ether')
            
            # Получаем nonce через NonceManager
            nonce = self.nonce_manager.get_nonce(self.account.address)
            
            # Создаем транзакцию
            transaction = {
                'to': Web3.to_checksum_address(to_address),
                'value': amount_wei,
                'gas': gas_limit if gas_limit else 21000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': 56  # BSC Mainnet
            }
            
            # Подписываем транзакцию
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            
            # Отправляем транзакцию
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Ждем подтверждения
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if tx_receipt['status'] == 1:
                # Увеличиваем nonce после успешной отправки
                self.nonce_manager.increment_nonce(self.account.address)
                return tx_hash.hex()
            else:
                raise Exception("Транзакция отклонена сетью")
                
        except Exception as e:
            logger.exception(f"Ошибка отправки BNB")
            raise
            
    def _send_token(self, to_address: str, amount: float, token_address: str, gas_price: int, gas_limit: int) -> str:
        """Отправка ERC20 токена с использованием NonceManager"""
        try:
            # Создаем контракт токена
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            # Получаем decimals токена
            decimals = contract.functions.decimals().call()
            amount_in_units = int(amount * (10 ** decimals))
            
            # Получаем nonce через NonceManager
            nonce = self.nonce_manager.get_nonce(self.account.address)
            
            # Создаем транзакцию transfer
            transaction = contract.functions.transfer(
                Web3.to_checksum_address(to_address),
                amount_in_units
            ).build_transaction({
                'from': self.account.address,
                'gas': gas_limit if gas_limit else 100000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': 56  # BSC Mainnet
            })
            
            # Подписываем транзакцию
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            
            # Отправляем транзакцию
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Ждем подтверждения
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if tx_receipt['status'] == 1:
                # Увеличиваем nonce после успешной отправки
                self.nonce_manager.increment_nonce(self.account.address)
                return tx_hash.hex()
            else:
                raise Exception("Транзакция отклонена сетью")
                
        except Exception as e:
            logger.exception(f"Ошибка отправки токена")
            raise
        
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
