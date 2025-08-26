#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('WalletSender.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

results = []
results.append(f"Total lines: {len(lines)}")
results.append("")
results.append("Lines 1517-1527:")
results.append("-" * 50)

for i in range(1516, min(1527, len(lines))):
    line_num = i + 1
    line = lines[i].rstrip()
    marker = ">>>" if line_num == 1522 else "   "
    results.append(f"{marker} {line_num}: {line}")

results.append("")
results.append("All setSectionResizeMode calls:")
results.append("-" * 50)

count = 0
for i, line in enumerate(lines):
    if "setSectionResizeMode" in line:
        count += 1
        results.append(f"Line {i+1}: {line.strip()}")

results.append(f"\nTotal setSectionResizeMode calls: {count}")

# Save results
with open('analysis_result.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print("Done")
