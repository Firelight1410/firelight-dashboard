# Integrated Manufacturing Business System

A complete AI-powered business automation system for manufacturing companies. This system handles:

- **Inventory Management** - Tracks raw materials and finished products
- **Quotation Generation** - Automatically creates and emails professional quotations
- **Invoice Generation** - Creates invoices for orders with payment tracking
- **Bank Reconciliation** - Matches bank payments to invoices automatically

## 🚀 Features

### 1. Email-Based Inventory System (`inventory_monitor.py`)

- **AI Email Classification** - Uses Anthropic Claude to classify incoming emails as:
  - Quotation Requests (customer asking for prices)
  - Purchase Orders (customer placing orders)
  - Supplier Invoices (materials being delivered)

- **Automatic Quotation Generation**
  - Extracts customer details and product requirements using AI
  - Looks up prices from Google Sheets
  - Generates professional PDF quotations with company branding
  - Emails quotations automatically to customers
  - Tracks quotations in Google Sheets

- **Automatic Invoice Generation**
  - Creates invoices when purchase orders are received
  - Includes GST calculation (9%)
  - Adds payment details (bank account information)
  - Emails invoices to customers
  - Tracks invoice status (Paid/Unpaid/Partial)

- **Inventory Tracking**
  - Deducts materials when products are manufactured (based on BOM)
  - Adds materials when supplier invoices are processed
  - Sends Telegram alerts when inventory is low
  - Updates Google Sheets in real-time

### 2. Bank Statement Reconciliation Bot (`bank_statement_bot.py`)

- **Telegram PDF Upload** - Upload bank statement PDFs via Telegram
- **AI Transaction Extraction** - Uses Claude to extract all incoming payments
- **Fuzzy Matching** - Matches payments to invoices using customer name similarity
- **Automatic Status Updates** - Updates invoice status to Paid/Partial in Google Sheets
- **Reconciliation Reports** - Sends detailed reports via Telegram showing:
  - Matched payments
  - Partial payments
  - Unmatched transactions needing manual review
  - Current outstanding balance

## 📋 Google Sheets Structure

The system maintains 5 sheets:

### Inventory Sheet
| Material Name | Current Stock | Reorder Threshold | Last Updated |
|---------------|---------------|-------------------|--------------|
| Material A    | 1000          | 200               | 2024-01-04   |

### BOM (Bill of Materials) Sheet
| Product Name | Material A | Material B | Material C | Material D | Material E | Material F |
|--------------|------------|------------|------------|------------|------------|------------|
| Product X    | 2          | 5          | 0          | 0          | 0          | 0          |

### Price List Sheet
| Product Name | Unit Price |
|--------------|------------|
| Product X    | 100.00     |

### Quotations Sheet
| Quotation# | Date | Valid Until | Customer | Email | Products | Subtotal | GST | Total |
|------------|------|-------------|----------|-------|----------|----------|-----|-------|

### Invoices Sheet
| Invoice# | Date | Due Date | Customer | Email | Products | Subtotal | GST | Total | Status | Payment Date |
|----------|------|----------|----------|-------|----------|----------|-----|-------|--------|--------------|

## 🛠️ Installation

### Prerequisites

- Python 3.x
- Gmail account with App Password
- Google Cloud Service Account (for Sheets API)
- Anthropic API key
- Telegram Bot tokens

### Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt --break-system-packages
   ```

2. **Configure Environment Variables**

   Copy the example environment file and fill in your credentials:

   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

   Then export the variables before running the scripts:

   ```bash
   source .env  # or set each variable individually
   export GMAIL_USER="your-email@gmail.com"
   export GMAIL_APP_PASSWORD="your-app-password"
   export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
   export TELEGRAM_CHAT_ID="your-chat-id"
   export ANTHROPIC_API_KEY="your-anthropic-api-key"
   export GOOGLE_SHEET_ID="your-google-sheet-id"
   export SERVICE_ACCOUNT_FILE="/path/to/service-account.json"
   export TELEGRAM_BANK_BOT_TOKEN="your-bank-bot-token"
   ```

   **IMPORTANT**: Never commit .env file with real credentials to version control!

3. **Set Up Google Sheets**

   - Create a Google Cloud project
   - Enable Google Sheets API and Google Drive API
   - Create a Service Account and download the JSON credentials
   - Share your Google Sheet with the service account email
   - The system will auto-create all required sheets on first run

4. **Set Up Gmail App Password**

   - Go to Google Account settings
   - Enable 2-Step Verification
   - Generate an App Password for "Mail"

5. **Set Up Telegram Bots**

   - Create two bots using [@BotFather](https://t.me/botfather)
   - One for inventory alerts
   - One for bank statement uploads
   - Get your Chat ID by messaging [@userinfobot](https://t.me/userinfobot)

## 🚀 Usage

### Running the Inventory System

```bash
# Using tmux for persistent sessions
tmux new -s inventory
cd /root/inventory-system
./run_inventory.sh

# Detach from tmux: Ctrl+B, then D
# Reattach: tmux attach -t inventory
```

### Running the Bank Bot

```bash
# In a separate tmux session
tmux new -s bankbot
cd /root/inventory-system
./run_bank_bot.sh

# Detach: Ctrl+B, then D
# Reattach: tmux attach -t bankbot
```

## 📧 Email Workflow

### Quotation Request
1. Customer emails asking for prices
2. System classifies email as QUOTATION_REQUEST
3. AI extracts customer details and products
4. System generates PDF quotation
5. Quotation emailed to customer
6. Record added to Quotations sheet

### Purchase Order
1. Customer emails purchase order (with PDF attachment)
2. System classifies as PURCHASE_ORDER
3. AI extracts products and quantities
4. System:
   - Deducts materials from inventory (based on BOM)
   - Generates invoice PDF
   - Emails invoice to customer
   - Records in Invoices sheet as "Unpaid"
   - Sends Telegram inventory alert

### Supplier Invoice
1. Supplier emails invoice for materials
2. System checks if it contains tracked materials
3. If yes:
   - AI extracts materials and quantities
   - Adds materials to inventory
   - Sends Telegram inventory update

## 💳 Bank Reconciliation Workflow

1. Download bank statement PDF
2. Send PDF to Telegram bank bot
3. Bot extracts all incoming payments
4. Matches payments to unpaid invoices
5. Updates invoice status
6. Sends reconciliation report

## 📊 System Architecture

```
┌─────────────────┐
│   Gmail Inbox   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  AI Email Classifier    │
│  (Anthropic Claude)     │
└────────┬────────────────┘
         │
    ┌────┴────┬──────────────┬──────────────┐
    │         │              │              │
    ▼         ▼              ▼              ▼
┌─────────┐ ┌──────┐ ┌──────────┐ ┌──────────┐
│ Quote   │ │  PO  │ │ Supplier │ │  Other   │
│ Request │ │      │ │ Invoice  │ │ (Skip)   │
└────┬────┘ └──┬───┘ └────┬─────┘ └──────────┘
     │         │           │
     │         │           │
     ▼         ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│Generate  │ │Generate  │ │ Update   │
│Quotation │ │Invoice + │ │Inventory │
│          │ │Update    │ │          │
│          │ │Inventory │ │          │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │             │
     └────────────┴─────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ Google Sheets  │
         │  + Telegram    │
         └────────────────┘
```

## 🏢 Company Information

The system is configured for:

- **Company**: Precision Manufacturing Pte Ltd
- **Address**: 123 Tuas Link 2, #05-01, Singapore 638742
- **GST Registration**: 202401234G
- **Bank**: DBS Bank
- **Account**: 001-234567-8

All generated PDFs include this branding.

## 🔧 Customization

### Adding New Products

Edit `INITIAL_BOM` and `INITIAL_PRICES` in `inventory_monitor.py`, or directly update the Google Sheets.

### Adding New Materials

Edit `INITIAL_MATERIALS` in `inventory_monitor.py`, or update the Google Sheet.

### Changing GST Rate

Modify `GST_RATE = 0.09` in `inventory_monitor.py`.

### Changing Payment Terms

Modify `PAYMENT_TERMS_DAYS = 30` and `QUOTATION_VALIDITY_DAYS = 14` in `inventory_monitor.py`.

## 📝 Logs

- **Inventory System**: `/root/inventory-system/inventory.log`
- **Error Log**: `/root/inventory-system/error.log`
- **Bank Bot**: `/root/inventory-system/bank_bot.log`

## 🔒 Security Notes

- Never commit credentials to version control
- Use environment variables for all secrets
- Keep service account JSON file secure
- Use Gmail App Passwords (not main password)
- Restrict Google Sheet sharing to service account only

## 🧪 Testing

### Test Quotation Request
Send an email with subject "Price Inquiry" and body:
```
Hi, I'd like to get a quote for:
- Product X: 50 units
- Product Y: 30 units

Thanks!
```

### Test Purchase Order
Send an email with subject "Purchase Order PO-12345" with a PDF attachment containing product details.

### Test Bank Reconciliation
Send a bank statement PDF to the Telegram bank bot.

## 📚 Dependencies

- `gspread` - Google Sheets integration
- `google-auth` - Google authentication
- `anthropic` - Claude AI API
- `reportlab` - PDF generation
- `python-telegram-bot` - Telegram bot framework
- `requests` - HTTP requests for Telegram
- `Pillow` - Image processing
- `PyPDF2` - PDF handling

## 🤝 Support

For issues or questions:
1. Check logs in `/root/inventory-system/`
2. Verify all environment variables are set correctly
3. Ensure Google Sheets is shared with service account
4. Verify Telegram bot tokens are active

## 📜 License

Proprietary - For internal use only.

## 🎯 Future Enhancements

- Multi-currency support
- Customer portal
- Purchase order approval workflow
- Inventory forecasting
- Sales analytics dashboard
- Multi-warehouse support
