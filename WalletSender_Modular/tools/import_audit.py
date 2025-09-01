import ast
import sys
from pathlib import Path
import pkgutil

SRC = Path(__file__).resolve().parents[1] / 'src'
BASE = SRC / 'wallet_sender'

stdlib = set(sys.builtin_module_names)

# crude stdlib list augmentation
for m in ['os','sys','time','json','threading','typing','pathlib','datetime','itertools','functools','subprocess','logging','sqlite3','re','math','random','traceback','csv','collections','dataclasses']:
    stdlib.add(m)

ext = set()
internal = set()
files = list(SRC.rglob('*.py'))
for f in files:
    try:
        tree = ast.parse(f.read_text(encoding='utf-8'), filename=str(f))
    except Exception:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                top = n.name.split('.')[0]
                if top == 'wallet_sender' or (BASE in f.parents):
                    internal.add(top)
                elif top not in stdlib:
                    ext.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            top = node.module.split('.')[0]
            if top == 'wallet_sender' or (BASE in f.parents):
                internal.add(top)
            elif top not in stdlib:
                ext.add(top)

print('External top-level imports (unique):')
for name in sorted(ext):
    print('-', name)
