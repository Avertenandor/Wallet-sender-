"""
Диагностический патч для AutoSalesTab
Применяет трассировку ко всем методам для поиска точки краша
"""

def apply_diagnostics_to_auto_sales():
    """Применение диагностики к AutoSalesTab"""
    try:
        from wallet_sender.ui.tabs.auto_sales_tab import AutoSalesTab, AutoSalesWorker
        from wallet_sender.utils.crash_diagnostics import trace_execution, trace_qt_operation
        
        print("[CONFIG] Применение диагностики к AutoSalesTab...")
        
        # Патчим методы AutoSalesTab
        methods_to_trace = [
            'init_ui',
            'start_auto_sales', 
            'stop_auto_sales',
            'on_sale_completed',
            'on_sale_error',
            'update_ui_state',
            'validate_inputs'
        ]
        
        for method_name in methods_to_trace:
            if hasattr(AutoSalesTab, method_name):
                original = getattr(AutoSalesTab, method_name)
                # UI методы оборачиваем в trace_qt_operation
                if method_name in ['init_ui', 'update_ui_state', 'on_sale_completed', 'on_sale_error']:
                    setattr(AutoSalesTab, method_name, trace_qt_operation(original))
                else:
                    setattr(AutoSalesTab, method_name, trace_execution(original))
                print(f"  [OK] Патч применен к AutoSalesTab.{method_name}")
        
        # Патчим методы AutoSalesWorker
        worker_methods = [
            '__init__',
            'run',
            'execute_sale',
            'check_balance',
            'calculate_amounts',
            'send_transaction'
        ]
        
        for method_name in worker_methods:
            if hasattr(AutoSalesWorker, method_name):
                original = getattr(AutoSalesWorker, method_name)
                setattr(AutoSalesWorker, method_name, trace_execution(original))
                print(f"  [OK] Патч применен к AutoSalesWorker.{method_name}")
        
        # Патчим DexSwapService
        from wallet_sender.services.dex_swap_service import DexSwapService
        
        swap_methods = [
            '__init__',
            '_reserve_nonce',
            '_sync_nonce_with_network',
            '_build_and_send',
            'swap_exact_tokens_for_tokens',
            'swap_exact_tokens_for_eth',
            'wait_receipt'
        ]
        
        for method_name in swap_methods:
            if hasattr(DexSwapService, method_name):
                original = getattr(DexSwapService, method_name)
                setattr(DexSwapService, method_name, trace_execution(original))
                print(f"  [OK] Патч применен к DexSwapService.{method_name}")
        
        print("[OK] Диагностика применена!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка применения диагностики: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    apply_diagnostics_to_auto_sales()
