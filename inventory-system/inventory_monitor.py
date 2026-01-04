#!/usr/bin/env python3
"""
Automated Email-Based Inventory Management System - Anthropic API Version
Monitors Gmail for Purchase Orders and Supplier Invoices
Extracts data using Anthropic API and updates Google Sheets inventory
Generates Quotations and Invoices automatically
"""

import imaplib
import email
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import time
import json
import logging
from datetime import datetime, timedelta
import base64
import re
import traceback
import smtplib

import gspread
from google.oauth2.service_account import Credentials
import anthropic
import requests
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# Environment variables
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_FILE', './service-account.json')

# Business information
COMPANY_NAME = "Precision Manufacturing Pte Ltd"
COMPANY_ADDRESS = "123 Tuas Link 2, #05-01\nSingapore 638742"
COMPANY_GST = "202401234G"
BANK_NAME = "DBS Bank"
BANK_ACCOUNT_NUMBER = "001-234567-8"
BANK_ACCOUNT_NAME = "Precision Manufacturing Pte Ltd"
GST_RATE = 0.09
PAYMENT_TERMS_DAYS = 30
QUOTATION_VALIDITY_DAYS = 14

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/inventory-system/inventory.log'),
        logging.StreamHandler()
    ]
)
error_logger = logging.getLogger('error')
error_handler = logging.FileHandler('/root/inventory-system/error.log')
error_handler.setLevel(logging.ERROR)
error_logger.addHandler(error_handler)

ATTACHMENT_DIR = "/root/inventory-system/attachments"
GENERATED_PDF_DIR = "/root/inventory-system/generated_pdfs"
CHECK_INTERVAL = 60
REORDER_THRESHOLD = 200

PO_EXTRACTION_PROMPT = """You are an expert document extraction system. Extract ALL product information from this purchase order.

CRITICAL RULES:
1. Extract ONLY the base product identifier (e.g. "Product X", "Product Y", "Product Z")
2. IGNORE any descriptions, part numbers, or additional text after the product name
3. If you see "Product X - Industrial Component Assembly", return ONLY "Product X"
4. If you see "Product Y (Premium Grade)", return ONLY "Product Y"
5. Look for patterns like "Product X", "Product Y", "Product Z" - these are the BOM identifiers
6. Extract ALL line items, not just the first one
7. Extract quantity as a number only (no units)

Return ONLY valid JSON array with no markdown, no backticks, no explanations:
[
  {"product": "Product X", "quantity": 50},
  {"product": "Product Y", "quantity": 30}
]

If extraction fails, return: []
"""

INVOICE_EXTRACTION_PROMPT = """You are an expert invoice extraction system. Extract ALL material/item information from this supplier invoice.

CRITICAL RULES:
1. Extract ONLY the base material identifier (e.g. "Material A", "Material B", "Material C")
2. IGNORE any descriptions, part numbers, or additional text after the material name
3. If you see "Material A - Premium Grade Steel", return ONLY "Material A"
4. If you see "Material B (Aluminum Alloy)", return ONLY "Material B"
5. Look for patterns like "Material A", "Material B", "Material C" - these are the inventory identifiers
6. Extract ALL line items, not just the first one
7. Ignore: prices, GST, totals, company names

Return ONLY valid JSON array with no markdown, no backticks, no explanations:
[
  {"material": "Material A", "quantity": 500},
  {"material": "Material B", "quantity": 200}
]

If extraction fails, return: []
"""

INITIAL_MATERIALS = [
    ["Material A", 1000, 200, ""],
    ["Material B", 1000, 200, ""],
    ["Material C", 1000, 200, ""],
    ["Material D", 1000, 200, ""],
    ["Material E", 1000, 200, ""],
    ["Material F", 1000, 200, ""]
]

INITIAL_BOM = [
    ["Product X", 2, 5, 0, 0, 0, 0],
    ["Product Y", 3, 0, 1, 0, 0, 0],
    ["Product Z", 1, 0, 0, 2, 3, 0]
]

INITIAL_PRICES = [
    ["Product X", 100.00],
    ["Product Y", 150.00],
    ["Product Z", 200.00]
]


class InventoryManager:
    def __init__(self):
        self.sheet = None
        self.inventory_sheet = None
        self.bom_sheet = None
        self.price_sheet = None
        self.quotations_sheet = None
        self.invoices_sheet = None
        self.connect_sheets()

    def connect_sheets(self):
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(GOOGLE_SHEET_ID)

            # Inventory sheet
            try:
                self.inventory_sheet = self.sheet.worksheet("Inventory")
                logging.info("Connected to existing Inventory sheet")
            except gspread.WorksheetNotFound:
                logging.info("Creating new Inventory sheet")
                self.inventory_sheet = self.sheet.add_worksheet(title="Inventory", rows=100, cols=10)
                self.inventory_sheet.update('A1:D1', [['Material Name', 'Current Stock', 'Reorder Threshold', 'Last Updated']])
                self.inventory_sheet.update('A2:D7', INITIAL_MATERIALS)

            # BOM sheet
            try:
                self.bom_sheet = self.sheet.worksheet("BOM")
                logging.info("Connected to existing BOM sheet")
            except gspread.WorksheetNotFound:
                logging.info("Creating new BOM sheet")
                self.bom_sheet = self.sheet.add_worksheet(title="BOM", rows=100, cols=10)
                self.bom_sheet.update('A1:G1', [['Product Name', 'Material A', 'Material B', 'Material C', 'Material D', 'Material E', 'Material F']])
                self.bom_sheet.update('A2:G4', INITIAL_BOM)

            # Price List sheet
            try:
                self.price_sheet = self.sheet.worksheet("Price List")
                logging.info("Connected to existing Price List sheet")
            except gspread.WorksheetNotFound:
                logging.info("Creating new Price List sheet")
                self.price_sheet = self.sheet.add_worksheet(title="Price List", rows=100, cols=5)
                self.price_sheet.update('A1:B1', [['Product Name', 'Unit Price']])
                self.price_sheet.update('A2:B4', INITIAL_PRICES)

            # Quotations sheet
            try:
                self.quotations_sheet = self.sheet.worksheet("Quotations")
                logging.info("Connected to existing Quotations sheet")
            except gspread.WorksheetNotFound:
                logging.info("Creating new Quotations sheet")
                self.quotations_sheet = self.sheet.add_worksheet(title="Quotations", rows=100, cols=10)
                self.quotations_sheet.update('A1:I1', [[
                    'Quotation#', 'Date', 'Valid Until', 'Customer', 'Email',
                    'Products', 'Subtotal', 'GST', 'Total'
                ]])

            # Invoices sheet
            try:
                self.invoices_sheet = self.sheet.worksheet("Invoices")
                logging.info("Connected to existing Invoices sheet")
            except gspread.WorksheetNotFound:
                logging.info("Creating new Invoices sheet")
                self.invoices_sheet = self.sheet.add_worksheet(title="Invoices", rows=100, cols=12)
                self.invoices_sheet.update('A1:K1', [[
                    'Invoice#', 'Date', 'Due Date', 'Customer', 'Email',
                    'Products', 'Subtotal', 'GST', 'Total', 'Status', 'Payment Date'
                ]])

            logging.info("Google Sheets initialized successfully")
        except Exception as e:
            error_logger.error(f"Failed to connect to Google Sheets: {e}\n{traceback.format_exc()}")
            raise

    def get_bom(self, product_name):
        try:
            all_bom = self.bom_sheet.get_all_records()
            for row in all_bom:
                if row['Product Name'].lower().strip() == product_name.lower().strip():
                    return {
                        'Material A': row.get('Material A', 0),
                        'Material B': row.get('Material B', 0),
                        'Material C': row.get('Material C', 0),
                        'Material D': row.get('Material D', 0),
                        'Material E': row.get('Material E', 0),
                        'Material F': row.get('Material F', 0)
                    }
            logging.warning(f"BOM not found for product: {product_name}")
            return None
        except Exception as e:
            error_logger.error(f"Error looking up BOM: {e}\n{traceback.format_exc()}")
            return None

    def get_price(self, product_name):
        try:
            all_prices = self.price_sheet.get_all_records()
            for row in all_prices:
                if row['Product Name'].lower().strip() == product_name.lower().strip():
                    return float(row['Unit Price'])
            logging.warning(f"Price not found for product: {product_name}")
            return 0.0
        except Exception as e:
            error_logger.error(f"Error looking up price: {e}\n{traceback.format_exc()}")
            return 0.0

    def update_inventory(self, material_name, quantity_change):
        try:
            all_inventory = self.inventory_sheet.get_all_records()
            for idx, row in enumerate(all_inventory, start=2):
                if row['Material Name'].lower().strip() == material_name.lower().strip():
                    current_stock = row['Current Stock']
                    new_stock = current_stock + quantity_change
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.inventory_sheet.update(f'B{idx}:D{idx}', [[new_stock, row['Reorder Threshold'], timestamp]])
                    logging.info(f"Updated {material_name}: {current_stock} -> {new_stock} (change: {quantity_change:+d})")
                    return True
            logging.warning(f"Material not found in inventory: {material_name}")
            return False
        except Exception as e:
            error_logger.error(f"Error updating inventory: {e}\n{traceback.format_exc()}")
            return False

    def get_inventory_status(self):
        try:
            all_inventory = self.inventory_sheet.get_all_records()
            return all_inventory
        except Exception as e:
            error_logger.error(f"Error getting inventory status: {e}\n{traceback.format_exc()}")
            return []

    def send_telegram_update(self):
        try:
            inventory = self.get_inventory_status()
            if not inventory:
                logging.error("No inventory data to send")
                return

            message = "📦 **INVENTORY UPDATE**\n" + "━━━━━━━━━━━━━━━━━━\n"
            for item in inventory:
                material_name = item['Material Name']
                current_stock = item['Current Stock']
                threshold = item['Reorder Threshold']
                if current_stock < threshold:
                    message += f"🔺 **{material_name}: {current_stock} units - MATERIAL LOW**\n"
                else:
                    message += f"{material_name}: {current_stock} units\n"

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message += "━━━━━━━━━━━━━━━━━━\n" + f"Last Updated: {timestamp}"

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            logging.info("Telegram update sent successfully")
        except Exception as e:
            error_logger.error(f"Error sending Telegram update: {e}\n{traceback.format_exc()}")

    def generate_quotation(self, email_message):
        try:
            # Extract sender email
            sender = email_message['From']
            sender_email = re.search(r'<(.+?)>', sender)
            sender_email = sender_email.group(1) if sender_email else sender

            # Get email body
            body_text = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body_text = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')

            # Extract customer details and items using Anthropic
            logging.info("Extracting quotation data using Anthropic API")
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": f"""Extract quotation request details from this email.

Email From: {sender}
Email Body: {body_text[:1000]}

Extract:
- customer_name (company or person name)
- customer_email
- items: array of {{product, quantity}}

Products available: Product X, Product Y, Product Z

Return ONLY valid JSON with no markdown:
{{"customer_name": "...", "customer_email": "...", "items": [{{"product": "Product X", "quantity": 10}}]}}
"""
                }]
            )

            output = message.content[0].text.strip()
            output = re.sub(r'^```json\s*', '', output)
            output = re.sub(r'^```\s*', '', output)
            output = re.sub(r'\s*```$', '', output)
            data = json.loads(output)

            customer_name = data.get('customer_name', 'Valued Customer')
            customer_email = data.get('customer_email', sender_email)
            items = data.get('items', [])

            if not items:
                logging.warning("No items found in quotation request")
                return False

            # Calculate pricing
            line_items = []
            subtotal = 0
            for item in items:
                product = item['product']
                quantity = int(item['quantity'])
                price = self.get_price(product)
                amount = quantity * price
                subtotal += amount
                line_items.append({
                    'product': product,
                    'quantity': quantity,
                    'price': price,
                    'amount': amount
                })

            gst = subtotal * GST_RATE
            total = subtotal + gst

            # Get next quotation number
            all_quotations = self.quotations_sheet.get_all_records()
            if all_quotations:
                last_num = max([int(q['Quotation#'].split('-')[1]) for q in all_quotations if q.get('Quotation#')])
                quote_num = f"QT-{last_num + 1:04d}"
            else:
                quote_num = "QT-0001"

            # Generate dates
            quote_date = datetime.now()
            valid_until = quote_date + timedelta(days=QUOTATION_VALIDITY_DAYS)

            # Generate PDF
            pdf_filename = f"{GENERATED_PDF_DIR}/quotation_{quote_num}.pdf"
            self._generate_quotation_pdf(
                pdf_filename, quote_num, quote_date, valid_until,
                customer_name, line_items, subtotal, gst, total
            )

            # Email PDF
            self._send_email(
                customer_email,
                f"Quotation {quote_num} from {COMPANY_NAME}",
                f"""Dear {customer_name},

Thank you for your inquiry. Please find attached our quotation {quote_num}.

The quotation is valid for {QUOTATION_VALIDITY_DAYS} days from {quote_date.strftime('%Y-%m-%d')}.

If you have any questions, please don't hesitate to contact us.

Best regards,
{COMPANY_NAME}
{COMPANY_ADDRESS}""",
                pdf_filename
            )

            # Add to quotations sheet
            products_str = ", ".join([f"{item['product']} x{item['quantity']}" for item in line_items])
            self.quotations_sheet.append_row([
                quote_num,
                quote_date.strftime('%Y-%m-%d'),
                valid_until.strftime('%Y-%m-%d'),
                customer_name,
                customer_email,
                products_str,
                f"{subtotal:.2f}",
                f"{gst:.2f}",
                f"{total:.2f}"
            ])

            logging.info(f"Quotation {quote_num} generated and sent to {customer_email}")
            return True

        except Exception as e:
            error_logger.error(f"Error generating quotation: {e}\n{traceback.format_exc()}")
            return False

    def generate_invoice(self, customer_name, customer_email, products_list, email_message=None):
        try:
            # If email_message provided, try to extract better customer details
            if email_message:
                sender = email_message['From']
                sender_email = re.search(r'<(.+?)>', sender)
                customer_email = sender_email.group(1) if sender_email else customer_email

            # Calculate pricing
            line_items = []
            subtotal = 0
            for item in products_list:
                product = item['product']
                quantity = int(item['quantity'])
                price = self.get_price(product)
                amount = quantity * price
                subtotal += amount
                line_items.append({
                    'product': product,
                    'quantity': quantity,
                    'price': price,
                    'amount': amount
                })

            gst = subtotal * GST_RATE
            total = subtotal + gst

            # Get next invoice number
            all_invoices = self.invoices_sheet.get_all_records()
            if all_invoices:
                last_num = max([int(inv['Invoice#'].split('-')[1]) for inv in all_invoices if inv.get('Invoice#')])
                invoice_num = f"INV-{last_num + 1:04d}"
            else:
                invoice_num = "INV-0001"

            # Generate dates
            invoice_date = datetime.now()
            due_date = invoice_date + timedelta(days=PAYMENT_TERMS_DAYS)

            # Generate PDF
            pdf_filename = f"{GENERATED_PDF_DIR}/invoice_{invoice_num}.pdf"
            self._generate_invoice_pdf(
                pdf_filename, invoice_num, invoice_date, due_date,
                customer_name, line_items, subtotal, gst, total
            )

            # Email PDF
            self._send_email(
                customer_email,
                f"Invoice {invoice_num} from {COMPANY_NAME}",
                f"""Dear {customer_name},

Thank you for your order. Please find attached invoice {invoice_num}.

Payment Details:
Bank: {BANK_NAME}
Account Number: {BANK_ACCOUNT_NUMBER}
Account Name: {BANK_ACCOUNT_NAME}

Payment due: {due_date.strftime('%Y-%m-%d')}

Best regards,
{COMPANY_NAME}
{COMPANY_ADDRESS}""",
                pdf_filename
            )

            # Add to invoices sheet
            products_str = ", ".join([f"{item['product']} x{item['quantity']}" for item in line_items])
            self.invoices_sheet.append_row([
                invoice_num,
                invoice_date.strftime('%Y-%m-%d'),
                due_date.strftime('%Y-%m-%d'),
                customer_name,
                customer_email,
                products_str,
                f"{subtotal:.2f}",
                f"{gst:.2f}",
                f"{total:.2f}",
                "Unpaid",
                ""
            ])

            logging.info(f"Invoice {invoice_num} generated and sent to {customer_email}")
            return True

        except Exception as e:
            error_logger.error(f"Error generating invoice: {e}\n{traceback.format_exc()}")
            return False

    def _generate_quotation_pdf(self, filename, quote_num, quote_date, valid_until,
                                customer_name, line_items, subtotal, gst, total):
        c = canvas.Canvas(filename, pagesize=A4)
        width, height = A4

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1*inch, height - 1*inch, COMPANY_NAME)
        c.setFont("Helvetica", 10)
        y = height - 1.3*inch
        for line in COMPANY_ADDRESS.split('\n'):
            c.drawString(1*inch, y, line)
            y -= 0.2*inch
        c.drawString(1*inch, y, f"GST Reg: {COMPANY_GST}")

        # Title
        c.setFont("Helvetica-Bold", 20)
        c.drawString(1*inch, height - 2.5*inch, "QUOTATION")

        # Quote details
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, height - 3*inch, f"Quotation #: {quote_num}")
        c.drawString(1*inch, height - 3.2*inch, f"Date: {quote_date.strftime('%Y-%m-%d')}")
        c.drawString(1*inch, height - 3.4*inch, f"Valid Until: {valid_until.strftime('%Y-%m-%d')}")

        # Customer details
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1*inch, height - 4*inch, "To:")
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, height - 4.2*inch, customer_name)

        # Table
        y = height - 5*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1*inch, y, "Product")
        c.drawString(3.5*inch, y, "Qty")
        c.drawString(4.5*inch, y, "Unit Price")
        c.drawString(6*inch, y, "Amount")

        y -= 0.3*inch
        c.line(1*inch, y, 7*inch, y)

        c.setFont("Helvetica", 10)
        for item in line_items:
            y -= 0.3*inch
            c.drawString(1*inch, y, item['product'])
            c.drawString(3.5*inch, y, str(item['quantity']))
            c.drawString(4.5*inch, y, f"${item['price']:.2f}")
            c.drawString(6*inch, y, f"${item['amount']:.2f}")

        y -= 0.3*inch
        c.line(1*inch, y, 7*inch, y)

        # Totals
        y -= 0.3*inch
        c.drawString(5*inch, y, "Subtotal:")
        c.drawString(6*inch, y, f"${subtotal:.2f}")

        y -= 0.3*inch
        c.drawString(5*inch, y, f"GST (9%):")
        c.drawString(6*inch, y, f"${gst:.2f}")

        y -= 0.3*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(5*inch, y, "Total:")
        c.drawString(6*inch, y, f"${total:.2f}")

        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(1*inch, 1*inch, f"Valid for {QUOTATION_VALIDITY_DAYS} days. Payment terms: Net {PAYMENT_TERMS_DAYS} days.")

        c.save()
        logging.info(f"Generated quotation PDF: {filename}")

    def _generate_invoice_pdf(self, filename, invoice_num, invoice_date, due_date,
                              customer_name, line_items, subtotal, gst, total):
        c = canvas.Canvas(filename, pagesize=A4)
        width, height = A4

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1*inch, height - 1*inch, COMPANY_NAME)
        c.setFont("Helvetica", 10)
        y = height - 1.3*inch
        for line in COMPANY_ADDRESS.split('\n'):
            c.drawString(1*inch, y, line)
            y -= 0.2*inch
        c.drawString(1*inch, y, f"GST Reg: {COMPANY_GST}")

        # Title
        c.setFont("Helvetica-Bold", 20)
        c.drawString(1*inch, height - 2.5*inch, "INVOICE")

        # Invoice details
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, height - 3*inch, f"Invoice #: {invoice_num}")
        c.drawString(1*inch, height - 3.2*inch, f"Date: {invoice_date.strftime('%Y-%m-%d')}")
        c.drawString(1*inch, height - 3.4*inch, f"Due Date: {due_date.strftime('%Y-%m-%d')}")

        # Customer details
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1*inch, height - 4*inch, "Bill To:")
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, height - 4.2*inch, customer_name)

        # Table
        y = height - 5*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1*inch, y, "Product")
        c.drawString(3.5*inch, y, "Qty")
        c.drawString(4.5*inch, y, "Unit Price")
        c.drawString(6*inch, y, "Amount")

        y -= 0.3*inch
        c.line(1*inch, y, 7*inch, y)

        c.setFont("Helvetica", 10)
        for item in line_items:
            y -= 0.3*inch
            c.drawString(1*inch, y, item['product'])
            c.drawString(3.5*inch, y, str(item['quantity']))
            c.drawString(4.5*inch, y, f"${item['price']:.2f}")
            c.drawString(6*inch, y, f"${item['amount']:.2f}")

        y -= 0.3*inch
        c.line(1*inch, y, 7*inch, y)

        # Totals
        y -= 0.3*inch
        c.drawString(5*inch, y, "Subtotal:")
        c.drawString(6*inch, y, f"${subtotal:.2f}")

        y -= 0.3*inch
        c.drawString(5*inch, y, f"GST (9%):")
        c.drawString(6*inch, y, f"${gst:.2f}")

        y -= 0.3*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(5*inch, y, "Total:")
        c.drawString(6*inch, y, f"${total:.2f}")

        # Payment details
        y -= 0.6*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1*inch, y, "Payment Details:")
        c.setFont("Helvetica", 9)
        y -= 0.2*inch
        c.drawString(1*inch, y, f"Bank: {BANK_NAME}")
        y -= 0.2*inch
        c.drawString(1*inch, y, f"Account Number: {BANK_ACCOUNT_NUMBER}")
        y -= 0.2*inch
        c.drawString(1*inch, y, f"Account Name: {BANK_ACCOUNT_NAME}")

        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(1*inch, 1*inch, f"Payment terms: Net {PAYMENT_TERMS_DAYS} days.")

        c.save()
        logging.info(f"Generated invoice PDF: {filename}")

    def _send_email(self, to_email, subject, body, attachment_path):
        try:
            msg = MIMEMultipart()
            msg['From'] = GMAIL_USER
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            # Attach PDF
            with open(attachment_path, 'rb') as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                pdf_attachment.add_header('Content-Disposition', 'attachment',
                                         filename=os.path.basename(attachment_path))
                msg.attach(pdf_attachment)

            # Send email
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()

            logging.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            error_logger.error(f"Error sending email: {e}\n{traceback.format_exc()}")
            return False

    def process_purchase_order(self, product_name, quantity, email_message=None):
        logging.info(f"Processing Purchase Order: {product_name} x {quantity}")
        bom = self.get_bom(product_name)
        if not bom:
            logging.warning(f"Cannot process PO - BOM not found for: {product_name}")
            return False

        materials_updated = False
        for material, ratio in bom.items():
            if ratio > 0:
                quantity_needed = quantity * ratio
                if self.update_inventory(material, -quantity_needed):
                    materials_updated = True

        return materials_updated

    def process_supplier_invoice(self, material_name, quantity):
        logging.info(f"Processing Supplier Invoice: {material_name} x {quantity}")
        return self.update_inventory(material, quantity)


class EmailMonitor:
    def __init__(self, inventory_manager):
        self.inventory_manager = inventory_manager
        self.processed_emails = set()
        self.ensure_attachment_dir()

    def ensure_attachment_dir(self):
        os.makedirs(ATTACHMENT_DIR, exist_ok=True)
        os.makedirs(GENERATED_PDF_DIR, exist_ok=True)

    def connect_imap(self):
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(GMAIL_USER, GMAIL_PASSWORD)
            return mail
        except Exception as e:
            error_logger.error(f"IMAP connection failed: {e}\n{traceback.format_exc()}")
            raise

    def get_email_body_preview(self, message):
        """Extract first 500 chars of email body"""
        try:
            body_text = ""
            if message.is_multipart():
                for part in message.walk():
                    if part.get_content_type() == "text/plain":
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body_text = message.get_payload(decode=True).decode('utf-8', errors='ignore')
            return body_text[:500]
        except:
            return ""

    def classify_email(self, subject, body_preview):
        """Use Anthropic to classify email type"""
        try:
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=100,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": f"""Classify this email into ONE category:
- QUOTATION_REQUEST: Customer asking for price quote
- PURCHASE_ORDER: Customer placing an order for products
- SUPPLIER_INVOICE: Supplier billing for materials
- OTHER: None of the above

Email Subject: {subject}
Email Body Preview: {body_preview}

Return ONLY the category name, nothing else."""
                }]
            )

            classification = message.content[0].text.strip()
            logging.info(f"Email classified as: {classification}")
            return classification
        except Exception as e:
            error_logger.error(f"Error classifying email: {e}\n{traceback.format_exc()}")
            return "OTHER"

    def check_supplier_invoice_for_materials(self, body_preview):
        """Check if supplier invoice contains known materials"""
        try:
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=50,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": f"""Does this invoice mention any of these materials: Material A, Material B, Material C, Material D, Material E, Material F?

Email: {body_preview}

Return ONLY: MATERIALS or OTHER"""
                }]
            )

            result = message.content[0].text.strip()
            return result == "MATERIALS"
        except Exception as e:
            error_logger.error(f"Error checking invoice materials: {e}\n{traceback.format_exc()}")
            return False

    def check_emails(self):
        try:
            mail = self.connect_imap()
            mail.select('inbox')
            _, message_numbers = mail.search(None, 'UNSEEN')

            for num in message_numbers[0].split():
                email_id = num.decode()
                if email_id in self.processed_emails:
                    continue

                _, msg_data = mail.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                message = email.message_from_bytes(email_body)

                subject, encoding = decode_header(message['Subject'])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or 'utf-8')

                logging.info(f"Processing email: {subject}")

                # Get email body preview
                body_preview = self.get_email_body_preview(message)

                # Classify email using AI
                classification = self.classify_email(subject, body_preview)

                # Route based on classification
                if classification == "QUOTATION_REQUEST":
                    logging.info("Processing as quotation request")
                    self.inventory_manager.generate_quotation(message)

                elif classification == "PURCHASE_ORDER":
                    logging.info("Processing as purchase order")
                    # Extract customer info first
                    sender = message['From']
                    sender_email = re.search(r'<(.+?)>', sender)
                    customer_email = sender_email.group(1) if sender_email else sender

                    # Extract customer name using AI
                    try:
                        ai_response = anthropic_client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=100,
                            temperature=0,
                            messages=[{
                                "role": "user",
                                "content": f"Extract customer/company name from: {sender}. Return ONLY the name."
                            }]
                        )
                        customer_name = ai_response.content[0].text.strip()
                    except:
                        customer_name = "Valued Customer"

                    # Process attachments for PO details
                    self.process_attachments(message, is_purchase_order=True,
                                            customer_name=customer_name,
                                            customer_email=customer_email)

                elif classification == "SUPPLIER_INVOICE":
                    logging.info("Processing as supplier invoice")
                    # Check if it contains materials
                    if self.check_supplier_invoice_for_materials(body_preview):
                        self.process_attachments(message, is_purchase_order=False)
                    else:
                        logging.info("Supplier invoice doesn't contain tracked materials, skipping")

                else:
                    logging.info("Email classified as OTHER, skipping")

                self.processed_emails.add(email_id)

            mail.close()
            mail.logout()
        except Exception as e:
            error_logger.error(f"Error checking emails: {e}\n{traceback.format_exc()}")

    def process_attachments(self, message, is_purchase_order, customer_name=None, customer_email=None):
        for part in message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if not filename:
                continue

            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.pdf', '.png', '.jpg', '.jpeg']:
                continue

            filepath = os.path.join(ATTACHMENT_DIR, f"{datetime.now().timestamp()}_{filename}")
            with open(filepath, 'wb') as f:
                f.write(part.get_payload(decode=True))

            logging.info(f"Saved attachment: {filepath}")
            self.extract_and_process(filepath, is_purchase_order, message,
                                    customer_name, customer_email)

    def extract_and_process(self, filepath, is_purchase_order, email_message=None,
                           customer_name=None, customer_email=None):
        try:
            if is_purchase_order:
                prompt = PO_EXTRACTION_PROMPT
            else:
                prompt = INVOICE_EXTRACTION_PROMPT

            logging.info(f"Extracting data from {filepath} using Anthropic API")

            with open(filepath, 'rb') as f:
                file_data = f.read()
                file_base64 = base64.b64encode(file_data).decode('utf-8')

            ext = os.path.splitext(filepath)[1].lower()
            if ext == '.pdf':
                media_type = "application/pdf"
            elif ext == '.png':
                media_type = "image/png"
            elif ext in ['.jpg', '.jpeg']:
                media_type = "image/jpeg"
            else:
                logging.error(f"Unsupported file type: {ext}")
                return

            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": file_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            output = message.content[0].text
            logging.info(f"Anthropic API response: {output}")

            clean_output = output.strip()
            clean_output = re.sub(r'^```json\s*', '', clean_output)
            clean_output = re.sub(r'^```\s*', '', clean_output)
            clean_output = re.sub(r'\s*```$', '', clean_output)
            data = json.loads(clean_output)

            inventory_changed = False
            products_for_invoice = []

            if is_purchase_order:
                if isinstance(data, list):
                    for item in data:
                        product = item.get('product', 'UNKNOWN')
                        quantity = item.get('quantity', 0)
                        if product != 'UNKNOWN' and quantity > 0:
                            if self.inventory_manager.process_purchase_order(product, quantity, email_message):
                                inventory_changed = True
                                products_for_invoice.append({'product': product, 'quantity': quantity})
                else:
                    product = data.get('product', 'UNKNOWN')
                    quantity = data.get('quantity', 0)
                    if product != 'UNKNOWN' and quantity > 0:
                        if self.inventory_manager.process_purchase_order(product, quantity, email_message):
                            inventory_changed = True
                            products_for_invoice.append({'product': product, 'quantity': quantity})

                # Generate invoice after processing PO
                if products_for_invoice and customer_name and customer_email:
                    self.inventory_manager.generate_invoice(customer_name, customer_email,
                                                           products_for_invoice, email_message)
            else:
                if isinstance(data, list):
                    for item in data:
                        material = item.get('material', 'UNKNOWN')
                        quantity = item.get('quantity', 0)
                        if material != 'UNKNOWN' and quantity > 0:
                            if self.inventory_manager.process_supplier_invoice(material, quantity):
                                inventory_changed = True
                else:
                    material = data.get('material', 'UNKNOWN')
                    quantity = data.get('quantity', 0)
                    if material != 'UNKNOWN' and quantity > 0:
                        if self.inventory_manager.process_supplier_invoice(material, quantity):
                            inventory_changed = True

            if inventory_changed:
                self.inventory_manager.send_telegram_update()

        except json.JSONDecodeError as e:
            error_logger.error(f"Failed to parse JSON: {output}\n{e}\n{traceback.format_exc()}")
        except Exception as e:
            error_logger.error(f"Error extracting/processing document: {e}\n{traceback.format_exc()}")


def main():
    logging.info("="*50)
    logging.info("Inventory Management System Starting (Anthropic API)")
    logging.info("="*50)

    required_vars = [
        'GMAIL_USER', 'GMAIL_APP_PASSWORD', 'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID', 'ANTHROPIC_API_KEY', 'GOOGLE_SHEET_ID'
    ]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        logging.error(f"Missing required environment variables: {', '.join(missing)}")
        return

    try:
        inventory_manager = InventoryManager()
        email_monitor = EmailMonitor(inventory_manager)

        logging.info("Sending initial inventory status")
        inventory_manager.send_telegram_update()

        logging.info(f"Starting email monitoring (checking every {CHECK_INTERVAL} seconds)")
        while True:
            try:
                email_monitor.check_emails()
            except Exception as e:
                error_logger.error(f"Error in monitoring loop: {e}\n{traceback.format_exc()}")
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")
    except Exception as e:
        error_logger.error(f"Fatal error: {e}\n{traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
