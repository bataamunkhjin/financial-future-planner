# Financial Future Planner v3

A GitHub-ready two-tab Streamlit app for a finance class and personal portfolio. **Four required loan inputs + five required retirement inputs**; all other settings are optional and tucked inside expandable sections. No sign-in, bank connection, API key, or paid service.

## What the app does

### Mortgage / Loan Planner
- Calculates fixed-rate monthly payment, scheduled versus accelerated payoff, total interest, and detailed amortization tables.
- Generates automatic extra-payment and loan-rate what-if scenarios; rate changes are **hypothetical new-loan quotes**, not repricing an existing fixed loan.
- **New in v3:** Shows the payment month/date at which **25%, 50%, 75%, and 100%** of the original principal has been repaid.
- Compares prepaying the mortgage with investing spare cash, using the **same monthly budget and loan maturity** for both strategies.
- **New in v3:** Fixed-return investment stress tests (0%, assumed -3 percentage points, assumed return, assumed +3 points, mortgage break-even return).
- Charts, insights, CSV schedule downloads, and a PDF summary.

### Retirement Planner
- Models saving and retirement spending in **today's purchasing power**.
- Calculates projected portfolio, 4%-rule-style target with editable initial withdrawal rate, surplus or shortfall, and needed monthly contribution.
- Finds earliest *modeled* eligible retirement age, checks both a withdrawal-rule target and a deterministic spending requirement; not a retirement guarantee.
- Monte Carlo fan chart and separate probabilities for reaching the portfolio target and sustaining monthly spending through the planning age.
- **New in v3:** Estimates real monthly contributions required to reach the initial withdrawal-rule portfolio target in **approximately 80% of illustrative simulated return paths**, reusing existing inputs. This is **not** 80% probability of sustaining retirement spending.
- Auto what-if comparisons, downloadable CSVs, and PDF reporting.

### Classroom-friendly additions
- **New in v3:** Expandable **“Understand the calculations”** sections in each tab, explaining loan amortization, the real-return formula, and Monte Carlo simulation.
- **New in v3:** `TEACHER_GUIDE.md` includes a four-minute live demonstration and explanation of every source file.
- **New in v3:** `.github/workflows/tests.yml` automatically runs finance tests after commits/PRs when enabled on GitHub Actions.
- Combined PDF includes all new results and works offline without custom font files or paid services.

## Project files

```text
app.py                         Streamlit UI and charts
finance.py                     Independent finance calculations
report.py                      PDF generator
requirements.txt               Packages installed by Streamlit Cloud
README.md                      Project overview and setup
TEACHER_GUIDE.md               Presentation walkthrough and formulas
.streamlit/config.toml         Theme settings
.github/workflows/tests.yml    GitHub Actions test workflow
tests/test_finance.py          Loan and retirement baseline tests
tests/test_features.py         v2 scenarios and report tests
tests/test_v3.py               New v3 feature tests
tests/smoke_app_mock.py        Simulated app interaction, no Streamlit needed
```

## Publish updates to GitHub

1. Extract the ZIP. Open the resulting project folder.
2. In your existing GitHub repository, upload the **contents** of the folder, keeping `app.py` and `requirements.txt` at the repository root. Replace existing files when prompted.
3. Keep the `.streamlit` folder at the root for theme settings. Keep `.github/workflows/tests.yml` for automated tests if your repository accepts workflows. GitHub's web upload may require creating/editing nested files separately; GitHub Desktop or Cursor Git integration is easier for full-folder updates.
4. Commit your changes to the branch Streamlit deploys (usually `main`).
5. Open your existing Streamlit site; a successful GitHub commit should trigger a new deployment. If it doesn't, check Streamlit Cloud logs and the selected branch/main file.

To create a new Streamlit Community Cloud app: go to https://share.streamlit.io, select your GitHub repository, branch, and `app.py` as the main file. Public deployments can be shared with a teacher via URL.

## Local installation with Cursor (Windows)

1. Install Python 3.11 or 3.12 and Cursor.
2. In Cursor: **File → Open Folder**, select this extracted project folder.
3. Open **Terminal → New Terminal**, run:

```bat
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

If `py` is unavailable, use `python -m ...`. The browser opens at `http://localhost:8501`.

## Run the tests

```bat
py -m pip install pytest pypdf
py -m pytest -q
```

`tests/smoke_app_mock.py` also exercises both currency choices and confirms the PDF can be generated without a real Streamlit browser session. To run it:

```bat
py tests/smoke_app_mock.py
```

## Financial modeling assumptions

- **Mortgage:** fixed nominal annual interest divided by 12, first payment one month after start, immediate principal reduction from extra payments, no bank-specific rounding, escrow adjustments, lender charges, penalties or missed payments. Tax/insurance/PMI add to monthly household outflow only; they don't change principal or interest computations.
- **Mortgage vs investing:** same nominal monthly cash budget, same mortgage, same end date (original maturity). Market returns are shown as fixed-return what-if cases and exclude investment taxes and fees. Paying down debt reduces interest with much greater certainty than investment returns.
- **Retirement inputs:** current savings, monthly contributions, and target spending are constant in **today's money**; real return comes from nominal investment return and inflation assumptions. Actual nominal contributions/spending would rise with inflation.
- **Retirement eligibility:** uses a heuristic withdrawal rate and a constant-return spending present value test, not a guarantee or a simulation outcome.
- **Retirement Monte Carlo:** independent annual lognormal return factors with a user-specified arithmetic expected return and volatility; inflation is fixed. Each annual return is spread across the year's 12 months. Ignores taxes, fees, correlation, regime changes, and pensions. Seed fixed to make class demos reproducible.
- **80% savings target:** an illustrative **probability of reaching the initial withdrawal-rule portfolio at retirement**. It is *not* a 80% chance the money lasts through the chosen planning age. Use the separate sustain probability for that question.
- **Currency:** USD, EUR, MNT selectors change display symbols and example starting amounts; they do **not** perform exchange conversion. PDFs use ISO `MNT` instead of the tugrik symbol for reliable PDF font rendering.

**For education and scenario analysis, not personalized financial advice.**
