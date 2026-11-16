"""Optional Yahoo Finance adapter for stocks, funds and supported crypto tickers.

No network access is required for manual valuations. Functions deliberately raise
friendly exceptions so a data-provider outage cannot break loan/retirement tabs.
"""
from __future__ import annotations

from typing import Iterable
import pandas as pd


def _extract(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        if ticker in raw.columns.get_level_values(0):
            stock = raw.xs(ticker, axis=1, level=0)
        elif ticker in raw.columns.get_level_values(1):
            stock = raw.xs(ticker, axis=1, level=1)
        else:
            return pd.DataFrame()
    else:
        stock = raw.copy()
    if "Close" not in stock:
        return pd.DataFrame()
    result = pd.DataFrame({"close": pd.to_numeric(stock["Close"], errors="coerce")})
    result["adjusted"] = pd.to_numeric(stock.get("Adj Close", stock["Close"]), errors="coerce")
    result.index = pd.DatetimeIndex(result.index).tz_localize(None)
    return result.dropna(subset=["close"]).loc[lambda x: x["close"] > 0].sort_index()


def download_market_history(tickers: Iterable[str], period: str = "3y") -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Download unadjusted last close + adjusted-return series, USD tickers only."""
    tickers = list(dict.fromkeys(str(t).upper() for t in tickers if str(t).strip()))
    if not tickers:
        return {}, []
    if period not in ("1y", "3y", "5y"):
        raise ValueError("Analysis period must be 1y, 3y or 5y.")
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is not installed. Install the requirements.txt packages.") from exc
    try:
        raw = yf.download(tickers=tickers, period=period, interval="1d",
                          auto_adjust=False, group_by="ticker", progress=False,
                          threads=False, timeout=12)
    except Exception as exc:
        raise RuntimeError(f"Market data is temporarily unavailable: {exc}") from exc
    histories = {ticker: _extract(raw, ticker) for ticker in tickers}
    unavailable = [ticker for ticker in tickers if histories[ticker].empty]
    return {ticker: frame for ticker, frame in histories.items() if not frame.empty}, unavailable


def usd_exchange_rate(target: str) -> float | None:
    """Yahoo FX quote converting one USD to target. None means no safe conversion."""
    if target == "USD":
        return 1.0
    if target not in ("EUR", "MNT"):
        return None
    direct = f"USD{target}=X"
    inverse = f"{target}USD=X"
    try:
        frames, _ = download_market_history([direct, inverse], period="1y")
    except Exception:
        return None
    if direct in frames:
        px = float(frames[direct]["close"].iloc[-1])
        return px if px > 0 else None
    if inverse in frames:
        px = float(frames[inverse]["close"].iloc[-1])
        return 1.0/px if px > 0 else None
    return None
