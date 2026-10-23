"""Core tests (T1). Each test names the acceptance criterion (AC) it covers."""
import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal

from receipt_tally.config import Rule, UserError, load_config, parse_rules
from receipt_tally.parse import read_transactions
from receipt_tally.rules import categorise
from receipt_tally.summary import build_summary, render

FX = os.path.join(os.path.dirname(__file__), "fixtures")


def fx(name):
    return os.path.join(FX, name)


def load(csv, toml):
    cfg = load_config(fx(toml))
    tx, problems = read_transactions(fx(csv), cfg)
    return cfg, tx, problems


class CoreTests(unittest.TestCase):
    def test_core_layout_a_signed_amount(self):
        """AC-1"""
        _, tx, problems = load("a.csv", "a.toml")
        self.assertEqual(problems, [])
        self.assertEqual(len(tx), 6)
        self.assertEqual(tx[0].date, date(2026, 9, 1))
        self.assertEqual(tx[0].amount, Decimal("-23.10"))
        self.assertEqual(tx[2].amount, Decimal("1500.00"))

    def test_core_layout_b_debit_credit(self):
        """AC-2"""
        _, tx, _ = load("b.csv", "b.toml")
        self.assertEqual([t.amount for t in tx],
                         [Decimal("-23.10"), Decimal("-40.00"), Decimal("1500.00")])
        self.assertEqual(tx[0].date, date(2026, 9, 1))
        _, ta, _ = load("a.csv", "a.toml")
        self.assertEqual(type(ta[0]), type(tx[0]))

    def test_core_mapping_only_config_change(self):
        """AC-3"""
        with tempfile.TemporaryDirectory() as d:
            csv_p, cfg_p = os.path.join(d, "c.csv"), os.path.join(d, "c.toml")
            with open(csv_p, "w", encoding="utf-8") as f:
                f.write("Memo,Money,When\nCOFFEE,-3.50,09/09/2026\n")
            with open(cfg_p, "w", encoding="utf-8") as f:
                f.write('[columns]\ndate="When"\ndate_format="%d/%m/%Y"\n'
                        'description="Memo"\namount="Money"\n')
            tx, problems = read_transactions(csv_p, load_config(cfg_p))
        self.assertEqual(problems, [])
        self.assertEqual((tx[0].description, tx[0].amount), ("COFFEE", Decimal("-3.50")))

    def test_core_unknown_column_is_user_error(self):
        """AC-3 / AC-16: names the column, not any row data"""
        cfg = load_config(fx("a.toml"))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.csv")
            with open(p, "w", encoding="utf-8") as f:
                f.write("Foo,Bar\n1,2\n")
            with self.assertRaises(UserError) as cm:
                read_transactions(p, cfg)
        self.assertIn("'Date'", str(cm.exception))

    def test_core_exact_money(self):
        """AC-4"""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.csv")
            with open(p, "w", encoding="utf-8") as f:
                f.write("Date,Description,Amount\n01/09/2026,A,0.10\n02/09/2026,B,0.20\n")
            tx, _ = read_transactions(p, load_config(fx("a.toml")))
        total = sum((t.amount for t in tx), Decimal(0))
        self.assertEqual(total, Decimal("0.30"))
        self.assertTrue(all(isinstance(t.amount, Decimal) for t in tx))

    def test_core_amount_symbols_and_thousands(self):
        """AC-4 (parsing rule)"""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.csv")
            with open(p, "w", encoding="utf-8") as f:
                f.write('Date,Description,Amount\n01/09/2026,A,"£1,234.50"\n'
                        "02/09/2026,B,NaN\n")
            tx, problems = read_transactions(p, load_config(fx("a.toml")))
        self.assertEqual(tx[0].amount, Decimal("1234.50"))
        self.assertEqual(len(problems), 1)

    def test_core_first_match_wins(self):
        """AC-5"""
        rules = parse_rules(["tesco = Groceries", "tesco stores = Other"])
        self.assertEqual(categorise("TESCO STORES", rules), "Groceries")
        self.assertEqual(categorise("TESCO STORES", list(reversed(rules))), "Other")

    def test_core_case_insensitive_substring(self):
        """AC-6"""
        rules = parse_rules(["tesco = Groceries"])
        self.assertEqual(categorise("CARD PAYMENT TO TESCO STORES", rules), "Groceries")
        self.assertEqual(categorise("Tesco", [Rule("tesco", "G")]), "G")

    def test_core_uncategorised_counted(self):
        """AC-7"""
        cfg, tx, _ = load("a.csv", "a.toml")
        s = build_summary(tx, cfg.rules, "2026-09")
        self.assertEqual(s.uncategorised_count, 2)
        self.assertEqual(s.by_category["Uncategorised"], Decimal("-0.30"))

    def test_core_bad_rule_is_user_error(self):
        """AC-16: rule errors cite the rule number only"""
        with self.assertRaises(UserError) as cm:
            parse_rules(["ok = Fine", "no equals sign"])
        self.assertIn("rule 2", str(cm.exception))
        self.assertNotIn("equals sign", str(cm.exception))

    def test_core_month_summary(self):
        """AC-8"""
        cfg, tx, _ = load("a.csv", "a.toml")
        s = build_summary(tx, cfg.rules)  # default = latest month
        self.assertEqual(s.month, "2026-09")
        self.assertEqual(s.income, Decimal("1500.00"))
        self.assertEqual(s.spending, Decimal("63.40"))
        self.assertEqual(s.by_category["Groceries"], Decimal("-23.10"))
        self.assertEqual(s.top5[0].amount, Decimal("-40.00"))
        text = render(s)
        for needle in ("Groceries", "Total income", "Total spending", "Net",
                       "5 largest spends", "Uncategorised transactions: 2",
                       "1,436.60", "SHELL PETROL"):
            self.assertIn(needle, text)
        aug = build_summary(tx, cfg.rules, "2026-08")
        self.assertEqual(aug.spending, Decimal("5.00"))

    def test_core_top5_limited_and_ordered(self):
        """AC-8 / AC-13: ties broken by date then description"""
        from receipt_tally.parse import Transaction
        tx = [Transaction(date(2026, 9, d), Decimal("-10"), f"S{d}") for d in range(7, 0, -1)]
        s = build_summary(tx, [])
        self.assertEqual(len(s.top5), 5)
        self.assertEqual([t.date.day for t in s.top5], [1, 2, 3, 4, 5])

    def test_core_bad_rows_collected(self):
        """AC-10 (collection): skipped, others kept, no descriptions in messages"""
        _, tx, problems = load("bad.csv", "a.toml")
        self.assertEqual(len(tx), 2)
        self.assertEqual([(p.line, p.message) for p in problems], [
            (3, "bad amount 'abc'"), (4, "bad date '31/31/2026'"),
            (5, "missing field 'Description'")])
        text = render(build_summary(tx, [], skipped=len(problems)), problems)
        self.assertIn("line 3: bad amount 'abc'", text)
        self.assertIn("3 rows skipped", text)
        for p in problems:
            self.assertNotIn("SHOP", p.message)
        self.assertNotIn("SHOP THREE", text)

    def test_core_deterministic_and_plain(self):
        """AC-13, AC-17: identical output, no ANSI, no timestamps"""
        cfg, tx, _ = load("a.csv", "a.toml")
        one = render(build_summary(tx, cfg.rules))
        two = render(build_summary(list(reversed(tx)), cfg.rules))
        self.assertEqual(one, two)
        self.assertNotIn("\x1b", one)
        self.assertTrue(one.isascii())
