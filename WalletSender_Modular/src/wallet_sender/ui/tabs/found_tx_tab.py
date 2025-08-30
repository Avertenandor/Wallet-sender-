"""
Вкладка найденных транзакций
Отображает транзакции, найденные через поиск
"""

from datetime import datetime
from typing import List, Optional
import pandas as pd

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QMessageBox, QHeaderView, QMenu, QFileDialog, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from .base_tab import BaseTab
from ...database.database import DatabaseManager
from ...utils.logger import get_logger

logger = get_logger(__name__)


class FoundTxTab(BaseTab):
    """Вкладка найденных транзакций"""
    
    # Сигналы
    import_to_rewards_signal = pyqtSignal(list)  # Список транзакций для импорта в награды
    
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        self.db_manager = DatabaseManager()
        self.found_transactions = []
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QGroupBox("🔍 Найденные транзакции")
        header.setStyleSheet("QGroupBox { font-weight: bold; }")
        header_layout = QVBoxLayout(header)
        
        # Панель управления
        control_panel = QHBoxLayout()
        
        # Фильтры
        control_panel.addWidget(QLabel("Токен:"))
        self.token_filter = QComboBox()
        self.token_filter.addItems(["Все", "PLEX", "USDT", "BNB", "Другие"])
        self.token_filter.currentTextChanged.connect(self.apply_filters)
        control_panel.addWidget(self.token_filter)
        
        control_panel.addWidget(QLabel("Мин. сумма:"))
        self.min_amount_filter = QLineEdit()
        self.min_amount_filter.setPlaceholderText("0.0")
        self.min_amount_filter.setMaximumWidth(100)
        self.min_amount_filter.textChanged.connect(self.apply_filters)
        control_panel.addWidget(self.min_amount_filter)
        
        control_panel.addWidget(QLabel("Адрес:"))
        self.address_filter = QLineEdit()
        self.address_filter.setPlaceholderText("Фильтр по адресу...")
        self.address_filter.textChanged.connect(self.apply_filters)
        control_panel.addWidget(self.address_filter)
        
        control_panel.addStretch()
        
        # Кнопки действий
        self.clear_btn = QPushButton("🗑 Очистить")
        self.clear_btn.clicked.connect(self.clear_found_transactions)
        control_panel.addWidget(self.clear_btn)
        
        self.import_rewards_btn = QPushButton("🎁 Импорт в награды")
        self.import_rewards_btn.clicked.connect(self.import_to_rewards)
        control_panel.addWidget(self.import_rewards_btn)
        
        self.export_btn = QPushButton("📥 Экспорт")
        self.export_btn.clicked.connect(self.export_transactions)
        control_panel.addWidget(self.export_btn)
        
        header_layout.addLayout(control_panel)
        layout.addWidget(header)
        
        # Таблица транзакций
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(10)
        self.transactions_table.setHorizontalHeaderLabels([
            "Выбор", "Дата/Время", "От кого", "Кому", "Токен",
            "Сумма", "TX Hash", "Блок", "Статус", "Источник"
        ])
        
        # Настройка таблицы
        self.transactions_table.setAlternatingRowColors(True)
        self.transactions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transactions_table.setSortingEnabled(True)
        self.transactions_table.horizontalHeader().setStretchLastSection(True)
        self.transactions_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.transactions_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Устанавливаем ширину колонок
        header = self.transactions_table.horizontalHeader()
        header.resizeSection(0, 50)  # Чекбокс
        header.resizeSection(1, 150)  # Дата
        header.resizeSection(2, 120)  # От
        header.resizeSection(3, 120)  # Кому
        header.resizeSection(4, 80)   # Токен
        header.resizeSection(5, 100)  # Сумма
        header.resizeSection(6, 120)  # TX Hash
        header.resizeSection(7, 80)   # Блок
        header.resizeSection(8, 80)   # Статус
        
        layout.addWidget(self.transactions_table)
        
        # Статистика
        stats_group = QGroupBox("Статистика")
        stats_layout = QHBoxLayout(stats_group)
        
        self.total_label = QLabel("Всего: 0")
        stats_layout.addWidget(self.total_label)
        
        self.selected_label = QLabel("Выбрано: 0")
        stats_layout.addWidget(self.selected_label)
        
        self.total_amount_label = QLabel("Общая сумма: 0")
        stats_layout.addWidget(self.total_amount_label)
        
        self.unique_senders_label = QLabel("Уникальных отправителей: 0")
        stats_layout.addWidget(self.unique_senders_label)
        
        stats_layout.addStretch()
        
        layout.addWidget(stats_group)
        
        logger.info("FoundTxTab инициализирована")
        
    def add_found_transaction(self, tx_data: dict):
        """Добавление найденной транзакции"""
        try:
            # Добавляем в список
            self.found_transactions.append(tx_data)
            
            # Добавляем в таблицу
            row = self.transactions_table.rowCount()
            self.transactions_table.insertRow(row)
            
            # Чекбокс для выбора
            from PyQt5.QtWidgets import QCheckBox
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.update_selection_stats)
            self.transactions_table.setCellWidget(row, 0, checkbox)
            
            # Дата/Время
            timestamp = tx_data.get('timestamp', 0)
            if timestamp:
                date_str = datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = "-"
            self.transactions_table.setItem(row, 1, QTableWidgetItem(date_str))
            
            # От кого
            from_addr = tx_data.get('from', '')
            from_short = from_addr[:6] + "..." + from_addr[-4:] if from_addr else "-"
            from_item = QTableWidgetItem(from_short)
            from_item.setData(Qt.UserRole, from_addr)  # Полный адрес
            self.transactions_table.setItem(row, 2, from_item)
            
            # Кому
            to_addr = tx_data.get('to', '')
            to_short = to_addr[:6] + "..." + to_addr[-4:] if to_addr else "-"
            to_item = QTableWidgetItem(to_short)
            to_item.setData(Qt.UserRole, to_addr)  # Полный адрес
            self.transactions_table.setItem(row, 3, to_item)
            
            # Токен
            token = tx_data.get('tokenSymbol', 'Unknown')
            self.transactions_table.setItem(row, 4, QTableWidgetItem(token))
            
            # Сумма
            amount = tx_data.get('value', 0)
            decimals = tx_data.get('tokenDecimal', 18)
            if decimals:
                amount_formatted = float(amount) / (10 ** int(decimals))
                amount_str = f"{amount_formatted:.4f}"
            else:
                amount_str = str(amount)
            self.transactions_table.setItem(row, 5, QTableWidgetItem(amount_str))
            
            # TX Hash
            tx_hash = tx_data.get('hash', '')
            hash_short = tx_hash[:8] + "..." if tx_hash else "-"
            hash_item = QTableWidgetItem(hash_short)
            hash_item.setData(Qt.UserRole, tx_hash)  # Полный хеш
            self.transactions_table.setItem(row, 6, hash_item)
            
            # Блок
            block = tx_data.get('blockNumber', '-')
            self.transactions_table.setItem(row, 7, QTableWidgetItem(str(block)))
            
            # Статус (для найденных транзакций обычно success)
            status = "success"
            status_item = QTableWidgetItem(status)
            status_item.setBackground(QColor(76, 175, 80))
            self.transactions_table.setItem(row, 8, status_item)
            
            # Источник
            source = tx_data.get('source', 'Search')
            self.transactions_table.setItem(row, 9, QTableWidgetItem(source))
            
            # Обновляем статистику
            self.update_statistics()
            
        except Exception as e:
            logger.error(f"Ошибка добавления транзакции: {e}")
            
    def add_multiple_transactions(self, transactions: List[dict]):
        """Добавление нескольких транзакций"""
        for tx in transactions:
            self.add_found_transaction(tx)
            
        self.log_message(f"Добавлено {len(transactions)} транзакций", "INFO")
        
    def apply_filters(self):
        """Применение фильтров к таблице"""
        try:
            token_filter = self.token_filter.currentText()
            min_amount = self.min_amount_filter.text()
            address_filter = self.address_filter.text().lower()
            
            for row in range(self.transactions_table.rowCount()):
                show_row = True
                
                # Фильтр по токену
                if token_filter != "Все":
                    token_item = self.transactions_table.item(row, 4)
                    if token_item and token_filter not in token_item.text():
                        show_row = False
                        
                # Фильтр по минимальной сумме
                if min_amount and show_row:
                    try:
                        amount_item = self.transactions_table.item(row, 5)
                        if amount_item:
                            amount = float(amount_item.text())
                            if amount < float(min_amount):
                                show_row = False
                    except ValueError:
                        pass
                        
                # Фильтр по адресу
                if address_filter and show_row:
                    from_item = self.transactions_table.item(row, 2)
                    to_item = self.transactions_table.item(row, 3)
                    
                    from_addr = from_item.data(Qt.UserRole) if from_item else ""
                    to_addr = to_item.data(Qt.UserRole) if to_item else ""
                    
                    if address_filter not in from_addr.lower() and address_filter not in to_addr.lower():
                        show_row = False
                        
                self.transactions_table.setRowHidden(row, not show_row)
                
        except Exception as e:
            logger.error(f"Ошибка применения фильтров: {e}")
            
    def update_statistics(self):
        """Обновление статистики"""
        total = self.transactions_table.rowCount()
        visible_count = 0
        total_amount = 0
        unique_senders = set()
        
        for row in range(total):
            if not self.transactions_table.isRowHidden(row):
                visible_count += 1
                
                # Сумма
                amount_item = self.transactions_table.item(row, 5)
                if amount_item:
                    try:
                        total_amount += float(amount_item.text())
                    except ValueError:
                        pass
                        
                # Уникальные отправители
                from_item = self.transactions_table.item(row, 2)
                if from_item:
                    from_addr = from_item.data(Qt.UserRole)
                    if from_addr:
                        unique_senders.add(from_addr)
                        
        self.total_label.setText(f"Всего: {visible_count}/{total}")
        self.total_amount_label.setText(f"Общая сумма: {total_amount:.4f}")
        self.unique_senders_label.setText(f"Уникальных отправителей: {len(unique_senders)}")
        
        self.update_selection_stats()
        
    def update_selection_stats(self):
        """Обновление статистики выбранных"""
        selected_count = 0
        
        for row in range(self.transactions_table.rowCount()):
            checkbox = self.transactions_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1
                
        self.selected_label.setText(f"Выбрано: {selected_count}")
        
    def import_to_rewards(self):
        """Импорт выбранных транзакций в награды"""
        selected_transactions = []
        
        for row in range(self.transactions_table.rowCount()):
            checkbox = self.transactions_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # Собираем данные транзакции
                tx_data = {
                    'from_address': self.transactions_table.item(row, 2).data(Qt.UserRole),
                    'to_address': self.transactions_table.item(row, 3).data(Qt.UserRole),
                    'token': self.transactions_table.item(row, 4).text(),
                    'amount': self.transactions_table.item(row, 5).text(),
                    'tx_hash': self.transactions_table.item(row, 6).data(Qt.UserRole),
                    'block': self.transactions_table.item(row, 7).text(),
                }
                selected_transactions.append(tx_data)
                
        if not selected_transactions:
            QMessageBox.warning(self, "Предупреждение", "Не выбрано ни одной транзакции!")
            return
            
        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Импортировать {len(selected_transactions)} транзакций в награды?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.import_to_rewards_signal.emit(selected_transactions)
            self.log_message(f"Импортировано {len(selected_transactions)} транзакций в награды", "SUCCESS")
            
            # Снимаем выделение
            for row in range(self.transactions_table.rowCount()):
                checkbox = self.transactions_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(False)
                    
    def export_transactions(self):
        """Экспорт транзакций в файл"""
        try:
            if self.transactions_table.rowCount() == 0:
                QMessageBox.warning(self, "Предупреждение", "Нет транзакций для экспорта!")
                return
                
            # Выбор файла
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт транзакций", "",
                "CSV файлы (*.csv);;Excel файлы (*.xlsx)"
            )
            
            if not file_path:
                return
                
            # Собираем данные
            data = []
            for row in range(self.transactions_table.rowCount()):
                if not self.transactions_table.isRowHidden(row):
                    row_data = {
                        'Дата': self.transactions_table.item(row, 1).text(),
                        'От': self.transactions_table.item(row, 2).data(Qt.UserRole),
                        'Кому': self.transactions_table.item(row, 3).data(Qt.UserRole),
                        'Токен': self.transactions_table.item(row, 4).text(),
                        'Сумма': self.transactions_table.item(row, 5).text(),
                        'TX Hash': self.transactions_table.item(row, 6).data(Qt.UserRole),
                        'Блок': self.transactions_table.item(row, 7).text(),
                        'Статус': self.transactions_table.item(row, 8).text(),
                        'Источник': self.transactions_table.item(row, 9).text(),
                    }
                    data.append(row_data)
                    
            # Создаем DataFrame
            df = pd.DataFrame(data)
            
            # Сохраняем
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
                
            self.log_message(f"Экспортировано {len(data)} транзакций", "SUCCESS")
            QMessageBox.information(self, "Успех", f"Транзакции экспортированы:\n{file_path}")
            
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта:\n{str(e)}")
            
    def clear_found_transactions(self):
        """Очистка найденных транзакций"""
        if self.transactions_table.rowCount() == 0:
            return
            
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Очистить все найденные транзакции ({self.transactions_table.rowCount()})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.transactions_table.setRowCount(0)
            self.found_transactions.clear()
            self.update_statistics()
            self.log_message("Найденные транзакции очищены", "INFO")
            
    def show_context_menu(self, position):
        """Контекстное меню таблицы"""
        menu = QMenu()
        
        # Действия
        copy_hash_action = menu.addAction("📋 Копировать TX Hash")
        copy_from_action = menu.addAction("📋 Копировать адрес отправителя")
        copy_to_action = menu.addAction("📋 Копировать адрес получателя")
        menu.addSeparator()
        view_on_bscscan_action = menu.addAction("🔗 Открыть в BscScan")
        menu.addSeparator()
        select_all_action = menu.addAction("✅ Выбрать все")
        deselect_all_action = menu.addAction("❌ Снять выделение")
        
        # Показываем меню
        action = menu.exec_(self.transactions_table.mapToGlobal(position))
        
        if action:
            current_row = self.transactions_table.currentRow()
            
            if action == copy_hash_action and current_row >= 0:
                hash_item = self.transactions_table.item(current_row, 6)
                if hash_item:
                    tx_hash = hash_item.data(Qt.UserRole)
                    if tx_hash:
                        QApplication.clipboard().setText(tx_hash)
                        self.log_message("TX Hash скопирован", "INFO")
                        
            elif action == copy_from_action and current_row >= 0:
                from_item = self.transactions_table.item(current_row, 2)
                if from_item:
                    from_addr = from_item.data(Qt.UserRole)
                    if from_addr:
                        QApplication.clipboard().setText(from_addr)
                        self.log_message("Адрес отправителя скопирован", "INFO")
                        
            elif action == copy_to_action and current_row >= 0:
                to_item = self.transactions_table.item(current_row, 3)
                if to_item:
                    to_addr = to_item.data(Qt.UserRole)
                    if to_addr:
                        QApplication.clipboard().setText(to_addr)
                        self.log_message("Адрес получателя скопирован", "INFO")
                        
            elif action == view_on_bscscan_action and current_row >= 0:
                hash_item = self.transactions_table.item(current_row, 6)
                if hash_item:
                    tx_hash = hash_item.data(Qt.UserRole)
                    if tx_hash:
                        import webbrowser
                        webbrowser.open(f"https://bscscan.com/tx/{tx_hash}")
                        
            elif action == select_all_action:
                for row in range(self.transactions_table.rowCount()):
                    if not self.transactions_table.isRowHidden(row):
                        checkbox = self.transactions_table.cellWidget(row, 0)
                        if checkbox:
                            checkbox.setChecked(True)
                            
            elif action == deselect_all_action:
                for row in range(self.transactions_table.rowCount()):
                    checkbox = self.transactions_table.cellWidget(row, 0)
                    if checkbox:
                        checkbox.setChecked(False)
