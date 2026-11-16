"""Offline Investment tab: all inputs and results are in the chosen currency."""
from __future__ import annotations

import math
from html import escape
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from portfolio import ASSET_TYPES, analyze_holdings, allocation_by_class, project_portfolio
from portfolio_report import make_portfolio_pdf

COLORS = ["#118c92", "#5779ac", "#ed9a70", "#876cba", "#42ac9a", "#9eafbe", "#9c765e", "#9dc95e"]


def _money(value: float, symbol: str, decimals: int = 0) -> str:
    return f"{symbol}{value:,.{decimals}f}" if math.isfinite(float(value)) else "N/A"


def _chart(fig: go.Figure, *, height: int = 410):
    fig.update_layout(
        template="plotly_white", height=height,
        margin=dict(l=32, r=25, t=45, b=35),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", color="#335064", size=12),
        legend=dict(orientation="h", x=0, y=1.15),
        colorway=COLORS, hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor="#e1e9ef")
    fig.update_yaxes(gridcolor="#edf2f6", separatethousands=True)
    st.plotly_chart(fig, use_container_width=True)


def _examples(currency: str):
    # Example numbers are deliberately hypothetical and should be replaced.
    scale = 4000 if currency == "MNT" else 1.0
    return pd.DataFrame([
        {"Asset class": "Stock / ETF", "Investment": "Example stock", "Units": 10.0,
         "Current price / unit": 200*scale, "Avg buy / unit": 180*scale,
         "Expected return %": 7.0, "Volatility %": 20.0},
        {"Asset class": "Bond / Bond ETF", "Investment": "Example bond", "Units": 5.0,
         "Current price / unit": 1000*scale, "Avg buy / unit": 980*scale,
         "Expected return %": 5.0, "Volatility %": 6.0},
        {"Asset class": "Crypto", "Investment": "Example coin", "Units": 0.1,
         "Current price / unit": 60000*scale, "Avg buy / unit": 55000*scale,
         "Expected return %": 10.0, "Volatility %": 65.0},
    ])


def render_investment_tab(currency_choice: str):
    """Render an offline multi-asset portfolio. No network dependency."""
    code = currency_choice.split(" ")[0]
    symbol = {"MNT": "₮", "USD": "$", "EUR": "€"}.get(code, "$" )
    st.markdown("""<div class="asset-hero"><div class="asset-eyebrow">OFFLINE INVESTMENT PLANNING</div>
      <h2>Your investments. Your assumptions. Your forecast.</h2>
      <p>Stocks, bonds, crypto, property and other assets — without fetching any market data.</p></div>""", unsafe_allow_html=True)
    st.caption(f"All values are entered and reported in **{code}**. Changing the currency changes the unit, "
               "not the exchange rate. Prices, returns and risk estimates are provided by you.")

    st.markdown("#### 1 · Portfolio inputs")
    with st.container(border=True):
        st.caption("Edit the **example values**, add holdings or delete rows. Enter a current unit price and assumed "
                   "annual return for each holding. Purchase price is optional, but needed for profit/loss. "
                   "Volatility is your hypothetical annual risk assumption—not historical data.")
        with st.form("offline_portfolio_form", border=False):
            data = st.data_editor(
                st.session_state.get(f"manual_holdings_{code}", _examples(code)),
                num_rows="dynamic", hide_index=True, use_container_width=True,
                column_config={
                    "Asset class": st.column_config.SelectboxColumn("Asset type", options=list(ASSET_TYPES), required=True),
                    "Investment": st.column_config.TextColumn("Name", required=True),
                    "Units": st.column_config.NumberColumn("Quantity", min_value=0.000001, format="%.6f", required=True),
                    "Current price / unit": st.column_config.NumberColumn(f"Current price ({symbol})", min_value=0.0, format="%.2f", required=True),
                    "Avg buy / unit": st.column_config.NumberColumn(f"Buy price ({symbol}) · optional", min_value=0.0, format="%.2f"),
                    "Expected return %": st.column_config.NumberColumn("Expected return (%)", min_value=-90.0, max_value=100.0, format="%.1f", required=True),
                    "Volatility %": st.column_config.NumberColumn("Volatility (%)", min_value=0.0, max_value=150.0, format="%.1f", required=True),
                },
                key=f"manual_portfolio_editor_{code}",
            )
            left, right = st.columns(2)
            with left:
                horizon = st.slider("Projection period (years)", min_value=1, max_value=30, value=10, step=1)
            with right:
                monthly_extra = st.number_input(f"Monthly additional investment ({symbol}) · optional",
                                                min_value=0.0, max_value=1e12, value=0.0, step=100.0,
                                                help="Invested after each month; projected using the portfolio's assumed overall return.")
            with st.expander("Advanced projection assumptions (optional)"):
                correlation = st.slider("Assumed correlation between holdings", min_value=0.0, max_value=1.0, value=0.35, step=0.05,
                                        help="One simplified correlation used for all pairs; not measured from markets.")
                inflation = st.number_input("Annual inflation assumption (%)", min_value=0.0, max_value=40.0, value=2.5, step=0.5)
                simulations = st.selectbox("Simulation scenarios", ["500", "1000", "2000"], index=1)
            run = st.form_submit_button("Analyze my portfolio", type="primary", use_container_width=True)

    if run:
        try:
            positions, summary = analyze_holdings(data, correlation=float(correlation))
            forecast = project_portfolio(summary["total_value"], summary["expected_return"],
                                         summary["modeled_volatility"], years=int(horizon),
                                         monthly_contribution=float(monthly_extra), scenarios=int(simulations), seed=42)
            st.session_state["portfolio_result"] = {
                "positions": positions, "summary": summary, "projection": forecast,
                "currency_code": code, "inflation": float(inflation),
                "monthly_contribution": float(monthly_extra), "inputs": data.copy(),
            }
            st.session_state[f"manual_holdings_{code}"] = data.copy()
        except ValueError as exc:
            st.error(f"Please check your portfolio inputs: {exc}")

    result = st.session_state.get("portfolio_result")
    if result is None or result.get("currency_code") != code:
        st.info("Enter your portfolio and click **Analyze my portfolio**. The examples are hypothetical—not market quotes.")
        return
    positions, summary, forecast = result["positions"], result["summary"], result["projection"]
    inflation = result["inflation"]
    years = forecast["years"]
    def fm(v, decimals=0): return _money(v, symbol, decimals)

    st.markdown("#### 2 · Portfolio snapshot")
    a,b,c,d = st.columns(4)
    a.metric("Current portfolio value", fm(summary["total_value"]))
    b.metric("Unrealized profit/loss*", fm(summary["unrealized_profit"]))
    c.metric("Assumed annual return", f"{summary['expected_return']:.1f}%")
    d.metric("Modeled annual volatility", f"{summary['modeled_volatility']:.1f}%")
    st.caption("*Profit/loss excludes holdings without entered purchase prices. Return and volatility are "
               "**user assumptions**, not observed market performance. Risk uses one assumed cross-asset correlation.")

    st.markdown("#### 3 · Portfolio allocation")
    cls = allocation_by_class(positions)
    fig = go.Figure(go.Bar(
        x=cls["Value"], y=cls["Class"], orientation="h",
        marker_color=[COLORS[i%len(COLORS)] for i in range(len(cls))],
        text=[fm(v) for v in cls["Value"]], textposition="outside",
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title=f"Current value ({code})", range=[0, float(cls["Value"].max())*1.22])
    _chart(fig, height=max(290, 65*len(cls)+115))
    with st.expander("View allocation by individual holding"):
        ranked = positions.sort_values("Weight %", ascending=False)
        fig2 = go.Figure(go.Bar(x=ranked["Weight %"], y=ranked["Asset"], orientation="h",
                                marker_color="#11969a", text=[f"{v:.1f}%" for v in ranked["Weight %"]],
                                textposition="outside"))
        fig2.update_yaxes(autorange="reversed")
        fig2.update_xaxes(title="Portfolio weight (%)", range=[0, 110])
        _chart(fig2, height=max(290, 50*len(ranked)+110))

    st.markdown("#### 4 · Future investment projection")
    one,two,three,four = st.columns(4)
    one.metric(f"Base value in {years} years", fm(forecast["base_ending"]))
    two.metric("Projected growth · base", fm(forecast["base_growth"]))
    three.metric("Simulated 10th percentile", fm(forecast["p10"]))
    four.metric("Simulated 90th percentile", fm(forecast["p90"]))
    st.caption("Base = constant assumed return; shaded range = 10th–90th percentile of illustrative simulations. "
               "Monthly additional investments are included. No future market movements are known.")
    annual = forecast["annual"]
    line = go.Figure()
    line.add_trace(go.Scatter(x=annual["Year"], y=annual["P90"], mode="lines", line=dict(width=0),
                              hoverinfo="skip", showlegend=False))
    line.add_trace(go.Scatter(x=annual["Year"], y=annual["P10"], mode="lines", line=dict(width=0),
                              fill="tonexty", fillcolor="rgba(14,148,151,.17)", name="10th–90th percentile"))
    line.add_trace(go.Scatter(x=annual["Year"], y=annual["Median"], name="Simulation median",
                              mode="lines", line=dict(color="#4f7ba4", width=2, dash="dash")))
    line.add_trace(go.Scatter(x=annual["Year"], y=annual["Base case"], name="Constant-return base",
                              mode="lines", line=dict(color="#0d9692", width=3)))
    line.update_xaxes(title="Years from now")
    line.update_yaxes(title=f"Portfolio value ({code})")
    _chart(line, height=450)

    st.markdown("#### 5 · Investment risk & purchasing power")
    a,b,c = st.columns(3)
    a.metric("Simulated chance of ending below paid-in capital", f"{forecast['below_contributions']:.1%}")
    b.metric("Simulated chance of >20% interim drawdown", f"{forecast['chance_negative_drawdown']:.1%}")
    c.metric("Largest holding", f"{summary['largest_weight']:.1%}")
    factor = (1 + inflation/100)**annual["Year"]
    fig_real = go.Figure()
    fig_real.add_trace(go.Scatter(x=annual["Year"], y=annual["Base case"],
                                  name="Future nominal balance", mode="lines", line=dict(color="#0e9398", width=3)))
    fig_real.add_trace(go.Scatter(x=annual["Year"], y=annual["Base case"]/factor,
                                  name="In today's purchasing power", mode="lines", line=dict(color="#a77662", width=2, dash="dash")))
    fig_real.update_xaxes(title="Years from now")
    fig_real.update_yaxes(title=f"Value ({code})")
    _chart(fig_real, height=360)
    st.caption(f"Inflation shown at a constant **{inflation:.1f}%** yearly. The risk figures are outputs of a "
               "simplified return model with fixed assumptions and do not measure actual historical risk.")

    st.markdown("#### 6 · Holdings & downloads")
    table = positions.copy()
    for field in ("Unit price", "Value", "Cost basis", "Unrealized P/L"):
        table[field] = table[field].map(lambda x: fm(x, 2) if pd.notna(x) else "—")
    table["Weight %"] = table["Weight %"].map(lambda v:f"{v:.1f}%")
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.download_button("Download holdings CSV", data=positions.to_csv(index=False).encode("utf-8-sig"),
                       file_name="portfolio_holdings.csv", mime="text/csv")
    st.download_button("Download projection CSV", data=annual.to_csv(index=False).encode("utf-8-sig"),
                       file_name="portfolio_projection.csv", mime="text/csv")
    st.download_button("Download investment PDF", data=make_portfolio_pdf(positions, summary, forecast, code, inflation),
                       file_name="investment_projection.pdf", mime="application/pdf")
    st.markdown("""<div class="linked-ribbon"><b>Connect this with retirement</b>
      <span>Return to Retirement → Bank savings vs investing. You can choose this portfolio's starting value, "
      "assumed expected return, and modeled volatility for an optional comparison. "
      "No personal retirement inputs are overwritten.</span></div>""", unsafe_allow_html=True)
    st.caption("Educational projections only. No price feeds, exchange-rate downloads, investment advice, "
               "dividends, coupons, fees, taxes or automatic contributions by asset are modeled.")
