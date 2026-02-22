"""
Audit Runner — Orchestrates the audit pipeline.
Now accepts any file type (not just CSV) and passes structured data to the PDF generator.
"""
from services.pdf_report import create_pdf


def run_audit_pipeline(messages: list, audit_data: dict):
    """
    Generate a professional PDF audit report from structured audit data.
    
    Args:
        messages: List of raw message strings that were analyzed
        audit_data: Dictionary containing:
            - total_messages: int
            - category_breakdown: dict
            - top_opportunities: list
            - recommendations: list
            - time_saved_annually: str
            - cost_reduction_annually: str
            - automation_score: int
    """
    create_pdf(audit_data)
    print(f"✅ Audit pipeline complete — {audit_data['total_messages']} messages processed")
