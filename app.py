"""Financial Future Planner — two-tab, offline mortgage and retirement tool.

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
)
from report import generate_pdf_report


st.set_page_config(
    page_title="Financial Future Planner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Clean two-tab layout with spacious charts. */
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
    .planner-hero .hero-eyebrow {color: #99efe0; font-size: .89rem; letter-spacing: .05em; font-weight: 750; margin: 0 0 8px;}
    .hero-header {display:flex;justify-content:space-between;align-items:center;gap:22px;position:relative;z-index:1;}
    .hero-copy {min-width:0;flex:1;}
    .university-logo-wrap {background:#ffffff;padding:12px 15px;border-radius:14px;flex-shrink:0;box-shadow:0 5px 16px rgba(0,0,0,.10);}
    .university-logo {width:min(290px,100%);height:auto;display:block;}
    .hero-subtext {max-width:580px;}

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
        .hero-header {flex-direction:column-reverse;align-items:flex-start;gap:15px;}
        .university-logo {width:220px;}
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


# The user-provided American University of Mongolia logo is embedded locally so
# uploading only app.py to GitHub still renders the exact image without a URL.
AUM_LOGO_BASE64 = (
    "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"
)
logo_markup = (
    '<div class="university-logo-wrap"><img class="university-logo" '
    f'src="data:image/png;base64,{AUM_LOGO_BASE64}" '
    'alt="American University of Mongolia logo"></div>'
)

hero_html = """<section class="planner-hero">
  <div class="hero-header">
    <div class="hero-copy">
      <p class="hero-eyebrow">Munkhjin Bataa</p>
      <h1>Financial Future Planner</h1>
      <p class="hero-subtext">Understand borrowing costs. Plan your retirement with clarity.</p>
      <div class="chip-row">
        <span class="chip">🏠 Mortgage &amp; Loan</span>
        <span class="chip">🌱 Retirement Planning</span>
        <span class="chip">📄 PDF Reports</span>
      </div>
    </div>
    __SCHOOL_LOGO__
  </div>
</section>"""
st.markdown(hero_html.replace("__SCHOOL_LOGO__", logo_markup), unsafe_allow_html=True)
st.caption("Two planners | 4 loan inputs + 5 retirement inputs | No external market data or account needed.")
st.sidebar.caption("Figures are educational estimates, not personalized financial advice.")
st.sidebar.caption("All calculations work offline. Currency selection changes labels, not exchange rates.")

loan_tab, retirement_tab = st.tabs(["🏠 Mortgage / Loan Planner", "🌱 Retirement Planner"])

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
    fan = simulation["fan"]  # Retained for the Monte Carlo percentile CSV export.
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

# ─────────────────── DOWNLOADABLE TWO-PLANNER PDF ───────────────────

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
    inflation_df=inflation_table,
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
    st.caption("Includes your loan and retirement results, scenarios, and inflation analysis.")
    st.divider()
    st.caption("Retirement return and inflation assumptions are educational estimates, not guarantees.")

with retirement_tab:
    st.markdown("#### Download your financial report")
    st.download_button(
        "⬇ Download full loan + retirement PDF report",
        data=report_data,
        file_name="financial_future_planner_report.pdf",
        mime="application/pdf",
    )


st.divider()
st.caption("Financial Future Planner · Munkhjin Bataa · Educational estimates; not financial advice")
