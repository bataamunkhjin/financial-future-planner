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
                if before_transaction + 1e-8 < target_monthly_income and depletion_age is None:
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
                depleted |= before_transaction + 1e-8 < monthly_retirement_income
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
