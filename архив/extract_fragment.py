import os
os.chdir(r'C:\Users\konfu\Desktop\Sites\Experiment\Experiment1\WalletSender_MCP  копия')

with open('WalletSender.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Записываем интересующий фрагмент
with open('fragment_1522.txt', 'w', encoding='utf-8') as out:
    # Строки 1517-1527 (индексы 1516-1526)
    for i in range(1516, min(1527, len(lines))):
        out.write(f"Line {i+1}: {lines[i]}")

print("Fragment saved to fragment_1522.txt")
