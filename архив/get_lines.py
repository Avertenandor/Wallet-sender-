with open('WalletSender.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Извлекаем строки вокруг 1522
target = []
for i in range(1517, min(1527, len(lines))):
    target.append(f"{i}: {lines[i-1]}")

with open('target_lines.txt', 'w', encoding='utf-8') as f:
    f.write(''.join(target))
