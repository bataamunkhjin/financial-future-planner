"""Portable, self-contained PDF summary for Financial Future Planner.

Uses ReportLab's built-in fonts so GitHub/Streamlit Cloud needs no font files.
MNT is shown as its ISO currency code to avoid missing-glyph problems in PDFs.
"""
from __future__ import annotations

from datetime import date
from html import escape
from io import BytesIO

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)
from reportlab.graphics.shapes import Drawing, Line, PolyLine, String

NAVY = colors.HexColor("#17233A")
MID = colors.HexColor("#53667E")
TEAL = colors.HexColor("#078F7A")
BLUE = colors.HexColor("#6477C8")
ORANGE = colors.HexColor("#D5912A")
LITE = colors.HexColor("#EDF3F6")
BORDER = colors.HexColor("#DBE3EB")


def _currency(value: float, code: str) -> str:
    return f"{code} {value:,.0f}"


def _styles():
    st = getSampleStyleSheet()
    st.add(ParagraphStyle(name="ReportTitle", parent=st["Title"], fontName="Helvetica-Bold", fontSize=20,
        textColor=NAVY, spaceAfter=5, leading=24, alignment=TA_LEFT))
    st.add(ParagraphStyle(name="ReportSub", fontSize=9, leading=13, textColor=MID, spaceAfter=12))
    st.add(ParagraphStyle(name="SectionHeading", fontName="Helvetica-Bold", fontSize=12,
        leading=15, textColor=NAVY, spaceBefore=12, spaceAfter=7))
    st.add(ParagraphStyle(name="ReportBody", fontSize=8.6, leading=13, textColor=NAVY, spaceAfter=6))
    st.add(ParagraphStyle(name="ReportSmall", fontSize=7.5, leading=10.5, textColor=MID, spaceAfter=5))
    st.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=7.5, leading=10,
        textColor=NAVY, alignment=TA_LEFT))
    st.add(ParagraphStyle(name="CellHeader", parent=st["Cell"], fontName="Helvetica-Bold",
        textColor=colors.white))
    return st


def _p(value, style):
    # ReportLab built-in Helvetica has no tugrik glyph or several Unicode symbols.
    # Keep the PDF portable by expanding them to plain-text alternatives.
    safe = str(value)
    for original, replacement in (("₮", "MNT "), ("€", "EUR "),
                                  ("—", "-"), ("–", "-"), ("≈", "~"),
                                  ("→", "->"), ("×", "x"), ("≥", ">=")):
        safe = safe.replace(original, replacement)
    return Paragraph(escape(safe), style)


def _table(headers: list[str], rows: list[list], widths: list[float], styles):
    contents = [[_p(x, styles["CellHeader"]) for x in headers]]
    contents.extend([[_p(x, styles["Cell"]) for x in row] for row in rows])
    t = Table(contents, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LITE]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _line_chart(series: list[tuple[str, np.ndarray, np.ndarray, colors.Color]], width=510, height=155):
    """Vector line chart that renders without Plotly image export or Kaleido."""
    d = Drawing(width, height)
    left, bottom, right, top = 52, 29, 16, 25
    chart_w, chart_h = width - left - right, height - bottom - top
    all_x = [float(x) for _, xs, _, _ in series for x in xs]
    all_y = [float(y) for _, _, ys, _ in series for y in ys]
    xmax = max(all_x) if all_x else 1.0
    xmin = min(all_x) if all_x else 0.0
    lo = min(0.0, min(all_y)) if all_y else 0.0
    hi = max(0.0, max(all_y)) if all_y else 1.0
    pad = max(1.0, (hi - lo) * .07)
    ymin, ymax = lo - (pad if lo < 0 else 0), hi + pad
    for i in range(5):
        y = bottom + i * chart_h / 4
        value = ymin + i * (ymax - ymin) / 4
        d.add(Line(left, y, left + chart_w, y, strokeColor=BORDER, strokeWidth=0.6))
        scaled = value / 1e9 if ymax >= 1e9 else value / 1e6 if ymax >= 1e6 else value / 1e3 if ymax >= 1e3 else value
        unit = "B" if ymax >= 1e9 else "M" if ymax >= 1e6 else "K" if ymax >= 1e3 else ""
        d.add(String(left-5, y-2.3, f"{scaled:,.0f}{unit}", fontSize=7, textAnchor="end", fillColor=MID))
    for i in range(5):
        x = left + i * chart_w / 4
        d.add(String(x, bottom-15, f"{xmin + i * (xmax-xmin)/4:.0f}", fontSize=7, textAnchor="middle", fillColor=MID))
    d.add(Line(left, bottom, left+chart_w, bottom, strokeColor=MID, strokeWidth=.6))
    for idx, (name, xs, ys, line_color) in enumerate(series):
        if len(xs) != len(ys) or len(xs) < 2:
            continue
        points = []
        for x, y in zip(xs, ys):
            points.extend([left + (float(x) - xmin) / max(1e-12, xmax-xmin) * chart_w,
                           bottom + (float(y) - ymin) / max(1e-12, ymax - ymin) * chart_h])
        d.add(PolyLine(points, strokeColor=line_color, strokeWidth=2.0, fillColor=None))
        legend_x = left + idx * 165
        d.add(Line(legend_x, height-7, legend_x+16, height-7, strokeColor=line_color, strokeWidth=2))
        d.add(String(legend_x+21, height-10, name, fontSize=7.1, fillColor=MID))
    return d


def _page(canvas, document):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(BORDER)
    canvas.line(42, h-34, w-42, h-34)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MID)
    canvas.drawString(42, h-27, "FINANCIAL FUTURE PLANNER")
    canvas.line(42, 33, w-42, 33)
    canvas.drawString(42, 22, "Educational estimates - not personalized financial advice")
    canvas.drawRightString(w-42, 22, f"Page {document.page}")
    canvas.restoreState()


def generate_pdf_report(
    *, code: str,
    loan: dict,
    retirement: dict,
    loan_rate_sensitivity: pd.DataFrame,
    loan_extra_sensitivity: pd.DataFrame,
    retirement_sensitivity: pd.DataFrame,
    investing: dict,
    base_loan_schedule: pd.DataFrame,
    chosen_loan_schedule: pd.DataFrame,
    retirement_projection_df: pd.DataFrame,
    loan_insights: list[str],
    retirement_insights: list[str],
    investment_insights: list[str],
    loan_milestones: pd.DataFrame | None = None,
    investment_sensitivity: pd.DataFrame | None = None,
    savings_goal: dict | None = None,
) -> bytes:
    """Generate a small multi-page financial report from already-calculated app data."""
    code = code if code in {"USD", "MNT", "EUR"} else "CUR"
    buf = BytesIO()
    styles = _styles()
    width = A4[0] - 84
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=42, rightMargin=42, topMargin=50, bottomMargin=45,
        title="Financial Future Planner Report", author="Financial Future Planner")
    frame = Frame(42, 45, width, A4[1]-95, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="report", frames=[frame], onPage=_page))
    story = []
    def heading(txt): story.append(_p(txt, styles["SectionHeading"]))
    def para(txt): story.append(_p(txt, styles["ReportBody"]))
    def small(txt): story.append(_p(txt, styles["ReportSmall"]))
    def table(headers, rows, widths): story.append(_table(headers, rows, widths, styles)); story.append(Spacer(1, 6))

    story.append(_p("Your financial planning report", styles["ReportTitle"]))
    story.append(_p(f"Prepared {date.today():%d %B %Y}  |  {code}  |  Two linked planning models", styles["ReportSub"]))
    para("This report summarizes the assumptions and automatic what-if analysis currently entered in the app. Figures are estimates, not offers or guarantees.")
    heading("01  |  Mortgage and loan analysis")
    table(["Loan input", "Value", "Loan output", "Value"], [
        ["Starting principal", _currency(loan["amount"], code), "Scheduled monthly P&I", _currency(loan["payment"], code)],
        ["Loan interest rate", f'{loan["rate"]:.2f}%', "Standard lifetime interest", _currency(loan["standard_interest"], code)],
        ["Loan term", f'{loan["years"]} years', "Interest saved with extra", _currency(loan["interest_saved"], code)],
        ["Extra payment / month", _currency(loan["extra"], code), "Earlier payoff", f'{loan["months_saved"]} months'],
        ["Loan start date", str(loan["start_date"]), "Payoff with extra", str(loan["payoff_date"])],
    ], [115, 128, 153, width-396])
    heading("Rate sensitivity - new loan with selected extra payment")
    table(["Rate scenario", "Annual rate", "Monthly P&I", "Total interest"], [
        [r["Scenario"], f'{r["Rate (%)"]:.2f}%', _currency(r["Monthly P&I"], code),
         _currency(r["Total Interest"], code)] for _, r in loan_rate_sensitivity.iterrows()
    ], [113, 100, 145, width-358])
    heading("Automatic extra-payment strategies")
    table(["Strategy", "Extra / month", "Interest saved", "Payoff months"], [
        [r["Scenario"], _currency(r["Extra / Month"], code), _currency(r["Interest Saved"], code),
         f'{int(r["Payoff Months"])}'] for _, r in loan_extra_sensitivity.iterrows()
    ], [157, 133, 130, width-420])
    small("An existing fixed-rate loan will not change when market rates move. Extra payments are assumed to reduce principal immediately with no prepayment penalty. Property tax, insurance and PMI are not modeled in interest or investment comparisons.")
    heading("Remaining mortgage principal")
    story.append(_line_chart([
        ("Standard", np.concatenate([[0], base_loan_schedule["Month"].to_numpy()]),
         np.concatenate([[loan["amount"]], base_loan_schedule["Ending Balance"].to_numpy()]), BLUE),
        ("With extra", np.concatenate([[0], chosen_loan_schedule["Month"].to_numpy()]),
         np.concatenate([[loan["amount"]], chosen_loan_schedule["Ending Balance"].to_numpy()]), TEAL),
    ], width=width, height=145))

    story.append(PageBreak())
    heading("02  |  Mortgage prepayment versus investing")
    para("Both strategies have the same fixed monthly cash budget. Investing uses the leftover cash while making standard loan payments. Prepaying puts the extra toward the mortgage and invests the freed payment after payoff.")
    table(["Assumption / result", "Value", "Assumption / result", "Value"], [
        ["Extra budget / month", _currency(investing["comparison_extra"], code), "Investment annual return", f'{retirement["return"]:.2f}%'],
        ["Fixed monthly budget", _currency(investing["monthly_budget"], code), "Comparison horizon", f'{investing["horizon_months"] // 12} years'],
        ["Invest extra - end value", _currency(investing["invest_portfolio"], code), "Prepay first - end value", _currency(investing["prepay_portfolio"], code)],
        ["Modeled winner", investing["winner"], "End value difference", _currency(abs(investing["difference"]), code)],
    ], [127, 122, 141, width-390])
    small("Both strategies are debt-free by the scheduled loan maturity. Results are future nominal portfolio balances, not inflation-adjusted figures. Fixed investment return, no investing taxes/fees, no property value, liquidity or prepayment fees. This is a sensitivity model, not a recommendation.")
    plot = investing["table"]
    heading("Net financial wealth (investment balance minus outstanding debt)")
    story.append(_line_chart([
        ("Invest extra", plot["Month"].to_numpy(), plot["Invest Strategy Net Wealth"].to_numpy(), BLUE),
        ("Prepay first", plot["Month"].to_numpy(), plot["Prepay Strategy Net Wealth"].to_numpy(), TEAL),
    ], width=width, height=145))
    if loan_milestones is not None:
        heading("Loan principal repayment milestones")
        table(["Repaid", "Month", "Payoff date", "Balance remaining"], [
            [row["Loan Repaid"], str(row["Payment Month"]), str(row["Payment Date"]),
             _currency(row["Balance Remaining"], code)] for _, row in loan_milestones.iterrows()
        ], [70, 65, 150, width - 285])
    if investment_sensitivity is not None:
        heading("Investing return stress test")
        table(["Scenario", "Return", "Invest - prepay", "Favored strategy"], [
            [row["Scenario"], f'{row["Investment Return (%)"]:.2f}%',
             _currency(row["Invest - Prepay"], code), row["Favored Strategy"]]
            for _, row in investment_sensitivity.iterrows()
        ], [173, 65, 133, width - 371])
        small("Investment return cases are hypothetical constants, not a probability distribution or recommended strategy.")
    heading("Loan and investing insights")
    for line in (loan_insights + investment_insights)[:2]:
        para("- " + line)

    story.append(PageBreak())
    heading("03  |  Retirement readiness")
    table(["Retirement input", "Value", "Result", "Value"], [
        ["Current age", retirement["current_age"], "Planned retirement age", retirement["retirement_age"]],
        ["Savings today", _currency(retirement["savings"], code), "Monthly saving", _currency(retirement["contribution"], code)],
        ["Target monthly spending", _currency(retirement["income"], code), "Plan through age", str(retirement["planning_age"])],
        ["Nominal return assumption", f'{retirement["return"]:.2f}%', "Inflation assumption", f'{retirement["inflation"]:.2f}%'],
        ["Est. retirement portfolio", _currency(retirement["planned_balance"], code), "Capital needed for spending", _currency(retirement["target"], code)],
        ["Needed monthly saving", _currency(retirement["needed"], code), "Surplus / shortfall", _currency(retirement["difference"], code)],
        ["Earliest modeled retirement", str(retirement["earliest_age"]), "Spending success (sim.)", f'{retirement["sustain_probability"]:.1%}'],
    ], [127, 119, 135, width-381])
    small("Required capital is the present value of all planned monthly withdrawals through the planning age at a constant real return. Returns keep compounding after retirement; contributions end at retirement. This is not guaranteed.")
    if savings_goal is not None:
        heading("Savings target for simulated spending success")
        table(["Measurement", "Value", "Measurement", "Value"], [
            ["Target success chance", f'{savings_goal["probability_target"]:.0%}',
             "Current spending success", f'{savings_goal["current_sustain_probability"]:.1%}'],
            ["Saving / month for goal", _currency(savings_goal["monthly_contribution_needed"], code),
             "Extra savings / month", _currency(savings_goal["monthly_increase_needed"], code)],
        ], [122, 122, 145, width - 389])
        small("The 80% goal measures simulated paths funding EVERY withdrawal through the chosen planning age, not just reaching an account balance at retirement. Market outcomes are uncertain.")
    heading("Automatic retirement what-if scenarios")
    table(["Scenario", "Retire age", "Portfolio (today's value)", "Surplus / shortfall"], [
        [r["Scenario"], int(r["Retirement Age"]), _currency(r["Portfolio"], code),
         _currency(r["Surplus / Shortfall"], code)] for _, r in retirement_sensitivity.iterrows()
    ], [151, 75, 151, width-377])
    heading("Constant-return savings and retirement drawdown")
    story.append(_line_chart([
        ("Real portfolio", retirement_projection_df["Age"].to_numpy(),
         retirement_projection_df["Balance (today's money)"].to_numpy(), TEAL),
    ], width=width, height=145))
    story.append(PageBreak())
    heading("04  |  Interpretation and model transparency")
    heading("Retirement insights")
    for line in retirement_insights[:4]:
        para("- " + line)
    small(f"Monte Carlo: {retirement['simulations']:,} illustrative independent-annual-return paths. Fully funding every withdrawal through age {retirement['planning_age']}: {retirement['sustain_probability']:.1%}.")
    small("Not modeled: local tax rules, employer/pension income, fees, shocks to inflation, changes in contribution or spending, variable mortgage rates, or correlations. Retirement assumptions use constant real purchasing power; mortgage investing comparison uses constant nominal cash flows.")
    heading("What these results mean")
    table(["Measure", "Interpretation"], [
        ["Total loan interest", "Cumulative interest charged under the assumed fixed-rate amortization schedule."],
        ["Principal milestones", "The first loan payment date when the stated share of ORIGINAL principal is repaid."],
        ["Mortgage vs investing", "Two strategies with equal monthly cash spending, compared at original loan maturity."],
        ["Retirement capital needed", "Present value of planned real monthly spending through the chosen age, using a constant real return."],
        ["80% simulated savings goal", "Monthly saving for at least ~80% of simulated paths to fund every modeled withdrawal."],
        ["Monte Carlo spending success", "Share of simulated paths able to fund all modeled monthly withdrawals until planning age."],
    ], [175, width - 175])
    heading("Calculation assumptions")
    table(["Topic", "Method and important omissions"], [
        ["Monthly loan payment", "Annual nominal loan rate divided by 12; extra repayments go to principal; no penalties."],
        ["Investment comparison", "Constant nominal monthly budget and hypothetical fixed investment returns; no taxes or market risk."],
        ["Real-value retirement model", "Annual nominal return and inflation converted to a monthly REAL return; spending and deposits constant in today's purchasing power."],
        ["Monte Carlo simulation", "Independent annual lognormal return samples spread equally across each year; fixed inflation; fixed random seed."],
        ["Drawdown capital method", "Discounted monthly withdrawals over the selected horizon at an assumed constant real return."],
    ], [149, width - 149])
    small("This is a simplified education-only analysis: do not substitute these outputs for a real lender quote, financial advisor, actuarial plan, or personalized investment recommendation.")

    doc.build(story)
    return buf.getvalue()
