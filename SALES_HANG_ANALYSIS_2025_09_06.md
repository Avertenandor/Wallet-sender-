# Анализ зависания автопродажи

**Дата:** 6 сентября 2025  
**Проблема:** Приложение повисло при первой продаже  
**Статус:** 🔧 В ПРОЦЕССЕ ИСПРАВЛЕНИЯ

## 🔍 Потенциальные причины зависания

### 1. **Блокирующие операции без таймаутов**
```python
# Проблемное место:
receipt = self.web3.eth.wait_for_transaction_receipt(swap_hash, timeout=300)
```
- **Проблема**: 300 секунд (5 минут) - слишком долго
- **Решение**: Уменьшить до 60-120 секунд

### 2. **Бесконечные retry циклы**
```python
# В _retry_call:
for attempt in range(max_retries):
    try:
        return func()
    except Exception as e:
        # Может зависнуть на сетевых ошибках
        time.sleep(delay * (attempt + 1))
```
- **Проблема**: Экспоненциальная задержка может быть слишком большой
- **Решение**: Ограничить максимальную задержку

### 3. **Блокирующие вызовы к блокчейну**
```python
# Проблемные места:
amounts_out = self._get_amounts_out_with_retry(amount_wei, path)
current_allowance = token_contract.functions.allowance(...).call()
```
- **Проблема**: Нет таймаутов для RPC вызовов
- **Решение**: Добавить таймауты для всех Web3 вызовов

### 4. **Мониторинг в основном потоке**
```python
# В _monitoring_worker:
while not self.stop_monitoring.is_set():
    # Может заблокироваться на любой операции
    for token_address, settings in self.monitored_tokens.items():
        # Выполнение продажи в том же потоке
        self._execute_sell(token_address, sell_amount, settings)
```
- **Проблема**: Продажа выполняется в потоке мониторинга
- **Решение**: Вынести продажу в отдельный поток

### 5. **Отсутствие обработки исключений**
```python
# В _execute_sell нет try-catch для критических операций:
signed_swap = self.web3.eth.account.sign_transaction(swap_tx, self.account.key)
swap_hash = self.web3.eth.send_raw_transaction(signed_swap.rawTransaction)
```
- **Проблема**: Любая ошибка может привести к зависанию
- **Решение**: Обернуть в try-catch с таймаутами

## 🔧 План исправлений

### 1. Добавить таймауты для всех операций
```python
# Для Web3 вызовов:
def _safe_web3_call(self, func, timeout=30):
    """Безопасный вызов Web3 с таймаутом"""
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Web3 call timeout")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        result = func()
        signal.alarm(0)
        return result
    except:
        signal.alarm(0)
        raise
```

### 2. Ограничить retry задержки
```python
# В _retry_call:
max_delay = 10  # Максимум 10 секунд
delay = min(delay * (attempt + 1), max_delay)
```

### 3. Вынести продажу в отдельный поток
```python
# В _monitoring_worker:
if should_sell and balance > 0:
    # Запускаем продажу в отдельном потоке
    sell_thread = threading.Thread(
        target=self._execute_sell_async,
        args=(token_address, sell_amount, settings),
        daemon=True
    )
    sell_thread.start()
```

### 4. Добавить heartbeat для мониторинга
```python
# В _monitoring_worker:
last_heartbeat = time.time()
while not self.stop_monitoring.is_set():
    # Проверяем каждые 30 секунд
    if time.time() - last_heartbeat > 30:
        self.log("💓 Мониторинг активен", "INFO")
        last_heartbeat = time.time()
```

### 5. Улучшить обработку ошибок
```python
# В _execute_sell:
try:
    # Все критические операции
except TimeoutError:
    self.log("⏰ Таймаут операции", "WARNING")
    return
except Exception as e:
    self.log(f"❌ Ошибка: {e}", "ERROR")
    return
```

## 🎯 Приоритеты исправлений

1. **Высокий**: Таймауты для Web3 вызовов
2. **Высокий**: Ограничение retry задержек
3. **Средний**: Отдельный поток для продаж
4. **Средний**: Heartbeat мониторинга
5. **Низкий**: Улучшение логирования

## 📋 Следующие шаги

1. Исправить таймауты в автопродаже
2. Добавить обработку ошибок
3. Протестировать исправления
4. Мониторить стабильность работы
