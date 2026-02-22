import pandas as pd
from PyPDF2 import PdfReader
from PIL import Image
import io

def parse_csv(file_path):
    """Parse CSV file and return list of text content"""
    try:
        df = pd.read_csv(file_path)
        return _extract_relevant_text(df)
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        return []

def parse_excel(file_path):
    """Parse Excel file and return list of text content"""
    try:
        df = pd.read_excel(file_path)
        return _extract_relevant_text(df)
    except Exception as e:
        print(f"Error parsing Excel: {e}")
        return []

def _extract_relevant_text(df):
    """Internal helper to identify text columns and extract content"""
    # Identify text-heavy columns
    text_cols = []
    text_keywords = ['message', 'subject', 'description', 'content', 'body', 'text', 'comment', 'review', 'summary', 'details']
    
    # First, look for specific keywords in column names
    for col in df.columns:
        if any(key in str(col).lower() for key in text_keywords):
            text_cols.append(col)
    
    # If no keywords found, look for columns with long strings
    if not text_cols:
        for col in df.columns:
            # Check if majority of values are strings and have some length
            sample = df[col].dropna().head(10)
            if not sample.empty and sample.apply(lambda x: isinstance(x, str) and len(x) > 10).mean() > 0.5:
                text_cols.append(col)
                
    # If still no candidates, fallback to all columns but exclude very short ones (IDs, numbers)
    if not text_cols:
        text_cols = [col for col in df.columns if not ('id' in str(col).lower() or 'num' in str(col).lower())]

    if not text_cols:
        return df.astype(str).values.flatten().tolist()

    # Combine text from relevant columns
    messages = []
    for _, row in df[text_cols].iterrows():
        # Combine non-null values into a single string for that row
        msg_parts = [str(val).strip() for val in row if pd.notnull(val) and len(str(val).strip()) > 3]
        if msg_parts:
            messages.append(" | ".join(msg_parts))
            
    return messages

def parse_pdf(file_path):
    """Parse PDF file and return list of text content"""
    try:
        text_lines = []
        reader = PdfReader(file_path)
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_lines.extend(text.split('\n'))
        
        return [line.strip() for line in text_lines if line.strip()]
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return []

def parse_image(file_path):
    """
    Parse image file - basic implementation
    Note: OCR requires pytesseract which needs system Tesseract installation
    For now, just return image metadata
    """
    try:
        img = Image.open(file_path)
        # Return basic image info since we can't do OCR without tesseract
        return [
            f"Image file: {file_path}",
            f"Format: {img.format}",
            f"Size: {img.size[0]}x{img.size[1]} pixels",
            f"Mode: {img.mode}",
            "Note: OCR text extraction requires Tesseract installation"
        ]
    except Exception as e:
        print(f"Error parsing image: {e}")
        return []

def parse_txt(file_path):
    """Parse text file and return list of lines"""
    try:
        with open(file_path, "r", encoding="utf-8", errors='ignore') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        print(f"Error parsing text file: {e}")
        return []

def parse_file(file_path):
    """
    Main parser function - detects file type and routes to appropriate parser
    """
    file_lower = file_path.lower()
    
    try:
        if file_lower.endswith(".csv"):
            return parse_csv(file_path)
        elif file_lower.endswith((".xlsx", ".xls")):
            return parse_excel(file_path)
        elif file_lower.endswith(".pdf"):
            return parse_pdf(file_path)
        elif file_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
            return parse_image(file_path)
        elif file_lower.endswith(".txt"):
            return parse_txt(file_path)
        else:
            print(f"Unsupported file type: {file_path}")
            return [f"Unsupported file type: {file_path}"]
    except Exception as e:
        print(f"Error parsing file {file_path}: {e}")
        return []