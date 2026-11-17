"""Offline, documented historical interest-rate reference data.

Annual observations (2000-2025) from user-supplied World Bank and central-bank
files. Retail lending/deposit indicators may be unavailable; policy rates are
separately labeled benchmarks, not substitutes for bank product rates.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent / 'data'
CURRENCY_TO_REGION = {'MNT': 'MNG', 'USD': 'USA', 'EUR': 'EMU'}
METRIC_LABELS = {
    'lending_rate_pct': 'Lending interest rate (World Bank)',
    'deposit_rate_pct': 'Deposit interest rate (World Bank)',
    'policy_rate_annual_avg_pct': 'Policy rate / policy proxy (annual average)',
}

@lru_cache(maxsize=1)
def annual_rates() -> pd.DataFrame:
    frame = pd.read_csv(DATA/'historical_rates_annual.csv', encoding='utf-8-sig')
    required = {'region_code','region','year',*METRIC_LABELS}
    if not required.issubset(frame.columns):
        raise ValueError('The packaged historical dataset is missing required columns')
    frame['year'] = frame['year'].astype(int)
    for name in METRIC_LABELS:
        frame[name] = pd.to_numeric(frame[name], errors='coerce')
    return frame.sort_values(['region_code','year']).reset_index(drop=True)

@lru_cache(maxsize=1)
def quality_report() -> pd.DataFrame:
    return pd.read_csv(DATA/'data_quality.csv',encoding='utf-8-sig')

@lru_cache(maxsize=1)
def sources() -> pd.DataFrame:
    return pd.read_csv(DATA/'sources_and_definitions.csv',encoding='utf-8-sig').fillna('')

def region_rows(currency: str) -> pd.DataFrame:
    code=CURRENCY_TO_REGION[currency]
    return annual_rates().loc[lambda d:d['region_code']==code].copy()

def observed_rates(currency: str, metric: str) -> pd.DataFrame:
    if metric not in METRIC_LABELS:raise ValueError('Unknown rate series')
    result=region_rows(currency)[['year',metric]].dropna()
    return result.sort_values('year').reset_index(drop=True)

def rate_summary(currency: str, metric: str, start_year: int = 2010) -> dict | None:
    df=observed_rates(currency,metric)
    df=df[df.year>=start_year]
    if df.empty:return None
    return {'n_years':len(df),'first_year':int(df.year.min()),'last_year':int(df.year.max()),
            'latest':float(df[metric].iloc[-1]),'average':float(df[metric].mean()),
            'minimum':float(df[metric].min()),'maximum':float(df[metric].max())}
