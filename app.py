"""Financial Future Planner — three-tab Streamlit class / portfolio project.

Run: python -m streamlit run app.py
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from finance import (
    grow_savings,
    loan_payment,
    loan_schedule,
    loan_stats,
    monte_carlo_projection,
    real_monthly_return,
    required_monthly_contribution,
    retirement_projection,
    loan_rate_scenarios,
    annual_loan_scenario,
    earliest_feasible_retirement_age,
    retirement_what_if_scenarios,
    compare_mortgage_vs_investing,
    loan_payoff_milestones,
    simulated_lifetime_savings_goal,
    drawdown_portfolio_requirement,
    mortgage_investing_return_scenarios,
    retirement_life_schedule,
    inflation_purchasing_power,
    model_supported_monthly_spending,
)
from report import generate_pdf_report
from portfolio_ui import render_investment_tab, cached_fx
from savings_comparison import compare_bank_and_investment


st.set_page_config(
    page_title="Financial Future Planner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* v4.3 visual refresh: spacious full-width charts and simpler chart navigation. */
    :root {--ink:#142c41;--ocean:#047e8d;--mint:#16b59b;--edge:#dce8ed;}
    html,body,[data-testid="stAppViewContainer"] {font-family: Inter, "Segoe UI", Arial, sans-serif;}
    .block-container {max-width: 1380px; padding-top: 1.1rem; padding-bottom: 3rem;}
    [data-testid="stAppViewContainer"] {background:linear-gradient(180deg,#f2f8fc 0%,#f9fbfd 36%,#fff 100%);}
    section[data-testid="stSidebar"] {background:linear-gradient(180deg,#edf6f8,#f8fbfc);border-right:1px solid #dbe6eb;}
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {line-height:1.55;}
    .block-container h4 {color:#17374f; padding-left:12px; border-left:4px solid #1a9f9e; margin-top:1.7rem; margin-bottom: .75rem;}
    .block-container h3 {color:#102c43;}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {border-color:#dce9ed !important;}
    [data-testid="stPlotlyChart"] {background:#fff;border:1px solid #e1ebef;border-radius:16px;padding:8px 10px;box-shadow:0 6px 24px rgba(11,51,71,.035);}
    [data-testid="stDataFrame"] {border-radius:12px;overflow:hidden;}
    .insight-strip{background:#f0f8fa;border:1px solid #d7ebed;padding:13px 17px;border-radius:14px;color:#284658;margin:12px 0 18px;line-height:1.55;}
    .section-kicker {font-size:.72rem;font-weight:800;letter-spacing:.11em;color:#168487;text-transform:uppercase;margin:10px 0 2px;}
    .section-intro {font-size:.9rem;color:#627989;margin:0 0 16px;}
    .chip-row{display:flex;gap:8px;flex-wrap:wrap;margin:13px 0 0;}
    .chip{border:1px solid rgba(255,255,255,.28);padding:5px 10px;border-radius:30px;font-size:.78rem;color:#e3fbf9;background:rgba(255,255,255,.11);}
    .viz-label{font-size:1.02rem;font-weight:750;color:#1e465a;margin:16px 0 5px;}
    /* Charts are given their own breathing space and no longer compete in narrow columns. */
    [data-testid="stPlotlyChart"] {margin:12px 0 20px;}
    [data-testid="stTabs"] [data-baseweb="tab-list"] {gap: 8px;}
    [data-testid="stTabs"] button {border-radius:9px 9px 0 0;}


    h1, h2, h3, h4 {letter-spacing: -.026em;}
    .planner-hero {
        position:relative;overflow:hidden;
        background: linear-gradient(113deg, #102c46 0%, #13516b 56%, #007e83 100%);
        border-radius: 22px; padding: 30px 34px; color: #fff;
        margin-bottom: 1.2rem; box-shadow: 0 15px 36px rgba(11,49,70,.16);
    }
    .planner-hero::after {content:"";position:absolute;width:310px;height:310px;right:-125px;top:-165px;border:54px solid rgba(173,255,227,.075);border-radius:50%;pointer-events:none;}
    .planner-hero h1 {color: #fff; margin: 0; font-size: 2.0rem; line-height: 1.25;}
    .planner-hero p {color: #dcefeb; margin: 8px 0 0; font-size: .99rem;}
    .asset-hero {background:linear-gradient(114deg,#12344b,#087c82);color:white;padding:25px 29px;border-radius:20px;margin:8px 0 14px;box-shadow:0 10px 28px rgba(20,61,80,.11);}
    .asset-hero h2 {font-size:1.65rem;color:white;margin:4px 0 8px;}
    .asset-hero p {margin:0;color:#d8f2f0;font-size:.96rem;}
    .asset-eyebrow {font-size:.7rem;font-weight:800;letter-spacing:.12em;color:#9ee9dd;}
    .linked-ribbon {padding:17px 20px;border:1px solid #c8e4e5;border-left:5px solid #078e93;border-radius:13px;background:#eff9f9;display:flex;flex-direction:column;gap:5px;margin:20px 0;color:#173d4f;}
    .linked-ribbon span {color:#597987;font-size:.89rem;line-height:1.5;}
    .planner-hero .hero-eyebrow {color: #8ee2cc; font-size: .76rem; letter-spacing: .12em; font-weight: 800; margin: 0 0 6px;}
    [data-testid="stMetric"] {
        background: #fff; padding: 16px; border-radius: 16px;
        border: 1px solid #dce9eb; min-height: 116px;
        box-shadow:0 6px 17px rgba(20,61,80,.04);
    }
    [data-testid="stMetricValue"] {font-size: 1.53rem; letter-spacing: -.035em;color:#143749;}
    [data-testid="stMetricLabel"] {color:#5d7888;font-weight:650;font-size:.88rem;}
    [data-testid="stMetricLabel"] {line-height: 1.25;}
    [data-testid="stTabs"] button[aria-selected="true"] {font-weight: 800;color:#007f87;border-bottom:3px solid #139d97;}
    [data-testid="stTabs"] button {padding:12px 17px;font-weight:650;}
    [data-testid="stExpander"] {border-radius: 12px;}
    [data-testid="stMetricDelta"] {font-size: .9rem;}
    .section-note {color:#586a74; font-size: .91rem;}
    @media (max-width: 760px) {
        .block-container {padding-top: .7rem;}
        .planner-hero {padding: 23px;}
        .chip-row {gap:5px;}
        .planner-hero h1 {font-size: 1.5rem;}
        [data-testid="stMetricValue"] {font-size: 1.22rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

CURRENCIES = {"USD ($)": "$", "MNT (₮)": "₮", "EUR (€)": "€"}
st.sidebar.header("⚙️ App settings")
currency_choice = st.sidebar.selectbox(
    "Currency / number labels",
    list(CURRENCIES),
    help="Choose the symbol for your inputs and results. No foreign exchange conversion is performed.",
)
CURRENCY = CURRENCIES[currency_choice]
IS_MNT = currency_choice.startswith("MNT")


def money(value: float, decimals: int = 0) -> str:
    if decimals:
        return f"{CURRENCY}{value:,.{decimals}f}"
    return f"{CURRENCY}{value:,.0f}"


# Money fields are text inputs because Streamlit number_input's format must be numeric.
# Comma grouping is normalized in an on_change callback BEFORE the app reruns.
_MONEY_FORMAT = re.compile(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{0,2})?\Z")


def parse_money_text(text: str, min_value: float = 0.0,
                     max_value: float = 10_000_000_000_000.0) -> Decimal:
    """Validate a monetary entry, accepting correct grouping and up to two decimals."""
    value_text = str(text).strip()
    if not _MONEY_FORMAT.fullmatch(value_text):
        raise ValueError("Enter a number such as 5,000,000 or 5,000,000.50 (up to 2 decimals).")
    try:
        number = Decimal(value_text.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("Enter a valid number.") from exc
    if not number.is_finite() or not Decimal(str(min_value)) <= number <= Decimal(str(max_value)):
        raise ValueError(f"Enter an amount between {min_value:,.0f} and {max_value:,.0f}.")
    return number


def format_money_text(value: Decimal | float, min_decimals: int = 0) -> str:
    """Format without discarding user-entered cents; MNT defaults to whole units."""
    number = Decimal(str(value))
    explicit_places = max(0, -number.as_tuple().exponent)
    # Whole tugrik defaults shouldn't display trailing .0 or .00, but any
    # nonzero fractional amount retains its supplied decimal precision.
    places = min_decimals if number == number.to_integral_value() else max(min_decimals, explicit_places)
    if places > 2:
        raise ValueError("Monetary values can contain at most two decimal places.")
    return f"{number:,.{places}f}"


def _normalize_money_input(key: str, value_key: str, error_key: str,
                           min_value: float, max_value: float,
                           min_decimals: int) -> None:
    """Called by Streamlit before rerendering, so editing the widget key is safe."""
    try:
        amount = parse_money_text(st.session_state[key], min_value, max_value)
    except ValueError as exc:
        st.session_state[error_key] = str(exc)
        return  # Keep last valid value and clearly show the error beside the field.
    st.session_state[key] = format_money_text(amount, min_decimals)
    st.session_state[value_key] = float(amount)
    st.session_state.pop(error_key, None)


def money_input(label: str, *, name: str, default: float, min_value: float = 0.0,
                max_value: float = 10_000_000_000_000.0,
                help_text: str | None = None) -> float:
    """Grouped text input with per-currency state and a safe numeric result."""
    code = currency_choice.split(" ")[0]
    key = f"money_{code}_{name}"
    value_key = f"{key}_last_valid"
    error_key = f"{key}_error"
    min_decimals = 0 if IS_MNT else 2
    if key not in st.session_state:
        st.session_state[key] = format_money_text(default, min_decimals)
        st.session_state[value_key] = float(default)
    st.text_input(
        label, key=key,
        help=(help_text + " " if help_text else "") +
             "Commas are added when you press Enter or click outside. You can type with or without commas.",
        on_change=_normalize_money_input,
        args=(key, value_key, error_key, min_value, max_value, min_decimals),
    )
    if error_key in st.session_state:
        st.error(f"{st.session_state[error_key]} Using the last valid amount: "
                 f"{format_money_text(st.session_state[value_key], min_decimals)}")
    return float(st.session_state[value_key])


def months_as_text(months: int) -> str:
    years, leftover = divmod(int(months), 12)
    return f"{years}y {leftover}m" if years else f"{leftover}m"


def plot_layout(fig: go.Figure, height: int = 350, y_label: str | None = None) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=40, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.13, x=0, font=dict(size=12)),
        hovermode="x unified",
        font=dict(family="Arial, sans-serif", size=12, color="#334e62"),
        colorway=["#0d8f93", "#335e98", "#f29c56", "#8675bf", "#a4b8c7"],
        hoverlabel=dict(bgcolor="#ffffff", font_size=12),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#e3eaf0", ticks="outside", tickcolor="#d5e1e7")
    fig.update_yaxes(gridcolor="rgba(135,147,166,.14)", zeroline=False, title=y_label, separatethousands=True)
    return fig


st.markdown(
    """<section class="planner-hero">
      <p class="hero-eyebrow">FINANCIAL FUTURE PLANNER &nbsp; / &nbsp; LINKED PLANNING EDITION v5.1</p>
      <h1>Make confident financial decisions.</h1>
      <p>Clear numbers, richer charts, and a better view of the road ahead.</p>
      <div class="chip-row"><span class="chip">🏠 Loan insights</span><span class="chip">🌱 Retirement planning</span><span class="chip">📊 Multi-asset investing</span><span class="chip">📉 Risk scenarios</span><span class="chip">📄 PDF reporting</span></div>
    </section>""",
    unsafe_allow_html=True,
)
st.caption(
    "Three planners | 4 loan inputs + 5 retirement inputs | multi-asset analysis | PDF reports. "
    "Loan/retirement currencies change labels only; investments use quoted USD prices and FX when available."
)
st.sidebar.caption("Figures are estimates, not personalized financial advice.")
st.sidebar.caption("Loans and retirement work offline; investment live quotes require Yahoo Finance access. No sign-in or API key is needed.")

loan_tab, retirement_tab, investment_tab = st.tabs(["🏠 Mortgage / Loan Planner", "🌱 Retirement Planner", "📊 Investments"])

# ────────────────────────── LOAN TAB ──────────────────────────
with loan_tab:
    st.subheader("What will your loan really cost?")
    st.caption("Four essential inputs. Monetary fields add commas after pressing Enter or clicking outside.")

    with st.container(border=True):
        # Align the four widget controls along one baseline even when
        # their native Streamlit widget types have different label spacing.
        a, b, c, d = st.columns(4, vertical_alignment="bottom")
        with a:
            loan_amount = money_input(
                f"Loan amount ({CURRENCY})", name="loan_amount",
                min_value=1.0, max_value=1_000_000_000_000.0,
                default=250_000_000.0 if IS_MNT else 150_000.0,
            )
        with b:
            interest_rate = st.number_input(
                "Annual interest rate (%)", min_value=0.0, max_value=50.0,
                value=16.0 if IS_MNT else 6.5, step=0.25, format="%.2f",
            )
        with c:
            loan_years = st.slider("Loan term (years)", min_value=1, max_value=40, value=20 if IS_MNT else 30)
        with d:
            extra_monthly = money_input(
                f"Extra payment ({CURRENCY})", name="extra_monthly",
                min_value=0.0, max_value=10_000_000_000.0,
                default=300_000.0 if IS_MNT else 200.0,
                help_text="Extra amount paid every month on top of your regular loan payment; applied to principal.",
            )

        with st.expander("Advanced mortgage costs and loan start date (optional)"):
            st.caption(
                "Taxes, insurance, and PMI affect monthly housing cash flow, not the "
                "principal-and-interest amortization calculation."
            )
            x, y, z, w = st.columns(4, vertical_alignment="bottom")
            with x:
                loan_start = st.date_input("Loan starts", value=date.today(), min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
            with y:
                monthly_tax = money_input(f"Property tax / month ({CURRENCY})", name="monthly_tax", default=0.0)
            with z:
                monthly_insurance = money_input(f"Insurance / month ({CURRENCY})", name="monthly_insurance", default=0.0)
            with w:
                monthly_pmi = money_input(f"PMI / month ({CURRENCY})", name="monthly_pmi", default=0.0)
            st.caption("PMI is held constant until payoff in this simplified model; actual cancellation rules differ.")

    scheduled_payment = loan_payment(loan_amount, interest_rate, loan_years)
    standard = loan_schedule(loan_amount, interest_rate, loan_years, 0, loan_start)
    chosen = loan_schedule(loan_amount, interest_rate, loan_years, extra_monthly, loan_start)
    standard_stats = loan_stats(standard, loan_amount)
    chosen_stats = loan_stats(chosen, loan_amount)
    saved_interest = max(0.0, standard_stats["interest"] - chosen_stats["interest"])
    months_saved = standard_stats["months"] - chosen_stats["months"]

    st.markdown("#### Loan snapshot")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Scheduled monthly P&I", money(scheduled_payment, 2))
    m2.metric("Total interest · standard", money(standard_stats["interest"]))
    m3.metric("Interest saved with extra", money(saved_interest))
    m4.metric("Payoff time saved", months_as_text(months_saved))

    with st.container(border=True):
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Monthly outflow incl. extra", money(scheduled_payment + extra_monthly + monthly_tax + monthly_insurance + monthly_pmi, 2))
        q2.metric("Payoff date · with extra", chosen_stats["payoff_date"].strftime("%b %Y"))
        q3.metric("Total loan payments · with extra", money(chosen_stats["paid"]))
        q4.metric("Principal vs. interest · standard", f"{100 * standard_stats['interest_to_principal']:.1f}%")
        st.caption(
            "P&I means principal and interest. Monthly outflow includes any optional taxes/insurance/PMI. "
            "Principal-vs-interest percentage is total standard interest divided by original loan principal. "
            "Payoff assumes the first scheduled payment occurs one month after the loan start date."
        )

    # Keep charts separated vertically so nothing is squeezed into narrow columns.
    # Cost allocation is a horizontal stacked bar: easier to read than a small donut.
    st.markdown('<p class="section-kicker">Your mortgage, visualized</p>', unsafe_allow_html=True)
    st.markdown("#### Loan cost at a glance")
    st.caption("Your original principal and the interest you will pay with the selected extra payment.")
    loan_total = loan_amount + chosen_stats["interest"]
    interest_share = chosen_stats["interest"] / loan_total if loan_total > 0 else 0
    principal_share = loan_amount / loan_total if loan_total > 0 else 0
    allocation = go.Figure()
    allocation.add_trace(go.Bar(
        y=["Cost allocation"], x=[loan_amount], orientation="h",
        name="Original principal", marker_color="#078f96",
        text=f"Principal {principal_share:.1%}", textposition="inside",
        insidetextanchor="middle",
        hovertemplate=f"Original principal: {CURRENCY}{loan_amount:,.2f}<extra></extra>",
    ))
    allocation.add_trace(go.Bar(
        y=["Cost allocation"], x=[chosen_stats["interest"]], orientation="h",
        name="Loan interest", marker_color="#f2a36b",
        text=f"Interest {interest_share:.1%}" if interest_share >= 0.12 else "",
        textposition="inside", insidetextanchor="middle",
        hovertemplate=f"Total interest: {CURRENCY}{chosen_stats['interest']:,.2f}<extra></extra>",
    ))
    allocation.update_layout(barmode="stack", bargap=0.25, height=170,
                             uniformtext_minsize=11, uniformtext_mode="hide")
    allocation.update_xaxes(visible=False, range=[0, loan_total * 1.02] if loan_total > 0 else None)
    allocation.update_yaxes(visible=False, fixedrange=True)
    st.plotly_chart(plot_layout(allocation, height=170), use_container_width=True)
    st.caption(
        f"Total repaid with extra payments: **{money(chosen_stats['paid'])}** · "
        f"Original principal: **{money(loan_amount)}** · "
        f"Interest: **{money(chosen_stats['interest'])}**. "
        "The bar represents principal and interest only (not taxes, insurance or PMI)."
    )

    st.markdown("#### Interest accumulated over the loan")
    st.caption("Compare total interest paid over time with and without extra principal payments.")
    fig_interest = go.Figure()
    fig_interest.add_trace(go.Scatter(
        x=[0] + standard["Month"].tolist(), y=[0] + standard["Cumulative Interest"].tolist(),
        name="Standard loan", mode="lines", line=dict(color="#8295a8", width=3),
        hovertemplate="Month %{x}: %{y:,.0f}<extra></extra>",
    ))
    fig_interest.add_trace(go.Scatter(
        x=[0] + chosen["Month"].tolist(), y=[0] + chosen["Cumulative Interest"].tolist(),
        name="With extra payments", mode="lines", line=dict(color="#0d9b92", width=3),
        hovertemplate="Month %{x}: %{y:,.0f}<extra></extra>",
    ))
    fig_interest.update_xaxes(title="Months from loan start")
    st.plotly_chart(
        plot_layout(fig_interest, height=365, y_label=f"Interest paid ({CURRENCY})"),
        use_container_width=True,
    )
    st.divider()

    st.markdown("#### Repayment timeline")
    st.caption("Switch views to explore remaining debt or how each year's payments are allocated.")
    balance_tab, payment_mix_tab = st.tabs(["Remaining loan balance", "Annual principal & interest"])
    with balance_tab:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[0] + standard["Month"].tolist(),
            y=[loan_amount] + standard["Ending Balance"].tolist(),
            mode="lines", line=dict(color="#64748b", width=3),
            name="Standard payment",
        ))
        fig.add_trace(go.Scatter(
            x=[0] + chosen["Month"].tolist(),
            y=[loan_amount] + chosen["Ending Balance"].tolist(),
            mode="lines", line=dict(color="#10b981", width=3),
            name="With extra payment",
        ))
        fig.update_xaxes(title="Months since loan start")
        st.plotly_chart(plot_layout(fig, height=360, y_label=f"Balance ({CURRENCY})"), use_container_width=True)
    with payment_mix_tab:
        annual = standard.groupby("Year", as_index=False)[["Principal", "Interest"]].sum()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=annual["Year"], y=annual["Principal"], name="Principal", marker_color="#10b981"))
        fig.add_trace(go.Bar(x=annual["Year"], y=annual["Interest"], name="Interest", marker_color="#f59e0b"))
        fig.update_layout(barmode="stack")
        fig.update_xaxes(title="Loan year")
        st.plotly_chart(plot_layout(fig, height=360, y_label=f"Annual payment ({CURRENCY})"), use_container_width=True)

    st.markdown("#### Automatic extra-payment scenarios")
    extra_scenarios = annual_loan_scenario(
        loan_amount, interest_rate, loan_years, extra_monthly, loan_start
    )
    display_extra = extra_scenarios.copy()
    for field in ["Extra / Month", "Monthly Budget", "Total Interest", "Interest Saved"]:
        display_extra[field] = display_extra[field].map(lambda v: money(v, 2))
    display_extra["Payoff Time"] = extra_scenarios["Payoff Months"].map(months_as_text)
    display_extra["Payoff Date"] = display_extra["Payoff Date"].astype(str)
    st.dataframe(
        display_extra[["Scenario", "Extra / Month", "Monthly Budget", "Payoff Time",
                       "Interest Saved", "Total Interest", "Payoff Date"]],
        hide_index=True, use_container_width=True,
    )

    st.markdown('<div class="viz-label">Interest saved under different extra-payment strategies</div>', unsafe_allow_html=True)
    fig_extra = go.Figure(go.Bar(
        x=extra_scenarios["Scenario"], y=extra_scenarios["Interest Saved"],
        marker=dict(color=["#b1c2cb" if i == 0 else "#16a2a0" for i in range(len(extra_scenarios))],
                    line=dict(width=0)),
        text=[money(v) for v in extra_scenarios["Interest Saved"]], textposition="outside",
        hovertemplate="%{x}<br>Interest saved: %{y:,.0f}<extra></extra>",
    ))
    fig_extra.update_layout(showlegend=False)
    st.plotly_chart(plot_layout(fig_extra, height=305, y_label=f"Interest saved ({CURRENCY})"), use_container_width=True)

    st.markdown("#### What if interest rates were different?")
    rate_scenarios = loan_rate_scenarios(
        loan_amount, interest_rate, loan_years, extra_monthly, loan_start
    )
    show_rates = rate_scenarios.copy()
    show_rates["Annual Rate"] = show_rates["Rate (%)"].map(lambda x: f"{x:.2f}%")
    show_rates["Monthly P&I"] = show_rates["Monthly P&I"].map(lambda x: money(x, 2))
    show_rates["Total Interest"] = show_rates["Total Interest"].map(money)
    show_rates["Payoff Date"] = show_rates["Payoff Date"].astype(str)
    st.dataframe(
        show_rates[["Scenario", "Annual Rate", "Monthly P&I", "Total Interest", "Payoff Date"]],
        hide_index=True, use_container_width=True,
    )
    fig_rates = go.Figure(go.Scatter(
        x=rate_scenarios["Rate (%)"], y=rate_scenarios["Monthly P&I"],
        name="Monthly payment", mode="lines+markers",
        line=dict(color="#0f8f99", width=3), marker=dict(size=10,color="#0f8f99",line=dict(color="#fff",width=2)),
        hovertemplate="Rate: %{x:.2f}%<br>Payment: %{y:,.2f}<extra></extra>",
    ))
    fig_rates.update_xaxes(title="Hypothetical annual interest rate (%)")
    st.plotly_chart(plot_layout(fig_rates, height=275, y_label=f"Monthly principal & interest ({CURRENCY})"),use_container_width=True)
    st.caption(
        "Rate scenarios are hypothetical quotes for a *new* fixed-rate loan. "
        "Existing fixed-rate mortgages do not automatically reprice when interest rates change. "
        "The entered extra payment stays unchanged in each scenario."
    )

    st.markdown("#### Your potential interest savings")
    reduction_ratio = saved_interest / standard_stats["interest"] if standard_stats["interest"] > 0 else 0.0
    st.progress(min(1.0,max(0.0,reduction_ratio)), text=f"{reduction_ratio:.1%} of standard loan interest avoided with your extra payment")
    st.markdown("#### Automatic loan insights")
    loan_insights = []
    if extra_monthly > 0:
        loan_insights.append(
            f"Putting {money(extra_monthly)} toward loan principal monthly saves "
            f"about {money(saved_interest)} in total interest and pays off "
            f"the loan {months_as_text(months_saved)} earlier."
        )
    else:
        suggested_extra = scheduled_payment * 0.10
        suggested_stats = loan_stats(
            loan_schedule(loan_amount, interest_rate, loan_years, suggested_extra, loan_start), loan_amount
        )
        loan_insights.append(
            f"Adding a hypothetical 10% extra payment ({money(suggested_extra)}/month) "
            f"could save {money(standard_stats['interest'] - suggested_stats['interest'])} in interest."
        )
    loan_insights.append(
        f"Standard loan interest totals {money(standard_stats['interest'])}, "
        f"or {standard_stats['interest_to_principal'] * 100:.1f}% of the borrowed principal."
    )
    if interest_rate >= 12:
        loan_insights.append(
            "The assumed nominal borrowing rate is high; prioritize affordable payments "
            "and emergency cash reserves before increasing prepayments."
        )
    for index, item in enumerate(loan_insights):
        (st.success if index == 0 and extra_monthly > 0 else st.info)(item)
    st.caption(
        "All loan results assume a fixed rate, monthly interest, no fees or prepayment "
        "penalties, and no missed payments. Extra payments reduce principal."
    )

    st.markdown("#### Loan payoff milestones")
    milestones = loan_payoff_milestones(chosen, loan_amount)
    milestones_display = milestones.copy()
    milestones_display["Payment Date"] = milestones_display["Payment Date"].astype(str)
    milestones_display["Principal Repaid"] = milestones_display["Principal Repaid"].map(money)
    milestones_display["Balance Remaining"] = milestones_display["Balance Remaining"].map(money)
    st.dataframe(milestones_display, hide_index=True, use_container_width=True)
    st.caption("Milestones refer to the percentage of original loan PRINCIPAL repaid, not total cash spent.")
    with st.expander("Understand the mortgage calculations · for your class presentation"):
        st.markdown(r"""
**1. Monthly fixed loan payment**

$$M=P\frac{r(1+r)^n}{(1+r)^n-1}$$

- $P$ = starting principal; $r$ = annual nominal interest rate divided by 12; $n$ = months.
- When the interest rate is zero, monthly payment is simply $P/n$.
- Monthly interest = remaining principal × monthly rate.
- Principal repaid = actual payment − monthly interest. Extra payments go to principal.
- The actual last payment is capped at the remaining balance plus interest.

**2. Break-even investment return**

The mortgage's effective annual borrowing rate is $((1+r)^{12}-1)\times100\%$.
This is the mathematical break-even fixed return **before** investment taxes, fees, risk or liquidity differences.
""")

    st.markdown("#### Monthly amortization schedule")
    display_schedule = chosen.copy()
    display_schedule["Payment Date"] = display_schedule["Payment Date"].astype(str)
    st.dataframe(
        display_schedule.style.format({
            col: "{:,.2f}" for col in display_schedule.select_dtypes(include="number").columns if col not in ("Month", "Year")
        }),
        use_container_width=True,
        hide_index=True,
        height=350,
    )
    st.download_button(
        "⬇ Download loan amortization CSV",
        data=display_schedule.to_csv(index=False).encode("utf-8-sig"),
        file_name="loan_amortization.csv",
        mime="text/csv",
    )

# ─────────────────────── RETIREMENT TAB ───────────────────────
with retirement_tab:
    st.subheader("Will your savings support retirement?")
    st.caption("Five essential inputs. Monetary fields add commas after pressing Enter or clicking outside; all values are in today's purchasing power.")

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns(5, vertical_alignment="bottom")
        with c1:
            current_age = st.number_input("Current age", min_value=18, max_value=80, value=25, step=1)
        with c2:
            retirement_age = st.number_input("Retirement age", min_value=int(current_age) + 1, max_value=90, value=max(60, int(current_age) + 1), step=1)
        with c3:
            retirement_savings = money_input(
                f"Current savings ({CURRENCY})", name="retirement_savings",
                min_value=0.0, max_value=10_000_000_000_000.0,
                default=30_000_000.0 if IS_MNT else 10_000.0,
            )
        with c4:
            retirement_contribution = money_input(
                f"Monthly savings ({CURRENCY})", name="retirement_contribution",
                min_value=0.0, max_value=10_000_000_000.0,
                default=1_000_000.0 if IS_MNT else 300.0,
            )
        with c5:
            target_income = money_input(
                f"Target income ({CURRENCY})", name="target_income",
                min_value=1.0, max_value=10_000_000_000.0,
                default=10_000_000.0 if IS_MNT else 1_500.0,
                help_text="The monthly income you want during retirement, in today's purchasing power.",
            )

        with st.expander("Advanced retirement assumptions (optional)"):
            st.caption("Illustrative assumptions, not forecasts or guaranteed performance.")
            v1, v2, v3, v4 = st.columns(4, vertical_alignment="bottom")
            with v1:
                expected_return = st.number_input("Annual nominal return (%)", min_value=-10.0, max_value=30.0, value=7.0, step=0.5)
            with v2:
                inflation = st.number_input("Annual inflation (%)", min_value=0.0, max_value=30.0, value=2.5, step=0.5)
            with v3:
                volatility = st.number_input("Annual volatility (%)", min_value=0.0, max_value=60.0, value=15.0, step=1.0)
            with v4:
                planning_age = st.number_input(
                    "Plan through age", min_value=int(retirement_age) + 1,
                    max_value=110, value=max(100, int(retirement_age) + 1), step=1,
                    help="Choose how long you want your savings to support retirement spending. This does not predict how long you will live.",
                )
            simulations = st.select_slider("Monte Carlo scenarios", options=[250, 500, 1000, 2000], value=1000)
            st.caption(
                "Savings and withdrawals are held constant in today's money, meaning their nominal "
                "amounts rise with inflation. Fixed inflation is assumed in simulations."
            )

    months_to_retire = int((retirement_age - current_age) * 12)
    real_rate = real_monthly_return(expected_return, inflation)
    planned_balance = grow_savings(retirement_savings, retirement_contribution, months_to_retire, real_rate)
    retirement_months = (int(planning_age) - int(retirement_age)) * 12
    # This target is derived from planned real spending and the chosen horizon.
    # Contributions cease at retirement; returns continue during withdrawals.
    portfolio_target = drawdown_portfolio_requirement(target_income, retirement_months, real_rate)
    difference = planned_balance - portfolio_target
    needed_per_month = required_monthly_contribution(retirement_savings, months_to_retire, portfolio_target, real_rate)
    projected_contributions = retirement_savings + retirement_contribution * months_to_retire
    investment_growth = planned_balance - projected_contributions
    supported_income = planned_balance / drawdown_portfolio_requirement(1.0, retirement_months, real_rate)
    feasible_retirement = earliest_feasible_retirement_age(
        int(current_age), int(planning_age), retirement_savings, retirement_contribution,
        target_income, real_rate,
    )
    earliest_age = feasible_retirement["age"] if feasible_retirement else None
    retirement_scenarios = retirement_what_if_scenarios(
        int(current_age), int(retirement_age), int(planning_age),
        retirement_savings, retirement_contribution, target_income,
        expected_return, inflation,
    )
    projection, depletion_age = retirement_projection(
        int(current_age), int(retirement_age), int(planning_age),
        retirement_savings, retirement_contribution, target_income,
        expected_return, inflation,
    )
    simulation = monte_carlo_projection(
        int(current_age), int(retirement_age), int(planning_age),
        retirement_savings, retirement_contribution, target_income,
        expected_return, inflation, volatility, portfolio_target,
        simulations=int(simulations), seed=42,
    )
    savings_goal_80 = simulated_lifetime_savings_goal(
        int(current_age), int(retirement_age), int(planning_age),
        retirement_savings, retirement_contribution, target_income,
        expected_return, inflation, volatility,
        simulations=int(simulations), target_probability=0.80, seed=42,
    )
    # v4: detailed post-retirement cashflows, inflation views, and simulated spending limits.
    retirement_monthly, retirement_yearly = retirement_life_schedule(
        planned_balance, int(retirement_age), int(planning_age), target_income,
        expected_return, inflation,
    )
    inflation_table = inflation_purchasing_power(
        projection, int(current_age), target_income, inflation,
    )
    safe_spending = model_supported_monthly_spending(
        int(current_age), int(retirement_age), int(planning_age),
        retirement_savings, retirement_contribution, target_income,
        expected_return, inflation, volatility,
        simulations=int(simulations), seed=42,
    )
    monthly_income_to_horizon = supported_income
    monthly_saving_to_horizon = needed_per_month
    additional_saving_to_horizon = max(0.0, needed_per_month - retirement_contribution)
    lasts_to_horizon = depletion_age is None

    st.markdown(f"#### Can you fund {money(target_income)}/month through age {planning_age}?")
    with st.container(border=True):
        if lasts_to_horizon:
            st.success(
                f"Yes under the constant-return assumptions: your balance supports "
                f"{money(target_income)} per month from age {retirement_age} through age {planning_age}."
            )
        else:
            st.warning(
                f"Not with the current savings plan. At {money(target_income)} per month "
                f"from age {retirement_age}, the constant-return model estimates "
                f"savings run short around age {depletion_age:.1f}, before age {planning_age}."
            )
        life1, life2, life3, life4 = st.columns(4)
        life1.metric(f"Money lasts to {planning_age}?", "Yes" if lasts_to_horizon else "No")
        life2.metric("Estimated funds run out", f"Age {depletion_age:.1f}" if depletion_age is not None else f"Beyond {planning_age}")
        life3.metric(f"Monthly spending sustainable to {planning_age}", money(monthly_income_to_horizon))
        life4.metric("Extra saving/month for this goal", money(additional_saving_to_horizon))
        st.caption(
            f"To fund the full {money(target_income)}/month through age {planning_age} under a "
            f"constant real return, the model estimates a portfolio of {money(portfolio_target)} "
            f"at retirement and total monthly saving of {money(monthly_saving_to_horizon)} "
            f"before retirement. This is a fixed-horizon drawdown calculation, not a guaranteed result."
        )
        st.caption(
            f"In {int(simulations):,} illustrative variable-return simulations, "
            f"{simulation['sustain_probability']:.1%} fully funded those withdrawals through age {planning_age}. "
            "That is a model estimate, not a guarantee; living to age 100 is not predicted."
        )

    st.markdown("#### Retirement snapshot")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Portfolio at retirement · real", money(planned_balance))
    r2.metric(f"Portfolio needed through age {planning_age}", money(portfolio_target))
    r3.metric("Monthly spending supported", money(supported_income))
    r4.metric("Readiness · spending horizon", "On track" if lasts_to_horizon else "Shortfall", money(difference))

    with st.container(border=True):
        j1, j2, j3, j4 = st.columns(4)
        j1.metric("Monthly saving needed", money(needed_per_month))
        j2.metric("Additional saving / month", money(max(0.0, needed_per_month - retirement_contribution)))
        j3.metric("Estimated investment growth", money(investment_growth))
        j4.metric("Earliest modeled retirement age", str(earliest_age) if earliest_age is not None else f"Not by {planning_age}")
        st.caption(
            f"All amounts are in today's {currency_choice.split(' ')[0]} purchasing power. "
            f"The capital target is the present value of {money(target_income)} monthly withdrawals "
            f"from age {retirement_age} through age {planning_age} at the assumed constant real return. "
            "Remaining funds continue earning returns during retirement. This is not a guarantee."
        )

    st.markdown("#### Your progress toward retirement")
    funded_share = planned_balance / portfolio_target if portfolio_target > 0 else 1.0
    st.progress(min(1.0,max(0.0,funded_share)), text=f"{funded_share:.1%} of modeled fixed-return retirement capital target")
    st.caption("The funded ratio compares projected savings at retirement with the capital needed to finance your chosen spending horizon at a constant real return. It is not a success probability.")

    st.markdown("#### Savings deposits versus investment growth")
    st.caption("Your deposits and your investment balance are separated to show the effect of compounding before retirement. All amounts are inflation-adjusted.")
    before_retirement = projection.loc[projection["Age"] <= int(retirement_age)].copy()
    before_retirement["Deposits including starting savings"] = (
        retirement_savings + (before_retirement["Age"] - int(current_age)) * 12 * retirement_contribution
    )
    fig_build = go.Figure()
    fig_build.add_trace(go.Scatter(
        x=before_retirement["Age"], y=before_retirement["Deposits including starting savings"],
        name="Your deposits + starting savings", mode="lines", line=dict(color="#91a5b8",width=3),
        hovertemplate="Age %{x}: %{y:,.0f}<extra></extra>"
    ))
    fig_build.add_trace(go.Scatter(
        x=before_retirement["Age"], y=before_retirement["Balance (today's money)"],
        name="Total projected portfolio", mode="lines", line=dict(color="#098f96",width=4),
        hovertemplate="Age %{x}: %{y:,.0f}<extra></extra>"
    ))
    fig_build.update_xaxes(title="Age before retirement")
    st.plotly_chart(plot_layout(fig_build, height=340, y_label=f"Value ({CURRENCY}, today's money)"), use_container_width=True)

    st.markdown("#### Savings goal for 80% modeled spending success")
    with st.container(border=True):
        st.caption(f"Savings needed for approximately 80% of simulated paths to pay every monthly withdrawal through age {planning_age}.")
        g1, g2, g3 = st.columns(3)
        g1.metric("Savings / month for ~80% success", money(savings_goal_80["monthly_contribution_needed"]))
        g2.metric("Extra saving needed / month", money(savings_goal_80["monthly_increase_needed"]))
        g3.metric("Current modeled spending success", f"{savings_goal_80['current_sustain_probability']:.1%}")
        st.progress(min(1.0, max(0.0, savings_goal_80["current_sustain_probability"])),
                    text="Share of simulated paths funding all monthly spending")
        st.caption(
            "The 80% goal is an illustrative planning threshold, not a recommended risk tolerance. "
            "Success depends on the assumed market return distribution, constant inflation, and selected planning age."
        )

    st.markdown("#### Model-supported monthly spending")
    st.caption(
        "How much monthly spending would be funded in at least 80%, 90%, or 95% of the "
        "simulated market paths? These are scenario thresholds, not guaranteed safe withdrawals."
    )
    spending_levels = safe_spending["options"]
    s80, s90, s95 = st.columns(3)
    for col, (_, option) in zip((s80, s90, s95), spending_levels.iterrows()):
        col.metric(
            f"At least {option['Success Target']:.0%} modeled success",
            money(option["Monthly Spending"]),
        )
    fig_spend = go.Figure()
    fig_spend.add_trace(go.Bar(
        x=[f"{p:.0%}" for p in spending_levels["Success Target"]],
        y=spending_levels["Monthly Spending"],
        marker_color=["#159579", "#2483a5", "#405f8b"],
        name="Simulated spending capacity",
        hovertemplate="%{x} success target: %{y:,.0f}<extra></extra>",
    ))
    fig_spend.add_hline(
        y=target_income, line_dash="dot", line_color="#db773a",
        annotation_text="Your target", annotation_position="top right",
    )
    fig_spend.update_xaxes(title="Required share of simulated paths")
    st.plotly_chart(
        plot_layout(fig_spend, height=310, y_label=f"Monthly spending ({CURRENCY}, today's money)"),
        use_container_width=True,
    )
    st.caption(
        f"Your entered {money(target_income)}/month is funded in "
        f"{safe_spending['current_spending_success']:.1%} of these same simulated paths. "
        "More conservative percentages generally imply a lower monthly spending limit. "
        "The simulation assumes fixed inflation and independent annual market returns."
    )

    st.markdown("#### Retirement trajectory and uncertainty")
    fan = simulation["fan"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fan["Age"], y=fan["P90"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=fan["Age"], y=fan["P10"], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(99,102,241,.13)", name="10th–90th percentile", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(x=fan["Age"], y=fan["P75"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=fan["Age"], y=fan["P25"], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(99,102,241,.23)", name="25th–75th percentile", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=fan["Age"], y=fan["Median"], mode="lines", name="Simulation median", line=dict(color="#6366f1", width=3),
    ))
    fig.add_trace(go.Scatter(
        x=projection["Age"], y=projection["Balance (today's money)"],
        mode="lines", name="Constant-return projection", line=dict(color="#10b981", dash="dash", width=2),
    ))
    fig.add_vline(x=retirement_age, line_dash="dot", line_color="#f59e0b")
    fig.add_annotation(x=retirement_age, y=1, yref="paper", text="Retirement", showarrow=False, yshift=15)
    fig.update_xaxes(title="Age")
    st.plotly_chart(plot_layout(fig, height=445, y_label=f"Portfolio in today's {CURRENCY}"), use_container_width=True)
    st.caption(
        f"Fan chart: {int(simulations):,} simulated return paths, with independent annual returns. "
        "Shaded bands show percentiles, not guaranteed outcomes. Dashed line assumes a constant annual return. "
        "After retirement, the target income is withdrawn monthly in today's money."
    )

    p1, p2, p3 = st.columns(3)
    p1.metric("Required monthly saving · fixed return", money(needed_per_month))
    p2.metric(f"Simulations funding withdrawals through age {planning_age}", f"{100 * simulation['sustain_probability']:.1f}%")
    p3.metric(
        "Constant-return income depletion",
        f"Around age {depletion_age:.1f}" if depletion_age is not None else f"Not through age {planning_age}",
    )

    st.markdown("#### Retirement Life Simulator")
    st.caption(
        "At retirement, deposits stop. Your portfolio continues earning the modeled return "
        "each month, then pays that month's living expenses. Figures below are in today's money."
    )
    yr_final = retirement_yearly.iloc[-1]
    unpaid_total = float(retirement_yearly["Unfunded Spending"].sum())
    first_unfunded = retirement_monthly.loc[retirement_monthly["Unfunded Spending"] > 0.01]
    if first_unfunded.empty:
        first_unfunded_label = f"Not by age {planning_age}"
    else:
        first_unfunded_label = f"Age {float(first_unfunded.iloc[0]['Age']):.1f}"
    l1, l2, l3, l4 = st.columns(4)
    l1.metric(f"Balance at age {planning_age}", money(float(yr_final["Ending Balance"])))
    l2.metric("Withdrawals actually funded", money(float(yr_final["Cumulative Withdrawals"])))
    l3.metric("First shortfall", first_unfunded_label)
    l4.metric("Unfunded lifetime spending", money(unpaid_total))

    life_age = [int(retirement_age)] + retirement_yearly["Age"].tolist()
    life_bal = [planned_balance] + retirement_yearly["Ending Balance"].tolist()
    fig_life = go.Figure()
    fig_life.add_trace(go.Scatter(
        x=life_age, y=life_bal, mode="lines", name="Retirement balance",
        line=dict(color="#128c79", width=3), fill="tozeroy", fillcolor="rgba(18,140,121,.10)",
        hovertemplate="Age %{x}: %{y:,.0f}<extra></extra>",
    ))
    fig_life.update_xaxes(title="Age during retirement")
    st.plotly_chart(
        plot_layout(fig_life, height=355, y_label=f"Remaining portfolio ({CURRENCY}, today's money)"),
        use_container_width=True,
    )
    st.markdown("**Yearly retirement cash flow**")
    show_life = retirement_yearly.copy()
    st.dataframe(
        show_life.style.format({
            "Starting Balance": "{:,.0f}", "Investment Growth": "{:,.0f}",
            "Planned Spending": "{:,.0f}", "Actual Withdrawals": "{:,.0f}",
            "Unfunded Spending": "{:,.0f}", "Ending Balance": "{:,.0f}",
            "Cumulative Withdrawals": "{:,.0f}",
        }),
        use_container_width=True, hide_index=True, height=300,
    )
    st.markdown("**Annual investment growth versus withdrawals**")
    cashflow_fig = go.Figure()
    cashflow_fig.add_trace(go.Bar(
        x=retirement_yearly["Age"], y=retirement_yearly["Investment Growth"],
        name="Investment growth",marker_color="#0d9792",
        hovertemplate="Age %{x}: %{y:,.0f}<extra></extra>",
    ))
    cashflow_fig.add_trace(go.Bar(
        x=retirement_yearly["Age"],y=-retirement_yearly["Actual Withdrawals"],
        name="Withdrawals funded",marker_color="#ed9865",
        hovertemplate="Age %{x}: %{customdata:,.0f}<extra></extra>",
        customdata=retirement_yearly["Actual Withdrawals"],
    ))
    cashflow_fig.update_layout(barmode="relative")
    cashflow_fig.update_xaxes(title="Age at end of retirement year")
    st.plotly_chart(plot_layout(cashflow_fig,height=350,y_label=f"Annual portfolio cash flow ({CURRENCY})"),use_container_width=True)
    st.caption("Withdrawals are shown below zero to distinguish cash leaving the portfolio. Returns continue after retirement, including years with investment losses.")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "⬇ Download annual retirement cash flow CSV",
            data=retirement_yearly.to_csv(index=False).encode("utf-8-sig"),
            file_name="retirement_life_annual.csv", mime="text/csv",
        )
    with d2:
        st.download_button(
            "⬇ Download monthly retirement cash flow CSV",
            data=retirement_monthly.to_csv(index=False).encode("utf-8-sig"),
            file_name="retirement_life_monthly.csv", mime="text/csv",
        )

    st.markdown("#### Inflation & Purchasing Power")
    st.caption(
        "Today's money shows purchasing power. Future (nominal) money includes inflation. "
        "Changing display units does not create real investment gains or change the retirement outcome."
    )
    at_retirement = inflation_table.loc[inflation_table["Age"] == int(retirement_age)].iloc[0]
    at_horizon = inflation_table.iloc[-1]
    pi1, pi2, pi3 = st.columns(3)
    pi1.metric("Target spending · today", money(target_income))
    pi2.metric(f"Same spending · at age {retirement_age}", money(float(at_retirement["Monthly Spending - Future Money"])))
    pi3.metric(f"Same spending · at age {planning_age}", money(float(at_horizon["Monthly Spending - Future Money"])))
    spending_tab, portfolio_tab = st.tabs(["Monthly spending: real vs. nominal", "Portfolio: real vs. nominal"])
    with spending_tab:
        fig_inflation = go.Figure()
        fig_inflation.add_trace(go.Scatter(
            x=inflation_table["Age"], y=inflation_table["Monthly Spending - Today's Money"],
            name="Today's purchasing power", line=dict(color="#138a7b", width=3),
        ))
        fig_inflation.add_trace(go.Scatter(
            x=inflation_table["Age"], y=inflation_table["Monthly Spending - Future Money"],
            name="Future nominal cost", line=dict(color="#d47b37", width=3),
        ))
        fig_inflation.update_xaxes(title="Age")
        st.plotly_chart(plot_layout(fig_inflation, height=365, y_label=f"Monthly spending ({CURRENCY})"), use_container_width=True)
    with portfolio_tab:
        fig_power = go.Figure()
        fig_power.add_trace(go.Scatter(
            x=inflation_table["Age"], y=inflation_table["Portfolio - Today's Money"],
            name="Portfolio · real", line=dict(color="#138a7b", width=3),
        ))
        fig_power.add_trace(go.Scatter(
            x=inflation_table["Age"], y=inflation_table["Portfolio - Future Money"],
            name="Portfolio · nominal", line=dict(color="#3a70a2", width=3),
        ))
        fig_power.update_xaxes(title="Age")
        st.plotly_chart(plot_layout(fig_power, height=365, y_label=f"Projected portfolio ({CURRENCY})"), use_container_width=True)
    with st.expander("See inflation-adjusted values by age"):
        money_cols = [col for col in inflation_table if "Portfolio - " in col or "Monthly Spending - " in col]
        fmt = {name: "{:,.0f}" for name in money_cols}
        fmt["Inflation Multiplier"] = "{:.3f}x"
        fmt["Purchasing Power of One Nominal Unit"] = "{:.3f}"
        st.dataframe(inflation_table.style.format(fmt), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇ Download inflation and purchasing power CSV",
            data=inflation_table.to_csv(index=False).encode("utf-8-sig"),
            file_name="inflation_purchasing_power.csv", mime="text/csv",
        )

    st.markdown("#### Automatic retirement what-if scenarios")
    show_retirement_scenarios = retirement_scenarios.copy()
    for col in ["Monthly Savings", "Portfolio", "Capital Needed", "Surplus / Shortfall", "Sustainable Monthly Income"]:
        show_retirement_scenarios[col] = show_retirement_scenarios[col].map(money)
    for col in ["Return (%)", "Inflation (%)"]:
        show_retirement_scenarios[col] = show_retirement_scenarios[col].map(lambda x: f"{x:.1f}%")
    show_retirement_scenarios["Funds Spending"] = show_retirement_scenarios["Funds Spending"].map({True: "Yes", False: "No"})
    st.dataframe(show_retirement_scenarios, use_container_width=True, hide_index=True)
    st.caption(
        "Each what-if scenario changes only one assumption from your base plan. "
        "Portfolio values and target income are in today's purchasing power; "
        "return and inflation changes are in percentage points (pp), not percentages of the rate."
    )

    st.markdown("#### Personalized retirement insights")
    retirement_insights = []
    if lasts_to_horizon:
        retirement_insights.append(
            f"Under a constant real return, the current plan funds {money(target_income)} "
            f"per month from age {retirement_age} through age {planning_age}. "
            f"The simulated share funding every withdrawal is {simulation['sustain_probability']:.1%}."
        )
    else:
        retirement_insights.append(
            f"At {money(target_income)} per month, constant-return savings run short around "
            f"age {depletion_age:.1f}, before age {planning_age}. "
            f"An additional {money(additional_saving_to_horizon)} per month before retirement "
            "would meet the fixed-return drawdown calculation, not eliminate market risk."
        )
    retirement_insights.append(
        (f"At the assumed constant return, the projected retirement balance exceeds "
         f"the capital needed to fund spending through age {planning_age} by {money(difference)}."
         if difference >= 0 else
         f"At the assumed constant return, the retirement portfolio falls short of the "
         f"age-{planning_age} spending requirement by {money(-difference)}.")
    )
    retirement_insights.append(
        (f"The earliest modeled retirement age is {earliest_age}, based on funding all "
         f"monthly withdrawals through age {planning_age} under a constant real return."
         if earliest_age is not None else
         f"No whole-year retirement age through {planning_age-1} funds all modeled "
         "withdrawals with current contributions under the fixed-return assumption.")
    )
    retirement_insights.append(
        f"{100 * simulation['sustain_probability']:.1f}% of {int(simulations):,} simulated "
        f"market-return paths fund every monthly withdrawal through age {planning_age}. "
        "It is not a guaranteed real-world probability."
    )
    retirement_insights.append(
        f"For approximately 80% simulated spending success, modeled monthly saving is "
        f"{money(savings_goal_80['monthly_contribution_needed'])} "
        f"(an additional {money(savings_goal_80['monthly_increase_needed'])} compared with the current plan)."
    )
    retirement_insights.append(
        f"Across {int(simulations):,} sampled market paths, modeled spending limits for 80%, 90% "
        f"and 95% success are {', '.join(money(v) for v in safe_spending['options']['Monthly Spending'])} "
        "per month in today's purchasing power. These values are not guaranteed safe withdrawals."
    )
    retirement_insights.append(
        "The model holds spending and saving constant in today's purchasing power, and ignores "
        "taxes, fees, pensions, flexible spending, and variable inflation."
    )
    for idx, line in enumerate(retirement_insights):
        if idx == 0 and not lasts_to_horizon:
            st.warning(line)
        elif idx == 0:
            st.success(line)
        else:
            st.info(line)

    with st.expander("Understand the retirement calculations · for your class presentation"):
        st.markdown(r"""
**1. Inflation-adjusted return**

$$r_{real,monthly}=\left(\frac{1+r_{nominal}}{1+i}\right)^{1/12}-1$$

Balances, contributions, and spending are expressed in **today's purchasing power**.

**2. Retirement portfolio needed to fund spending**

$$\text{Capital needed}=\sum_{m=1}^{N}\frac{\text{monthly spending}}{(1+r_{real,monthly})^m}$$

Here $N$ is the number of retirement months up to the chosen planning age. This assumes a constant return.

**3. Monthly retirement drawdown**

Every month, the portfolio **earns the modeled return**, then pays that month's withdrawal. Savings contributions stop at retirement. The program tracks whether any withdrawal cannot be paid in full.

**4. Monte Carlo simulation**

For each path, annual returns vary; monthly contributions continue only until retirement, and withdrawals are paid afterward. The success rate is the share of paths in which **every withdrawal** can be paid up to the chosen age.

**5. Savings goal for 80% simulated spending success**

The app calculates, for each return path, the retirement capital needed to pay every withdrawal and the monthly contribution required to build it. The 80th percentile of these path-by-path contributions is the approximately 80% success savings target. The simulated probability is not a guarantee.

**6. Retirement Life Simulator**

Each month after retirement: `closing balance = max(0, opening balance * (1 + real monthly return) - actual withdrawal)`. The app records investment growth, withdrawals actually funded, and any spending shortfall. Contributions are zero in retirement.

**7. Model-supported spending (80%, 90%, 95%)**

For each Monte Carlo path, the app computes the maximum constant-real monthly withdrawal the projected retirement savings could support through the planning age. The displayed threshold is a conservative empirical percentile. These are **model scenarios, not guaranteed safe withdrawal rates**.

**8. Purchasing power**

`Nominal future amount = amount in today's purchasing power * (1 + inflation) ^ years`. Both views describe the same real plan, not two different investment results.
""")

    st.markdown("#### Year-by-year balance projection")
    st.dataframe(
        projection.style.format({
            "Balance (today's money)": "{:,.2f}",
            "Cumulative Contributions": "{:,.2f}",
            "Cumulative Withdrawals": "{:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
        height=350,
    )
    z1, z2 = st.columns(2)
    with z1:
        st.download_button(
            "⬇ Download yearly retirement projection CSV",
            data=projection.to_csv(index=False).encode("utf-8-sig"),
            file_name="retirement_projection.csv",
            mime="text/csv",
        )
    with z2:
        st.download_button(
            "⬇ Download simulation percentiles CSV",
            data=fan.to_csv(index=False).encode("utf-8-sig"),
            file_name="retirement_monte_carlo_percentiles.csv",
            mime="text/csv",
        )

    st.caption(
        "Model limitations: no tax effects, pension benefits, fees, market correlations, variable inflation, "
        "or changing spending patterns. Simulations assume independent annual lognormal returns with fixed "
        "arithmetic mean and volatility. Historical returns and future results may differ substantially."
    )

# ───────────────── LINKED MORTGAGE VS INVESTING ─────────────────
# Running both tab calculations before this section allows us to reuse the
# Retirement tab's *existing* expected-return assumption: no fifth loan input.
comparison_extra = extra_monthly if extra_monthly > 0 else scheduled_payment * 0.05
invest_comparison = compare_mortgage_vs_investing(
    loan_amount, interest_rate, loan_years, comparison_extra, expected_return, loan_start
)
investing_rate_cases = mortgage_investing_return_scenarios(
    loan_amount, interest_rate, loan_years, comparison_extra, expected_return, loan_start
)
investment_insights = [
    f"With the same {money(invest_comparison['monthly_budget'])} monthly cash budget, "
    f"the modeled {invest_comparison['winner'].lower()} strategy finishes "
    f"{loan_years} years later with an advantage of {money(abs(invest_comparison['difference']))} "
    "in nominal financial assets.",
    f"The mortgage's effective annual borrowing rate is about "
    f"{invest_comparison['breakeven_effective_annual_pct']:.2f}% versus the assumed "
    f"{expected_return:.2f}% annual investment return. Both are model assumptions, "
    "and investment results are uncertain.",
]

with loan_tab:
    st.markdown("#### Mortgage prepayment versus investing")
    st.markdown(
        "**Should you put spare monthly cash toward your mortgage or invest it instead?** "
        "This comparison holds your total monthly cash budget constant under both strategies."
    )
    if extra_monthly == 0:
        st.info(
            f"Your extra payment is zero, so this example uses a hypothetical "
            f"5% of the scheduled payment ({money(comparison_extra)} per month) "
            "as money you could either invest or pay toward principal."
        )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monthly budget in both strategies", money(invest_comparison["monthly_budget"]))
    c2.metric("Invest extra · final portfolio", money(invest_comparison["invest_portfolio"]))
    c3.metric("Prepay first · final portfolio", money(invest_comparison["prepay_portfolio"]))
    c4.metric("Modeled advantage", money(abs(invest_comparison["difference"])), invest_comparison["winner"])

    wealth = invest_comparison["table"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=wealth["Month"], y=wealth["Invest Strategy Net Wealth"],
        name="Invest spare cash", line=dict(color="#6366f1", width=3)
    ))
    fig.add_trace(go.Scatter(
        x=wealth["Month"], y=wealth["Prepay Strategy Net Wealth"],
        name="Prepay, then invest", line=dict(color="#10b981", width=3)
    ))
    fig.update_xaxes(title="Months from loan start")
    st.plotly_chart(
        plot_layout(fig, height=380, y_label=f"Net financial wealth ({CURRENCY})"),
        use_container_width=True,
    )
    st.caption(
        "Net financial wealth = investment assets minus unpaid loan principal; "
        "home value is excluded because both strategies own the same property. "
        f"Investment return: {expected_return:.2f}% nominal/year, taken from the "
        "Retirement tab's Advanced assumptions. The same monthly loan-plus-spare-cash "
        "budget is allocated under both strategies, and any unused final payment is invested. "
        f"The comparison ends after {loan_years} years, when both mortgages are paid off. "
        "Fixed return, no fees or taxes, no loan prepayment fee or investment risk modeling. "
        "Investing has market risk and is not guaranteed to outperform paying down debt."
    )
    st.markdown("**Investment return stress test**")
    show_investing_cases = investing_rate_cases.copy()
    show_investing_cases["Investment Return (%)"] = show_investing_cases["Investment Return (%)"].map(lambda x: f"{x:.2f}%")
    for key in ("Invest Final", "Prepay Final", "Invest - Prepay"):
        show_investing_cases[key] = show_investing_cases[key].map(money)
    st.dataframe(show_investing_cases, hide_index=True, use_container_width=True)
    st.markdown("**Strategy advantage by assumed investment return**")
    difference_plot = go.Figure(go.Bar(
        x=investing_rate_cases["Scenario"], y=investing_rate_cases["Invest - Prepay"],
        marker_color=["#13a18f" if val >= 0 else "#df9a66" for val in investing_rate_cases["Invest - Prepay"]],
        hovertemplate="%{x}<br>Invest minus prepay: %{y:,.0f}<extra></extra>",
    ))
    difference_plot.add_hline(y=0,line_color="#8395a7",line_width=1)
    st.plotly_chart(plot_layout(difference_plot,height=280,y_label=f"Invest − prepay ({CURRENCY})"),use_container_width=True)
    st.caption(
        "Each row assumes a DIFFERENT constant investment return, not a predicted probability. "
        "The 'Loan return break-even' row uses the fixed mortgage's effective annual borrowing rate. "
        "Results exclude market volatility, taxes and fees."
    )
    for insight in investment_insights:
        st.info(insight)
    with st.expander("See month-by-month mortgage vs. investing results"):
        st.dataframe(wealth.style.format({
            col: "{:,.2f}" for col in wealth.select_dtypes(include="number").columns
            if col != "Month"
        }), hide_index=True, use_container_width=True, height=300)
        st.download_button(
            "⬇ Download strategy comparison CSV",
            wealth.to_csv(index=False).encode("utf-8-sig"),
            file_name="mortgage_vs_investing.csv", mime="text/csv",
        )

# ─────────────────── DOWNLOADABLE COMBINED PDF ───────────────────
# ────────────────── MULTI-ASSET INVESTMENT TAB ──────────────────
with investment_tab:
    render_investment_tab(currency_choice)

# ───────────── OPTIONAL BANK SAVINGS VS INVESTING COMPARISON ─────────────
# Placed AFTER the Investments tab is analyzed so its stored valuation is
# available immediately, even during the first completed portfolio analysis.
# It adds a section INSIDE Retirement; it does not create or remove any tabs.
with retirement_tab:
    st.markdown("#### Bank savings vs investing")
    st.markdown(
        '<div class="linked-ribbon"><b>Two ways to build your retirement savings</b>'
        '<span>Compare a bank deposit and an investment strategy using the same starting '
        'money, monthly savings, retirement date and monthly lifestyle budget. '
        'Only the assumed return differs.</span></div>',
        unsafe_allow_html=True,
    )
    linked_result = st.session_state.get("portfolio_result")
    linked_value = None
    linked_return = None
    linked_coverage = 0.0
    if isinstance(linked_result, dict):
        linked_summary = linked_result.get("summary") or {}
        linked_hist = linked_result.get("history") or {}
        linked_metrics = linked_hist.get("metrics") or {}
        linked_coverage = float(linked_summary.get("risk_coverage", 0.0))
        usd_value = float(linked_summary.get("total_value", 0.0))
        linked_fx = 1.0
        if currency_choice.split(" ")[0] != "USD":
            try:
                linked_fx = cached_fx(currency_choice.split(" ")[0])
            except Exception:
                linked_fx = None
        if linked_fx is not None and usd_value > 0:
            linked_value = usd_value * float(linked_fx)
        if (linked_metrics and linked_coverage >= 0.50
                and int(linked_metrics.get("weeks", 0)) >= 26):
            historical_rate = 100*float(linked_metrics["annualized_return"])
            if -30.0 <= historical_rate <= 30.0:
                linked_return = historical_rate

    with st.expander("Optional comparison assumptions", expanded=False):
        st.caption("These settings affect only this comparison, not your existing retirement projections.")
        bank_rate = st.number_input(
            "Bank annual interest assumption (%)", min_value=0.0, max_value=40.0,
            value=9.0 if IS_MNT else (3.0 if currency_choice.startswith("EUR") else 4.0),
            step=0.5, format="%.1f", key=f"bank_interest_{currency_choice[:3]}",
            help="Illustrative nominal deposit interest rate, not a live bank offer. Rates, taxes and bank terms can change.",
        )
        savings_sources = ["Your retirement savings input"]
        if linked_value is not None:
            savings_sources.extend([
                "Your analyzed investment portfolio instead",
                "Both balances (only if they are separate funds)",
            ])
        savings_source = st.selectbox("Starting money for this comparison", savings_sources,
                                      help="Portfolio value is converted from USD using the latest available FX estimate. Avoid counting the same investments twice.")
        return_sources = ["Your retirement expected-return assumption"]
        if linked_return is not None:
            return_sources.append("Historical listed-portfolio return (illustrative only)")
        return_source = st.selectbox("Investing return for this comparison", return_sources,
                                     help="A historical portfolio return is NOT a prediction; market returns fluctuate. Only listed assets with available history are included.")

    compare_initial = float(retirement_savings)
    if savings_source.startswith("Your analyzed") and linked_value is not None:
        compare_initial = float(linked_value)
    elif savings_source.startswith("Both") and linked_value is not None:
        compare_initial += float(linked_value)
    compare_investing_rate = float(linked_return if return_source.startswith("Historical") and linked_return is not None else expected_return)
    comparison_result = compare_bank_and_investment(
        current_age=int(current_age), retirement_age=int(retirement_age),
        planning_age=int(planning_age), starting_balance=compare_initial,
        monthly_saving=float(retirement_contribution), monthly_spending=float(target_income),
        bank_rate_pct=float(bank_rate), investing_rate_pct=compare_investing_rate,
        inflation_pct=float(inflation),
    )
    b1, b2, b3 = st.columns(3)
    b1.metric("Bank at retirement", money(comparison_result["retirement_balances"]["Bank"]))
    b2.metric("Investing at retirement", money(comparison_result["retirement_balances"]["Investing"]))
    b3.metric("Investing − bank", money(comparison_result["retirement_balances"]["Investing"]-comparison_result["retirement_balances"]["Bank"]))
    b4, b5 = st.columns(2)
    bank_age = comparison_result["first_shortfall_ages"]["Bank"]
    invest_age = comparison_result["first_shortfall_ages"]["Investing"]
    b4.metric("Bank funds monthly lifestyle", f"Through age {planning_age}" if bank_age is None else f"Until ~age {bank_age:.1f}")
    b5.metric("Investments fund monthly lifestyle", f"Through age {planning_age}" if invest_age is None else f"Until ~age {invest_age:.1f}")

    mode_col, period_col = st.columns(2)
    with mode_col:
        comparison_money_mode = st.selectbox("Display balances in", ["Today's purchasing power", "Future nominal money"], key="bank_compare_money_mode")
    with period_col:
        comparison_period = st.selectbox("Show period", ["Entire timeline", "Retirement years only"], key="bank_compare_phase")
    comparison_table = comparison_result["annual"]
    if comparison_period == "Retirement years only":
        comparison_table = comparison_table.loc[comparison_table["Age"] >= int(retirement_age)]
    suffix = "real" if comparison_money_mode.startswith("Today") else "nominal"
    bank_trace = f"Bank {suffix}"
    invest_trace = f"Investing {suffix}"
    fig_bank_compare = go.Figure()
    fig_bank_compare.add_trace(go.Scatter(
        x=comparison_table["Age"], y=comparison_table[bank_trace],
        name="Bank savings", mode="lines", line=dict(color="#305e90", width=3),
        hovertemplate="Age %{x:.0f}<br>Bank: %{y:,.0f}<extra></extra>",
    ))
    fig_bank_compare.add_trace(go.Scatter(
        x=comparison_table["Age"], y=comparison_table[invest_trace],
        name="Investing", mode="lines", line=dict(color="#099d91", width=3),
        hovertemplate="Age %{x:.0f}<br>Investing: %{y:,.0f}<extra></extra>",
    ))
    fig_bank_compare.add_vline(x=int(retirement_age), line_dash="dot", line_color="#c9a65c")
    fig_bank_compare.update_xaxes(title="Age")
    st.plotly_chart(plot_layout(fig_bank_compare, height=420, y_label=f"Portfolio value ({CURRENCY})"), use_container_width=True)
    st.caption(
        f"Bank rate {bank_rate:.1f}% vs investing return {compare_investing_rate:.1f}% nominal annually; "
        f"inflation {inflation:.1f}%. Both start with {money(compare_initial)} and save "
        f"{money(retirement_contribution)} monthly until age {retirement_age}, then seek "
        f"{money(target_income)} monthly in today's purchasing power through age {planning_age}. "
        "Savings and withdrawals rise with inflation in nominal terms. "
        "Constant returns, no fees/taxes or FX risk; bank rates may change and investments can lose value. "
        "This comparison is illustrative, not a risk-adjusted recommendation."
    )
    if linked_result:
        if linked_value is not None:
            st.info(
                f"Portfolio connection available: your current investment valuation is {money(linked_value)} "
                f"at the latest available USD/{currency_choice[:3]} conversion. "
                "Choose a portfolio starting-balance option above only if it doesn't double-count your retirement savings. "
                f"Historical risk metrics cover {linked_coverage:.0%} of your portfolio."
            )
        else:
            st.warning("The portfolio was analyzed, but no reliable currency conversion was available. "
                       "Its USD value is not combined with retirement balances in another currency.")
        if return_source.startswith("Historical"):
            st.warning("You selected a historical return from the listed subset of your portfolio. "
                       "It may not represent the whole portfolio or future returns; treat this as a stress scenario only.")
    st.download_button(
        "⬇ Download bank vs investing CSV",
        data=comparison_result["annual"].to_csv(index=False).encode("utf-8-sig"),
        file_name="bank_vs_investing_retirement.csv", mime="text/csv",
    )

# Existing loan + retirement combined PDF stays unchanged.
report_data = generate_pdf_report(
    code=currency_choice.split(" ")[0],
    loan={
        "amount": loan_amount, "rate": interest_rate, "years": loan_years,
        "extra": extra_monthly, "payment": scheduled_payment,
        "start_date": loan_start, "payoff_date": chosen_stats["payoff_date"],
        "standard_interest": standard_stats["interest"], "interest_saved": saved_interest,
        "months_saved": months_saved,
    },
    retirement={
        "current_age": int(current_age), "retirement_age": int(retirement_age),
        "planning_age": int(planning_age), "savings": retirement_savings,
        "contribution": retirement_contribution, "income": target_income,
        "return": expected_return,
        "inflation": inflation, "planned_balance": planned_balance,
        "target": portfolio_target, "needed": needed_per_month,
        "difference": difference,
        "earliest_age": earliest_age if earliest_age is not None else "Not found",
        "simulations": int(simulations),
        "reach_probability": simulation["reach_target_probability"],
        "sustain_probability": simulation["sustain_probability"],
    },
    loan_rate_sensitivity=rate_scenarios,
    loan_extra_sensitivity=extra_scenarios,
    loan_milestones=milestones,
    investment_sensitivity=investing_rate_cases,
    savings_goal=savings_goal_80,
    retirement_sensitivity=retirement_scenarios,
    investing=invest_comparison,
    base_loan_schedule=standard,
    chosen_loan_schedule=chosen,
    retirement_projection_df=projection,
    loan_insights=loan_insights,
    retirement_insights=retirement_insights,
    investment_insights=investment_insights,
    retirement_life_df=retirement_yearly,
    safe_spending=safe_spending,
    inflation_df=inflation_table,
    bank_comparison=comparison_result,
)
with st.sidebar:
    st.divider()
    st.subheader("📄 Financial report")
    st.download_button(
        "⬇ Download combined PDF",
        data=report_data,
        file_name="financial_future_planner_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
    st.caption("Includes mortgage, retirement, and bank vs investing comparisons. Download the separate portfolio PDF inside Investments.")
    st.divider()
    st.caption("Retirement assumptions and portfolio valuations are educational estimates, not guarantees.")

with retirement_tab:
    st.markdown("#### Download your financial report")
    st.download_button(
        "⬇ Download full loan + retirement PDF report",
        data=report_data,
        file_name="financial_future_planner_report.pdf",
        mime="application/pdf",
    )


st.divider()
st.caption("Financial Future Planner · v5.1 Linked Planning Edition · Educational estimates; not financial advice")
