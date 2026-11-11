# Financial Future Planner (v2)

A **two-tab Streamlit financial-planning app** for coursework and portfolio demonstrations. Four essential mortgage inputs, five essential retirement inputs, many automated outputs. No sign-in, paid API, or database.

## Features

### Tab 1: Mortgage / Loan Planner
- Scheduled principal-and-interest payment, total cost, payoff date, amortization charts, CSV schedule.
- Extra principal payment comparison and interest/time saved.
- **Automatic what-if scenarios:** standard / multiple extra-payment strategies; annual mortgage interest rate -2, -1, 0, +1, +2 percentage points (new-loan scenarios, *not* changes to an existing fixed rate).
- **Personalized insights** that recalculate when inputs change.
- **Mortgage vs investing:** invest spare cash while making regular payments versus prepay the mortgage first and invest freed payments afterwards. Both have **the same monthly cash budget**, including the last partial payment. Comparison ends at the original mortgage maturity. The comparison reuses the investment return assumption from the Retirement tab; it adds *no required inputs*.
- Optional property tax, insurance, PMI and loan start date in an expander.

### Tab 2: Retirement Planner
- Retirement savings projections in today's purchasing power, estimated target using an editable initial withdrawal rate, required monthly savings and shortfall.
- Yearly projection and Monte Carlo percentile fan chart with distinct metrics for reaching the target and funding withdrawals through the planning age.
- **Earliest modeled eligible retirement age:** finds the first whole-year age where saved capital meets **both** the initial withdrawal-rule target and the *deterministic* present-value cost of monthly spending through the chosen planning horizon. This is **not** a guaranteed retirement age or a Monte Carlo success threshold.
- **Automatic what-if scenarios:** ±2 percentage points on expected nominal return, +2 points inflation, +10% monthly saving, retirement 5 years earlier/later when valid. One variable changes at a time.
- **Personalized insights** and CSV projections.
- Optional return, inflation, withdrawal rate, volatility, planning age and simulation count in an expander.

### Combined PDF report
Use the **Download combined PDF** button in the sidebar or the Retirement tab. Generates an in-memory, multi-page ReportLab PDF containing both tabs' summary metrics, scenario comparisons, insights and simple vector charts, without an external service or font files. For portability, PDFs show `MNT` rather than the `₮` symbol. CSV downloads remain available for the full data tables.

## File structure

```
app.py
finance.py
report.py
requirements.txt
README.md
tests/
    test_finance.py
    test_features.py
```

> Upload these **files directly to your GitHub repository root** (do not upload the ZIP by itself, and do not nest the files in a second folder). `app.py` and `requirements.txt` should be visible at the top level.

## GitHub and Streamlit Cloud deployment

1. Create or open your public/private GitHub project repository (your choice; your Streamlit Cloud access must permit the repository).
2. If updating an existing repo, replace `app.py`, `finance.py`, `requirements.txt`, `README.md` and upload the **new** `report.py` and `tests/test_features.py` alongside the existing files (test files are optional for the hosted app).
3. Commit the changes to your default branch (usually `main`).
4. Open https://share.streamlit.io and deploy or manage the existing app. Set the repository, `main` branch (or your actual branch), and **main file `app.py`**.
5. Streamlit Cloud should install `requirements.txt` and rerun the updated app automatically. If it reports a missing `report` module, confirm **`report.py` is next to `app.py` in the repository root**.

No secrets or API keys are needed. Dependencies are listed in `requirements.txt`. On Streamlit Community Cloud, a public app can be shared with your instructor by URL.

## Run locally (Windows)

Open the project folder in File Explorer, click the address bar, enter `cmd`, then run:

```bat
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

If Windows uses `python` instead of `py`, substitute `python` in both commands. If `streamlit` is not recognized, use `py -m streamlit run app.py` instead of `streamlit run app.py`.

## Tests

The app's pure finance/report functions are tested without running a Streamlit server. Install test dependencies with `py -m pip install pytest pypdf` and run:

```bat
py -m pytest -q
```

## Model assumptions and limitations

- **Fixed-rate loan:** the nominal annual mortgage rate is divided by 12 for the monthly interest rate; extra payments reduce principal immediately; no prepayment fee, missed payment, or bank-specific rounding. Property tax, insurance and PMI appear in the household cash-outflow estimate only, **not** in mortgage amortization or the investing comparison.
- **Investment comparison:** projected fixed **nominal effective annual** investment return, cash flows held constant in nominal terms, gains before investment taxes/fees. All monthly cash allocations are equal between strategies; unused funds from the last installment are immediately invested. Both loans are repaid by standard maturity and property value cancels out. Results are *hypothetical*, not market forecasts. Early debt repayment can improve certainty and reduce risk even if a hypothetical higher-return portfolio wins the calculation.
- **Retirement:** savings, recurring contributions and spending targets are given in today's purchasing power. Constant real contributions and spending imply nominal cash figures grow over time with inflation. Nominal returns are translated into real returns. The initial withdrawal rate (default 4%) is a **heuristic**, not proof savings will last. The earliest modeled eligible age applies a constant-return requirement to spending through the selected planning age; it is **not** a probability of retirement success.
- **Monte Carlo:** independent annual lognormal returns, user-assumed arithmetic nominal mean/volatility, constant inflation; each annual return is spread evenly through its 12 months. It omits taxes, fees, correlation, fat tails, spending changes, pension income, and market regime shifts. The random seed is fixed for reproducibility.
- **Currency:** changing currency selections changes the symbol and initial example numbers, **not** exchange rates or the underlying numeric value.

**Educational tool only — not personalized financial advice.**
