"""Load the TOML config: column mapping and categorisation rules."""
import tomllib
from dataclasses import dataclass, field


class UserError(Exception):
    """A problem Sam can fix; shown as one plain line."""


@dataclass(frozen=True)
class Rule:
    pattern: str
    category: str


@dataclass(frozen=True)
class Config:
    date: str
    date_format: str
    description: str
    amount: str | None = None
    debit: str | None = None
    credit: str | None = None
    rules: list = field(default_factory=list)


def parse_rules(lines) -> list:
    rules = []
    for n, line in enumerate(lines, 1):
        pattern, sep, category = str(line).partition("=")
        pattern, category = pattern.strip(), category.strip()
        if not sep or not pattern or not category:
            raise UserError(f"rule {n} in the config must look like: text = Category")
        rules.append(Rule(pattern.lower(), category))
    return rules


def load_config(path) -> Config:
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except FileNotFoundError:
        raise UserError(f"config file not found: {path}") from None
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError):
        raise UserError(f"config file could not be read as TOML: {path}") from None
    cols = data.get("columns")
    if not isinstance(cols, dict):
        raise UserError("config is missing the [columns] section")
    for key in ("date", "date_format", "description"):
        if not cols.get(key):
            raise UserError(f"config [columns] is missing '{key}'")
    for key in ("date", "date_format", "description", "amount", "debit", "credit"):
        if key in cols and not isinstance(cols[key], str):
            raise UserError(f"config [columns] '{key}' must be text")
    amount, debit, credit = cols.get("amount"), cols.get("debit"), cols.get("credit")
    if not amount and not (debit or credit):
        raise UserError("config [columns] needs 'amount', or 'debit' and 'credit'")
    rules_sec = data.get("rules", {})
    rule_lines = rules_sec.get("list", []) if isinstance(rules_sec, dict) else None
    if not isinstance(rule_lines, list) or not all(isinstance(r, str) for r in rule_lines):
        raise UserError("config [rules] list must be a list of strings")
    return Config(cols["date"], cols["date_format"], cols["description"],
                  amount, debit, credit, parse_rules(rule_lines))
