"""Comprehensive tests for activeledger_pages."""

from decimal import Decimal

import pytest

from activeledger_pages import (
    Account,
    AccountType,
    AuditAction,
    AuditEntry,
    AuditTrail,
    FinancialReport,
    Ledger,
    Transaction,
    TransactionLine,
)


# ── Account ───────────────────────────────────────────────────────

class TestAccount:
    def test_create_asset(self):
        a = Account("Cash", AccountType.ASSET)
        assert a.name == "Cash"
        assert a.balance == Decimal("0")
        assert a.normal_side == "debit"

    def test_debit_increases_asset(self):
        a = Account("Cash", AccountType.ASSET)
        a.debit(Decimal("100"))
        assert a.balance == Decimal("100")

    def test_credit_decreases_asset(self):
        a = Account("Cash", AccountType.ASSET)
        a.debit(Decimal("100"))
        a.credit(Decimal("30"))
        assert a.balance == Decimal("70")

    def test_credit_increases_liability(self):
        a = Account("Loans", AccountType.LIABILITY)
        a.credit(Decimal("500"))
        assert a.balance == Decimal("500")
        assert a.normal_side == "credit"

    def test_revenue_normal_side(self):
        a = Account("Sales", AccountType.REVENUE)
        assert a.normal_side == "credit"

    def test_expense_normal_side(self):
        a = Account("Rent", AccountType.EXPENSE)
        assert a.normal_side == "debit"

    def test_negative_debit_rejected(self):
        a = Account("Cash", AccountType.ASSET)
        with pytest.raises(ValueError):
            a.debit(Decimal("-1"))

    def test_str_representation(self):
        a = Account("Cash", AccountType.ASSET, code="1000")
        assert "Cash" in str(a)
        assert "1000" in str(a)


# ── TransactionLine ───────────────────────────────────────────────

class TestTransactionLine:
    def test_debit_line(self):
        line = TransactionLine(account_name="Cash", debit=Decimal("50"))
        assert line.debit == Decimal("50")
        assert line.credit == Decimal("0")

    def test_both_sides_rejected(self):
        with pytest.raises(ValueError):
            TransactionLine(account_name="X", debit=Decimal("10"), credit=Decimal("10"))

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            TransactionLine(account_name="X", debit=Decimal("-5"))


# ── Transaction ───────────────────────────────────────────────────

class TestTransaction:
    def test_simple_transaction(self):
        txn = Transaction.simple("Sale", debit_account="Cash", credit_account="Revenue", amount=Decimal("100"))
        assert txn.is_balanced
        assert txn.total_debits == Decimal("100")
        assert txn.total_credits == Decimal("100")
        assert len(txn.lines) == 2

    def test_unbalanced_rejected(self):
        txn = Transaction(
            description="Bad",
            lines=[TransactionLine(account_name="Cash", debit=Decimal("100"))],
        )
        assert not txn.is_balanced
        with pytest.raises(ValueError):
            txn.validate()

    def test_empty_rejected(self):
        txn = Transaction(description="Empty")
        with pytest.raises(ValueError):
            txn.validate()

    def test_complex_transaction(self):
        txn = Transaction(
            description="Complex",
            lines=[
                TransactionLine(account_name="Equipment", debit=Decimal("800")),
                TransactionLine(account_name="Cash", credit=Decimal("300")),
                TransactionLine(account_name="Loans", credit=Decimal("500")),
            ],
        )
        assert txn.is_balanced

    def test_metadata(self):
        txn = Transaction.simple("Sale", "Cash", "Revenue", Decimal("10"), ref="INV-001")
        assert txn.metadata["ref"] == "INV-001"

    def test_auto_id_and_timestamp(self):
        txn = Transaction.simple("T", "A", "B", Decimal("1"))
        assert txn.id
        assert txn.timestamp is not None


# ── Ledger ────────────────────────────────────────────────────────

class TestLedger:
    def _make_ledger(self) -> Ledger:
        ldg = Ledger("Test")
        ldg.add_account("Cash", AccountType.ASSET)
        ldg.add_account("Revenue", AccountType.REVENUE)
        ldg.add_account("Expenses", AccountType.EXPENSE)
        ldg.add_account("Loans", AccountType.LIABILITY)
        ldg.add_account("Equity", AccountType.EQUITY)
        return ldg

    def test_add_account(self):
        ldg = Ledger()
        a = ldg.add_account("Cash", AccountType.ASSET, code="1000")
        assert a.name == "Cash"
        assert ldg.get_account("Cash") is a

    def test_duplicate_account_rejected(self):
        ldg = Ledger()
        ldg.add_account("Cash", AccountType.ASSET)
        with pytest.raises(KeyError):
            ldg.add_account("Cash", AccountType.ASSET)

    def test_missing_account_rejected(self):
        ldg = Ledger()
        with pytest.raises(KeyError):
            ldg.get_account("Nope")

    def test_post_transaction(self):
        ldg = self._make_ledger()
        txn = Transaction.simple("Sale", "Cash", "Revenue", Decimal("200"))
        ldg.post(txn)
        assert ldg.accounts["Cash"].balance == Decimal("200")
        assert ldg.accounts["Revenue"].balance == Decimal("200")
        assert len(ldg.transactions) == 1

    def test_post_unknown_account_rejected(self):
        ldg = Ledger()
        ldg.add_account("Cash", AccountType.ASSET)
        txn = Transaction.simple("Bad", "Cash", "Ghost", Decimal("10"))
        with pytest.raises(KeyError):
            ldg.post(txn)

    def test_accounts_by_type(self):
        ldg = self._make_ledger()
        assets = ldg.accounts_by_type(AccountType.ASSET)
        assert len(assets) == 1
        assert assets[0].name == "Cash"

    def test_trial_balance(self):
        ldg = self._make_ledger()
        ldg.post(Transaction.simple("Sale", "Cash", "Revenue", Decimal("100")))
        tb = ldg.trial_balance
        assert tb["Cash"] == Decimal("100")
        assert tb["Revenue"] == Decimal("100")

    def test_multi_post_balancing(self):
        ldg = self._make_ledger()
        ldg.post(Transaction.simple("Owner invests", "Cash", "Equity", Decimal("1000")))
        ldg.post(Transaction.simple("Earned", "Cash", "Revenue", Decimal("500")))
        ldg.post(Transaction.simple("Rent", "Expenses", "Cash", Decimal("200")))
        assert ldg.accounts["Cash"].balance == Decimal("1300")
        assert ldg.accounts["Expenses"].balance == Decimal("200")


# ── FinancialReport ───────────────────────────────────────────────

class TestFinancialReport:
    def _setup(self) -> tuple[Ledger, FinancialReport]:
        ldg = Ledger("Report Co")
        ldg.add_account("Cash", AccountType.ASSET)
        ldg.add_account("Equipment", AccountType.ASSET)
        ldg.add_account("Loans", AccountType.LIABILITY)
        ldg.add_account("Equity", AccountType.EQUITY)
        ldg.add_account("Revenue", AccountType.REVENUE)
        ldg.add_account("Expenses", AccountType.EXPENSE)

        ldg.post(Transaction.simple("Investment", "Cash", "Equity", Decimal("5000")))
        ldg.post(Transaction.simple("Loan", "Cash", "Loans", Decimal("2000")))
        ldg.post(Transaction.simple("Buy equipment", "Equipment", "Cash", Decimal("1500")))
        ldg.post(Transaction.simple("Earned", "Cash", "Revenue", Decimal("3000")))
        ldg.post(Transaction.simple("Rent", "Expenses", "Cash", Decimal("800")))

        return ldg, FinancialReport(ldg)

    def test_balance_sheet(self):
        ldg, rpt = self._setup()
        bs = rpt.balance_sheet()
        assert bs.total_assets > Decimal("0")
        assert bs.is_balanced

    def test_income_statement(self):
        ldg, rpt = self._setup()
        inc = rpt.income_statement()
        assert inc.total_revenue == Decimal("3000")
        assert inc.total_expenses == Decimal("800")
        assert inc.net_income == Decimal("2200")

    def test_trial_balance_report(self):
        ldg, rpt = self._setup()
        tb = rpt.trial_balance()
        assert "Cash" in tb
        assert "balance" in tb["Cash"]

    def test_balance_sheet_to_dict(self):
        _, rpt = self._setup()
        d = rpt.balance_sheet().to_dict()
        assert "balanced" in d

    def test_income_statement_to_dict(self):
        _, rpt = self._setup()
        d = rpt.income_statement().to_dict()
        assert "net_income" in d


# ── AuditTrail ────────────────────────────────────────────────────

class TestAuditTrail:
    def test_log_and_retrieve(self):
        trail = AuditTrail()
        entry = trail.log(AuditAction.ACCOUNT_CREATED, {"name": "Cash"})
        assert len(trail) == 1
        assert trail.last is entry

    def test_entry_hash_immutability(self):
        entry = AuditEntry(
            action=AuditAction.TRANSACTION_POSTED,
            details={"txn_id": "abc"},
        )
        assert entry.verify()

    def test_verify_clean_chain(self):
        trail = AuditTrail()
        trail.log(AuditAction.ACCOUNT_CREATED, {"name": "Cash"})
        trail.log(AuditAction.TRANSACTION_POSTED, {"txn_id": "t1"})
        assert trail.verify_chain()

    def test_filter_by_action(self):
        trail = AuditTrail()
        trail.log(AuditAction.ACCOUNT_CREATED, {"name": "A"})
        trail.log(AuditAction.TRANSACTION_POSTED, {"txn_id": "1"})
        trail.log(AuditAction.ACCOUNT_CREATED, {"name": "B"})
        result = trail.filter_by_action(AuditAction.ACCOUNT_CREATED)
        assert len(result) == 2

    def test_filter_by_actor(self):
        trail = AuditTrail()
        trail.log(AuditAction.TRANSACTION_POSTED, {"txn": "1"}, actor="alice")
        trail.log(AuditAction.TRANSACTION_POSTED, {"txn": "2"}, actor="bob")
        assert len(trail.filter_by_actor("alice")) == 1

    def test_empty_trail(self):
        trail = AuditTrail()
        assert trail.last is None
        assert trail.verify_chain()
