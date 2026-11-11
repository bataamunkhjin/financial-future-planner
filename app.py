"""Financial Future Planner — a two-tab Streamlit class / portfolio project.

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
    earliest_target_age,
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
    simulated_savings_goal,
    mortgage_investing_return_scenarios,
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
    .block-container {max-width: 1260px; padding-top: 2rem; padding-bottom: 3rem;}
    h1, h2, h3 {letter-spacing: -.02em;}
    [data-testid="stMetric"] {
        background: rgba(125, 145, 165, .08);
        padding: 16px 18px;
        border-radius: 12px;
        border: 1px solid rgba(125, 145, 165, .16);
    }
    [data-testid="stMetricValue"] {font-size: 1.65rem;}
    .subtle {color: #8291a2; font-size: 0.95rem;}
    [data-testid="stExpander"] {border-radius: 12px;}
    [data-testid="stMetricDelta"] {font-size: .9rem;}
    @media (max-width: 760px) {
        .block-container {padding-top: 1rem;}
        [data-testid="stMetricValue"] {font-size: 1.3rem;}
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
                max_value: float = 10_000_000_000_000.0) -> float:
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
        help="Commas are added when you press Enter or click outside. You can type with or without commas.",
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
        margin=dict(l=8, r=12, t=15, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.13, x=0),
        hovermode="x unified",
        font=dict(size=12),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(135,147,166,.16)", zeroline=False, title=y_label)
    return fig


st.title("📈 Financial Future Planner")
st.markdown("**Plan your debt. Stress-test your savings. Understand the trade-offs.**")
st.caption(
    "Enter a few key numbers, then explore repayment strategies, retirement readiness, "
    "automatically generated scenarios, and interactive charts."
)
st.sidebar.caption("Figures are estimates, not personalized financial advice.")
st.sidebar.caption("No bank account, sign-in, API key, or external data connection is required.")

loan_tab, retirement_tab = st.tabs(["🏠 Mortgage / Loan Planner", "🌱 Retirement Planner"])

# ────────────────────────── LOAN TAB ──────────────────────────
with loan_tab:
    st.subheader("What will your loan really cost?")
    st.caption("Four essential inputs. Monetary fields add commas after pressing Enter or clicking outside.")

    with st.container(border=True):
        a, b, c, d = st.columns(4)
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
                f"Extra monthly payment ({CURRENCY})", name="extra_monthly",
                min_value=0.0, max_value=10_000_000_000.0,
                default=300_000.0 if IS_MNT else 200.0,
            )

        with st.expander("Advanced mortgage costs and loan start date (optional)"):
            st.caption(
                "Taxes, insurance, and PMI affect monthly housing cash flow, not the "
                "principal-and-interest amortization calculation."
            )
            x, y, z, w = st.columns(4)
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

    st.markdown("#### Repayment charts")
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("**Remaining balance**")
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
        st.plotly_chart(plot_layout(fig, y_label=f"Balance ({CURRENCY})"), use_container_width=True)
    with right:
        st.markdown("**Annual principal versus interest · standard loan**")
        annual = standard.groupby("Year", as_index=False)[["Principal", "Interest"]].sum()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=annual["Year"], y=annual["Principal"], name="Principal", marker_color="#10b981"))
        fig.add_trace(go.Bar(x=annual["Year"], y=annual["Interest"], name="Interest", marker_color="#f59e0b"))
        fig.update_layout(barmode="stack")
        fig.update_xaxes(title="Loan year")
        st.plotly_chart(plot_layout(fig, y_label=f"Annual payment ({CURRENCY})"), use_container_width=True)

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
    st.caption(
        "Rate scenarios are hypothetical quotes for a *new* fixed-rate loan. "
        "Existing fixed-rate mortgages do not automatically reprice when interest rates change. "
        "The entered extra payment stays unchanged in each scenario."
    )

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
        c1, c2, c3, c4, c5 = st.columns(5)
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
                f"Target monthly income ({CURRENCY})", name="target_income",
                min_value=1.0, max_value=10_000_000_000.0,
                default=3_000_000.0 if IS_MNT else 1_500.0,
            )

        with st.expander("Advanced retirement assumptions (optional)"):
            st.caption("Illustrative assumptions, not forecasts or guaranteed performance.")
            v1, v2, v3, v4, v5 = st.columns(5)
            with v1:
                expected_return = st.number_input("Annual nominal return (%)", min_value=-10.0, max_value=30.0, value=7.0, step=0.5)
            with v2:
                inflation = st.number_input("Annual inflation (%)", min_value=0.0, max_value=30.0, value=2.5, step=0.5)
            with v3:
                withdrawal_rate = st.number_input("Initial withdrawal rate (%)", min_value=1.0, max_value=10.0, value=4.0, step=0.25)
            with v4:
                volatility = st.number_input("Annual volatility (%)", min_value=0.0, max_value=60.0, value=15.0, step=1.0)
            with v5:
                planning_age = st.number_input(
                    "Plan through age", min_value=int(retirement_age) + 1,
                    max_value=105, value=max(90, int(retirement_age) + 1), step=1,
                )
            simulations = st.select_slider("Monte Carlo scenarios", options=[250, 500, 1000, 2000], value=1000)
            st.caption(
                "Savings and withdrawals are held constant in today's money, meaning their nominal "
                "amounts rise with inflation. Fixed inflation is assumed in simulations."
            )

    months_to_retire = int((retirement_age - current_age) * 12)
    real_rate = real_monthly_return(expected_return, inflation)
    planned_balance = grow_savings(retirement_savings, retirement_contribution, months_to_retire, real_rate)
    portfolio_target = 12 * target_income / (withdrawal_rate / 100)
    difference = planned_balance - portfolio_target
    needed_per_month = required_monthly_contribution(retirement_savings, months_to_retire, portfolio_target, real_rate)
    projected_contributions = retirement_savings + retirement_contribution * months_to_retire
    investment_growth = planned_balance - projected_contributions
    supported_income = planned_balance * (withdrawal_rate / 100) / 12
    heuristic_target_age = earliest_target_age(
        int(current_age), retirement_savings, retirement_contribution,
        portfolio_target, real_rate, max_age=int(planning_age),
    )
    feasible_retirement = earliest_feasible_retirement_age(
        int(current_age), int(planning_age), retirement_savings, retirement_contribution,
        target_income, real_rate, withdrawal_rate,
    )
    earliest_age = feasible_retirement["age"] if feasible_retirement else None
    retirement_scenarios = retirement_what_if_scenarios(
        int(current_age), int(retirement_age), int(planning_age),
        retirement_savings, retirement_contribution, target_income,
        expected_return, inflation, withdrawal_rate,
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
    savings_goal_80 = simulated_savings_goal(
        int(current_age), int(retirement_age), retirement_savings,
        retirement_contribution, portfolio_target, expected_return,
        inflation, volatility, simulations=int(simulations),
        target_probability=0.80, seed=42,
    )

    st.markdown("#### Retirement snapshot")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Portfolio at retirement · real", money(planned_balance))
    r2.metric("Portfolio needed · withdrawal rule", money(portfolio_target))
    r3.metric("Monthly income supported", money(supported_income))
    r4.metric("Readiness · withdrawal rule", "On track" if difference >= 0 else "Shortfall", money(difference))

    with st.container(border=True):
        j1, j2, j3, j4 = st.columns(4)
        j1.metric("Monthly saving needed", money(needed_per_month))
        j2.metric("Additional saving / month", money(max(0.0, needed_per_month - retirement_contribution)))
        j3.metric("Estimated investment growth", money(investment_growth))
        j4.metric("Earliest modeled eligible age", str(earliest_age) if earliest_age is not None else f"Not by {planning_age}")
        st.caption(
            f"All amounts shown in today's {currency_choice.split(' ')[0]} purchasing power. "
            f"Portfolio target = target income × 12 ÷ {withdrawal_rate:.2f}% initial withdrawal rate. "
            "The earliest modeled eligible age requires both this withdrawal-rule target and "
            "enough funds to cover target withdrawals through the planning age under a constant return. "
            "Neither measure guarantees successful retirement."
        )
        st.caption(
            f"Withdrawal-rule target alone is first reached at age "
            f"{heuristic_target_age if heuristic_target_age is not None else 'beyond the planning horizon'}. "
            "The more conservative eligibility test also checks constant-return withdrawal funding."
        )

    st.markdown("#### Probability-based savings goal")
    with st.container(border=True):
        st.caption("Illustrative 80% chance of reaching the **initial withdrawal-rule portfolio target**, under the simulation's assumptions.")
        g1, g2, g3 = st.columns(3)
        g1.metric("Savings / month for ~80% target chance", money(savings_goal_80["monthly_contribution_needed"]))
        g2.metric("Extra saving needed / month", money(savings_goal_80["monthly_increase_needed"]))
        g3.metric("Current modeled chance of target", f"{savings_goal_80['current_reach_probability']:.1%}")
        st.progress(min(1.0, max(0.0, savings_goal_80["current_reach_probability"])),
                    text="Share of simulated paths reaching the initial portfolio target")
        st.caption(
            "The 80% goal is a fixed educational example, not a recommended risk tolerance. "
            "This checks only the target portfolio at retirement. It does NOT mean an 80% "
            "chance of funding all retirement withdrawals. Returns and inflation are uncertain."
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
    p1.metric("Simulations reaching target at retirement", f"{100 * simulation['reach_target_probability']:.1f}%")
    p2.metric(f"Simulations funding withdrawals through age {planning_age}", f"{100 * simulation['sustain_probability']:.1f}%")
    p3.metric(
        "Constant-return income depletion",
        f"Around age {depletion_age:.1f}" if depletion_age is not None else f"Not through age {planning_age}",
    )

    st.markdown("#### Automatic retirement what-if scenarios")
    show_retirement_scenarios = retirement_scenarios.copy()
    for col in ["Monthly Savings", "Portfolio", "Surplus / Shortfall", "Monthly Income (rule)"]:
        show_retirement_scenarios[col] = show_retirement_scenarios[col].map(money)
    for col in ["Return (%)", "Inflation (%)"]:
        show_retirement_scenarios[col] = show_retirement_scenarios[col].map(lambda x: f"{x:.1f}%")
    st.dataframe(show_retirement_scenarios, use_container_width=True, hide_index=True)
    st.caption(
        "Each what-if scenario changes only one assumption from your base plan. "
        "Portfolio values and target income are in today's purchasing power; "
        "return and inflation changes are in percentage points (pp), not percentages of the rate."
    )

    st.markdown("#### Personalized retirement insights")
    retirement_insights = []
    if difference >= 0:
        retirement_insights.append(
            f"At the assumed constant return, your projected portfolio exceeds "
            f"the {withdrawal_rate:.2f}% withdrawal-rule target by {money(difference)}."
        )
    else:
        retirement_insights.append(
            f"At the assumed constant return, your plan falls short of the withdrawal-rule "
            f"target by {money(-difference)}. Increasing real monthly savings by "
            f"approximately {money(max(0.0, needed_per_month - retirement_contribution))} "
            "may close that modeled gap."
        )
    retirement_insights.append(
        (f"The earliest modeled eligible retirement age is {earliest_age} under "
         f"the constant-return and age-{planning_age} spending assumptions."
         if earliest_age is not None else
         f"No whole-year retirement age through {planning_age-1} meets both modeled "
         "funding tests with current contributions.")
    )
    retirement_insights.append(
        f"{100 * simulation['reach_target_probability']:.1f}% of simulations reach the "
        f"withdrawal-rule target by planned retirement, while "
        f"{100 * simulation['sustain_probability']:.1f}% fund all modeled monthly "
        f"withdrawals through age {planning_age}. These are separate measures."
    )
    retirement_insights.append(
        f"To reach the withdrawal-rule portfolio target in roughly 80% of the same "
        f"simulated paths, the modeled contribution is {money(savings_goal_80['monthly_contribution_needed'])} "
        f"per month in today's money (an additional {money(savings_goal_80['monthly_increase_needed'])}). "
        "This target probability is NOT the lifetime spending-success probability."
    )
    retirement_insights.append(
        "Simulated results use fixed inflation and independent annual market returns. "
        "Taxes, fees, pensions and spending changes could change actual outcomes."
    )
    for idx, line in enumerate(retirement_insights):
        if idx == 0 and difference < 0:
            st.warning(line)
        elif idx == 0:
            st.success(line)
        else:
            st.info(line)

    with st.expander("Understand the retirement calculations · for your class presentation"):
        st.markdown(r"""
**1. Nominal to real (inflation-adjusted) return**

$$r_{real,monthly}=\left(\frac{1+r_{nominal}}{1+i}\right)^{1/12}-1$$

Here annual nominal return $r_{nominal}$ and annual inflation $i$ are decimals. Savings and spending stay constant in **today's purchasing power**.

**2. Initial withdrawal-rule target**

$$\text{Portfolio target}=\frac{12\times\text{target monthly income}}{\text{withdrawal rate}}$$

This is a rule of thumb; it does not establish that the funds will last.

**3. Monte Carlo simulation**

For each simulated path, the model generates annual investment returns, converts them into monthly real growth, adds deposits until retirement, and models monthly withdrawals afterwards. The **target probability** and **spending sustainability probability** are calculated separately.

**4. Savings goal for ~80% of simulated paths**

For each path, the retirement balance equals the grown starting savings plus monthly deposits multiplied by their accumulation factor. Solving that equation for the contribution gives a required amount for each path. The app takes the 80th percentile of those amounts.
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
        "withdrawal_rate": withdrawal_rate, "return": expected_return,
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
    st.caption("Includes both tabs, loan and retirement what-if scenarios, milestones, stress tests and insights.")
    st.divider()
    st.caption("**Teacher demo:** open the project's TEACHER_GUIDE.md in Cursor for a short walkthrough and formulas.")

with retirement_tab:
    st.markdown("#### Download your financial report")
    st.download_button(
        "⬇ Download full loan + retirement PDF report",
        data=report_data,
        file_name="financial_future_planner_report.pdf",
        mime="application/pdf",
    )


st.divider()
st.caption("Financial Future Planner • Streamlit class project • Educational estimates only")
