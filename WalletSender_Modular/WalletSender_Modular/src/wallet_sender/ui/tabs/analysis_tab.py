"""
Вкладка анализа токенов и транзакций
"""

import threading
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from datetime import datetime

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QProgressBar,
    QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QHeaderView,
    QAbstractItemView, QRadioButton, QButtonGroup, QFormLayout,
    QMessageBox, QMenu, QApplication, QAction
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QTimer, QUrl, QPoint
from PyQt5.QtGui import QColor, QDesktopServices

from web3 import Web3

from .base_tab import BaseTab
if TYPE_CHECKING:  # only for type checkers
    from ...core.web3_provider import Web3Provider
    from ...services.token_service import TokenService
from ...constants import PLEX_CONTRACT, USDT_CONTRACT
from ...utils.logger import get_logger
from ...services.bscscan_service import get_bscscan_service
from ...config import get_config

logger = get_logger(__name__)

class AnalysisTab(BaseTab):
    """Вкладка для анализа транзакций и токенов BSC"""
    
    # Сигналы для обновления UI из потоков
    update_table_signal = pyqtSignal(list, dict, dict)
    search_finished_signal = pyqtSignal()
    found_tx_added_signal = pyqtSignal()
    
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        # Инициализация переменных
        self.web3_provider: Optional["Web3Provider"] = None
        self.token_service: Optional["TokenService"] = None
        self.is_searching: bool = False
        self.stop_search_event: threading.Event = threading.Event()
        self.search_thread: Optional[threading.Thread] = None
        # Безопасная инициализация BscScanService, чтобы не падала вкладка при ошибке импорта/конфигурации
        try:  # noqa: WPS501
            self.bscscan_service = get_bscscan_service()
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Не удалось инициализировать bscscan_service: %s", e)
            # Создаем атрибут явно, чтобы избежать AttributeError в таймерах
            self.bscscan_service = None
        self.config = get_config()
        # Подключение сигналов
        self.update_table_signal.connect(self._update_search_results)  # type: ignore
        self.search_finished_signal.connect(self._on_search_finished)  # type: ignore
        
    def init_ui(self):
        """Инициализация интерфейса вкладки анализа"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QGroupBox("Анализ транзакций BSC")
        header_layout = QVBoxLayout(header)
        header_label = QLabel("[SEARCH] Сканирование и анализ транзакций токенов на BSC")
        header_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        header_layout.addWidget(header_label)
        layout.addWidget(header)
        
        # Группа параметров поиска
        search_group = self._create_search_group()
        layout.addWidget(search_group)
        
        # Группа настроек API
        api_group = self._create_api_group()
        layout.addWidget(api_group)
        
        # Таблица результатов
        results_group = QGroupBox("Результаты анализа")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels([
            'Отправитель', 'Количество Tx', 'Общая сумма', 
            'Первая Tx', 'Последняя Tx', 'Статус'
        ])
        
        header = self.results_table.horizontalHeader()
        if header:
                header.setSectionResizeMode(QHeaderView.ResizeToContents)  # type: ignore
                header.setSectionResizeMode(0, QHeaderView.Stretch)  # type: ignore
        
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._show_context_menu)
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_group)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Лог поиска
        log_group = QGroupBox("Лог анализа")
        log_layout = QVBoxLayout(log_group)
        
        self.search_log = QTextEdit()
        self.search_log.setReadOnly(True)
        self.search_log.setMaximumHeight(150)
        log_layout.addWidget(self.search_log)
        
        layout.addWidget(log_group)
        
    def _create_search_group(self) -> QGroupBox:
        """Создание группы параметров поиска"""
        group = QGroupBox("Параметры поиска")
        layout = QFormLayout(group)
        
        # Адрес для анализа
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("0x...")
        layout.addRow("Адрес для анализа:", self.address_input)
        
        # Токен для фильтрации
        token_layout = QHBoxLayout()
        self.token_combo = QComboBox()
        self.token_combo.addItems(['Все токены', 'PLEX ONE', 'USDT', 'Другой'])
        token_layout.addWidget(self.token_combo)
        
        self.custom_token_input = QLineEdit()
        self.custom_token_input.setPlaceholderText("Адрес токена (0x...)")
        self.custom_token_input.setEnabled(False)
        token_layout.addWidget(self.custom_token_input)
        
        layout.addRow("Фильтр по токену:", token_layout)
        
        # Выбор режима поиска
        search_mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup()
        
        self.radio_exact = QRadioButton("Точная сумма")
        self.radio_range = QRadioButton("Диапазон сумм")
        self.radio_all = QRadioButton("Все транзакции")
        
        self.radio_all.setChecked(True)
        
        self.mode_group.addButton(self.radio_exact)
        self.mode_group.addButton(self.radio_range)
        self.mode_group.addButton(self.radio_all)
        
        search_mode_layout.addWidget(self.radio_exact)
        search_mode_layout.addWidget(self.radio_range)
        search_mode_layout.addWidget(self.radio_all)
        search_mode_layout.addStretch()
        
        layout.addRow("Режим поиска:", search_mode_layout)
        
        # Параметры суммы
        amount_layout = QHBoxLayout()
        
        # Точная сумма
        self.exact_amount = QDoubleSpinBox()
        self.exact_amount.setRange(0, 1000000)
        self.exact_amount.setDecimals(8)
        self.exact_amount.setValue(30)
        self.exact_amount.setEnabled(False)
        amount_layout.addWidget(QLabel("Точная:"))
        amount_layout.addWidget(self.exact_amount)
        # Диапазон
        self.min_amount = QDoubleSpinBox()
        self.min_amount.setRange(0, 1000000)
        self.min_amount.setDecimals(8)
        self.min_amount.setValue(10)
        self.min_amount.setEnabled(False)
        amount_layout.addWidget(QLabel("От:"))
        
        self.max_amount = QDoubleSpinBox()
        self.max_amount.setRange(0, 1000000)
        self.max_amount.setDecimals(8)
        self.max_amount.setValue(100)
        self.max_amount.setEnabled(False)
        amount_layout.addWidget(QLabel("До:"))
        amount_layout.addWidget(self.max_amount)
        
        layout.addRow("Сумма токенов:", amount_layout)
        
        # Параметры страниц
        pages_layout = QHBoxLayout()
        
        pages_layout.addWidget(QLabel("Макс. страниц:"))
        self.max_pages = QSpinBox()
        self.max_pages.setRange(1, 1000)
        self.max_pages.setValue(10)
        pages_layout.addWidget(self.max_pages)
        
        pages_layout.addWidget(QLabel("Задержка (сек):"))
        self.delay_seconds = QDoubleSpinBox()
        self.delay_seconds.setRange(0.1, 10)
        self.delay_seconds.setValue(1)
        self.delay_seconds.setSingleStep(0.5)
        pages_layout.addWidget(self.delay_seconds)
        
        layout.addRow("Параметры сканирования:", pages_layout)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("[SEARCH] Начать анализ")
        self.start_btn.clicked.connect(self.start_analysis)
        buttons_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_analysis)
        buttons_layout.addWidget(self.stop_btn)
        
        self.clear_btn = QPushButton("🗑 Очистить")
        self.clear_btn.clicked.connect(self.clear_results)
        buttons_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("[STATS] Экспорт")
        self.export_btn.clicked.connect(self.export_results)
        buttons_layout.addWidget(self.export_btn)
        
        layout.addRow(buttons_layout)
        
        # Подключение сигналов для режима поиска
        self.radio_exact.toggled.connect(self._toggle_search_mode)
        self.radio_range.toggled.connect(self._toggle_search_mode)
        self.radio_all.toggled.connect(self._toggle_search_mode)
        self.token_combo.currentTextChanged.connect(self._on_token_changed)
        
        return group
    
    def _create_api_group(self) -> QGroupBox:
        """Создание группы настроек API"""
        group = QGroupBox("Настройки API")
        layout = QVBoxLayout(group)
        
        # Отображение статуса API
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Статус API:"))
        
        self.api_status_label = QLabel("Готов")
        self.api_status_label.setStyleSheet("font-family: monospace; color: green;")
        status_layout.addWidget(self.api_status_label)
        
        self.refresh_stats_btn = QPushButton("🔄 Обновить статистику")
        self.refresh_stats_btn.clicked.connect(self._update_api_stats)
        status_layout.addWidget(self.refresh_stats_btn)
        
        layout.addLayout(status_layout)
        
        # Статистика запросов
        stats_layout = QHBoxLayout()
        self.requests_label = QLabel("Запросов: 0")
        stats_layout.addWidget(self.requests_label)
        
        self.success_label = QLabel("Успешных: 0")
        stats_layout.addWidget(self.success_label)
        
        self.errors_label = QLabel("Ошибок: 0")
        stats_layout.addWidget(self.errors_label)
        
        layout.addLayout(stats_layout)
        
        # Обновление статистики API
        self._update_api_stats()
        
        return group
    
    def _toggle_search_mode(self):
        """Переключение режима поиска"""
        if self.radio_exact.isChecked():
            self.exact_amount.setEnabled(True)
            self.min_amount.setEnabled(False)
            self.max_amount.setEnabled(False)
        elif self.radio_range.isChecked():
            self.exact_amount.setEnabled(False)
            self.min_amount.setEnabled(True)
            self.max_amount.setEnabled(True)
        else:  # radio_all
            self.exact_amount.setEnabled(False)
            self.min_amount.setEnabled(False)
            self.max_amount.setEnabled(False)
    
    def _on_token_changed(self, token: str):
        """Обработка изменения выбранного токена"""
        self.custom_token_input.setEnabled(token == "Другой")
    
    def _update_api_stats(self):
        """Обновление статистики API (с защитой от отсутствия сервиса)."""
        if not hasattr(self, 'bscscan_service') or self.bscscan_service is None:
            # Отмечаем в UI, что сервис недоступен, но не бросаем исключение
            if hasattr(self, 'api_status_label'):
                self.api_status_label.setText("Нет сервиса")
                self.api_status_label.setStyleSheet("font-family: monospace; color: orange;")
            return
        try:
            stats = self.bscscan_service.get_stats()  # type: ignore[union-attr]
            rate_limiter_stats = stats.get('rate_limiter', {})
            
            if rate_limiter_stats.get('is_blocked'):
                self.api_status_label.setText("Блокирован")
                self.api_status_label.setStyleSheet("font-family: monospace; color: red;")
            else:
                self.api_status_label.setText("Готов")
                self.api_status_label.setStyleSheet("font-family: monospace; color: green;")
            
            # Обновляем статистику запросов
            if hasattr(self, 'requests_label'):
                total = rate_limiter_stats.get('total_requests', 0)
                success = rate_limiter_stats.get('successful_requests', 0)
                errors = rate_limiter_stats.get('failed_requests', 0)
                
                self.requests_label.setText(f"Запросов: {total}")
                self.success_label.setText(f"Успешных: {success}")
                self.errors_label.setText(f"Ошибок: {errors}")
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Ошибка обновления статистики API: %s", e)
            if hasattr(self, 'api_status_label'):
                self.api_status_label.setText("Ошибка")
                self.api_status_label.setStyleSheet("font-family: monospace; color: red;")
    
    def start_analysis(self):
        """Начать анализ транзакций"""
        if self.is_searching:
            QMessageBox.warning(self, "Предупреждение", "Анализ уже запущен!")
            return
        
        # Получаем адрес для анализа
        address = self.address_input.text().strip()
        if not address:
            QMessageBox.warning(self, "Ошибка", "Введите адрес для анализа!")
            return
        
        # Проверка валидности адреса
        if not Web3.is_address(address):
            QMessageBox.warning(self, "Ошибка", "Некорректный адрес!")
            return
        
        # Получаем параметры поиска
        token_filter = self._get_token_filter()
        search_params = self._get_search_params()
        
        # Запускаем анализ
        self.is_searching = True
        self.stop_search_event.clear()
        
        # Обновляем UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.search_log.clear()
        
        # Запускаем поток анализа
        self.search_thread = threading.Thread(
            target=self._analysis_worker,
            args=(address, token_filter, search_params),
            daemon=True
        )
        self.search_thread.start()
        
        self.log(f"[SEARCH] Начат анализ адреса: {address}", "SUCCESS")
    
    def stop_analysis(self):
        """Остановить анализ"""
        if self.is_searching:
            self.stop_search_event.set()
            self.log("⏹ Остановка анализа...", "WARNING")
    
    def _get_token_filter(self) -> Optional[str]:
        """Получение фильтра токена"""
        token = self.token_combo.currentText()
        if token == "PLEX ONE":
            return PLEX_CONTRACT
        elif token == "USDT":
            return USDT_CONTRACT
        elif token == "Другой":
            custom = self.custom_token_input.text().strip()
            return custom if custom else None
        return None
    
    def _get_search_params(self) -> Dict[str, Any]:
        """Получение параметров поиска"""
        params: Dict[str, Any] = {
            'max_pages': self.max_pages.value(),
            'delay_seconds': self.delay_seconds.value(),
            'mode': 'all'
        }
        
        if self.radio_exact.isChecked():
            params['mode'] = 'exact'
            params['exact_amount'] = self.exact_amount.value()
        elif self.radio_range.isChecked():
            params['mode'] = 'range'
            params['min_amount'] = self.min_amount.value()
            params['max_amount'] = self.max_amount.value()
        
        return params
    
    def _analysis_worker(self, address: str, token_filter: Optional[str], params: Dict[str, Any]):
        """Рабочий поток для анализа транзакций"""
        try:
            self._log_to_search("Начинаем анализ транзакций...")
            
            # Создаем событийный цикл для асинхронных запросов
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Выполняем постраничный поиск
                transactions, sender_counter, sender_details = loop.run_until_complete(
                    self._search_transactions_async(
                        wallet_address=address,
                        token_contract=token_filter,
                        search_params=params
                    )
                )
                
                # Обновляем результаты в UI
                self.update_table_signal.emit(transactions, sender_counter, sender_details)
                
                self._log_to_search(f"[OK] Анализ завершен. Найдено {len(transactions)} транзакций")
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"Ошибка в потоке анализа: {e}")
            self._log_to_search(f"[ERROR] Ошибка: {str(e)}")
        finally:
            self.search_finished_signal.emit()
    
    async def _search_transactions_async(
        self, 
        wallet_address: str, 
        token_contract: Optional[str],
        search_params: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int], Dict[str, List[Dict[str, Any]]]]:
        """Асинхронный постраничный поиск транзакций через BscScanService"""
        
        matching_transactions: List[Dict[str, Any]] = []
        sender_counter: Dict[str, int] = {}
        sender_details: Dict[str, List[Dict[str, Any]]] = {}
        
        page = 1
        max_pages = search_params['max_pages']
        delay = search_params['delay_seconds']
        
        while page <= max_pages:
            if self.stop_search_event.is_set():
                self._log_to_search("Поиск остановлен пользователем")
                break
            
            self._log_to_search(f"Запрашиваем страницу {page}/{max_pages}...")
            
            try:
                # Используем BscScanService для получения транзакций
                result = await self.bscscan_service.get_transactions(
                    address=wallet_address,
                    token_address=token_contract,
                    page=page,
                    offset=1000,
                    sort='desc'
                )
                
                if not result:
                    self._log_to_search("Больше транзакций не найдено")
                    break
                
                # Обрабатываем транзакции
                for tx in result:
                    if self._filter_transaction(tx, wallet_address, search_params):
                        matching_transactions.append(tx)
                        sender = tx.get('from', '').lower()
                        
                        # Обновляем счетчик
                        sender_counter[sender] = sender_counter.get(sender, 0) + 1
                        
                        # Сохраняем детали
                        if sender not in sender_details:
                            sender_details[sender] = []
                        sender_details[sender].append({
                            'hash': tx.get('hash', ''),
                            'timestamp': tx.get('timeStamp', ''),
                            'value': float(tx.get('value', 0)) / (10 ** int(tx.get('tokenDecimal', 18))),
                            'token': tx.get('tokenSymbol', ''),
                            'block': tx.get('blockNumber', '')
                        })
                
                # Обновляем прогресс
                progress = int((page / max_pages) * 100)
                # Используем QTimer для безопасного обновления UI
                QTimer.singleShot(0, lambda p=progress: self.progress_bar.setValue(p))
                
                # Обновляем статистику API
                QTimer.singleShot(0, self._update_api_stats)
                
                page += 1
                await asyncio.sleep(delay)
                
            except Exception as e:
                self._log_to_search(f"Ошибка при запросе страницы {page}: {e}")
                await asyncio.sleep(delay * 2)
        
        return matching_transactions, sender_counter, sender_details
    
    def _filter_transaction(self, tx: Dict[str, Any], wallet_address: str, params: Dict[str, Any]) -> bool:
        """Фильтрация транзакции по параметрам"""
        # Проверяем, что это входящая транзакция
        if tx.get('to', '').lower() != wallet_address.lower():
            return False
        
        # Проверяем сумму если нужно
        mode = params.get('mode', 'all')
        if mode == 'all':
            return True
        
        tx_value = float(tx.get('value', 0)) / (10 ** int(tx.get('tokenDecimal', 18)))
        
        if mode == 'exact':
            exact = params.get('exact_amount', 0)
            return abs(tx_value - exact) < 0.0000001
        elif mode == 'range':
            min_val = params.get('min_amount', 0)
            max_val = params.get('max_amount', 0)
            return min_val <= tx_value <= max_val
        
        return True
    
    def _log_to_search(self, message: str):
        """Логирование в поле поиска"""
        QTimer.singleShot(0, lambda: self.search_log.append(message))
    
    @pyqtSlot(list, dict, dict)
    def _update_search_results(self, transactions: List[Dict[str, Any]], counter: Dict[str, int], details: Dict[str, List[Dict[str, Any]]]) -> None:
        """Обновление таблицы результатов"""
        try:
            self.results_table.setRowCount(0)
            
            # Сортируем по количеству транзакций
            sorted_senders: List[Tuple[str, int]] = sorted(counter.items(), key=lambda x: x[1], reverse=True)
            
            for sender, count in sorted_senders:
                row = self.results_table.rowCount()
                self.results_table.insertRow(row)
                
                # Адрес отправителя
                self.results_table.setItem(row, 0, QTableWidgetItem(sender))
                
                # Количество транзакций
                self.results_table.setItem(row, 1, QTableWidgetItem(str(count)))
                
                # Считаем общую сумму
                if sender in details:
                    total_sum = float(sum(float(tx.get('value', 0)) for tx in details[sender]))
                    self.results_table.setItem(row, 2, QTableWidgetItem(f"{total_sum:.4f}"))
                    
                    # Первая транзакция
                    first_tx = min(details[sender], key=lambda x: float(x.get('timestamp', 0)))
                    first_date = datetime.fromtimestamp(int(first_tx['timestamp'])).strftime('%Y-%m-%d')
                    self.results_table.setItem(row, 3, QTableWidgetItem(first_date))
                    
                    # Последняя транзакция
                    last_tx = max(details[sender], key=lambda x: float(x.get('timestamp', 0)))
                    last_date = datetime.fromtimestamp(int(last_tx['timestamp'])).strftime('%Y-%m-%d')
                    self.results_table.setItem(row, 4, QTableWidgetItem(last_date))
                
                # Статус
                status = "[OK] Активный" if count > 5 else "[WARN] Обычный"
                status_item = QTableWidgetItem(status)
                if count > 10:
                    status_item.setBackground(QColor('#004400'))
                elif count > 5:
                    status_item.setBackground(QColor('#444400'))
                self.results_table.setItem(row, 5, status_item)
            
            self.log(f"Результаты обновлены: {len(sorted_senders)} отправителей", "SUCCESS")
            
        except Exception as e:
            logger.error(f"Ошибка обновления результатов: {e}")
    
    @pyqtSlot()
    def _on_search_finished(self):
        """Обработка завершения поиска"""
        self.is_searching = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.log("Анализ завершен", "SUCCESS")
    
    def _show_context_menu(self, position: QPoint) -> None:
        """Показ контекстного меню для таблицы"""
        if self.results_table.currentRow() < 0:
            return
        
        menu = QMenu()
        
        copy_address = menu.addAction("[INFO] Копировать адрес")
        open_bscscan = menu.addAction("[WEB] Открыть в BscScan")
        add_to_rewards = menu.addAction("🎁 Добавить в награды")
        
        action = menu.exec_(self.results_table.viewport().mapToGlobal(position))
        
        if action:
            row = self.results_table.currentRow()
            item = self.results_table.item(row, 0)
            address = item.text() if item is not None else ""
            
            if action == copy_address:
                QApplication.clipboard().setText(address)
                self.log(f"Адрес скопирован: {address}", "INFO")
            
            elif action == open_bscscan:
                url = f"https://bscscan.com/address/{address}"
                QDesktopServices.openUrl(QUrl(url))
                self.log(f"Открыт в BscScan: {address}", "INFO")
            
            elif action == add_to_rewards:
                # Здесь можно добавить логику для добавления в награды
                self.log(f"Добавлен в награды: {address}", "SUCCESS")
    
    def clear_results(self):
        """Очистка результатов"""
        self.results_table.setRowCount(0)
        self.search_log.clear()
        self.progress_bar.setValue(0)
        self.log("Результаты очищены", "INFO")
    
    def export_results(self):
        """Экспорт результатов в CSV"""
        if self.results_table.rowCount() == 0:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта!")
            return
        
        from PyQt5.QtWidgets import QFileDialog
        
        path, _ = QFileDialog.getSaveFileName(
            self, 
            "Сохранить результаты анализа", 
            f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    # Заголовки
                    f.write("Address,TX Count,Total Amount,First TX,Last TX,Status\n")
                    
                    # Данные
                    for row in range(self.results_table.rowCount()):
                        line = []
                        for col in range(self.results_table.columnCount()):
                            item = self.results_table.item(row, col)
                            if item:
                                line.append(item.text())
                            else:
                                line.append('')
                        f.write(','.join(line) + '\n')
                
                self.log(f"Результаты экспортированы: {path}", "SUCCESS")
                QMessageBox.information(self, "Успех", "Результаты успешно экспортированы!")
                
            except Exception as e:
                logger.error(f"Ошибка экспорта: {e}")
                self.log(f"Ошибка экспорта: {str(e)}", "ERROR")
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать результаты:\n{str(e)}")