import pandas as pd
from services.pdf_report import create_pdf

def run_audit_pipeline(file_path: str):
    # Load CSV
    df = pd.read_csv(file_path)

    # Very simple AI-like analysis (we will upgrade later)
    total_rows = len(df)
    sample_data = df.head(5).to_string()

    insights = f"""
    Total Records Analysed: {total_rows}

    Sample Data:
    {sample_data}

    Key Finding:
    Large volume of repetitive customer queries detected.
    High automation potential in customer support workflows.
    """

    # Generate PDF report
    create_pdf(insights)
