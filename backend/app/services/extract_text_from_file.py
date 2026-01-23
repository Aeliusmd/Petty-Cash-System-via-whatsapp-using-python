import mimetypes
from pathlib import Path
from .textract_service import extract_expense_from_image, extract_text_from_image, extract_amount_from_text

async def extract_text_from_file(file_path: str) -> dict:
    """
    Extract text, amount, and vendor from a local file (image or PDF)
    Returns: dict with keys: text, amount, vendor
    """
    try:
        # Guess mime type
        mime_type, _ = mimetypes.guess_type(file_path)
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        # Try expense extraction first
        result = await extract_expense_from_image(file_bytes)
        text = result.get('fullText') or result.get('text') or ''
        amount = None
        vendor = None
        if result.get('success') and result.get('expenses'):
            expense = result['expenses'][0]
            amount = expense.get('total')
            vendor = expense.get('vendorName')
        # Fallback: try to extract amount from text
        if not amount:
            amount = extract_amount_from_text(text)
        # Fallback: vendor as first line
        if not vendor and text:
            vendor = text.split('\n', 1)[0].strip()
        return {
            'success': True,
            'text': text,
            'amount': float(amount) if amount else None,
            'vendor': vendor
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'text': '', 'amount': None, 'vendor': None}
