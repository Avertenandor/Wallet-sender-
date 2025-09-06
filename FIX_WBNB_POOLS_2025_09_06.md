# Исправление проблемы с несуществующими пулами WBNB

**Дата:** 6 сентября 2025  
**Файл:** `src/wallet_sender/ui/tabs/auto_buy_tab.py`  
**Проблема:** Вкладка автопокупки пыталась использовать несуществующий прямой пул WBNB → PLEX ONE

## 🐛 Описание проблемы

Вкладка автопокупки содержала логику, которая пыталась использовать несуществующий прямой пул ликвидности между WBNB и PLEX ONE, что приводило к ошибкам при попытке покупки PLEX ONE за BNB.

### Проблемные места в коде:

1. **Функция `_check_known_pools`** - пыталась найти прямой пул WBNB → PLEX ONE
2. **Логика определения путей** - предполагала существование прямого пула WBNB → PLEX ONE
3. **Создание транзакций** - использовала несуществующий путь WBNB → PLEX ONE

## ✅ Внесенные исправления

### 1. Обновлена функция `_check_known_pools`

**Было:**
```python
# Для BNB пробуем разные пути
paths_to_try = [
    [CONTRACTS['WBNB'], CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']],  # BNB->USDT->PLEX
    [CONTRACTS['WBNB'], CONTRACTS['PLEX_ONE']],  # BNB->PLEX (если есть прямой пул)
]
```

**Стало:**
```python
# Для BNB используем только существующий путь через USDT
# WBNB -> USDT -> PLEX ONE (прямой пул WBNB->PLEX не существует)
try:
    bnb_path = [CONTRACTS['WBNB'], CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']]
    result = self._get_amounts_out_with_retry(amount_in, bnb_path)
    if result and result[-1] > 0:
        self.log(f"✅ Найден рабочий путь BNB->USDT->PLEX! Результат: {result}", "SUCCESS")
        return result
```

### 2. Исправлена логика определения путей для BNB

**Было:**
```python
if len(amounts_out) == 2:  # Прямой путь BNB -> PLEX ONE
    path = [CONTRACTS['WBNB'], CONTRACTS['PLEX_ONE']]
    self.log("✅ Используем прямой путь: BNB -> PLEX ONE", "SUCCESS")
else:  # Путь через USDT BNB -> USDT -> PLEX ONE
    path = [CONTRACTS['WBNB'], CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']]
    self.log("✅ Используем путь через USDT: BNB -> USDT -> PLEX ONE", "SUCCESS")
```

**Стало:**
```python
# Для BNB всегда используем путь через USDT (прямой пул WBNB->PLEX не существует)
path = [CONTRACTS['WBNB'], CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']]
self.log("✅ Используем путь через USDT: BNB -> USDT -> PLEX ONE", "SUCCESS")
```

### 3. Исправлена логика определения путей для USDT

**Было:**
```python
if len(amounts_out) == 2:  # Прямой путь USDT -> PLEX ONE
    path = [CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']]
    self.log("✅ Используем прямой путь: USDT -> PLEX ONE", "SUCCESS")
else:  # Путь через WBNB USDT -> WBNB -> PLEX ONE
    path = [CONTRACTS['USDT'], CONTRACTS['WBNB'], CONTRACTS['PLEX_ONE']]
    self.log("✅ Используем путь через WBNB: USDT -> WBNB -> PLEX ONE", "SUCCESS")
```

**Стало:**
```python
# Для USDT используем прямой путь (пул USDT->PLEX существует)
path = [CONTRACTS['USDT'], CONTRACTS['PLEX_ONE']]
self.log("✅ Используем прямой путь: USDT -> PLEX ONE", "SUCCESS")
```

### 4. Исправлено создание транзакций для BNB

**Было:**
```python
# Для PLEX ONE используем прямой путь к WBNB
if token_address.lower() == CONTRACTS['PLEX_ONE'].lower():
    path = [
        CONTRACTS['WBNB'],  # WBNB
        CONTRACTS['PLEX_ONE']  # PLEX ONE
    ]
    self.log(f"🔄 Путь обмена: WBNB -> PLEX ONE (прямой)", "INFO")
```

**Стало:**
```python
# Для PLEX ONE используем путь через USDT (прямой пул WBNB->PLEX не существует)
if token_address.lower() == CONTRACTS['PLEX_ONE'].lower():
    path = [
        CONTRACTS['WBNB'],  # WBNB
        CONTRACTS['USDT'],  # USDT
        CONTRACTS['PLEX_ONE']  # PLEX ONE
    ]
    self.log(f"🔄 Путь обмена: WBNB -> USDT -> PLEX ONE", "INFO")
```

### 5. Обновлена логика отображения путей

**Было:**
```python
if len(path) == 2:
    self.log(f"🔄 Путь обмена: BNB -> PLEX ONE (прямой)", "INFO")
else:
    self.log(f"🔄 Путь обмена: BNB -> USDT -> PLEX ONE (через USDT)", "INFO")
```

**Стало:**
```python
# Для BNB всегда через USDT (прямой пул WBNB->PLEX не существует)
self.log(f"🔄 Путь обмена: BNB -> USDT -> PLEX ONE (через USDT)", "INFO")
```

## 📊 Результат исправлений

### До исправления:
- ❌ Попытки использовать несуществующий пул WBNB → PLEX ONE
- ❌ Ошибки при покупке PLEX ONE за BNB
- ❌ Неправильная логика определения путей

### После исправления:
- ✅ Используется только существующий путь BNB → USDT → PLEX ONE
- ✅ Прямой путь USDT → PLEX ONE для покупок за USDT
- ✅ Корректная логика определения путей
- ✅ Улучшенное логирование

## 🎯 Поддерживаемые пути обмена

### Для покупки PLEX ONE:

**За BNB:**
- `BNB → WBNB → USDT → PLEX ONE` ✅ (единственный рабочий путь)

**За USDT:**
- `USDT → PLEX ONE` ✅ (прямой путь)

### Для других токенов:
- `BNB → WBNB → [TOKEN]` ✅ (стандартный путь)
- `USDT → [TOKEN]` ✅ (если пул существует)

## 🔍 Тестирование

### Рекомендуемые тесты:

1. **Покупка PLEX ONE за BNB:**
   - Проверить, что используется путь BNB → USDT → PLEX ONE
   - Убедиться в успешном выполнении транзакции

2. **Покупка PLEX ONE за USDT:**
   - Проверить, что используется прямой путь USDT → PLEX ONE
   - Убедиться в успешном выполнении транзакции

3. **Покупка других токенов:**
   - Проверить стандартные пути обмена
   - Убедиться в корректной работе

## 📝 Логи для мониторинга

После исправления в логах должны появляться следующие сообщения:

```
✅ Найден рабочий путь BNB->USDT->PLEX! Результат: [amounts]
✅ Используем путь через USDT: BNB -> USDT -> PLEX ONE
🔄 Путь обмена: WBNB -> USDT -> PLEX ONE
```

## ⚠️ Важные замечания

1. **Не удаляйте исправления** - они критически важны для корректной работы
2. **Мониторинг логов** - следите за сообщениями о путях обмена
3. **Тестирование** - обязательно протестируйте покупки перед продакшеном
4. **Документация** - обновите документацию пользователей о поддерживаемых путях

## 🔄 Связанные файлы

- `src/wallet_sender/ui/tabs/auto_buy_tab.py` - основной исправленный файл
- `WBNB_POOL_ISSUE.md` - документация проблемы
- `CONTEXT_SUMMARY.md` - общая сводка проекта

---

**Статус:** ✅ Исправлено  
**Тестирование:** Требуется  
**Готовность к продакшену:** Да (после тестирования)