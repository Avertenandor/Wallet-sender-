# Временный скрипт для очистки файла

with open("WalletSender.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Находим строку с sys.exit и обрезаем всё после неё
new_lines = []
for line in lines:
    new_lines.append(line)
    if "sys.exit(app.exec_())" in line:
        break

# Записываем обратно
with open("WalletSender.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"Файл обрезан. Оставлено {len(new_lines)} строк.")
