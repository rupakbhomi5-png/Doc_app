import os
import anthropic
import base64
import json

def extract_bill_data(pdf_path: str) -> dict:
    """Extract structure data from invoice, receipt, statement, bill PDF using Claude."""

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
                        "text": """Extract ALL financial data from this document(invoice, receipt, bill or statement). Return ONLY valid JSON, no markdown or explanation.
                        {
                        "vendor_name": "Company or entity name, null if missing",
                        "invoice_date": "YYYY-MM-DD format, null if missing",
                        "invoice_number": "Invoice/reference/transaction ID, null if missing",
                        "amount": "Total amount as number (e.g. 150.50), null if missing",
                        "currency": "USD, GBP, EUR, etc",
                        "line_items": [{"description": "Item or service description", "quantity": "number or null", "unit_price": "number or null",
                        "amount": "total amount for this line"}],
                        "tax_amount": "Tax amount as number, null if none",
                        "notes": "Any additional details (payment terms, notes, etc), null if none",
                        "bill_type": "invoice, receipt, bill, statement, or other"
                        }

                        CRITCAL RULES:
                        - Extract vendor/company name EXACTLY as written. Do not guess.
                        - For amount fields: extract the FINAL total, not subtotals. Never return 0 if there's a total present.
                        - For line items: only include if document has itemized details.
                        - Dates: always YYYY-MM-DD format.
                        - Return null only if field is genuinely missing, not if amount is $0."""
                        
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
            if response_text.endswith('```'):
                response_text = response_text[:-3]

        extracted = json.loads(response_text.strip())

        if not isinstance(extracted, dict):
            return {"error": "Invalid response format"}

        result = {
            "vendor": extracted.get("vendor"),
            "date": extracted.get("date"),
            "invoice_number": extracted.get("invoice_number"),
            "amount": extracted.get("amount"),
            "currency": extracted.get("currency", "USD"),
            "line_items": extracted.get("line_items", []),
            "tax": extracted.get("tax"),
            "notes": extracted.get("notes"),
            "bill_type": extracted.get("bill_type", "invoice")
        }

        
        return result
    except json.JSONDecodeError as e:
        return {"error": f"Failed to praise extraction: {str(e)}",
"raw_response": response_text[:200]}
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}

def extract_invoice_data(pdf_path: str) -> dict:
    return extract_bill_data(pdf_path)


    