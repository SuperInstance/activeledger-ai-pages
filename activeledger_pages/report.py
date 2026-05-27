"""FinancialReport — generate balance sheet, income statement, trial balance."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .account import Account, AccountType
from .ledger import Ledger


@dataclass
class BalanceSheet:
    """Snapshot of assets, liabilities, and equity."""

    assets: dict[str, Decimal]
    liabilities: dict[str, Decimal]
    equity: dict[str, Decimal]

    @property
    def total_assets(self) -> Decimal:
        return sum(self.assets.values(), Decimal("0"))

    @property
    def total_liabilities(self) -> Decimal:
        return sum(self.liabilities.values(), Decimal("0"))

    @property
    def total_equity(self) -> Decimal:
        return sum(self.equity.values(), Decimal("0"))

    @property
    def is_balanced(self) -> bool:
        return self.total_assets == self.total_liabilities + self.total_equity

    def to_dict(self) -> dict[str, Any]:
        return {
            "assets": {**self.assets, "__total": str(self.total_assets)},
            "liabilities": {**self.liabilities, "__total": str(self.total_liabilities)},
            "equity": {**self.equity, "__total": str(self.total_equity)},
            "balanced": self.is_balanced,
        }


@dataclass
class IncomeStatement:
    """Revenue and expenses over a period."""

    revenue: dict[str, Decimal]
    expenses: dict[str, Decimal]

    @property
    def total_revenue(self) -> Decimal:
        return sum(self.revenue.values(), Decimal("0"))

    @property
    def total_expenses(self) -> Decimal:
        return sum(self.expenses.values(), Decimal("0"))

    @property
    def net_income(self) -> Decimal:
        return self.total_revenue - self.total_expenses

    def to_dict(self) -> dict[str, Any]:
        return {
            "revenue": {**self.revenue, "__total": str(self.total_revenue)},
            "expenses": {**self.expenses, "__total": str(self.total_expenses)},
            "net_income": str(self.net_income),
        }


class FinancialReport:
    """Generate standard financial reports from a Ledger."""

    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger

    def _account_balances(self, account_type: AccountType) -> dict[str, Decimal]:
        return {a.name: a.balance for a in self.ledger.accounts_by_type(account_type)}

    def trial_balance(self) -> dict[str, dict[str, Decimal]]:
        """Return debit and credit totals per account."""
        result: dict[str, dict[str, Decimal]] = {}
        for name, acct in self.ledger.accounts.items():
            result[name] = {
                "debit": acct.raw_debits,
                "credit": acct.raw_credits,
                "balance": acct.balance,
            }
        return result

    def balance_sheet(self) -> BalanceSheet:
        assets = self._account_balances(AccountType.ASSET)
        liabilities = self._account_balances(AccountType.LIABILITY)
        equity = dict(self._account_balances(AccountType.EQUITY))
        # Include retained earnings (net income) in equity
        inc = self.income_statement()
        if inc.net_income != Decimal("0"):
            equity["Retained Earnings"] = inc.net_income
        return BalanceSheet(assets=assets, liabilities=liabilities, equity=equity)

    def income_statement(self) -> IncomeStatement:
        revenue = self._account_balances(AccountType.REVENUE)
        expenses = self._account_balances(AccountType.EXPENSE)
        return IncomeStatement(revenue=revenue, expenses=expenses)
