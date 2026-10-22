"""CLI tests (T2). Each test names the acceptance criterion (AC) it covers."""
import ast
import contextlib
import io
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from receipt_tally.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(ROOT, "tests", "fixtures")
A_CSV, A_TOML, BAD = (os.path.join(FX, n) for n in ("a.csv", "a.toml", "bad.csv"))


class Out:
    """Run main() in-process capturing stdout bytes and stderr."""
    def __init__(self, argv):
        raw = io.BytesIO()
        stdout = io.TextIOWrapper(raw, encoding="utf-8", newline="\n")
        err = io.StringIO()
        with mock.patch.object(sys, "stdout", stdout), contextlib.redirect_stderr(err):
            self.code = main(argv)
            stdout.flush()
        self.out = raw.getvalue().decode("utf-8")
        self.err = err.getvalue()


class CliTests(unittest.TestCase):
    def test_missing_file(self):
        """AC-9 (via real process: non-zero, one line, no traceback)"""
        r = subprocess.run([sys.executable, "-m", "receipt_tally", "nope.csv",
                            "--config", A_TOML], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1)
        self.assertNotIn("Traceback", r.stderr)

    def test_bad_rows_exit_zero(self):
        """AC-10 (CLI): reported, skipped, exit 0, N rows skipped"""
        r = Out([BAD, "--config", A_TOML])
        self.assertEqual(r.code, 0)
        self.assertIn("line 3: bad amount 'abc'", r.out)
        self.assertIn("3 rows skipped", r.out)
        self.assertNotIn("SHOP THREE", r.out)

    def test_dry_run_creates_nothing(self):
        """AC-11"""
        with tempfile.TemporaryDirectory() as d:
            old = os.getcwd()
            os.chdir(d)
            try:
                r = Out([A_CSV, "--config", A_TOML])
                self.assertEqual(os.listdir(d), [])
            finally:
                os.chdir(old)
        self.assertEqual(r.code, 0)
        self.assertIn("Spending summary for 2026-09", r.out)

    def test_out_file_and_force(self):
        """AC-12"""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "report.txt")
            self.assertEqual(Out([A_CSV, "--config", A_TOML, "--out", p]).code, 0)
            with open(p, encoding="utf-8") as f:
                first = f.read()
            self.assertEqual(first, Out([A_CSV, "--config", A_TOML]).out)
            self.assertEqual(os.listdir(d), ["report.txt"])
            with open(p, "w", encoding="utf-8") as f:
                f.write("old")
            r = Out([A_CSV, "--config", A_TOML, "--out", p])
            self.assertEqual(r.code, 2)
            self.assertIn("--force", r.err)
            with open(p, encoding="utf-8") as f:
                self.assertEqual(f.read(), "old")
            self.assertEqual(Out([A_CSV, "--config", A_TOML, "--out", p, "--force"]).code, 0)
            with open(p, encoding="utf-8") as f:
                self.assertEqual(f.read(), first)

    def test_out_cannot_be_input(self):
        """AC-15 (safety): --out pointing at the bank file is refused"""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "bank.csv")
            with open(A_CSV, "rb") as s, open(p, "wb") as t:
                t.write(s.read())
            r = Out([p, "--config", A_TOML, "--out", p, "--force"])
            self.assertEqual(r.code, 2)

    def test_month_option(self):
        """AC-8 (CLI) --month"""
        r = Out([A_CSV, "--config", A_TOML, "--month", "2026-08"])
        self.assertIn("Spending summary for 2026-08", r.out)
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                main([A_CSV, "--config", A_TOML, "--month", "09-2026"])

    def test_no_network(self):
        """AC-14: runs with sockets blocked; package imports no networking modules"""
        def boom(*a, **k):
            raise AssertionError("network used")
        with mock.patch.object(socket, "socket", boom):
            self.assertEqual(Out([A_CSV, "--config", A_TOML]).code, 0)
        banned = {"socket", "urllib", "http", "ftplib", "smtplib", "requests",
                  "ssl", "asyncio", "xmlrpc", "telnetlib", "socketserver"}
        pkg = os.path.join(ROOT, "receipt_tally")
        for name in os.listdir(pkg):
            if name.endswith(".py"):
                with open(os.path.join(pkg, name), encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    mods = []
                    if isinstance(node, ast.Import):
                        mods = [a.name for a in node.names]
                    elif isinstance(node, ast.ImportFrom) and not node.level:
                        mods = [node.module]
                    for m in mods:
                        self.assertNotIn(m.split(".")[0], banned, name)

    def test_no_float_for_money(self):
        """AC-4: package source never uses float"""
        pkg = os.path.join(ROOT, "receipt_tally")
        for name in os.listdir(pkg):
            if name.endswith(".py"):
                with open(os.path.join(pkg, name), encoding="utf-8") as f:
                    for node in ast.walk(ast.parse(f.read())):
                        self.assertFalse(isinstance(node, ast.Name) and node.id == "float", name)
                        self.assertFalse(isinstance(node, ast.Constant)
                                         and isinstance(node.value, float), name)

    def test_input_untouched(self):
        """AC-15: bytes and mtime unchanged"""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "bank.csv")
            with open(A_CSV, "rb") as s, open(p, "wb") as t:
                t.write(s.read())
            os.utime(p, ns=(1_000_000_000_000_000_000, 1_000_000_000_000_000_000))
            before = (open(p, "rb").read(), os.stat(p).st_mtime_ns)
            Out([p, "--config", A_TOML])
            Out([p, "--config", A_TOML, "--out", os.path.join(d, "r.txt")])
            after = (open(p, "rb").read(), os.stat(p).st_mtime_ns)
        self.assertEqual(before, after)

    def test_errors_never_echo_descriptions(self):
        """AC-16: errors/warnings cite lines and fields only; no log files"""
        r = Out([BAD, "--config", A_TOML])
        for word in ("SHOP", "TESCO"):
            self.assertNotIn(word, r.err)
        for word in ("SHOP ONE", "SHOP TWO", "SHOP THREE"):
            self.assertNotIn(word, r.out.split("Problems:")[-1])
        r2 = Out([A_CSV, "--config", os.path.join(FX, "missing.toml")])
        self.assertEqual(r2.code, 2)
        self.assertTrue(r2.err.startswith("Error:"))

    def test_plain_output_and_deterministic(self):
        """AC-13, AC-17: byte-identical runs, no ANSI"""
        one, two = (Out([A_CSV, "--config", A_TOML]).out for _ in range(2))
        self.assertEqual(one, two)
        self.assertNotIn("\x1b", one)

    def test_examples_run(self):
        """README examples work"""
        ex = os.path.join(ROOT, "examples")
        r = Out([os.path.join(ex, "bank_layout_a.csv"), "--config", os.path.join(ex, "config.toml")])
        self.assertEqual(r.code, 0)
        self.assertIn("Groceries", r.out)


if __name__ == "__main__":
    unittest.main()
