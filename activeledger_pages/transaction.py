"""Transaction and TransactionLine dataclasses."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


@dataclass
class TransactionLine:
    """A single debit or credit line within a transaction."""

    account_name: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    description: str = ""

    def __post_init__(self) -> None:
        self.debit = Decimal(str(self.debit))
        self.credit = Decimal(str(self.credit))
        if self.debit < 0 or self.credit < 0:
            raise ValueError("Debit and credit amounts must be non-negative")
        if self.debit and self.credit:
            raise ValueError("A line must be debit OR credit, not both")


@dataclass
class Transaction:
    """A double-entry transaction with balanced debits and credits."""

    description: str
    lines: list[TransactionLine] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = field(default_factory=dict)

    # ── construction helpers ──────────────────────────────────────

    @classmethod
    def simple(
        cls,
        description: str,
        debit_account: str,
        credit_account: str,
        amount: Decimal,
        **meta: str,
    ) -> Transaction:
        """Create a two-line (simple) transaction."""
        amount = Decimal(str(amount))
        return cls(
            description=description,
            lines=[
                TransactionLine(account_name=debit_account, debit=amount),
                TransactionLine(account_name=credit_account, credit=amount),
            ],
            metadata=meta,
        )

    # ── validation ────────────────────────────────────────────────

    @property
    def total_debits(self) -> Decimal:
        return sum((ln.debit for ln in self.lines), Decimal("0"))

    @property
    def total_credits(self) -> Decimal:
        return sum((ln.credit for ln in self.lines), Decimal("0"))

    @property
    def is_balanced(self) -> bool:
        return self.total_debits == self.total_credits

    def validate(self) -> None:
        """Raise ValueError if transaction is not balanced or has no lines."""
        if not self.lines:
            raise ValueError(f"Transaction {self.id} has no lines")
        if not self.is_balanced:
            raise ValueError(
                f"Transaction {self.id} not balanced: "
                f"debits={self.total_debits} credits={self.total_credits}"
            )

    def __str__(self) -> str:
        return (
            f"TXN {self.id} | {self.description} | "
            f"DR {self.total_debits} / CR {self.total_credits} | "
            f"{self.timestamp:%Y-%m-%d %H:%M}"
        )
