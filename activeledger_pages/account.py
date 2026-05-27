"""Account types and Account dataclass."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


class AccountType(enum.Enum):
    """Standard accounting account types."""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


# Normal balance: debit-increasing or credit-increasing
_DEBIT_NORMAL: set[AccountType] = {AccountType.ASSET, AccountType.EXPENSE}
_CREDIT_NORMAL: set[AccountType] = {AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE}


@dataclass
class Account:
    """A single ledger account with balance tracking."""

    name: str
    account_type: AccountType
    code: Optional[str] = None
    description: str = ""
    _balance: Decimal = field(default_factory=lambda: Decimal("0"), repr=False)
    _debit_total: Decimal = field(default_factory=lambda: Decimal("0"), repr=False)
    _credit_total: Decimal = field(default_factory=lambda: Decimal("0"), repr=False)

    @property
    def normal_side(self) -> str:
        """Return 'debit' or 'credit' — the side that increases this account."""
        return "debit" if self.account_type in _DEBIT_NORMAL else "credit"

    @property
    def balance(self) -> Decimal:
        """Current balance (positive means normal-balance side exceeds the other)."""
        if self.account_type in _DEBIT_NORMAL:
            return self._debit_total - self._credit_total
        return self._credit_total - self._debit_total

    @property
    def raw_debits(self) -> Decimal:
        return self._debit_total

    @property
    def raw_credits(self) -> Decimal:
        return self._credit_total

    def debit(self, amount: Decimal) -> None:
        """Apply a debit to this account."""
        if amount < 0:
            raise ValueError("Debit amount must be non-negative")
        self._debit_total += amount

    def credit(self, amount: Decimal) -> None:
        """Apply a credit to this account."""
        if amount < 0:
            raise ValueError("Credit amount must be non-negative")
        self._credit_total += amount

    def __str__(self) -> str:
        code_prefix = f"({self.code}) " if self.code else ""
        return f"{code_prefix}{self.name} [{self.account_type.value}] = {self.balance}"
