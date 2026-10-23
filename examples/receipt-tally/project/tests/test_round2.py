"""Review round 1 fixes (T1/T2)."""
import contextlib
import io
import os
import tempfile
import unittest
from decimal import Decimal

from receipt_tally.cli import main
from receipt_tally.config import Config, UserError, load_config
from receipt_tally.parse import parse_amount, read_transactions

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
A_CSV, A_TOML = os.path.join(FX, "a.csv"), os.path.join(FX, "a.toml")
GOOD = '[columns]\ndate="Date"\ndate_format="%Y-%m-%d"\ndescription="Description"\namount="Amount"\n'


def run(argv):
    out, err = io.StringIO(), io.StringIO()

    class W:
        buffer = type("B", (), {"write": lambda s, b: out.write(b.decode())})()
    import sys
    from unittest import mock
    with mock.patch.object(sys, "stdout", W()), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class Round2(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def cfg(self, content, mode="w"):
        p = os.path.join(self.d, "c.toml")
        with open(p, mode) as f:
            f.write(content)
        return p

    def csv(self, body):
        p = os.path.join(self.d, "t.csv")
        with open(p, "w", encoding="utf-8") as f:
            f.write("Date,Description,Amount\n" + body)
        return p

    def test_bad_config_never_traceback(self):
        bads = [GOOD.replace('"%Y-%m-%d"', "5"), GOOD.replace('"Date"', "7"),
                GOOD.replace('"Amount"', "[1]"), GOOD + "rules=5\n",
                GOOD + "[rules]\nlist=[1]\n", GOOD + "rules=[]\n", "[columns]\n"]
        for text in bads:
            code, _, err = run([A_CSV, "--config", self.cfg(text)])
            self.assertEqual(code, 2, text)
            self.assertEqual(len(err.strip().splitlines()), 1, text)
        code, _, err = run([A_CSV, "--config", self.cfg(b"\xff\xfe\x80", "wb")])
        self.assertEqual((code, len(err.strip().splitlines())), (2, 1))

    def test_amount_bounds(self):
        for bad in ["1E+100000", "NaN", "Infinity", "-inf", "1e5", "1000000000000",
                    "-1000000000000.00"]:
            with self.assertRaises(ValueError, msg=bad):
                parse_amount(bad)
        self.assertEqual(parse_amount("999999999999.99"), Decimal("999999999999.99"))

    def test_bad_amount_is_bad_row_not_hang(self):
        cfg = load_config(self.cfg(GOOD))
        tx, problems = read_transactions(self.csv("2026-09-01,x,1E+100000\n"), cfg)
        self.assertEqual((tx, len(problems)), ([], 1))

    def test_sums_not_rounded(self):
        code, out, _ = run([self.csv("2026-09-01,a,999999999999.99\n2026-09-02,b,0.01\n"
                                      "2026-09-03,c,999999999999.99\n"),
                            "--config", self.cfg(GOOD)])
        self.assertIn("1,999,999,999,999.99", out)

    def test_two_decimals_and_european(self):
        for bad in ["-0.005", "1.234,56", "1.23456", "1,5", "12."]:
            with self.assertRaises(ValueError, msg=bad):
                parse_amount(bad)
        self.assertEqual(parse_amount("£1,234.5"), Decimal("1234.5"))

    def test_quoted_thousands_separator(self):
        cfg = load_config(self.cfg(GOOD))
        tx, problems = read_transactions(self.csv('2026-09-01,rent,"-1,234.50"\n'), cfg)
        self.assertEqual((problems, tx[0].amount), ([], Decimal("-1234.50")))

    def test_month_strict_and_empty(self):
        c = self.cfg(GOOD)
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(io.StringIO()):
            run([self.csv("2026-09-01,a,-1.00\n"), "--config", c, "--month", "2026-3"])
        self.assertEqual(cm.exception.code, 2)
        code, out, _ = run([self.csv("2026-09-01,a,-1.00\n"), "--config", c, "--month", "2026-03"])
        self.assertEqual((code, len(out.strip().splitlines())), (0, 1))
        self.assertIn("2026-03", out)

    def test_control_chars_stripped(self):
        code, out, _ = run([self.csv('2026-09-01,"evil\x1b[31mred",-5.00\n2026-09-02,x,ab\x1bc\n'),
                            "--config", self.cfg(GOOD)])
        self.assertNotIn("\x1b", out)
        self.assertIn("evil[31mred", out)

    def test_dangling_symlink_out(self):
        target = os.path.join(self.d, "target.txt")
        link = os.path.join(self.d, "link.txt")
        os.symlink(target, link)
        code, _, err = run([A_CSV, "--config", A_TOML, "--out", link, "--force"])
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(target))

    def test_skipped_plural(self):
        c = self.cfg(GOOD)
        _, out, _ = run([self.csv("2026-09-01,a,-1.00\nbad,a,1\n"), "--config", c])
        self.assertIn("1 row skipped", out)
        _, out, _ = run([self.csv("2026-09-01,a,-1.00\nbad,a,1\nbad,b,2\n"), "--config", c])
        self.assertIn("2 rows skipped", out)


if __name__ == "__main__":
    unittest.main()
