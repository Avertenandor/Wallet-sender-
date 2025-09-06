"""
Валидатор и нормализатор адресов для файла 01.09_ГЕНА_50.txt
"""

import sys
from pathlib import Path
from web3 import Web3


def validate_and_normalize_addresses(file_path: str):
    """
    Валидация и нормализация адресов из файла
    
    Args:
        file_path: Путь к файлу с адресами
    """
    print("=" * 60)
    print("ВАЛИДАЦИЯ АДРЕСОВ")
    print("=" * 60)
    
    # Читаем файл
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Файл не найден: {file_path}")
        return
    
    print(f"📂 Файл: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"📊 Прочитано строк: {len(lines)}")
    
    # Обработка адресов
    addresses = []
    invalid = []
    duplicates = []
    seen = set()
    
    for i, line in enumerate(lines, 1):
        addr = line.strip()
        
        # Пропускаем пустые строки
        if not addr:
            continue
        
        # Проверка формата
        if not addr.startswith('0x'):
            invalid.append((i, addr, "Не начинается с 0x"))
            continue
        
        if len(addr) != 42:
            invalid.append((i, addr, f"Неверная длина: {len(addr)} (должно быть 42)"))
            continue
        
        # Проверка валидности через Web3
        if not Web3.is_address(addr):
            invalid.append((i, addr, "Невалидный адрес по Web3"))
            continue
        
        # Нормализация к checksum формату
        normalized = Web3.to_checksum_address(addr)
        
        # Проверка дубликатов
        if normalized.lower() in seen:
            duplicates.append((i, addr, normalized))
        else:
            seen.add(normalized.lower())
            addresses.append(normalized)
    
    # Вывод результатов
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ВАЛИДАЦИИ")
    print("=" * 60)
    
    print(f"✅ Валидных адресов: {len(addresses)}")
    print(f"❌ Невалидных адресов: {len(invalid)}")
    print(f"⚠️  Дубликатов: {len(duplicates)}")
    
    # Детали невалидных адресов
    if invalid:
        print("\n❌ НЕВАЛИДНЫЕ АДРЕСА:")
        for line_num, addr, reason in invalid[:10]:  # Показываем первые 10
            print(f"  Строка {line_num}: {addr[:20]}... - {reason}")
        if len(invalid) > 10:
            print(f"  ... и еще {len(invalid) - 10} адресов")
    
    # Детали дубликатов
    if duplicates:
        print("\n⚠️  ДУБЛИКАТЫ:")
        for line_num, addr, normalized in duplicates[:10]:
            print(f"  Строка {line_num}: {addr[:10]}... → {normalized[:10]}...")
        if len(duplicates) > 10:
            print(f"  ... и еще {len(duplicates) - 10} дубликатов")
    
    # Проверка на известные контракты
    known_contracts = {
        '0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1': 'PLEX ONE Token',
        '0x55d398326f99059ff775485246999027b3197955': 'USDT Token',
        '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d': 'USDC Token',
        '0xe9e7cea3dedca5984780bafc599bd69add087d56': 'BUSD Token',
        '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c': 'WBNB Token',
        '0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82': 'CAKE Token',
        '0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c': 'BTCB Token',
        '0x2170Ed0880ac9A755fd29B2688956BD959F933F8': 'ETH Token'
    }
    
    found_contracts = []
    for addr in addresses:
        if addr.lower() in known_contracts:
            found_contracts.append((addr, known_contracts[addr.lower()]))
    
    if found_contracts:
        print("\n⚠️  ОБНАРУЖЕНЫ КОНТРАКТЫ ТОКЕНОВ:")
        for addr, name in found_contracts:
            print(f"  {addr[:10]}... - {name}")
        print("  Эти адреса являются контрактами токенов, а не кошельками!")
    
    # Сохранение нормализованных адресов
    if addresses:
        output_file = path.parent / f"{path.stem}_normalized.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            for addr in addresses:
                f.write(addr + '\n')
        
        print(f"\n✅ Нормализованные адреса сохранены в:")
        print(f"   {output_file}")
        
        # Создание файла только с уникальными EOA (не контракты)
        eoa_addresses = [addr for addr in addresses 
                        if addr.lower() not in known_contracts]
        
        if eoa_addresses:
            eoa_file = path.parent / f"{path.stem}_eoa_only.txt"
            with open(eoa_file, 'w', encoding='utf-8') as f:
                for addr in eoa_addresses:
                    f.write(addr + '\n')
            
            print(f"\n✅ EOA адреса (без контрактов) сохранены в:")
            print(f"   {eoa_file}")
            print(f"   Количество: {len(eoa_addresses)}")
    
    print("\n" + "=" * 60)
    print("РЕКОМЕНДАЦИИ")
    print("=" * 60)
    
    if found_contracts:
        print("⚠️  Удалите адреса контрактов токенов из списка рассылки")
    
    if duplicates:
        print("⚠️  Используйте нормализованный файл без дубликатов")
    
    if not invalid and not duplicates and not found_contracts:
        print("✅ Все адреса валидны и готовы к использованию!")
    
    return {
        'total': len(lines),
        'valid': len(addresses),
        'invalid': len(invalid),
        'duplicates': len(duplicates),
        'contracts': len(found_contracts),
        'eoa': len(addresses) - len(found_contracts)
    }


if __name__ == "__main__":
    # Путь к файлу
    file_path = "01.09_ГЕНА_50.txt"
    
    # Запуск валидации
    stats = validate_and_normalize_addresses(file_path)
    
    if stats:
        print("\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"   Всего строк: {stats['total']}")
        print(f"   Валидных адресов: {stats['valid']}")
        print(f"   Невалидных: {stats['invalid']}")
        print(f"   Дубликатов: {stats['duplicates']}")
        print(f"   Контрактов: {stats['contracts']}")
        print(f"   EOA кошельков: {stats['eoa']}")
