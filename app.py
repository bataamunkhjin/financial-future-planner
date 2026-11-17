"""Financial Future Planner v6.5 — accessible, readable typography.

Two planners and all financial computations are retained from v6.4.
Currency labels do not convert money. All projections are hypothetical.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from finance import (
    loan_payment, loan_schedule, loan_stats, add_months,
    currency_assumptions, inflation_shock_presets,
    loan_rate_scenarios, annual_loan_scenario, loan_payoff_milestones,
    real_monthly_return, grow_savings, required_monthly_contribution,
    drawdown_portfolio_requirement, earliest_feasible_retirement_age,
    retirement_what_if_scenarios, retirement_projection,
    monte_carlo_projection, simulated_lifetime_savings_goal,
    retirement_life_schedule, inflation_purchasing_power,
    inflation_shock_projection, compare_mortgage_vs_investing,
    mortgage_investing_return_scenarios,
)
from report import generate_pdf_report

st.set_page_config(
    page_title="Financial Future Planner", page_icon="F", layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown('''<style>
/* Calm, readable financial dashboard. Streamlit's native widgets use config.toml. */
:root {
  --fp-bg:#F5F7F8; --fp-surface:#FFFFFF; --fp-surface-alt:#EFF5F5;
  --fp-border:#D9E3E7; --fp-text:#183247; --fp-muted:#586F80;
  --fp-accent:#167C75; --fp-warning:#B77C38; --fp-blue:#557FA8;
}
html,body,[data-testid="stAppViewContainer"],.stApp {
  background:var(--fp-bg)!important; color:var(--fp-text)!important;
  font-family:Inter,"Segoe UI",Arial,sans-serif;
}
[data-testid="stHeader"] {background:var(--fp-bg)!important;}
[data-testid="stDecoration"] {display:none;}
.block-container {max-width:1240px;padding:1.6rem 2.4rem 4.5rem;}
section[data-testid="stSidebar"] {background:#EAF1F3!important;border-right:1px solid var(--fp-border);}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#5B7182!important;}
[data-testid="stVerticalBlockBorderWrapper"] > div {border-color:var(--fp-border)!important;}
/* Accessible UI text sizes: readable labels, tabs, controls, captions and buttons. */
html {font-size:16px;}
[data-testid="stCaptionContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
  font-size:.94rem!important;line-height:1.55!important;color:#536B7C!important;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] span {
  font-size:1.04rem!important;color:var(--fp-text)!important;
}
[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button,
[data-testid="stFormSubmitButton"] button {font-size:1rem!important;min-height:42px;}
[data-testid="stButton"] button p,
[data-testid="stDownloadButton"] button p,
[data-testid="stFormSubmitButton"] button p {font-size:1rem!important;}
[data-testid="stExpander"] summary p {font-size:1rem!important;}
/* High-contrast labels and calm input outlines. Do not override native focus handling. */
[data-testid="stWidgetLabel"] p {font-size:1rem!important;font-weight:650!important;color:#28445A!important;}
[data-testid="stMetric"] {background:#FFFFFF;border:1px solid var(--fp-border);border-radius:14px;padding:14px;min-width:0;}
[data-testid="stMetricLabel"] p {font-size:.95rem!important;color:#526A7A!important;}
[data-testid="stMetricValue"] {font-size:clamp(1.4rem,2.1vw,1.8rem)!important;line-height:1.22!important;letter-spacing:-.025em;overflow-wrap:anywhere;color:#183247!important;}
[data-testid="stMetricDelta"] {font-size:.95rem!important;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:8px;border-bottom:1px solid var(--fp-border);}
[data-testid="stTabs"] [data-baseweb="tab-list"] button {
  color:#425B70;padding:13px 20px;border-radius:9px 9px 0 0;font-size:1.03rem!important;font-weight:700;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"] {
  color:#116D65!important;border-bottom:2px solid #167C75;background:#E5F2EF;
}
[data-testid="stDownloadButton"] button {border-radius:9px!important;border:1px solid #97C6BE!important;}
[data-testid="stExpander"] {border-color:var(--fp-border)!important;border-radius:12px!important;}
[data-testid="stExpander"] summary {font-weight:650;font-size:1rem!important;}
[data-testid="stMarkdownContainer"] p {font-size:1rem;line-height:1.65;}
.fp-header {display:flex;align-items:center;justify-content:space-between;gap:24px;
 background:#FFFFFF;border:1px solid var(--fp-border);border-radius:15px;padding:20px 23px;
 margin-bottom:18px;box-shadow:0 4px 18px rgba(30,62,83,.04);}
.fp-kicker {font-size:.84rem;text-transform:uppercase;letter-spacing:.10em;color:#126D65;font-weight:800;margin-bottom:5px;}
.fp-header h1 {font-size:clamp(1.85rem,2.5vw,2.25rem);line-height:1.2;margin:0 0 7px;letter-spacing:-.035em;color:#183247;}
.fp-header p {margin:0;color:#5A7181;font-size:1rem;}
.fp-brand {display:flex;align-items:center;gap:11px;flex-shrink:0;}
.fp-logo {display:flex;align-items:center;justify-content:center;width:48px;height:55px;
 background:#F4F6FA;border:1px solid #DFE6EC;border-radius:9px;padding:4px;}
.fp-logo img {width:39px;height:47px;object-fit:contain;}
.fp-brand-name {font-size:.94rem;font-weight:760;line-height:1.4;color:#183247;}
.fp-brand-name span {display:block;color:#98702F;font-size:.84rem;}
.fp-section {margin:24px 0 10px;}
.fp-section h2 {font-size:1.48rem;margin:0 0 5px;font-weight:760;letter-spacing:-.02em;color:#183247;}
.fp-section p {font-size:1rem;line-height:1.55;color:#617586;margin:0;}
.fp-intro {color:#617586;font-size:1rem;margin-bottom:18px;}
.fp-answer {background:#EAF6F2;border:1px solid #BCDAD1;border-left:4px solid #167C75;
 border-radius:12px;padding:17px 20px;margin:14px 0 16px;}
.fp-answer.caution {background:#FFF7EA;border-color:#E9D1AD;border-left-color:#B77C38;}
.fp-answer .fp-answer-label {color:#446D67;text-transform:uppercase;letter-spacing:.07em;font-size:.84rem;font-weight:800;}
.fp-answer.caution .fp-answer-label {color:#805B30;}
.fp-answer .fp-answer-title {font-size:1.4rem;font-weight:800;color:#16394A;margin:5px 0;}
.fp-answer .fp-answer-sub {font-size:1rem;color:#3D5D67;line-height:1.55;}
.fp-note {background:#F0F5F7;border:1px solid var(--fp-border);color:#4E6575;
 padding:12px 16px;border-radius:11px;font-size:.98rem;line-height:1.6;margin:10px 0 16px;}
.fp-metric-row {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:10px 0 18px;}
.fp-card {background:#FFFFFF;border:1px solid var(--fp-border);border-radius:13px;padding:15px 15px 13px;
 min-height:114px;box-shadow:0 2px 8px rgba(30,62,83,.025);}
.fp-card .label {font-size:.96rem;line-height:1.45;color:#536C7C;}
.fp-card .value {font-size:clamp(1.27rem,1.85vw,1.65rem);font-weight:800;color:#16394A;
 margin:10px 0 5px;line-height:1.14;letter-spacing:-.032em;overflow-wrap:anywhere;}
.fp-card .detail {font-size:.9rem;color:#586F80;line-height:1.4;}
.fp-chart-note {font-size:.94rem;color:#526B7B;margin-top:-8px;}
.fp-divider {height:1px;background:var(--fp-border);margin:28px 0 12px;}
@media(max-width:960px){.block-container {padding:1.3rem 1.2rem 3.6rem;}
 .fp-metric-row{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media(max-width:600px){.fp-header{padding:16px;gap:9px}.fp-brand-name{display:none;}
 .fp-logo{width:40px;height:47px}.fp-logo img{width:32px;height:40px;}
 .fp-metric-row{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}
 .fp-card{min-height:110px;padding:11px;}}
/* At phone widths, preserve tap targets and avoid oversized KPI wrapping. */
@media(max-width:700px) {
 [data-testid="stTabs"] [data-baseweb="tab-list"] button {
   font-size:1rem!important;padding:11px 12px!important;
 }
 .fp-header h1 {font-size:1.8rem;}
 .fp-card .value {font-size:1.36rem;}
}
</style>''', unsafe_allow_html=True)

# Currency controls are labels and regional planning assumptions, NOT FX conversions.
CURRENCIES = {"MNT (₮)": "₮", "USD ($)": "$", "EUR (€)": "€"}
st.sidebar.markdown("**FINANCIAL FUTURE PLANNER**")
st.sidebar.caption("Your planning settings")
currency_choice = st.sidebar.selectbox(
    "Currency", list(CURRENCIES),
    help="Changes default rates and currency labels; does not convert balances between currencies.",
)
CURRENCY = CURRENCIES[currency_choice]
CURRENCY_CODE = currency_choice.split(" ")[0]
IS_MNT = CURRENCY_CODE == "MNT"
DEFAULT_RATES = currency_assumptions(CURRENCY_CODE)

with st.sidebar.expander("About these default rates"):
    st.caption(f"Lending: {DEFAULT_RATES['loan_pct']:.2f}% — {DEFAULT_RATES['loan_reference']}.")
    st.caption(f"Deposit: {DEFAULT_RATES['deposit_pct']:.2f}% — {DEFAULT_RATES['deposit_reference']}.")
    st.caption("Investment returns, volatility, and inflation are editable scenario assumptions, not guarantees. "
               "Loan benchmarks may be housing-related; use your own lender's quote for another loan type.")

# Reusable money field keeps typed digits comma-grouped without silently losing decimals.
_MONEY_FORMAT = re.compile(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{0,2})?\Z")

def parse_money_text(text: str, min_value: float = 0.0,
                     max_value: float = 10_000_000_000_000.0) -> Decimal:
    content = str(text).strip()
    if not _MONEY_FORMAT.fullmatch(content):
        raise ValueError("Enter a number such as 1,000,000 or 1,000,000.50.")
    try:
        number = Decimal(content.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("Enter a valid number.") from exc
    if not number.is_finite() or not Decimal(str(min_value)) <= number <= Decimal(str(max_value)):
        raise ValueError(f"Enter an amount between {min_value:,.0f} and {max_value:,.0f}.")
    return number

def format_money_text(value: Decimal | float, min_decimals: int = 0) -> str:
    d = Decimal(str(value))
    places = min_decimals if d == d.to_integral_value() else max(min_decimals, -d.as_tuple().exponent)
    if places > 2:
        raise ValueError("Monetary values may have at most two decimal places.")
    return f"{d:,.{places}f}"

def _normalize_money_input(key: str, value_key: str, error_key: str,
                           min_value: float, max_value: float, min_decimals: int) -> None:
    try:
        amount = parse_money_text(st.session_state[key], min_value, max_value)
    except ValueError as exc:
        st.session_state[error_key] = str(exc)
        return
    st.session_state[key] = format_money_text(amount, min_decimals)
    st.session_state[value_key] = float(amount)
    st.session_state.pop(error_key, None)

def money_input(label: str, *, name: str, default: float, min_value: float = 0.,
                max_value: float = 10_000_000_000_000.,
                help_text: str | None = None) -> float:
    code = CURRENCY_CODE
    key = f"money_{code}_{name}"
    value_key, error_key = key + "_last_valid", key + "_error"
    decimals = 0 if IS_MNT else 2
    if key not in st.session_state:
        st.session_state[key] = format_money_text(default, decimals)
        st.session_state[value_key] = float(default)
    st.text_input(label, key=key,
        help=(help_text + " " if help_text else "") + "Press Enter to add thousands separators.",
        on_change=_normalize_money_input,
        args=(key, value_key, error_key, min_value, max_value, decimals),
    )
    if error_key in st.session_state:
        st.error(st.session_state[error_key] + " Using the last valid amount.")
    return float(st.session_state[value_key])

def money(value: float, decimals: int = 0) -> str:
    return f"{CURRENCY}{value:,.{decimals}f}"

def months_as_text(months: int) -> str:
    y, m = divmod(max(0, int(months)), 12)
    return f"{y} years {m} months" if y else f"{m} months"

def section(title: str, caption: str = "") -> None:
    st.markdown('<div class="fp-section"><h2>' + escape(title) + '</h2><p>' +
                escape(caption) + '</p></div>', unsafe_allow_html=True)

def cards(items: list[tuple[str,str,str]]) -> None:
    parts = []
    for label, value, detail in items:
        parts.append('<div class="fp-card"><div class="label">' + escape(str(label)) +
                     '</div><div class="value">' + escape(str(value)) +
                     '</div><div class="detail">' + escape(str(detail)) + '</div></div>')
    st.markdown('<div class="fp-metric-row">' + ''.join(parts) + '</div>', unsafe_allow_html=True)

def answer(label: str, title: str, explanation: str, caution: bool = False) -> None:
    css = 'fp-answer caution' if caution else 'fp-answer'
    st.markdown(f'<div class="{css}"><div class="fp-answer-label">{escape(label)}</div>'
                f'<div class="fp-answer-title">{escape(title)}</div>'
                f'<div class="fp-answer-sub">{escape(explanation)}</div></div>', unsafe_allow_html=True)

def chart(fig: go.Figure, *, x_label: str = "", y_label: str = "", height: int = 390) -> None:
    fig.update_layout(
        template="plotly_white", height=height,
        margin=dict(l=55, r=22, t=82, b=66),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=14, color="#28475B"),
        colorway=["#167C75", "#557FA8", "#B77C38", "#8B74B1"],
        legend=dict(orientation="h", y=1.16, x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=13)),
        hovermode="x unified", hoverlabel=dict(bgcolor="#FFFFFF",font_size=14,font_color="#183247",bordercolor="#D9E3E7"),
    )
    fig.update_xaxes(title=x_label, showgrid=False, zeroline=False,
                     title_font=dict(size=13,color="#526B7B"), tickfont=dict(size=13), linecolor="#CAD7DE")
    fig.update_yaxes(title=y_label, gridcolor="rgba(58,93,110,.12)",
                     zeroline=False, separatethousands=True,
                     title_font=dict(size=13,color="#526B7B"), tickfont=dict(size=13))
    st.plotly_chart(fig, use_container_width=True, theme=None,
                    config={"displayModeBar":False,"scrollZoom":False,"responsive":True})

def paged_table(data: pd.DataFrame, *, key: str, page_size: int = 10) -> None:
    total = len(data)
    if total > page_size:
        ranges = [(i, min(i + page_size,total)) for i in range(0,total,page_size)]
        options = [f"Rows {start+1}–{end} of {total}" for start,end in ranges]
        selected = st.selectbox("Choose table page",options,key=key+"_page")
        start,end = ranges[options.index(selected)]
        data = data.iloc[start:end]
    # Ten rows maximum; an explicit content-sized height works on old and new Streamlit.
    # Avoid a nested scrollbar inside a fixed-height data table.
    visible_height = 40 * (len(data) + 1) + 16
    st.dataframe(data,hide_index=True,use_container_width=True,height=visible_height)


def download_csv(label: str, frame: pd.DataFrame, filename: str) -> None:
    st.download_button(label,frame.to_csv(index=False).encode("utf-8-sig"),
                       file_name=filename,mime="text/csv")

# School branding is local and self-contained. No remote logo service or extra GitHub asset required.
AUM_CREST_BASE64 = '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'

st.markdown('''<div class="fp-header"><div><div class="fp-kicker">Munkhjin Bataa</div>
<h1>Financial Future Planner</h1><p>Simple decisions for borrowing and retirement.</p></div>
<div class="fp-brand"><div class="fp-logo"><img alt="AUM crest" src="data:image/png;base64,''' +
AUM_CREST_BASE64 + '''"></div><div class="fp-brand-name">AMERICAN UNIVERSITY<span>OF MONGOLIA</span></div></div></div>''',
unsafe_allow_html=True)

loan_tab, retirement_tab = st.tabs(["Loan Planner", "Retirement Planner"])

# ====================== LOAN PLANNER ======================
with loan_tab:
    section("Start with your loan", "Enter four numbers. Everything below updates automatically.")
    with st.container(border=True):
        col1,col2 = st.columns(2,gap="large")
        with col1:
            loan_amount = money_input(f"Loan amount ({CURRENCY})",name="loan_amount",
                default=250_000_000. if IS_MNT else 150_000.,min_value=1.,max_value=1e12,
                help_text="The amount borrowed, excluding interest.")
        with col2:
            interest_rate = st.number_input("Annual interest rate (%)",min_value=0.0,max_value=50.0,
                value=DEFAULT_RATES["loan_pct"],step=0.25,format="%.2f",
                key=f"loan_interest_{CURRENCY_CODE}",
                help="Interest rate charged on the loan each year; enter your lender's actual rate.")
        col3,col4=st.columns(2,gap="large")
        with col3:
            loan_years = st.number_input("Loan length (years)",min_value=1,max_value=40,
                value=20 if IS_MNT else 30,step=1,
                help="Number of years for standard repayment.")
        with col4:
            extra_monthly = money_input(f"Extra payment / month ({CURRENCY})",name="extra_monthly",
                default=300_000. if IS_MNT else 200.,min_value=0.,max_value=1e10,
                help_text="Optional money paid on top of the required payment to reduce principal faster.")
        with st.expander("Loan start date (optional)"):
            loan_start=st.date_input("Loan starts",value=date.today(),
                min_value=date(2000,1,1),max_value=date(2100,12,31),
                help="Used to show the projected final payment date.")
    scheduled_payment=loan_payment(loan_amount,interest_rate,loan_years)
    standard=loan_schedule(loan_amount,interest_rate,loan_years,0.,loan_start)
    chosen=loan_schedule(loan_amount,interest_rate,loan_years,extra_monthly,loan_start)
    standard_stats=loan_stats(standard,loan_amount)
    chosen_stats=loan_stats(chosen,loan_amount)
    saved_interest=max(0.,standard_stats["interest"]-chosen_stats["interest"])
    months_saved=standard_stats["months"]-chosen_stats["months"]

    answer("YOUR LOAN SUMMARY",f"{money(scheduled_payment,2)} per month",
        "This is your required principal-and-interest payment. Your chosen extra payment "
        f"adds {money(extra_monthly,2)}/month toward principal.")
    cards([
        ("Total interest with extras",money(chosen_stats["interest"]),"Over the shortened repayment period"),
        ("Interest you save",money(saved_interest),"Versus standard repayment"),
        ("Paid off by",chosen_stats["payoff_date"].strftime("%b %Y"),"Assuming no missed payments"),
        ("Time saved",months_as_text(months_saved),"With your extra payments"),
    ])
    section("See the difference extra payments make","The lower line means less outstanding debt.")
    loan_bal=go.Figure()
    for df,name,col in [(standard,"Standard repayment","#557FA8"),(chosen,"With extra payments","#167C75")]:
        loan_bal.add_trace(go.Scatter(x=[0]+df["Month"].tolist(),
              y=[loan_amount]+df["Ending Balance"].tolist(),name=name,
              line=dict(color=col,width=3),mode="lines"))
    chart(loan_bal,x_label="Months since loan began",y_label=f"Remaining loan ({CURRENCY})",height=380)
    st.caption(f"Your extra payment saves {money(saved_interest)} and moves payoff forward by {months_as_text(months_saved)}. "
               "Fixed rate, no fees or prepayment penalties are assumed.")
    with st.expander("Understand the cost: principal, interest, and repayment history"):
        st.caption("Principal is the borrowed amount. Interest is the price paid to borrow it.")
        allocation=go.Figure()
        allocation.add_trace(go.Bar(y=["Loan cost"],x=[loan_amount],name="Principal",
                                    orientation="h",marker_color="#167C75"))
        allocation.add_trace(go.Bar(y=["Loan cost"],x=[chosen_stats["interest"]],name="Interest",
                                    orientation="h",marker_color="#B77C38"))
        allocation.update_layout(barmode="stack")
        chart(allocation,x_label=f"Total repayment ({CURRENCY})",height=240)
        interest_chart=go.Figure()
        for df,name,col in [(standard,"Standard","#557FA8"),(chosen,"With extras","#167C75")]:
            interest_chart.add_trace(go.Scatter(x=df["Month"],y=df["Interest"].cumsum(),
                                      name=name,line=dict(color=col,width=3)))
        chart(interest_chart,x_label="Month",y_label=f"Cumulative interest ({CURRENCY})",height=340)
        st.caption("Total cash paid with extras: "+money(chosen_stats["paid"])+". "
                   "If your extra payment is zero, both loan lines overlap.")

    extra_scenarios=annual_loan_scenario(loan_amount,interest_rate,loan_years,extra_monthly,loan_start)
    rate_scenarios=loan_rate_scenarios(loan_amount,interest_rate,loan_years,extra_monthly,loan_start)
    milestones=loan_payoff_milestones(chosen,loan_amount)
    with st.expander("Compare extra payments and interest-rate scenarios"):
        section("Pay more or pay less?","Automatically compare several payment strategies.")
        st.dataframe(extra_scenarios,hide_index=True,use_container_width=True)
        section("What if the interest rate changed?","These are scenarios for a new loan, not repricing your existing fixed-rate loan.")
        st.dataframe(rate_scenarios,hide_index=True,use_container_width=True)
        scenario_view=st.selectbox("Choose a scenario chart",[
            "Interest saved with extra payments", "Monthly payment at different rates", "Annual principal and interest"
        ],key="loan_scenario_chart")
        if scenario_view=="Interest saved with extra payments":
            scenario_fig=go.Figure(go.Bar(
                x=extra_scenarios["Scenario"],y=extra_scenarios["Interest Saved"],
                marker_color="#167C75"))
            chart(scenario_fig,y_label=f"Interest avoided ({CURRENCY})",height=300)
        elif scenario_view=="Monthly payment at different rates":
            scenario_fig=go.Figure(go.Scatter(
                x=rate_scenarios["Rate (%)"],y=rate_scenarios["Monthly P&I"],
                mode="lines+markers",name="Monthly payment",line=dict(color="#557FA8",width=3)))
            chart(scenario_fig,x_label="Annual interest (%)",y_label=f"Payment ({CURRENCY})",height=300)
        else:
            yearly_paid=standard.groupby("Year",as_index=False)[["Principal","Interest"]].sum()
            scenario_fig=go.Figure()
            scenario_fig.add_trace(go.Bar(x=yearly_paid["Year"],y=yearly_paid["Principal"],
                                          name="Principal",marker_color="#167C75"))
            scenario_fig.add_trace(go.Bar(x=yearly_paid["Year"],y=yearly_paid["Interest"],
                                          name="Interest",marker_color="#B77C38"))
            scenario_fig.update_layout(barmode="stack")
            chart(scenario_fig,x_label="Year",y_label=f"Annual repayment ({CURRENCY})",height=320)
        st.caption("Higher rates increase borrowing costs, but all results are illustrative.")
    with st.expander("Repayment milestones and amortization table"):
        st.dataframe(milestones,hide_index=True,use_container_width=True)
        paged_table(chosen,key="amortization_table")
        download_csv("Download complete amortization CSV",chosen,"loan_amortization.csv")

    loan_insights=[
        (f"Paying {money(extra_monthly)} in extra principal each month saves about "
         f"{money(saved_interest)} in total interest." if extra_monthly>0 else
         "An extra principal payment would shorten your repayment period; try a small extra amount above."),
        f"Without extra payments, total lifetime interest is {money(standard_stats['interest'])}.",
        "Loan calculations assume a constant interest rate and no lender fees or prepayment penalties.",
    ]

# ====================== RETIREMENT PLANNER ======================
with retirement_tab:
    section("Set your retirement goal","Five simple inputs. Balances and spending are measured in today's purchasing power.")
    with st.container(border=True):
        a,b=st.columns(2,gap="large")
        with a:
            current_age=st.number_input("Your current age",min_value=18,max_value=80,value=25,step=1)
        with b:
            retirement_age=st.number_input("Age you want to retire",min_value=int(current_age)+1,
                max_value=90,value=max(60,int(current_age)+1),step=1)
        c,d=st.columns(2,gap="large")
        with c:
            retirement_savings=money_input(f"Savings you already have ({CURRENCY})",name="retirement_savings",
                default=30_000_000. if IS_MNT else 10_000.,min_value=0.)
        with d:
            retirement_contribution=money_input(f"Money you save each month ({CURRENCY})",name="retirement_contribution",
                default=1_000_000. if IS_MNT else 300.,min_value=0.,max_value=1e10)
        target_income=money_input(f"Monthly spending you want in retirement ({CURRENCY})",name="target_income",
            default=10_000_000. if IS_MNT else 1_500.,min_value=1.,max_value=1e10,
            help_text="Your desired monthly lifestyle cost in today's purchasing power.")
        with st.expander("Adjust assumptions (optional)"):
            st.caption("You may change these defaults. They are not guaranteed market returns.")
            q1,q2=st.columns(2,gap="large")
            with q1:
                expected_return=st.number_input("Expected investment return (%/year)",min_value=-10.,max_value=30.,
                    value=DEFAULT_RATES["investment_return_pct"],step=.5,
                    key=f"investment_return_{CURRENCY_CODE}")
            with q2:
                inflation=st.number_input("Inflation (%/year)",min_value=0.,max_value=30.,
                    value=DEFAULT_RATES["inflation_pct"],step=.5,
                    key=f"retirement_inflation_{CURRENCY_CODE}")
            q3,q4=st.columns(2,gap="large")
            with q3:
                volatility=st.number_input("Investment volatility (%/year)",min_value=0.,max_value=60.,
                    value=DEFAULT_RATES["investment_volatility_pct"],step=1.,
                    key=f"retirement_volatility_{CURRENCY_CODE}",
                    help="How widely simulated annual investment returns vary. Not the currency's volatility.")
            with q4:
                planning_age=st.number_input("Plan through age",min_value=int(retirement_age)+1,
                    max_value=120,value=max(100,int(retirement_age)+1),step=1)
            q5,q6=st.columns(2,gap="large")
            with q5:
                bank_deposit_rate=st.number_input("Bank deposit rate (%/year)",min_value=0.,max_value=35.,
                    value=DEFAULT_RATES["deposit_pct"],step=.1,
                    key=f"bank_deposit_{CURRENCY_CODE}",
                    help="Illustrative deposit-rate sensitivity; not guaranteed long-term.")
            with q6:
                simulations=st.selectbox("Monte Carlo scenarios",options=[250,500,1000,2000],index=2,
                    help="Number of hypothetical investment futures generated.")

    months_to_retire=(int(retirement_age)-int(current_age))*12
    real_rate=real_monthly_return(expected_return,inflation)
    planned_balance=grow_savings(retirement_savings,retirement_contribution,months_to_retire,real_rate)
    retirement_months=(int(planning_age)-int(retirement_age))*12
    portfolio_target=drawdown_portfolio_requirement(target_income,retirement_months,real_rate)
    difference=planned_balance-portfolio_target
    needed_per_month=required_monthly_contribution(retirement_savings,months_to_retire,portfolio_target,real_rate)
    supported_income=(planned_balance / drawdown_portfolio_requirement(1.,retirement_months,real_rate))
    feasible_retirement=earliest_feasible_retirement_age(int(current_age),int(planning_age),retirement_savings,
                                retirement_contribution,target_income,real_rate)
    earliest_age=feasible_retirement["age"] if feasible_retirement else None
    retirement_scenarios=retirement_what_if_scenarios(int(current_age),int(retirement_age),int(planning_age),
             retirement_savings,retirement_contribution,target_income,expected_return,inflation,
             bank_deposit_pct=bank_deposit_rate)
    projection,depletion_age=retirement_projection(int(current_age),int(retirement_age),int(planning_age),
             retirement_savings,retirement_contribution,target_income,expected_return,inflation)
    simulation=monte_carlo_projection(int(current_age),int(retirement_age),int(planning_age),
             retirement_savings,retirement_contribution,target_income,expected_return,
             inflation,volatility,portfolio_target,simulations=int(simulations),seed=42)
    fan=simulation["fan"]
    savings_goal_80=simulated_lifetime_savings_goal(int(current_age),int(retirement_age),int(planning_age),
             retirement_savings,retirement_contribution,target_income,expected_return,inflation,
             volatility,simulations=int(simulations),target_probability=.80,seed=42)
    retirement_monthly,retirement_yearly=retirement_life_schedule(planned_balance,int(retirement_age),
             int(planning_age),target_income,expected_return,inflation)
    inflation_table=inflation_purchasing_power(projection,int(current_age),target_income,inflation)
    additional_saving=max(0.,needed_per_month-retirement_contribution)
    lasts_to_horizon=depletion_age is None
    funded_share=(planned_balance/portfolio_target if portfolio_target>0 else 1.)

    if lasts_to_horizon:
        answer("YOUR RETIREMENT OUTLOOK",f"Savings could last through age {planning_age}",
               "Under a steady-return assumption, your projected savings cover the spending goal. "
               "Market returns can vary, so see the simulation below.")
    else:
        answer("YOUR RETIREMENT OUTLOOK",f"Savings may run out near age {depletion_age:.1f}",
               f"With {money(target_income)} monthly spending, the steady-return model falls short "
               f"of age {planning_age}. Consider saving more or adjusting your retirement goal.",True)

    cards([
        ("Savings at retirement",money(planned_balance),"Value in today's money"),
        ("Needed for your goal",money(portfolio_target),f"Retirement to age {planning_age}"),
        ("Modeled success rate",f"{simulation['sustain_probability']:.0%}",f"{int(simulations):,} simulated futures"),
        ("Extra saving needed",money(additional_saving),"Per month before retirement"),
    ])
    st.progress(min(1.,max(0.,funded_share)),text=f"{funded_share:.0%} of steady-return savings target")
    st.caption("This progress bar is not a probability. The success rate above comes from Monte Carlo simulations.")

    section("Your savings over time","Savings grow before retirement, then support monthly withdrawals. Returns continue after retirement.")
    balance_fig=go.Figure()
    balance_fig.add_trace(go.Scatter(x=projection["Age"],y=projection["Balance (today's money)"],
         name="Expected balance (steady returns)",line=dict(color="#167C75",width=3),
         fill="tozeroy",fillcolor="rgba(22,124,117,.09)"))
    balance_fig.add_vline(x=int(retirement_age),line_color="#B77C38",line_dash="dot",line_width=2)
    chart(balance_fig,x_label="Your age",y_label=f"Balance ({CURRENCY}, today's money)",height=365)
    st.caption(f"The dotted line marks retirement at age {retirement_age}. Savings and spending are assumed to rise with inflation in nominal terms.")

    section("What if investment returns vary?","Monte Carlo estimates a range of possible outcomes instead of assuming perfect steady growth.")
    st.markdown(f"**{simulation['sustain_probability']:.1%}** of {int(simulations):,} simulated outcomes fund every planned "
                f"monthly withdrawal through age {planning_age}. This is a model result, not a guarantee.")
    show_middle=st.checkbox("Also show the middle 50% of simulations",value=False,
                 help="Adds a narrower 25th–75th percentile band to the chart.")
    mc_fig=go.Figure()
    mc_fig.add_trace(go.Scatter(x=fan["Age"],y=fan["P10"],line=dict(width=0),
                    name="Lower 10% boundary",showlegend=False,hoverinfo="skip"))
    mc_fig.add_trace(go.Scatter(x=fan["Age"],y=fan["P90"],line=dict(width=0),
                    fill="tonexty",fillcolor="rgba(85,127,168,.16)",name="10th–90th percentile range"))
    if show_middle:
        mc_fig.add_trace(go.Scatter(x=fan["Age"],y=fan["P25"],line=dict(width=0),
                    showlegend=False,hoverinfo="skip"))
        mc_fig.add_trace(go.Scatter(x=fan["Age"],y=fan["P75"],line=dict(width=0),
                    fill="tonexty",fillcolor="rgba(22,124,117,.17)",name="Middle 50% range"))
    mc_fig.add_trace(go.Scatter(x=fan["Age"],y=fan["Median"],line=dict(color="#167C75",width=3),
                    name="Typical simulated outcome"))
    mc_fig.add_trace(go.Scatter(x=projection["Age"],y=projection["Balance (today's money)"],
                    line=dict(color="#B77C38",dash="dash",width=2),name="Steady-return estimate"))
    mc_fig.add_vline(x=int(retirement_age),line_dash="dot",line_color="#8A9EA9")
    chart(mc_fig,x_label="Your age",y_label=f"Portfolio ({CURRENCY}, today's money)",height=400)
    st.caption("The shaded area covers the 10th to 90th percentile at each age. The green line is the median. "
               "The dashed gold line assumes a fixed return every year. Simulations assume fixed inflation and independent annual returns.")

    with st.expander("Ways to improve your retirement plan"):
        cards([
            ("Monthly saving required",money(needed_per_month),"For the steady-return goal"),
            ("Earliest modeled retirement",str(earliest_age) if earliest_age else "Not reached", "At the selected target spending"),
            ("Sustainable monthly spending",money(supported_income),"Steady-return assumption"),
            ("Monthly saving for ~80% success",money(savings_goal_80["monthly_contribution_needed"]),"Illustrative Monte Carlo target"),
        ])
        st.caption("An 80% modeled threshold is not a recommended risk level. Higher contributions may improve success, but not guarantee it.")
        st.dataframe(retirement_scenarios,hide_index=True,use_container_width=True)
        savings_build=projection[projection["Age"]<=int(retirement_age)].copy()
        savings_build["Starting savings + deposits"]=(
            retirement_savings+(savings_build["Age"]-int(current_age))*12*retirement_contribution
        )
        contribution_fig=go.Figure()
        contribution_fig.add_trace(go.Scatter(x=savings_build["Age"],
            y=savings_build["Starting savings + deposits"],name="Your deposits",
            line=dict(color="#557FA8",width=3)))
        contribution_fig.add_trace(go.Scatter(x=savings_build["Age"],
            y=savings_build["Balance (today's money)"],name="Portfolio incl. growth",
            line=dict(color="#167C75",width=3)))
        chart(contribution_fig,x_label="Age",y_label=f"Savings ({CURRENCY})",height=320)

    with st.expander("Retirement life simulator and annual cash flow"):
        st.caption("At retirement, saving contributions stop. The portfolio keeps earning modeled returns while funding monthly spending.")
        life=go.Figure()
        life.add_trace(go.Scatter(x=[int(retirement_age)]+retirement_yearly["Age"].tolist(),
             y=[planned_balance]+retirement_yearly["Ending Balance"].tolist(),
             line=dict(color="#167C75",width=3),name="Portfolio remaining"))
        life_view=st.selectbox("Retirement chart",["Remaining portfolio","Annual growth and withdrawals"],
                               key="retirement_cashflow_chart")
        if life_view=="Remaining portfolio":
            chart(life,x_label="Age",y_label=f"Balance ({CURRENCY}, today's money)",height=320)
        else:
            cf_fig=go.Figure()
            cf_fig.add_trace(go.Bar(x=retirement_yearly["Age"],
                y=retirement_yearly["Investment Growth"],name="Investment growth",marker_color="#167C75"))
            cf_fig.add_trace(go.Bar(x=retirement_yearly["Age"],
                y=-retirement_yearly["Actual Withdrawals"],name="Spending funded",marker_color="#B77C38"))
            cf_fig.update_layout(barmode="relative")
            chart(cf_fig,x_label="Age",y_label=f"Annual cash flow ({CURRENCY})",height=320)
        paged_table(retirement_yearly,key="retirement_yearly")
        download_csv("Download annual retirement cash flow CSV",retirement_yearly,"retirement_life_annual.csv")
        download_csv("Download monthly retirement cash flow CSV",retirement_monthly,"retirement_life_monthly.csv")

    with st.expander("Inflation and purchasing power"):
        st.caption("Today's money is purchasing power; nominal money is the amount printed on future bills.")
        at_retirement=inflation_table.loc[inflation_table["Age"]==int(retirement_age)].iloc[0]
        cards([
            ("Spending today",money(target_income),"Monthly, today's money"),
            (f"Cost at age {retirement_age}",money(float(at_retirement["Monthly Spending - Future Money"])),"Nominal money"),
            (f"Cost at age {planning_age}",money(float(inflation_table.iloc[-1]["Monthly Spending - Future Money"])),"Nominal money"),
            ("Inflation assumption",f"{inflation:.1f}%", "Per year, editable"),
        ])
        purchasing=go.Figure()
        purchasing.add_trace(go.Scatter(x=inflation_table["Age"],
             y=inflation_table["Monthly Spending - Today's Money"],name="Today's purchasing power",
             line=dict(color="#167C75",width=3)))
        purchasing.add_trace(go.Scatter(x=inflation_table["Age"],
             y=inflation_table["Monthly Spending - Future Money"],name="Future nominal cost",
             line=dict(color="#B77C38",width=3)))
        chart(purchasing,x_label="Age",y_label=f"Monthly spending ({CURRENCY})",height=340)
        download_csv("Download inflation projection CSV",inflation_table,"inflation_projection.csv")

    # Inflation shock is modeled even if its detail expander is closed so PDF stays accurate.
    with st.expander("Inflation shock simulator"):
        st.caption("Compare normal inflation with a temporary inflation surge starting at retirement.")
        l,r=st.columns(2,gap="large")
        shock_options=inflation_shock_presets(inflation)
        with l:
            shock_inflation=st.select_slider("Inflation during shock (%)",options=shock_options,
                         value=shock_options[1],key=f"inflation_shock_{CURRENCY_CODE}")
        with r:
            available_years=[y for y in [1,3,5,10] if y <= int(planning_age)-int(retirement_age)]
            shock_duration=st.select_slider("Duration of shock (years)",options=available_years,
                          value=5 if 5 in available_years else available_years[-1])
        shock_result=inflation_shock_projection(current_age=int(current_age),retirement_age=int(retirement_age),
                     planning_age=int(planning_age),starting_portfolio_real=planned_balance,
                     monthly_spending_real=target_income,annual_nominal_return_pct=expected_return,
                     baseline_inflation_pct=inflation,shock_inflation_pct=float(shock_inflation),
                     shock_years=int(shock_duration))
        cards([
            ("Ending balance, normal",money(shock_result["baseline_ending_balance"]),"Steady inflation"),
            ("Ending balance, shock",money(shock_result["shock_ending_balance"]),"Temporary higher inflation"),
            ("Extra unfunded spending",money(max(0.,shock_result["shock_total_shortfall"]-shock_result["baseline_total_shortfall"])),"Over retirement"),
            ("Extra monthly cost at horizon",money(max(0.,shock_result["shock_end_monthly_nominal_spending"]-shock_result["baseline_end_monthly_nominal_spending"])),"Nominal money"),
        ])
        shock_yearly=shock_result["yearly"]
        shock_fig=go.Figure()
        shock_fig.add_trace(go.Scatter(x=shock_yearly["Age"],y=shock_yearly["Base balance (today's money)"],
                  name="Normal",line=dict(color="#167C75",width=3)))
        shock_fig.add_trace(go.Scatter(x=shock_yearly["Age"],y=shock_yearly["Shock balance (today's money)"],
                  name="Inflation shock",line=dict(color="#B77C38",width=3,dash="dash")))
        chart(shock_fig,x_label="Age",y_label=f"Portfolio ({CURRENCY}, today's money)",height=340)
        st.caption("Investment returns remain unchanged during the shock. The higher price level persists after inflation normalizes. "
                   "This deterministic scenario does not recalculate Monte Carlo probabilities.")
        download_csv("Download inflation shock CSV",shock_yearly,"inflation_shock.csv")

    # Ensure the same shock settings feed the PDF even when the expander is closed.
    retirement_insights=[
        (f"Steady-return savings fund spending through age {planning_age}." if lasts_to_horizon
         else f"With current spending, steady-return savings run short near age {depletion_age:.1f}."),
        f"Modeled monthly saving required: {money(needed_per_month)}; extra above current saving: {money(additional_saving)}.",
        f"{simulation['sustain_probability']:.1%} of {simulations} simulated paths fund every withdrawal through age {planning_age}.",
        "Results assume no pensions, taxes, investment fees, or flexible spending; all savings and spending use today's money.",
    ]
    with st.expander("Projection tables and downloads"):
        paged_table(projection,key="retirement_projection_table")
        download_csv("Download yearly retirement projection CSV",projection,"retirement_projection.csv")
        download_csv("Download Monte Carlo percentiles CSV",fan,"monte_carlo_percentiles.csv")

# ================ RELATED LOAN DECISION =================
comparison_extra=extra_monthly if extra_monthly>0 else scheduled_payment*.05
invest_comparison=compare_mortgage_vs_investing(loan_amount,interest_rate,loan_years,
                                                  comparison_extra,expected_return,loan_start)
investing_rate_cases=mortgage_investing_return_scenarios(loan_amount,interest_rate,loan_years,
                                                          comparison_extra,expected_return,loan_start)
investment_insights=[
    f"Under a fixed return, {invest_comparison['winner']} has a modeled ending advantage of {money(abs(invest_comparison['difference']))}.",
    f"Compared interest-rate break-even: {invest_comparison['breakeven_effective_annual_pct']:.2f}% effective annually; "
    f"assumed investment return: {expected_return:.2f}% nominal.",
]
with loan_tab:
    with st.expander("Optional: repay your loan early or invest instead?"):
        st.caption("Both scenarios use the same monthly budget. The investment rate comes from Retirement assumptions.")
        cards([
            ("Monthly cash budget",money(invest_comparison["monthly_budget"]),"Same in both strategies"),
            ("Invest-extra portfolio",money(invest_comparison["invest_portfolio"]),"At loan maturity"),
            ("Prepay-first portfolio",money(invest_comparison["prepay_portfolio"]),"At loan maturity"),
            ("Modeled advantage",money(abs(invest_comparison["difference"])),invest_comparison["winner"]),
        ])
        wealth=invest_comparison["table"]
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=wealth["Month"],y=wealth["Invest Strategy Net Wealth"],
                         name="Invest spare cash",line=dict(color="#557FA8",width=3)))
        fig.add_trace(go.Scatter(x=wealth["Month"],y=wealth["Prepay Strategy Net Wealth"],
                         name="Prepay then invest",line=dict(color="#167C75",width=3)))
        chart(fig,x_label="Loan month",y_label=f"Net financial wealth ({CURRENCY})",height=350)
        st.caption("This comparison excludes the value of items bought with the loan and assumes steady returns, no fees, and no taxes. "
                   "It is not an investment recommendation.")
        st.dataframe(investing_rate_cases,hide_index=True,use_container_width=True)
        download_csv("Download loan vs investing CSV",wealth,"loan_vs_investing.csv")

# ================ UNCHANGED PDF ENGINE =================
report_data=generate_pdf_report(
    code=CURRENCY_CODE,
    loan={"amount":loan_amount,"rate":interest_rate,"years":loan_years,
          "extra":extra_monthly,"payment":scheduled_payment,"start_date":loan_start,
          "payoff_date":chosen_stats["payoff_date"],"standard_interest":standard_stats["interest"],
          "interest_saved":saved_interest,"months_saved":months_saved},
    retirement={"current_age":int(current_age),"retirement_age":int(retirement_age),
          "planning_age":int(planning_age),"savings":retirement_savings,"contribution":retirement_contribution,
          "income":target_income,"return":expected_return,"inflation":inflation,
          "volatility":volatility,"bank_deposit":bank_deposit_rate,
          "planned_balance":planned_balance,"target":portfolio_target,"needed":needed_per_month,
          "difference":difference,"earliest_age":earliest_age if earliest_age is not None else "Not found",
          "simulations":int(simulations),"reach_probability":simulation["reach_target_probability"],
          "sustain_probability":simulation["sustain_probability"]},
    loan_rate_sensitivity=rate_scenarios,loan_extra_sensitivity=extra_scenarios,
    loan_milestones=milestones,investment_sensitivity=investing_rate_cases,
    savings_goal=savings_goal_80,retirement_sensitivity=retirement_scenarios,
    investing=invest_comparison,base_loan_schedule=standard,chosen_loan_schedule=chosen,
    retirement_projection_df=projection,loan_insights=loan_insights,
    retirement_insights=retirement_insights,investment_insights=investment_insights,
    retirement_life_df=retirement_yearly,inflation_df=inflation_table,inflation_shock=shock_result,
)
with st.sidebar:
    st.divider()
    st.markdown("**Download your report**")
    st.download_button("Download financial PDF",report_data,
                       file_name="financial_future_planner_report.pdf",mime="application/pdf",
                       use_container_width=True)
    st.caption("Includes both planners, scenario assumptions, and detailed projections.")
    st.divider()
    st.caption("Educational estimates. Not personal financial advice.")
with retirement_tab:
    st.download_button("Download full PDF report",report_data,
                       file_name="financial_future_planner_report.pdf",mime="application/pdf")
st.caption("Financial Future Planner · Munkhjin Bataa · Returns and projections are not guaranteed.")
