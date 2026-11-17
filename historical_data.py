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


# ---------------------------------------------------------------
# Historical shocks are replayed as *scenarios*, not forecasts.
# Retail series are used when available; missing ones are NEVER
# filled with central-bank policy levels. Policy movements can
# instead drive an explicit, editable hypothetical pass-through.
# ---------------------------------------------------------------

def scenario_source(currency: str, decision: str) -> tuple[pd.DataFrame, str]:
    """Return observed annual values and the evidence class for one decision."""
    if decision not in {"loan", "savings"}:
        raise ValueError("Unknown simulation type")
    primary = 'lending_rate_pct' if decision == 'loan' else 'deposit_rate_pct'
    retail = observed_rates(currency, primary)
    if not retail.empty:
        return retail.rename(columns={primary:'reference_rate_pct'}), 'retail'
    policy = observed_rates(currency, 'policy_rate_annual_avg_pct')
    if policy.empty:
        raise ValueError('No suitable observations in the uploaded files')
    return policy.rename(columns={'policy_rate_annual_avg_pct':'reference_rate_pct'}), 'policy_change_proxy'


def consecutive_windows(series: pd.DataFrame, years: int) -> list[tuple[int,int]]:
    """Newest-first complete-year windows, with no imputation or gaps."""
    if years < 2:
        raise ValueError('A scenario requires at least two years')
    dates = sorted(set(int(y) for y in series['year']))
    available=set(dates)
    windows=[(yr-years+1,yr) for yr in dates if all(t in available for t in range(yr-years+1,yr+1))]
    return list(reversed(windows))


def scenario_rate_path(series: pd.DataFrame, start_year: int, end_year: int,
                       starting_rate_pct: float, *, observed_levels: bool,
                       pass_through_pct: float=100.0) -> pd.DataFrame:
    """Annual rate scenario. Historical changes are percentage POINT differences.

    When observed_levels=False, anchor year 1 to the user's starting rate,
    then apply pct/100 of each year-on-year movement from the *observed*
    series. These movements are assumptions, NOT observed retail rates.
    """
    import math
    if not math.isfinite(starting_rate_pct) or starting_rate_pct < 0:
        raise ValueError('Starting interest rate must be nonnegative and finite')
    if not 0 <= pass_through_pct <= 100:
        raise ValueError('Pass-through must be between 0 and 100%')
    data=series.loc[series['year'].between(start_year,end_year),['year','reference_rate_pct']].copy()
    data=data.sort_values('year').reset_index(drop=True)
    if len(data)!=end_year-start_year+1 or list(data.year)!=list(range(start_year,end_year+1)):
        raise ValueError('Selected period contains missing years; choose a complete period')
    if data.reference_rate_pct.isna().any():
        raise ValueError('Historical series contains missing observations')
    changes=data.reference_rate_pct.diff().fillna(0.0)
    if observed_levels:
        applied=data.reference_rate_pct.clip(lower=0.0)
    else:
        # Cumulative changes (not rate levels) respect the loan/deposit user's
        # entered starting rate and avoid negative bank rates in the scenario.
        applied=(starting_rate_pct + changes.cumsum()*pass_through_pct/100).clip(lower=0.0)
    data['Observed change (pp)']=changes
    data['Scenario rate (%)']=applied
    return data.rename(columns={'year':'Historical year','reference_rate_pct':'Source rate (%)'})


def simulate_loan_rate_replay(principal:float, loan_rate_pct:float, years:int,
                              extra_monthly:float, path:pd.DataFrame) -> dict:
    """Annual repricing over a historical-shock window vs the user's fixed APR.

    A variable-rate hypothetical fully amortizes over the *remaining* original
    term after each annual repricing, keeps the same extra monthly payment and
    never pays more than the debt owed. Compare equal months only.
    """
    from finance import loan_schedule, loan_payment
    import math
    if principal<=0 or years<1 or extra_monthly<0:
        raise ValueError('Invalid loan assumptions')
    months=min(years*12,len(path)*12)
    if months==0:raise ValueError('Rate path is empty')
    original=loan_schedule(principal,loan_rate_pct,years,extra_monthly)
    fixed=original.iloc[:months]
    fixed_interest=float(fixed['Interest'].sum())
    fixed_balance=float(fixed['Ending Balance'].iloc[-1])
    balance=float(principal)
    accrued=0.
    rows=[]
    max_required=0.
    previous_rate=None
    required=0.0
    for idx, record in enumerate(path.itertuples(index=False)):
        yr=int(record[0]); rate=float(record[3]) # path col order: year, source, change, scenario
        remaining=years*12-idx*12
        if remaining<=0:break
        mrate=rate/1200.
        # Keep the existing required payment if rates have not changed.
        # Repricing to the same APR must reproduce the fixed-rate baseline,
        # even when the borrower makes additional principal payments.
        if previous_rate is None or abs(rate-previous_rate)>1e-10:
            if balance>1e-7:
                if abs(mrate)<1e-12:required=balance/remaining
                else:required=balance*mrate/(1-(1+mrate)**(-remaining))
            else:required=0.0
        previous_rate=rate
        max_required=max(max_required,required)
        yearly_interest=0.; paid=0.; actual_months=0
        for _ in range(min(12,remaining)):
            if balance<=1e-7:break
            interest=balance*mrate
            due=balance+interest
            payment=min(required+extra_monthly,due)
            balance=max(0.,due-payment)
            yearly_interest+=interest;accrued+=interest;paid+=payment;actual_months+=1
        rows.append({'Historical year':yr,'Scenario rate (%)':rate,
                     'Required payment / month':required,
                     'Interest paid':yearly_interest,'Total paid':paid,
                     'Remaining balance':balance,'Months paid':actual_months})
    return {'years':len(path),'months_compared':months,'fixed_payment':loan_payment(principal,loan_rate_pct,years),
            'peak_required_payment':max_required,'scenario_interest':accrued,'fixed_interest':fixed_interest,
            'scenario_balance':balance,'fixed_balance':fixed_balance,
            'interest_difference':accrued-fixed_interest,'balance_difference':balance-fixed_balance,
            'yearly':pd.DataFrame(rows)}


def simulate_savings_rate_replay(current_savings:float,monthly_saving:float,
                                 steady_deposit_pct:float,inflation_pct:float,
                                 contribution_growth_pct:float,path:pd.DataFrame)->dict:
    """Compare steady and changing bank deposit returns IN TODAY'S MONEY.

    Uses the user's constant forward inflation assumption for both scenarios,
    not historical inflation (which was not supplied). Annual deposit rates
    are assumed to apply all year, compounded monthly with end-month deposits.
    """
    from finance import real_monthly_return
    if current_savings<0 or monthly_saving<0 or steady_deposit_pct<0 or inflation_pct<0:
        raise ValueError('Savings and interest/inflation inputs must be nonnegative')
    if not 0<=contribution_growth_pct<=20:raise ValueError('Invalid savings contribution increase')
    if path.empty:raise ValueError('Rate path is empty')
    steady=float(current_savings);varying=float(current_savings)
    invested=0.;details=[]
    steady_monthly=real_monthly_return(steady_deposit_pct,inflation_pct)
    for idx,record in enumerate(path.itertuples(index=False)):
        year=int(record[0]);variable_rate=float(record[3])
        variable_monthly=real_monthly_return(variable_rate,inflation_pct)
        contribution=float(monthly_saving)*(1+contribution_growth_pct/100)**idx
        for _ in range(12):
            steady=steady*(1+steady_monthly)+contribution
            varying=varying*(1+variable_monthly)+contribution
            invested+=contribution
        details.append({'Historical year':year,'Scenario deposit rate (%)':variable_rate,
                        'Monthly saving (today\'s money)':contribution,
                        'Steady-rate balance':steady,'Changing-rate balance':varying})
    return {'years':len(path),'steady_balance':steady,'scenario_balance':varying,
            'difference':varying-steady,'contributions':invested,
            'steady_rate':steady_deposit_pct,'yearly':pd.DataFrame(details)}
