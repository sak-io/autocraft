"""Build and render the monthly summary (plain aligned text, no colour)."""
from dataclasses import dataclass
import decimal
import re
from decimal import Decimal

from .config import UserError
from .rules import UNCATEGORISED, categorise


@dataclass(frozen=True)
class Summary:
    month: str
    by_category: dict
    income: Decimal
    spending: Decimal  # positive magnitude
    top5: list
    uncategorised_count: int
    skipped: int


def latest_month(transactions) -> str:
    if not transactions:
        raise UserError("no valid rows found in the CSV")
    return max(t.date for t in transactions).strftime("%Y-%m")


def build_summary(transactions, rules, month=None, skipped=0) -> Summary:
    with decimal.localcontext() as ctx:
        ctx.prec = 60  # amounts are < 10**12 with 2 decimals: sums stay exact
        return _build(transactions, rules, month, skipped)


def _build(transactions, rules, month, skipped) -> Summary:
    month = month or latest_month(transactions)
    rows = [t for t in transactions if t.date.strftime("%Y-%m") == month]
    totals, uncat = {}, 0
    for t in rows:
        cat = categorise(t.description, rules)
        uncat += cat == UNCATEGORISED
        totals[cat] = totals.get(cat, Decimal(0)) + t.amount
    ordered = dict(sorted(totals.items(), key=lambda kv: (kv[1], kv[0])))
    income = sum((t.amount for t in rows if t.amount > 0), Decimal(0))
    spending = -sum((t.amount for t in rows if t.amount < 0), Decimal(0))
    spends = sorted((t for t in rows if t.amount < 0),
                    key=lambda t: (t.amount, t.date, t.description))
    return Summary(month, ordered, income, spending, spends[:5], uncat, skipped)


def _money(value: Decimal) -> str:
    return f"{value:,.2f}"


_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _clean(text) -> str:
    return _CONTROL.sub("", str(text))


def render(s: Summary, problems=()) -> str:
    if not s.by_category:
        return f"No transactions found for {s.month}.\n"
    with decimal.localcontext() as ctx:
        ctx.prec = 60
        return _render(s, problems)


def _render(s: Summary, problems) -> str:
    out = [f"Spending summary for {s.month}", "", "By category (net):"]
    width = max([len(c) for c in s.by_category] + [14])
    amounts = [_money(v) for v in s.by_category.values()]
    aw = max([len(a) for a in amounts] + [10])
    for cat, amt in zip(s.by_category, amounts):
        out.append(f"  {_clean(cat):<{width}}  {amt:>{aw}}")
    net = s.income - s.spending
    out += ["", f"  {'Total income':<{width}}  {_money(s.income):>{aw}}",
            f"  {'Total spending':<{width}}  {_money(s.spending):>{aw}}",
            f"  {'Net':<{width}}  {_money(net):>{aw}}", "", "5 largest spends:"]
    if not s.top5:
        out.append("  (none)")
    for t in s.top5:
        out.append(f"  {t.date.isoformat()}  {_money(-t.amount):>{aw}}  {_clean(t.description)}")
    out += ["", f"Uncategorised transactions: {s.uncategorised_count}"]
    if problems:
        out += ["", "Problems:"] + [f"  line {p.line}: {_clean(p.message)}" for p in problems]
    if s.skipped:
        out += ["", f"{s.skipped} {'row' if s.skipped == 1 else 'rows'} skipped"]
    return "\n".join(out) + "\n"
