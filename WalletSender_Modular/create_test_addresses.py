"""
Создание тестового файла с адресами для импорта
"""

addresses = [
    "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
    "0x5aAeb6053f3E94C9b9A09f33669435E7Ef1BeAed",
    "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
    "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB",
    "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb",
    "0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
    "0xF977814e90dA44bFA03b6295A0616a897441aceC",
    "0x2FAF487A4414Fe77e2327F0bf4AE2a264a776AD2",
    "0x267be6C49b78fCBa8Fd3D9b2E10De9e70c72a4cD",
    "0x6f46CF5569AEfA1acC1009290c8E043747172d89"
]

# Сохраняем в CSV
with open("test_addresses.csv", "w") as f:
    f.write("Address,Amount\n")
    for addr in addresses:
        f.write(f"{addr},10\n")

print(f"Создан файл test_addresses.csv с {len(addresses)} адресами")
