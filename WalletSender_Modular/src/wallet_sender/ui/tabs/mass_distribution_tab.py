"""
Вкладка массовой рассылки токенов
"""

import threading
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QProgressBar,
    QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QSplitter,
    QHeaderView, QAbstractItemView, QFileDialog, QMessageBox,
    QCheckBox, QRadioButton, QButtonGroup, QFormLayout, QGridLayout
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt5.QtGui import QColor, QFont

from web3 import Web3
from eth_account import Account

from .base_tab import BaseTab
from ...core.wallet_manager import WalletManager
from ...services.token_service import TokenService
from ...services.transaction_service import TransactionService
from ...constants import PLEX_CONTRACT, USDT_CONTRACT
from ...utils.logger import get_logger

logger = get_logger(__name__)

try:
    from mnemonic import Mnemonic
except ImportError:
    Mnemonic = None
    logger.warning("Библиотека mnemonic не установлена. Установите через: pip install mnemonic")

# Адреса токенов BSC
CONTRACTS = {
    'PLEX_ONE': '0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1',
    'USDT': '0x55d398326f99059ff775485246999027b3197955',
    'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
}

# ABI для ERC20 токенов
ERC20_ABI = [
    {"constant":True,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":False,"stateMutability":"view","type":"function"},
    {"constant":False,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":False,"stateMutability":"nonpayable","type":"function"},
    {"constant":True,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},
    {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":False,"stateMutability":"view","type":"function"},
    {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},
    {"constant":True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":False,"stateMutability":"view","type":"function"},
    {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":False,"stateMutability":"nonpayable","type":"function"},
    {"constant":True,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"}
]


class MassDistributionTab(BaseTab):
    """Вкладка для массовой рассылки токенов"""
    
    # Дополнительные сигналы
    address_status_update = pyqtSignal(int, str)  # row, status
    transaction_completed = pyqtSignal(dict)  # transaction info
    distribution_finished = pyqtSignal()
    balance_updated = pyqtSignal(dict)  # balance updates
    
    def __init__(self, main_window, parent=None, slot_number=1):
        # Номер слота для отображения (должен быть установлен ДО вызова super())
        self.slot_number = slot_number
        
        super().__init__(main_window, parent)
        
        # Инициализация переменных для кошелька
        self.web3 = None
        self.account = None
        self.balances = {}
        
        # Настройка таймера для обновления балансов
        self.balance_timer = QTimer()
        self.balance_timer.timeout.connect(self.update_balances)
        
        # Подключение сигналов
        self.balance_updated.connect(self._update_balance_display)
        
        # Инициализация Web3
        self._init_web3()
        
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
        
        # Заголовок слота
        slot_header = QGroupBox(f"Массовая рассылка {self.slot_number} - Слот {self.slot_number}")
        header_layout = QVBoxLayout(slot_header)
        slot_label = QLabel("🔶 Независимый слот для массовой рассылки с собственными настройками")
        slot_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        header_layout.addWidget(slot_label)
        layout.addWidget(slot_header)
        
        # Группа подключения кошелька
        wallet_group = self._create_wallet_group()
        layout.addWidget(wallet_group)
        
        # Группа отображения балансов
        balance_group = self._create_balance_group()
        layout.addWidget(balance_group)
        
        # Настройки рассылки
        settings_group = QGroupBox(f"Настройки массовой рассылки (Слот {self.slot_number})")
        settings_layout = QVBoxLayout(settings_group)
        
        # Выбор токена
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Токен:"))
        
        self.token_combo = QComboBox()
        self.token_combo.addItems(['PLEX ONE', 'USDT', 'Другой'])
        token_layout.addWidget(self.token_combo)
        
        self.custom_token_input = QLineEdit()
        self.custom_token_input.setPlaceholderText("Адрес токена (0x...)")
        self.custom_token_input.setEnabled(False)
        token_layout.addWidget(self.custom_token_input)
        
        settings_layout.addLayout(token_layout)
        
        # Сумма на адрес
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("Сумма на адрес:"))
        
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0.00000001, 1000000)
        self.amount_input.setDecimals(8)
        self.amount_input.setValue(1.0)
        amount_layout.addWidget(self.amount_input)
        
        settings_layout.addLayout(amount_layout)
        
        # Настройки газа
        gas_layout = QHBoxLayout()
        gas_layout.addWidget(QLabel("Цена газа (Gwei):"))
        
        self.gas_price_input = QSpinBox()
        self.gas_price_input.setRange(1, 1000)
        self.gas_price_input.setValue(5)
        gas_layout.addWidget(self.gas_price_input)
        
        gas_layout.addWidget(QLabel("Лимит газа:"))
        
        self.gas_limit_input = QSpinBox()
        self.gas_limit_input.setRange(21000, 1000000)
        self.gas_limit_input.setValue(100000)
        gas_layout.addWidget(self.gas_limit_input)
        
        settings_layout.addLayout(gas_layout)
        
        # Количество циклов
        cycles_layout = QHBoxLayout()
        cycles_layout.addWidget(QLabel("Количество циклов:"))
        
        self.cycles_input = QSpinBox()
        self.cycles_input.setRange(1, 100)
        self.cycles_input.setValue(1)
        cycles_layout.addWidget(self.cycles_input)
        
        cycles_layout.addWidget(QLabel("Интервал (сек):"))
        
        self.interval_input = QSpinBox()
        self.interval_input.setRange(0, 3600)
        self.interval_input.setValue(2)
        cycles_layout.addWidget(self.interval_input)
        
        settings_layout.addLayout(cycles_layout)
        
        layout.addWidget(settings_group)
        
        # Настройки газа
        gas_group = self.create_gas_settings_group()
        layout.addWidget(gas_group)
        
        # Управление адресами
        addresses_group = QGroupBox(f"Адреса получателей (Слот {self.slot_number})")
        addresses_layout = QVBoxLayout(addresses_group)
        
        # Кнопки импорта
        import_buttons_layout = QHBoxLayout()
        
        self.import_file_btn = QPushButton("Импорт из файла")
        self.import_file_btn.clicked.connect(self.import_from_file)
        import_buttons_layout.addWidget(self.import_file_btn)
        
        self.import_clipboard_btn = QPushButton("Импорт из буфера")
        self.import_clipboard_btn.clicked.connect(self.import_from_clipboard)
        import_buttons_layout.addWidget(self.import_clipboard_btn)
        
        self.clear_addresses_btn = QPushButton("Очистить")
        self.clear_addresses_btn.clicked.connect(self.clear_addresses)
        import_buttons_layout.addWidget(self.clear_addresses_btn)
        
        addresses_layout.addLayout(import_buttons_layout)
        
        # Таблица адресов
        self.addresses_table = QTableWidget(0, 3)
        self.addresses_table.setHorizontalHeaderLabels(['Адрес', 'Статус', 'Tx Hash'])
        
        header = self.addresses_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        self.addresses_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        addresses_layout.addWidget(self.addresses_table)
        
        # Статистика
        stats_layout = QHBoxLayout()
        self.total_addresses_label = QLabel("Всего адресов: 0")
        stats_layout.addWidget(self.total_addresses_label)
        
        self.processed_label = QLabel("Обработано: 0")
        stats_layout.addWidget(self.processed_label)
        
        self.success_label = QLabel("Успешно: 0")
        stats_layout.addWidget(self.success_label)
        
        self.failed_label = QLabel("Ошибок: 0")
        stats_layout.addWidget(self.failed_label)
        
        addresses_layout.addLayout(stats_layout)
        
        layout.addWidget(addresses_group)
        
        # Кнопки управления
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton(f"Начать рассылку (Слот {self.slot_number})")
        self.start_btn.clicked.connect(self.start_distribution)
        control_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("Пауза")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_distribution)
        control_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_distribution)
        control_layout.addWidget(self.stop_btn)
        
        self.export_btn = QPushButton("Экспорт результатов")
        self.export_btn.clicked.connect(self.export_results)
        control_layout.addWidget(self.export_btn)
        
        layout.addLayout(control_layout)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Инициализация переменных
        self.addresses: List[str] = []
        self.is_distributing = False
        self.is_paused = False
        self.stop_flag = threading.Event()
        self.distribution_thread = None
        self.slot_id = f"slot{self.slot_number}"  # Уникальный ID слота
        
        # Подключение сигналов
        self.token_combo.currentTextChanged.connect(self.on_token_changed)
        self.address_status_update.connect(self.update_address_status)
        self.transaction_completed.connect(self.on_transaction_completed)
        self.distribution_finished.connect(self.on_distribution_finished)
        
        # Инициализация сервисов (будут созданы при старте)
        self.wallet_manager = None
        self.token_service = None
        self.tx_service = None
        
        self.log(f"Вкладка массовой рассылки {self.slot_id} инициализирована")
        
    def on_token_changed(self, token: str):
        """Обработка изменения выбранного токена"""
        self.custom_token_input.setEnabled(token == "Другой")
        
    def import_from_file(self):
        """Импорт адресов из файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Выберите файл с адресами ({self.slot_id})",
            "",
            "Text Files (*.txt);;CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        try:
            addresses = []
            
            if file_path.endswith('.xlsx'):
                # Импорт из Excel
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(file_path)
                    sheet = wb.active
                    
                    for row in sheet.iter_rows(values_only=True):
                        if row and row[0]:
                            addr = str(row[0]).strip()
                            if self.is_valid_address(addr):
                                addresses.append(addr)
                except ImportError:
                    self.log("Библиотека openpyxl не установлена", "ERROR")
                    return
            else:
                # Импорт из текстового/CSV файла
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        # Обработка CSV (если есть запятые)
                        if ',' in line:
                            addr = line.split(',')[0].strip()
                        else:
                            addr = line.strip()
                        
                        if self.is_valid_address(addr):
                            addresses.append(addr)
            
            self.add_addresses(addresses)
            self.log(f"[{self.slot_id}] Импортировано {len(addresses)} адресов из файла", "SUCCESS")
            
        except Exception as e:
            self.log(f"[{self.slot_id}] Ошибка импорта из файла: {e}", "ERROR")
            
    def import_from_clipboard(self):
        """Импорт адресов из буфера обмена"""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            
            if not text:
                self.log("Буфер обмена пуст", "WARNING")
                return
                
            addresses = []
            for line in text.split('\n'):
                addr = line.strip()
                if self.is_valid_address(addr):
                    addresses.append(addr)
                    
            self.add_addresses(addresses)
            self.log(f"[{self.slot_id}] Импортировано {len(addresses)} адресов из буфера обмена", "SUCCESS")
            
        except Exception as e:
            self.log(f"Ошибка импорта из буфера обмена: {e}", "ERROR")
            
    def is_valid_address(self, address: str) -> bool:
        """Проверка валидности адреса"""
        if not address:
            return False
            
        # Базовая проверка формата
        if not address.startswith('0x'):
            return False
            
        if len(address) != 42:
            return False
            
        # Проверка на hex символы
        try:
            int(address, 16)
            return True
        except ValueError:
            return False
            
    def add_addresses(self, addresses: List[str]):
        """Добавление адресов в таблицу"""
        for addr in addresses:
            if addr not in self.addresses:
                self.addresses.append(addr)
                
                row = self.addresses_table.rowCount()
                self.addresses_table.insertRow(row)
                
                # Адрес
                self.addresses_table.setItem(row, 0, QTableWidgetItem(addr))
                
                # Статус
                status_item = QTableWidgetItem("Ожидает")
                self.addresses_table.setItem(row, 1, status_item)
                
                # Tx Hash
                self.addresses_table.setItem(row, 2, QTableWidgetItem(""))
                
        self.update_statistics()
        
    def clear_addresses(self):
        """Очистка списка адресов"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите очистить список адресов?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.addresses.clear()
            self.addresses_table.setRowCount(0)
            self.update_statistics()
            self.log("Список адресов очищен")
            
    def update_statistics(self):
        """Обновление статистики"""
        total = len(self.addresses)
        processed = 0
        success = 0
        failed = 0
        
        for row in range(self.addresses_table.rowCount()):
            status = self.addresses_table.item(row, 1).text()
            if status != "Ожидает":
                processed += 1
            if status == "✓ Успешно":
                success += 1
            elif status == "✗ Ошибка":
                failed += 1
                
        self.total_addresses_label.setText(f"Всего адресов: {total}")
        self.processed_label.setText(f"Обработано: {processed}")
        self.success_label.setText(f"Успешно: {success}")
        self.failed_label.setText(f"Ошибок: {failed}")
        
        # Обновление прогресса
        if total > 0:
            progress = int((processed / total) * 100)
            self.progress_bar.setValue(progress)
            
    def start_distribution(self):
        """Начать массовую рассылку"""
        if self.is_distributing:
            self.log("Рассылка уже выполняется!", "WARNING")
            return
            
        if not self.addresses:
            self.log("Список адресов пустой! Импортируйте адреса.", "ERROR")
            return
            
        # Получаем настройки
        token_type = self.token_combo.currentText()
        amount = self.amount_input.value()
        cycles = self.cycles_input.value()
        interval = self.interval_input.value()
        
        # Получаем адрес токена
        if token_type == "PLEX ONE":
            token_address = Web3.to_checksum_address(CONTRACTS['PLEX_ONE'])
        elif token_type == "USDT":
            token_address = Web3.to_checksum_address(CONTRACTS['USDT'])
        else:
            token_address = self.custom_token_input.text().strip()
            if not token_address or not Web3.is_address(token_address):
                self.log("Введите корректный адрес токена!", "ERROR")
                return
            token_address = Web3.to_checksum_address(token_address)
        
        # Проверяем подключение кошелька
        if not self.account:
            self.log("Кошелек не подключен! Загрузите приватный ключ.", "ERROR")
            return
            
        # Инициализируем сервисы если не созданы
        self._init_services()
        
        self.log(f"🚀 Начинаем массовую рассылку {token_type} (Слот {self.slot_number})", "SUCCESS")
        self.log(f"📊 Параметры: {amount} токенов, {cycles} циклов, интервал {interval}с", "INFO")
        self.log(f"📋 Адресов в списке: {len(self.addresses)}", "INFO")
        
        # Настраиваем UI
        self.is_distributing = True
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setMaximum(len(self.addresses) * cycles)
        self.progress_bar.setValue(0)
        
        # Запускаем поток рассылки
        self.stop_flag.clear()
        self.distribution_thread = threading.Thread(
            target=self._distribution_worker,
            args=(token_type, token_address, amount, cycles, interval),
            daemon=False  # Важно: не daemon поток
        )
        self.distribution_thread.start()
        
        
    def _distribution_worker(self, token_type: str, token_address: str, amount: float, cycles: int, interval: int):
        """Основной рабочий поток массовой рассылки"""
        try:
            total_sent = 0
            total_errors = 0
            
            self.log(f"🔄 Начат рабочий поток массовой рассылки (Слот {self.slot_number})", "INFO")
            
            for cycle in range(1, cycles + 1):
                if self.stop_flag.is_set():
                    self.log(f"⏹️ Рассылка остановлена на цикле {cycle}", "WARNING")
                    break
                    
                self.log(f"🔄 Цикл {cycle}/{cycles}", "INFO")
                
                for i, address in enumerate(self.addresses):
                    if self.stop_flag.is_set():
                        break
                        
                    # Проверка паузы
                    while self.is_paused and not self.stop_flag.is_set():
                        time.sleep(0.5)
                        
                    if self.stop_flag.is_set():
                        break
                        
                    # Обновляем статус адреса
                    self.address_status_update.emit(i, "Отправка...")
                    
                    try:
                        # Отправляем транзакцию
                        if token_type == "BNB":
                            result = self._send_bnb(address, amount)
                        else:
                            result = self._send_token(address, amount, token_address)
                            
                        if result and result.get('success'):
                            total_sent += 1
                            tx_hash = result.get('tx_hash', '')
                            self.address_status_update.emit(i, f"Успешно: {tx_hash[:10]}...")
                            self.transaction_completed.emit({
                                'address': address,
                                'cycle': cycle,
                                'tx_hash': tx_hash,
                                'status': 'success',
                                'amount': amount,
                                'token': token_type
                            })
                            self.log(f"✅ {address}: {amount} {token_type}, tx: {tx_hash[:20]}...", "SUCCESS")
                        else:
                            total_errors += 1
                            error = result.get('error', 'Неизвестная ошибка') if result else 'Нет результата'
                            self.address_status_update.emit(i, f"Ошибка: {error}")
                            self.log(f"❌ {address}: {error}", "ERROR")
                            
                    except Exception as e:
                        total_errors += 1
                        error_msg = str(e)
                        self.address_status_update.emit(i, f"Ошибка: {error_msg}")
                        self.log(f"❌ {address}: {error_msg}", "ERROR")
                        logger.exception(f"Ошибка отправки на {address}")
                        
                    # Обновляем прогресс
                    current_progress = (cycle - 1) * len(self.addresses) + i + 1
                    QTimer.singleShot(0, lambda p=current_progress: self.progress_bar.setValue(p))
                    
                    # Пауза между отправками
                    if not self.stop_flag.is_set() and i < len(self.addresses) - 1:
                        time.sleep(interval)
                        
                # Пауза между циклами (если не последний цикл)
                if cycle < cycles and not self.stop_flag.is_set():
                    self.log(f"⏳ Пауза между циклами: {interval} секунд", "INFO")
                    time.sleep(interval)
                    
            self.log(f"🏁 Рассылка завершена! Отправлено: {total_sent}, ошибок: {total_errors}", "SUCCESS")
            
        except Exception as e:
            self.log(f"💥 Критическая ошибка в потоке рассылки: {str(e)}", "ERROR")
            logger.exception("Ошибка в _distribution_worker")
            
        finally:
            # Завершаем рассылку
            QTimer.singleShot(0, self.distribution_finished.emit)

    # Остальные методы класса...
    # (продолжение методов для управления кошельком, отправки транзакций и т.д.)
    
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

    # Дополнительные методы-заглушки для полноты функционала
    def connect_wallet(self):
        """Подключение кошелька"""
        pass
        
    def disconnect_wallet(self):
        """Отключение кошелька"""
        pass
        
    def update_balances(self):
        """Обновление балансов"""
        pass
        
    def _update_balance_display(self, balances: dict):
        """Обновление отображения балансов"""
        pass
        
    def _toggle_auto_refresh(self, enabled: bool):
        """Переключение авто-обновления"""
        pass
        
    def _init_services(self):
        """Инициализация сервисов"""
        pass
        
    def _send_bnb(self, to_address: str, amount: float) -> Dict[str, Any]:
        """Отправка BNB"""
        return {'success': False, 'error': 'Not implemented'}
        
    def _send_token(self, to_address: str, amount: float, token_address: str) -> Dict[str, Any]:
        """Отправка токена"""
        return {'success': False, 'error': 'Not implemented'}
        
    @pyqtSlot(int, str)
    def update_address_status(self, row: int, status: str):
        """Обновление статуса адреса"""
        pass
        
    @pyqtSlot(dict)
    def on_transaction_completed(self, tx_info: Dict[str, Any]):
        """Обработка завершенной транзакции"""
        pass
        
    @pyqtSlot()
    def on_distribution_finished(self):
        """Обработка завершения рассылки"""
        pass
        
    def pause_distribution(self):
        """Приостановка рассылки"""
        pass
        
    def stop_distribution(self):
        """Остановка рассылки"""
        pass
        
    def export_results(self):
        """Экспорт результатов"""
        pass
