# Financial Future Planner v7.1 — Historical Rate Data

**Munkhjin Bataa | American University of Mongolia**

Two-tab Streamlit app: **Loan Planner** and **Retirement Planner**. Version 7.1 adds a documented, offline historical interest-rate dataset cleaned from nine files supplied for the class project. No internet connection or API key is required.

## What changed

- Under **Loan Planner → Historical interest rates (uploaded dataset)**, explore available annual lending, deposit and central-bank policy rates. The observed lending-rate series can be used to compare a hypothetical loan payment against your chosen loan rate (same principal and term).
- Under **Retirement Planner → Historical deposit and policy rates**, see deposit-rate history where it exists and policy-rate history, alongside the app's current editable bank deposit assumption.
- Both sections include clearly labeled plots, available-year counts, downloads and source/coverage notes. The Loan Planner offers an optional three-region policy-rate comparison.
- Existing user-entered rates, the two main tabs, loan amortization, Monte Carlo, inflation shock, contribution growth, charts and PDF reports are **unchanged**.

## Source data and cleaning

Six ZIPs are **duplicate regional downloads** of two complete World Bank World Development Indicators (WDI) worldwide datasets, rather than six distinct country-level datasets:

- `FR.INR.LEND` — Lending interest rate (%): https://data.worldbank.org/indicator/FR.INR.LEND
- `FR.INR.DPST` — Deposit interest rate (%): https://data.worldbank.org/indicator/FR.INR.DPST

The processing script identified identical contents using SHA-256, retained **Mongolia (MNG), United States (USA), and Euro area (EMU)**, converted wide year columns to yearly observations, and kept missing fields empty rather than filling with zero.

Three further files contain policy-rate observations:

- `policy-interest-rate-mongolia.xlsx`: Bank of Mongolia policy-rate announcement/effective dates, converted from Excel serial dates. https://www.mongolbank.mn/
- `policy-interest-rate-eu.xlsx`: ECB main refinancing operation rate decisions. Grouped years and footnote numbers were cleaned. https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html
- `policy rate us.csv`: a daily US rate series. **Its precise benchmark definition is not stated in the file**, so it is labeled as an *uploaded daily policy-rate proxy*, not an officially verified policy target.

Annual policy-rate averages are **calendar-day-weighted**: the most recent observation is carried forward through each calendar day until the next dated observation. This creates meaningful annual averages from event-change records and a near-daily series. The separate policy-rate series are **not equivalent to retail lending or bank deposit rates**.

All three regions have annual rows for **2000–2025** (78 rows), with blank cells where the source is missing. Policy events from 2026 are retained in the original dated observation file, but 2026 is deliberately excluded from complete-year averages.

### Data availability in the 2000–2025 window

| Region | Lending rates | Deposit rates | Annual policy rates |
|---|---|---|---|
| Mongolia | 2000–2021 (22) | 2000–2021 (22) | 2008–2025 (18) |
| United States | 2000–2021 (22) | No observations | 2000–2025 (26) |
| Euro area | No observations | No observations | 2000–2025 (26) |

**There were no historical inflation files in the nine uploads.** The app's existing MNT/USD/EUR inflation defaults remain **editable assumptions**, not historical estimates. Likewise, the current example loan and deposit defaults are preserved rather than replaced with stale 2021 WDI retail observations or different policy benchmarks.

## Files

| File | Contents |
|---|---|
| `data/historical_rates_annual.csv` | Master wide-format table, one row per region-year (78 rows) |
| `data/historical_rates_long.csv` | Observed values only in tidy format (136 rows) |
| `data/policy_rate_observations.csv` | Dated central-bank and proxy observations (25,593 rows) |
| `data/data_quality.csv` | Available/missing years and data coverage |
| `data/sources_and_definitions.csv` | Definitions and source URLs |
| `data/input_inventory.csv` | Upload inventory, checksums and duplicate handling |
| `Historical_Interest_Rates_Cleaned.xlsx` | Human-readable cleaned workbook (overview, annual rates, quality, definitions) |
| `historical_data.py` | Offline data loading and validation for the app |
| `build_historical_data.py` | Reproducible ETL script (requires supplied `input/` files and `artifact_tool` for XLSX reads) |
| `app.py` | Original planners plus optional historical-analysis sections |
| `finance.py` and `report.py` | Unchanged v7.0 finance models and combined PDF report |
| `tests/test_historical_data.py` | New data-quality and integration regression tests |

## Running and deployment

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
python -m pytest -q tests
```

For Streamlit Community Cloud, ensure `app.py`, `historical_data.py`, and the `data/` CSV files are committed **together** in the exact directory structure. Set the main file path to `app.py`. The app reads the local CSV files; it does **not** download financial datasets at runtime.

## Limitations and appropriate interpretation

Historical country interest rates reflect different definitions across countries and products. An ECB refinancing rate should not be presented as a euro mortgage APR; the US supplied daily rate must not be presented as an official target without verification. Missing annual retail-rate data cannot substantiate a loan offer. A historical annual rate applied to a current loan is a **hypothetical sensitivity scenario**, not a quote or forecast. Nominal savings projections do not include tax, account restrictions, lender fees, or changing interest-rate paths unless the simulation specifically models them.
