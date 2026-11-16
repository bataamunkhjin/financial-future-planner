"""Risk-aware bank savings versus investing, with honest model limitations.

The bank's contractual/illustrative return is deterministic in the base model;
its interest-rate risk is represented by a separate lower-rate stress scenario.
Investing uses the SAME seeded annual-lognormal market model as the Retirement
Planner. All simulation balances are in today's purchasing power.

This is a scenario comparison, NOT a deposit-insurance determination or
investment recommendation. No taxes, charges, or currency risk are included.
"""
from __future__ import annotations

import math

from finance import monte_carlo_projection
from savings_comparison import compare_bank_and_investment


def one_year_loss_probability(expected_return_pct: float, volatility_pct: float) -> float:
    """P(annual nominal market return < 0) under the planner's lognormal model."""
    mean_factor = 1.0 + float(expected_return_pct) / 100.0
    sigma = float(volatility_pct) / 100.0
    if not math.isfinite(mean_factor) or mean_factor <= 0:
        raise ValueError("Expected return must exceed -100% and be finite.")
    if not math.isfinite(sigma) or sigma < 0:
        raise ValueError("Volatility must be finite and nonnegative.")
    if sigma == 0:
        return 1.0 if mean_factor < 1.0 else 0.0
    sigma_log = math.sqrt(math.log1p((sigma / mean_factor) ** 2))
    mu_log = math.log(mean_factor) - sigma_log ** 2 / 2
    return 0.5 * math.erfc(mu_log / (sigma_log * math.sqrt(2)))


def compare_savings_investing_risks(
    comparison: dict,
    *,
    annual_volatility_pct: float,
    scenarios: int = 1000,
    seed: int = 42,
    bank_rate_drop_pp: float = 2.0,
) -> dict:
    """Create bank rate sensitivity and investing downside distribution.

    Bank rate-drop stress assumes the *lower rate applies over the entire horizon*;
    it does not imply a forecast or that an existing fixed-rate deposit can be
    repriced immediately. The market model samples independent yearly returns
    using arithmetic mean + volatility, with constant inflation.
    """
    vol = float(annual_volatility_pct)
    if not math.isfinite(vol) or vol < 0 or vol > 100:
        raise ValueError("Investment volatility must be between 0% and 100%.")
    if not isinstance(scenarios, int) or not 1 <= scenarios <= 10000:
        raise ValueError("Scenarios must be an integer between 1 and 10000.")
    if not math.isfinite(float(bank_rate_drop_pp)) or bank_rate_drop_pp < 0:
        raise ValueError("Bank interest-rate stress must be nonnegative.")

    bank_rate = float(comparison["bank_rate_pct"])
    expected_return = float(comparison["investing_rate_pct"])
    inflation = float(comparison["inflation_pct"])
    start_age = int(comparison["current_age"])
    retire_age = int(comparison["retirement_age"])
    plan_age = int(comparison["planning_age"])
    bank_low_rate = max(0.0, bank_rate - float(bank_rate_drop_pp))
    stress = compare_bank_and_investment(
        current_age=start_age, retirement_age=retire_age, planning_age=plan_age,
        starting_balance=float(comparison["starting_balance"]),
        monthly_saving=float(comparison["monthly_saving"]),
        monthly_spending=float(comparison["monthly_spending"]),
        bank_rate_pct=bank_low_rate, investing_rate_pct=expected_return,
        inflation_pct=inflation,
    )
    market = monte_carlo_projection(
        current_age=start_age, retirement_age=retire_age, planning_age=plan_age,
        savings=float(comparison["starting_balance"]),
        monthly_contribution=float(comparison["monthly_saving"]),
        monthly_retirement_income=float(comparison["monthly_spending"]),
        expected_nominal_return_pct=expected_return,
        inflation_pct=inflation,
        annual_volatility_pct=vol,
        target_portfolio=0.0, simulations=scenarios, seed=seed,
    )
    fan = market["fan"]
    at_retirement = fan.loc[fan["Age"] == retire_age]
    if len(at_retirement) != 1:
        raise ValueError("Retirement quantiles were not produced.")
    row = at_retirement.iloc[0]
    bank_real_return = (1 + bank_rate / 100.0) / (1 + inflation / 100.0) - 1
    return {
        "bank_real_return_pct": bank_real_return * 100.0,
        "bank_loses_purchasing_power": bank_real_return < -1e-10,
        "bank_lower_rate_pct": bank_low_rate,
        "bank_lower_rate_retirement_balance": stress["retirement_balances"]["Bank"],
        "bank_lower_rate_depletion_age": stress["first_shortfall_ages"]["Bank"],
        "bank_base_retirement_balance": comparison["retirement_balances"]["Bank"],
        "bank_base_sustains": comparison["bank_sustains"],
        "bank_base_depletion_age": comparison["first_shortfall_ages"]["Bank"],
        "bank_lower_rate_sustains": stress["bank_sustains"],
        "bank_interest_stress_difference": (
            comparison["retirement_balances"]["Bank"]
            - stress["retirement_balances"]["Bank"]
        ),
        "invest_one_year_loss_probability": one_year_loss_probability(expected_return, vol),
        "invest_sustain_probability": market["sustain_probability"],
        "invest_p10_at_retirement": float(row["P10"]),
        "invest_median_at_retirement": float(row["Median"]),
        "invest_p90_at_retirement": float(row["P90"]),
        "fan": fan,
        "investment_volatility_pct": vol,
        "scenarios": scenarios,
        "seed": seed,
    }
