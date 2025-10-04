import pytesseract
from PIL import Image
import streamlit as st
import re
from datetime import datetime
import tempfile
import os
from typing import Optional, Dict

def extract_text_from_image(image) -> Optional[str]:
    """Extract text from uploaded image using OCR"""
    try:
        # Convert streamlit uploaded file to PIL Image
        if hasattr(image, 'read'):
            image_data = image.read()
            image = Image.open(image)
        
        # Perform OCR
        text = pytesseract.image_to_string(image)
        return text.strip()
        
    except Exception as e:
        st.error(f"OCR processing failed: {e}")
        return None

def parse_receipt_data(text: str) -> Dict[str, any]:
    """Parse OCR text to extract expense data"""
    receipt_data: Dict[str, any] = {
        'amount': None,
        'date': None,
        'merchant': None,
        'description': None
    }
    
    if not text:
        return receipt_data
    
    lines = text.split('\n')
    
    # Extract amount (look for patterns like $12.34, 12.34, etc.)
    amount_patterns = [
        r'\$\s*(\d+\.?\d*)',  # $12.34
        r'(\d+\.\d{2})',      # 12.34
        r'TOTAL:?\s*\$?\s*(\d+\.?\d*)',  # TOTAL: $12.34
        r'AMOUNT:?\s*\$?\s*(\d+\.?\d*)',  # AMOUNT: $12.34
    ]
    
    for line in lines:
        for pattern in amount_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match and not receipt_data['amount']:
                try:
                    receipt_data['amount'] = float(match.group(1))
                    break
                except ValueError:
                    continue
    
    # Extract date (various date formats)
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # MM/DD/YYYY or MM-DD-YYYY
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',    # YYYY/MM/DD or YYYY-MM-DD
        r'(\w+\s+\d{1,2},?\s+\d{4})',        # Month DD, YYYY
    ]
    
    for line in lines:
        for pattern in date_patterns:
            match = re.search(pattern, line)
            if match and not receipt_data['date']:
                date_str = match.group(1)
                try:
                    # Try different date parsing formats
                    for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d', '%Y-%m-%d', '%B %d, %Y', '%b %d, %Y']:
                        try:
                            receipt_data['date'] = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    if receipt_data['date']:
                        break
                except:
                    continue
    
    # Extract merchant name (usually first few lines, excluding common receipt words)
    excluded_words = ['receipt', 'tax', 'total', 'amount', 'date', 'time', 'card', 'cash', 'change']
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if line and len(line) > 3 and not any(word in line.lower() for word in excluded_words):
            if not receipt_data['merchant'] and not re.match(r'^\d+[/\-]\d+[/\-]\d+', line):
                receipt_data['merchant'] = line
                break
    
    # Generate description from merchant and any relevant details
    if receipt_data['merchant']:
        receipt_data['description'] = f"Expense at {receipt_data['merchant']}"
    else:
        receipt_data['description'] = "Receipt-based expense"
    
    return receipt_data

def save_uploaded_file(uploaded_file) -> Optional[str]:
    """Save uploaded file and return path"""
    try:
        # Create receipts directory if it doesn't exist
        receipts_dir = "receipts"
        if not os.path.exists(receipts_dir):
            os.makedirs(receipts_dir)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uploaded_file.name}"
        filepath = os.path.join(receipts_dir, filename)
        
        # Save file
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return filepath
        
    except Exception as e:
        st.error(f"Failed to save receipt: {e}")
        return None

def process_receipt_upload(uploaded_file) -> Optional[Dict[str, any]]:
    """Process uploaded receipt file and return extracted data"""
    if not uploaded_file:
        return None
    
    # Save the uploaded file
    filepath = save_uploaded_file(uploaded_file)
    
    if not filepath:
        return None
    
    try:
        # Extract text using OCR
        text = extract_text_from_image(uploaded_file)
        
        if not text:
            st.error("No text could be extracted from the receipt")
            return None
        
        # Parse the extracted text
        receipt_data = parse_receipt_data(text)
        receipt_data['receipt_path'] = filepath
        receipt_data['extracted_text'] = text
        
        return receipt_data
        
    except Exception as e:
        st.error(f"Receipt processing failed: {e}")
        return None
