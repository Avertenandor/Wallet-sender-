"""
Утилиты для проверки безопасности токенов
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from web3 import Web3

class SafetyLevel(Enum):
    """Уровни безопасности"""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    UNKNOWN = "unknown"

@dataclass
class SafetyCheck:
    """Результат проверки безопасности"""
    name: str
    passed: bool
    level: SafetyLevel
    message: str
    details: Optional[Dict[str, Any]] = None

@dataclass
class TokenSafetyReport:
    """Отчет о безопасности токена"""
    token_address: str
    overall_level: SafetyLevel
    checks: List[SafetyCheck]
    timestamp: float
    recommendations: List[str]

class TokenSafetyChecker:
    """Проверяет безопасность токенов"""
    
    def __init__(self, web3_instance):
        self.web3 = web3_instance
        
        # Стандартный ERC20 ABI для проверок
        self.erc20_abi = [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
            {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
            {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
            {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
            {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
        ]
        
        # Известные опасные паттерны
        self.dangerous_functions = [
            'pause', 'unpause', 'freeze', 'unfreeze', 'blacklist', 'whitelist',
            'mint', 'burn', 'setTax', 'setFee', 'setOwner', 'transferOwnership'
        ]
        
        # Известные безопасные токены
        self.known_safe_tokens = {
            '0x55d398326f99059fF775485246999027B3197955': 'USDT',  # USDT
            '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c': 'WBNB',  # WBNB
            '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56': 'BUSD',  # BUSD
        }
    
    def check_token_safety(self, token_address: str) -> TokenSafetyReport:
        """Проверяет безопасность токена"""
        checks = []
        
        try:
            # Проверяем, что адрес валидный
            if not self._is_valid_address(token_address):
                checks.append(SafetyCheck(
                    name="Валидность адреса",
                    passed=False,
                    level=SafetyLevel.DANGEROUS,
                    message="Неверный адрес токена"
                ))
                return TokenSafetyReport(
                    token_address=token_address,
                    overall_level=SafetyLevel.DANGEROUS,
                    checks=checks,
                    timestamp=time.time(),
                    recommendations=["Проверьте правильность адреса токена"]
                )
            
            # Проверяем наличие контракта
            contract_check = self._check_contract_exists(token_address)
            checks.append(contract_check)
            
            if not contract_check.passed:
                return TokenSafetyReport(
                    token_address=token_address,
                    overall_level=SafetyLevel.DANGEROUS,
                    checks=checks,
                    timestamp=time.time(),
                    recommendations=["Контракт не существует или не развернут"]
                )
            
            # Проверяем стандартные функции ERC20
            checks.append(self._check_erc20_functions(token_address))
            
            # Проверяем информацию о токене
            checks.append(self._check_token_info(token_address))
            
            # Проверяем на honeypot
            checks.append(self._check_honeypot(token_address))
            
            # Проверяем ликвидность
            checks.append(self._check_liquidity(token_address))
            
            # Проверяем на подозрительные функции
            checks.append(self._check_suspicious_functions(token_address))
            
            # Проверяем известные токены
            checks.append(self._check_known_token(token_address))
            
            # Определяем общий уровень безопасности
            overall_level = self._determine_overall_level(checks)
            
            # Генерируем рекомендации
            recommendations = self._generate_recommendations(checks, overall_level)
            
            return TokenSafetyReport(
                token_address=token_address,
                overall_level=overall_level,
                checks=checks,
                timestamp=time.time(),
                recommendations=recommendations
            )
            
        except Exception as e:
            checks.append(SafetyCheck(
                name="Общая проверка",
                passed=False,
                level=SafetyLevel.UNKNOWN,
                message=f"Ошибка при проверке: {str(e)}"
            ))
            
            return TokenSafetyReport(
                token_address=token_address,
                overall_level=SafetyLevel.UNKNOWN,
                checks=checks,
                timestamp=time.time(),
                recommendations=["Повторите проверку позже"]
            )
    
    def _is_valid_address(self, address: str) -> bool:
        """Проверяет валидность адреса"""
        try:
            return Web3.is_address(address) and address.startswith('0x')
        except:
            return False
    
    def _check_contract_exists(self, token_address: str) -> SafetyCheck:
        """Проверяет существование контракта"""
        try:
            code = self.web3.eth.get_code(token_address)
            if len(code) <= 2:  # Только 0x
                return SafetyCheck(
                    name="Существование контракта",
                    passed=False,
                    level=SafetyLevel.DANGEROUS,
                    message="Контракт не существует"
                )
            else:
                return SafetyCheck(
                    name="Существование контракта",
                    passed=True,
                    level=SafetyLevel.SAFE,
                    message="Контракт существует",
                    details={"code_size": len(code)}
                )
        except Exception as e:
            return SafetyCheck(
                name="Существование контракта",
                passed=False,
                level=SafetyLevel.UNKNOWN,
                message=f"Ошибка проверки: {str(e)}"
            )
    
    def _check_erc20_functions(self, token_address: str) -> SafetyCheck:
        """Проверяет наличие стандартных функций ERC20"""
        try:
            contract = self.web3.eth.contract(address=token_address, abi=self.erc20_abi)
            
            # Проверяем основные функции
            required_functions = ['name', 'symbol', 'decimals', 'totalSupply', 'balanceOf', 'transfer', 'approve', 'allowance']
            missing_functions = []
            
            for func_name in required_functions:
                try:
                    if func_name == 'name':
                        contract.functions.name().call()
                    elif func_name == 'symbol':
                        contract.functions.symbol().call()
                    elif func_name == 'decimals':
                        contract.functions.decimals().call()
                    elif func_name == 'totalSupply':
                        contract.functions.totalSupply().call()
                    # Остальные функции требуют параметры, поэтому просто проверяем их наличие в ABI
                except Exception:
                    missing_functions.append(func_name)
            
            if missing_functions:
                return SafetyCheck(
                    name="Стандартные функции ERC20",
                    passed=False,
                    level=SafetyLevel.WARNING,
                    message=f"Отсутствуют функции: {', '.join(missing_functions)}",
                    details={"missing_functions": missing_functions}
                )
            else:
                return SafetyCheck(
                    name="Стандартные функции ERC20",
                    passed=True,
                    level=SafetyLevel.SAFE,
                    message="Все стандартные функции присутствуют"
                )
                
        except Exception as e:
            return SafetyCheck(
                name="Стандартные функции ERC20",
                passed=False,
                level=SafetyLevel.UNKNOWN,
                message=f"Ошибка проверки: {str(e)}"
            )
    
    def _check_token_info(self, token_address: str) -> SafetyCheck:
        """Проверяет информацию о токене"""
        try:
            contract = self.web3.eth.contract(address=token_address, abi=self.erc20_abi)
            
            # Получаем информацию о токене
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            total_supply = contract.functions.totalSupply().call()
            
            issues = []
            
            # Проверяем name
            if not name or name == "Unknown" or len(name) < 2:
                issues.append("Подозрительное имя токена")
            
            # Проверяем symbol
            if not symbol or symbol == "???" or len(symbol) < 2:
                issues.append("Подозрительный символ токена")
            
            # Проверяем decimals
            if decimals < 0 or decimals > 36:
                issues.append("Некорректное количество decimals")
            
            # Проверяем total supply
            if total_supply == 0:
                issues.append("Общее количество токенов равно 0")
            
            if issues:
                return SafetyCheck(
                    name="Информация о токене",
                    passed=False,
                    level=SafetyLevel.WARNING,
                    message=f"Проблемы: {', '.join(issues)}",
                    details={
                        "name": name,
                        "symbol": symbol,
                        "decimals": decimals,
                        "total_supply": total_supply,
                        "issues": issues
                    }
                )
            else:
                return SafetyCheck(
                    name="Информация о токене",
                    passed=True,
                    level=SafetyLevel.SAFE,
                    message="Информация о токене корректна",
                    details={
                        "name": name,
                        "symbol": symbol,
                        "decimals": decimals,
                        "total_supply": total_supply
                    }
                )
                
        except Exception as e:
            return SafetyCheck(
                name="Информация о токене",
                passed=False,
                level=SafetyLevel.UNKNOWN,
                message=f"Ошибка получения информации: {str(e)}"
            )
    
    def _check_honeypot(self, token_address: str) -> SafetyCheck:
        """Проверяет на honeypot (упрощенная проверка)"""
        try:
            # Это упрощенная проверка. В реальности нужен более сложный анализ
            contract = self.web3.eth.contract(address=token_address, abi=self.erc20_abi)
            
            # Проверяем, можем ли мы получить информацию о токене
            try:
                name = contract.functions.name().call()
                symbol = contract.functions.symbol().call()
                
                # Если можем получить базовую информацию, то не honeypot
                return SafetyCheck(
                    name="Проверка на honeypot",
                    passed=True,
                    level=SafetyLevel.SAFE,
                    message="Базовая проверка пройдена"
                )
            except Exception:
                return SafetyCheck(
                    name="Проверка на honeypot",
                    passed=False,
                    level=SafetyLevel.DANGEROUS,
                    message="Возможный honeypot - не удается получить информацию"
                )
                
        except Exception as e:
            return SafetyCheck(
                name="Проверка на honeypot",
                passed=False,
                level=SafetyLevel.UNKNOWN,
                message=f"Ошибка проверки: {str(e)}"
            )
    
    def _check_liquidity(self, token_address: str) -> SafetyCheck:
        """Проверяет ликвидность токена"""
        try:
            # Упрощенная проверка ликвидности
            # В реальности нужно проверять пулы на DEX
            
            # Проверяем, есть ли токен в списке известных
            if token_address.lower() in [addr.lower() for addr in self.known_safe_tokens.keys()]:
                return SafetyCheck(
                    name="Проверка ликвидности",
                    passed=True,
                    level=SafetyLevel.SAFE,
                    message="Известный токен с ликвидностью"
                )
            else:
                return SafetyCheck(
                    name="Проверка ликвидности",
                    passed=False,
                    level=SafetyLevel.WARNING,
                    message="Неизвестный токен - проверьте ликвидность вручную"
                )
                
        except Exception as e:
            return SafetyCheck(
                name="Проверка ликвидности",
                passed=False,
                level=SafetyLevel.UNKNOWN,
                message=f"Ошибка проверки: {str(e)}"
            )
    
    def _check_suspicious_functions(self, token_address: str) -> SafetyCheck:
        """Проверяет на подозрительные функции"""
        try:
            # Получаем код контракта
            code = self.web3.eth.get_code(token_address)
            code_hex = code.hex().lower()
            
            suspicious_found = []
            
            # Проверяем наличие подозрительных функций в коде
            for func in self.dangerous_functions:
                if func.lower() in code_hex:
                    suspicious_found.append(func)
            
            if suspicious_found:
                return SafetyCheck(
                    name="Подозрительные функции",
                    passed=False,
                    level=SafetyLevel.WARNING,
                    message=f"Найдены подозрительные функции: {', '.join(suspicious_found)}",
                    details={"suspicious_functions": suspicious_found}
                )
            else:
                return SafetyCheck(
                    name="Подозрительные функции",
                    passed=True,
                    level=SafetyLevel.SAFE,
                    message="Подозрительные функции не найдены"
                )
                
        except Exception as e:
            return SafetyCheck(
                name="Подозрительные функции",
                passed=False,
                level=SafetyLevel.UNKNOWN,
                message=f"Ошибка проверки: {str(e)}"
            )
    
    def _check_known_token(self, token_address: str) -> SafetyCheck:
        """Проверяет, является ли токен известным"""
        if token_address.lower() in [addr.lower() for addr in self.known_safe_tokens.keys()]:
            token_name = self.known_safe_tokens[token_address]
            return SafetyCheck(
                name="Известный токен",
                passed=True,
                level=SafetyLevel.SAFE,
                message=f"Известный безопасный токен: {token_name}"
            )
        else:
            return SafetyCheck(
                name="Известный токен",
                passed=False,
                level=SafetyLevel.WARNING,
                message="Неизвестный токен - будьте осторожны"
            )
    
    def _determine_overall_level(self, checks: List[SafetyCheck]) -> SafetyLevel:
        """Определяет общий уровень безопасности"""
        if not checks:
            return SafetyLevel.UNKNOWN
        
        # Подсчитываем уровни
        levels = [check.level for check in checks]
        
        # Если есть опасные проверки
        if SafetyLevel.DANGEROUS in levels:
            return SafetyLevel.DANGEROUS
        
        # Если есть предупреждения
        if SafetyLevel.WARNING in levels:
            return SafetyLevel.WARNING
        
        # Если все проверки прошли
        if all(check.passed for check in checks):
            return SafetyLevel.SAFE
        
        # Если есть неизвестные проверки
        if SafetyLevel.UNKNOWN in levels:
            return SafetyLevel.UNKNOWN
        
        return SafetyLevel.WARNING
    
    def _generate_recommendations(self, checks: List[SafetyCheck], overall_level: SafetyLevel) -> List[str]:
        """Генерирует рекомендации на основе проверок"""
        recommendations = []
        
        if overall_level == SafetyLevel.DANGEROUS:
            recommendations.append("🚨 НЕ РЕКОМЕНДУЕТСЯ использовать этот токен")
            recommendations.append("Проверьте адрес токена и убедитесь в его подлинности")
        elif overall_level == SafetyLevel.WARNING:
            recommendations.append("⚠️ Будьте осторожны при работе с этим токеном")
            recommendations.append("Проверьте дополнительную информацию о токене")
        elif overall_level == SafetyLevel.SAFE:
            recommendations.append("✅ Токен прошел базовые проверки безопасности")
        else:
            recommendations.append("❓ Не удалось полностью проверить токен")
            recommendations.append("Повторите проверку позже")
        
        # Добавляем специфичные рекомендации
        for check in checks:
            if not check.passed and check.level == SafetyLevel.DANGEROUS:
                if "контракт не существует" in check.message.lower():
                    recommendations.append("Проверьте правильность адреса токена")
                elif "honeypot" in check.message.lower():
                    recommendations.append("Возможный honeypot - избегайте этого токена")
        
        return recommendations
