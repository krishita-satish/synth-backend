"""
Professional PDF Report Generator for Synth AI Audit Reports.
Now uses structured audit data to generate data-driven reports with
actual findings, category breakdowns, and AI-generated recommendations.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os
from datetime import datetime


# ─── Color palette matching the Synth brand ──────────────────────────
SYNTH_GREEN = colors.HexColor('#10B981')
SYNTH_DARK_GREEN = colors.HexColor('#059669')
DARK_BG = colors.HexColor('#1F2937')
GRAY_TEXT = colors.HexColor('#6B7280')
LIGHT_BG = colors.HexColor('#F9FAFB')
WHITE = colors.white


def create_pdf(audit_data: dict, output_path: str = None):
    """
    Create a professional, data-driven PDF audit report.
    
    Args:
        audit_data: Dictionary containing:
            - total_messages: int
            - category_breakdown: dict
            - top_opportunities: list[dict]
            - recommendations: list[str]
            - time_saved_annually: str
            - cost_reduction_annually: str
            - automation_score: int
        output_path: Optional custom output path
    """
    # Determine output path
    if output_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_folder = os.path.join(base_dir, "output")
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, "audit_report.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=60,
        leftMargin=60,
        topMargin=50,
        bottomMargin=50,
    )

    # ─── Custom Styles ──────────────────────────────────────────────
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'SynthTitle',
        parent=styles['Heading1'],
        fontName='Times-Bold',
        fontSize=28,
        textColor=SYNTH_GREEN,
        spaceAfter=8,
        alignment=TA_CENTER,
    )

    subtitle_style = ParagraphStyle(
        'SynthSubtitle',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        textColor=GRAY_TEXT,
        spaceAfter=20,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        'SynthHeading',
        parent=styles['Heading2'],
        fontName='Times-Bold',
        fontSize=16,
        textColor=DARK_BG,
        spaceAfter=10,
        spaceBefore=24,
    )

    body_style = ParagraphStyle(
        'SynthBody',
        parent=styles['BodyText'],
        fontName='Times-Roman',
        fontSize=11,
        textColor=DARK_BG,
        spaceAfter=8,
        leading=16,
    )

    metric_label_style = ParagraphStyle(
        'MetricLabel',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=9,
        textColor=GRAY_TEXT,
        alignment=TA_CENTER,
    )

    metric_value_style = ParagraphStyle(
        'MetricValue',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=20,
        textColor=SYNTH_GREEN,
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    # ─── Build the PDF ──────────────────────────────────────────────
    story = []

    # === HEADER ===
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("SYNTH AI", title_style))
    story.append(Paragraph("AI Automation Opportunity Audit Report", subtitle_style))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        ParagraphStyle('DateLine', parent=body_style, fontSize=9, textColor=GRAY_TEXT, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 0.1 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=SYNTH_GREEN))
    story.append(Spacer(1, 0.2 * inch))

    # === EXECUTIVE SUMMARY ===
    story.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
    
    total = audit_data.get("total_messages", 0)
    score = audit_data.get("automation_score", 0)
    time_saved = audit_data.get("time_saved_annually", "N/A")
    cost_saved = audit_data.get("cost_reduction_annually", "N/A")
    
    story.append(Paragraph(
        f"This audit analyzed <b>{total}</b> business messages and communications. "
        f"Our AI engine identified an <b>automation score of {score}/100</b>, indicating "
        f"{'significant' if score > 60 else 'moderate' if score > 30 else 'some'} "
        f"potential for AI-powered automation in your operations. "
        f"Implementing our recommendations could save your organization approximately "
        f"<b>{time_saved}</b> of manual work and <b>{cost_saved}</b> annually.",
        body_style
    ))
    story.append(Spacer(1, 0.2 * inch))

    # === KEY METRICS (as a table) ===
    story.append(Paragraph("KEY METRICS", heading_style))
    
    metrics_data = [
        [
            Paragraph(f"{total}", metric_value_style),
            Paragraph(f"{score}/100", metric_value_style),
            Paragraph(f"{time_saved}", metric_value_style),
            Paragraph(f"{cost_saved}", metric_value_style),
        ],
        [
            Paragraph("Messages Analyzed", metric_label_style),
            Paragraph("Automation Score", metric_label_style),
            Paragraph("Annual Time Saved", metric_label_style),
            Paragraph("Annual Cost Savings", metric_label_style),
        ],
    ]
    
    metrics_table = Table(metrics_data, colWidths=[1.2 * inch] * 4)
    metrics_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.3 * inch))

    # === CATEGORY BREAKDOWN TABLE ===
    category_breakdown = audit_data.get("category_breakdown", {})
    if category_breakdown:
        story.append(Paragraph("CATEGORY BREAKDOWN", heading_style))
        story.append(Paragraph(
            "The following table shows how your business communications were classified by our AI engine:",
            body_style
        ))
        story.append(Spacer(1, 0.1 * inch))

        # Sort by count descending
        sorted_cats = sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)
        
        table_data = [
            [
                Paragraph("<b>Category</b>", body_style),
                Paragraph("<b>Count</b>", body_style),
                Paragraph("<b>Percentage</b>", body_style),
                Paragraph("<b>Automation Potential</b>", body_style),
            ]
        ]
        
        high_automation = {"Order Status", "Refund/Return", "Payment Issue", "Billing Inquiry",
                          "Technical Support", "Account Access", "Shipping/Delivery",
                          "Leave Request", "Access/Permissions", "Software Issue"}
        
        for cat, count in sorted_cats:
            pct = f"{int(count / total * 100)}%" if total > 0 else "0%"
            potential = "High" if cat in high_automation else "Medium"
            
            table_data.append([
                Paragraph(cat, body_style),
                Paragraph(str(count), body_style),
                Paragraph(pct, body_style),
                Paragraph(potential, body_style),
            ])
        
        cat_table = Table(table_data, colWidths=[2.2 * inch, 0.8 * inch, 1.0 * inch, 1.5 * inch])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), SYNTH_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), LIGHT_BG),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, WHITE]),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 0.3 * inch))

    # === TOP OPPORTUNITIES ===
    top_opportunities = audit_data.get("top_opportunities", [])
    if top_opportunities:
        story.append(Paragraph("TOP AUTOMATION OPPORTUNITIES", heading_style))
        story.append(Paragraph(
            "These are the highest-impact areas where AI automation can deliver immediate ROI:",
            body_style
        ))
        story.append(Spacer(1, 0.1 * inch))

        for i, opp in enumerate(top_opportunities, 1):
            area = opp.get("area", "Unknown")
            count = opp.get("count", 0)
            saving = opp.get("potential_saving", "0%")
            impact = opp.get("impact", "Medium")
            
            story.append(Paragraph(
                f"<b>{i}. {area}</b> — {count} messages ({saving} of total volume) | Impact: <b>{impact}</b>",
                body_style
            ))
        
        story.append(Spacer(1, 0.2 * inch))

    # === AI-GENERATED RECOMMENDATIONS ===
    recommendations = audit_data.get("recommendations", [])
    if recommendations:
        story.append(Paragraph("AI-POWERED RECOMMENDATIONS", heading_style))
        story.append(Paragraph(
            "Based on our analysis, here are specific, actionable strategies tailored to your data:",
            body_style
        ))
        story.append(Spacer(1, 0.1 * inch))

        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"<b>{i}.</b> {rec}", body_style))
            story.append(Spacer(1, 4))

        story.append(Spacer(1, 0.2 * inch))

    # === NEXT STEPS ===
    story.append(Paragraph("NEXT STEPS", heading_style))
    next_steps = [
        "Review this report with your operations and technology teams",
        "Prioritize the top 2-3 opportunities with highest ROI potential",
        "Schedule a consultation with Synth AI to discuss custom agent development",
        "Begin pilot implementation of the highest-impact automation solution",
        "Monitor KPIs (response time, resolution rate, cost per ticket) for 30 days",
    ]
    for i, step in enumerate(next_steps, 1):
        story.append(Paragraph(f"{i}. {step}", body_style))
        story.append(Spacer(1, 4))

    # === FOOTER ===
    story.append(Spacer(1, 0.4 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E5E7EB')))
    story.append(Spacer(1, 0.1 * inch))

    footer_style = ParagraphStyle(
        'Footer', parent=body_style, fontSize=8, textColor=GRAY_TEXT, alignment=TA_CENTER
    )
    story.append(Paragraph(
        "This report is confidential and prepared exclusively for the recipient organization.",
        footer_style
    ))
    story.append(Paragraph(
        "Powered by Synth AI — Discover What Your Company Can Automate With AI",
        footer_style
    ))
    story.append(Paragraph(
        "contact@synth-ai.com | synth-ai.com",
        footer_style
    ))

    # Build
    doc.build(story)
    print(f"✅ Professional PDF report saved at: {output_path}")
    return output_path