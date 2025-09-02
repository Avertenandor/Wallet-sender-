"""
Вкладка системы наград с полным функционалом
"""

import json
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QWidget,
    QPushButton, QTableWidget, QTableWidgetItem, QProgressBar,
    QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QHeaderView,
    QAbstractItemView, QMessageBox, QMenu, QApplication,
    QFileDialog, QDialog, QDialogButtonBox, QListWidget,
    QCheckBox, QSplitter
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt5.QtGui import QColor

from web3 import Web3
import csv

from .base_tab import BaseTab
from ...core.wallet_manager import WalletManager
from ...services.token_service import TokenService
from ...services.job_router import get_job_router
from ...constants import PLEX_CONTRACT, USDT_CONTRACT
from ...database.database import Database
from ...utils.logger import get_logger

logger = get_logger(__name__)


class RewardsTab(BaseTab):
    """Вкладка управления системой наград"""
    
    # Сигналы
    update_rewards_signal = pyqtSignal(list)
    sending_progress_signal = pyqtSignal(int, str)
    reward_sent_signal = pyqtSignal(str, bool, str)  # address, success, tx_hash
    
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)

        # Инициализация сервисов
        self.wallet_manager = None
        self.wallet_sender = None
        self.token_service = None
        self.database = Database()
        self.job_router = get_job_router()
        self.current_job_id = None
        self.current_job_tag = None

        # Переменные состояния
        self.rewards_list = []
        self.selected_rewards = []
        self.is_sending = False
        self.rewards_configs = {}
        
        # Регистрируем колбеки для событий задач
        self.job_router.register_callback('job_progress', self._on_job_progress)
        self.job_router.register_callback('job_completed', self._on_job_completed)
        self.job_router.register_callback('job_failed', self._on_job_failed)

        # Подключение сигналов
        self.update_rewards_signal.connect(self._update_rewards_table)
        self.sending_progress_signal.connect(self._update_sending_progress)
        self.reward_sent_signal.connect(self._on_reward_sent)
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QGroupBox("Система наград")
        header_layout = QVBoxLayout(header)
        header_label = QLabel("🎁 Управление наградами за транзакции")
        header_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        header_layout.addWidget(header_label)
        layout.addWidget(header)
        
        # Splitter для основного контента
        splitter = QSplitter(Qt.Horizontal)
        
        # Левая панель - список наград
        left_widget = self._create_rewards_panel()
        splitter.addWidget(left_widget)
        
        # Правая панель - конфигурации и управление
        right_widget = self._create_control_panel()
        splitter.addWidget(right_widget)
        
        splitter.setSizes([700, 400])
        layout.addWidget(splitter)
        
        # Панель статуса
        status_group = self._create_status_panel()
        layout.addWidget(status_group)
        
        # Лог операций
        log_group = QGroupBox("Лог операций")
        log_layout = QVBoxLayout(log_group)
        
        self.operation_log = QTextEdit()
        self.operation_log.setReadOnly(True)
        self.operation_log.setMaximumHeight(100)
        log_layout.addWidget(self.operation_log)
        
        layout.addWidget(log_group)
        
    @pyqtSlot(list)
    def _update_rewards_table(self, rewards: List[Dict[str, Any]]):
        """Обновление таблицы наград из списка.
        Ожидается список словарей с ключами: address, amount, token, source, created_at, status, tx_hash.
        """
        try:
            self.rewards_list = rewards or []
            self.rewards_table.setRowCount(0)
            for reward in self.rewards_list:
                row = self.rewards_table.rowCount()
                self.rewards_table.insertRow(row)
                # ✓ чекбокс
                check_item = QTableWidgetItem()
                check_item.setCheckState(Qt.Checked)
                self.rewards_table.setItem(row, 0, check_item)
                # Адрес
                addr_item = QTableWidgetItem(reward.get('address', ''))
                addr_item.setData(Qt.UserRole, reward.get('address', ''))
                self.rewards_table.setItem(row, 1, addr_item)
                # Сумма
                self.rewards_table.setItem(row, 2, QTableWidgetItem(str(reward.get('amount', ''))))
                # Токен
                self.rewards_table.setItem(row, 3, QTableWidgetItem(reward.get('token', '')))
                # Источник
                self.rewards_table.setItem(row, 4, QTableWidgetItem(reward.get('source', '')))
                # Дата
                self.rewards_table.setItem(row, 5, QTableWidgetItem(reward.get('created_at', '')))
                # Статус
                self.rewards_table.setItem(row, 6, QTableWidgetItem(reward.get('status', 'New')))
                # TX Hash
                tx = reward.get('tx_hash', '')
                tx_item = QTableWidgetItem(f"{tx[:10]}..." if tx else '')
                tx_item.setData(Qt.UserRole, tx)
                self.rewards_table.setItem(row, 7, tx_item)
            self._update_statistics()
        except Exception as e:
            logger.error(f"Ошибка обновления таблицы наград: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить список наград: {e}")

    def _create_rewards_panel(self) -> QWidget:
        """Создание панели со списком наград"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Заголовок
        layout.addWidget(QLabel("📋 Список наград для отправки"))
        
        # Таблица наград
        self.rewards_table = QTableWidget(0, 8)
        self.rewards_table.setHorizontalHeaderLabels([
            '✓', 'Адрес получателя', 'Сумма', 'Токен', 
            'Источник', 'Дата добавления', 'Статус', 'TX Hash'
        ])
        
        header = self.rewards_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.resizeSection(0, 30)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            for i in range(2, 8):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.rewards_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rewards_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.rewards_table.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.rewards_table)
        
        # Кнопки управления списком
        buttons_layout = QHBoxLayout()
        
        self.add_reward_btn = QPushButton("➕ Добавить награду")
        self.add_reward_btn.clicked.connect(self.add_reward_manual)
        buttons_layout.addWidget(self.add_reward_btn)
        
        self.import_csv_btn = QPushButton("📥 Импорт из CSV")
        self.import_csv_btn.clicked.connect(self.import_from_csv)
        buttons_layout.addWidget(self.import_csv_btn)
        
        self.export_csv_btn = QPushButton("📤 Экспорт в CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        buttons_layout.addWidget(self.export_csv_btn)
        
        self.clear_btn = QPushButton("🗑 Очистить список")
        self.clear_btn.clicked.connect(self.clear_rewards)
        buttons_layout.addWidget(self.clear_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Кнопки выбора
        select_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("☑ Выбрать все")
        self.select_all_btn.clicked.connect(self.select_all_rewards)
        select_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("☐ Снять выбор")
        self.deselect_all_btn.clicked.connect(self.deselect_all_rewards)
        select_layout.addWidget(self.deselect_all_btn)
        
        self.remove_selected_btn = QPushButton("❌ Удалить выбранные")
        self.remove_selected_btn.clicked.connect(self.remove_selected_rewards)
        select_layout.addWidget(self.remove_selected_btn)
        
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        return widget
        
    def _create_control_panel(self) -> QWidget:
        """Создание панели управления"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Конфигурации наград
        config_group = QGroupBox("Конфигурации наград")
        config_layout = QVBoxLayout(config_group)
        
        # Список сохраненных конфигураций
        config_layout.addWidget(QLabel("Сохраненные конфигурации:"))
        
        self.configs_list = QListWidget()
        self.configs_list.setMaximumHeight(100)
        self.configs_list.itemDoubleClicked.connect(self.load_config)
        config_layout.addWidget(self.configs_list)
        
        # Кнопки управления конфигурациями
        config_buttons_layout = QHBoxLayout()
        
        self.save_config_btn = QPushButton("💾 Сохранить")
        self.save_config_btn.clicked.connect(self.save_config)
        config_buttons_layout.addWidget(self.save_config_btn)
        
        self.load_config_btn = QPushButton("📂 Загрузить")
        self.load_config_btn.clicked.connect(self.load_config)
        config_buttons_layout.addWidget(self.load_config_btn)
        
        self.delete_config_btn = QPushButton("🗑 Удалить")
        self.delete_config_btn.clicked.connect(self.delete_config)
        config_buttons_layout.addWidget(self.delete_config_btn)
        
        config_layout.addLayout(config_buttons_layout)
        
        layout.addWidget(config_group)
        
        # Параметры отправки
        sending_group = QGroupBox("Параметры отправки")
        sending_layout = QVBoxLayout(sending_group)
        
        # Выбор токена
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Токен награды:"))
        
        self.reward_token_combo = QComboBox()
        self.reward_token_combo.addItems(['PLEX ONE', 'USDT', 'BNB'])
        token_layout.addWidget(self.reward_token_combo)
        
        sending_layout.addLayout(token_layout)
        
        # Сумма награды
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("Сумма награды:"))
        
        self.reward_amount = QDoubleSpinBox()
        self.reward_amount.setRange(0.00001, 10000)
        self.reward_amount.setDecimals(8)
        self.reward_amount.setValue(0.1)
        amount_layout.addWidget(self.reward_amount)
        
        self.use_percentage = QCheckBox("% от суммы TX")
        amount_layout.addWidget(self.use_percentage)
        
        self.percentage_amount = QDoubleSpinBox()
        self.percentage_amount.setRange(0.01, 100)
        self.percentage_amount.setDecimals(2)
        self.percentage_amount.setValue(1.0)
        self.percentage_amount.setSuffix(" %")
        self.percentage_amount.setEnabled(False)
        amount_layout.addWidget(self.percentage_amount)
        
        self.use_percentage.toggled.connect(self.percentage_amount.setEnabled)
        self.use_percentage.toggled.connect(lambda checked: self.reward_amount.setEnabled(not checked))
        
        sending_layout.addLayout(amount_layout)
        
        # Параметры газа
        gas_layout = QHBoxLayout()
        gas_layout.addWidget(QLabel("Цена газа (Gwei):"))
        
        self.gas_price = QDoubleSpinBox()
        self.gas_price.setRange(1, 100)
        self.gas_price.setDecimals(1)
        self.gas_price.setValue(5)
        gas_layout.addWidget(self.gas_price)
        
        gas_layout.addWidget(QLabel("Лимит газа:"))
        
        self.gas_limit = QSpinBox()
        self.gas_limit.setRange(21000, 500000)
        self.gas_limit.setValue(100000)
        gas_layout.addWidget(self.gas_limit)
        
        sending_layout.addLayout(gas_layout)
        
        # Задержка между отправками
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Задержка между отправками (сек):"))
        
        self.send_delay = QDoubleSpinBox()
        self.send_delay.setRange(0.1, 60)
        self.send_delay.setValue(2)
        self.send_delay.setSingleStep(0.5)
        delay_layout.addWidget(self.send_delay)
        
        sending_layout.addLayout(delay_layout)
        
        layout.addWidget(sending_group)
        
        # Кнопки отправки
        send_buttons_group = QGroupBox("Управление отправкой")
        send_buttons_layout = QVBoxLayout(send_buttons_group)
        
        self.send_rewards_btn = QPushButton("🚀 Отправить выбранные награды")
        self.send_rewards_btn.clicked.connect(self.start_sending_rewards)
        send_buttons_layout.addWidget(self.send_rewards_btn)
        
        self.stop_sending_btn = QPushButton("⏹ Остановить отправку")
        self.stop_sending_btn.setEnabled(False)
        self.stop_sending_btn.clicked.connect(self.stop_sending_rewards)
        send_buttons_layout.addWidget(self.stop_sending_btn)
        
        # Прогресс отправки
        self.sending_progress = QProgressBar()
        send_buttons_layout.addWidget(self.sending_progress)
        
        self.sending_status = QLabel("Готов к отправке")
        send_buttons_layout.addWidget(self.sending_status)
        
        layout.addWidget(send_buttons_group)
        
        layout.addStretch()
        
        return widget
        
    def _create_status_panel(self) -> QGroupBox:
        """Создание панели статуса"""
        group = QGroupBox("Статистика")
        layout = QHBoxLayout(group)
        
        # Общее количество
        self.total_rewards_label = QLabel("Всего наград: 0")
        layout.addWidget(self.total_rewards_label)
        
        # Выбрано
        self.selected_rewards_label = QLabel("Выбрано: 0")
        layout.addWidget(self.selected_rewards_label)
        
        # Отправлено
        self.sent_rewards_label = QLabel("Отправлено: 0")
        layout.addWidget(self.sent_rewards_label)
        
        # Ошибки
        self.failed_rewards_label = QLabel("Ошибок: 0")
        layout.addWidget(self.failed_rewards_label)
        
        layout.addStretch()
        
        # Общая сумма
        self.total_amount_label = QLabel("Общая сумма: 0")
        layout.addWidget(self.total_amount_label)
        
        return group
        
    def add_reward_manual(self):
        """Добавление награды вручную"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить награду")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Адрес получателя
        layout.addWidget(QLabel("Адрес получателя:"))
        address_input = QLineEdit()
        address_input.setPlaceholderText("0x...")
        layout.addWidget(address_input)
        
        # Сумма
        layout.addWidget(QLabel("Сумма:"))
        amount_input = QDoubleSpinBox()
        amount_input.setRange(0.00001, 10000)
        amount_input.setDecimals(8)
        amount_input.setValue(0.1)
        layout.addWidget(amount_input)
        
        # Токен
        layout.addWidget(QLabel("Токен:"))
        token_combo = QComboBox()
        token_combo.addItems(['PLEX ONE', 'USDT', 'BNB'])
        layout.addWidget(token_combo)
        
        # Источник
        layout.addWidget(QLabel("Источник (опционально):"))
        source_input = QLineEdit()
        source_input.setPlaceholderText("TX hash или описание")
        layout.addWidget(source_input)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            address = address_input.text().strip()
            
            if not address:
                QMessageBox.warning(self, "Ошибка", "Введите адрес получателя!")
                return
                
            if not Web3.is_address(address):
                QMessageBox.warning(self, "Ошибка", "Некорректный адрес!")
                return
                
            # Добавляем награду
            reward = {
                'address': address,
                'amount': amount_input.value(),
                'token': token_combo.currentText(),
                'source': source_input.text() or 'Manual',
                'date_added': datetime.now(),
                'status': 'Pending',
                'tx_hash': ''
            }
            
            self.rewards_list.append(reward)
            self._add_reward_to_table(reward)
            self._update_statistics()
            
            self.log(f"Добавлена награда: {address[:8]}...{address[-6:]} - {reward['amount']} {reward['token']}", "SUCCESS")
            
    def import_from_csv(self):
        """Импорт наград из CSV файла"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт наград из CSV",
            "",
            "CSV Files (*.csv)"
        )
        
        if not path:
            return
            
        try:
            imported_count = 0
            
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Проверяем обязательные поля
                    if 'address' not in row or 'amount' not in row:
                        continue
                        
                    address = row['address'].strip()
                    
                    if not Web3.is_address(address):
                        continue
                        
                    try:
                        amount = float(row['amount'])
                    except ValueError:
                        continue
                        
                    # Создаем награду
                    reward = {
                        'address': address,
                        'amount': amount,
                        'token': row.get('token', 'PLEX ONE'),
                        'source': row.get('source', 'CSV Import'),
                        'date_added': datetime.now(),
                        'status': 'Pending',
                        'tx_hash': ''
                    }
                    
                    self.rewards_list.append(reward)
                    self._add_reward_to_table(reward)
                    imported_count += 1
                    
            self._update_statistics()
            
            self.log(f"✅ Импортировано {imported_count} наград", "SUCCESS")
            QMessageBox.information(self, "Успех", f"Импортировано {imported_count} наград из CSV")
            
        except Exception as e:
            logger.error(f"Ошибка импорта CSV: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка импорта:\n{str(e)}")
            
    def export_to_csv(self):
        """Экспорт наград в CSV файл"""
        if not self.rewards_list:
            QMessageBox.warning(self, "Предупреждение", "Нет наград для экспорта!")
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт наград в CSV",
            f"rewards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not path:
            return
            
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['address', 'amount', 'token', 'source', 'date_added', 'status', 'tx_hash']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                
                for reward in self.rewards_list:
                    row = reward.copy()
                    if isinstance(row['date_added'], datetime):
                        row['date_added'] = row['date_added'].isoformat()
                    writer.writerow(row)
                    
            self.log(f"✅ Экспортировано {len(self.rewards_list)} наград", "SUCCESS")
            QMessageBox.information(self, "Успех", f"Данные экспортированы в:\n{path}")
            
        except Exception as e:
            logger.error(f"Ошибка экспорта CSV: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта:\n{str(e)}")
            
    def _add_reward_to_table(self, reward: Dict):
        """Добавление награды в таблицу"""
        row = self.rewards_table.rowCount()
        self.rewards_table.insertRow(row)
        
        # Чекбокс
        checkbox = QTableWidgetItem()
        checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        checkbox.setCheckState(Qt.Unchecked)
        self.rewards_table.setItem(row, 0, checkbox)
        
        # Адрес
        address = reward['address']
        address_item = QTableWidgetItem(f"{address[:8]}...{address[-6:]}")
        address_item.setData(Qt.UserRole, address)  # Сохраняем полный адрес
        self.rewards_table.setItem(row, 1, address_item)
        
        # Сумма
        self.rewards_table.setItem(row, 2, QTableWidgetItem(f"{reward['amount']:.8f}"))
        
        # Токен
        self.rewards_table.setItem(row, 3, QTableWidgetItem(reward['token']))
        
        # Источник
        self.rewards_table.setItem(row, 4, QTableWidgetItem(reward['source']))
        
        # Дата добавления
        date_str = reward['date_added'].strftime('%Y-%m-%d %H:%M') if isinstance(reward['date_added'], datetime) else str(reward['date_added'])
        self.rewards_table.setItem(row, 5, QTableWidgetItem(date_str))
        
        # Статус
        status_item = QTableWidgetItem(reward['status'])
        if reward['status'] == 'Sent':
            status_item.setBackground(QColor('#004400'))
        elif reward['status'] == 'Failed':
            status_item.setBackground(QColor('#440000'))
        self.rewards_table.setItem(row, 6, status_item)
        
        # TX Hash
        tx_hash = reward.get('tx_hash', '')
        if tx_hash:
            tx_item = QTableWidgetItem(f"{tx_hash[:10]}...")
            tx_item.setData(Qt.UserRole, tx_hash)
        else:
            tx_item = QTableWidgetItem("")
        self.rewards_table.setItem(row, 7, tx_item)
        
    def _update_statistics(self):
        """Обновление статистики"""
        total = len(self.rewards_list)
        selected = sum(1 for i in range(self.rewards_table.rowCount()) 
                      if self.rewards_table.item(i, 0).checkState() == Qt.Checked)
        sent = sum(1 for r in self.rewards_list if r['status'] == 'Sent')
        failed = sum(1 for r in self.rewards_list if r['status'] == 'Failed')
        
        self.total_rewards_label.setText(f"Всего наград: {total}")
        self.selected_rewards_label.setText(f"Выбрано: {selected}")
        self.sent_rewards_label.setText(f"Отправлено: {sent}")
        self.failed_rewards_label.setText(f"Ошибок: {failed}")
        
        # Считаем общую сумму выбранных
        total_amount = 0
        for i in range(self.rewards_table.rowCount()):
            if self.rewards_table.item(i, 0).checkState() == Qt.Checked:
                amount_text = self.rewards_table.item(i, 2).text()
                try:
                    total_amount += float(amount_text)
                except:
                    pass
                    
        self.total_amount_label.setText(f"Общая сумма: {total_amount:.8f}")
        
    def select_all_rewards(self):
        """Выбрать все награды"""
        for i in range(self.rewards_table.rowCount()):
            self.rewards_table.item(i, 0).setCheckState(Qt.Checked)
        self._update_statistics()
        
    def deselect_all_rewards(self):
        """Снять выбор со всех наград"""
        for i in range(self.rewards_table.rowCount()):
            self.rewards_table.item(i, 0).setCheckState(Qt.Unchecked)
        self._update_statistics()
        
    def remove_selected_rewards(self):
        """Удалить выбранные награды"""
        rows_to_remove = []
        
        for i in range(self.rewards_table.rowCount()):
            if self.rewards_table.item(i, 0).checkState() == Qt.Checked:
                rows_to_remove.append(i)
                
        if not rows_to_remove:
            QMessageBox.warning(self, "Предупреждение", "Выберите награды для удаления!")
            return
            
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить {len(rows_to_remove)} выбранных наград?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Удаляем в обратном порядке чтобы не сбить индексы
            for row in reversed(rows_to_remove):
                self.rewards_table.removeRow(row)
                del self.rewards_list[row]
                
            self._update_statistics()
            self.log(f"Удалено {len(rows_to_remove)} наград", "INFO")
            
    def clear_rewards(self):
        """Очистить весь список наград"""
        if not self.rewards_list:
            return
            
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Очистить весь список наград?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.rewards_table.setRowCount(0)
            self.rewards_list.clear()
            self._update_statistics()
            self.log("Список наград очищен", "INFO")
            
    def start_sending_rewards(self):
        """Начать отправку наград через JobRouter"""
        if self.is_sending:
            QMessageBox.warning(self, "Предупреждение", "Отправка уже запущена!")
            return
            
        # Собираем выбранные награды
        selected_rewards = []
        for i in range(self.rewards_table.rowCount()):
            if self.rewards_table.item(i, 0).checkState() == Qt.Checked:
                if i < len(self.rewards_list) and self.rewards_list[i]['status'] != 'Sent':
                    reward = self.rewards_list[i].copy()
                    reward['row_index'] = i  # Сохраняем индекс строки
                    selected_rewards.append(reward)
                    
        if not selected_rewards:
            QMessageBox.warning(self, "Предупреждение", "Выберите награды для отправки!")
            return
            
        # Проверяем наличие приватного ключа
        if not self.wallet_manager or not self.wallet_manager.get_private_key():
            QMessageBox.critical(self, "Ошибка", "Не загружен приватный ключ кошелька!")
            return
            
        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение отправки",
            f"Отправить {len(selected_rewards)} наград?\n\n"
            f"Токен: {self.reward_token_combo.currentText()}\n"
            f"Газ: {self.gas_price.value()} Gwei",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # Определяем токен
        token_name = self.reward_token_combo.currentText()
        if token_name == 'PLEX ONE':
            token_address = PLEX_CONTRACT
        elif token_name == 'USDT':
            token_address = USDT_CONTRACT
        else:
            token_address = 'BNB'
        
        # Формируем конфигурацию для JobRouter
        rewards_config = {
            'rewards': selected_rewards,
            'token_address': token_address,
            'token_name': token_name,
            'gas_price': self.gas_price.value(),
            'gas_limit': self.gas_limit.value(),
            'delay_between_tx': self.send_delay.value(),
            'use_percentage': self.use_percentage.isChecked(),
            'percentage_amount': self.percentage_amount.value() if self.use_percentage.isChecked() else None,
            'fixed_amount': self.reward_amount.value() if not self.use_percentage.isChecked() else None
        }
        
        # Создаем тег для задачи
        from datetime import datetime
        self.current_job_tag = f"rewards_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Отправляем задачу в JobRouter
            self.current_job_id = self.job_router.submit_rewards(
                rewards_config=rewards_config,
                sender_key=self.wallet_manager.get_private_key(),
                tag=self.current_job_tag,
                priority=7  # Высокий приоритет для наград
            )
            
            # Обновляем состояние
            self.is_sending = True
            self.selected_rewards = selected_rewards
            
            # Обновляем UI
            self.send_rewards_btn.setEnabled(False)
            self.stop_sending_btn.setEnabled(True)
            self.sending_progress.setValue(0)
            
            self.log(f"🚀 Задача отправки {len(selected_rewards)} наград добавлена в очередь (ID: {self.current_job_id})", "SUCCESS")
            
            # Запускаем таймер для обновления статуса
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self._update_job_status)
            self.update_timer.start(1000)  # Обновляем каждую секунду
            
        except Exception as e:
            logger.error(f"Ошибка отправки задачи наград: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать задачу: {str(e)}")
            self.is_sending = False
        
    def stop_sending_rewards(self):
        """Остановить отправку наград через JobRouter"""
        if self.is_sending and self.current_job_id:
            try:
                if self.job_router.cancel_job(self.current_job_id):
                    self.log(f"⏹ Задача #{self.current_job_id} отменена", "WARNING")
                    self._on_sending_finished()
                else:
                    self.log("Не удалось отменить задачу", "ERROR")
            except Exception as e:
                logger.error(f"Ошибка отмены задачи: {e}")
                self.log(f"Ошибка отмены: {str(e)}", "ERROR")
            
    def _update_job_status(self):
        """Обновление статуса текущей задачи"""
        if not self.current_job_id:
            return
            
        try:
            progress = self.job_router.get_progress(self.current_job_id)
            if progress:
                # Обновляем прогресс-бар
                if progress['total'] > 0:
                    percent = int((progress['done'] / progress['total']) * 100)
                    self.sending_progress.setValue(percent)
                    self.sending_status.setText(
                        f"Отправлено {progress['done']}/{progress['total']} (Ошибок: {progress['failed']})"
                    )
                
                # Проверяем завершение
                if progress['is_completed']:
                    self.update_timer.stop()
                    self._on_sending_finished()
                    
        except Exception as e:
            logger.error(f"Ошибка обновления статуса задачи: {e}")
    
    def _on_job_progress(self, job_id: int, progress: Dict):
        """Колбек прогресса задачи"""
        if job_id != self.current_job_id:
            return
            
        # Обновляем UI через сигнал
        if progress['total'] > 0:
            percent = int((progress['done'] / progress['total']) * 100)
            message = f"Отправлено {progress['done']}/{progress['total']}"
            self.sending_progress_signal.emit(percent, message)
    
    def _on_job_completed(self, job_id: int):
        """Колбек завершения задачи"""
        if job_id != self.current_job_id:
            return
            
        self._log_operation("🏁 Отправка наград завершена успешно")
        self.sending_progress_signal.emit(100, "Завершено")
        
        # Обновляем статусы наград в таблице
        for reward in self.selected_rewards:
            if 'row_index' in reward:
                row = reward['row_index']
                if row < self.rewards_table.rowCount():
                    status_item = self.rewards_table.item(row, 6)
                    status_item.setText('Sent')
                    status_item.setBackground(QColor('#004400'))
        
        self._on_sending_finished()
    
    def _on_job_failed(self, job_id: int):
        """Колбек ошибки задачи"""
        if job_id != self.current_job_id:
            return
            
        self._log_operation("❌ Отправка наград завершилась с ошибкой")
        self.sending_progress_signal.emit(100, "Ошибка")
        self._on_sending_finished()
            
    def _log_operation(self, message: str):
        """Логирование операции"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        QTimer.singleShot(0, lambda: self.operation_log.append(f"[{timestamp}] {message}"))
        
    @pyqtSlot(int, str)
    def _update_sending_progress(self, value: int, message: str):
        """Обновление прогресса отправки"""
        self.sending_progress.setValue(value)
        self.sending_status.setText(message)
        
    @pyqtSlot(str, bool, str)
    def _on_reward_sent(self, address: str, success: bool, tx_hash: str):
        """Обработка отправленной награды"""
        # Находим награду в списке
        for i, reward in enumerate(self.rewards_list):
            if reward['address'] == address:
                if success:
                    reward['status'] = 'Sent'
                    reward['tx_hash'] = tx_hash
                else:
                    reward['status'] = 'Failed'
                    
                # Обновляем таблицу
                if i < self.rewards_table.rowCount():
                    status_item = self.rewards_table.item(i, 6)
                    status_item.setText(reward['status'])
                    
                    if success:
                        status_item.setBackground(QColor('#004400'))
                        tx_item = self.rewards_table.item(i, 7)
                        tx_item.setText(f"{tx_hash[:10]}...")
                        tx_item.setData(Qt.UserRole, tx_hash)
                    else:
                        status_item.setBackground(QColor('#440000'))
                        
                break
                
        self._update_statistics()
        
    def _on_sending_finished(self):
        """Обработка завершения отправки"""
        # Останавливаем таймер если он работает
        if hasattr(self, 'update_timer') and self.update_timer.isActive():
            self.update_timer.stop()
        
        # Обновляем состояние
        self.is_sending = False
        self.current_job_id = None
        self.current_job_tag = None
        self.selected_rewards = []
        
        # Обновляем UI
        self.send_rewards_btn.setEnabled(True)
        self.stop_sending_btn.setEnabled(False)
        
        # Обновляем статистику
        self._update_statistics()
        
        self.log("Отправка наград завершена", "SUCCESS")
        
    def _show_context_menu(self, position):
        """Показ контекстного меню"""
        if self.rewards_table.currentRow() < 0:
            return
            
        menu = QMenu()
        
        copy_address = menu.addAction("📋 Копировать адрес")
        copy_tx = menu.addAction("📋 Копировать TX hash")
        menu.addSeparator()
        open_bscscan = menu.addAction("🌐 Открыть TX в BscScan")
        menu.addSeparator()
        resend = menu.addAction("🔄 Отправить повторно")
        remove = menu.addAction("❌ Удалить")
        
        action = menu.exec_(self.rewards_table.viewport().mapToGlobal(position))
        
        if action:
            row = self.rewards_table.currentRow()
            
            if action == copy_address:
                address = self.rewards_table.item(row, 1).data(Qt.UserRole)
                QApplication.clipboard().setText(address)
                self.log("Адрес скопирован", "INFO")
                
            elif action == copy_tx:
                tx_hash = self.rewards_table.item(row, 7).data(Qt.UserRole)
                if tx_hash:
                    QApplication.clipboard().setText(tx_hash)
                    self.log("TX hash скопирован", "INFO")
                else:
                    QMessageBox.warning(self, "Предупреждение", "TX hash отсутствует")
                    
            elif action == open_bscscan:
                tx_hash = self.rewards_table.item(row, 7).data(Qt.UserRole)
                if tx_hash:
                    from PyQt5.QtGui import QDesktopServices
                    from PyQt5.QtCore import QUrl
                    url = f"https://bscscan.com/tx/{tx_hash}"
                    QDesktopServices.openUrl(QUrl(url))
                    self.log("Открыто в BscScan", "INFO")
                else:
                    QMessageBox.warning(self, "Предупреждение", "TX hash отсутствует")
                    
            elif action == resend:
                if row < len(self.rewards_list):
                    self.rewards_list[row]['status'] = 'Pending'
                    self.rewards_list[row]['tx_hash'] = ''
                    
                    status_item = self.rewards_table.item(row, 6)
                    status_item.setText('Pending')
                    status_item.setBackground(QColor())
                    
                    tx_item = self.rewards_table.item(row, 7)
                    tx_item.setText('')
                    tx_item.setData(Qt.UserRole, '')
                    
                    self.log("Награда помечена для повторной отправки", "INFO")
                    
            elif action == remove:
                reply = QMessageBox.question(
                    self,
                    "Подтверждение",
                    "Удалить выбранную награду?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.rewards_table.removeRow(row)
                    if row < len(self.rewards_list):
                        del self.rewards_list[row]
                    self._update_statistics()
                    self.log("Награда удалена", "INFO")
                    
    def save_config(self):
        """Сохранение конфигурации наград"""
        from PyQt5.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(
            self,
            "Сохранить конфигурацию",
            "Введите название конфигурации:"
        )
        
        if ok and name:
            config = {
                'token': self.reward_token_combo.currentText(),
                'amount': self.reward_amount.value(),
                'use_percentage': self.use_percentage.isChecked(),
                'percentage': self.percentage_amount.value(),
                'gas_price': self.gas_price.value(),
                'gas_limit': self.gas_limit.value(),
                'delay': self.send_delay.value()
            }
            
            self.rewards_configs[name] = config
            
            # Добавляем в список если еще нет
            items = [self.configs_list.item(i).text() for i in range(self.configs_list.count())]
            if name not in items:
                self.configs_list.addItem(name)
                
            # Сохраняем в файл
            self._save_configs_to_file()
            
            self.log(f"Конфигурация '{name}' сохранена", "SUCCESS")
            QMessageBox.information(self, "Успех", f"Конфигурация '{name}' сохранена!")
            
    def load_config(self):
        """Загрузка конфигурации наград"""
        current_item = self.configs_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Предупреждение", "Выберите конфигурацию для загрузки!")
            return
            
        name = current_item.text()
        if name in self.rewards_configs:
            config = self.rewards_configs[name]
            
            self.reward_token_combo.setCurrentText(config.get('token', 'PLEX ONE'))
            self.reward_amount.setValue(config.get('amount', 0.1))
            self.use_percentage.setChecked(config.get('use_percentage', False))
            self.percentage_amount.setValue(config.get('percentage', 1.0))
            self.gas_price.setValue(config.get('gas_price', 5))
            self.gas_limit.setValue(config.get('gas_limit', 100000))
            self.send_delay.setValue(config.get('delay', 2))
            
            self.log(f"Конфигурация '{name}' загружена", "SUCCESS")
            
    def delete_config(self):
        """Удаление конфигурации"""
        current_item = self.configs_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Предупреждение", "Выберите конфигурацию для удаления!")
            return
            
        name = current_item.text()
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить конфигурацию '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if name in self.rewards_configs:
                del self.rewards_configs[name]
                
            self.configs_list.takeItem(self.configs_list.row(current_item))
            self._save_configs_to_file()
            
            self.log(f"Конфигурация '{name}' удалена", "INFO")
            
    def _save_configs_to_file(self):
        """Сохранение конфигураций в файл"""
        try:
            with open('rewards_configs.json', 'w', encoding='utf-8') as f:
                json.dump(self.rewards_configs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигураций: {e}")
            
    def _load_configs_from_file(self):
        """Загрузка конфигураций из файла"""
        try:
            with open('rewards_configs.json', 'r', encoding='utf-8') as f:
                self.rewards_configs = json.load(f)
                
            # Обновляем список
            self.configs_list.clear()
            for name in self.rewards_configs.keys():
                self.configs_list.addItem(name)
                
        except FileNotFoundError:
            self.rewards_configs = {}
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигураций: {e}")
            self.rewards_configs = {}
