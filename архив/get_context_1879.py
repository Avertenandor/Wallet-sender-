with open('WalletSender.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Показываем строки 1874-1884
with open('context_1879.txt', 'w', encoding='utf-8') as out:
    for i in range(1873, min(1884, len(lines))):
        out.write(f"{i+1}: {lines[i]}")

print("Context saved to context_1879.txt")
