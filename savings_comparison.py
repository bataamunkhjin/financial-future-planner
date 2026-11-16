"""Bank savings vs investing over a shared retirement timeline.

All deposits, withdrawals, and portfolio balances are in CURRENT purchasing-power
currency. The nominal estimates are these same balances grown by assumed inflation.
The bank and investment paths share the same starting balance, contributions,
retirement age, withdrawal target and planning horizon. The only difference is
assumed nominal annual return; neither path is a guaranteed forecast.
"""
from __future__ import annotations

import math
import pandas as pd
from finance import real_monthly_return


def _valid_nonnegative(name: str, value: float) -> float:
    try:
        val = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric.") from exc
    if not math.isfinite(val) or val < 0:
        raise ValueError(f"{name} cannot be negative or non-finite.")
    return val


def compare_bank_and_investment(*, current_age: int, retirement_age: int,
                                planning_age: int, starting_balance: float,
                                monthly_saving: float, monthly_spending: float,
                                bank_rate_pct: float, investing_rate_pct: float,
                                inflation_pct: float) -> dict:
    """Monthly return-then-cashflow model; withdrawals never exceed available funds.

    Uses the same real-monthly-return and end-of-month contribution/withdrawal
    conventions as the Retirement tab. A failed withdrawal records the first
    depletion age; no artificial negative balance or post-depletion recovery.
    """
    ages = (int(current_age), int(retirement_age), int(planning_age))
    if ages[0] < 0 or not (ages[0] < ages[1] < ages[2]) or ages[2] > 120:
        raise ValueError("Choose current age < retirement age < planning age <= 120.")
    starting_balance = _valid_nonnegative("Starting savings", starting_balance)
    monthly_saving = _valid_nonnegative("Monthly savings", monthly_saving)
    monthly_spending = _valid_nonnegative("Monthly spending", monthly_spending)
    if not all(math.isfinite(float(v)) and -99 < float(v) <= 100 for v in
               [bank_rate_pct, investing_rate_pct, inflation_pct]):
        raise ValueError("Annual rates must be finite and between -99% and 100%.")

    bank_real_rate = real_monthly_return(bank_rate_pct, inflation_pct)
    invest_real_rate = real_monthly_return(investing_rate_pct, inflation_pct)
    rates = {"Bank": bank_real_rate, "Investing": invest_real_rate}
    balances = {"Bank": starting_balance, "Investing": starting_balance}
    shortfalls = {"Bank": 0.0, "Investing": 0.0}
    first_shortfall = {"Bank": None, "Investing": None}
    retire_balances = {}
    months_to_retirement = (ages[1]-ages[0])*12
    total_months = (ages[2]-ages[0])*12
    rows = [{"Age": float(ages[0]), "Phase": "Saving", 
             "Bank real": starting_balance, "Investing real": starting_balance,
             "Bank nominal": starting_balance, "Investing nominal": starting_balance}]

    for month in range(1, total_months + 1):
        saving = month <= months_to_retirement
        for label, rate in rates.items():
            available = max(0.0, balances[label]*(1+rate))
            if saving:
                balances[label] = available + monthly_saving
            else:
                paid = min(available, monthly_spending)
                unpaid = max(0.0, monthly_spending-paid)
                if unpaid > 1e-6:
                    if first_shortfall[label] is None:
                        first_shortfall[label] = ages[0]+month/12
                    shortfalls[label] += unpaid
                balances[label] = max(0.0, available-paid)
        if month == months_to_retirement:
            retire_balances = balances.copy()
        if month % 12 == 0:
            age = ages[0]+month/12
            multiplier = (1+inflation_pct/100) ** (month/12)
            rows.append({
                "Age": float(age),
                "Phase": "Saving" if month <= months_to_retirement else "Retired",
                "Bank real": balances["Bank"], "Investing real": balances["Investing"],
                "Bank nominal": balances["Bank"]*multiplier,
                "Investing nominal": balances["Investing"]*multiplier,
            })
    return {
        "annual": pd.DataFrame(rows),
        "retirement_balances": retire_balances,
        "ending_balances": balances.copy(),
        "shortfalls": shortfalls,
        "first_shortfall_ages": first_shortfall,
        "bank_sustains": first_shortfall["Bank"] is None,
        "investment_sustains": first_shortfall["Investing"] is None,
        "bank_rate_pct": float(bank_rate_pct),
        "investing_rate_pct": float(investing_rate_pct),
        "inflation_pct": float(inflation_pct),
        "monthly_spending": monthly_spending,
        "starting_balance": starting_balance,
        "monthly_saving": monthly_saving,
        "retirement_age": ages[1],
        "planning_age": ages[2],
    }
