"""
AWS Textract Service
Extracts text from images and PDFs using AWS Textract
"""

import boto3
import httpx
import os
import re
from typing import Optional


import asyncio
from concurrent.futures import ThreadPoolExecutor

# Initialize Textract client
textract_client = boto3.client(
    'textract',
    region_name=os.getenv('AWS_REGION', 'ap-south-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

async def run_in_thread(func, *args, **kwargs):
    """Helper to run sync functions in a thread"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

async def extract_text_from_image(image_buffer: bytes) -> dict:
    """
    Extract text from an image buffer
    
    Args:
        image_buffer: Image data as bytes
        
    Returns:
        Extracted text and confidence
    """
    try:
        response = await run_in_thread(
            textract_client.detect_document_text,
            Document={'Bytes': image_buffer}
        )
        
        # Extract all text blocks
        text_blocks = [
            block for block in response.get('Blocks', [])
            if block.get('BlockType') == 'LINE'
        ]
        
        extracted_lines = [
            {
                'text': block.get('Text', ''),
                'confidence': block.get('Confidence', 0)
            }
            for block in text_blocks
        ]
        
        # Combine all text
        full_text = '\n'.join(line['text'] for line in extracted_lines)
        avg_confidence = (
            sum(line['confidence'] for line in extracted_lines) / len(extracted_lines)
            if extracted_lines else 0
        )
        
        print(f'📄 Textract: Extracted {len(extracted_lines)} lines, avg confidence: {avg_confidence:.1f}%')
        
        return {
            'success': True,
            'text': full_text,
            'lines': extracted_lines,
            'confidence': avg_confidence,
            'blockCount': len(extracted_lines)
        }
    except Exception as e:
        print(f'❌ Textract error: {e}')
        return {
            'success': False,
            'error': str(e),
            'text': '',
            'lines': [],
            'confidence': 0
        }


async def extract_expense_from_image(image_buffer: bytes) -> dict:
    """
    Extract expense/receipt data from an image
    
    Args:
        image_buffer: Image data as bytes
        
    Returns:
        Extracted expense data
    """
    try:
        response = await run_in_thread(
            textract_client.analyze_expense,
            Document={'Bytes': image_buffer}
        )
        
        # Collect all extracted text
        all_text = []
        summary_data = {}
        
        # Parse expense documents
        expenses = []
        for doc in response.get('ExpenseDocuments', []):
            # Extract from SummaryFields (most important data)
            for field in doc.get('SummaryFields', []):
                field_type = field.get('Type', {}).get('Text', 'UNKNOWN')
                field_value = field.get('ValueDetection', {}).get('Text', '')
                field_label = field.get('LabelDetection', {}).get('Text', '')
                
                if field_value:
                    summary_data[field_type] = field_value
                    all_text.append(f"{field_label or field_type}: {field_value}")
            
            # Extract from LineItemGroups
            for group in doc.get('LineItemGroups', []):
                for item in group.get('LineItems', []):
                    for field in item.get('LineItemExpenseFields', []):
                        field_type = field.get('Type', {}).get('Text', 'UNKNOWN')
                        text = field.get('ValueDetection', {}).get('Text', '')
                        if text:
                            all_text.append(f"{field_type}: {text}")
            
            # Extract any Block text
            for block in doc.get('Blocks', []):
                if block.get('BlockType') == 'LINE' and block.get('Text'):
                    all_text.append(block['Text'])
            
            expenses.append({
                'vendorName': summary_data.get('VENDOR_NAME') or summary_data.get('NAME', ''),
                'total': summary_data.get('TOTAL') or summary_data.get('AMOUNT_DUE') or summary_data.get('AMOUNT_PAID', ''),
                'subtotal': summary_data.get('SUBTOTAL', ''),
                'tax': summary_data.get('TAX') or summary_data.get('TAX_PAYER_ID', ''),
                'date': summary_data.get('INVOICE_RECEIPT_DATE') or summary_data.get('DATE') or summary_data.get('ORDER_DATE', ''),
                'invoiceId': summary_data.get('INVOICE_RECEIPT_ID') or summary_data.get('RECEIVER_VAT_NUMBER', ''),
                'allFields': summary_data
            })
        
        # Remove duplicates and join
        unique_text = '\n'.join(list(dict.fromkeys(all_text)))
        
        print(f'🧾 Textract Expense: Found {len(expenses)} documents, {len(all_text)} text items')
        if expenses:
            print(f'🧾 Summary data: {expenses[0]}')
        
        return {
            'success': True,
            'expense': expenses[0] if expenses else {},
            'text': unique_text,
            'raw': response,
            'documentCount': len(expenses)
        }
    except Exception as e:
        print(f'❌ Textract expense error: {e}')
        # Fall back to basic text extraction
        return await extract_text_from_image(image_buffer)


async def extract_text_from_url(media_url: str, mime_type: str = 'image/jpeg') -> dict:
    """
    Download media from WAHA and extract text
    
    Args:
        media_url: URL to download media from
        mime_type: MIME type of the media
        
    Returns:
        Extraction result
    """
    try:
        print(f'📥 Downloading media from: {media_url}')
        print(f'📄 Media type: {mime_type}')
        
        # Download the media
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                media_url,
                headers={'X-Api-Key': os.getenv('WAHA_API_KEY', '')}
            )
            response.raise_for_status()
        
        document_buffer = response.content
        print(f'📥 Downloaded {len(document_buffer) / 1024:.1f} KB')
        
        # Check file size - Textract sync API limit is 5MB for bytes
        if len(document_buffer) > 5 * 1024 * 1024:
            print('⚠️ File too large for Textract sync API (max 5MB)')
            return {
                'success': False,
                'error': 'File too large (max 5MB)',
                'text': '[Document too large for processing]'
            }
        
        # Check if it's a supported format (image or PDF)
        is_image = 'image' in mime_type
        is_pdf = 'pdf' in mime_type
        
        if not is_image and not is_pdf:
            return {
                'success': False,
                'error': 'Unsupported media type',
                'text': ''
            }
        
        print(f'📄 Processing {"PDF" if is_pdf else "image"} with Textract...')
        
        # Try expense extraction first for better receipt parsing
        expense_result = await extract_expense_from_image(document_buffer)
        if expense_result.get('success') and expense_result.get('expenses'):
            expense = expense_result['expenses'][0]
            text_parts = []
            
            # Add structured expense data first
            if expense.get('vendorName'):
                text_parts.append(f"Vendor: {expense['vendorName']}")
            if expense.get('date'):
                text_parts.append(f"Date: {expense['date']}")
            if expense.get('total'):
                text_parts.append(f"Total: {expense['total']}")
            if expense.get('subtotal'):
                text_parts.append(f"Subtotal: {expense['subtotal']}")
            if expense.get('tax'):
                text_parts.append(f"Tax: {expense['tax']}")
            if expense.get('invoiceId'):
                text_parts.append(f"Invoice ID: {expense['invoiceId']}")
            
            # Add full extracted text
            if expense_result.get('fullText'):
                text_parts.append('---')
                text_parts.append(expense_result['fullText'])
            
            text = '\n'.join(text_parts) or '[Expense document found but no text extracted]'
            
            print(f'📄 Expense extracted: {text[:200]}...')
            
            return {
                'success': True,
                'text': text,
                'expense': expense,
                'confidence': 90,
                'isPdf': is_pdf
            }
        
        # Fall back to basic text extraction
        return await extract_text_from_image(document_buffer)
        
    except Exception as e:
        print(f'❌ Error downloading/processing media: {e}')
        return {
            'success': False,
            'error': str(e),
            'text': ''
        }


def extract_amount_from_text(text: str) -> Optional[float]:
    """
    Extract amount from text (handles various formats)
    
    Args:
        text: Text to search for amounts
        
    Returns:
        Extracted amount or None
    """
    if not text:
        return None
    
    # Patterns for amounts: Rs. 1,234.56, LKR 1234, රු. 1234, 1,234.00
    patterns = [
        r'(?:rs\.?|lkr\.?|රු\.?)\s*([\d,]+(?:\.\d{2})?)',
        r'(?:total|amount|subtotal|due)[\s:]*(?:rs\.?|lkr\.?)?\s*([\d,]+(?:\.\d{2})?)',
        r'\b([\d,]+\.\d{2})\b'
    ]
    
    max_amount = 0
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                if amount > max_amount:
                    max_amount = amount
            except ValueError:
                continue
    
    return max_amount if max_amount > 0 else None
