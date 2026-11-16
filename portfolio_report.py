"""Self-contained assumption-based investment portfolio PDF; no network data."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import math
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


def _font():
    p = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    if p.exists():
        if 'ManualPortfolioFont' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('ManualPortfolioFont', str(p)))
        return 'ManualPortfolioFont'
    return 'Helvetica'


def make_portfolio_pdf(positions, summary, forecast, currency='USD', inflation=2.5):
    font = _font()
    symbol = {'USD':'$', 'MNT':'₮', 'EUR':'€'}.get(currency,'$')
    if font == 'Helvetica' and symbol == '₮':
        symbol = 'MNT '
    def money(v):
        return 'N/A' if v is None or not math.isfinite(float(v)) else f'{symbol}{float(v):,.0f}'
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, topMargin=43, bottomMargin=40,
                                 leftMargin=42, rightMargin=42)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ManualHead', fontName=font, fontSize=19, leading=26,
                              textColor=colors.HexColor('#12354d'), spaceAfter=9))
    styles.add(ParagraphStyle(name='ManualSub', fontName=font, fontSize=11, leading=16,
                              textColor=colors.HexColor('#087f86'), spaceBefore=14, spaceAfter=9))
    styles.add(ParagraphStyle(name='ManualBody', fontName=font, fontSize=8.5, leading=14,
                              textColor=colors.HexColor('#315162'), spaceAfter=8))
    styles.add(ParagraphStyle(name='ManualSmall', fontName=font, fontSize=8, leading=12,
                              textColor=colors.HexColor('#315162')))
    p = lambda s: Paragraph(escape(str(s)), styles['ManualSmall'])
    story = [Paragraph('FINANCIAL FUTURE PLANNER | INVESTMENTS', styles['ManualHead']),
             Paragraph('Offline portfolio projection. All prices, expected returns and volatility assumptions were supplied by the user; no market data was downloaded.', styles['ManualBody'])]
    rows = [
        ('Portfolio value today', money(summary['total_value'])),
        ('Expected annual return (assumed)', f"{summary['expected_return']:.1f}%"),
        ('Modeled portfolio volatility', f"{summary['modeled_volatility']:.1f}%"),
        ('Unrealized P/L (known costs only)', money(summary['unrealized_profit'])),
        ('Base ending value', money(forecast['base_ending'])),
        ('Base investment growth', money(forecast['base_growth'])),
        ('Simulated 10th-percentile end', money(forecast['p10'])),
        ('Simulated 90th-percentile end', money(forecast['p90'])),
        ('Probability below total contributions (modeled)', f"{forecast['below_contributions']:.1%}"),
    ]
    story.append(Paragraph('Portfolio and projection summary', styles['ManualSub']))
    tab=Table([[p(k),p(v)] for k,v in rows],colWidths=[300,190], hAlign='LEFT')
    tab.setStyle(TableStyle([('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.HexColor('#f2f8f9'),colors.white]),
                             ('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7)]))
    story.append(tab)
    story.append(Paragraph('Current holdings', styles['ManualSub']))
    hold=[[p(x) for x in ('Investment','Class','Value','Weight')]]
    for _,row in positions.sort_values('Value', ascending=False).iterrows():
        hold.append([p(str(row['Asset'])[:30]),p(str(row['Class'])[:24]),
                     p(money(row['Value'])),p(f"{row['Weight %']:.1f}%")])
    t=Table(hold,colWidths=[135,155,125,75],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcebee')),
                           ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f8fa')]),
                           ('VALIGN',(0,0),(-1,-1),'TOP'),
                           ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.append(t)
    story.append(Paragraph('Method & limitations',styles['ManualSub']))
    story.append(Paragraph('The constant-return base case compounds monthly and adds the specified contribution at the end of each month. Simulation bands use illustrative lognormal returns from the user-supplied expected annual return and modeled portfolio volatility. The latter uses a common cross-asset correlation assumption, not observed covariance.',styles['ManualBody']))
    story.append(Paragraph(f'Inflation is assumed constant at {inflation:.1f}% per year. No fees, taxes, cash dividends, transactions, exchange-rate movements or market-price updates are modeled. Simulated scenarios are not predictive probabilities and are not investment advice.',styles['ManualBody']))
    document.build(story)
    return buffer.getvalue()
