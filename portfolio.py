"""Offline, assumption-based multi-asset portfolio analysis.

No internet access, market history, or exchange conversion. All monetary
values use the currency selected in the main Streamlit app. The scenario model
is illustrative, not a calibrated portfolio risk or price forecast.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

ASSET_TYPES = (
    "Stock / ETF", "Bond / Bond ETF", "Crypto", "Property / REIT",
    "Gold / Commodity", "Cash / Deposit", "Private investment", "Other",
)


def _amount(value, field, *, optional=False):
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)) or str(value).strip() == "":
        if optional:
            return math.nan
        raise ValueError(f"{field} is required.")
    try:
        amount = float(str(value).replace(",", "").strip())
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be a valid number.") from exc
    if not math.isfinite(amount):
        raise ValueError(f"{field} must be finite.")
    return amount


def analyze_holdings(entries: pd.DataFrame, correlation: float = 0.35) -> tuple[pd.DataFrame, dict]:
    """Value holdings and compute weighted assumption-based expected return/risk.

    Uniform cross-asset correlation is an explicit simplifying assumption,
    NOT an estimated covariance matrix or observed historical correlation.
    """
    required = {"Asset class", "Investment", "Units", "Current price / unit",
                "Avg buy / unit", "Expected return %", "Volatility %"}
    if not required.issubset(entries.columns):
        raise ValueError("The holdings table is missing required columns.")
    if not math.isfinite(correlation) or not 0 <= correlation <= 1:
        raise ValueError("Assumed correlation must be between 0 and 1.")
    rows = []
    for index, entry in entries.iterrows():
        name = str(entry["Investment"] if pd.notna(entry["Investment"]) else "").strip()
        kind = str(entry["Asset class"] if pd.notna(entry["Asset class"]) else "").strip()
        if not name and pd.isna(entry["Units"]):
            continue
        if not name or kind not in ASSET_TYPES:
            raise ValueError(f"Row {index+1}: select an asset class and enter an investment name.")
        units = _amount(entry["Units"], f"Row {index+1} units")
        price = _amount(entry["Current price / unit"], f"Row {index+1} current unit price")
        cost = _amount(entry["Avg buy / unit"], f"Row {index+1} average purchase price", optional=True)
        rate = _amount(entry["Expected return %"], f"Row {index+1} expected return")
        vol = _amount(entry["Volatility %"], f"Row {index+1} volatility")
        if units <= 0 or price <= 0 or (math.isfinite(cost) and cost < 0):
            raise ValueError(f"Row {index+1}: units and current price must be positive; cost cannot be negative.")
        if not -90 <= rate <= 100 or not 0 <= vol <= 150:
            raise ValueError(f"Row {index+1}: expected return must be -90% to 100%, volatility 0% to 150%.")
        value = units * price
        if not math.isfinite(value) or value > 1e18:
            raise ValueError(f"Row {index+1}: investment value is too large.")
        basis = units * cost if math.isfinite(cost) else math.nan
        rows.append({"Asset": name, "Class": kind, "Units": units,
                     "Unit price": price, "Value": value, "Cost basis": basis,
                     "Unrealized P/L": value-basis if math.isfinite(basis) else math.nan,
                     "Expected return %": rate, "Volatility %": vol})
    if not rows:
        raise ValueError("Enter at least one investment.")
    if len(rows) > 30:
        raise ValueError("Use 30 or fewer holdings for a responsive dashboard.")
    positions = pd.DataFrame(rows)
    total = float(positions["Value"].sum())
    w = (positions["Value"] / total).to_numpy()
    sigma = positions["Volatility %"].to_numpy(dtype=float)
    # covariance with a common pairwise correlation; no observed history.
    signed_risk = w * sigma
    variance = (1-correlation) * np.sum(signed_risk**2) + correlation * np.sum(signed_risk)**2
    annual_vol = float(np.sqrt(max(0.0, variance)))
    weighted_return = float(np.dot(w, positions["Expected return %"].to_numpy(dtype=float)))
    positions["Weight %"] = 100.0*w
    costed = positions["Cost basis"].notna()
    summary = {
        "total_value": total,
        "unrealized_profit": float(positions.loc[costed, "Unrealized P/L"].sum()) if costed.any() else math.nan,
        "cost_coverage": float(positions.loc[costed, "Value"].sum())/total,
        "expected_return": weighted_return,
        "modeled_volatility": annual_vol,
        "largest_weight": float(w.max()),
        "hhi": float(np.sum(w**2)),
        "correlation_assumption": float(correlation),
    }
    return positions, summary


def project_portfolio(starting_value: float, annual_return_pct: float,
                      annual_volatility_pct: float, years: int,
                      monthly_contribution: float = 0.0, scenarios: int = 1200,
                      seed: int = 42) -> dict:
    """Monthly end-of-month contributions with fixed-return path + lognormal bands.

    Monthly iid factors are parameterized to reproduce the annual arithmetic
    growth-factor mean and standard deviation implied by the two assumptions.
    Correlations between distinct holdings are summarized at the portfolio level
    by analyze_holdings; this function does not model rebalancing or asset paths.
    """
    vals = [starting_value, annual_return_pct, annual_volatility_pct, monthly_contribution]
    if not all(math.isfinite(float(v)) for v in vals):
        raise ValueError("Projection inputs must be finite.")
    if starting_value <= 0 or monthly_contribution < 0 or not -90 <= annual_return_pct <= 100 or not 0 <= annual_volatility_pct <= 150:
        raise ValueError("Invalid starting value, contribution, annual return, or volatility.")
    if not 1 <= int(years) <= 50 or not 100 <= int(scenarios) <= 5000:
        raise ValueError("Choose 1–50 years and 100–5,000 simulations.")
    years = int(years)
    scenarios = int(scenarios)
    months = years*12
    factor = 1 + float(annual_return_pct)/100
    monthly_fixed = factor**(1/12)
    deterministic = np.empty(months+1, dtype=float)
    deterministic[0] = starting_value
    for i in range(1, months+1):
        deterministic[i] = deterministic[i-1]*monthly_fixed+monthly_contribution
    ratio = float(annual_volatility_pct)/100 / factor
    sigma_y = math.sqrt(math.log1p(ratio**2))
    mu_y = math.log(factor)-sigma_y**2/2
    mu_m = mu_y / 12
    sigma_m = sigma_y / math.sqrt(12)
    rng = np.random.default_rng(seed)
    path = np.full(scenarios, float(starting_value))
    lows = [starting_value]
    mids = [starting_value]
    highs = [starting_value]
    worst_drawdown = np.zeros(scenarios)
    peaks = path.copy()
    for i in range(1, months+1):
        shock = rng.standard_normal(scenarios) if sigma_m else np.zeros(scenarios)
        path = path * np.exp(mu_m + sigma_m*shock) + monthly_contribution
        peaks = np.maximum(peaks, path)
        worst_drawdown = np.minimum(worst_drawdown, path/peaks-1)
        if i % 12 == 0:
            q = np.quantile(path, [0.1, 0.5, 0.9])
            lows.append(float(q[0])); mids.append(float(q[1])); highs.append(float(q[2]))
    # for consistent yearly deterministic output, sample after 12,24... months
    fixed_ann = deterministic[::12]
    total_added = starting_value+monthly_contribution*months
    annual = pd.DataFrame({"Year": np.arange(years+1), "Base case": fixed_ann,
                           "P10": lows, "Median": mids, "P90": highs})
    return {
        "annual": annual,
        "base_ending": float(deterministic[-1]),
        "base_growth": float(deterministic[-1]-total_added),
        "paid_in": float(total_added),
        "p10": lows[-1], "median": mids[-1], "p90": highs[-1],
        "below_contributions": float(np.mean(path < total_added)),
        "chance_negative_drawdown": float(np.mean(worst_drawdown < -0.20)),
        "avg_worst_drawdown": float(np.mean(worst_drawdown)),
        "simulated_final_values": path,
        "years": years,
    }


def allocation_by_class(positions: pd.DataFrame) -> pd.DataFrame:
    return positions.groupby("Class", as_index=False)["Value"].sum().sort_values("Value", ascending=False)
