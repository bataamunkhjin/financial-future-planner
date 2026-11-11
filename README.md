# Financial Future Planner

A Streamlit two-tab app designed for a class project and finance portfolio.

- **Mortgage / Loan Planner:** 4 essential inputs; monthly payment, total loan cost, amortization, extra-payment savings, payoff date, automatically generated scenarios, charts, CSV export; optional property tax, insurance, PMI, loan start date.
- **Retirement Planner:** 5 essential inputs; inflation-adjusted savings projection, retirement income target, 4% initial-withdrawal heuristic (editable), required savings, alternative retirement ages, Monte Carlo percentile fan chart, probability of reaching a target, probability of funding withdrawals through a planning age, CSV exports.

## Run on Windows

Open the project folder in File Explorer, click the address bar, type `cmd`, and press Enter. Then run:

```bat
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

If your system uses `python` instead of `py`:

```bat
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit should open a browser window automatically. If not, open the localhost URL printed in the terminal (commonly `http://localhost:8501`). To stop, press `Ctrl+C` in the terminal.

If `streamlit` isn't recognized, do **not** use `streamlit run app.py` alone; `py -m streamlit run app.py` avoids many PATH issues.

## File structure

- `app.py` — Streamlit user interface and interactive Plotly charts
- `finance.py` — tested financial calculation functions
- `requirements.txt` — Python dependencies
- `tests/test_finance.py` — calculation tests

## Financial assumptions and interpretation

**Loan:** Monthly fixed-rate fully amortizing loan, with nominal annual rate divided by 12 for monthly interest. Scheduled payment is constant except the final smaller payment. Additional payments reduce principal immediately; no penalties. First repayment happens one calendar month after loan start. Optional property tax, insurance, and PMI are *monthly cash outflow only*, not financed amounts or interest. PMI does not automatically stop at an LTV threshold; that would need home price and applicable cancellation rules.

**Retirement:** The 5 core inputs use *today's money*. The model keeps contributions and target retirement withdrawals constant **in purchasing power**; in real life their nominal cash amounts would increase with inflation. Nominal return is converted to real return using `(1 + nominal return)/(1 + inflation)`. Deposits and withdrawals happen at month-end. The 4% rule is used as an initial-withdrawal sizing heuristic, not proof that withdrawals are sustainable.

**Monte Carlo:** For each simulated year, draw a lognormal gross return calibrated to the entered arithmetic nominal mean and annual standard deviation. Each yearly return is spread evenly over its 12 months, converted to constant purchasing power using fixed annual inflation. Returns are independent between years; the simulation does not model fat tails, serial correlation, tax, fees, or varying inflation. The percentage of paths reaching the starting portfolio target at retirement **differs** from the percentage able to fund all monthly target withdrawals through the selected planning age. The random seed is fixed (42) for repeatable classroom results; simulations are illustrative, not calibrated forecasts.

**Currency:** The selector only changes number labels and input defaults. It never converts currencies or fetches exchange rates. Loan and retirement figures in the selected mode should be entered in that currency.

## Performance

Designed to run locally without cloud services. Monte Carlo defaults to 1,000 paths (250–2,000 options). For an older 4 GB RAM laptop, 250 or 500 simulations may render faster.

## Run tests

Install pytest if needed: `py -m pip install pytest`

```bat
py -m pytest -q
```

## Potential follow-ups

1. Add a third 'Pay Debt vs. Invest' comparison *after* the two tabs are stable.
2. Add one-click PDF report export and URL-sharing of scenario parameters.
3. Add different mortgage rate schedules or investment/fee assumptions.

*Educational purposes only; not personalized financial advice.*
