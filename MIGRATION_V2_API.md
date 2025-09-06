# Миграция на Etherscan V2 API

## Дата миграции: 30 августа 2025

## Причина миграции
BSCScan V1 API был отключен 15 августа 2025 года. Все проекты должны мигрировать на единый Etherscan V2 API, который поддерживает множество блокчейнов через параметр `chainid`.

## Основные изменения

### 1. Новый базовый URL
- **Было:** `https://api.bscscan.com/api`
- **Стало:** `https://api.etherscan.io/v2/api`

### 2. Обязательный параметр chainid
Все запросы теперь требуют параметр `chainid=56` для BSC (Binance Smart Chain).

### 3. Новые API ключи
Требуются ключи Etherscan (не BSCScan). Один ключ работает для всех поддерживаемых сетей.

**Текущие ключи:**
- RF1Q8SCFHFD1EVAP5A4WCMIM4DREA7UNUH
- U89HXHR9Y26CHMWAA9JUZ17YK2AAXS65CZ
- RAI3FTD9W53JPYZ2AHW8IBH9BXUC71NRH1

## Измененные файлы

### Новые файлы
1. `src/wallet_sender/api/etherscan.py` - новый модуль для работы с Etherscan V2 API

### Обновленные файлы
1. `main.py` - исправлены импорты и Qt атрибуты
2. `src/wallet_sender/api/bscscan.py` - теперь обертка над etherscan.py для обратной совместимости
3. `src/wallet_sender/api/__init__.py` - обновлен экспорт модулей
4. `src/wallet_sender/config.py` - добавлены Etherscan API ключи
5. `src/wallet_sender/services/bscscan_service.py` - обновлен для работы с V2 API

## Новые возможности V2 API

### 1. Получение списка держателей токенов
```python
holders = await api.get_token_holders(contract_address)
```

### 2. Получение информации о токене
```python
info = await api.get_token_info(contract_address)
```

### 3. Получение блока по временной метке
```python
block = await api.get_block_by_timestamp(timestamp)
```

### 4. Улучшенная работа с логами событий
```python
logs = await api.get_event_logs(from_block, to_block, address, topics)
```

## Обратная совместимость

Все существующие вызовы BSCScanAPI продолжают работать благодаря:
1. Класс `BSCScanAPI` теперь наследуется от `EtherscanAPI`
2. Свойство `bscscan_api_keys` в конфигурации возвращает `etherscan_api_keys`
3. Все методы сохранили свои сигнатуры

## Тестирование

### Проверить после миграции:
- [ ] Поиск транзакций по адресу
- [ ] Получение баланса кошелька
- [ ] Получение баланса токенов
- [ ] История транзакций
- [ ] Анализ держателей токенов
- [ ] Ротация API ключей
- [ ] Обработка лимитов запросов

## Дополнительная информация

### Документация
- [Etherscan V2 Migration Guide](https://docs.etherscan.io/v2-migration)
- [Etherscan V2 API Endpoints](https://docs.etherscan.io/etherscan-v2/api-endpoints)

### Поддерживаемые сети
Etherscan V2 API поддерживает следующие chainid:
- Ethereum Mainnet: 1
- BSC (Binance Smart Chain): 56
- Polygon: 137
- Avalanche: 43114
- И другие...

## Контакты для поддержки
При возникновении проблем с API обращайтесь:
- Etherscan Support: https://etherscan.io/contactus
- GitHub Issues: https://github.com/Avertenandor/Wallet-sender/issues
