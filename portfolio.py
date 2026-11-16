"""Independent multi-asset portfolio calculation engine.

Current holdings are valued in USD. Historical return/risk uses ONLY assets with
reliable weekly market series. Manually priced assets are included in total
valuation and allocation but excluded from historical risk and return charts.
"""
from __future__ import annotations

import math
import re
from typing import Mapping

import numpy as np
import pandas as pd

LISTED_TYPES = (
    "Stock", "Stock ETF", "Bond ETF", "Crypto", "Commodity ETF",
    "REIT / Property ETF", "Other listed",
)
MANUAL_TYPES = ("Direct bond", "Property", "Cash", "Private investment", "Other manual")
ASSET_TYPES = LISTED_TYPES + MANUAL_TYPES
SYMBOL_RE = re.compile(r"^[A-Za-z0-9^][A-Za-z0-9.\-^=]{0,22}$")


def _number(value, name: str, *, required: bool = False) -> float | None:
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)) or str(value).strip() == "":
        if required:
            raise ValueError(f"{name} is required.")
        return None
    if isinstance(value, str):
        value = value.replace(",", "").replace("$", "").strip()
    try:
        numeric = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be a number.") from exc
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"{name} must be a finite, nonnegative number.")
    return numeric


def prepare_holdings(df: pd.DataFrame) -> pd.DataFrame:
    """Clean st.data_editor rows, preserving optional purchase costs and manual prices."""
    required = {"Asset type", "Ticker / name", "Units", "Avg buy / unit", "Current price (manual)"}
    if not required.issubset(df.columns):
        raise ValueError("Portfolio table is missing required columns.")
    holdings = []
    for i, row in df.iterrows():
        kind = str(row["Asset type"] or "").strip()
        title = str(row["Ticker / name"] or "").strip()
        if (not title or title.lower() == "nan") and pd.isna(row["Units"]):
            continue  # A blank data-editor row, not an investment.
        if kind not in ASSET_TYPES:
            raise ValueError(f"Row {i + 1}: choose a supported asset type.")
        if not title or title.lower() == "nan":
            raise ValueError(f"Row {i + 1}: enter a ticker or asset name.")
        if kind in LISTED_TYPES:
            title = title.upper()
            if not SYMBOL_RE.fullmatch(title):
                raise ValueError(f"Row {i + 1}: invalid market ticker '{title}'.")
        units = _number(row["Units"], f"Row {i+1} units", required=True)
        if units <= 0:
            raise ValueError(f"Row {i+1}: units must be greater than zero.")
        avg_cost = _number(row["Avg buy / unit"], f"Row {i+1} average buy")
        price = _number(row["Current price (manual)"], f"Row {i+1} manual price", required=kind in MANUAL_TYPES)
        holdings.append({"asset_type": kind, "ticker": title, "units": units,
                         "avg_cost": avg_cost, "manual_price": price,
                         "is_listed": kind in LISTED_TYPES})
    if not holdings:
        raise ValueError("Add at least one investment to analyze.")
    if len(holdings) > 30:
        raise ValueError("Use at most 30 investments for a responsive dashboard.")
    return pd.DataFrame(holdings)


def position_valuation(holdings: pd.DataFrame,
                       quotes: Mapping[str, pd.DataFrame]) -> tuple[pd.DataFrame, list[str]]:
    """Calculate present valuations, excluding inaccessible live tickers explicitly."""
    positions = []
    missing = []
    for _, h in holdings.iterrows():
        symbol = str(h["ticker"])
        if h["is_listed"]:
            history = quotes.get(symbol)
            if history is None or history.empty or "close" not in history:
                missing.append(symbol)
                continue
            prices = pd.to_numeric(history["close"], errors="coerce").dropna()
            prices = prices[prices > 0]
            if prices.empty:
                missing.append(symbol)
                continue
            unit_price = float(prices.iloc[-1])
            quote_date = str(pd.Timestamp(prices.index[-1]).date())
            source = "Market"
        else:
            unit_price = float(h["manual_price"])
            quote_date = "User entered"
            source = "Manual"
        value = float(h["units"]) * unit_price
        avg_cost = h["avg_cost"]
        cost_basis = float(h["units"]) * float(avg_cost) if pd.notna(avg_cost) else math.nan
        positions.append({
            "Asset": symbol, "Class": h["asset_type"], "Units": float(h["units"]),
            "Unit price USD": unit_price, "Value USD": value,
            "Cost basis USD": cost_basis,
            "Unrealized P/L USD": value-cost_basis if math.isfinite(cost_basis) else math.nan,
            "Pricing": source, "Quote date": quote_date,
        })
    positions_df = pd.DataFrame(positions)
    if not positions_df.empty:
        total = float(positions_df["Value USD"].sum())
        positions_df["Weight %"] = 100*positions_df["Value USD"]/total if total > 0 else 0.0
    return positions_df, sorted(set(missing))


def market_return_history(holdings: pd.DataFrame,
                          quotes: Mapping[str, pd.DataFrame],
                          benchmark: pd.DataFrame | None = None,
                          min_weeks: int = 12) -> dict:
    """Historical buy-and-hold proxy for *listed holdings only* at fixed units.

    Adjusted closes measure price/dividend history; scale the series to the
    actual current close for an intuitive valuation axis. Manual holdings do
    not receive an invented historical price path. Weekly sampling gives
    comparable dates for markets that trade on different days (crypto/ETFs).
    """
    series = {}
    for ticker, grp in holdings.loc[holdings["is_listed"]].groupby("ticker"):
        history = quotes.get(ticker)
        if history is None or history.empty:
            continue
        raw = history.get("adjusted", history.get("close"))
        if raw is None:
            continue
        adj = pd.to_numeric(raw, errors="coerce").dropna()
        adj = adj[adj > 0]
        close = pd.to_numeric(history["close"], errors="coerce").dropna()
        close = close[close > 0]
        if adj.size < 12 or close.empty:
            continue
        adj.index = pd.DatetimeIndex(adj.index).tz_localize(None)
        weekly = adj.resample("W-FRI").last().dropna()
        if weekly.size < min_weeks:
            continue
        qty = float(grp["units"].sum())
        # Investment series is in current USD price units at the same quantity.
        # Scaling adjusted history avoids treating accumulated dividends as price.
        scaled = weekly / float(adj.iloc[-1]) * float(close.iloc[-1]) * qty
        series[ticker] = scaled.rename(ticker)
    result = {"weekly_values": pd.DataFrame(), "weekly_portfolio": pd.Series(dtype=float),
              "weekly_returns": pd.Series(dtype=float), "benchmark_index": None,
              "correlations": pd.DataFrame(), "metrics": {}, "tickers_used": []}
    if not series:
        return result
    frame = pd.concat(series, axis=1).dropna(how="any").sort_index()
    if len(frame) < min_weeks:
        return result
    # Portfolio constructed as though current positions were held for this period.
    weekly_portfolio = frame.sum(axis=1)
    weekly_returns = weekly_portfolio.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    if len(weekly_returns) < min_weeks - 1 or weekly_portfolio.iloc[0] <= 0:
        return result
    weeks = len(weekly_returns)
    vol = float(weekly_returns.std(ddof=1) * math.sqrt(52)) if weeks > 1 else 0.0
    annualized_return = (float(weekly_portfolio.iloc[-1]) / float(weekly_portfolio.iloc[0])) ** (52/weeks)-1
    peak = weekly_portfolio.cummax()
    drawdown = weekly_portfolio / peak-1
    var95 = max(0.0, -float(np.quantile(weekly_returns, .05)))
    losses = weekly_returns[weekly_returns <= np.quantile(weekly_returns, .05)]
    cvar = max(0.0, -float(losses.mean())) if not losses.empty else 0.0
    corr = frame.pct_change().dropna().corr() if frame.shape[1] > 1 else pd.DataFrame()
    benchmark_index = None
    if benchmark is not None and not benchmark.empty:
        bm = benchmark.get("adjusted", benchmark.get("close"))
        if bm is not None:
            bm = pd.to_numeric(bm, errors="coerce").dropna()
            bm.index = pd.DatetimeIndex(bm.index).tz_localize(None)
            bm_weekly = bm.resample("W-FRI").last().dropna()
            aligned = bm_weekly.reindex(frame.index).dropna()
            if len(aligned) >= min_weeks and aligned.iloc[0] > 0:
                benchmark_index = 100*aligned/aligned.iloc[0]
    result.update({
        "weekly_values": frame,
        "weekly_portfolio": weekly_portfolio,
        "weekly_returns": weekly_returns,
        "correlations": corr,
        "benchmark_index": benchmark_index,
        "tickers_used": list(frame.columns),
        "metrics": {"annualized_return": float(annualized_return),
                    "volatility": vol,
                    "max_drawdown": float(drawdown.min()),
                    "var95_week": var95,
                    "cvar95_week": cvar,
                    "weeks": weeks,
                    "worst_week": float(weekly_returns.min()),
                    "best_week": float(weekly_returns.max())},
    })
    return result


def portfolio_summary(positions: pd.DataFrame, history: dict, annual_rf: float = 0.03) -> dict:
    if positions.empty:
        return {"total_value": 0.0, "market_coverage": 0.0, "cost_coverage": 0.0, "unrealized_profit": math.nan,
                "largest_weight": 0.0, "hhi": 0.0, "sharpe": math.nan, "risk_coverage": 0.0}
    total = float(positions["Value USD"].sum())
    market_value = float(positions.loc[positions["Pricing"] == "Market", "Value USD"].sum())
    priced_for_risk = set(history.get("tickers_used", []))
    risk_value = float(positions.loc[positions["Asset"].isin(priced_for_risk), "Value USD"].sum())
    costed = positions.loc[positions["Cost basis USD"].notna()]
    costed_value = float(costed["Value USD"].sum())
    profit = float(costed["Unrealized P/L USD"].sum()) if not costed.empty else math.nan
    risk = history["metrics"]
    vol = risk.get("volatility", 0.0)
    # Arithmetic expected weekly return annualized, for same return series as vol.
    sharpe = (float(history["weekly_returns"].mean())*52 - annual_rf) / vol if vol > 0 else math.nan
    weights = (positions["Value USD"] / total).to_numpy() if total else np.array([])
    return {"total_value": total, "market_coverage": market_value/total if total else 0.0,
            "cost_coverage": costed_value/total if total else 0.0,
            "unrealized_profit": profit,
            "largest_weight": float(max(weights)) if weights.size else 0.0,
            "hhi": float(np.sum(weights**2)) if weights.size else 0.0,
            "risk_coverage": risk_value/total if total else 0.0,
            "sharpe": float(sharpe)}


def allocation_by_class(positions: pd.DataFrame) -> pd.DataFrame:
    if positions.empty:
        return pd.DataFrame(columns=["Class", "Value USD"])
    return positions.groupby("Class", as_index=False)["Value USD"].sum().sort_values("Value USD", ascending=False)


def portfolio_insights(positions: pd.DataFrame, summary: dict, history: dict) -> list[str]:
    notes = []
    if positions.empty:
        return ["No priced holdings were available for analysis."]
    largest = positions.loc[positions["Value USD"].idxmax()]
    if summary["largest_weight"] >= .40:
        notes.append(f"Concentration: {largest['Asset']} accounts for {summary['largest_weight']:.1%} of portfolio value.")
    else:
        notes.append(f"Largest position: {largest['Asset']} ({summary['largest_weight']:.1%} of value).")
    if summary["risk_coverage"] < .80:
        notes.append(f"Historical risk covers only {summary['risk_coverage']:.1%} of current portfolio value; missing history and manual assets are excluded.")
    if summary["cost_coverage"] < .999:
        notes.append("Some average purchase prices are missing, so portfolio-wide unrealized profit/loss is incomplete.")
    if history["metrics"]:
        notes.append(f"Historical maximum drawdown for the listed subset was {history['metrics']['max_drawdown']:.1%}. This is a past observation, not a future loss limit.")
    else:
        notes.append("Not enough overlapping historical prices to calculate meaningful risk statistics.")
    if len(allocation_by_class(positions)) == 1:
        notes.append("All holdings are in one asset class; diversify across types if appropriate to your investment goals.")
    return notes
