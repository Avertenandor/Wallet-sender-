import re

with open("WalletSender.py", 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# Поиск всех определений методов с _mass_
pattern = r'^\s*def (_mass_\w+)\('
results = []

for i, line in enumerate(lines, 1):
    match = re.match(pattern, line)
    if match:
        results.append(f"Line {i}: {match.group(1)}")

# Запись результатов
with open("found_methods.txt", 'w') as f:
    f.write('\n'.join(results))

print(f"Found {len(results)} _mass_ methods")
