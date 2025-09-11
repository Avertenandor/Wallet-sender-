"""
Валидация и подготовка адресов для рассылки
"""

from web3 import Web3
from typing import List, Set, Tuple
import sys
from pathlib import Path

def validate_and_prepare_addresses(file_path: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Валидация и подготовка адресов из файла
    
    Returns:
        Tuple[valid_addresses, invalid_addresses, duplicates]
    """
    valid_addresses = []
    invalid_addresses = []
    duplicates = []
    seen = set()
    
    # Читаем файл
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"[ERROR] Файл не найден: {file_path}")
        return [], [], []
    
    print(f"[INFO] Прочитано {len(lines)} строк из файла")
    
    # Обрабатываем каждую строку
    for i, line in enumerate(lines, 1):
        address = line.strip()
        
        # Пропускаем пустые строки
        if not address:
            continue
        
        # Проверяем валидность адреса
        if not Web3.is_address(address):
            invalid_addresses.append(f"Строка {i}: {address}")
            continue
        
        # Нормализуем адрес (checksum)
        try:
            checksum_address = Web3.to_checksum_address(address)
        except Exception as e:
            invalid_addresses.append(f"Строка {i}: {address} - {e}")
            continue
        
        # Проверяем на дубликаты
        if checksum_address.lower() in seen:
            duplicates.append(f"Строка {i}: {checksum_address}")
        else:
            seen.add(checksum_address.lower())
            valid_addresses.append(checksum_address)
    
    return valid_addresses, invalid_addresses, duplicates


def save_cleaned_addresses(addresses: List[str], output_file: str):
    """Сохранение очищенных адресов в файл"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for addr in addresses:
            f.write(f"{addr}\n")
    print(f"[OK] Сохранено {len(addresses)} адресов в {output_file}")


def check_special_addresses(addresses: List[str]):
    """Проверка на известные адреса (токены, биржи и т.д.)"""
    known_addresses = {
        '0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1': 'PLEX ONE Token',
        '0x55d398326f99059ff775485246999027b3197955': 'USDT Token',
        '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d': 'USDC Token',
        '0xe9e7cea3dedca5984780bafc599bd69add087d56': 'BUSD Token',
        '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c': 'WBNB Token',
        '0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82': 'CAKE Token',
        '0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c': 'BTCB Token',
        '0x2170Ed0880ac9A755fd29B2688956BD959F933F8': 'ETH Token',
        '0xF977814e90dA44bFA03b6295A0616a897441aceC': 'Binance Hot Wallet',
        '0x2FAF487A4414Fe77e2327F0bf4AE2a264a776AD2': 'FTX Exchange',
    }
    
    warnings = []
    for addr in addresses:
        lower_addr = addr.lower()
        for known_addr, description in known_addresses.items():
            if lower_addr == known_addr.lower():
                warnings.append(f"[WARN] {addr} - это {description}")
    
    return warnings


def main():
    """Главная функция"""
    print("=" * 60)
    print("[SEARCH] Валидация адресов для рассылки")
    print("=" * 60)
    
    # Путь к файлу
    input_file = "01.09_ГЕНА_50.txt"
    output_file = "01.09_ГЕНА_50_validated.txt"
    
    # Валидация адресов
    valid, invalid, duplicates = validate_and_prepare_addresses(input_file)
    
    print(f"\n[STATS] Результаты валидации:")
    print(f"[OK] Валидных адресов: {len(valid)}")
    print(f"[ERROR] Невалидных адресов: {len(invalid)}")
    print(f"🔄 Дубликатов: {len(duplicates)}")
    
    # Показываем невалидные адреса
    if invalid:
        print("\n[ERROR] Невалидные адреса:")
        for addr in invalid:
            print(f"  - {addr}")
    
    # Показываем дубликаты
    if duplicates:
        print("\n🔄 Дубликаты:")
        for addr in duplicates:
            print(f"  - {addr}")
    
    # Проверяем на известные адреса
    warnings = check_special_addresses(valid)
    if warnings:
        print("\n[WARN] ВНИМАНИЕ! Обнаружены системные адреса:")
        for warning in warnings:
            print(f"  {warning}")
        print("\n❗ Рекомендуется исключить токены и адреса бирж из рассылки!")
        
        # Фильтруем системные адреса
        system_addresses = {
            '0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1',  # PLEX
            '0x55d398326f99059ff775485246999027b3197955',  # USDT
            '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d',  # USDC
            '0xe9e7cea3dedca5984780bafc599bd69add087d56',  # BUSD
            '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',  # WBNB
            '0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82',  # CAKE
            '0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c',  # BTCB
            '0x2170Ed0880ac9A755fd29B2688956BD959F933F8',  # ETH
            '0xF977814e90dA44bFA03b6295A0616a897441aceC',  # Binance
            '0x2FAF487A4414Fe77e2327F0bf4AE2a264a776AD2',  # FTX
        }
        
        # Фильтруем EOA (externally owned accounts) адреса
        eoa_addresses = [
            addr for addr in valid 
            if addr.lower() not in [s.lower() for s in system_addresses]
        ]
        
        print(f"\n[INFO] После фильтрации системных адресов: {len(eoa_addresses)} адресов")
        
        # Сохраняем только EOA адреса
        eoa_output = "01.09_ГЕНА_50_eoa_only.txt"
        save_cleaned_addresses(eoa_addresses, eoa_output)
    else:
        # Сохраняем все валидные адреса
        if valid:
            save_cleaned_addresses(valid, output_file)
    
    print("\n[OK] Валидация завершена!")
    
    # Показываем итоговую статистику
    if valid:
        print(f"\n[STATS] Итоговая статистика:")
        print(f"  • Всего валидных: {len(valid)}")
        print(f"  • Уникальных: {len(set(addr.lower() for addr in valid))}")
        print(f"  • Готово к рассылке: {len(valid) - len(warnings)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
