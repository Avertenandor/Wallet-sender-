import sys, traceback, importlib
from pathlib import Path

src = (Path(__file__).parent / 'src').resolve()
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
print('Using src:', src)

def safe_import(mod_name: str) -> None:
    print(f'Trying import: {mod_name}')
    try:
        m = importlib.import_module(mod_name)
        mf = str(getattr(m, '__file__', ''))
        print(f'OK: {mod_name} -> {mf}')
    except Exception:
        print(f'FAIL: {mod_name}')
        traceback.print_exc()

safe_import('wallet_sender.ui.tabs.analysis_tab')
safe_import('wallet_sender.ui.main_window')
