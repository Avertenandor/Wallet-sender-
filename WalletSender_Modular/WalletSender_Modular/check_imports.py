import os
import sys
import importlib
from pathlib import Path
from typing import Iterator, List, Tuple

ROOT = Path(__file__).parent
SRC = ROOT / 'src'
PKG = SRC / 'wallet_sender'

sys.path.insert(0, str(SRC))

def iter_modules(base: Path, pkg_prefix: str) -> Iterator[str]:
    for path, dirs, files in os.walk(base):
        # skip __pycache__
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
        for f in files:
            if not f.endswith('.py'):
                continue
            if f == '__init__.py':
                # allow package import via directory walk
                pass
            mod_path = Path(path) / f
            rel = mod_path.relative_to(SRC)
            mod_name = rel.with_suffix('').as_posix().replace('/', '.')
            yield mod_name

errors: List[Tuple[str, str]] = []
modules: List[str] = list(iter_modules(PKG, 'wallet_sender'))
print(f'Total python modules found: {len(modules)}')
for name in modules:
    try:
        importlib.import_module(name)
    except Exception as e:
        errors.append((name, repr(e)))

if errors:
    print('Import errors:')
    for name, err in errors:
        print(f' - {name}: {err}')
    sys.exit(1)
else:
    print('All modules imported successfully.')
