"""Pure finance calculations for Financial Future Planner.

Amounts are in an arbitrary currency: changing the currency label does NOT convert
amounts. Retirement balances and contributions are expressed in today's money.
"""

from __future__ import annotations

import calendar
from datetime import date
import math

import numpy as np
import pandas as pd



# Static educational presets, reviewed on 17 November 2026. No external
# requests occur while the Streamlit app runs. The official bank reference
# rates apply to different credit/deposit products; users should enter their
# own bank quote when comparing real offers.
CURRENCY_ASSUMPTIONS = {
    "MNT": {
        "loan_pct": 17.60, "deposit_pct": 11.80,
        "inflation_pct": 9.00,  # User-selected planning assumption; not latest CPI.
        "investment_return_pct": 14.00, "investment_volatility_pct": 20.00,
        "loan_reference": "Bank of Mongolia: bank lending rate, September 2026",
        "deposit_reference": "Bank of Mongolia: new deposit rate, September 2026",
    },
    "USD": {
        "loan_pct": 7.11, "deposit_pct": 1.81,
        "inflation_pct": 3.70,
        "investment_return_pct": 7.00, "investment_volatility_pct": 15.00,
        "loan_reference": "Freddie Mac: US 30-year fixed mortgage, 12 November 2026",
        "deposit_reference": "FDIC: US national 12-month CD average, 16 November 2026",
    },
    "EUR": {
        "loan_pct": 3.62, "deposit_pct": 2.37,
        "inflation_pct": 4.00,
        "investment_return_pct": 7.00, "investment_volatility_pct": 15.00,
        "loan_reference": "ECB: euro-area new house-purchase loans, September 2026",
        "deposit_reference": "ECB: euro-area new agreed-maturity household deposits, September 2026",
    },
}


def currency_assumptions(code: str) -> dict:
    """Return editable starting assumptions for one currency/market.

    Investment returns and volatility are EXAMPLES, not observed statistics.
    They depend on asset allocation, NOT just currency denomination.
    """
    try:
        return CURRENCY_ASSUMPTIONS[code.upper()].copy()
    except (KeyError, AttributeError) as exc:
        raise ValueError("Currency must be MNT, USD, or EUR") from exc


def inflation_shock_presets(baseline_pct: float) -> list[float]:
    """Three increasing inflation shocks relative to the user's baseline."""
    import math
    if not math.isfinite(baseline_pct) or not 0 <= baseline_pct <= 30:
        raise ValueError("Annual inflation baseline must be between 0 and 30%")
    return [round(baseline_pct + delta, 2) for delta in (2.0, 5.0, 9.0)]


def add_months(base: date, months: int) -> date:
    """Add calendar months and clip day-of-month (e.g., Jan 31 -> Feb 28)."""
    month_index = base.year * 12 + base.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    return date(year, month, min(base.day, calendar.monthrange(year, month)[1]))


def loan_payment(principal: float, annual_rate_pct: float, years: int) -> float:
    """Scheduled monthly payment for a fixed-rate, fully amortizing loan."""
    if principal <= 0 or years <= 0 or annual_rate_pct < 0:
        raise ValueError("Loan amount and term must be positive; rate must be >= 0.")
    months = int(years) * 12
    monthly_rate = annual_rate_pct / 1200
    if monthly_rate == 0:
        return principal / months
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** (-months))


def loan_schedule(
    principal: float,
    annual_rate_pct: float,
    years: int,
    extra_monthly: float = 0.0,
    start_date: date | None = None,
) -> pd.DataFrame:
    """Monthly amortization. Extra payments apply to principal, with no prepayment fees."""
    if extra_monthly < 0:
        raise ValueError("Extra monthly payment cannot be negative.")
    if start_date is None:
        start_date = date.today()

    regular = loan_payment(principal, annual_rate_pct, years)
    monthly_rate = annual_rate_pct / 1200
    balance = float(principal)
    cumulative_interest = 0.0
    cumulative_principal = 0.0
    rows = []

    for month in range(1, years * 12 + 1):
        if balance <= 1e-8:
            break
        beginning = balance
        interest = beginning * monthly_rate
        scheduled_paid = min(regular, beginning + interest)
        extra_paid = min(extra_monthly, max(0.0, beginning + interest - scheduled_paid))
        total_payment = scheduled_paid + extra_paid
        principal_paid = total_payment - interest
        balance = max(0.0, beginning - principal_paid)
        cumulative_interest += interest
        cumulative_principal += principal_paid
        payment_date = add_months(start_date, month)
        rows.append(
            {
                "Month": month,
                "Payment Date": payment_date,
                "Year": (month - 1) // 12 + 1,
                "Starting Balance": beginning,
                "Scheduled Payment": scheduled_paid,
                "Extra Payment": extra_paid,
                "Total Payment": total_payment,
                "Principal": principal_paid,
                "Interest": interest,
                "Ending Balance": balance,
                "Cumulative Principal": cumulative_principal,
                "Cumulative Interest": cumulative_interest,
            }
        )
    return pd.DataFrame(rows)


def loan_stats(schedule: pd.DataFrame, original_principal: float) -> dict:
    if schedule.empty:
        raise ValueError("The amortization schedule cannot be empty.")
    return {
        "months": len(schedule),
        "interest": float(schedule["Interest"].sum()),
        "principal": float(schedule["Principal"].sum()),
        "paid": float(schedule["Total Payment"].sum()),
        "payoff_date": schedule["Payment Date"].iloc[-1],
        "interest_to_principal": float(schedule["Interest"].sum()) / original_principal,
    }


def real_monthly_return(annual_return_pct: float, annual_inflation_pct: float) -> float:
    """Return per month in constant purchasing-power units."""
    if annual_return_pct <= -100 or annual_inflation_pct <= -100:
        raise ValueError("Annual return and inflation must each be greater than -100%.")
    return ((1 + annual_return_pct / 100) / (1 + annual_inflation_pct / 100)) ** (1 / 12) - 1


def grow_savings(
    current_savings: float, monthly_contribution: float, months: int, monthly_real_return: float
) -> float:
    """Balance after monthly compounding and end-of-month deposits (today's money)."""
    if months <= 0:
        return float(current_savings)
    growth = (1 + monthly_real_return) ** months
    if abs(monthly_real_return) < 1e-12:
        return current_savings + months * monthly_contribution
    return current_savings * growth + monthly_contribution * (growth - 1) / monthly_real_return


def required_monthly_contribution(
    savings: float,
    months_to_retire: int,
    target_portfolio: float,
    monthly_real_return: float,
) -> float:
    if months_to_retire <= 0:
        return 0.0 if savings >= target_portfolio else math.inf
    growth = (1 + monthly_real_return) ** months_to_retire
    annuity_factor = (
        float(months_to_retire)
        if abs(monthly_real_return) < 1e-12
        else (growth - 1) / monthly_real_return
    )
    return max(0.0, (target_portfolio - savings * growth) / annuity_factor)


def earliest_target_age(
    current_age: int,
    savings: float,
    contribution: float,
    target_portfolio: float,
    monthly_real_return: float,
    max_age: int = 90,
) -> int | None:
    for age in range(current_age, max_age + 1):
        bal = grow_savings(savings, contribution, (age - current_age) * 12, monthly_real_return)
        if bal >= target_portfolio:
            return age
    return None


def retirement_projection(
    current_age: int,
    retirement_age: int,
    planning_age: int,
    savings: float,
    contribution: float,
    target_monthly_income: float,
    annual_return_pct: float,
    annual_inflation_pct: float,
) -> tuple[pd.DataFrame, int | None]:
    """Monthly simulation, summarized at each birthday in today's money.

    Before retirement, contribute a constant REAL amount at the end of each month
    (so the actual nominal contribution would rise with inflation). At and after
    retirement, withdraw constant REAL target income at the end of each month.
    """
    rate = real_monthly_return(annual_return_pct, annual_inflation_pct)
    balance = float(savings)
    contributions = 0.0
    withdrawals = 0.0
    depletion_age = None
    records = [
        {
            "Age": current_age,
            "Balance (today's money)": balance,
            "Cumulative Contributions": contributions,
            "Cumulative Withdrawals": withdrawals,
            "Phase": "Saving" if current_age < retirement_age else "Retired",
        }
    ]
    for age in range(current_age, planning_age):
        for month in range(12):
            before_transaction = balance * (1 + rate)
            if age < retirement_age:
                balance = before_transaction + contribution
                contributions += contribution
            else:
                # A cent-level tolerance avoids a false shortfall in the final
                # payment caused solely by floating-point compounding error.
                if (before_transaction + max(0.01, target_monthly_income * 1e-10)
                        < target_monthly_income and depletion_age is None):
                    depletion_age = age + (month + 1) / 12
                actual_withdrawal = min(before_transaction, target_monthly_income)
                balance = max(0.0, before_transaction - actual_withdrawal)
                withdrawals += actual_withdrawal
        records.append(
            {
                "Age": age + 1,
                "Balance (today's money)": balance,
                "Cumulative Contributions": contributions,
                "Cumulative Withdrawals": withdrawals,
                "Phase": "Saving" if age + 1 < retirement_age else "Retired",
            }
        )
    return pd.DataFrame(records), depletion_age


def monte_carlo_projection(
    current_age: int,
    retirement_age: int,
    planning_age: int,
    savings: float,
    monthly_contribution: float,
    monthly_retirement_income: float,
    expected_nominal_return_pct: float,
    inflation_pct: float,
    annual_volatility_pct: float,
    target_portfolio: float,
    simulations: int = 1000,
    seed: int = 42,
) -> dict:
    """Independent annual lognormal return scenarios, monthly compounding/deposits.

    expected_nominal_return_pct is an arithmetic annual mean, while volatility is
    the standard deviation of annual SIMPLE returns. Inflation is fixed.
    """
    if simulations <= 0 or annual_volatility_pct < 0:
        raise ValueError("Simulation count must be positive and volatility >= 0.")
    mean_multiplier = 1 + expected_nominal_return_pct / 100
    if mean_multiplier <= 0:
        raise ValueError("Expected annual return must exceed -100%.")
    volatility = annual_volatility_pct / 100
    sigma_log = np.sqrt(np.log1p((volatility / mean_multiplier) ** 2))
    mu_log = np.log(mean_multiplier) - 0.5 * sigma_log**2
    inflation_factor = 1 + inflation_pct / 100
    if inflation_factor <= 0:
        raise ValueError("Inflation must exceed -100%.")

    rng = np.random.default_rng(seed)
    years = planning_age - current_age
    paths = np.empty((years + 1, simulations), dtype=float)
    paths[0] = savings
    balances = np.full(simulations, savings, dtype=float)
    depleted = np.zeros(simulations, dtype=bool)

    for year_idx in range(years):
        age = current_age + year_idx
        normal = rng.standard_normal(simulations)
        annual_nominal_factor = np.exp(mu_log + sigma_log * normal)
        monthly_real_factor = (annual_nominal_factor / inflation_factor) ** (1 / 12)
        for _ in range(12):
            before_transaction = balances * monthly_real_factor
            if age < retirement_age:
                balances = before_transaction + monthly_contribution
            else:
                depleted |= (before_transaction + max(0.01, monthly_retirement_income * 1e-10)
                             < monthly_retirement_income)
                balances = np.maximum(0.0, before_transaction - monthly_retirement_income)
        paths[year_idx + 1] = balances

    ret_idx = retirement_age - current_age
    at_retire = paths[ret_idx]
    quantiles = np.percentile(paths, [10, 25, 50, 75, 90], axis=1)
    fan = pd.DataFrame(
        {
            "Age": np.arange(current_age, planning_age + 1),
            "P10": quantiles[0],
            "P25": quantiles[1],
            "Median": quantiles[2],
            "P75": quantiles[3],
            "P90": quantiles[4],
        }
    )
    return {
        "fan": fan,
        "reach_target_probability": float(np.mean(at_retire >= target_portfolio)),
        "sustain_probability": float(np.mean(~depleted)),
        "median_at_retirement": float(np.median(at_retire)),
        "paths_count": simulations,
    }


# -------------------- Financial Future Planner v2 --------------------

def loan_rate_scenarios(
    principal: float,
    annual_rate_pct: float,
    years: int,
    extra_monthly: float,
    start_date: date,
    changes: tuple[float, ...] = (-2.0, -1.0, 0.0, 1.0, 2.0),
) -> pd.DataFrame:
    """Hypothetical *new loan* rates; an existing fixed loan does not reprice."""
    records = []
    for change in changes:
        hypothetical_rate = max(0.0, annual_rate_pct + change)
        schedule = loan_schedule(principal, hypothetical_rate, years, extra_monthly, start_date)
        stats = loan_stats(schedule, principal)
        records.append({
            "Scenario": f"{change:+.0f} pp" if change else "Current rate",
            "Rate (%)": hypothetical_rate,
            "Monthly P&I": loan_payment(principal, hypothetical_rate, years),
            "Total Interest": stats["interest"],
            "Payoff Months": stats["months"],
            "Payoff Date": stats["payoff_date"],
        })
    return pd.DataFrame(records)


def annual_loan_scenario(
    principal: float, annual_rate_pct: float, years: int, extra_monthly: float, start_date: date
) -> pd.DataFrame:
    """Auto-generated payment variations without another user input."""
    payment = loan_payment(principal, annual_rate_pct, years)
    if extra_monthly > 0:
        variations = [
            ("Standard", 0.0),
            ("Half selected extra", extra_monthly * 0.5),
            ("Selected extra", extra_monthly),
            ("Double selected extra", extra_monthly * 2.0),
        ]
    else:
        variations = [
            ("Standard", 0.0),
            ("+5% of scheduled", payment * 0.05),
            ("+10% of scheduled", payment * 0.10),
            ("+20% of scheduled", payment * 0.20),
        ]
    baseline_interest = loan_stats(loan_schedule(principal, annual_rate_pct, years, 0, start_date), principal)["interest"]
    rows = []
    for label, extra in variations:
        stats = loan_stats(loan_schedule(principal, annual_rate_pct, years, extra, start_date), principal)
        rows.append({
            "Scenario": label,
            "Extra / Month": extra,
            "Monthly Budget": payment + extra,
            "Payoff Months": stats["months"],
            "Total Interest": stats["interest"],
            "Interest Saved": baseline_interest - stats["interest"],
            "Payoff Date": stats["payoff_date"],
        })
    return pd.DataFrame(rows)


def drawdown_portfolio_requirement(
    monthly_income: float, months: int, monthly_real_return: float
) -> float:
    """Capital needed for end-of-month real withdrawals through a fixed horizon.

    This is a deterministic annuity present value, not a safe withdrawal estimate.
    """
    if months <= 0 or monthly_income <= 0:
        return 0.0
    if monthly_real_return <= -1:
        raise ValueError("Monthly real return must be greater than -100%.")
    if abs(monthly_real_return) < 1e-12:
        return monthly_income * months
    return monthly_income * (-math.expm1(-months * math.log1p(monthly_real_return))) / monthly_real_return


def earliest_feasible_retirement_age(
    current_age: int,
    planning_age: int,
    current_savings: float,
    monthly_contribution: float,
    monthly_target_income: float,
    monthly_real_return: float,
) -> dict | None:
    """Earliest whole retirement age whose balance funds every modeled withdrawal.

    The post-retirement portfolio continues compounding at the assumed constant
    real rate, while end-of-month spending is paid until the planning age.
    This is a deterministic result, not a probabilistic guarantee.
    """
    if current_age >= planning_age or monthly_target_income < 0:
        raise ValueError("Invalid ages or target monthly income.")
    for age in range(current_age + 1, planning_age):
        months_until = (age - current_age) * 12
        nest_egg = grow_savings(current_savings, monthly_contribution, months_until, monthly_real_return)
        months_retired = (planning_age - age) * 12
        required = drawdown_portfolio_requirement(monthly_target_income, months_retired, monthly_real_return)
        if nest_egg + max(0.01, required * 1e-10) >= required:
            return {"age": age, "portfolio": float(nest_egg), "required_portfolio": float(required)}
    return None

def retirement_what_if_scenarios(
    current_age: int,
    retirement_age: int,
    planning_age: int,
    current_savings: float,
    monthly_contribution: float,
    monthly_target_income: float,
    expected_return_pct: float,
    inflation_pct: float,
    bank_deposit_pct: float | None = None,
) -> pd.DataFrame:
    """One-change-at-a-time scenarios, all using the same monthly drawdown test."""
    configs = [
        ("Base plan", retirement_age, monthly_contribution, expected_return_pct, inflation_pct),
        ("Investment return -2 pp", retirement_age, monthly_contribution, expected_return_pct - 2, inflation_pct),
        ("Investment return +2 pp", retirement_age, monthly_contribution, expected_return_pct + 2, inflation_pct),
        ("Inflation +2 pp", retirement_age, monthly_contribution, expected_return_pct, inflation_pct + 2),
        ("Savings +10%", retirement_age, monthly_contribution * 1.1, expected_return_pct, inflation_pct),
    ]
    if bank_deposit_pct is not None:
        if not math.isfinite(bank_deposit_pct) or not -99.0 < bank_deposit_pct <= 100.0:
            raise ValueError("Bank deposit rate must be finite and between -99 and 100%")
        configs.append(("Bank deposit at reference rate", retirement_age,
                        monthly_contribution, bank_deposit_pct, inflation_pct))
    if retirement_age - 5 > current_age:
        configs.append(("Retire 5 years earlier", retirement_age - 5, monthly_contribution, expected_return_pct, inflation_pct))
    if retirement_age + 5 < planning_age:
        configs.append(("Retire 5 years later", retirement_age + 5, monthly_contribution, expected_return_pct, inflation_pct))
    rows = []
    for label, age, contrib, nominal_return, inflation in configs:
        real = real_monthly_return(nominal_return, inflation)
        balance = grow_savings(current_savings, contrib, (age - current_age) * 12, real)
        retire_months = (planning_age - age) * 12
        target = drawdown_portfolio_requirement(monthly_target_income, retire_months, real)
        unit_target = drawdown_portfolio_requirement(1, retire_months, real)
        rows.append({
            "Scenario": label,
            "Retirement Age": age,
            "Monthly Savings": contrib,
            "Return (%)": nominal_return,
            "Inflation (%)": inflation,
            "Portfolio": balance,
            "Capital Needed": target,
            "Surplus / Shortfall": balance - target,
            "Sustainable Monthly Income": balance / unit_target if unit_target else 0.0,
            "Funds Spending": bool(balance + max(0.01, target * 1e-10) >= target),
        })
    return pd.DataFrame(rows)

def compare_mortgage_vs_investing(
    principal: float,
    mortgage_rate_pct: float,
    years: int,
    extra_monthly_budget: float,
    investment_return_pct: float,
    start_date: date | None = None,
) -> dict:
    """Same fixed cash budget, two strategies, to scheduled mortgage maturity.

    A: make only scheduled payments, invest the remaining cash each month.
    B: pay extra principal until loan payoff, invest all remaining budget afterward.

    Both have *identical total cash outlays* every month. When the final mortgage
    payment is smaller, the unused cash is invested in that same month. Investment
    grows at a fixed effective annual *nominal* return before each end-month deposit.
    Net financial wealth = investment account - remaining debt (property excluded).
    """
    if extra_monthly_budget < 0:
        raise ValueError("Extra monthly budget cannot be negative.")
    if investment_return_pct <= -100:
        raise ValueError("Investment return must be greater than -100%.")
    payment = loan_payment(principal, mortgage_rate_pct, years)
    budget = payment + extra_monthly_budget
    base = loan_schedule(principal, mortgage_rate_pct, years, 0.0, start_date)
    accelerated = loan_schedule(principal, mortgage_rate_pct, years, extra_monthly_budget, start_date)
    n = years * 12
    monthly_factor = (1.0 + investment_return_pct / 100) ** (1.0 / 12)
    invest_balance, paydown_balance = 0.0, 0.0
    records = [{
        "Month": 0,
        "Invest Strategy Portfolio": 0.0,
        "Prepay Strategy Portfolio": 0.0,
        "Invest Strategy Debt": principal,
        "Prepay Strategy Debt": principal,
        "Invest Strategy Net Wealth": -principal,
        "Prepay Strategy Net Wealth": -principal,
    }]
    for i in range(n):
        regular_paid = float(base.iloc[i]["Total Payment"]) if i < len(base) else 0.0
        extra_paid = float(accelerated.iloc[i]["Total Payment"]) if i < len(accelerated) else 0.0
        invest_balance = invest_balance * monthly_factor + max(0.0, budget - regular_paid)
        paydown_balance = paydown_balance * monthly_factor + max(0.0, budget - extra_paid)
        regular_debt = float(base.iloc[i]["Ending Balance"]) if i < len(base) else 0.0
        prepay_debt = float(accelerated.iloc[i]["Ending Balance"]) if i < len(accelerated) else 0.0
        records.append({
            "Month": i + 1,
            "Invest Strategy Portfolio": invest_balance,
            "Prepay Strategy Portfolio": paydown_balance,
            "Invest Strategy Debt": regular_debt,
            "Prepay Strategy Debt": prepay_debt,
            "Invest Strategy Net Wealth": invest_balance - regular_debt,
            "Prepay Strategy Net Wealth": paydown_balance - prepay_debt,
        })
    table = pd.DataFrame(records)
    diff = invest_balance - paydown_balance
    threshold = (1 + mortgage_rate_pct / 1200) ** 12 * 100 - 100
    return {
        "monthly_budget": budget,
        "comparison_extra": extra_monthly_budget,
        "invest_portfolio": invest_balance,
        "prepay_portfolio": paydown_balance,
        "difference": diff,
        "winner": "Invest extra" if diff > 0.01 else "Prepay loan" if diff < -0.01 else "Approximately tied",
        "breakeven_effective_annual_pct": threshold,
        "interest_saved_by_prepaying": float(base["Interest"].sum() - accelerated["Interest"].sum()),
        "table": table,
        "horizon_months": n,
    }

# -------------------- Financial Future Planner v3 --------------------

def loan_payoff_milestones(schedule: pd.DataFrame, original_principal: float) -> pd.DataFrame:
    """First payment at which 25%, 50%, 75%, and 100% is repaid.

    Uses cumulative principal, never total repayments, so the percentage does not
    overstate progress on high-interest loans.
    """
    if schedule.empty or original_principal <= 0:
        raise ValueError("A positive loan and a nonempty schedule are required.")
    rows = []
    for share in (0.25, 0.50, 0.75, 1.0):
        mask = schedule["Cumulative Principal"] >= original_principal * share - 1e-6
        if not bool(mask.any()):
            raise ValueError(f"Loan does not reach {share:.0%} payoff.")
        row = schedule.loc[mask].iloc[0]
        rows.append({
            "Loan Repaid": f"{share:.0%}",
            "Payment Month": int(row["Month"]),
            "Payment Date": row["Payment Date"],
            "Principal Repaid": float(row["Cumulative Principal"]),
            "Balance Remaining": float(row["Ending Balance"]),
        })
    return pd.DataFrame(rows)


def simulated_lifetime_savings_goal(
    current_age: int,
    retirement_age: int,
    planning_age: int,
    current_savings: float,
    monthly_contribution: float,
    monthly_retirement_income: float,
    expected_nominal_return_pct: float,
    inflation_pct: float,
    annual_volatility_pct: float,
    simulations: int = 1000,
    target_probability: float = 0.80,
    seed: int = 42,
) -> dict:
    """Minimum real monthly saving for a specified *lifetime funding* probability.

    Returns across the complete pre- and post-retirement horizon are sampled once.
    Each simulated path defines:
       balance at retirement = initial_savings * A + monthly_contribution * B
       minimum required capital = PV of every retirement withdrawal on that path
    Solve for the smallest contribution that succeeds on each path, then select
    the target quantile. This measures paying *every* retirement withdrawal,
    not simply reaching a generic withdrawal-rule balance at retirement.

    Uses the same random draw sequence, fixed inflation and lognormal return
    assumptions as monte_carlo_projection, for comparable probabilities.
    """
    if not (0 < target_probability < 1):
        raise ValueError("Target probability must lie strictly between 0 and 1.")
    if not (current_age < retirement_age < planning_age) or simulations < 1:
        raise ValueError("Require current age < retirement age < planning age and simulations >= 1.")
    if min(current_savings, monthly_contribution, monthly_retirement_income) < 0:
        raise ValueError("Amounts must be nonnegative.")
    if annual_volatility_pct < 0 or expected_nominal_return_pct <= -100 or inflation_pct <= -100:
        raise ValueError("Investment assumptions are out of range.")

    mean_factor = 1 + expected_nominal_return_pct / 100.0
    sigma_log = np.sqrt(np.log1p((annual_volatility_pct / 100.0 / mean_factor) ** 2))
    mu_log = np.log(mean_factor) - 0.5 * sigma_log**2
    inflation_factor = 1 + inflation_pct / 100.0
    rng = np.random.default_rng(seed)
    years = planning_age - current_age
    retirement_idx = retirement_age - current_age
    annual_real_factors = np.vstack([
        np.exp(mu_log + sigma_log * rng.standard_normal(simulations)) / inflation_factor
        for _ in range(years)
    ])

    accumulation = np.ones(simulations)
    annuity = np.zeros(simulations)
    for year in range(retirement_idx):
        monthly_factor = annual_real_factors[year] ** (1 / 12)
        for _ in range(12):
            accumulation *= monthly_factor
            annuity = annuity * monthly_factor + 1.0

    # Work backward to determine capital needed at retirement for every path.
    # Returns are positive multipliers, so funding all withdrawals is equivalent
    # to funding their discounted present value at retirement.
    required_at_retirement = np.zeros(simulations)
    for year in range(years - 1, retirement_idx - 1, -1):
        monthly_factor = annual_real_factors[year] ** (1 / 12)
        for _ in range(12):
            required_at_retirement = (required_at_retirement + monthly_retirement_income) / monthly_factor

    base_at_retirement = current_savings * accumulation
    needed_each_path = (required_at_retirement - base_at_retirement) / annuity
    monthly_needed = max(0.0, float(np.quantile(needed_each_path, target_probability, method="higher")))
    monthly_needed = float(np.nextafter(monthly_needed, np.inf)) if monthly_needed > 0 else 0.0
    tolerance = np.maximum(0.01, required_at_retirement * 1e-10)
    current_probability = float(np.mean(base_at_retirement + monthly_contribution * annuity + tolerance >= required_at_retirement))
    achieved_probability = float(np.mean(base_at_retirement + monthly_needed * annuity + tolerance >= required_at_retirement))

    return {
        "probability_target": target_probability,
        "monthly_contribution_needed": monthly_needed,
        "monthly_increase_needed": max(0.0, monthly_needed - monthly_contribution),
        "current_sustain_probability": current_probability,
        "achieved_probability": achieved_probability,
        "simulations": simulations,
    }

def mortgage_investing_return_scenarios(
    principal: float,
    mortgage_rate_pct: float,
    years: int,
    extra_monthly_budget: float,
    expected_nominal_return_pct: float,
    start_date: date | None = None,
) -> pd.DataFrame:
    """Fixed-return stress tests of the same-cash-budget prepay-vs-invest comparison.

    They are NOT market forecasts, and do not imply risk-free investment returns.
    """
    breakeven = ((1 + mortgage_rate_pct / 1200) ** 12 - 1) * 100
    candidates = [
        ("Zero investment growth", 0.0),
        ("Return -3 percentage points", max(-99.0, expected_nominal_return_pct - 3)),
        ("Entered return assumption", expected_nominal_return_pct),
        ("Return +3 percentage points", expected_nominal_return_pct + 3),
        ("Loan return break-even", breakeven),
    ]
    rows = []
    for label, assumed_return in candidates:
        result = compare_mortgage_vs_investing(
            principal, mortgage_rate_pct, years, extra_monthly_budget,
            assumed_return, start_date,
        )
        rows.append({
            "Scenario": label,
            "Investment Return (%)": float(assumed_return),
            "Invest Final": result["invest_portfolio"],
            "Prepay Final": result["prepay_portfolio"],
            "Invest - Prepay": result["difference"],
            "Favored Strategy": result["winner"],
        })
    return pd.DataFrame(rows)

# -------------------- Financial Future Planner v4 --------------------

def retirement_life_schedule(
    starting_portfolio: float,
    retirement_age: int,
    planning_age: int,
    monthly_spending: float,
    annual_nominal_return_pct: float,
    inflation_pct: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Month-by-month drawdown after retirement, summarized into retirement years.

    Returns are credited before each end-of-month withdrawal. All currency amounts
    are in today's purchasing power; contributions STOP at the retirement age.
    Unfunded withdrawals remain visible as a shortfall, never a negative balance.
    """
    if not (retirement_age < planning_age):
        raise ValueError("The planning age must exceed the retirement age.")
    if starting_portfolio < 0 or monthly_spending < 0:
        raise ValueError("The starting portfolio and spending must be nonnegative.")
    rate = real_monthly_return(annual_nominal_return_pct, inflation_pct)
    balance = float(starting_portfolio)
    total_withdrawn = 0.0
    monthly_rows, annual_rows = [], []
    for year in range(planning_age - retirement_age):
        age = retirement_age + year
        annual_start = balance
        annual_growth = 0.0
        actual_paid = 0.0
        annual_shortfall = 0.0
        for m in range(1, 13):
            beginning = balance
            growth = beginning * rate
            available = max(0.0, beginning + growth)
            withdrawn = min(available, monthly_spending)
            unpaid = max(0.0, monthly_spending - withdrawn)
            # Ignore cent-level discrepancies from float accumulation.
            if unpaid <= max(0.01, monthly_spending * 1e-10):
                unpaid = 0.0
            balance = max(0.0, available - withdrawn)
            total_withdrawn += withdrawn
            annual_growth += growth
            actual_paid += withdrawn
            annual_shortfall += unpaid
            monthly_rows.append({
                "Retirement Month": year * 12 + m,
                "Age": age + m / 12,
                "Beginning Balance": beginning,
                "Investment Growth": growth,
                "Planned Spending": monthly_spending,
                "Actual Withdrawal": withdrawn,
                "Unfunded Spending": unpaid,
                "Ending Balance": balance,
            })
        annual_rows.append({
            "Age": age + 1,
            "Starting Balance": annual_start,
            "Investment Growth": annual_growth,
            "Planned Spending": 12 * monthly_spending,
            "Actual Withdrawals": actual_paid,
            "Unfunded Spending": annual_shortfall,
            "Ending Balance": balance,
            "Cumulative Withdrawals": total_withdrawn,
        })
    return pd.DataFrame(monthly_rows), pd.DataFrame(annual_rows)


def inflation_purchasing_power(
    retirement_projection_df: pd.DataFrame,
    current_age: int,
    target_monthly_spending: float,
    annual_inflation_pct: float,
) -> pd.DataFrame:
    """Show constant-real values versus nominal future-money equivalents.

    Real portfolios and real spending are in purchasing power as of current_age.
    Nominal figures use a fixed inflation assumption, not currency conversion.
    """
    if current_age < 0 or target_monthly_spending < 0 or annual_inflation_pct <= -100:
        raise ValueError("Invalid age, spending, or inflation.")
    ages = retirement_projection_df["Age"].to_numpy(dtype=float)
    if len(ages) == 0 or np.any(ages < current_age):
        raise ValueError("The retirement projection must start at or after current age.")
    real_portfolio = retirement_projection_df["Balance (today's money)"].to_numpy(dtype=float)
    nominal_factor = np.power(1 + annual_inflation_pct / 100, ages - current_age)
    return pd.DataFrame({
        "Age": ages.astype(int),
        "Years from Today": (ages - current_age).astype(int),
        "Inflation Multiplier": nominal_factor,
        "Portfolio - Today's Money": real_portfolio,
        "Portfolio - Future Money": real_portfolio * nominal_factor,
        "Monthly Spending - Today's Money": np.full(len(ages), target_monthly_spending),
        "Monthly Spending - Future Money": target_monthly_spending * nominal_factor,
        "Purchasing Power of One Nominal Unit": 1.0 / nominal_factor,
    })


def model_supported_monthly_spending(
    current_age: int,
    retirement_age: int,
    planning_age: int,
    current_savings: float,
    monthly_contribution: float,
    monthly_target_income: float,
    expected_nominal_return_pct: float,
    inflation_pct: float,
    annual_volatility_pct: float,
    simulations: int = 1000,
    target_probabilities: tuple[float, ...] = (0.80, 0.90, 0.95),
    seed: int = 42,
) -> dict:
    """Find model-supported spending at a stated *simulated* success frequency.

    Each path is sampled exactly as in monte_carlo_projection with the same seed.
    After accumulating before retirement, compute the present value at retirement
    of one real unit withdrawn at the end of each retirement month. The maximum
    affordable constant-real withdrawal for a path is nest_egg / unit_annuity.
    Sort path limits to return conservative empirical 80%, 90%, 95% thresholds.
    These are scenario-model thresholds, not guarantees or investment advice.
    """
    if not (current_age < retirement_age < planning_age):
        raise ValueError("Require current age < retirement age < planning age.")
    if min(current_savings, monthly_contribution, monthly_target_income) < 0:
        raise ValueError("Savings, contributions, and spending must be nonnegative.")
    if not (1 <= simulations <= 100000) or annual_volatility_pct < 0:
        raise ValueError("Invalid simulation count or volatility.")
    if expected_nominal_return_pct <= -100 or inflation_pct <= -100:
        raise ValueError("Rates must be greater than -100%.")
    if any(p <= 0 or p > 1 for p in target_probabilities):
        raise ValueError("Success targets must be in (0, 1].")

    multiplier = 1 + expected_nominal_return_pct / 100.0
    vol = annual_volatility_pct / 100.0
    sigma_log = np.sqrt(np.log1p((vol / multiplier) ** 2))
    mu_log = np.log(multiplier) - 0.5 * sigma_log**2
    inflation_factor = 1 + inflation_pct / 100.0
    rng = np.random.default_rng(seed)
    savings = np.full(simulations, current_savings, dtype=float)
    discount = np.ones(simulations, dtype=float)
    unit_annuity = np.zeros(simulations, dtype=float)
    at_retirement = None

    for age in range(current_age, planning_age):
        annual_factor = np.exp(mu_log + sigma_log * rng.standard_normal(simulations))
        monthly_factor = (annual_factor / inflation_factor) ** (1 / 12)
        if age < retirement_age:
            for _ in range(12):
                savings = savings * monthly_factor + monthly_contribution
            if age == retirement_age - 1:
                at_retirement = savings.copy()
        else:
            for _ in range(12):
                discount = discount / monthly_factor
                unit_annuity += discount

    if at_retirement is None:
        raise RuntimeError("Retirement accumulation failed.")
    capacities = at_retirement / unit_annuity
    sorted_capacities = np.sort(capacities)
    options = []
    for prob in target_probabilities:
        count_required = math.ceil(prob * simulations)
        # At this order statistic at least ceil(prob*N) paths support spending.
        index = simulations - count_required
        amount = float(sorted_capacities[index])
        options.append({
            "Success Target": prob,
            "Monthly Spending": amount,
            "Simulated Success": float(np.mean(capacities >= amount - max(0.01, amount * 1e-10))),
        })
    current_success = float(np.mean(capacities + max(0.01, monthly_target_income * 1e-10) >= monthly_target_income))
    return {
        "options": pd.DataFrame(options),
        "current_spending_success": current_success,
        "capacities": capacities,
        "median_retirement_balance": float(np.median(at_retirement)),
        "simulations": simulations,
    }


# -------------------- Financial Future Planner v5.9 --------------------

def inflation_shock_projection(
    current_age: int,
    retirement_age: int,
    planning_age: int,
    starting_portfolio_real: float,
    monthly_spending_real: float,
    annual_nominal_return_pct: float,
    baseline_inflation_pct: float,
    shock_inflation_pct: float,
    shock_years: int = 5,
) -> dict:
    """Compare baseline inflation with a temporary higher-inflation retirement shock.

    The *shock starts at retirement* and persists for ``shock_years``; after
    that, inflation returns to the baseline rate. Before retirement the two
    scenarios are identical. The investment's NOMINAL return stays constant.
    Real contributions stop at retirement; real planned withdrawals continue
    each month and are inflation-indexed in nominal currency.

    Real portfolio balances are expressed in purchasing power as of current_age.
    Nominal spending is expressed in actual future money: inflation from
    current_age to retirement is included at the baseline rate in both paths.
    Returns are credited before an end-of-month withdrawal, consistent with
    ``retirement_life_schedule`` and ``retirement_projection``.

    This is an illustrative deterministic stress test, not a forecast or a
    Monte Carlo probability calculation.
    """
    import math

    if not (0 <= current_age < retirement_age < planning_age):
        raise ValueError("Require current_age < retirement_age < planning_age.")
    if not math.isfinite(starting_portfolio_real) or starting_portfolio_real < 0:
        raise ValueError("Starting portfolio must be a nonnegative finite amount.")
    if not math.isfinite(monthly_spending_real) or monthly_spending_real < 0:
        raise ValueError("Monthly spending must be a nonnegative finite amount.")
    rates = (annual_nominal_return_pct, baseline_inflation_pct, shock_inflation_pct)
    if not all(math.isfinite(x) and -100 < x <= 100 for x in rates):
        raise ValueError("Annual return/inflation rates must be finite and greater than -100%.")
    if not isinstance(shock_years, int) or not 1 <= shock_years <= planning_age - retirement_age:
        raise ValueError("Shock years must be a positive whole number within retirement.")

    monthly_base_return = real_monthly_return(annual_nominal_return_pct, baseline_inflation_pct)
    monthly_shock_return = real_monthly_return(annual_nominal_return_pct, shock_inflation_pct)
    monthly_baseline_cpi = (1 + baseline_inflation_pct / 100) ** (1 / 12)
    monthly_shock_cpi = (1 + shock_inflation_pct / 100) ** (1 / 12)
    # Both futures start at the same forecast portfolio in CURRENT purchasing power.
    base_balance = stressed_balance = float(starting_portfolio_real)
    # Price levels, measured relative to TODAY, not retirement day.
    pre_retirement_price_level = (1 + baseline_inflation_pct / 100) ** (retirement_age - current_age)
    base_cpi = stressed_cpi = pre_retirement_price_level
    shortage_base = shortage_stressed = 0.0
    depleted_base = depleted_stressed = None
    months = (planning_age - retirement_age) * 12
    shock_months = shock_years * 12
    rows = [{
        "Age": float(retirement_age),
        "Base balance (today's money)": base_balance,
        "Shock balance (today's money)": stressed_balance,
        "Base monthly spending (nominal)": monthly_spending_real * base_cpi,
        "Shock monthly spending (nominal)": monthly_spending_real * stressed_cpi,
        "Cumulative base shortfall (real)": 0.0,
        "Cumulative shock shortfall (real)": 0.0,
    }]
    monthly_rows = []
    for month in range(1, months + 1):
        under_shock = month <= shock_months
        stressed_rate = monthly_shock_return if under_shock else monthly_base_return
        stressed_cpi *= monthly_shock_cpi if under_shock else monthly_baseline_cpi
        base_cpi *= monthly_baseline_cpi

        available_base = max(0.0, base_balance * (1 + monthly_base_return))
        available_stress = max(0.0, stressed_balance * (1 + stressed_rate))
        unpaid_base = max(0.0, monthly_spending_real - available_base)
        unpaid_stressed = max(0.0, monthly_spending_real - available_stress)
        epsilon = max(0.01, monthly_spending_real * 1e-10)
        if unpaid_base <= epsilon:
            unpaid_base = 0.0
        if unpaid_stressed <= epsilon:
            unpaid_stressed = 0.0
        if unpaid_base > 0.0 and depleted_base is None:
            depleted_base = retirement_age + month / 12
        if unpaid_stressed > 0.0 and depleted_stressed is None:
            depleted_stressed = retirement_age + month / 12
        base_balance = max(0.0, available_base - min(available_base, monthly_spending_real))
        stressed_balance = max(0.0, available_stress - min(available_stress, monthly_spending_real))
        shortage_base += unpaid_base
        shortage_stressed += unpaid_stressed
        monthly_rows.append({
            "Retirement Month": month,
            "Age": retirement_age + month / 12,
            "Inflation in shock path (%)": shock_inflation_pct if under_shock else baseline_inflation_pct,
            "Base balance (today's money)": base_balance,
            "Shock balance (today's money)": stressed_balance,
            "Base monthly spending (nominal)": monthly_spending_real * base_cpi,
            "Shock monthly spending (nominal)": monthly_spending_real * stressed_cpi,
            "Base unfunded spending (real)": unpaid_base,
            "Shock unfunded spending (real)": unpaid_stressed,
        })
        if month % 12 == 0:
            rows.append({
                "Age": float(retirement_age + month / 12),
                "Base balance (today's money)": base_balance,
                "Shock balance (today's money)": stressed_balance,
                "Base monthly spending (nominal)": monthly_spending_real * base_cpi,
                "Shock monthly spending (nominal)": monthly_spending_real * stressed_cpi,
                "Cumulative base shortfall (real)": shortage_base,
                "Cumulative shock shortfall (real)": shortage_stressed,
            })
    return {
        "yearly": pd.DataFrame(rows),
        "monthly": pd.DataFrame(monthly_rows),
        "baseline_depletion_age": depleted_base,
        "shock_depletion_age": depleted_stressed,
        "baseline_ending_balance": base_balance,
        "shock_ending_balance": stressed_balance,
        "baseline_total_shortfall": shortage_base,
        "shock_total_shortfall": shortage_stressed,
        "baseline_end_monthly_nominal_spending": monthly_spending_real * base_cpi,
        "shock_end_monthly_nominal_spending": monthly_spending_real * stressed_cpi,
        "shock_annual_inflation_pct": shock_inflation_pct,
        "baseline_annual_inflation_pct": baseline_inflation_pct,
        "shock_duration_years": shock_years,
        "shock_start_age": retirement_age,
        "shock_end_age": retirement_age + shock_years,
    }
