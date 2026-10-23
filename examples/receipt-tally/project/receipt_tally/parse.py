"""Read a bank CSV into transactions plus a list of problems (never raises per row)."""
import csv
import datetime
import re
from dataclasses import dataclass
from decimal import Decimal

from .config import UserError


@dataclass(frozen=True)
class Transaction:
    date: datetime.date
    amount: Decimal  # signed: negative = spending
    description: str


@dataclass(frozen=True)
class Problem:
    line: int
    message: str


_AMOUNT = re.compile(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)?(?:\.\d{1,2})?", re.ASCII)
_LIMIT = Decimal(10) ** 12


def parse_amount(text) -> Decimal:
    """Plain amounts only: optional currency symbol, thousands commas, <=2 decimals."""
    cleaned = "".join(ch for ch in (text or "") if ch not in "£$€  ")
    if not cleaned or not any(c.isdigit() for c in cleaned) or not _AMOUNT.fullmatch(cleaned):
        raise ValueError(text)
    value = Decimal(cleaned.replace(",", ""))
    if abs(value) >= _LIMIT:
        raise ValueError(text)
    return value


def _blank(value) -> bool:
    return value is None or not value.strip()


def _row_to_transaction(row, cfg) -> Transaction:
    """Raise ValueError('message') describing the first problem (no descriptions)."""
    if _blank(row.get(cfg.date)):
        raise ValueError(f"missing field '{cfg.date}'")
    if _blank(row.get(cfg.description)):
        raise ValueError(f"missing field '{cfg.description}'")
    raw_date = row[cfg.date].strip()
    try:
        date = datetime.datetime.strptime(raw_date, cfg.date_format).date()
    except ValueError:
        raise ValueError(f"bad date '{raw_date}'") from None
    if cfg.amount:
        if _blank(row.get(cfg.amount)):
            raise ValueError(f"missing field '{cfg.amount}'")
        amount = _amount(row[cfg.amount])
    else:
        debit, credit = row.get(cfg.debit or ""), row.get(cfg.credit or "")
        if _blank(debit) and _blank(credit):
            raise ValueError(f"missing field '{cfg.debit or cfg.credit}'")
        amount = Decimal(0)
        if not _blank(debit):
            amount -= abs(_amount(debit))
        if not _blank(credit):
            amount += abs(_amount(credit))
    return Transaction(date, amount, row[cfg.description].strip())


def _amount(text) -> Decimal:
    try:
        return parse_amount(text)
    except ValueError:
        raise ValueError(f"bad amount '{text.strip()}'") from None


def read_transactions(path, cfg):
    """Return (transactions, problems). Opens the file read-only."""
    try:
        fh = open(path, encoding="utf-8-sig", newline="")
    except FileNotFoundError:
        raise UserError(f"file not found: {path}") from None
    except OSError:
        raise UserError(f"could not open file: {path}") from None
    transactions, problems = [], []
    with fh:
        try:
            reader = csv.DictReader(fh)
            header = reader.fieldnames or []
            wanted = [cfg.date, cfg.description, cfg.amount, cfg.debit, cfg.credit]
            for name in wanted:
                if name and name not in header:
                    raise UserError(f"column '{name}' not found in the CSV header")
            for row in reader:
                try:
                    transactions.append(_row_to_transaction(row, cfg))
                except ValueError as exc:
                    problems.append(Problem(reader.line_num, str(exc)))
        except (csv.Error, UnicodeDecodeError):
            raise UserError("the file is not a readable UTF-8 CSV") from None
    return transactions, problems
