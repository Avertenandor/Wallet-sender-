"""
Вкладка истории операций
Полная реализация с отображением транзакций из БД
"""

from datetime import datetime
from typing import Optional, List
import asyncio
import pandas as pd

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QDateEdit, QMessageBox, QHeaderView, QMenu, QFileDialog,
    QApplication
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QThread
from PyQt5.QtGui import QColor

from .base_tab import BaseTab
from ...database.models import Transaction
from ...database.database import Database
from ...utils.logger import get_logger

logger = get_logger(__name__)


class TransactionStatusChecker(QThread):
    """Поток для проверки статусов транзакций"""
    status_updated = pyqtSignal(str, str)  # tx_hash, new_status
    
    def __init__(self, web3_provider, tx_hashes):
        super().__init__()
        self.web3_provider = web3_provider
        self.tx_hashes = tx_hashes
        self.is_running = True
        
    def run(self):
        """Проверка статусов"""
        for tx_hash in self.tx_hashes:
            if not self.is_running:
                break
                
            try:
                receipt = self.web3_provider.w3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    status = "success" if receipt.status == 1 else "failed"
                    self.status_updated.emit(tx_hash, status)
            except Exception as e:
                logger.error(f"Ошибка проверки статуса {tx_hash}: {e}")
                
        logger.info(f"Проверка {len(self.tx_hashes)} транзакций завершена")
        
    def stop(self):
        """Остановка потока"""
        self.is_running = False


class HistoryTab(BaseTab):
    """Вкладка истории операций"""
    
    def __init__(self, main_window, parent=None):
        # Важно: создать менеджер БД до вызова BaseTab.__init__,
        # т.к. BaseTab вызывает init_ui(), где используется db_manager (load_history)
        self.db_manager = Database()
        self.status_checker = None
        super().__init__(main_window, parent)
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QGroupBox("📜 История транзакций")
        header.setStyleSheet("QGroupBox { font-weight: bold; }")
        header_layout = QVBoxLayout(header)
        
        # Панель фильтров
        filters_group = QGroupBox("Фильтры")
        filters_layout = QHBoxLayout(filters_group)
        
        # Фильтр по типу
        filters_layout.addWidget(QLabel("Тип:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems([
            "Все", "transfer", "reward", "distribution", "buy", "sell"
        ])
        self.type_filter.currentTextChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.type_filter)
        
        # Фильтр по статусу
        filters_layout.addWidget(QLabel("Статус:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems([
            "Все", "pending", "success", "failed"
        ])
        self.status_filter.currentTextChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.status_filter)
        
        # Фильтр по адресу
        filters_layout.addWidget(QLabel("Адрес:"))
        self.address_filter = QLineEdit()
        self.address_filter.setPlaceholderText("0x...")
        self.address_filter.textChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.address_filter)
        
        # Фильтр по дате
        filters_layout.addWidget(QLabel("С:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.dateChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.date_from)
        
        filters_layout.addWidget(QLabel("По:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.date_to)
        
        filters_layout.addStretch()
        
        # Кнопки действий
        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.clicked.connect(self.load_history)
        filters_layout.addWidget(self.refresh_btn)
        
        self.check_status_btn = QPushButton("✅ Проверить статусы")
        self.check_status_btn.clicked.connect(self.check_pending_statuses)
        filters_layout.addWidget(self.check_status_btn)
        
        self.export_btn = QPushButton("📥 Экспорт")
        self.export_btn.clicked.connect(self.export_history)
        filters_layout.addWidget(self.export_btn)
        
        header_layout.addWidget(filters_group)
        layout.addWidget(header)
        
        # Таблица транзакций
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(10)
        self.history_table.setHorizontalHeaderLabels([
            "Дата", "Тип", "От", "Кому", "Токен", "Сумма", 
            "Gas", "Статус", "TX Hash", "Блок"
        ])
        
        # Настройка таблицы
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSortingEnabled(True)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.history_table)
        
        # Статистика
        stats_group = QGroupBox("Статистика")
        stats_layout = QHBoxLayout(stats_group)
        
        self.stats_label = QLabel("Всего: 0 | Успешных: 0 | Неудачных: 0 | В ожидании: 0")
        stats_layout.addWidget(self.stats_label)
        
        layout.addWidget(stats_group)
        
        # Загрузка данных при инициализации
        self.load_history()
        
        logger.info("HistoryTab полностью инициализирована")
        
    def load_history(self):
        """Загрузка истории из БД"""
        try:
            session = self.db_manager.get_session()
            
            # Получаем все транзакции
            transactions = session.query(Transaction).order_by(
                Transaction.created_at.desc()
            ).all()
            
            # Очищаем таблицу
            self.history_table.setRowCount(0)
            
            # Заполняем таблицу
            for tx in transactions:
                self.add_transaction_to_table(tx)
                
            # Обновляем статистику
            self.update_statistics(transactions)
            
            session.close()
            
            self.log_message(f"Загружено {len(transactions)} транзакций", "INFO")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки истории: {e}")
            self.log_message(f"Ошибка загрузки истории: {e}", "ERROR")
            
    def add_transaction_to_table(self, tx: Transaction):
        """Добавление транзакции в таблицу"""
        row_position = self.history_table.rowCount()
        self.history_table.insertRow(row_position)
        
        # Дата
        date_str = tx.created_at.strftime("%Y-%m-%d %H:%M:%S") if tx.created_at else ""
        self.history_table.setItem(row_position, 0, QTableWidgetItem(date_str))
        
        # Тип
        self.history_table.setItem(row_position, 1, QTableWidgetItem(tx.type or "transfer"))
        
        # От
        from_addr = tx.from_address[:6] + "..." + tx.from_address[-4:] if tx.from_address else ""
        self.history_table.setItem(row_position, 2, QTableWidgetItem(from_addr))
        
        # Кому
        to_addr = tx.to_address[:6] + "..." + tx.to_address[-4:] if tx.to_address else ""
        self.history_table.setItem(row_position, 3, QTableWidgetItem(to_addr))
        
        # Токен
        self.history_table.setItem(row_position, 4, QTableWidgetItem(tx.token_symbol or "BNB"))
        
        # Сумма
        amount_str = f"{tx.amount:.4f}" if tx.amount else "0"
        self.history_table.setItem(row_position, 5, QTableWidgetItem(amount_str))
        
        # Gas
        gas_str = f"{tx.gas_price:.2f}" if tx.gas_price else "0"
        self.history_table.setItem(row_position, 6, QTableWidgetItem(gas_str))
        
        # Статус
        status_item = QTableWidgetItem(tx.status or "pending")
        # Цветовая индикация статуса
        if tx.status == "success":
            status_item.setBackground(QColor(76, 175, 80))  # Зеленый
        elif tx.status == "failed":
            status_item.setBackground(QColor(244, 67, 54))  # Красный
        else:
            status_item.setBackground(QColor(255, 152, 0))  # Оранжевый
        self.history_table.setItem(row_position, 7, status_item)
        
        # TX Hash
        tx_hash = tx.tx_hash[:8] + "..." if tx.tx_hash else ""
        hash_item = QTableWidgetItem(tx_hash)
        hash_item.setData(Qt.UserRole, tx.tx_hash)  # Сохраняем полный hash
        self.history_table.setItem(row_position, 8, hash_item)
        
        # Блок
        block_str = str(tx.block_number) if tx.block_number else "-"
        self.history_table.setItem(row_position, 9, QTableWidgetItem(block_str))
        
    def apply_filters(self):
        """Применение фильтров"""
        try:
            session = self.db_manager.get_session()
            query = session.query(Transaction)
            
            # Фильтр по типу
            if self.type_filter.currentText() != "Все":
                query = query.filter(Transaction.type == self.type_filter.currentText())
                
            # Фильтр по статусу
            if self.status_filter.currentText() != "Все":
                query = query.filter(Transaction.status == self.status_filter.currentText())
                
            # Фильтр по адресу
            address = self.address_filter.text().strip()
            if address:
                query = query.filter(
                    (Transaction.from_address.contains(address)) |
                    (Transaction.to_address.contains(address))
                )
                
            # Фильтр по дате
            date_from = self.date_from.date().toPyDate()
            date_to = self.date_to.date().toPyDate()
            query = query.filter(
                Transaction.created_at >= datetime.combine(date_from, datetime.min.time()),
                Transaction.created_at <= datetime.combine(date_to, datetime.max.time())
            )
            
            # Получаем результаты
            transactions = query.order_by(Transaction.created_at.desc()).all()
            
            # Обновляем таблицу
            self.history_table.setRowCount(0)
            for tx in transactions:
                self.add_transaction_to_table(tx)
                
            # Обновляем статистику
            self.update_statistics(transactions)
            
            session.close()
            
            self.log_message(f"Фильтры применены. Найдено: {len(transactions)}", "INFO")
            
        except Exception as e:
            logger.error(f"Ошибка применения фильтров: {e}")
            self.log_message(f"Ошибка фильтрации: {e}", "ERROR")
            
    def update_statistics(self, transactions: List[Transaction]):
        """Обновление статистики"""
        total = len(transactions)
        success = len([t for t in transactions if t.status == "success"])
        failed = len([t for t in transactions if t.status == "failed"])
        pending = len([t for t in transactions if t.status == "pending"])
        
        self.stats_label.setText(
            f"Всего: {total} | Успешных: {success} | Неудачных: {failed} | В ожидании: {pending}"
        )
        
    def check_pending_statuses(self):
        """Проверка статусов pending транзакций"""
        try:
            session = self.db_manager.get_session()
            
            # Получаем pending транзакции
            pending_txs = session.query(Transaction).filter(
                Transaction.status == "pending"
            ).all()
            
            if not pending_txs:
                self.log_message("Нет транзакций в ожидании", "INFO")
                return
                
            # Собираем хеши
            tx_hashes = [tx.tx_hash for tx in pending_txs if tx.tx_hash]
            
            if not tx_hashes:
                self.log_message("Нет хешей для проверки", "WARNING")
                return
                
            # Запускаем проверку в отдельном потоке
            self.status_checker = TransactionStatusChecker(
                self.main_window.web3_provider, tx_hashes
            )
            self.status_checker.status_updated.connect(self.update_transaction_status)
            self.status_checker.start()
            
            self.log_message(f"Запущена проверка {len(tx_hashes)} транзакций", "INFO")
            self.check_status_btn.setEnabled(False)
            self.check_status_btn.setText("⏳ Проверка...")
            
            # Восстановим кнопку после завершения
            self.status_checker.finished.connect(
                lambda: self.check_status_btn.setEnabled(True)
            )
            self.status_checker.finished.connect(
                lambda: self.check_status_btn.setText("✅ Проверить статусы")
            )
            
            session.close()
            
        except Exception as e:
            logger.error(f"Ошибка проверки статусов: {e}")
            self.log_message(f"Ошибка проверки: {e}", "ERROR")
            
    def update_transaction_status(self, tx_hash: str, new_status: str):
        """Обновление статуса транзакции"""
        try:
            session = self.db_manager.get_session()
            
            # Обновляем в БД
            tx = session.query(Transaction).filter(
                Transaction.tx_hash == tx_hash
            ).first()
            
            if tx:
                tx.status = new_status
                tx.confirmed_at = datetime.utcnow()
                session.commit()
                
                # Обновляем в таблице
                for row in range(self.history_table.rowCount()):
                    hash_item = self.history_table.item(row, 8)
                    if hash_item and hash_item.data(Qt.UserRole) == tx_hash:
                        status_item = self.history_table.item(row, 7)
                        status_item.setText(new_status)
                        
                        if new_status == "success":
                            status_item.setBackground(QColor(76, 175, 80))
                        elif new_status == "failed":
                            status_item.setBackground(QColor(244, 67, 54))
                        break
                        
                self.log_message(f"Статус {tx_hash[:8]}... обновлен: {new_status}", "INFO")
                
            session.close()
            
        except Exception as e:
            logger.error(f"Ошибка обновления статуса: {e}")
            
    def show_context_menu(self, position):
        """Контекстное меню таблицы"""
        menu = QMenu()
        
        # Действия
        copy_hash_action = menu.addAction("📋 Копировать TX Hash")
        copy_address_action = menu.addAction("📋 Копировать адрес")
        menu.addSeparator()
        view_on_bscscan_action = menu.addAction("🔗 Открыть в BscScan")
        
        # Показываем меню
        action = menu.exec_(self.history_table.mapToGlobal(position))
        
        if action:
            current_row = self.history_table.currentRow()
            if current_row >= 0:
                if action == copy_hash_action:
                    hash_item = self.history_table.item(current_row, 8)
                    if hash_item:
                        tx_hash = hash_item.data(Qt.UserRole)
                        if tx_hash:
                            QApplication.clipboard().setText(tx_hash)
                            self.log_message("TX Hash скопирован", "INFO")
                            
                elif action == copy_address_action:
                    # Копируем адрес получателя
                    to_address = self.history_table.item(current_row, 3).text()
                    if to_address:
                        # Нужно получить полный адрес из БД
                        hash_item = self.history_table.item(current_row, 8)
                        if hash_item:
                            tx_hash = hash_item.data(Qt.UserRole)
                            session = self.db_manager.get_session()
                            tx = session.query(Transaction).filter(
                                Transaction.tx_hash == tx_hash
                            ).first()
                            if tx and tx.to_address:
                                QApplication.clipboard().setText(tx.to_address)
                                self.log_message("Адрес скопирован", "INFO")
                            session.close()
                            
                elif action == view_on_bscscan_action:
                    hash_item = self.history_table.item(current_row, 8)
                    if hash_item:
                        tx_hash = hash_item.data(Qt.UserRole)
                        if tx_hash:
                            import webbrowser
                            webbrowser.open(f"https://bscscan.com/tx/{tx_hash}")
                            
    def export_history(self):
        """Экспорт истории в файл"""
        try:
            # Выбор файла
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт истории", "", 
                "CSV файлы (*.csv);;Excel файлы (*.xlsx)"
            )
            
            if not file_path:
                return
                
            # Собираем данные из таблицы
            data = []
            for row in range(self.history_table.rowCount()):
                row_data = []
                for col in range(self.history_table.columnCount()):
                    item = self.history_table.item(row, col)
                    if col == 8:  # TX Hash - берем полное значение
                        row_data.append(item.data(Qt.UserRole) if item else "")
                    else:
                        row_data.append(item.text() if item else "")
                data.append(row_data)
                
            # Создаем DataFrame
            df = pd.DataFrame(data, columns=[
                "Дата", "Тип", "От", "Кому", "Токен", "Сумма", 
                "Gas", "Статус", "TX Hash", "Блок"
            ])
            
            # Сохраняем
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
                
            self.log_message(f"История экспортирована: {file_path}", "SUCCESS")
            
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            self.log_message(f"Ошибка экспорта: {e}", "ERROR")
            
    def cleanup(self):
        """Очистка ресурсов при закрытии вкладки"""
        if self.status_checker and self.status_checker.isRunning():
            self.status_checker.stop()
            self.status_checker.wait()
