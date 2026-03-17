import ast
from typing import Any, Callable, Dict, List, Optional, Union

from .tools import transfer_funcs
from .visitor import Visitor


class API:
    def __init__(self, source_code: str, firewall_rules: Optional[Dict[str, str]] = None, optimized: bool = True, transfer: Union[str, Callable[..., Any], List[Callable[..., Any]], None] = '') -> None:
        self.source_code = source_code
        self.root = ast.parse(self.source_code)
        self.firewall_rules = firewall_rules or {}
        self.optimized = optimized
        self.transfer = transfer

    def _generate(self) -> Visitor:
        visitor = Visitor(
            self.source_code, self.firewall_rules
        )
        visitor.visit(self.root)
        visitor.souse()
        return visitor

    def generate(self) -> Any:
        visitor = Visitor(
            self.source_code,
            self.firewall_rules,
        )
        visitor.visit(self.root)
        visitor.souse()

        result = visitor.result

        if self.optimized:
            result = visitor.optimize()

        transfer = self.transfer

        if isinstance(transfer, list):
            for func in transfer:
                result = func(result)

            return result

        if transfer is None or isinstance(transfer, str):
            transfer = transfer_funcs(transfer)
            self.transfer = transfer

        if callable(transfer):
            return transfer(result)
        return result
