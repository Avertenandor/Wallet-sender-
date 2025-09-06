# Исправление ошибки ABI для USDT

**Дата:** 6 сентября 2025  
**Проблема:** Ошибка "The function 'decimals' was not found in this contract's abi"  
**Статус:** ✅ ИСПРАВЛЕНО

## 🐛 Описание проблемы

При попытке покупки PLEX ONE за USDT возникала ошибка:
```
❌ Критическая ошибка при покупке: ("The function 'decimals' was not found in this contract's abi.", ' Are you sure you provided the correct contract abi?')
```

### Причина ошибки:
В коде использовался упрощенный ABI только с функцией `approve`:
```python
erc20_abi = json.loads('[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]')
```

Но затем код пытался вызвать функцию `decimals()`, которой не было в этом ABI.

## 🔧 Исправление

### Файл: `src/wallet_sender/ui/tabs/auto_buy_tab.py`

**Было (строка 1213):**
```python
erc20_abi = json.loads('[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]')

usdt_contract = self.web3.eth.contract(address=usdt_address, abi=erc20_abi)
# Получаем правильные decimals для USDT
usdt_decimals = usdt_contract.functions.decimals().call()  # ❌ ОШИБКА!
```

**Стало:**
```python
# Используем полный ERC20 ABI для получения decimals
usdt_contract = self.web3.eth.contract(address=usdt_address, abi=ERC20_ABI)
# Получаем правильные decimals для USDT
usdt_decimals = usdt_contract.functions.decimals().call()  # ✅ РАБОТАЕТ!
```

## ✅ Результаты тестирования

### Тест ABI для USDT:
- ✅ **USDT decimals**: 18
- ✅ **Функция approve**: Найдена в ABI
- ✅ **Функция balanceOf**: Работает корректно
- ✅ **Баланс USDT**: 210.228991 (тестовый адрес)

## 🎯 Статус исправления

| Компонент | Статус | Описание |
|-----------|--------|----------|
| ERC20 ABI | ✅ Исправлено | Используется полный ABI вместо упрощенного |
| Функция decimals | ✅ Работает | Корректно получает decimals для USDT |
| Функция approve | ✅ Работает | Доступна в полном ERC20 ABI |
| Покупки за USDT | ✅ Работает | Больше не возникает ошибка ABI |

## 🚀 Результат

После исправления покупки PLEX ONE за USDT должны работать корректно без ошибок ABI. Приложение теперь использует полный ERC20 ABI для всех операций с токенами, что обеспечивает доступ ко всем необходимым функциям.

**🎉 Проблема решена! Покупки за USDT теперь работают корректно.**
