#!/usr/bin/env python3
"""Outside check for Receipt Tally: a black-box test of any build against the spec.

Usage:  python3 outside_check.py <project_dir> [--json out.json]

It only runs `python -m receipt_tally ...` as a subprocess from <project_dir>,
so it knows nothing about how a build is structured. Each check is tagged with:
  ac        which acceptance criterion (or NF-x non-functional goal / ROB robustness)
  severity  MAJOR (crash, data loss, wrong money, privacy), MINOR, NIT
Spec-conformance checks come from docs/specs/receipt-tally.md. Robustness checks
probe hostile or sloppy input the spec implies must not crash the tool.

Written before the solo-vs-team builds existed; builds never saw it.
"""
import ast, hashlib, json, os, re, subprocess, sys, tempfile, textwrap, time

PROJECT = None
CHECKS = []


def check(cid, ac, severity, title):
    def deco(fn):
        CHECKS.append((cid, ac, severity, title, fn))
        return fn
    return deco


# ---------------------------------------------------------------- helpers
def run(args, cwd=None, timeout=20, env_extra=None, code=None):
    env = dict(os.environ, PYTHONPATH=PROJECT, PYTHONDONTWRITEBYTECODE="1")
    env.update(env_extra or {})
    cmd = [sys.executable, "-m", "receipt_tally"] + list(args)
    if code:
        cmd = [sys.executable, "-c", code] + list(args)
    t = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, env=env)
        out = p.stdout.decode("utf-8", "replace")
        err = p.stderr.decode("utf-8", "replace")
        return p.returncode, out, err, time.time() - t
    except subprocess.TimeoutExpired:
        return -999, "", "TIMEOUT", time.time() - t


class Sandbox:
    def __enter__(self):
        self.d = tempfile.mkdtemp(prefix="oc-")
        return self

    def __exit__(self, *a):
        subprocess.run(["rm", "-rf", self.d])

    def write(self, name, content, binary=False):
        p = os.path.join(self.d, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") if binary else open(p, "w", newline="") as f:
            f.write(content)
        return p

    def p(self, name):
        return os.path.join(self.d, name)

    def listing(self):
        out = set()
        for r, _, fs in os.walk(self.d):
            for f in fs:
                out.add(os.path.relpath(os.path.join(r, f), self.d))
        return out


CFG_A = textwrap.dedent("""\
    [columns]
    date = "Date"
    date_format = "%d/%m/%Y"
    description = "Description"
    amount = "Amount"
    [rules]
    list = [
      "tesco = Groceries",
      "shell = Transport",
      "salary = Income",
    ]
    """)
CSV_A = textwrap.dedent("""\
    Date,Description,Amount
    01/09/2026,CARD PAYMENT TO TESCO STORES,-23.10
    02/09/2026,Shell Petrol Station,-40.00
    03/09/2026,ACME LTD SALARY,1500.00
    04/09/2026,MYSTERY ONE,-0.10
    05/09/2026,MYSTERY TWO,-0.20
    """)


def cfg(date_fmt="%d/%m/%Y", amount='amount = "Amount"', rules=None, date="Date", desc="Description"):
    rules = rules if rules is not None else ['"tesco = Groceries"', '"shell = Transport"', '"salary = Income"']
    return ("[columns]\ndate = \"%s\"\ndate_format = \"%s\"\ndescription = \"%s\"\n%s\n[rules]\nlist = [%s]\n"
            % (date, date_fmt, desc, amount, ", ".join(rules)))


def nocomma(s):
    return s.replace(",", "")


def has_num(text, num):
    """True if the number appears as a whole token (commas ignored)."""
    return re.search(r"(?<![\d.])" + re.escape(num) + r"(?![\d])", nocomma(text)) is not None


def tb(out, err):
    return "Traceback" in out or "Traceback" in err


def basic(csv=CSV_A, conf=CFG_A, extra=(), sb=None):
    sb = sb
    c = sb.write("bank.csv", csv)
    k = sb.write("rules.toml", conf)
    return run([c, "--config", k] + list(extra), cwd=sb.d), c, k


def fail(msg):
    return (False, msg)


OK = (True, "")


# ---------------------------------------------------------------- AC checks
@check("AC1", "AC-1", "MAJOR", "Layout A: signed amount column parsed; negative = spending, positive = income")
def _():
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(sb=sb)
        if rc != 0: return fail("rc=%s %s" % (rc, err[:150]))
        for n in ("63.40", "1500.00", "1436.60", "40.00", "23.10"):
            if not has_num(out, n): return fail("missing %s in output" % n)
        return OK


@check("AC2", "AC-2", "MAJOR", "Layout B: separate Debit/Credit columns, YYYY-MM-DD dates")
def _():
    csv = "Date,Description,Debit,Credit\n2026-09-01,TESCO,12.50,\n2026-09-02,ACME SALARY,,100.00\n2026-09-03,SHELL,7.25,\n"
    conf = cfg("%Y-%m-%d", 'debit = "Debit"\ncredit = "Credit"')
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, conf, sb=sb)
        if rc != 0: return fail("rc=%s %s" % (rc, err[:150]))
        for n in ("19.75", "100.00", "80.25"):
            if not has_num(out, n): return fail("missing %s" % n)
        return OK


@check("AC3", "AC-3", "MAJOR", "Column order/header names changed in config only")
def _():
    csv = "Memo;x,Value,When,Other\nTESCO STORES,-10.00,31/08/2026,zzz\n"
    csv = "Memo,Value,When,Other\nTESCO STORES,-10.00,31/08/2026,zzz\nSHELL,-5.50,30/08/2026,zzz\n"
    conf = cfg(date="When", desc="Memo", amount='amount = "Value"')
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, conf, sb=sb)
        if rc != 0: return fail("rc=%s %s" % (rc, err[:150]))
        return OK if has_num(out, "15.50") and "Groceries" in out else fail("mapping not honoured:\n" + out[:200])


@check("AC4", "AC-4", "MAJOR", "Exact money: 0.10 + 0.20 totals 0.30; income 0.30 vs spending 0.30 nets to 0.00 (not -0.00)")
def _():
    csv = "Date,Description,Amount\n01/09/2026,A,-0.10\n02/09/2026,B,-0.20\n03/09/2026,C,0.30\n"
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        if rc != 0: return fail("rc=%s" % rc)
        if not has_num(out, "0.30"): return fail("0.30 missing")
        if "-0.00" in out: return fail("'-0.00' printed")
        return OK


@check("AC4b", "AC-4", "MAJOR", "Exact money: 1000 rows of 0.10 total exactly 100.00")
def _():
    csv = "Date,Description,Amount\n" + "".join("01/09/2026,ROW%d,-0.10\n" % i for i in range(1000))
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        return OK if rc == 0 and has_num(out, "100.00") else fail("total not 100.00:\n" + out[:300])


@check("AC5", "AC-5", "MAJOR", "First matching rule wins (file order)")
def _():
    conf = cfg(rules=['"shop = Shopping"', '"tesco = Groceries"'])
    csv = "Date,Description,Amount\n01/09/2026,TESCO SHOP,-10.00\n"
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, conf, sb=sb)
        return OK if "Shopping" in out and "Groceries" not in out else fail(out[:300])


@check("AC6", "AC-6", "MAJOR", "Rule is a case-insensitive substring match")
def _():
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(sb=sb)
        return OK if "Groceries" in out and "Transport" in out and "Income" in out else fail(out[:300])


@check("AC7", "AC-7", "MAJOR", "No match -> 'Uncategorised' bucket and its count")
def _():
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(sb=sb)
        if "ncategori" not in out: return fail("no uncategorised bucket")
        return OK if re.search(r"ncategori[^\n]*\b2\b", out) or has_num(out, "0.30") else fail("count 2 / total 0.30 not shown")


@check("AC8a", "AC-8", "MAJOR", "Summary has category totals, income, spending, net, top-5 spends, uncategorised count")
def _():
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(sb=sb)
        low = out.lower()
        for w in ("income", "spending", "net"):
            if w not in low: return fail("missing %s" % w)
        if "2026-09-02" not in out and "02/09/2026" not in out: return fail("top spends have no date")
        return OK


@check("AC8b", "AC-8", "MAJOR", "Top 5 lists the five largest spends only, largest first, income excluded")
def _():
    rows = [("01", "S10", "-10.00"), ("02", "S20", "-20.00"), ("03", "S30", "-30.00"), ("04", "S40", "-40.00"),
            ("05", "S50", "-50.00"), ("06", "S60", "-60.00"), ("07", "S01", "-1.00"), ("08", "INCOMEROW", "9999.00")]
    csv = "Date,Description,Amount\n" + "".join("%s/09/2026,%s,%s\n" % r for r in rows)
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        i60, i50, i20 = out.find("S60"), out.find("S50"), out.find("S20")
        if min(i60, i50, i20) < 0: return fail("expected top-5 spends missing")
        if i60 > i50: return fail("not largest first")
        if "S10" in out or "S01" in out: return fail("6th/7th largest spend listed in top 5")
        if "INCOMEROW" in out: return fail("income row listed as a spend")
        return OK


@check("AC8c", "AC-8", "MAJOR", "--month selects that month only; default is the latest month in the file")
def _():
    csv = "Date,Description,Amount\n15/08/2026,TESCO,-11.11\n15/09/2026,TESCO,-22.22\n05/10/2026,TESCO,-33.33\n"
    with Sandbox() as sb:
        c = sb.write("b.csv", csv); k = sb.write("r.toml", CFG_A)
        rc1, o1, e1, _ = run([c, "--config", k], cwd=sb.d)
        rc2, o2, e2, _ = run([c, "--config", k, "--month", "2026-08"], cwd=sb.d)
        if rc1 != 0 or rc2 != 0: return fail("rc %s/%s" % (rc1, rc2))
        if not (has_num(o1, "33.33") and not has_num(o1, "22.22") and not has_num(o1, "11.11")): return fail("default month is not latest")
        if not (has_num(o2, "11.11") and not has_num(o2, "33.33")): return fail("--month ignored")
        return OK


@check("AC9", "AC-9", "MAJOR", "Missing file: one plain line, non-zero exit, no traceback")
def _():
    with Sandbox() as sb:
        k = sb.write("r.toml", CFG_A)
        rc, out, err, _ = run([sb.p("nope.csv"), "--config", k], cwd=sb.d)
        text = (out + err).strip()
        if rc == 0: return fail("exit 0")
        if tb(out, err): return fail("traceback")
        return OK if len(text.splitlines()) == 1 and text else fail("not one line: %r" % text[:120])


@check("AC10a", "AC-10", "MAJOR", "Bad amount/date/short row: reported with line number, skipped, others processed, exit 0, skipped note")
def _():
    csv = ("Date,Description,Amount\n01/09/2026,TESCO,-10.00\n02/09/2026,BADAMT,abc\n"
           "99/09/2026,BADDATE,-1.00\n04/09/2026\n05/09/2026,TESCO,-5.00\n")
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        text = out + err
        if rc != 0: return fail("rc=%s" % rc)
        if not has_num(text, "15.00"): return fail("good rows not processed")
        for ln in ("3", "4", "5"):
            if not re.search(r"line\s*%s\b" % ln, text, re.I): return fail("line %s not reported" % ln)
        if not re.search(r"\b3\b[^\n]*skipped|skipped[^\n]*\b3\b", text, re.I): return fail("no '3 rows skipped' note")
        return OK


@check("AC11", "AC-11", "MAJOR", "No --out: nothing written anywhere (cwd tree unchanged)")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("rules.toml", CFG_A)
        before = sb.listing()
        run([c, "--config", k], cwd=sb.d)
        return OK if sb.listing() == before else fail("new files: %s" % (sb.listing() - before))


@check("AC12a", "AC-12", "MAJOR", "--out writes the summary to that file")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("rules.toml", CFG_A)
        rc, out, err, _ = run([c, "--config", k, "--out", sb.p("rep.txt")], cwd=sb.d)
        if rc != 0 or not os.path.exists(sb.p("rep.txt")): return fail("rc=%s, no file" % rc)
        return OK if has_num(open(sb.p("rep.txt")).read(), "63.40") else fail("report content wrong")


@check("AC12b", "AC-12", "MAJOR", "Existing --out file is not overwritten without --force; --force overwrites")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("rules.toml", CFG_A); sb.write("rep.txt", "PRECIOUS")
        rc, out, err, _ = run([c, "--config", k, "--out", sb.p("rep.txt")], cwd=sb.d)
        if rc == 0 or open(sb.p("rep.txt")).read() != "PRECIOUS": return fail("overwrote without --force (rc=%s)" % rc)
        if tb(out, err): return fail("traceback")
        rc, out, err, _ = run([c, "--config", k, "--out", sb.p("rep.txt"), "--force"], cwd=sb.d)
        return OK if rc == 0 and has_num(open(sb.p("rep.txt")).read(), "63.40") else fail("--force did not overwrite")


@check("AC13a", "AC-13", "MAJOR", "Deterministic: two runs byte-identical, no timestamps")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("rules.toml", CFG_A)
        a = run([c, "--config", k], cwd=sb.d)[1]; b = run([c, "--config", k], cwd=sb.d)[1]
        return OK if a == b and a else fail("outputs differ")


@check("AC13b", "AC-13", "MINOR", "Deterministic: equal-amount ties ordered by date then description regardless of file order")
def _():
    r1 = ["05/09/2026,ZED,-10.00", "05/09/2026,ALPHA,-10.00", "01/09/2026,MID,-10.00", "09/09/2026,BIG,-99.00"]
    with Sandbox() as sb:
        k = sb.write("r.toml", CFG_A)
        o = []
        for i, rows in enumerate((r1, list(reversed(r1)))):
            c = sb.write("b%d.csv" % i, "Date,Description,Amount\n" + "\n".join(rows) + "\n")
            o.append(run([c, "--config", k], cwd=sb.d)[1])
        if o[0] != o[1]: return fail("output depends on input row order")
        t = o[0]
        if not (t.find("MID") < t.find("ALPHA") < t.find("ZED")): return fail("tie order not date then description")
        return OK


NET_BLOCK = ("import sys,socket,runpy\n"
             "def _b(*a,**k): raise RuntimeError('network blocked')\n"
             "socket.socket=_b; socket.create_connection=_b; socket.getaddrinfo=_b\n"
             "sys.argv=['receipt_tally']+sys.argv[1:]\n"
             "try:\n    runpy.run_module('receipt_tally', run_name='__main__')\n"
             "finally:\n"
             "    bad=[m for m in ('urllib.request','http.client','requests','smtplib','ftplib','telnetlib','ssl','httpx','aiohttp','urllib3') if m in sys.modules]\n"
             "    print('NETMODS:'+','.join(bad), file=sys.stderr)\n")


@check("AC14", "AC-14", "MAJOR", "Works with sockets blocked and imports no networking modules")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("rules.toml", CFG_A)
        rc, out, err, _ = run([c, "--config", k], cwd=sb.d, code=NET_BLOCK)
        if rc != 0 or not has_num(out, "63.40"): return fail("fails with sockets blocked: rc=%s %s" % (rc, err[:150]))
        m = re.search(r"NETMODS:(.*)", err)
        return OK if m and not m.group(1).strip() else fail("network modules imported: %s" % (m.group(1) if m else "?"))


@check("AC15a", "AC-15", "MAJOR", "Bank file bytes and mtime unchanged")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("rules.toml", CFG_A)
        os.utime(c, (1_000_000_000, 1_000_000_000)); h = hashlib.md5(open(c, "rb").read()).hexdigest()
        run([c, "--config", k], cwd=sb.d); run([c, "--config", k, "--out", sb.p("r.txt")], cwd=sb.d)
        ok = hashlib.md5(open(c, "rb").read()).hexdigest() == h and int(os.stat(c).st_mtime) == 1_000_000_000
        return OK if ok else fail("input modified")


@check("AC15b", "AC-15", "MAJOR", "--out pointing at the bank file (even with --force) is refused; bank file survives")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("rules.toml", CFG_A)
        for extra in ([], ["--force"]):
            rc, out, err, _ = run([c, "--config", k, "--out", c] + extra, cwd=sb.d)
            if open(c).read() != CSV_A: return fail("BANK FILE OVERWRITTEN (extra=%s)" % extra)
            if rc == 0 or tb(out, err): return fail("not refused cleanly rc=%s" % rc)
        return OK


@check("AC15c", "AC-15", "MAJOR", "--out via a symlink (or ./x/../) to the bank file is refused; bank file survives")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("rules.toml", CFG_A)
        os.symlink(c, sb.p("link.txt")); os.makedirs(sb.p("sub"))
        for target in (sb.p("link.txt"), sb.p("sub/../bank.csv")):
            run([c, "--config", k, "--out", target, "--force"], cwd=sb.d)
            if open(c).read() != CSV_A: return fail("BANK FILE OVERWRITTEN via %s" % os.path.basename(target))
        return OK


@check("AC16a", "AC-16", "MAJOR", "Bad-row messages never contain the transaction description")
def _():
    csv = "Date,Description,Amount\n01/09/2026,SECRETMERCHANT1,abc\n99/09/2026,SECRETMERCHANT2,-1.00\n02/09/2026,TESCO,-5.00\n03/09/2026\n"
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        # description may appear only in the spec-mandated top-5 listing, never with the problem lines
        problem_lines = [l for l in (out + err).splitlines() if re.search(r"line\s*\d+", l, re.I)]
        if not problem_lines: return fail("no problem lines at all")
        return OK if not any("SECRETMERCHANT" in l for l in problem_lines) and "SECRETMERCHANT" not in err else fail("description leaked: %s" % problem_lines)


@check("AC16b", "AC-16", "MAJOR", "No log/side files are written during runs or errors")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A + "99/99/9999,X,zz\n"); k = sb.write("rules.toml", CFG_A)
        before = sb.listing()
        run([c, "--config", k], cwd=sb.d); run([sb.p("nope.csv"), "--config", k], cwd=sb.d)
        return OK if sb.listing() == before else fail("new files %s" % (sb.listing() - before))


@check("AC17a", "AC-17", "MINOR", "Plain text output: no ANSI escape codes")
def _():
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(sb=sb)
        return OK if "\x1b" not in out + err else fail("ESC in output")


@check("AC17b", "AC-17", "MINOR", "Escape/control characters inside a transaction description do not reach the terminal")
def _():
    csv = "Date,Description,Amount\n01/09/2026,\"EVIL \x1b[31mRED\x1b[0m \x07BEL\",-99.00\n"
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        bad = [c for c in out + err if (ord(c) < 32 and c not in "\n\t") or ord(c) == 127]
        return OK if rc == 0 and not bad else fail("control chars in output: %r" % bad[:3])


# ---------------------------------------------------------------- non-functional / packaging
@check("NF1", "NF-simplicity", "MINOR", "Stdlib only and package code <= 400 lines")
def _():
    pkg = os.path.join(PROJECT, "receipt_tally")
    if not os.path.isdir(pkg): return fail("no receipt_tally package")
    n = 0; third = set()
    std = set(sys.stdlib_module_names)
    for f in os.listdir(pkg):
        if f.endswith(".py"):
            src = open(os.path.join(pkg, f)).read(); n += len(src.splitlines())
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Import):
                    third |= {a.name.split(".")[0] for a in node.names} - std
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    third |= {node.module.split(".")[0]} - std
    third -= {"receipt_tally"}
    if third: return fail("non-stdlib imports: %s" % sorted(third))
    return OK if n <= 400 else fail("%d lines (> 400)" % n)


@check("NF2", "AC-4", "MAJOR", "No float() used for money in the package")
def _():
    pkg = os.path.join(PROJECT, "receipt_tally")
    for f in os.listdir(pkg):
        if f.endswith(".py") and re.search(r"\bfloat\s*\(", open(os.path.join(pkg, f)).read()):
            return fail("float( in %s" % f)
    return OK


@check("NF3", "T2", "MINOR", "README exists and explains running and rules")
def _():
    for n in ("README.md", "readme.md", "README.txt"):
        p = os.path.join(PROJECT, n)
        if os.path.exists(p):
            t = open(p).read().lower()
            return OK if "--config" in t and "rule" in t else fail("README lacks --config / rules")
    return fail("no README")


# ---------------------------------------------------------------- robustness probes
def cfg_error_case(conf_bytes, label):
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("rules.toml", conf_bytes, binary=True)
        rc, out, err, _ = run([c, "--config", k], cwd=sb.d)
        if tb(out, err): return fail("%s: traceback" % label)
        if rc == 0: return fail("%s: exit 0 on bad config" % label)
        return OK


@check("R1", "ROB", "MAJOR", "Config with wrong value type (date_format = 5): clean error, no traceback")
def _():
    return cfg_error_case(cfg().replace('date_format = "%d/%m/%Y"', "date_format = 5").encode(), "date_format=5")


@check("R2", "ROB", "MAJOR", "Config that is not valid UTF-8: clean error")
def _():
    return cfg_error_case(b'[columns]\ndate = "D\xff\xfe"\n', "non-utf8 config")


@check("R3", "ROB", "MAJOR", "Missing config file: clean error")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A)
        rc, out, err, _ = run([c, "--config", sb.p("none.toml")], cwd=sb.d)
        return OK if rc != 0 and not tb(out, err) else fail("rc=%s tb=%s" % (rc, tb(out, err)))


@check("R4", "ROB", "MAJOR", "Invalid TOML syntax: clean error")
def _():
    return cfg_error_case(b"[columns\nthis is = = not toml", "bad toml")


@check("R5", "ROB", "MAJOR", "Config missing required keys / sections: clean error")
def _():
    a = cfg_error_case(b"[rules]\nlist = []\n", "no columns section")
    if not a[0]: return a
    return cfg_error_case(b'[columns]\ndate = "Date"\n', "columns missing keys")


@check("R6", "ROB", "MAJOR", "Config names a column that is not in the CSV: clean error naming it (exit non-zero)")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("rules.toml", cfg(amount='amount = "Nonexistent"'))
        rc, out, err, _ = run([c, "--config", k], cwd=sb.d)
        return OK if rc != 0 and not tb(out, err) and "Nonexistent" in out + err else fail("rc=%s tb=%s" % (rc, tb(out, err)))


@check("R7", "ROB", "MINOR", "Malformed rule line (no '='): no traceback")
def _():
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(conf=cfg(rules=['"justtext"', '"tesco = Groceries"']), sb=sb)
        return OK if not tb(out, err) else fail("traceback")


@check("R8a", "ROB", "MAJOR", "Hostile amount 1E+100000 does not hang or print a gigantic number")
def _():
    csv = "Date,Description,Amount\n01/09/2026,TESCO,1E+100000\n02/09/2026,TESCO,-5.00\n"
    with Sandbox() as sb:
        (rc, out, err, el), *_ = basic(csv, sb=sb)
        if rc == -999 or el > 10: return fail("timeout/hang")
        if len(out) > 5000 or re.search(r"\d{40,}", out): return fail("huge number printed (%d chars)" % len(out))
        return OK if not tb(out, err) else fail("traceback")


@check("R8b", "ROB", "MAJOR", "NaN / Infinity amounts rejected as bad rows (no crash, no 'nan' totals)")
def _():
    csv = "Date,Description,Amount\n01/09/2026,A,NaN\n02/09/2026,B,Infinity\n03/09/2026,C,-sNaN\n04/09/2026,TESCO,-5.00\n"
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        if tb(out, err) or rc != 0: return fail("crash rc=%s" % rc)
        body = "\n".join(l for l in out.splitlines() if not re.search(r"line\s*\d+", l, re.I))
        return OK if has_num(out, "5.00") and not re.search(r"\bnan\b|\binf(inity)?\b", body, re.I) else fail("nan/inf leaked:\n" + out[:200])


@check("R9", "ROB", "MINOR", "Sub-cent amounts: rejected, or printed figures stay consistent (top-5 lines add up to the total)")
def _():
    csv = "Date,Description,Amount\n01/09/2026,A,-0.005\n02/09/2026,B,-0.005\n03/09/2026,C,-0.005\n04/09/2026,TESCO,-1.00\n"
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        if tb(out, err): return fail("traceback")
        if re.search(r"skipped|bad", out + err, re.I): return OK
        m = re.search(r"Total spending\s+([\d,.]+)", out, re.I)
        lines = re.findall(r"^\s*\S+\s+([\d,]+\.\d+)\s+\S", out.split("largest", 1)[-1], re.M)
        if not m or not lines: return fail("could not read output to check consistency")
        from decimal import Decimal
        tot = Decimal(nocomma(m.group(1))); s = sum(Decimal(nocomma(x)) for x in lines)
        return OK if tot == s else fail("total %s but lines add to %s" % (tot, s))


@check("R10", "ROB", "MINOR", "--month 2026-3 is normalised or rejected, never a silent all-zero summary")
def _():
    csv = "Date,Description,Amount\n05/03/2026,TESCO,-77.77\n"
    with Sandbox() as sb:
        c = sb.write("b.csv", csv); k = sb.write("r.toml", CFG_A)
        rc, out, err, _ = run([c, "--config", k, "--month", "2026-3"], cwd=sb.d)
        if tb(out, err): return fail("traceback")
        return OK if (rc != 0 and (out + err).strip()) or has_num(out, "77.77") else fail("silent empty summary, rc=%s" % rc)


@check("R11", "ROB", "MINOR", "--month with garbage, and a month with no rows: no traceback; garbage rejected")
def _():
    with Sandbox() as sb:
        c = sb.write("b.csv", CSV_A); k = sb.write("r.toml", CFG_A)
        rc, out, err, _ = run([c, "--config", k, "--month", "banana"], cwd=sb.d)
        if rc == 0 or tb(out, err): return fail("garbage month: rc=%s tb=%s" % (rc, tb(out, err)))
        rc, out, err, _ = run([c, "--config", k, "--month", "2030-01"], cwd=sb.d)
        return OK if not tb(out, err) and (out + err).strip() else fail("empty month: traceback/no message")


@check("R11b", "ROB", "NIT", "Month with no transactions says so in words (not just zeros)")
def _():
    with Sandbox() as sb:
        c = sb.write("b.csv", CSV_A); k = sb.write("r.toml", CFG_A)
        rc, out, err, _ = run([c, "--config", k, "--month", "2030-01"], cwd=sb.d)
        return OK if re.search(r"no transactions|no rows|nothing|no data|empty", out + err, re.I) else fail("no explicit message")


@check("R12", "ROB", "MAJOR", "European number '1.234,56' is rejected or read correctly, never read as 1.23456")
def _():
    csv = 'Date,Description,Amount\n01/09/2026,A,"-1.234,56"\n02/09/2026,TESCO,-5.00\n'
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        if tb(out, err): return fail("traceback")
        if re.search(r"skipped|bad", out + err, re.I) or has_num(out, "1234.56"): return OK
        return fail("silently misread:\n" + out[:200])


@check("R13", "ROB", "MAJOR", "Quoted thousands separator \"-1,234.50\" and currency symbols are parsed correctly")
def _():
    csv = 'Date,Description,Amount\n01/09/2026,A,"-1,234.50"\n02/09/2026,B,£-10.00\n03/09/2026,C,$20.00\n'
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        return OK if rc == 0 and has_num(out, "1234.50") and has_num(out, "1244.50") and not re.search(r"skipped", out + err, re.I) else fail("misparsed:\n" + out[:300])


@check("R14", "ROB", "MAJOR", "UTF-8 BOM, CRLF line endings, blank lines, padded values")
def _():
    raw = "﻿Date,Description,Amount\r\n01/09/2026,TESCO,-10.00\r\n\r\n02/09/2026,SHELL, -5.50 \r\n".encode("utf-8")
    with Sandbox() as sb:
        c = sb.write("bank.csv", raw, binary=True); k = sb.write("r.toml", CFG_A)
        rc, out, err, _ = run([c, "--config", k], cwd=sb.d)
        return OK if rc == 0 and has_num(out, "15.50") and not tb(out, err) else fail("rc=%s\n%s" % (rc, (out + err)[:200]))


@check("R15", "ROB", "MAJOR", "Empty file, header-only file, headerless file: no traceback")
def _():
    for label, body in (("empty", ""), ("header-only", "Date,Description,Amount\n"), ("no-header", "01/09/2026,TESCO,-1.00\n")):
        with Sandbox() as sb:
            (rc, out, err, _), *_ = basic(body, sb=sb)
            if tb(out, err): return fail("%s: traceback" % label)
    return OK


@check("R16", "ROB", "MAJOR", "CSV that is not valid UTF-8: no traceback")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", b"Date,Description,Amount\n01/09/2026,CAF\xc9 TESCO,-10.00\n02/09/2026,A,\xff\xfe\n", binary=True)
        k = sb.write("r.toml", CFG_A)
        rc, out, err, _ = run([c, "--config", k], cwd=sb.d)
        return OK if not tb(out, err) and (out + err).strip() else fail("traceback or silent")


@check("R17", "ROB", "MINOR", "20,000 rows processed in under 5 seconds")
def _():
    csv = "Date,Description,Amount\n" + "".join("%02d/09/2026,TESCO ITEM %d,-%d.%02d\n" % (i % 28 + 1, i, i % 90, i % 100) for i in range(20000))
    with Sandbox() as sb:
        (rc, out, err, el), *_ = basic(csv, sb=sb)
        return OK if rc == 0 and el < 5 else fail("rc=%s %.1fs" % (rc, el))


@check("R18", "ROB", "MINOR", "--out into a missing directory: clean one-line error")
def _():
    with Sandbox() as sb:
        c = sb.write("bank.csv", CSV_A); k = sb.write("r.toml", CFG_A)
        rc, out, err, _ = run([c, "--config", k, "--out", sb.p("no/such/dir/r.txt")], cwd=sb.d)
        return OK if rc != 0 and not tb(out, err) else fail("rc=%s tb=%s" % (rc, tb(out, err)))


@check("R19", "ROB", "MINOR", "Zero amount rows and -0.00 never print as '-0.00'; 29 Feb 2024 valid, 31 Feb invalid")
def _():
    csv = "Date,Description,Amount\n29/02/2024,TESCO,-4.00\n31/02/2024,TESCO,-9.00\n01/02/2024,ZERO,0.00\n02/02/2024,NEGZERO,-0.00\n"
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        if tb(out, err) or rc != 0: return fail("crash")
        if "-0.00" in out: return fail("'-0.00' printed")
        if has_num(out, "9.00"): return fail("31 Feb accepted")
        return OK if has_num(out, "4.00") else fail("29 Feb rejected")


@check("R20", "ROB", "MINOR", "Rule match is case-insensitive for non-ASCII text (café = Food matches 'CAFÉ NERO')")
def _():
    csv = "Date,Description,Amount\n01/09/2026,CAFÉ NERO,-3.50\n"
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, conf=cfg(rules=['"café = Food"']), sb=sb)
        return OK if "Food" in out else fail("not categorised as Food:\n" + out[:200])


@check("R21", "ROB", "MINOR", "Quoted description with commas and a newline inside does not crash")
def _():
    csv = 'Date,Description,Amount\n01/09/2026,"TESCO, STORE\nLONDON",-10.00\n02/09/2026,SHELL,-5.00\n'
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        return OK if rc == 0 and has_num(out, "15.00") and not tb(out, err) else fail("rc=%s" % rc)


@check("R22", "ROB", "MINOR", "Rows from other months do not leak into the chosen month; unordered input fine")
def _():
    csv = "Date,Description,Amount\n20/10/2026,TESCO,-1.00\n01/09/2026,TESCO,-2.00\n31/08/2026,TESCO,-4.00\n01/10/2026,TESCO,-8.00\n"
    with Sandbox() as sb:
        c = sb.write("b.csv", csv); k = sb.write("r.toml", CFG_A)
        rc, out, err, _ = run([c, "--config", k, "--month", "2026-10"], cwd=sb.d)
        return OK if has_num(out, "9.00") and not has_num(out, "2.00") and not has_num(out, "4.00") else fail(out[:200])


@check("R23", "ROB", "NIT", "Plural: '1 row(s) skipped' is grammatical")
def _():
    csv = "Date,Description,Amount\n01/09/2026,TESCO,-1.00\n02/09/2026,B,abc\n"
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        return OK if not re.search(r"\b1 rows\b", out + err) else fail("'1 rows'")


@check("R24", "ROB", "MAJOR", "Absurdly large magnitude (1e30 as plain digits) does not corrupt sums silently")
def _():
    big = "1" + "0" * 30 + ".00"
    csv = "Date,Description,Amount\n01/09/2026,A,-%s\n02/09/2026,TESCO,-0.01\n" % big
    with Sandbox() as sb:
        (rc, out, err, _), *_ = basic(csv, sb=sb)
        if tb(out, err): return fail("traceback")
        # either rejected as a bad row, or the exact total (big + 0.01) is shown
        if re.search(r"skipped|bad", out + err, re.I): return OK
        return OK if has_num(out, "1" + "0" * 30 + ".01") or ("1" + "0" * 30 + ".01") in nocomma(out) else fail("silent rounding of huge sum:\n" + out[:300])


# ---------------------------------------------------------------- the builds' own tests
def own_tests():
    """Run whatever test suite the build ships; return (count, passed_all, how)."""
    env = dict(os.environ, PYTHONPATH=PROJECT, PYTHONDONTWRITEBYTECODE="1")
    for cmd in ([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], [sys.executable, "-m", "unittest", "discover", "-s", "tests"]):
        try:
            p = subprocess.run(cmd, cwd=PROJECT, capture_output=True, timeout=300, env=env)
        except Exception:
            continue
        o = (p.stdout + p.stderr).decode("utf-8", "replace")
        if "No module named pytest" in o:
            continue
        m = re.search(r"(\d+) passed", o) or re.search(r"Ran (\d+) tests?", o)
        n = int(m.group(1)) if m else 0
        return n, p.returncode == 0, " ".join(cmd[2:4])
    return 0, False, "no runner"


def main():
    global PROJECT
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    PROJECT = os.path.abspath(sys.argv[1])
    jpath = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    results = []
    for cid, ac, sev, title, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as e:  # a crash inside a check is a failed check, with the reason kept
            ok, detail = False, "check error: %r" % (e,)
        results.append(dict(id=cid, ac=ac, severity=sev, title=title, passed=ok, detail=detail))
    n, all_ok, how = own_tests()
    failed = [r for r in results if not r["passed"]]
    summary = dict(project=PROJECT, checks=len(results), passed=len(results) - len(failed),
                   failed={s: sum(1 for r in failed if r["severity"] == s) for s in ("MAJOR", "MINOR", "NIT")},
                   own_tests=n, own_tests_pass=all_ok, own_runner=how)
    for r in failed:
        print("FAIL %-6s %-5s %s\n       %s" % (r["id"], r["severity"], r["title"], r["detail"].replace("\n", " | ")[:200]))
    print(json.dumps(summary))
    if jpath:
        json.dump(dict(summary=summary, results=results), open(jpath, "w"), indent=1)


if __name__ == "__main__":
    main()
