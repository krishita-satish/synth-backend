import pandas as pd
from PyPDF2 import PdfReader
from PIL import Image
import io

def parse_csv(file_path):
    """Parse CSV file and return list of text content"""
    try:
        df = pd.read_csv(file_path)
        # Convert all data to strings and flatten
        return df.astype(str).values.flatten().tolist()
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        return []

def parse_excel(file_path):
    """Parse Excel file and return list of text content"""
    try:
        df = pd.read_excel(file_path)
        return df.astype(str).values.flatten().tolist()
    except Exception as e:
        print(f"Error parsing Excel: {e}")
        return []

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