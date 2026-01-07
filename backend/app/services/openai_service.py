"""
OpenAI Service for Intelligent Receipt Parsing

Uses OpenAI GPT to analyze Textract OCR output and extract:
- Total amount (Net Total, NOT cash paid)
- Vendor name
- Date
- Line items (optional)

Based on Gemini-style detailed prompting for accurate extraction.
"""

import os
import json
import re
from typing import Optional, Dict
import httpx


def normalize_currency(value):
    """Normalize currency strings to float values by removing symbols and formatting."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    # Remove currency symbols and text
    currency_symbols = ['$', '€', '£', '¥', '₹', 'Rs.', 'Rs', 'LKR', 'රු.', 'රු']
    cleaned = value
    for symbol in currency_symbols:
        cleaned = cleaned.replace(symbol, '')

    # Remove commas (thousand separators)
    cleaned = cleaned.replace(',', '').strip()

    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_currency_symbol(value):
    """Extract the first recognized currency symbol from a string."""
    if not isinstance(value, str):
        return None
    symbols = ['$', '€', '£', '¥', '₹', 'Rs.', 'Rs', 'LKR']
    for symbol in symbols:
        if symbol in value:
            return symbol
    return None


async def parse_receipt_text(ocr_text: str) -> Dict:
    """
    Use OpenAI to intelligently parse receipt OCR text
    
    This uses a detailed Gemini-style prompt that is very specific about:
    - What values to extract
    - What values to IGNORE (like CASH paid, Balance/Change)
    - How to identify the correct total
    
    Args:
        ocr_text: Raw text from Textract OCR
        
    Returns:
        {
            'total_amount': float,
            'vendor_name': str,
            'date': str,
            'currency': str,
            'success': bool,
            'raw_response': str
        }
    """
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key or api_key == 'your-openai-api-key-here':
        print("⚠️ OpenAI API key not configured, skipping AI parsing")
        return {
            'success': False,
            'error': 'OpenAI API key not configured'
        }
    
    try:
        # Detailed prompt inspired by the user's Gemini approach
        prompt = f"""You are an expert receipt/invoice processing system. Analyze this OCR text and extract data.

REQUIRED FIELDS TO EXTRACT:

1. **VENDOR NAME** (the business/store name)
   - Usually at the top of the receipt
   - Examples: "CARGILLS FOOD CITY", "Keells Super", "Dialog", etc.

2. **DATE** (transaction date)
   - Look for date formats like DD/MM/YYYY, DD.MM.YYYY, YYYY-MM-DD
   - Return in DD/MM/YYYY format

3. **TOTAL AMOUNT** - THIS IS CRITICAL, FOLLOW THESE RULES EXACTLY:
   
   For RETAIL RECEIPTS (grocery stores, supermarkets):
   - Extract "Net Total", "Total", or "Sub Total" - this is the PURCHASE AMOUNT
   - ABSOLUTELY IGNORE these values:
     * "CASH" or "Cash Tendered" - this is what customer PAID (often more than total)
     * "Balance" or "Change" - this is money RETURNED to customer
     * "Rounding Off" - this is just an adjustment
   - The correct total is usually SMALLER than the CASH value
   
   For INVOICES:
   - Look for "Invoice Total", "Grand Total", "Total Due", "Amount Due"
   - IGNORE "Subtotal", "Discount", "Tax" lines - use the FINAL total only
   
   Priority order for total:
   1. "Net Total" (most accurate for retail)
   2. "Total" / "Grand Total" / "Invoice Total"
   3. "Sub Total" (if no Net Total found)
   4. "Amount Due" / "Balance Due"

   IMPORTANT: If you see both "Net Total: 398.50" and "CASH: 1000.00", 
   the correct total_amount is 398.50 (NOT 1000.00!)

4. **CURRENCY**
   - Usually LKR for Sri Lankan receipts
   - Look for Rs., LKR, or රු symbols

OCR TEXT TO ANALYZE:
---
{ocr_text}
---

RESPOND WITH ONLY THIS JSON FORMAT (no markdown, no explanation):
{{
  "vendor_name": "extracted vendor name or null",
  "date": "DD/MM/YYYY format or null",
  "total_amount": numeric_value_only_no_currency_symbol,
  "currency": "LKR or detected currency symbol",
  "extraction_confidence": "high/medium/low",
  "notes": "brief note if anything unusual"
}}

REMEMBER: total_amount must be a NUMBER (e.g., 398.50), not a string with currency!
"""

        # Call OpenAI API with gpt-4o-mini for better accuracy
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o-mini',  # Using gpt-4o-mini for better accuracy
                    'messages': [
                        {
                            'role': 'system',
                            'content': '''You are an expert receipt and invoice parser. 
Your job is to extract the ACTUAL PURCHASE AMOUNT from receipts.
CRITICAL: For retail receipts, the "Net Total" is what the customer OWES.
The "CASH" line shows what they PAID (could be more than owed).
The "Balance" shows their CHANGE (money returned).
NEVER confuse payment with purchase total!
Always respond with valid JSON only.'''
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': 0,  # Zero temperature for maximum consistency
                    'max_tokens': 300,
                    'response_format': {'type': 'json_object'}  # Force JSON response
                }
            )
        
        if response.status_code != 200:
            print(f"❌ OpenAI API error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f'OpenAI API returned {response.status_code}'
            }
        
        # Parse response
        result = response.json()
        ai_response = result['choices'][0]['message']['content'].strip()
        
        print(f"🤖 OpenAI response: {ai_response}")
        
        # Try to parse JSON from response
        # Sometimes GPT wraps JSON in markdown code blocks
        if '```json' in ai_response:
            ai_response = ai_response.split('```json')[1].split('```')[0].strip()
        elif '```' in ai_response:
            ai_response = ai_response.split('```')[1].split('```')[0].strip()
        
        parsed_data = json.loads(ai_response)
        
        # Normalize the total amount (ensure it's a float)
        total_amount = parsed_data.get('total_amount')
        if isinstance(total_amount, str):
            total_amount = normalize_currency(total_amount)
        
        # Validate and return
        return {
            'success': True,
            'total_amount': total_amount,
            'vendor_name': parsed_data.get('vendor_name'),
            'date': parsed_data.get('date'),
            'currency': parsed_data.get('currency', 'LKR'),
            'confidence': parsed_data.get('extraction_confidence', 'medium'),
            'raw_response': ai_response
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse OpenAI JSON response: {e}")
        print(f"   Raw response: {ai_response if 'ai_response' in locals() else 'N/A'}")
        return {
            'success': False,
            'error': 'Failed to parse AI response as JSON'
        }
    except Exception as e:
        print(f"❌ OpenAI parsing error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


# Fallback regex-based extraction
def extract_amount_fallback(text: str) -> Optional[float]:
    """
    Fallback regex extraction if OpenAI fails.
    Prioritizes Net Total > Total > Sub Total
    """
    # Priority patterns
    patterns = [
        (r'Net\s*Total[:\s]*(?:Rs\.?|LKR)?\s*([\d,]+(?:\.\d{2})?)', 'Net Total'),
        (r'Total\s*(?:Amount)?[:\s]*(?:Rs\.?|LKR)?\s*([\d,]+(?:\.\d{2})?)', 'Total'),
        (r'Grand\s*Total[:\s]*(?:Rs\.?|LKR)?\s*([\d,]+(?:\.\d{2})?)', 'Grand Total'),
        (r'Sub\s*Total[:\s]*(?:Rs\.?|LKR)?\s*([\d,]+(?:\.\d{2})?)', 'Sub Total'),
    ]
    
    for pattern, name in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                print(f"📊 Fallback found {name}: {amount}")
                return amount
            except ValueError:
                continue
    
    return None
