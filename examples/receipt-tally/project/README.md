# Receipt Tally

Turns your bank's CSV file into a plain-text spending summary for one month.
It never connects to the internet and never changes your bank file.
You need Python 3.11 or newer. Nothing else to install.

## Run it each month
1. Download the month's CSV from your bank and save it somewhere, e.g. `sept.csv`.
2. In a terminal, in this folder, run:

    python -m receipt_tally sept.csv --config examples/config.toml

That prints the summary on screen and saves nothing. Useful extras:
- `--month 2026-09` summarise a specific month (default: the latest month in the file).
- `--out report.txt` also save the summary to a file. It will not overwrite an
  existing file unless you add `--force`.

Try it now with the fake data: `python -m receipt_tally examples/bank_layout_a.csv --config examples/config.toml`

## The config file
Open `examples/config.toml` in any text editor and copy it for your bank.
- `[columns]` says which CSV headings to use. Spelling must match your CSV's first line.
- `date_format` describes your dates: `%d/%m/%Y` is 31/12/2026, `%Y-%m-%d` is 2026-12-31.
- Use `amount` if your bank has one column where spending is negative. Use `debit`
  and `credit` if it has two columns. `examples/bank_layout_b.csv` shows the second kind.

## Writing rules
Under `[rules]`, each line is `"text = Category"`, for example `"tesco = Groceries"`.
- It looks for the text anywhere in the description, ignoring capital letters.
- The first rule that matches wins, so put specific rules above general ones.
- Anything that matches nothing goes in "Uncategorised"; add a rule for it next month.
- Refunds (money in) reduce their category's total.

## What the messages mean
- `Error: file not found` - the CSV path is wrong. Nothing was changed.
- `Error: column 'X' not found in the CSV header` - the name in the config does not match your CSV's first line.
- `Error: rule 3 in the config must look like: text = Category` - fix the third rule.
- `Error: ... already exists; use --force` - choose another `--out` name, or add `--force`.
- `line 7: bad amount 'abc'` - that row was skipped (it also says if the date or a field is bad). The rest were still counted; the total skipped is shown at the end.

Messages mention line numbers and column names, never what you bought.
