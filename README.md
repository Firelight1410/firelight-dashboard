# Automated Email-Based Inventory Management System

## Overview

This system automatically monitors a Gmail inbox for Purchase Orders and Supplier Invoices, extracts product/material information using AI (Replicate API with Claude vision model), updates inventory in Google Sheets, and sends real-time Telegram notifications.

## Features

- **Email Monitoring**: Checks Gmail every 60 seconds for relevant emails
- **Document Processing**: Handles PDF, PNG, JPG, JPEG attachments
- **AI Extraction**: Uses Claude 3.5 Sonnet via Replicate API with temperature=0 for consistent results
- **Bill of Materials (BOM)**: Automatically calculates material requirements from product orders
- **Inventory Tracking**: Real-time updates to Google Sheets
- **Telegram Alerts**: Instant notifications with complete inventory status after every change
- **Low Stock Warnings**: Automatic alerts when materials fall below threshold (200 units)

## System Architecture

```
Gmail Inbox → Email Monitor → Replicate API (Claude 3.5) → Google Sheets → Telegram Bot
                    ↓
              Attachment Processing
                    ↓
              Document Classification
                    ↓
         Purchase Order / Invoice
                    ↓
        BOM Lookup / Direct Update
                    ↓
         Inventory Adjustment
                    ↓
            Telegram Notification
```

## Prerequisites

- Hetzner VPS (5.223.54.209)
- Python 3.x
- Gmail account with App Password
- Telegram Bot
- Replicate API account
- Google Cloud Service Account
- Google Sheet

## Installation

### Step 1: Connect to VPS

```bash
ssh root@5.223.54.209
# Password: t0573066F
```

### Step 2: Create Project Directory

```bash
mkdir -p /root/inventory-system
cd /root/inventory-system
```

### Step 3: Create Project Files

Create the following files in `/root/inventory-system/`:

1. **requirements.txt**
2. **inventory_monitor.py**
3. **run_inventory.sh**

(Copy contents from the provided files)

### Step 4: Copy Service Account

```bash
cp /root/invoice-bot/service-account.json /root/inventory-system/
```

### Step 5: Install Dependencies

```bash
pip3 install -r requirements.txt --break-system-packages
```

### Step 6: Get Telegram Chat ID

Before running the system, you need your Telegram Chat ID:

```bash
# Start a conversation with your bot on Telegram
# Send any message to: @YourBotName

# Then run this command to get your chat ID:
curl https://api.telegram.org/bot7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ/getUpdates

# Look for "chat":{"id": YOUR_CHAT_ID in the response
```

### Step 7: Update Chat ID in run_inventory.sh

```bash
nano /root/inventory-system/run_inventory.sh

# Replace this line:
# export TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
# With your actual chat ID:
# export TELEGRAM_CHAT_ID="123456789"
```

### Step 8: Make Script Executable

```bash
chmod +x /root/inventory-system/run_inventory.sh
```

### Step 9: Start the System

```bash
# Create a persistent tmux session
tmux new -s inventory-bot

# Inside tmux, run:
cd /root/inventory-system
./run_inventory.sh
```

### Step 10: Detach from tmux

Press: `Ctrl+B`, then press `D`

The system is now running in the background!

## Management Commands

### Check if System is Running

```bash
tmux ls
# Should show: inventory-bot: 1 windows (created ...)
```

### Reattach to Session

```bash
tmux attach -t inventory-bot
```

### Stop the System

```bash
# Attach to session first
tmux attach -t inventory-bot

# Then press Ctrl+C to stop

# Or kill the session entirely:
tmux kill-session -t inventory-bot
```

### View Logs

```bash
# Main log (all operations)
tail -f /root/inventory-system/inventory.log

# Error log (errors only)
tail -f /root/inventory-system/error.log

# View last 50 lines
tail -n 50 /root/inventory-system/inventory.log
```

## Google Sheets Setup

The system automatically creates two sheets:

### Sheet 1: Inventory

| Material Name | Current Stock | Reorder Threshold | Last Updated |
|--------------|---------------|-------------------|--------------|
| Material A   | 1000          | 200               |              |
| Material B   | 1000          | 200               |              |
| Material C   | 1000          | 200               |              |
| Material D   | 1000          | 200               |              |
| Material E   | 1000          | 200               |              |
| Material F   | 1000          | 200               |              |

### Sheet 2: BOM (Bill of Materials)

| Product Name | Material A | Material B | Material C | Material D | Material E | Material F |
|-------------|-----------|-----------|-----------|-----------|-----------|-----------|
| Product X   | 2         | 5         | 0         | 0         | 0         | 0         |
| Product Y   | 3         | 0         | 1         | 0         | 0         | 0         |
| Product Z   | 1         | 0         | 0         | 2         | 3         | 0         |

## How It Works

### Purchase Order Processing

1. Email arrives with subject containing "Purchase Order", "PO", or "Order"
2. System downloads PDF/image attachments
3. Replicate API extracts: Product name and Quantity
4. System looks up product in BOM sheet
5. Calculates materials needed: `Material Qty = Product Qty × BOM Ratio`
6. Subtracts materials from inventory
7. Sends Telegram update

**Example:**
- Email: "Purchase Order #1234"
- Extracted: Product X, Quantity 10
- BOM: Product X needs 2× Material A, 5× Material B
- Calculation: 10 products × 2 = 20 Material A, 10 × 5 = 50 Material B
- Result: Material A: 1000 → 980, Material B: 1000 → 950

### Supplier Invoice Processing

1. Email arrives with subject containing "Invoice" or "Quotation"
2. System downloads PDF/image attachments
3. Replicate API extracts: Material name and Quantity
4. Adds materials directly to inventory
5. Sends Telegram update

**Example:**
- Email: "Tax Invoice #5678"
- Extracted: Material C, Quantity 500
- Result: Material C: 1000 → 1500

## Telegram Notifications

After every inventory change, you'll receive:

```
📦 **INVENTORY UPDATE**
━━━━━━━━━━━━━━━━━━
Material A: 850 units
🔺 **Material B: 180 units - MATERIAL LOW**
Material C: 950 units
Material D: 720 units
Material E: 1000 units
Material F: 1000 units
━━━━━━━━━━━━━━━━━━
Last Updated: 2026-01-03 14:32:18
```

- ✅ Normal stock (≥200): Regular formatting
- 🔺 Low stock (<200): Bold with warning emoji

## Testing the System

### Test 1: Send a Purchase Order Email

1. Create a simple document with:
   - Text: "Purchase Order"
   - Product: Product X
   - Quantity: 5

2. Email to: emailtest122221@gmail.com
3. Subject: "Purchase Order #TEST001"
4. Attach the document as PDF or image

5. Wait up to 60 seconds
6. Check Telegram for inventory update
7. Verify Google Sheet shows Material A decreased by 10, Material B decreased by 25

### Test 2: Send a Supplier Invoice Email

1. Create a simple document with:
   - Text: "Tax Invoice"
   - Item: Material C
   - Quantity: 100

2. Email to: emailtest122221@gmail.com
3. Subject: "Invoice #INV002"
4. Attach the document

5. Wait up to 60 seconds
6. Check Telegram for inventory update
7. Verify Google Sheet shows Material C increased by 100

### Test 3: Verify Low Stock Alert

1. Send multiple Purchase Orders to reduce Material B below 200
2. Telegram message should show: 🔺 **Material B: XXX units - MATERIAL LOW**

## Supported Document Formats

### Purchase Orders
- Digital PO forms
- Handwritten order forms (scanned)
- Excel/spreadsheet screenshots
- Typed documents
- Company-branded PO templates

### Supplier Invoices
- Tax invoices
- Proforma invoices
- Delivery notes
- Packing lists
- Supplier quotations
- Handwritten receipts

### File Types
- PDF (.pdf)
- PNG (.png)
- JPEG (.jpg, .jpeg)

## Troubleshooting

### System Not Starting

```bash
# Check if tmux session exists
tmux ls

# View logs for errors
tail -n 100 /root/inventory-system/error.log

# Verify environment variables
cat /root/inventory-system/run_inventory.sh | grep export
```

### Emails Not Being Processed

```bash
# Check main log
tail -f /root/inventory-system/inventory.log

# Common issues:
# 1. Gmail App Password incorrect
# 2. Subject doesn't contain keywords
# 3. No attachments in email
# 4. Email already marked as read
```

### Replicate API Errors

```bash
# Check error log
tail -f /root/inventory-system/error.log

# Verify API token:
echo $REPLICATE_API_TOKEN

# Check Replicate account quota:
# Visit: https://replicate.com/account
```

### Google Sheets Not Updating

```bash
# Verify service account file exists
ls -la /root/inventory-system/service-account.json

# Check if Sheet ID is correct
echo $GOOGLE_SHEET_ID

# Ensure service account has Editor access to the Sheet
```

### Telegram Not Sending

```bash
# Test bot manually:
curl -X POST "https://api.telegram.org/bot7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ/sendMessage" \
  -d "chat_id=YOUR_CHAT_ID" \
  -d "text=Test message"

# Verify chat ID is correct in run_inventory.sh
```

### Extraction Accuracy Issues

The system uses **temperature=0** for consistent extraction. If extraction fails:

1. Check error.log for JSON parsing errors
2. Verify document has clear text (not too blurry)
3. Ensure product names match BOM exactly (case-insensitive)
4. Review Replicate API response in inventory.log

## Configuration

### Change Check Interval

Edit `inventory_monitor.py`:
```python
CHECK_INTERVAL = 60  # Change to desired seconds
```

### Add More Materials

1. Add row to Google Sheet "Inventory" tab
2. Add column to "BOM" tab
3. Update INITIAL_MATERIALS and INITIAL_BOM in inventory_monitor.py

### Change Reorder Threshold

Edit Google Sheet "Inventory" tab, column "Reorder Threshold"

### Add More Products

Add rows to Google Sheet "BOM" tab with product name and material quantities

## File Structure

```
/root/inventory-system/
├── inventory_monitor.py      # Main application
├── run_inventory.sh          # Startup script
├── requirements.txt          # Python dependencies
├── service-account.json      # Google Cloud credentials
├── inventory.log             # Operation log
├── error.log                 # Error log
└── attachments/              # Downloaded email attachments
    └── (timestamp)_filename.pdf
```

## Security Notes

- Gmail App Password is used (not main password)
- Service account has limited Google Sheet access only
- Telegram bot token is for notifications only
- All credentials in run_inventory.sh (protect this file)
- Replicate API token has usage limits

## Maintenance

### Daily Tasks
- Monitor Telegram for inventory alerts
- Check for low stock materials

### Weekly Tasks
- Review inventory.log for any errors
- Verify BOM data is up to date

### Monthly Tasks
- Review Replicate API usage
- Clean up old attachments: `rm -rf /root/inventory-system/attachments/*`
- Backup Google Sheet

## Performance

- Email check interval: 60 seconds
- Replicate API response time: 3-10 seconds per document
- Google Sheets update: 1-2 seconds
- Telegram notification: <1 second
- Total processing time: ~5-15 seconds per email

## Limitations

- Processes only first product/material from multi-item documents
- Requires clear, readable documents for accurate extraction
- Dependent on Replicate API availability
- Gmail IMAP must be enabled
- Internet connection required

## Support

### Check System Status

```bash
# Overall health check
tmux attach -t inventory-bot
# Should show "Starting email monitoring..." message

# Recent activity
tail -n 20 /root/inventory-system/inventory.log

# Error count
wc -l /root/inventory-system/error.log
```

### Restart System

```bash
tmux kill-session -t inventory-bot
tmux new -s inventory-bot
cd /root/inventory-system
./run_inventory.sh
# Press Ctrl+B then D to detach
```

## Credentials Summary

- **VPS**: 5.223.54.209 (root / t0573066F)
- **Gmail**: emailtest122221@gmail.com
- **Gmail App Password**: gcki gxee syfu umgc
- **Telegram Bot**: 7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ
- **Replicate API**: [Contact system admin for token]
- **Google Sheet**: 1cJ04Z9gHcJLJMqcW_yXO0jaCY0t89OBEA-SwaUhtINA

## Version

- Version: 1.0.0
- Last Updated: 2026-01-03
- Author: Automated Inventory System
