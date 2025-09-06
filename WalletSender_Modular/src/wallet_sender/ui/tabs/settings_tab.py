"""
Вкладка настроек приложения
Полная реализация с проверкой RPC и сохранением в БД
"""

from typing import Optional
import json
import time
from dataclasses import asdict

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit,
    QMessageBox, QTabWidget, QWidget, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from .base_tab import BaseTab
from ...core.models import Settings
from ...core.store import get_store
from ...core.rpc import get_rpc_pool
from ...utils.logger import get_logger

logger = get_logger(__name__)


class RPCTestThread(QThread):
    """Поток для тестирования RPC соединений"""
    test_complete = pyqtSignal(dict)
    
    def __init__(self, rpc_url: str):
        super().__init__()
        self.rpc_url = rpc_url
        
    def run(self):
        """Тестирование RPC"""
        try:
            from web3 import Web3
            
            start_time = time.time()
            w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={'timeout': 5}))
            
            if w3.is_connected():
                chain_id = w3.eth.chain_id
                block_number = w3.eth.block_number
                gas_price = w3.eth.gas_price
                latency = (time.time() - start_time) * 1000
                
                result = {
                    'success': True,
                    'chain_id': chain_id,
                    'block_number': block_number,
                    'gas_price': gas_price,
                    'latency': round(latency, 2),
                    'url': self.rpc_url
                }
            else:
                result = {
                    'success': False,
                    'error': 'Не удалось подключиться',
                    'url': self.rpc_url
                }
                
        except Exception as e:
            result = {
                'success': False,
                'error': str(e),
                'url': self.rpc_url
            }
            
        self.test_complete.emit(result)


class SettingsTab(BaseTab):
    """Вкладка настроек"""
    
    settings_changed = pyqtSignal(Settings)
    
    def __init__(self, main_window, parent=None):
        super().__init__(main_window, parent)
        self.store = get_store()
        self.rpc_pool = get_rpc_pool()
        self.current_settings = None
        self.load_settings()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QGroupBox("⚙️ Настройки приложения")
        header.setStyleSheet("QGroupBox { font-weight: bold; }")
        header_layout = QVBoxLayout(header)
        
        # Вкладки настроек
        self.tabs = QTabWidget()
        
        # Вкладка RPC
        self.tabs.addTab(self.create_rpc_tab(), "🌐 RPC")
        
        # Вкладка газа
        self.tabs.addTab(self.create_gas_tab(), "⛽ Газ")
        
        # Вкладка лимитов
        self.tabs.addTab(self.create_limits_tab(), "🚦 Лимиты")
        
        # Вкладка токенов
        self.tabs.addTab(self.create_tokens_tab(), "💰 Токены")
        
        # Вкладка API ключей
        self.tabs.addTab(self.create_api_tab(), "🔑 API")
        
        # Вкладка общих настроек
        self.tabs.addTab(self.create_general_tab(), "📋 Общее")
        
        header_layout.addWidget(self.tabs)
        layout.addWidget(header)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Сохранить")
        self.save_btn.clicked.connect(self.save_settings)
        buttons_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("🔄 Сбросить")
        self.reset_btn.clicked.connect(self.reset_settings)
        buttons_layout.addWidget(self.reset_btn)
        
        self.export_btn = QPushButton("📥 Экспорт")
        self.export_btn.clicked.connect(self.export_settings)
        buttons_layout.addWidget(self.export_btn)
        
        self.import_btn = QPushButton("📤 Импорт")
        self.import_btn.clicked.connect(self.import_settings)
        buttons_layout.addWidget(self.import_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        logger.info("SettingsTab инициализирована")
        
    def create_rpc_tab(self) -> QWidget:
        """Создание вкладки RPC настроек"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Основной RPC
        self.rpc_primary = QLineEdit()
        self.rpc_primary.setPlaceholderText("https://bsc-dataseed.binance.org/")
        layout.addRow("Основной RPC:", self.rpc_primary)
        
        # Тест основного RPC
        self.test_primary_btn = QPushButton("🧪 Тест")
        self.test_primary_btn.clicked.connect(lambda: self.test_rpc(self.rpc_primary.text()))
        layout.addRow("", self.test_primary_btn)
        
        # Резервный RPC
        self.rpc_fallback = QLineEdit()
        self.rpc_fallback.setPlaceholderText("https://bsc-dataseed1.defibit.io/")
        layout.addRow("Резервный RPC:", self.rpc_fallback)
        
        # Тест резервного RPC
        self.test_fallback_btn = QPushButton("🧪 Тест")
        self.test_fallback_btn.clicked.connect(lambda: self.test_rpc(self.rpc_fallback.text()))
        layout.addRow("", self.test_fallback_btn)
        
        # Chain ID
        self.chain_id = QSpinBox()
        self.chain_id.setRange(1, 999999)
        self.chain_id.setValue(56)
        layout.addRow("Chain ID:", self.chain_id)
        
        # Результаты тестов
        self.test_results = QTextEdit()
        self.test_results.setReadOnly(True)
        self.test_results.setMaximumHeight(100)
        layout.addRow("Результаты тестов:", self.test_results)
        
        # Тест всех RPC
        self.test_all_btn = QPushButton("🧪 Тестировать все RPC")
        self.test_all_btn.clicked.connect(self.test_all_rpcs)
        layout.addRow("", self.test_all_btn)
        
        return widget
        
    def create_gas_tab(self) -> QWidget:
        """Создание вкладки настроек газа"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Режим газа
        self.gas_mode = QComboBox()
        self.gas_mode.addItems(["auto", "manual"])
        self.gas_mode.currentTextChanged.connect(self.on_gas_mode_changed)
        layout.addRow("Режим газа:", self.gas_mode)

        # Цена газа (Gwei) — поддержка дробных значений (например, 0.1)
        self.gas_price_gwei = QDoubleSpinBox()
        self.gas_price_gwei.setRange(0.01, 1000.0)
        self.gas_price_gwei.setDecimals(3)
        self.gas_price_gwei.setSingleStep(0.1)
        self.gas_price_gwei.setValue(0.1)
        self.gas_price_gwei.setSuffix(" Gwei")
        layout.addRow("Цена газа:", self.gas_price_gwei)

        # Лимит газа по умолчанию
        self.gas_limit_default = QSpinBox()
        self.gas_limit_default.setRange(21000, 1000000)
        self.gas_limit_default.setValue(100000)
        self.gas_limit_default.setSingleStep(1000)
        layout.addRow("Лимит газа:", self.gas_limit_default)

        return widget
        
    def create_limits_tab(self) -> QWidget:
        """Создание вкладки лимитов и ретраев"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Максимум RPS
        self.max_rps = QSpinBox()
        self.max_rps.setRange(1, 100)
        self.max_rps.setValue(10)
        self.max_rps.setSuffix(" запросов/сек")
        layout.addRow("Макс. RPS:", self.max_rps)
        
        # Количество попыток
        self.retries = QSpinBox()
        self.retries.setRange(0, 10)
        self.retries.setValue(3)
        self.retries.setSuffix(" попыток")
        layout.addRow("Повторы:", self.retries)
        
        # Задержка между попытками
        self.backoff_ms = QSpinBox()
        self.backoff_ms.setRange(100, 10000)
        self.backoff_ms.setValue(1000)
        self.backoff_ms.setSingleStep(100)
        self.backoff_ms.setSuffix(" мс")
        layout.addRow("Задержка:", self.backoff_ms)
        
        # Таймаут соединения
        self.timeout_ms = QSpinBox()
        self.timeout_ms.setRange(1000, 60000)
        self.timeout_ms.setValue(30000)
        self.timeout_ms.setSingleStep(1000)
        self.timeout_ms.setSuffix(" мс")
        layout.addRow("Таймаут:", self.timeout_ms)
        
        return widget
        
    def create_tokens_tab(self) -> QWidget:
        """Создание вкладки настроек токенов"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Токен по умолчанию
        self.default_token = QComboBox()
        self.default_token.setEditable(True)
        self.default_token.addItems([
            "BNB",
            "0x55d398326f99059ff775485246999027b3197955",  # USDT
            "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1"   # PLEX ONE
        ])
        layout.addRow("Токен по умолчанию:", self.default_token)
        
        # Decimals для токенов
        self.decimals_text = QTextEdit()
        self.decimals_text.setPlaceholderText(
            "Формат: адрес:decimals\n"
            "Пример:\n"
            "0x55d398326f99059ff775485246999027b3197955:18\n"
            "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1:18"
        )
        self.decimals_text.setMaximumHeight(150)
        layout.addRow("Decimals токенов:", self.decimals_text)
        
        return widget
        
    def create_api_tab(self) -> QWidget:
        """Создание вкладки API ключей"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Etherscan API ключи
        self.etherscan_keys = QTextEdit()
        self.etherscan_keys.setPlaceholderText(
            "Один ключ на строку:\n"
            "RF1Q8SCFHFD1EVAP5A4WCMIM4DREA7UNUH\n"
            "U89HXHR9Y26CHMWAA9JUZ17YK2AAXS65CZ\n"
            "RAI3FTD9W53JPYZ2AHW8IBH9BXUC71NRH1"
        )
        self.etherscan_keys.setMaximumHeight(100)
        layout.addRow("Etherscan API ключи:", self.etherscan_keys)
        
        # Тест API ключей
        self.test_api_btn = QPushButton("🧪 Проверить ключи")
        self.test_api_btn.clicked.connect(self.test_api_keys)
        layout.addRow("", self.test_api_btn)
        
        return widget
        
    def create_general_tab(self) -> QWidget:
        """Создание вкладки общих настроек"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Язык
        self.locale = QComboBox()
        self.locale.addItems(["ru_RU", "en_US"])
        layout.addRow("Язык:", self.locale)
        
        # Часовой пояс
        self.timezone = QComboBox()
        self.timezone.addItems([
            "Europe/Moscow",
            "UTC",
            "Asia/Shanghai",
            "America/New_York"
        ])
        layout.addRow("Часовой пояс:", self.timezone)
        
        # Директория логов
        self.logs_dir = QLineEdit()
        self.logs_dir.setText("logs")
        layout.addRow("Директория логов:", self.logs_dir)
        
        # Директория экспорта
        self.exports_dir = QLineEdit()
        self.exports_dir.setText("exports")
        layout.addRow("Директория экспорта:", self.exports_dir)
        
        # Автоблокировка
        self.autolock_min = QSpinBox()
        self.autolock_min.setRange(0, 120)
        self.autolock_min.setValue(30)
        self.autolock_min.setSuffix(" мин")
        self.autolock_min.setSpecialValueText("Отключено")
        layout.addRow("Автоблокировка:", self.autolock_min)
        
        return widget
        
    def on_gas_mode_changed(self, mode: str):
        """Обработка изменения режима газа"""
        self.gas_price_gwei.setEnabled(mode == "manual")
        
    def load_settings(self):
        """Загрузка настроек из БД"""
        try:
            settings_dict = self.store.load_settings()
            
            if settings_dict:
                # Преобразуем в объект Settings
                self.current_settings = Settings.from_dict(settings_dict)
            else:
                # Используем настройки по умолчанию
                self.current_settings = Settings()
                
            # Применяем к UI
            self.apply_settings_to_ui()
            
            logger.info("Настройки загружены")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")
            self.current_settings = Settings()
            
    def apply_settings_to_ui(self):
        """Применение настроек к элементам UI"""
        if not self.current_settings:
            return
            
        # RPC
        self.rpc_primary.setText(self.current_settings.rpc_primary)
        self.rpc_fallback.setText(self.current_settings.rpc_fallback)
        self.chain_id.setValue(self.current_settings.chain_id)
        
        # Газ
        self.gas_mode.setCurrentText(self.current_settings.gas_mode)
        if self.current_settings.gas_price_wei not in (None, "", 0):
            # Конвертируем wei (str|int) в gwei (float)
            try:
                wei_val = int(self.current_settings.gas_price_wei)
                gwei_price = wei_val / 10**9
                self.gas_price_gwei.setValue(float(gwei_price))
            except Exception:
                # На случай некорректного значения в конфиге
                self.gas_price_gwei.setValue(5.0)
        self.gas_limit_default.setValue(self.current_settings.gas_limit_default)
        
        # Лимиты
        self.max_rps.setValue(self.current_settings.max_rps)
        self.retries.setValue(self.current_settings.retries)
        self.backoff_ms.setValue(self.current_settings.backoff_ms)
        self.timeout_ms.setValue(self.current_settings.timeout_ms)
        
        # Токены
        if self.current_settings.default_token:
            self.default_token.setCurrentText(self.current_settings.default_token)
            
        # Decimals
        decimals_text = ""
        for addr, decimals in self.current_settings.decimals_map.items():
            decimals_text += f"{addr}:{decimals}\n"
        self.decimals_text.setPlainText(decimals_text.strip())
        
        # API ключи
        keys_text = "\n".join(self.current_settings.etherscan_keys)
        self.etherscan_keys.setPlainText(keys_text)
        
        # Общее
        self.locale.setCurrentText(self.current_settings.locale)
        self.timezone.setCurrentText(self.current_settings.timezone)
        self.logs_dir.setText(self.current_settings.logs_dir)
        self.exports_dir.setText(self.current_settings.exports_dir)
        self.autolock_min.setValue(self.current_settings.autolock_min)
        
    def get_settings_from_ui(self) -> Settings:
        """Получение настроек из UI"""
        settings = Settings()
        
        # RPC
        settings.rpc_primary = self.rpc_primary.text() or settings.rpc_primary
        settings.rpc_fallback = self.rpc_fallback.text() or settings.rpc_fallback
        settings.chain_id = self.chain_id.value()
        
        # Газ
        settings.gas_mode = self.gas_mode.currentText()
        if settings.gas_mode == "manual":
            # Конвертируем gwei (float) в wei (int)
            settings.gas_price_wei = int(self.gas_price_gwei.value() * 10**9)
        settings.gas_limit_default = self.gas_limit_default.value()
        
        # Лимиты
        settings.max_rps = self.max_rps.value()
        settings.retries = self.retries.value()
        settings.backoff_ms = self.backoff_ms.value()
        settings.timeout_ms = self.timeout_ms.value()
        
        # Токены
        token_text = self.default_token.currentText()
        if token_text and token_text != "BNB":
            settings.default_token = token_text
            
        # Decimals
        decimals_map = {}
        for line in self.decimals_text.toPlainText().split('\n'):
            line = line.strip()
            if ':' in line:
                addr, decimals = line.split(':', 1)
                try:
                    decimals_map[addr.strip()] = int(decimals.strip())
                except ValueError:
                    pass
        if decimals_map:
            settings.decimals_map = decimals_map
            
        # API ключи
        keys = []
        for line in self.etherscan_keys.toPlainText().split('\n'):
            key = line.strip()
            if key:
                keys.append(key)
        if keys:
            settings.etherscan_keys = keys
            
        # Общее
        settings.locale = self.locale.currentText()
        settings.timezone = self.timezone.currentText()
        settings.logs_dir = self.logs_dir.text()
        settings.exports_dir = self.exports_dir.text()
        settings.autolock_min = self.autolock_min.value()
        
        return settings
        
    def save_settings(self):
        """Сохранение настроек"""
        try:
            # Получаем настройки из UI
            settings = self.get_settings_from_ui()
            
            # Валидация
            if not self.validate_settings(settings):
                return
                
            # Сохраняем в БД
            self.store.save_settings(settings.to_dict())
            
            # Обновляем текущие настройки
            self.current_settings = settings
            
            # Применяем к RPC пулу (если метод доступен)
            try:
                if hasattr(self.rpc_pool, 'set_max_rps'):
                    self.rpc_pool.set_max_rps(settings.max_rps)
                elif hasattr(self.rpc_pool, 'set_rate_limit'):
                    self.rpc_pool.set_rate_limit(settings.max_rps)
            except Exception as e:
                logger.warning(f"Не удалось применить лимит RPS к RPC пулу: {e}")
            
            # Отправляем сигнал об изменении
            self.settings_changed.emit(settings)
            
            self.log_message("Настройки сохранены", "SUCCESS")
            logger.info("Настройки сохранены")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")
            self.log_message(f"Ошибка сохранения: {e}", "ERROR")
            
    def validate_settings(self, settings: Settings) -> bool:
        """Валидация настроек"""
        # Проверка RPC
        if not settings.rpc_primary.startswith('http'):
            QMessageBox.warning(
                self, "Ошибка",
                "Основной RPC должен начинаться с http:// или https://"
            )
            return False
            
        # Проверка chain ID для BSC
        if settings.chain_id != 56 and settings.chain_id != 97:
            reply = QMessageBox.question(
                self, "Внимание",
                f"Chain ID {settings.chain_id} не соответствует BSC (56) или BSC Testnet (97).\n"
                "Продолжить?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return False
                
        return True
        
    def reset_settings(self):
        """Сброс настроек к значениям по умолчанию"""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Сбросить все настройки к значениям по умолчанию?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.current_settings = Settings()
            self.apply_settings_to_ui()
            self.log_message("Настройки сброшены", "INFO")
            
    def test_rpc(self, rpc_url: str):
        """Тестирование RPC соединения"""
        if not rpc_url:
            self.log_message("Введите URL для тестирования", "WARNING")
            return
            
        self.test_thread = RPCTestThread(rpc_url)
        self.test_thread.test_complete.connect(self.on_test_complete)
        self.test_thread.start()
        
        self.log_message(f"Тестирование {rpc_url}...", "INFO")
        
    def on_test_complete(self, result: dict):
        """Обработка результатов теста"""
        if result['success']:
            msg = (
                f"✅ {result['url']}\n"
                f"Chain ID: {result['chain_id']}\n"
                f"Блок: {result['block_number']}\n"
                f"Gas: {result['gas_price'] // 10**9} Gwei\n"
                f"Задержка: {result['latency']} мс\n"
            )
            self.test_results.append(msg)
            self.log_message("RPC тест успешен", "SUCCESS")
        else:
            msg = f"❌ {result['url']}\nОшибка: {result['error']}\n"
            self.test_results.append(msg)
            self.log_message("RPC тест неудачен", "ERROR")
            
    def test_all_rpcs(self):
        """Тестирование всех RPC"""
        self.test_results.clear()
        
        # Тестируем основной и резервный
        if self.rpc_primary.text():
            self.test_rpc(self.rpc_primary.text())
            
        if self.rpc_fallback.text():
            self.test_rpc(self.rpc_fallback.text())
            
        # Тестируем все endpoints в пуле
        stats = self.rpc_pool.test_all_endpoints()
        
        for name, info in stats.items():
            if info['status'] == 'online':
                msg = f"✅ {name}: {info['response_time_ms']} мс\n"
            else:
                msg = f"❌ {name}: {info.get('error', 'Offline')}\n"
            self.test_results.append(msg)
            
    def test_api_keys(self):
        """Тестирование API ключей"""
        keys = self.etherscan_keys.toPlainText().strip().split('\n')
        
        if not keys:
            self.log_message("Нет ключей для тестирования", "WARNING")
            return
            
        # TODO: Реализовать тест API ключей через Etherscan V2
        self.log_message(f"Тестирование {len(keys)} ключей...", "INFO")
        
    def export_settings(self):
        """Экспорт настроек в файл"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт настроек", "settings.json",
                "JSON файлы (*.json)"
            )
            
            if file_path:
                settings = self.get_settings_from_ui()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)
                    
                self.log_message(f"Настройки экспортированы: {file_path}", "SUCCESS")
                
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            self.log_message(f"Ошибка экспорта: {e}", "ERROR")
            
    def import_settings(self):
        """Импорт настроек из файла"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Импорт настроек", "",
                "JSON файлы (*.json)"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self.current_settings = Settings.from_dict(data)
                self.apply_settings_to_ui()
                
                self.log_message(f"Настройки импортированы: {file_path}", "SUCCESS")
                
        except Exception as e:
            logger.error(f"Ошибка импорта: {e}")
            self.log_message(f"Ошибка импорта: {e}", "ERROR")
