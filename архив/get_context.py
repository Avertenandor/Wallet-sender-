with open('WalletSender.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Показываем строки 2155-2175
with open('context_2164.txt', 'w', encoding='utf-8') as out:
    for i in range(2154, min(2175, len(lines))):
        out.write(f"{i+1}: {lines[i]}")

print("Context saved")
