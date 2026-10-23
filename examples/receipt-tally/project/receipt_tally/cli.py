"""Command line: the only module that touches files or the screen."""
import argparse
import datetime
import os
import re
import sys

from .config import UserError, load_config
from .parse import read_transactions
from .summary import build_summary, render


def _month(text):
    try:
        if not re.fullmatch(r"\d{4}-\d{2}", text, re.ASCII):
            raise ValueError(text)
        datetime.datetime.strptime(text, "%Y-%m")
    except ValueError:
        raise argparse.ArgumentTypeError("must look like 2026-09") from None
    return text


def _parser():
    p = argparse.ArgumentParser(prog="receipt_tally",
                                description="Monthly spending summary from a bank CSV.")
    p.add_argument("csv", help="bank CSV file (never modified)")
    p.add_argument("--config", required=True, help="TOML config with columns and rules")
    p.add_argument("--month", type=_month, help="month to summarise, YYYY-MM (default: latest)")
    p.add_argument("--out", help="write the summary to this file instead of only the screen")
    p.add_argument("--force", action="store_true", help="allow --out to overwrite a file")
    return p


def _write_out(path, text, force, csv_path):
    if os.path.islink(path) and not os.path.exists(path):
        raise UserError(f"{path} is a broken link; choose another --out")
    if os.path.exists(path):
        if os.path.samefile(path, csv_path):
            raise UserError("--out must not be the bank CSV")
        if not force:
            raise UserError(f"{path} already exists; use --force to overwrite it")
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError:
        raise UserError(f"could not write {path}") from None


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
        transactions, problems = read_transactions(args.csv, cfg)
        summary = build_summary(transactions, cfg.rules, args.month, len(problems))
        text = render(summary, problems)
        if args.out:
            _write_out(args.out, text, args.force, args.csv)
            print(f"Summary written to {args.out}")
        else:
            sys.stdout.buffer.write(text.encode("utf-8"))
    except UserError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0
