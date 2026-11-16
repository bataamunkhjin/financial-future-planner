"""Standalone PDF summary for the Investment Portfolio Analyzer."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import math

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


def _font():
    path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    if path.exists():
        if 'PortfolioDejaVu' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('PortfolioDejaVu', str(path)))
        return 'PortfolioDejaVu'
    return 'Helvetica'


def make_portfolio_pdf(positions, summary, history, currency: str = 'USD', rate: float = 1.0) -> bytes:
    font = _font()
    money_symbol = {'MNT':'₮','USD':'$','EUR':'€'}.get(currency, '$')
    if font == 'Helvetica' and money_symbol == '₮':
        money_symbol = 'MNT '
    def amt(v):
        return 'N/A' if v is None or not math.isfinite(float(v)) else f'{money_symbol}{float(v)*rate:,.0f}'
    buff = BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=A4, topMargin=42, bottomMargin=36, leftMargin=42, rightMargin=42)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='PortHead', fontName=font, fontSize=19, leading=25,
                              textColor=colors.HexColor('#12334c'), spaceAfter=8))
    styles.add(ParagraphStyle(name='PortSub', fontName=font, fontSize=11, leading=16,
                              textColor=colors.HexColor('#177d87'), spaceBefore=14, spaceAfter=8))
    styles.add(ParagraphStyle(name='PortText', fontName=font, fontSize=8.3, leading=13,
                              textColor=colors.HexColor('#304c60'), spaceAfter=6))
    styles.add(ParagraphStyle(name='PortTiny', fontName=font, fontSize=7.3, leading=11,
                              textColor=colors.HexColor('#304c60')))
    story = [Paragraph('INVESTMENT PORTFOLIO | FINANCIAL FUTURE PLANNER v5', styles['PortHead']),
             Paragraph('A multi-asset valuation and historical risk snapshot. Illustrative educational analysis only.', styles['PortText'])]
    metrics = history.get('metrics', {})
    values = [
        ('Total portfolio value', amt(summary['total_value'])),
        ('Unrealized P/L (known costs)', amt(summary['unrealized_profit'])),
        ('Largest holding weight', f"{summary['largest_weight']:.1%}"),
        ('Live-price valuation coverage', f"{summary['market_coverage']:.1%}"),
        ('Historical annualized return*', f"{metrics['annualized_return']:.1%}" if metrics else 'N/A'),
        ('Annualized historical volatility*', f"{metrics['volatility']:.1%}" if metrics else 'N/A'),
        ('Maximum drawdown*', f"{metrics['max_drawdown']:.1%}" if metrics else 'N/A'),
        ('Weekly historical 95% VaR*', f"{metrics['var95_week']:.1%}" if metrics else 'N/A'),
    ]
    story.append(Paragraph('Portfolio summary', styles['PortSub']))
    summary_table = Table([[Paragraph(k, styles['PortTiny']), Paragraph(v, styles['PortTiny'])] for k,v in values],
                          colWidths=[275, 215], hAlign='LEFT')
    summary_table.setStyle(TableStyle([
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.HexColor('#f2f7f9'),colors.white]),
        ('BOTTOMPADDING',(0,0),(-1,-1),8), ('TOPPADDING',(0,0),(-1,-1),8),
        ('LINEBELOW',(0,-1),(-1,-1),0.6,colors.HexColor('#d8e4ec')),
    ]))
    story.append(summary_table)
    story.append(Paragraph('Current holdings', styles['PortSub']))
    rows = [[Paragraph(s,styles['PortTiny']) for s in ('Investment','Asset class','Market value','Weight')]]
    for _,p in positions.sort_values('Value USD', ascending=False).iterrows():
        rows.append([Paragraph(str(p['Asset'])[:32],styles['PortTiny']),
                     Paragraph(str(p['Class'])[:24],styles['PortTiny']),
                     Paragraph(amt(p['Value USD']),styles['PortTiny']),
                     Paragraph(f"{p['Weight %']:.1f}%",styles['PortTiny'])])
    table = Table(rows,colWidths=[150,130,135,75],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecef')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f8fa')]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),
        ('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),
    ]))
    story.append(table)
    story.extend([Spacer(1,12),Paragraph('Interpretation and limitations',styles['PortSub']),
        Paragraph('*Historical return, volatility, drawdown and VaR reflect only listed holdings with overlapping data, assuming current quantities were held over the historical period. Manual assets have no invented return histories.', styles['PortText']),
        Paragraph('Market prices are third-party observations and may be delayed or missing. Average purchase price is optional; unrealized P/L excludes positions without cost information and does not include trading fees, realized gains or taxes.',styles['PortText']),
        Paragraph('Live tickers and manually entered USD-equivalent prices are combined into one valuation. Currency conversion (if selected) uses a market estimate; historical FX risk is not modeled. Not financial advice.',styles['PortText'])])
    doc.build(story)
    return buff.getvalue()
