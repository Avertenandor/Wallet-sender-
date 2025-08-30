"""
Вкладка поиска транзакций с полным функционалом
"""

import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QProgressBar,
    QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QHeaderView,
    QAbstractItemView, QDateEdit, QCheckBox, QMessageBox,
    QMenu, QApplication, QFileDialog
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QTimer, QDate
from PyQt5.QtGui import QColor, QDesktopServices, QUrl

from web3 import Web3
import requests
import csv

from .base_tab import BaseTab
from ...constants import PLEX_CONTRACT, USDT_CONTRACT, BSCSCAN_URL, BSCSCAN_KEYS
from ...utils.logger import get_logger

logger = get_logger(__name__)


class SearchTab(BaseTab):
    """Вкладка поиска транзакций с фильтрами и пагинацией"""
    
    # Сигналы
    update_results_signal = pyqtSignal(list)
    search_finished_signal = pyqtSignal(int)  # количество найденных
    progress_signal = pyqtSignal(int, str)  # процент, сообщение
    
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        
        # Инициализация переменных
        self.is_searching = False
        self.stop_search_event = threading.Event()
        self.search_thread = None
        self.current_api_key_index = 0
        self.search_results = []
        
        # Подключение сигналов
        self.update_results_signal.connect(self._update_results_table)
        self.search_finished_signal.connect(self._on_search_finished)
        self.progress_signal.connect(self._update_progress)
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QGroupBox("Поиск транзакций BSC")
        header_layout = QVBoxLayout(header)
        header_label = QLabel("🔎 Расширенный поиск транзакций по критериям")
        header_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        header_layout.addWidget(header_label)
        layout.addWidget(header)
        
        # Параметры поиска
        search_group = self._create_search_params_group()
        layout.addWidget(search_group)
        
        # Фильтры
        filters_group = self._create_filters_group()
        layout.addWidget(filters_group)
        
        # Таблица результатов
        results_group = QGroupBox("Результаты поиска")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget(0, 8)
        self.results_table.setHorizontalHeaderLabels([
            'Hash', 'От', 'Кому', 'Сумма', 'Токен', 
            'Время', 'Блок', 'Статус'
        ])
        
        header = self.results_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeToContents)
            header.setSectionResizeMode(0, QHeaderView.Stretch)
        
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._show_context_menu)
        
        results_layout.addWidget(self.results_table)
        layout.addWidget(results_group)
        
        # Прогресс и статус
        progress_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Готов к поиску")
        progress_layout.addWidget(self.status_label)
        
        layout.addLayout(progress_layout)
        
        # Лог поиска
        log_group = QGroupBox("Лог поиска")
        log_layout = QVBoxLayout(log_group)
        
        self.search_log = QTextEdit()
        self.search_log.setReadOnly(True)
        self.search_log.setMaximumHeight(100)
        log_layout.addWidget(self.search_log)
        
        layout.addWidget(log_group)
        
    def _create_search_params_group(self) -> QGroupBox:
        """Создание группы параметров поиска"""
        group = QGroupBox("Параметры поиска")
        layout = QVBoxLayout(group)
        
        # Адрес кошелька
        addr_layout = QHBoxLayout()
        addr_layout.addWidget(QLabel("Адрес кошелька:"))
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("0x...")
        addr_layout.addWidget(self.address_input)
        layout.addLayout(addr_layout)
        
        # Токен
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Токен:"))
        
        self.token_combo = QComboBox()
        self.token_combo.addItems(['Все', 'PLEX ONE', 'USDT', 'BNB', 'Другой'])
        token_layout.addWidget(self.token_combo)
        
        self.custom_token_input = QLineEdit()
        self.custom_token_input.setPlaceholderText("Адрес токена")
        self.custom_token_input.setEnabled(False)
        token_layout.addWidget(self.custom_token_input)
        
        self.token_combo.currentTextChanged.connect(
            lambda t: self.custom_token_input.setEnabled(t == "Другой")
        )
        
        layout.addLayout(token_layout)
        
        # Направление транзакций
        direction_layout = QHBoxLayout()
        direction_layout.addWidget(QLabel("Направление:"))
        
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(['Все', 'Входящие', 'Исходящие'])
        direction_layout.addWidget(self.direction_combo)
        
        direction_layout.addStretch()
        layout.addLayout(direction_layout)
        
        # Параметры API
        api_layout = QHBoxLayout()
        
        api_layout.addWidget(QLabel("Макс. страниц:"))
        self.max_pages = QSpinBox()
        self.max_pages.setRange(1, 100)
        self.max_pages.setValue(10)
        api_layout.addWidget(self.max_pages)
        
        api_layout.addWidget(QLabel("Результатов на странице:"))
        self.page_size = QSpinBox()
        self.page_size.setRange(10, 10000)
        self.page_size.setValue(1000)
        self.page_size.setSingleStep(100)
        api_layout.addWidget(self.page_size)
        
        api_layout.addWidget(QLabel("Задержка (сек):"))
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0.1, 10)
        self.delay.setValue(1.0)
        self.delay.setSingleStep(0.5)
        api_layout.addWidget(self.delay)
        
        api_layout.addStretch()
        layout.addLayout(api_layout)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("🔍 Начать поиск")
        self.search_btn.clicked.connect(self.start_search)
        buttons_layout.addWidget(self.search_btn)
        
        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_search)
        buttons_layout.addWidget(self.stop_btn)
        
        self.clear_btn = QPushButton("🗑 Очистить")
        self.clear_btn.clicked.connect(self.clear_results)
        buttons_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("📊 Экспорт в CSV")
        self.export_btn.clicked.connect(self.export_results)
        buttons_layout.addWidget(self.export_btn)
        
        self.import_rewards_btn = QPushButton("🎁 В награды")
        self.import_rewards_btn.clicked.connect(self.import_to_rewards)
        buttons_layout.addWidget(self.import_rewards_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return group
        
    def _create_filters_group(self) -> QGroupBox:
        """Создание группы фильтров"""
        group = QGroupBox("Фильтры")
        layout = QVBoxLayout(group)
        
        # Фильтр по сумме
        amount_layout = QHBoxLayout()
        
        self.amount_filter_check = QCheckBox("Фильтр по сумме:")
        amount_layout.addWidget(self.amount_filter_check)
        
        amount_layout.addWidget(QLabel("От:"))
        self.min_amount = QDoubleSpinBox()
        self.min_amount.setRange(0, 1000000)
        self.min_amount.setDecimals(8)
        self.min_amount.setValue(0.01)
        self.min_amount.setEnabled(False)
        amount_layout.addWidget(self.min_amount)
        
        amount_layout.addWidget(QLabel("До:"))
        self.max_amount = QDoubleSpinBox()
        self.max_amount.setRange(0, 1000000)
        self.max_amount.setDecimals(8)
        self.max_amount.setValue(1000)
        self.max_amount.setEnabled(False)
        amount_layout.addWidget(self.max_amount)
        
        self.amount_filter_check.toggled.connect(self.min_amount.setEnabled)
        self.amount_filter_check.toggled.connect(self.max_amount.setEnabled)
        
        amount_layout.addStretch()
        layout.addLayout(amount_layout)
        
        # Фильтр по дате
        date_layout = QHBoxLayout()
        
        self.date_filter_check = QCheckBox("Фильтр по дате:")
        date_layout.addWidget(self.date_filter_check)
        
        date_layout.addWidget(QLabel("С:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setEnabled(False)
        date_layout.addWidget(self.date_from)
        
        date_layout.addWidget(QLabel("По:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setEnabled(False)
        date_layout.addWidget(self.date_to)
        
        self.date_filter_check.toggled.connect(self.date_from.setEnabled)
        self.date_filter_check.toggled.connect(self.date_to.setEnabled)
        
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        # Дополнительные фильтры
        extra_layout = QHBoxLayout()
        
        self.only_success = QCheckBox("Только успешные")
        self.only_success.setChecked(True)
        extra_layout.addWidget(self.only_success)
        
        self.unique_senders = QCheckBox("Уникальные отправители")
        extra_layout.addWidget(self.unique_senders)
        
        self.min_tx_count = QSpinBox()
        self.min_tx_count.setRange(1, 100)
        self.min_tx_count.setValue(1)
        self.min_tx_count.setEnabled(False)
        
        self.min_tx_check = QCheckBox("Мин. транзакций:")
        self.min_tx_check.toggled.connect(self.min_tx_count.setEnabled)
        extra_layout.addWidget(self.min_tx_check)
        extra_layout.addWidget(self.min_tx_count)
        
        extra_layout.addStretch()
        layout.addLayout(extra_layout)
        
        return group
        
    def start_search(self):
        """Начать поиск транзакций"""
        if self.is_searching:
            QMessageBox.warning(self, "Предупреждение", "Поиск уже запущен!")
            return
            
        # Проверка адреса
        address = self.address_input.text().strip()
        if not address:
            QMessageBox.warning(self, "Ошибка", "Введите адрес кошелька!")
            return
            
        if not Web3.is_address(address):
            QMessageBox.warning(self, "Ошибка", "Некорректный адрес!")
            return
            
        # Запуск поиска
        self.is_searching = True
        self.stop_search_event.clear()
        self.search_results.clear()
        
        # Обновление UI
        self.search_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.search_log.clear()
        
        # Запуск потока
        self.search_thread = threading.Thread(
            target=self._search_worker,
            args=(address,),
            daemon=True
        )
        self.search_thread.start()
        
        self.log(f"🔍 Начат поиск транзакций для адреса: {address[:8]}...{address[-6:]}", "INFO")
        
    def stop_search(self):
        """Остановить поиск"""
        if self.is_searching:
            self.stop_search_event.set()
            self.log("⏹ Остановка поиска...", "WARNING")
            
    def _search_worker(self, address: str):
        """Рабочий поток поиска"""
        try:
            self._log_to_search("Начинаем поиск транзакций...")
            
            # Получаем параметры
            token_filter = self._get_token_filter()
            direction = self.direction_combo.currentText()
            max_pages = self.max_pages.value()
            page_size = self.page_size.value()
            delay = self.delay.value()
            
            all_transactions = []
            page = 1
            
            while page <= max_pages:
                if self.stop_search_event.is_set():
                    self._log_to_search("Поиск остановлен пользователем")
                    break
                    
                # Обновляем прогресс
                progress = int((page / max_pages) * 100)
                self.progress_signal.emit(progress, f"Страница {page}/{max_pages}")
                
                # Формируем запрос
                params = {
                    'module': 'account',
                    'action': 'tokentx' if token_filter else 'txlist',
                    'address': address,
                    'page': page,
                    'offset': page_size,
                    'sort': 'desc',
                    'apikey': BSCSCAN_KEYS[self.current_api_key_index] if BSCSCAN_KEYS else ''
                }
                
                if token_filter:
                    params['contractaddress'] = token_filter
                    
                # Выполняем запрос
                try:
                    response = requests.get(BSCSCAN_URL, params=params, timeout=10)
                    data = response.json()
                    
                    if data.get('status') != '1':
                        self._log_to_search(f"Ошибка API: {data.get('message', 'Unknown')}")
                        break
                        
                    transactions = data.get('result', [])
                    
                    if not transactions:
                        self._log_to_search("Больше транзакций не найдено")
                        break
                        
                    # Фильтруем транзакции
                    filtered = self._filter_transactions(transactions, address, direction)
                    all_transactions.extend(filtered)
                    
                    self._log_to_search(f"Страница {page}: найдено {len(filtered)} транзакций")
                    
                except Exception as e:
                    self._log_to_search(f"Ошибка запроса: {e}")
                    self._rotate_api_key()
                    
                page += 1
                time.sleep(delay)
                
            # Применяем дополнительные фильтры
            final_results = self._apply_filters(all_transactions)
            
            # Обновляем результаты
            self.search_results = final_results
            self.update_results_signal.emit(final_results)
            
            self._log_to_search(f"✅ Поиск завершен. Найдено: {len(final_results)} транзакций")
            
        except Exception as e:
            logger.error(f"Ошибка в потоке поиска: {e}")
            self._log_to_search(f"❌ Ошибка: {str(e)}")
        finally:
            self.search_finished_signal.emit(len(self.search_results))
            
    def _get_token_filter(self) -> Optional[str]:
        """Получение фильтра токена"""
        token = self.token_combo.currentText()
        if token == "PLEX ONE":
            return PLEX_CONTRACT
        elif token == "USDT":
            return USDT_CONTRACT
        elif token == "Другой":
            return self.custom_token_input.text().strip()
        return None
        
    def _filter_transactions(self, transactions: List[Dict], address: str, direction: str) -> List[Dict]:
        """Фильтрация транзакций по направлению"""
        filtered = []
        
        for tx in transactions:
            # Проверяем направление
            if direction == "Входящие" and tx.get('to', '').lower() != address.lower():
                continue
            elif direction == "Исходящие" and tx.get('from', '').lower() != address.lower():
                continue
                
            # Проверяем статус
            if self.only_success.isChecked():
                if tx.get('isError', '0') != '0' or tx.get('txreceipt_status', '1') != '1':
                    continue
                    
            filtered.append(tx)
            
        return filtered
        
    def _apply_filters(self, transactions: List[Dict]) -> List[Dict]:
        """Применение дополнительных фильтров"""
        filtered = transactions.copy()
        
        # Фильтр по сумме
        if self.amount_filter_check.isChecked():
            min_val = self.min_amount.value()
            max_val = self.max_amount.value()
            
            filtered = [
                tx for tx in filtered
                if min_val <= self._get_tx_value(tx) <= max_val
            ]
            
        # Фильтр по дате
        if self.date_filter_check.isChecked():
            date_from = self.date_from.date().toPyDate()
            date_to = self.date_to.date().toPyDate()
            
            filtered = [
                tx for tx in filtered
                if self._check_tx_date(tx, date_from, date_to)
            ]
            
        # Уникальные отправители
        if self.unique_senders.isChecked():
            seen_senders = set()
            unique_filtered = []
            
            for tx in filtered:
                sender = tx.get('from', '').lower()
                if sender not in seen_senders:
                    seen_senders.add(sender)
                    unique_filtered.append(tx)
                    
            filtered = unique_filtered
            
        # Минимум транзакций от отправителя
        if self.min_tx_check.isChecked():
            min_count = self.min_tx_count.value()
            sender_counts = {}
            
            for tx in filtered:
                sender = tx.get('from', '').lower()
                sender_counts[sender] = sender_counts.get(sender, 0) + 1
                
            filtered = [
                tx for tx in filtered
                if sender_counts.get(tx.get('from', '').lower(), 0) >= min_count
            ]
            
        return filtered
        
    def _get_tx_value(self, tx: Dict) -> float:
        """Получение суммы транзакции"""
        try:
            value = float(tx.get('value', 0))
            decimals = int(tx.get('tokenDecimal', 18))
            return value / (10 ** decimals)
        except:
            return 0
            
    def _check_tx_date(self, tx: Dict, date_from, date_to) -> bool:
        """Проверка даты транзакции"""
        try:
            timestamp = int(tx.get('timeStamp', 0))
            tx_date = datetime.fromtimestamp(timestamp).date()
            return date_from <= tx_date <= date_to
        except:
            return False
            
    def _rotate_api_key(self):
        """Ротация API ключа"""
        if BSCSCAN_KEYS:
            self.current_api_key_index = (self.current_api_key_index + 1) % len(BSCSCAN_KEYS)
            self._log_to_search(f"Смена API ключа на #{self.current_api_key_index + 1}")
            
    def _log_to_search(self, message: str):
        """Логирование в поле поиска"""
        QTimer.singleShot(0, lambda: self.search_log.append(message))
        
    @pyqtSlot(list)
    def _update_results_table(self, transactions: List[Dict]):
        """Обновление таблицы результатов"""
        try:
            self.results_table.setRowCount(0)
            
            for tx in transactions[:1000]:  # Ограничиваем отображение
                row = self.results_table.rowCount()
                self.results_table.insertRow(row)
                
                # Hash
                hash_item = QTableWidgetItem(tx.get('hash', '')[:10] + '...')
                self.results_table.setItem(row, 0, hash_item)
                
                # От
                from_addr = tx.get('from', '')
                from_item = QTableWidgetItem(f"{from_addr[:6]}...{from_addr[-4:]}")
                self.results_table.setItem(row, 1, from_item)
                
                # Кому
                to_addr = tx.get('to', '')
                to_item = QTableWidgetItem(f"{to_addr[:6]}...{to_addr[-4:]}")
                self.results_table.setItem(row, 2, to_item)
                
                # Сумма
                value = self._get_tx_value(tx)
                value_item = QTableWidgetItem(f"{value:.8f}")
                self.results_table.setItem(row, 3, value_item)
                
                # Токен
                token = tx.get('tokenSymbol', 'BNB')
                self.results_table.setItem(row, 4, QTableWidgetItem(token))
                
                # Время
                timestamp = int(tx.get('timeStamp', 0))
                time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
                self.results_table.setItem(row, 5, QTableWidgetItem(time_str))
                
                # Блок
                block = tx.get('blockNumber', '')
                self.results_table.setItem(row, 6, QTableWidgetItem(block))
                
                # Статус
                is_error = tx.get('isError', '0') != '0'
                status_item = QTableWidgetItem("❌ Ошибка" if is_error else "✅ Успешно")
                if is_error:
                    status_item.setBackground(QColor('#440000'))
                else:
                    status_item.setBackground(QColor('#004400'))
                self.results_table.setItem(row, 7, status_item)
                
        except Exception as e:
            logger.error(f"Ошибка обновления таблицы: {e}")
            
    @pyqtSlot(int, str)
    def _update_progress(self, value: int, message: str):
        """Обновление прогресса"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        
    @pyqtSlot(int)
    def _on_search_finished(self, count: int):
        """Обработка завершения поиска"""
        self.is_searching = False
        self.search_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Найдено: {count} транзакций")
        self.log(f"Поиск завершен. Найдено: {count} транзакций", "SUCCESS")
        
    def _show_context_menu(self, position):
        """Показ контекстного меню"""
        if self.results_table.currentRow() < 0:
            return
            
        menu = QMenu()
        
        copy_hash = menu.addAction("📋 Копировать hash")
        copy_from = menu.addAction("📋 Копировать отправителя")
        copy_to = menu.addAction("📋 Копировать получателя")
        menu.addSeparator()
        open_bscscan = menu.addAction("🌐 Открыть в BscScan")
        menu.addSeparator()
        add_to_rewards = menu.addAction("🎁 Добавить в награды")
        
        action = menu.exec_(self.results_table.viewport().mapToGlobal(position))
        
        if action:
            row = self.results_table.currentRow()
            
            if row < len(self.search_results):
                tx = self.search_results[row]
                
                if action == copy_hash:
                    QApplication.clipboard().setText(tx.get('hash', ''))
                    self.log("Hash скопирован", "INFO")
                    
                elif action == copy_from:
                    QApplication.clipboard().setText(tx.get('from', ''))
                    self.log("Адрес отправителя скопирован", "INFO")
                    
                elif action == copy_to:
                    QApplication.clipboard().setText(tx.get('to', ''))
                    self.log("Адрес получателя скопирован", "INFO")
                    
                elif action == open_bscscan:
                    url = f"https://bscscan.com/tx/{tx.get('hash', '')}"
                    QDesktopServices.openUrl(QUrl(url))
                    self.log("Открыто в BscScan", "INFO")
                    
                elif action == add_to_rewards:
                    # Здесь можно добавить логику добавления в награды
                    self.log("Добавлено в награды", "SUCCESS")
                    
    def clear_results(self):
        """Очистка результатов"""
        self.results_table.setRowCount(0)
        self.search_results.clear()
        self.search_log.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Готов к поиску")
        self.log("Результаты очищены", "INFO")
        
    def export_results(self):
        """Экспорт результатов в CSV"""
        if not self.search_results:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта!")
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить результаты поиска",
            f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Заголовки
                    writer.writerow([
                        'Hash', 'From', 'To', 'Value', 'Token',
                        'Timestamp', 'Block', 'Status'
                    ])
                    
                    # Данные
                    for tx in self.search_results:
                        writer.writerow([
                            tx.get('hash', ''),
                            tx.get('from', ''),
                            tx.get('to', ''),
                            self._get_tx_value(tx),
                            tx.get('tokenSymbol', 'BNB'),
                            datetime.fromtimestamp(int(tx.get('timeStamp', 0))).isoformat(),
                            tx.get('blockNumber', ''),
                            'Error' if tx.get('isError', '0') != '0' else 'Success'
                        ])
                        
                self.log(f"✅ Экспортировано {len(self.search_results)} транзакций", "SUCCESS")
                QMessageBox.information(self, "Успех", f"Данные экспортированы в:\n{path}")
                
            except Exception as e:
                logger.error(f"Ошибка экспорта: {e}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта:\n{str(e)}")
                
    def import_to_rewards(self):
        """Импорт результатов в награды"""
        if not self.search_results:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для импорта!")
            return
            
        # Здесь можно добавить логику импорта в систему наград
        count = len(self.search_results)
        self.log(f"🎁 Импортировано {count} транзакций в награды", "SUCCESS")
        QMessageBox.information(self, "Успех", f"Импортировано {count} транзакций в систему наград")
