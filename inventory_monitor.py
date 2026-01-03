#!/usr/bin/env python3
"""
Automated Email-Based Inventory Management System
Monitors Gmail for Purchase Orders and Supplier Invoices
Extracts data using Replicate API and updates Google Sheets inventory
"""

import imaplib
import email
from email.header import decode_header
import os
import time
import json
import logging
from datetime import datetime
import base64
import re
import traceback

import gspread
from google.oauth2.service_account import Credentials
import replicate
from telegram import Bot
from telegram.constants import ParseMode
import asyncio

# Configuration
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
REPLICATE_API_TOKEN = os.environ.get('REPLICATE_API_TOKEN')
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_FILE', './service-account.json')

# Logging setup
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

# Constants
SUBJECT_KEYWORDS = ["Purchase Order", "Invoice", "Order", "PO", "Quotation"]
ATTACHMENT_DIR = "/root/inventory-system/attachments"
CHECK_INTERVAL = 60  # seconds
REORDER_THRESHOLD = 200

# Replicate model - prefer Sonnet 3.5
REPLICATE_MODEL = "anthropic/claude-3.5-sonnet:latest"

# Extraction prompts
PO_EXTRACTION_PROMPT = """You are an expert document extraction system. Extract product information from this purchase order image.

CRITICAL RULES:
1. This can be ANY format: handwritten form, typed document, Excel screenshot, scanned paper, digital PO
2. Look for: Product/Item name, Quantity/Qty ordered
3. Common field names: "Product", "Item", "Description", "Part Number", "SKU", "Quantity", "Qty", "Units"
4. Ignore: supplier info, customer info, prices, dates (extract ONLY product and quantity)
5. If multiple products listed, extract ONLY the first one
6. If quantity has units like "pcs", "units", "boxes" - extract just the number

Return ONLY valid JSON with no markdown, no backticks, no explanations:
{"product": "exact product name", "quantity": numeric_value}

If extraction fails, return: {"product": "UNKNOWN", "quantity": 0}
"""

INVOICE_EXTRACTION_PROMPT = """You are an expert invoice extraction system. Extract material/item information from this supplier invoice.

CRITICAL RULES:
1. This can be ANY format: tax invoice, proforma, delivery note, packing list, handwritten, scanned
2. Look for: Material/Item/Product name, Quantity/Qty received
3. Common field names: "Description", "Item", "Product", "Material", "Part", "Quantity", "Qty", "Units Supplied"
4. The material name is in the line items section (NOT the company name)
5. If multiple items listed, extract ONLY the first one
6. Ignore: prices, GST, totals, company names

Return ONLY valid JSON with no markdown, no backticks, no explanations:
{"material": "exact material name", "quantity": numeric_value}

If extraction fails, return: {"material": "UNKNOWN", "quantity": 0}
"""

# Initial inventory data
INITIAL_MATERIALS = [
    ["Material A", 1000, 200, ""],
    ["Material B", 1000, 200, ""],
    ["Material C", 1000, 200, ""],
    ["Material D", 1000, 200, ""],
    ["Material E", 1000, 200, ""],
    ["Material F", 1000, 200, ""]
]

# Initial BOM data
INITIAL_BOM = [
    ["Product X", 2, 5, 0, 0, 0, 0],
    ["Product Y", 3, 0, 1, 0, 0, 0],
    ["Product Z", 1, 0, 0, 2, 3, 0]
]


class InventoryManager:
    """Manages inventory operations with Google Sheets"""

    def __init__(self):
        self.sheet = None
        self.inventory_sheet = None
        self.bom_sheet = None
        self.bot = None
        self.connect_sheets()
        self.setup_telegram()

    def connect_sheets(self):
        """Connect to Google Sheets and initialize if needed"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(GOOGLE_SHEET_ID)

            # Initialize Inventory sheet
            try:
                self.inventory_sheet = self.sheet.worksheet("Inventory")
                logging.info("Connected to existing Inventory sheet")
            except gspread.WorksheetNotFound:
                logging.info("Creating new Inventory sheet")
                self.inventory_sheet = self.sheet.add_worksheet(title="Inventory", rows=100, cols=10)
                self.inventory_sheet.update('A1:D1', [['Material Name', 'Current Stock', 'Reorder Threshold', 'Last Updated']])
                # Add initial data
                self.inventory_sheet.update('A2:D7', INITIAL_MATERIALS)

            # Initialize BOM sheet
            try:
                self.bom_sheet = self.sheet.worksheet("BOM")
                logging.info("Connected to existing BOM sheet")
            except gspread.WorksheetNotFound:
                logging.info("Creating new BOM sheet")
                self.bom_sheet = self.sheet.add_worksheet(title="BOM", rows=100, cols=10)
                self.bom_sheet.update('A1:G1', [['Product Name', 'Material A', 'Material B', 'Material C', 'Material D', 'Material E', 'Material F']])
                # Add initial BOM data
                self.bom_sheet.update('A2:G4', INITIAL_BOM)

            logging.info("Google Sheets initialized successfully")

        except Exception as e:
            error_logger.error(f"Failed to connect to Google Sheets: {e}\n{traceback.format_exc()}")
            raise

    def setup_telegram(self):
        """Initialize Telegram bot"""
        try:
            self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
            logging.info("Telegram bot initialized")
        except Exception as e:
            error_logger.error(f"Failed to initialize Telegram bot: {e}\n{traceback.format_exc()}")
            raise

    def get_bom(self, product_name):
        """Look up BOM for a product"""
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

    def update_inventory(self, material_name, quantity_change):
        """Update inventory for a material (positive = add, negative = subtract)"""
        try:
            all_inventory = self.inventory_sheet.get_all_records()

            for idx, row in enumerate(all_inventory, start=2):  # start=2 because row 1 is header
                if row['Material Name'].lower().strip() == material_name.lower().strip():
                    current_stock = row['Current Stock']
                    new_stock = current_stock + quantity_change

                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    # Update the row
                    self.inventory_sheet.update(f'B{idx}:D{idx}', [[new_stock, row['Reorder Threshold'], timestamp]])

                    logging.info(f"Updated {material_name}: {current_stock} -> {new_stock} (change: {quantity_change:+d})")
                    return True

            logging.warning(f"Material not found in inventory: {material_name}")
            return False

        except Exception as e:
            error_logger.error(f"Error updating inventory: {e}\n{traceback.format_exc()}")
            return False

    def get_inventory_status(self):
        """Get current inventory status for all materials"""
        try:
            all_inventory = self.inventory_sheet.get_all_records()
            return all_inventory
        except Exception as e:
            error_logger.error(f"Error getting inventory status: {e}\n{traceback.format_exc()}")
            return []

    async def send_telegram_update(self):
        """Send complete inventory update to Telegram"""
        try:
            inventory = self.get_inventory_status()

            if not inventory:
                logging.error("No inventory data to send")
                return

            # Build message
            message = "📦 **INVENTORY UPDATE**\n"
            message += "━━━━━━━━━━━━━━━━━━\n"

            for item in inventory:
                material_name = item['Material Name']
                current_stock = item['Current Stock']
                threshold = item['Reorder Threshold']

                if current_stock < threshold:
                    # Low stock - bold with warning
                    message += f"🔺 **{material_name}: {current_stock} units - MATERIAL LOW**\n"
                else:
                    # Normal stock
                    message += f"{material_name}: {current_stock} units\n"

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message += "━━━━━━━━━━━━━━━━━━\n"
            message += f"Last Updated: {timestamp}"

            # Send message
            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )

            logging.info("Telegram update sent successfully")

        except Exception as e:
            error_logger.error(f"Error sending Telegram update: {e}\n{traceback.format_exc()}")

    def process_purchase_order(self, product_name, quantity):
        """Process a purchase order - subtract materials based on BOM"""
        logging.info(f"Processing Purchase Order: {product_name} x {quantity}")

        bom = self.get_bom(product_name)
        if not bom:
            logging.warning(f"Cannot process PO - BOM not found for: {product_name}")
            return False

        # Calculate materials needed and update inventory
        materials_updated = False
        for material, ratio in bom.items():
            if ratio > 0:
                quantity_needed = quantity * ratio
                if self.update_inventory(material, -quantity_needed):
                    materials_updated = True

        return materials_updated

    def process_supplier_invoice(self, material_name, quantity):
        """Process a supplier invoice - add materials to inventory"""
        logging.info(f"Processing Supplier Invoice: {material_name} x {quantity}")

        return self.update_inventory(material_name, quantity)


class EmailMonitor:
    """Monitors Gmail for purchase orders and invoices"""

    def __init__(self, inventory_manager):
        self.inventory_manager = inventory_manager
        self.processed_emails = set()
        self.ensure_attachment_dir()

    def ensure_attachment_dir(self):
        """Create attachments directory if it doesn't exist"""
        os.makedirs(ATTACHMENT_DIR, exist_ok=True)

    def connect_imap(self):
        """Connect to Gmail via IMAP"""
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(GMAIL_USER, GMAIL_PASSWORD)
            return mail
        except Exception as e:
            error_logger.error(f"IMAP connection failed: {e}\n{traceback.format_exc()}")
            raise

    def check_emails(self):
        """Check for new emails matching criteria"""
        try:
            mail = self.connect_imap()
            mail.select('inbox')

            # Search for unread emails
            _, message_numbers = mail.search(None, 'UNSEEN')

            for num in message_numbers[0].split():
                email_id = num.decode()

                # Skip if already processed
                if email_id in self.processed_emails:
                    continue

                _, msg_data = mail.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                message = email.message_from_bytes(email_body)

                # Decode subject
                subject, encoding = decode_header(message['Subject'])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or 'utf-8')

                logging.info(f"Processing email: {subject}")

                # Check if subject contains any keyword
                if not any(keyword.lower() in subject.lower() for keyword in SUBJECT_KEYWORDS):
                    logging.info(f"Subject doesn't match criteria, skipping")
                    self.processed_emails.add(email_id)
                    continue

                # Determine document type based on subject
                is_purchase_order = any(kw in subject.lower() for kw in ['purchase order', 'po', 'order'])

                # Process attachments
                self.process_attachments(message, is_purchase_order)

                self.processed_emails.add(email_id)

            mail.close()
            mail.logout()

        except Exception as e:
            error_logger.error(f"Error checking emails: {e}\n{traceback.format_exc()}")

    def process_attachments(self, message, is_purchase_order):
        """Extract and process attachments from email"""
        for part in message.walk():
            if part.get_content_maintype() == 'multipart':
                continue

            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if not filename:
                continue

            # Check if it's a valid attachment type
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.pdf', '.png', '.jpg', '.jpeg']:
                continue

            # Save attachment
            filepath = os.path.join(ATTACHMENT_DIR, f"{datetime.now().timestamp()}_{filename}")
            with open(filepath, 'wb') as f:
                f.write(part.get_payload(decode=True))

            logging.info(f"Saved attachment: {filepath}")

            # Extract data from attachment
            self.extract_and_process(filepath, is_purchase_order)

    def extract_and_process(self, filepath, is_purchase_order):
        """Extract data using Replicate API and process"""
        try:
            # Prepare prompt based on document type
            if is_purchase_order:
                prompt = PO_EXTRACTION_PROMPT
            else:
                prompt = INVOICE_EXTRACTION_PROMPT

            logging.info(f"Extracting data from {filepath} using Replicate API")

            # Call Replicate API with temperature=0 for consistency
            with open(filepath, 'rb') as f:
                file_data = f.read()
                file_base64 = base64.b64encode(file_data).decode('utf-8')

            # Determine file type
            ext = os.path.splitext(filepath)[1].lower()
            if ext == '.pdf':
                data_uri = f"data:application/pdf;base64,{file_base64}"
            elif ext in ['.png', '.jpg', '.jpeg']:
                mime_type = 'image/png' if ext == '.png' else 'image/jpeg'
                data_uri = f"data:{mime_type};base64,{file_base64}"
            else:
                logging.error(f"Unsupported file type: {ext}")
                return

            # Run Replicate API
            output = replicate.run(
                REPLICATE_MODEL,
                input={
                    "prompt": prompt,
                    "image": data_uri,
                    "temperature": 0  # CRITICAL: temperature=0 for consistency
                }
            )

            # Combine output if it's a generator
            if hasattr(output, '__iter__') and not isinstance(output, str):
                output = ''.join(output)

            logging.info(f"Replicate API response: {output}")

            # Parse JSON response
            # Clean up response - remove markdown code blocks if present
            clean_output = output.strip()
            clean_output = re.sub(r'^```json\s*', '', clean_output)
            clean_output = re.sub(r'^```\s*', '', clean_output)
            clean_output = re.sub(r'\s*```$', '', clean_output)

            data = json.loads(clean_output)

            # Process based on document type
            inventory_changed = False

            if is_purchase_order:
                product = data.get('product', 'UNKNOWN')
                quantity = data.get('quantity', 0)

                if product != 'UNKNOWN' and quantity > 0:
                    inventory_changed = self.inventory_manager.process_purchase_order(product, quantity)
            else:
                material = data.get('material', 'UNKNOWN')
                quantity = data.get('quantity', 0)

                if material != 'UNKNOWN' and quantity > 0:
                    inventory_changed = self.inventory_manager.process_supplier_invoice(material, quantity)

            # Send Telegram update if inventory changed
            if inventory_changed:
                asyncio.run(self.inventory_manager.send_telegram_update())

        except json.JSONDecodeError as e:
            error_logger.error(f"Failed to parse JSON from Replicate: {output}\n{e}\n{traceback.format_exc()}")
        except Exception as e:
            error_logger.error(f"Error extracting/processing document: {e}\n{traceback.format_exc()}")


def main():
    """Main loop"""
    logging.info("="*50)
    logging.info("Inventory Management System Starting")
    logging.info("="*50)

    # Validate environment variables
    required_vars = ['GMAIL_USER', 'GMAIL_APP_PASSWORD', 'TELEGRAM_BOT_TOKEN',
                     'TELEGRAM_CHAT_ID', 'REPLICATE_API_TOKEN', 'GOOGLE_SHEET_ID']
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        logging.error(f"Missing required environment variables: {', '.join(missing)}")
        return

    try:
        # Initialize managers
        inventory_manager = InventoryManager()
        email_monitor = EmailMonitor(inventory_manager)

        # Send initial status
        logging.info("Sending initial inventory status")
        asyncio.run(inventory_manager.send_telegram_update())

        logging.info(f"Starting email monitoring (checking every {CHECK_INTERVAL} seconds)")

        # Main monitoring loop
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
