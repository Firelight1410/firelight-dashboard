#!/usr/bin/env python3
"""
Bank Statement Reconciliation Bot
Receives bank statement PDFs via Telegram
Automatically matches payments to invoices using AI and fuzzy matching
"""

import os
import logging
import base64
import json
import traceback
from datetime import datetime
from difflib import SequenceMatcher

import gspread
from google.oauth2.service_account import Credentials
import anthropic
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Environment variables
TELEGRAM_BANK_BOT_TOKEN = os.environ.get('TELEGRAM_BANK_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_FILE', '/root/inventory-system/service-account.json')

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/inventory-system/bank_bot.log'),
        logging.StreamHandler()
    ]
)

# Initialize Google Sheets
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(GOOGLE_SHEET_ID)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded bank statement PDFs"""
    try:
        logging.info("Received bank statement document")

        # Download the PDF
        doc = await update.message.document.get_file()
        filepath = f"/root/inventory-system/bank_statements/{datetime.now().timestamp()}_{update.message.document.file_name}"
        os.makedirs("/root/inventory-system/bank_statements", exist_ok=True)
        await doc.download_to_drive(filepath)

        logging.info(f"Downloaded bank statement to {filepath}")

        # Read and encode the PDF
        with open(filepath, 'rb') as f:
            file_base64 = base64.b64encode(f.read()).decode('utf-8')

        # Extract transactions using Anthropic
        logging.info("Extracting transactions from bank statement using Anthropic API")
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": file_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": """Extract ALL incoming payments (credits/deposits) from this bank statement.

IMPORTANT: Ignore all outgoing payments, withdrawals, and debits.

For each incoming payment, extract:
- date: in YYYY-MM-DD format
- amount: as a number (no currency symbols)
- payer: company or person name who made the payment
- reference: any reference number or description

Return ONLY valid JSON array with no markdown:
[
  {"date": "2024-01-15", "amount": 1500.50, "payer": "ABC Company", "reference": "Invoice payment"},
  {"date": "2024-01-16", "amount": 2300.00, "payer": "XYZ Ltd", "reference": "Order #123"}
]

If no incoming payments found, return: []
"""
                    }
                ]
            }]
        )

        output = message.content[0].text.strip()
        # Clean up any markdown formatting
        output = output.replace('```json', '').replace('```', '').strip()
        transactions = json.loads(output)

        logging.info(f"Extracted {len(transactions)} transactions")

        # Get invoices from Google Sheets
        invoices_sheet = sheet.worksheet("Invoices")
        invoices = invoices_sheet.get_all_records()

        matched = []
        partial = []
        unmatched = []

        # Match each transaction to invoices
        for txn in transactions:
            amount = float(txn['amount'])
            payer = txn['payer']
            date = txn['date']

            logging.info(f"Processing transaction: ${amount:.2f} from {payer}")

            best_match = None
            best_ratio = 0

            # Find best matching unpaid invoice
            for idx, inv in enumerate(invoices, start=2):
                # Skip paid invoices
                if inv['Status'] == 'Paid':
                    continue

                # Calculate name similarity
                name_ratio = SequenceMatcher(None, payer.lower(), inv['Customer'].lower()).ratio()

                # Check if amount matches (within 50 cents tolerance)
                amount_match = abs(float(inv['Total']) - amount) <= 0.50

                # Keep track of best match
                if name_ratio > 0.7 and amount_match and name_ratio > best_ratio:
                    best_match = (idx, inv)
                    best_ratio = name_ratio

            if best_match:
                idx, inv = best_match
                invoice_total = float(inv['Total'])

                # Check if full or partial payment
                if abs(invoice_total - amount) <= 0.50:
                    # Full payment
                    invoices_sheet.update(f'J{idx}:K{idx}', [['Paid', date]])
                    matched.append(f"{inv['Invoice#']} - {inv['Customer']} - ${amount:.2f}")
                    logging.info(f"Matched full payment: {inv['Invoice#']}")
                else:
                    # Partial payment
                    remaining = invoice_total - amount
                    invoices_sheet.update(f'J{idx}:K{idx}', [[f'Partial: ${remaining:.2f} remaining', date]])
                    partial.append(f"{inv['Invoice#']} - {inv['Customer']} - ${amount:.2f} paid, ${remaining:.2f} remaining")
                    logging.info(f"Matched partial payment: {inv['Invoice#']}")
            else:
                # No match found
                unmatched.append(f"${amount:.2f} from {payer} on {date} - needs manual review")
                logging.warning(f"Unmatched transaction: ${amount:.2f} from {payer}")

        # Calculate outstanding balance
        invoices = invoices_sheet.get_all_records()  # Refresh after updates
        outstanding = sum(float(inv['Total']) for inv in invoices if inv['Status'] not in ['Paid'] and inv.get('Total'))

        # Build reply message
        reply = f"📊 **BANK STATEMENT RECONCILIATION**\n\n"
        reply += f"Processed: {len(transactions)} transactions\n"
        reply += f"Matched: {len(matched)} invoices\n"
        reply += f"━━━━━━━━━━━━━━━━━━\n\n"

        if matched:
            reply += "✅ **PAID:**\n" + "\n".join(matched) + "\n\n"

        if partial:
            reply += "⚠️ **PARTIAL PAYMENTS:**\n" + "\n".join(partial) + "\n\n"

        if unmatched:
            reply += "❌ **UNMATCHED:**\n" + "\n".join(unmatched) + "\n\n"

        reply += f"━━━━━━━━━━━━━━━━━━\n"
        reply += f"Outstanding balance: ${outstanding:.2f}"

        await update.message.reply_text(reply)
        logging.info("Reconciliation completed successfully")

    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON: {e}\n{traceback.format_exc()}")
        await update.message.reply_text(f"Error parsing bank statement data. Please check the file format.")

    except Exception as e:
        logging.error(f"Error processing bank statement: {e}\n{traceback.format_exc()}")
        await update.message.reply_text(f"Error processing bank statement: {str(e)}")


def main():
    """Start the Telegram bot"""
    logging.info("="*50)
    logging.info("Bank Statement Reconciliation Bot Starting")
    logging.info("="*50)

    # Verify environment variables
    required_vars = ['TELEGRAM_BANK_BOT_TOKEN', 'ANTHROPIC_API_KEY', 'GOOGLE_SHEET_ID']
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        logging.error(f"Missing required environment variables: {', '.join(missing)}")
        return

    # Create application
    app = Application.builder().token(TELEGRAM_BANK_BOT_TOKEN).build()

    # Add PDF document handler
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    logging.info("Bank statement bot ready. Send PDF bank statements to process.")

    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
