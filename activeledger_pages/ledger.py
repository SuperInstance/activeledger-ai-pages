"""Ledger — the central book of accounts and transactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from .account import Account, AccountType
from .transaction import Transaction


@dataclass
class Ledger:
    """Double-entry ledger that owns accounts and validates transactions."""

    name: str = "General Ledger"
    accounts: dict[str, Account] = field(default_factory=dict)
    transactions: list[Transaction] = field(default_factory=list)

    # ── account management ────────────────────────────────────────

    def add_account(
        self,
        name: str,
        account_type: AccountType,
        code: Optional[str] = None,
        description: str = "",
    ) -> Account:
        if name in self.accounts:
            raise KeyError(f"Account '{name}' already exists")
        acct = Account(name=name, account_type=account_type, code=code, description=description)
        self.accounts[name] = acct
        return acct

    def get_account(self, name: str) -> Account:
        if name not in self.accounts:
            raise KeyError(f"Account '{name}' not found")
        return self.accounts[name]

    # ── transaction posting ───────────────────────────────────────

    def post(self, txn: Transaction) -> Transaction:
        """Validate and post a transaction. Returns the transaction on success."""
        txn.validate()
        for line in txn.lines:
            if line.account_name not in self.accounts:
                raise KeyError(f"Account '{line.account_name}' not found in ledger")
        # Apply to accounts
        for line in txn.lines:
            acct = self.accounts[line.account_name]
            if line.debit:
                acct.debit(line.debit)
            else:
                acct.credit(line.credit)
        self.transactions.append(txn)
        return txn

    # ── queries ───────────────────────────────────────────────────

    def accounts_by_type(self, account_type: AccountType) -> list[Account]:
        return [a for a in self.accounts.values() if a.account_type == account_type]

    @property
    def trial_balance(self) -> dict[str, Decimal]:
        """Return {account_name: balance} for every account."""
        return {name: acct.balance for name, acct in self.accounts.items()}

    def is_balanced(self) -> bool:
        """Check if total debits == total credits across all accounts."""
        total = sum(a.balance for a in self.accounts.values() if a.account_type in _BALANCE_CHECK)
        # In double-entry: sum(assets+expenses) == sum(liabilities+equity+revenue)
        debit_side = sum(
            a.balance for a in self.accounts.values() if a.account_type in _DEBIT_SIDE
        )
        credit_side = sum(
            a.balance for a in self.accounts.values() if a.account_type in _CREDIT_SIDE
        )
        return debit_side == credit_side

    def __str__(self) -> str:
        return f"{self.name} | {len(self.accounts)} accounts | {len(self.transactions)} transactions"


_DEBIT_SIDE = {AccountType.ASSET, AccountType.EXPENSE}
_CREDIT_SIDE = {AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE}
_BALANCE_CHECK = _DEBIT_SIDE | _CREDIT_SIDE
