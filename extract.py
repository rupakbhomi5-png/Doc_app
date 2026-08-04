import os
import anthropic
import base64
import json

def extract_invoice_data(pdf_path: str) -> dict:
    """Extract structure data from invoice/receipt PDF using Claude."""

    with open(pdf_path, 'rb') as f:
        pdf_data = base64.standard_b64encode(f.read()).decode('utf-8')

    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Extract invoice data and return ONLY valid JSON with no markdown:
                        {
                        "vendor_name": "string or null",
                        "invoice_date": "YYYY-MM-DD or null",
                        "invoice_number": "string or null",
                        "total_amount": "number or null",
                        "currency": "USD",
                        "line_items": [{"description": "string", "quantity": 0, "unit_price": 0,
                        "total": 0}]},
                        "tax_amount": "number or null",
                        "notes": "string or null"
                        }
                        
                        Be accurate. Use null if missing."""
                    }
                ]
            }
        ]
    )

    try:
        response_text = message.content[0].text.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]

        extracted = json.loads(response_text)
        return extracted
    except json.JSONDecodeError as e:
        return {"error": str(e), "raw": response_text}

    