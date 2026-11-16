"""Self-contained third Streamlit tab: multi-asset valuation and risk dashboard."""
from __future__ import annotations

import math
from html import escape
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from portfolio import (ASSET_TYPES, LISTED_TYPES, prepare_holdings, position_valuation,
                       market_return_history, portfolio_summary, portfolio_insights,
                       allocation_by_class)
from market_data import download_market_history, usd_exchange_rate
from portfolio_report import make_portfolio_pdf

COLORS = ["#0b8791", "#305e90", "#ea9b68", "#8975b6", "#50bfae", "#b7bec9", "#b4856d"]


@st.cache_data(ttl=3600, show_spinner=False, max_entries=40)
def cached_prices(tickers: tuple[str, ...], period: str):
    return download_market_history(tickers, period)


@st.cache_data(ttl=3600, show_spinner=False, max_entries=12)
def cached_fx(currency: str):
    return usd_exchange_rate(currency)


def chart(fig: go.Figure, *, height: int = 395, currency: str | None = None):
    fig.update_layout(
        height=height, template="plotly_white",
        margin=dict(l=25, r=20, t=35, b=35),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", color="#294457", size=12),
        legend=dict(orientation="h", x=0, y=1.17),
        hovermode="x unified",
        colorway=COLORS,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#e1e9ef")
    fig.update_yaxes(showgrid=True, gridcolor="#edf2f6", separatethousands=True)
    st.plotly_chart(fig, use_container_width=True)


def section(title: str, note: str | None = None):
    st.markdown(f"#### {title}")
    if note:
        st.caption(note)


def _fmt(value, symbol="$", decimals=0):
    if value is None or not np.isfinite(value):
        return "N/A"
    return f"{symbol}{value:,.{decimals}f}"


def _starter_holdings():
    return pd.DataFrame([
        {"Asset type": "Stock", "Ticker / name": "AAPL", "Units": 5.0,
         "Avg buy / unit": 175.0, "Current price (manual)": None},
        {"Asset type": "Bond ETF", "Ticker / name": "BND", "Units": 10.0,
         "Avg buy / unit": 72.0, "Current price (manual)": None},
        {"Asset type": "Crypto", "Ticker / name": "BTC-USD", "Units": 0.02,
         "Avg buy / unit": 55000.0, "Current price (manual)": None},
        {"Asset type": "Direct bond", "Ticker / name": "Government bond (sample)", "Units": 1.0,
         "Avg buy / unit": 1000.0, "Current price (manual)": 1030.0},
    ])


def render_investment_tab(currency_choice: str):
    """Render the Portfolio tab without affecting loan/retirement tabs."""
    st.subheader("Investment Portfolio Analyzer")
    st.caption("Stocks, bond funds, cryptocurrencies, commodity funds, property and manually valued assets — one portfolio.")

    with st.container(border=True):
        st.markdown("**1 · Enter your holdings**")
        st.caption("Edit the sample holdings or add rows. Market-listed investments need a ticker and units only; "
                   "manual assets also need their current unit price. All entered prices are **USD or USD-equivalent**. "
                   "Average buy price is optional and is used only for unrealized profit/loss.")
        with st.form("portfolio_form", border=False):
            input_df = st.data_editor(
                st.session_state.get("portfolio_input", _starter_holdings()),
                num_rows="dynamic", hide_index=True, use_container_width=True,
                column_config={
                    "Asset type": st.column_config.SelectboxColumn("Asset class", options=list(ASSET_TYPES), required=True,
                        help="Bond ETFs and commodity ETFs have live tickers. Direct bonds and property are manually valued."),
                    "Ticker / name": st.column_config.TextColumn("Ticker / name", required=True,
                        help="Examples: AAPL, BND, BTC-USD, GLD or 'Apartment'."),
                    "Units": st.column_config.NumberColumn("Units", min_value=0.00000001, format="%.6f", required=True),
                    "Avg buy / unit": st.column_config.NumberColumn("Avg buy / unit ($)", min_value=0.0, format="%.2f",
                        help="Optional; for unrealized P/L only."),
                    "Current price (manual)": st.column_config.NumberColumn("Manual price / unit ($)", min_value=0.0,
                        format="%.2f", help="Required for direct bonds, property, cash, private and other manual assets."),
                },
                key="portfolio_editor",
            )
            x, y, z = st.columns([1,1,1], vertical_alignment="bottom")
            with x:
                period = st.selectbox("History period", ["1y", "3y", "5y"], index=1,
                                      help="Historical market analysis for tickers with available data.")
            with y:
                benchmark_name = st.selectbox("Reference benchmark", ["S&P 500 (SPY)", "None"], index=0,
                    help="Reference comparison only; the S&P 500 is not necessarily suitable for a mixed-asset portfolio.")
            with z:
                analyze = st.form_submit_button("📊 Analyze portfolio", use_container_width=True, type="primary")
        st.caption("Examples: **Stocks** AAPL, MSFT · **Bond ETFs** BND, TLT · **Crypto** BTC-USD, ETH-USD · "
                   "**Commodity ETFs** GLD, SLV · **Property ETFs** VNQ. Direct bonds, apartments and cash use manual valuations.")

    if analyze:
        try:
            clean = prepare_holdings(input_df)
            listed = tuple(sorted(set(clean.loc[clean["is_listed"], "ticker"].tolist())))
            symbols = tuple(sorted(set(listed + (("SPY",) if benchmark_name.startswith("S&P") else ()))) )
            with st.spinner("Retrieving available market prices and calculating your portfolio..."):
                histories, failed = cached_prices(symbols, period) if symbols else ({}, [])
                positions, unavailable = position_valuation(clean, histories)
                if positions.empty:
                    st.error("No holdings could be priced. Check live tickers or add a manually valued asset.")
                else:
                    hist = market_return_history(clean, histories,
                        histories.get("SPY") if benchmark_name.startswith("S&P") else None)
                    summary = portfolio_summary(positions, hist)
                    st.session_state["portfolio_result"] = {
                        "positions": positions, "history": hist, "summary": summary,
                        "errors": sorted(set(unavailable)), "inputs": clean,
                        "period": period, "benchmark": benchmark_name,
                    }
                    st.session_state["portfolio_input"] = input_df
        except Exception as exc:
            st.error(f"Portfolio analysis could not complete: {exc}. Your other two planners are unaffected.")

    result = st.session_state.get("portfolio_result")
    if result is None:
        st.info("Adjust the sample investments and click **Analyze portfolio**. The other two planners work independently.")
        return
    positions = result["positions"]
    hist = result["history"]
    summary = result["summary"]
    if result["errors"]:
        st.warning("Market prices unavailable for: **" + ", ".join(result["errors"]) + "**. "
                   "These holdings were excluded from valuation rather than assigned a zero price. "
                   "You can enter an asset manually if its live ticker is unavailable.")

    display_code = currency_choice.split(" ")[0]
    symbols = {"USD": "$", "EUR": "€", "MNT": "₮"}
    fx = cached_fx(display_code) if display_code != "USD" else 1.0
    if fx is None:
        fx = 1.0
        display_code = "USD"
        st.warning("A reliable live exchange rate is unavailable. The portfolio is displayed in USD to avoid an incorrect currency conversion.")
    symbol = symbols[display_code]
    st.caption(f"Portfolio amounts shown in **{display_code}**. Market quotes and manual inputs are USD/USD-equivalents; "
               "converted totals use an estimated market FX rate. This does not change any loan or retirement amount.")

    def fm(value, decimals=0):
        return _fmt(float(value)*fx, symbol, decimals) if value is not None and pd.notna(value) else "N/A"

    section("Portfolio snapshot", "Current market or user-entered values; quotes may be delayed.")
    a,b,c,d = st.columns(4)
    a.metric("Total portfolio value", fm(summary["total_value"]))
    b.metric("Unrealized P/L · known cost", fm(summary["unrealized_profit"]))
    c.metric("Largest holding", f"{summary['largest_weight']:.1%}")
    d.metric("Assets with market quotes", f"{summary['market_coverage']:.1%} of value")
    a,b,c,d = st.columns(4)
    metrics = hist["metrics"]
    a.metric("Historical annualized return*", f"{metrics['annualized_return']:.1%}" if metrics else "N/A")
    b.metric("Annualized volatility*", f"{metrics['volatility']:.1%}" if metrics else "N/A")
    c.metric("Maximum drawdown*", f"{metrics['max_drawdown']:.1%}" if metrics else "N/A")
    d.metric("Sharpe ratio*", f"{summary['sharpe']:.2f}" if math.isfinite(summary["sharpe"]) else "N/A")
    st.caption(f"*Historical return and risk cover **{summary['risk_coverage']:.1%} of the current portfolio value**: "
               "only listed holdings with overlapping price histories, at fixed quantities. "
               "Manual assets and personal trading/cash-flow history are excluded.")

    section("Portfolio allocation", "Where your current investment value is concentrated.")
    allocation = allocation_by_class(positions)
    fig = go.Figure(go.Bar(
        x=allocation["Value USD"]*fx, y=allocation["Class"], orientation="h",
        marker_color=[COLORS[i%len(COLORS)] for i in range(len(allocation))],
        text=[fm(v) for v in allocation["Value USD"]], textposition="outside",
        hovertemplate="%{y}<br>Value: %{x:,.0f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title=f"Value ({display_code})")
    chart(fig, height=max(290, 58*len(allocation)+100))
    # Allocation by individual investment: independent data from asset-class graph
    top = positions.sort_values("Value USD", ascending=False)
    fig_w = go.Figure(go.Bar(
        x=top["Weight %"], y=top["Asset"], orientation="h",
        marker_color="#1a96a0", text=[f"{v:.1f}%" for v in top["Weight %"]], textposition="outside"))
    fig_w.update_yaxes(autorange="reversed")
    fig_w.update_xaxes(title="Share of total portfolio (%)", range=[0, max(100, top["Weight %"].max()*1.15)])
    with st.expander("View concentration by holding"):
        chart(fig_w, height=max(270, 45*len(top)+110))

    section("Portfolio positions", "Average purchase price is optional; blank costs do not count as zero investment.")
    table = positions.copy()
    for field in ["Unit price USD", "Value USD", "Cost basis USD", "Unrealized P/L USD"]:
        table[field] = table[field].map(lambda x: fm(x, 2) if pd.notna(x) else "—")
    table["Weight %"] = table["Weight %"].map(lambda x:f"{x:.1f}%")
    table = table.rename(columns={
        "Unit price USD": f"Unit price ({display_code})",
        "Value USD": f"Market value ({display_code})",
        "Unrealized P/L USD": f"Unrealized P/L ({display_code})",
    })
    st.dataframe(table[["Asset", "Class", "Units", f"Unit price ({display_code})", f"Market value ({display_code})",
                        f"Unrealized P/L ({display_code})", "Weight %", "Pricing", "Quote date"]],
                 use_container_width=True, hide_index=True)
    with st.expander("View profit and loss by investment"):
        known_cost = positions.dropna(subset=["Unrealized P/L USD"]).sort_values("Unrealized P/L USD")
        if known_cost.empty:
            st.caption("Enter an average purchase price to view unrealized gain/loss by holding.")
        else:
            pnl_fig = go.Figure(go.Bar(
                x=known_cost["Unrealized P/L USD"]*fx, y=known_cost["Asset"], orientation="h",
                marker_color=["#cd756e" if v < 0 else "#148e91" for v in known_cost["Unrealized P/L USD"]],
                text=[fm(v) for v in known_cost["Unrealized P/L USD"]], textposition="outside"))
            pnl_fig.update_xaxes(title=f"Unrealized gain or loss ({display_code})", zeroline=True)
            chart(pnl_fig, height=max(280, 47*len(known_cost)+120))
            st.caption("This is unrealized price change relative to entered average cost, not total return or realized earnings.")
    st.download_button("⬇ Download portfolio positions CSV", data=positions.to_csv(index=False).encode("utf-8-sig"),
                       file_name="investment_portfolio_positions.csv", mime="text/csv")

    if hist["metrics"]:
        section("Market performance", "Historical buy-and-hold proxy for listed holdings only, normalized to 100. It is not your actual transaction-based return.")
        portfolio_value_history = hist["weekly_portfolio"]
        benchmark = hist["benchmark_index"]
        # Compare both series over the same dates and against the same start.
        if benchmark is not None:
            common = portfolio_value_history.index.intersection(benchmark.index)
            portfolio_value_history = portfolio_value_history.loc[common]
            benchmark = benchmark.loc[common]
        portfolio_idx = 100 * portfolio_value_history / float(portfolio_value_history.iloc[0])
        pfig = go.Figure()
        pfig.add_trace(go.Scatter(x=portfolio_idx.index, y=portfolio_idx, mode="lines",
                                  name="Listed holdings", line=dict(color="#0a9597", width=3)))
        if benchmark is not None:
            pfig.add_trace(go.Scatter(x=benchmark.index, y=benchmark, mode="lines",
                                      name="S&P 500 ETF reference", line=dict(color="#6f85a4", width=2, dash="dash")))
        pfig.update_yaxes(title="Indexed growth (starting at 100)")
        chart(pfig, height=420)

        section("Risk & downside", "Downside measures are historical weekly statistics for assets with complete price data.")
        left, right, third = st.columns(3)
        left.metric("95% historical weekly VaR", f"{metrics['var95_week']:.1%}",
                    help="5% of observed historical weeks fell below approximately minus this return. It is not a worst-case limit.")
        right.metric("95% weekly CVaR", f"{metrics['cvar95_week']:.1%}",
                     help="Mean loss in the worst 5% of observed weekly returns.")
        third.metric("Worst historical week", f"{metrics['worst_week']:.1%}")
        line = hist["weekly_portfolio"]
        dd = 100*(line/line.cummax()-1)
        dfig = go.Figure(go.Scatter(x=dd.index, y=dd, mode="lines", name="Portfolio drawdown",
                                     line=dict(color="#d77b73", width=3), fill="tozeroy",
                                     fillcolor="rgba(215,123,115,.16)"))
        dfig.update_yaxes(title="Drawdown (%)")
        chart(dfig, height=340)
        st.caption("Weekly sampling aligns assets trading on different days (e.g., crypto and bond ETFs). "
                   "The risk statistics ignore manual assets and foreign-exchange fluctuations.")

        section("Portfolio diversification", "Pairwise correlation of the historical weekly returns for listed assets.")
        corr = hist["correlations"]
        if not corr.empty and len(corr.columns) > 1:
            heat = go.Figure(go.Heatmap(x=corr.columns, y=corr.index, z=corr.to_numpy(), zmin=-1, zmax=1,
                                        colorscale="RdBu", reversescale=True,
                                        hovertemplate="%{y} / %{x}: %{z:.2f}<extra></extra>"))
            heat.update_layout(height=max(315, len(corr)*53+140), margin=dict(l=35,r=25,t=25,b=35))
            chart(heat, height=max(315, len(corr)*53+140))
        else:
            st.info("Add two or more listed investments with overlapping price histories to view correlations.")
    else:
        st.info("No historical risk chart is available for these holdings. The app still calculates valuations, allocation and available profit/loss.")

    section("Automatic investment insights")
    for note in portfolio_insights(positions, summary, hist):
        st.markdown('<div class="insight-strip">'+escape(note)+'</div>', unsafe_allow_html=True)

    with st.expander("Financial formulas and interpretation · for your teacher"):
        st.markdown(r"""
**Portfolio value:** $V=\sum_i (\text{Units}_i \times \text{Current Price}_i)$.

**Unrealized profit/loss:** Current market value minus purchase cost for positions with a known average purchase price. Does not include trading fees, taxes, or realized sales.

**Annualized volatility:** Standard deviation of **weekly** returns multiplied by $\sqrt{52}$.

**Sharpe ratio:** $(52\times\text{average weekly return}-\text{assumed risk-free rate})/\text{annualized volatility}$. In this educational app the risk-free rate is assumed to be 3% annually.

**Maximum drawdown:** Largest historical percentage decline from a prior peak.

**Historical 95% weekly VaR:** Magnitude of the 5th percentile of observed weekly returns; it is not a worst-case loss.

**Price history limitation:** Adjusted close is used as a proxy for total returns. Current values use actual last closing prices. Historical portfolio performance assumes the current listed units were held over the entire selected period, rather than reconstructing individual trades.
""")

    st.download_button("📄 Download portfolio PDF summary",
                       data=make_portfolio_pdf(positions, summary, hist, display_code, fx),
                       file_name="portfolio_analysis.pdf", mime="application/pdf")
    st.caption("**Data:** Yahoo Finance through yfinance; may be delayed, incomplete, or unavailable. "
               "Use USD-quoted tickers for live lookup. A bond ETF is not equivalent to owning an individual bond; "
               "crypto and other volatile assets carry substantial risk. Not investment advice.")
