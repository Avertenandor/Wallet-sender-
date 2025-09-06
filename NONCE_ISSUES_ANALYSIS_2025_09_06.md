# Анализ проблем с nonce

**Дата:** 6 сентября 2025  
**Проблема:** Приложение падает из-за проблем с nonce  
**Статус:** 🔧 В ПРОЦЕССЕ ИСПРАВЛЕНИЯ

## 🔍 Анализ проблем с nonce

### Основные проблемы:

1. **Race conditions при получении nonce**
   ```python
   # Проблемное место:
   current_nonce = self.web3.eth.get_transaction_count(self.account.address)
   # ... другие операции ...
   final_nonce = self.web3.eth.get_transaction_count(self.account.address)
   ```
   - **Проблема**: Между вызовами nonce может измениться
   - **Решение**: Централизованное управление nonce

2. **Недостаточная обработка nonce ошибок**
   ```python
   # Текущая обработка:
   if "nonce too low" in str(e):
       # Только "nonce too low"
   ```
   - **Проблема**: Не обрабатываются "nonce too high", "replacement transaction underpriced"
   - **Решение**: Полная обработка всех nonce ошибок

3. **Отсутствие синхронизации между approve и swap**
   ```python
   # Проблема:
   # Approve использует nonce N
   # Swap пытается использовать nonce N+1, но approve еще не подтвержден
   ```
   - **Проблема**: Swap может начаться до подтверждения approve
   - **Решение**: Ожидание подтверждения approve

4. **Множественные retry без правильной логики**
   ```python
   # Текущий retry:
   for attempt in range(max_retries):
       # Простое обновление nonce
   ```
   - **Проблема**: Не учитывается состояние сети
   - **Решение**: Умный retry с анализом ошибок

## 🔧 План исправлений

### 1. Создать NonceManager
```python
class NonceManager:
    def __init__(self, web3, account):
        self.web3 = web3
        self.account = account
        self.current_nonce = None
        self.lock = threading.Lock()
    
    def get_next_nonce(self):
        """Получает следующий nonce с блокировкой"""
        with self.lock:
            if self.current_nonce is None:
                self.current_nonce = self.web3.eth.get_transaction_count(self.account.address)
            else:
                self.current_nonce += 1
            return self.current_nonce
    
    def update_nonce(self):
        """Обновляет nonce из сети"""
        with self.lock:
            self.current_nonce = self.web3.eth.get_transaction_count(self.account.address)
```

### 2. Улучшить обработку nonce ошибок
```python
def handle_nonce_error(self, error, transaction):
    """Обработка всех типов nonce ошибок"""
    error_str = str(error).lower()
    
    if "nonce too low" in error_str:
        # Nonce слишком низкий - обновляем
        self.nonce_manager.update_nonce()
        transaction['nonce'] = self.nonce_manager.get_next_nonce()
        return True
        
    elif "nonce too high" in error_str:
        # Nonce слишком высокий - сбрасываем
        self.nonce_manager.reset_nonce()
        transaction['nonce'] = self.nonce_manager.get_next_nonce()
        return True
        
    elif "replacement transaction underpriced" in error_str:
        # Нужно увеличить gas price
        transaction['gasPrice'] = int(transaction['gasPrice'] * 1.1)
        return True
        
    return False
```

### 3. Синхронизация approve и swap
```python
def wait_for_approve_confirmation(self, tx_hash, timeout=60):
    """Ждет подтверждения approve транзакции"""
    try:
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        if receipt and receipt['status'] == 1:
            # Обновляем nonce после подтверждения
            self.nonce_manager.update_nonce()
            return True
        return False
    except Exception as e:
        self.log(f"⚠️ Ошибка ожидания approve: {e}", "WARNING")
        return False
```

### 4. Умный retry механизм
```python
def send_transaction_with_retry(self, transaction, max_retries=3):
    """Отправка транзакции с умным retry"""
    for attempt in range(max_retries):
        try:
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            return tx_hash
            
        except Exception as e:
            if self.handle_nonce_error(e, transaction):
                self.log(f"🔄 Retry {attempt + 1}/{max_retries} после nonce ошибки", "WARNING")
                time.sleep(1)
                continue
            else:
                raise e
```

## 🎯 Приоритеты исправлений

1. **Высокий**: Создать NonceManager
2. **Высокий**: Улучшить обработку nonce ошибок
3. **Средний**: Синхронизация approve и swap
4. **Средний**: Умный retry механизм
5. **Низкий**: Логирование nonce операций

## 📋 Следующие шаги

1. Создать NonceManager класс
2. Интегрировать в автопокупку
3. Улучшить обработку ошибок
4. Протестировать исправления
5. Применить к автопродаже
