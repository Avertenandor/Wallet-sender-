"""
Модели данных для WalletSender v2.1.1
Датаклассы для типизации и структурирования данных
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Literal
from datetime import datetime
import json


@dataclass
class Settings:
    """Настройки приложения"""
    # RPC настройки
    rpc_primary: str = "https://bsc-dataseed.binance.org/"
    rpc_fallback: str = "https://bsc-dataseed1.defibit.io/"
    chain_id: int = 56
    
    # Газ настройки
    gas_mode: Literal["auto", "manual"] = "auto"
    gas_price_wei: Optional[int] = None
    gas_limit_default: int = 100000
    
    # Лимиты и ретраи
    max_rps: int = 10  # максимум запросов в секунду
    retries: int = 3
    backoff_ms: int = 1000
    timeout_ms: int = 30000
    
    # Токены
    default_token: Optional[str] = None
    decimals_map: Dict[str, int] = field(default_factory=lambda: {
        "0x55d398326f99059ff775485246999027b3197955": 18,  # USDT
        "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1": 18,  # PLEX ONE
    })
    
    # Локализация
    locale: str = "ru_RU"
    timezone: str = "Europe/Moscow"
    
    # Директории
    logs_dir: str = "logs"
    exports_dir: str = "exports"
    
    # Безопасность
    autolock_min: int = 30  # автоблокировка через N минут
    
    # API ключи
    etherscan_keys: list[str] = field(default_factory=lambda: [
        "RF1Q8SCFHFD1EVAP5A4WCMIM4DREA7UNUH",
        "U89HXHR9Y26CHMWAA9JUZ17YK2AAXS65CZ",
        "RAI3FTD9W53JPYZ2AHW8IBH9BXUC71NRH1"
    ])
    
    def to_dict(self) -> dict:
        """Преобразование в словарь для сохранения"""
        return {
            "rpc_primary": self.rpc_primary,
            "rpc_fallback": self.rpc_fallback,
            "chain_id": self.chain_id,
            "gas_mode": self.gas_mode,
            "gas_price_wei": self.gas_price_wei,
            "gas_limit_default": self.gas_limit_default,
            "max_rps": self.max_rps,
            "retries": self.retries,
            "backoff_ms": self.backoff_ms,
            "timeout_ms": self.timeout_ms,
            "default_token": self.default_token,
            "decimals_map": self.decimals_map,
            "locale": self.locale,
            "timezone": self.timezone,
            "logs_dir": self.logs_dir,
            "exports_dir": self.exports_dir,
            "autolock_min": self.autolock_min,
            "etherscan_keys": self.etherscan_keys
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Создание из словаря"""
        return cls(**data)


@dataclass
class Job:
    """Задание в очереди"""
    job_id: str
    created_ts: datetime
    title: str
    mode: Literal["BNB", "ERC20"]
    sender: str
    total_items: int
    done: int = 0
    failed: int = 0
    state: Literal["queued", "running", "paused", "completed", "aborted"] = "queued"
    params_json: str = "{}"  # JSON с параметрами задания
    
    @property
    def progress(self) -> float:
        """Прогресс выполнения в процентах"""
        if self.total_items == 0:
            return 0.0
        return (self.done + self.failed) / self.total_items * 100
    
    @property
    def params(self) -> dict:
        """Параметры задания"""
        try:
            return json.loads(self.params_json)
        except:
            return {}
    
    def set_params(self, params: dict):
        """Установка параметров"""
        self.params_json = json.dumps(params, ensure_ascii=False)


@dataclass
class TxRecord:
    """Запись о транзакции"""
    id: Optional[int] = None
    ts: datetime = field(default_factory=datetime.now)
    job_id: Optional[str] = None
    from_addr: str = ""
    to_addr: str = ""
    token: Optional[str] = None  # None для BNB, адрес для токенов
    amount_wei: int = 0
    tx_hash: Optional[str] = None
    status: Literal["pending", "signed", "broadcasted", "mined", "failed", "canceled"] = "pending"
    gas_price_wei: Optional[int] = None
    gas_used: Optional[int] = None
    error_code: Optional[str] = None
    note: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        """Успешная транзакция"""
        return self.status == "mined"
    
    @property
    def is_failed(self) -> bool:
        """Неудачная транзакция"""
        return self.status in ["failed", "canceled"]
    
    @property
    def is_pending(self) -> bool:
        """В процессе выполнения"""
        return self.status in ["pending", "signed", "broadcasted"]
    
    @property
    def gas_cost_wei(self) -> int:
        """Стоимость газа в wei"""
        if self.gas_price_wei and self.gas_used:
            return self.gas_price_wei * self.gas_used
        return 0


@dataclass
class Reward:
    """Награда за транзакцию"""
    id: Optional[int] = None
    ts: datetime = field(default_factory=datetime.now)
    addr: str = ""
    token: str = ""  # адрес токена или "BNB"
    amount_wei: int = 0
    source_job_id: Optional[str] = None
    rewarded_tx: Optional[str] = None  # хэш транзакции награды
    note: Optional[str] = None
    
    @property
    def is_rewarded(self) -> bool:
        """Награда выплачена"""
        return self.rewarded_tx is not None


@dataclass
class SearchResult:
    """Результат поиска"""
    type: Literal["tx", "job", "reward"]
    id: int
    title: str
    subtitle: str
    timestamp: datetime
    data: dict = field(default_factory=dict)


@dataclass
class AnalyticsData:
    """Данные аналитики"""
    period_start: datetime
    period_end: datetime
    total_tx: int = 0
    success_tx: int = 0
    failed_tx: int = 0
    total_volume_wei: int = 0
    total_gas_wei: int = 0
    unique_senders: int = 0
    unique_receivers: int = 0
    tokens_used: Dict[str, int] = field(default_factory=dict)
    avg_gas_price: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Процент успешных транзакций"""
        if self.total_tx == 0:
            return 0.0
        return self.success_tx / self.total_tx * 100
