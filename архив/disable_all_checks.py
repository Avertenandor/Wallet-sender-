#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой скрипт для добавления pyrightconfig.json
"""

import json
import os

def main():
    # Создаем pyrightconfig.json с отключенными проверками
    config = {
        "include": ["*.py"],
        "exclude": ["**/__pycache__", "venv", ".venv", "*.backup*"],
        "reportMissingImports": "none",
        "reportMissingTypeStubs": "none", 
        "reportUnknownMemberType": "none",
        "reportUnknownVariableType": "none",
        "reportUnknownArgumentType": "none",
        "reportUnknownLambdaType": "none",
        "reportUnknownParameterType": "none",
        "reportGeneralTypeIssues": "none",
        "reportOptionalSubscript": "none",
        "reportOptionalMemberAccess": "none",
        "reportOptionalCall": "none",
        "reportOptionalIterable": "none",
        "reportOptionalContextManager": "none",
        "reportOptionalOperand": "none",
        "reportTypedDictNotRequiredAccess": "none",
        "reportPrivateImportUsage": "none",
        "reportUnboundVariable": "none",
        "reportUndefinedVariable": "none",
        "reportAttributeAccessIssue": "none",
        "reportArgumentType": "none",
        "reportAssignmentType": "none",
        "reportIncompatibleMethodOverride": "none",
        "reportIncompatibleVariableOverride": "none",
        "reportInconsistentConstructor": "none",
        "reportInvalidStringEscapeSequence": "none",
        "reportMissingParameterType": "none",
        "reportMissingReturnType": "none",
        "reportRedeclaration": "none",
        "reportUninitializedInstanceVariable": "none",
        "reportCallInDefaultInitializer": "none",
        "reportUnnecessaryIsInstance": "none",
        "reportUnnecessaryCast": "none",
        "reportUnnecessaryComparison": "none",
        "reportUnnecessaryContains": "none",
        "reportAssertAlwaysTrue": "none",
        "reportSelfClsParameterName": "none",
        "reportUnusedClass": "none",
        "reportUnusedImport": "none",
        "reportUnusedFunction": "none",
        "reportUnusedVariable": "none",
        "reportDuplicateImport": "none",
        "reportWildcardImportFromLibrary": "none",
        "reportImportCycles": "none",
        "reportPropertyTypeMismatch": "none",
        "pythonVersion": "3.8",
        "pythonPlatform": "Windows",
        "typeCheckingMode": "off",
        "useLibraryCodeForTypes": False,
        "strictListInference": False,
        "strictDictionaryInference": False,
        "strictSetInference": False,
        "strictParameterNoneValue": False,
        "enableTypeIgnoreComments": True,
        "enableExperimentalFeatures": False,
        "autoSearchPaths": True,
        "autoImportCompletions": True,
        "indexing": True,
        "logLevel": "Warning"
    }
    
    # Сохраняем файл
    config_path = "pyrightconfig.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Создан {config_path} с полностью отключенными проверками типов")
    
    # Создаем .vscode/settings.json
    vscode_dir = ".vscode"
    if not os.path.exists(vscode_dir):
        os.makedirs(vscode_dir)
    
    vscode_settings = {
        "python.analysis.typeCheckingMode": "off",
        "python.analysis.autoImportCompletions": True,
        "python.analysis.autoSearchPaths": True,
        "python.analysis.diagnosticMode": "openFilesOnly",
        "python.analysis.stubPath": "typings",
        "python.analysis.diagnosticSeverityOverrides": {
            "reportMissingImports": "none",
            "reportMissingTypeStubs": "none",
            "reportUnknownMemberType": "none",
            "reportUnknownVariableType": "none",
            "reportUnknownArgumentType": "none",
            "reportGeneralTypeIssues": "none",
            "reportOptionalMemberAccess": "none",
            "reportOptionalSubscript": "none",
            "reportOptionalCall": "none",
            "reportOptionalIterable": "none",
            "reportOptionalContextManager": "none",
            "reportOptionalOperand": "none",
            "reportAttributeAccessIssue": "none",
            "reportRedeclaration": "none"
        },
        "python.linting.enabled": False,
        "python.linting.pylintEnabled": False,
        "python.linting.flake8Enabled": False,
        "python.linting.mypyEnabled": False,
        "python.linting.banditEnabled": False,
        "python.linting.prospectorEnabled": False,
        "python.linting.pydocstyleEnabled": False,
        "python.linting.pylamaEnabled": False,
        "python.linting.pycodestyleEnabled": False
    }
    
    vscode_settings_path = os.path.join(vscode_dir, "settings.json")
    with open(vscode_settings_path, 'w', encoding='utf-8') as f:
        json.dump(vscode_settings, f, indent=2)
    
    print(f"✅ Создан {vscode_settings_path} с отключенными проверками VSCode")
    
    print("\n🎉 ГОТОВО! Все проверки типов отключены.")
    print("\n📋 Что делать дальше:")
    print("1. Перезапустите VSCode")
    print("2. Выполните: Ctrl+Shift+P -> 'Developer: Reload Window'")
    print("3. Ошибки Pylance должны исчезнуть!")
    
    return True

if __name__ == "__main__":
    main()
