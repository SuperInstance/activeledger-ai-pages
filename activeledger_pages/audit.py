"""AuditTrail — immutable audit log for ledger operations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class AuditAction(str, Enum):
    """Tracked actions."""

    ACCOUNT_CREATED = "account_created"
    TRANSACTION_POSTED = "transaction_posted"
    TRANSACTION_VOIDED = "transaction_voided"
    REPORT_GENERATED = "report_generated"


@dataclass
class AuditEntry:
    """A single immutable audit record."""

    action: AuditAction
    details: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str = "system"
    _hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self._hash:
            self._hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = json.dumps(
            {
                "action": self.action.value,
                "details": self.details,
                "timestamp": self.timestamp.isoformat(),
                "actor": self.actor,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @property
    def hash(self) -> str:
        return self._hash

    def verify(self) -> bool:
        return self._hash == self._compute_hash()


@dataclass
class AuditTrail:
    """Append-only audit log. Entries cannot be modified or removed."""

    entries: list[AuditEntry] = field(default_factory=list)
    description: str = "Ledger Audit Trail"

    def log(
        self,
        action: AuditAction,
        details: dict[str, Any],
        actor: str = "system",
        timestamp: Optional[datetime] = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            action=action,
            details=details,
            actor=actor,
            timestamp=timestamp or datetime.now(timezone.utc),
        )
        self.entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """Verify every entry's hash is still valid (detects tampering)."""
        return all(e.verify() for e in self.entries)

    def filter_by_action(self, action: AuditAction) -> list[AuditEntry]:
        return [e for e in self.entries if e.action == action]

    def filter_by_actor(self, actor: str) -> list[AuditEntry]:
        return [e for e in self.entries if e.actor == actor]

    @property
    def last(self) -> Optional[AuditEntry]:
        return self.entries[-1] if self.entries else None

    def __len__(self) -> int:
        return len(self.entries)
