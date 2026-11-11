"""Financial Future Planner — a two-tab Streamlit class / portfolio project.

Run: python -m streamlit run app.py
"""

from __future__ import annotations

from datetime import date
import io

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
)


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
st.markdown("**Two simple calculators. One clearer financial future.**")
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
    st.caption("Four essential inputs. All calculations update automatically.")

    with st.container(border=True):
        a, b, c, d = st.columns(4)
        with a:
            loan_amount = st.number_input(
                f"Loan amount ({CURRENCY})",
                min_value=1.0,
                max_value=1_000_000_000_000.0,
                value=250_000_000.0 if IS_MNT else 150_000.0,
                step=5_000_000.0 if IS_MNT else 1_000.0,
            )
        with b:
            interest_rate = st.number_input(
                "Annual interest rate (%)", min_value=0.0, max_value=50.0,
                value=16.0 if IS_MNT else 6.5, step=0.25, format="%.2f",
            )
        with c:
            loan_years = st.slider("Loan term (years)", min_value=1, max_value=40, value=20 if IS_MNT else 30)
        with d:
            extra_monthly = st.number_input(
                f"Extra monthly payment ({CURRENCY})", min_value=0.0,
                max_value=10_000_000_000.0,
                value=300_000.0 if IS_MNT else 200.0,
                step=50_000.0 if IS_MNT else 25.0,
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
                monthly_tax = st.number_input(f"Property tax / month ({CURRENCY})", min_value=0.0, value=0.0)
            with z:
                monthly_insurance = st.number_input(f"Insurance / month ({CURRENCY})", min_value=0.0, value=0.0)
            with w:
                monthly_pmi = st.number_input(f"PMI / month ({CURRENCY})", min_value=0.0, value=0.0)
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
    if extra_monthly > 0:
        modest_extra = extra_monthly / 2
        aggressive_extra = extra_monthly
        scenario_names = ["Standard", "Half selected extra", "Your selected extra"]
    else:
        modest_extra = scheduled_payment * 0.05
        aggressive_extra = scheduled_payment * 0.10
        scenario_names = ["Standard", "+5% of scheduled", "+10% of scheduled"]

    scenarios = []
    for label, extra in zip(scenario_names, [0, modest_extra, aggressive_extra]):
        s = loan_stats(loan_schedule(loan_amount, interest_rate, loan_years, extra, loan_start), loan_amount)
        scenarios.append({
            "Scenario": label,
            "Extra / month": money(extra, 2),
            "Monthly loan outflow": money(scheduled_payment + extra, 2),
            "Payoff time": months_as_text(s["months"]),
            "Total interest": money(s["interest"]),
            "Interest saved": money(max(0.0, standard_stats["interest"] - s["interest"])),
            "Payoff date": s["payoff_date"].strftime("%b %Y"),
        })
    st.dataframe(pd.DataFrame(scenarios), hide_index=True, use_container_width=True)

    st.markdown("#### Automatic loan insights")
    if extra_monthly > 0:
        st.success(
            f"Adding {money(extra_monthly)} every month could save about {money(saved_interest)} "
            f"in interest and pay the loan off {months_as_text(months_saved)} earlier."
        )
    else:
        st.info(
            f"Try an extra payment of {money(aggressive_extra, 2)} per month "
            "(10% of the scheduled payment) and compare the savings above."
        )
    if interest_rate >= 12:
        st.warning("This is a high nominal interest-rate assumption. Even modest extra principal payments can have a large effect; consider affordability and cash reserves too.")
    st.caption("Assumes a fixed rate, monthly compounding, no fees or prepayment penalties, and no missed payments.")

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
    st.caption("Five essential inputs. All income, savings, and results are in today's purchasing power.")

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            current_age = st.number_input("Current age", min_value=18, max_value=80, value=25, step=1)
        with c2:
            retirement_age = st.number_input("Retirement age", min_value=int(current_age) + 1, max_value=90, value=max(60, int(current_age) + 1), step=1)
        with c3:
            retirement_savings = st.number_input(
                f"Current savings ({CURRENCY})", min_value=0.0,
                max_value=10_000_000_000_000.0,
                value=30_000_000.0 if IS_MNT else 10_000.0,
                step=1_000_000.0 if IS_MNT else 1_000.0,
            )
        with c4:
            retirement_contribution = st.number_input(
                f"Monthly savings ({CURRENCY})", min_value=0.0,
                max_value=10_000_000_000.0,
                value=1_000_000.0 if IS_MNT else 300.0,
                step=100_000.0 if IS_MNT else 50.0,
            )
        with c5:
            target_income = st.number_input(
                f"Target monthly income ({CURRENCY})", min_value=1.0,
                max_value=10_000_000_000.0,
                value=3_000_000.0 if IS_MNT else 1_500.0,
                step=100_000.0 if IS_MNT else 100.0,
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
    earliest_age = earliest_target_age(
        int(current_age), retirement_savings, retirement_contribution,
        portfolio_target, real_rate, max_age=int(planning_age),
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
        j4.metric("Earliest age reaching target", str(earliest_age) if earliest_age is not None else f"Not by {planning_age}")
        st.caption(
            f"All amounts shown in today's {currency_choice.split(' ')[0]} purchasing power. "
            f"Portfolio target = target income × 12 ÷ {withdrawal_rate:.2f}% initial withdrawal rate. "
            "This is a rule of thumb, not a guarantee of lasting income."
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

    st.markdown("#### Automatically generated retirement-age comparison")
    comparisons = []
    for age in sorted({age for age in [retirement_age - 5, retirement_age, retirement_age + 5] if current_age < age <= planning_age}):
        balance = grow_savings(retirement_savings, retirement_contribution, 12 * (age - current_age), real_rate)
        need = required_monthly_contribution(retirement_savings, 12 * (age - current_age), portfolio_target, real_rate)
        comparisons.append({
            "Retirement age": age,
            "Projected real portfolio": money(balance),
            "Portfolio gap": money(balance - portfolio_target),
            "Needed monthly saving": money(need),
            "Starting monthly income · withdrawal rule": money(balance * withdrawal_rate / 100 / 12),
        })
    st.dataframe(pd.DataFrame(comparisons), hide_index=True, use_container_width=True)

    st.markdown("#### Automatically generated financial insights")
    if difference >= 0:
        st.success(
            f"At the assumed constant return, you're on track to reach the {withdrawal_rate:.2f}% "
            f"withdrawal-rule target, with a projected cushion of {money(difference)}."
        )
    else:
        st.warning(
            f"At the assumed constant return, your projected portfolio falls short by {money(-difference)}. "
            f"Raising monthly savings by about {money(max(0.0, needed_per_month - retirement_contribution))} "
            "in today's money could close that gap under the same assumptions."
        )
    if simulation["sustain_probability"] < 0.70:
        st.info("Simulated withdrawal sustainability is below 70%. Try a later retirement age, a lower spending target, or higher monthly contributions.")
    else:
        st.info("Review both the withdrawal-rule target and simulated withdrawal sustainability: meeting one metric doesn't ensure the other.")

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

st.divider()
st.caption("Financial Future Planner • Streamlit class project • Educational estimates only")
