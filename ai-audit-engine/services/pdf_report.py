from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from datetime import datetime

def create_pdf(text, output_path=None):
    """
    Create a professional, insightful PDF audit report
    Uses Times New Roman font for professional appearance
    """
    # Get absolute project path
    if output_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_folder = os.path.join(base_dir, "output")
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, "audit_report.pdf")
    
    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )
    
    # Custom styles with Times New Roman
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName='Times-Bold',
        fontSize=28,
        textColor=colors.HexColor('#10B981'),  # Synth green
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    
    # Heading style
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName='Times-Bold',
        fontSize=18,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=12,
        spaceBefore=20,
    )
    
    # Subheading style
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontName='Times-Bold',
        fontSize=14,
        textColor=colors.HexColor('#374151'),
        spaceAfter=10,
        spaceBefore=15,
    )
    
    # Body text style
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontName='Times-Roman',
        fontSize=11,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=10,
        leading=16,
    )
    
    # Build the PDF content
    story = []
    
    # Header with logo placeholder
    story.append(Spacer(1, 0.2*inch))
    
    # Title
    story.append(Paragraph("SYNTH AI AUDIT REPORT", title_style))
    story.append(Paragraph("Business Automation Analysis & Recommendations", body_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Date
    date_text = f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    story.append(Paragraph(date_text, body_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Divider line
    story.append(Spacer(1, 12))
    
    # Executive Summary
    story.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
    story.append(Paragraph(
        "This comprehensive audit analyzes your business operations to identify automation opportunities "
        "using artificial intelligence. Our analysis reveals significant potential for time and cost savings "
        "through strategic AI implementation.",
        body_style
    ))
    story.append(Spacer(1, 20))
    
    # Main content from the text parameter
    story.append(Paragraph("DETAILED FINDINGS", heading_style))
    
    # Split text into paragraphs and add them
    paragraphs = text.split('\n\n')
    for para in paragraphs:
        if para.strip():
            # Check if it's a heading (contains ":")
            if ':' in para and len(para) < 100:
                story.append(Paragraph(para.strip(), subheading_style))
            else:
                story.append(Paragraph(para.replace('\n', '<br/>'), body_style))
            story.append(Spacer(1, 10))
    
    story.append(Spacer(1, 20))
    
    # Key Recommendations Section
    story.append(Paragraph("KEY RECOMMENDATIONS", heading_style))
    story.append(Paragraph(
        "Based on our analysis, we recommend the following strategic initiatives to maximize "
        "the return on your AI automation investment:",
        body_style
    ))
    story.append(Spacer(1, 12))
    
    recommendations = [
        "Implement AI-powered email classification and routing system",
        "Deploy chatbots for common customer inquiries",
        "Automate data entry processes using OCR and machine learning",
        "Set up predictive analytics for demand forecasting",
        "Establish automated reporting and dashboard systems"
    ]
    
    for i, rec in enumerate(recommendations, 1):
        story.append(Paragraph(f"{i}. {rec}", body_style))
        story.append(Spacer(1, 6))
    
    story.append(Spacer(1, 20))
    
    # Next Steps
    story.append(Paragraph("NEXT STEPS", heading_style))
    story.append(Paragraph(
        "To proceed with implementing these AI automation solutions:",
        body_style
    ))
    story.append(Spacer(1, 10))
    
    next_steps = [
        "Review this report with your technical team",
        "Schedule a consultation with Synth AI experts",
        "Prioritize automation opportunities based on ROI",
        "Begin pilot implementation of highest-impact solutions",
        "Monitor and measure results continuously"
    ]
    
    for i, step in enumerate(next_steps, 1):
        story.append(Paragraph(f"{i}. {step}", body_style))
        story.append(Spacer(1, 6))
    
    story.append(Spacer(1, 30))
    
    # Footer
    story.append(Paragraph("_" * 80, body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "This report is confidential and prepared exclusively for the recipient organization. "
        "For questions or assistance, contact: contact@synth-ai.com",
        ParagraphStyle('Footer', parent=body_style, fontSize=9, textColor=colors.grey)
    ))
    
    # Build PDF
    doc.build(story)
    
    print(f"✅ Professional PDF report saved at: {output_path}")
    return output_path