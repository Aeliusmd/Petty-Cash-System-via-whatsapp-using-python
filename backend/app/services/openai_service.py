"""
OpenAI Service for Intelligent Receipt Parsing

Uses OpenAI GPT to analyze Textract OCR output and extract:
- Total amount
- Vendor name
- Date
"""

import os
import json
from typing import Optional, Dict
import httpx


async def parse_receipt_text(ocr_text: str) -> Dict:
    """
    Use OpenAI to intelligently parse receipt OCR text
    
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
        # Prepare the prompt for GPT
        prompt = f"""Analyze this receipt OCR text and extract the following information:
- Total amount (the final amount to be paid, NOT subtotal or tax)
- Vendor/store name
- Date (in YYYY-MM-DD format if possible)
- Currency (usually LKR for Sri Lankan receipts)

Receipt text:
{ocr_text}

Return ONLY a JSON object with these exact keys: total_amount (as number), vendor_name (as string), date (as string), currency (as string).
If you cannot find a value, use null for that field.
"""

        # Call OpenAI API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-3.5-turbo',
                    'messages': [
                        {
                            'role': 'system',
                            'content': 'You are a receipt parsing assistant. Extract structured data from receipt OCR text. Always respond with valid JSON.'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': 0.1,  # Low temperature for consistent outputs
                    'max_tokens': 200
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
        
        # Validate and return
        return {
            'success': True,
            'total_amount': parsed_data.get('total_amount'),
            'vendor_name': parsed_data.get('vendor_name'),
            'date': parsed_data.get('date'),
            'currency': parsed_data.get('currency', 'LKR'),
            'raw_response': ai_response
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse OpenAI JSON response: {e}")
        print(f"   Raw response: {ai_response}")
        return {
            'success': False,
            'error': 'Failed to parse AI response as JSON'
        }
    except Exception as e:
        print(f"❌ OpenAI parsing error: {e}")
        return {
            'success': False,
            'error': str(e)
        }
