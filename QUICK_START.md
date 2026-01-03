# Quick Start Guide - Inventory Management System

## 🚀 Fastest Way to Deploy (5 minutes)

### Prerequisites
- Access to VPS: 5.223.54.209
- All files in this directory ready to upload

### Option 1: Automated Deployment (Recommended)

If you have Python 3 and pip on your local machine:

```bash
# Install paramiko (Python SSH library)
pip3 install paramiko

# Run automated deployment
python3 auto_deploy.py
```

The script will:
- ✓ Connect to VPS
- ✓ Create directories
- ✓ Upload all files
- ✓ Copy service account
- ✓ Install dependencies
- ✓ Set permissions

Then follow the on-screen instructions to:
1. Get Telegram Chat ID
2. Update run_inventory.sh
3. Start the system

### Option 2: Manual Deployment (if automated fails)

```bash
# 1. Connect to VPS
ssh root@5.223.54.209
# Password: t0573066F

# 2. Create directory
mkdir -p /root/inventory-system
exit

# 3. Upload files from your local machine
scp inventory_monitor.py root@5.223.54.209:/root/inventory-system/
scp requirements.txt root@5.223.54.209:/root/inventory-system/
scp run_inventory.sh root@5.223.54.209:/root/inventory-system/

# 4. Continue setup on VPS
ssh root@5.223.54.209

# 5. Copy service account
cp /root/invoice-bot/service-account.json /root/inventory-system/

# 6. Set permissions
chmod +x /root/inventory-system/*.sh /root/inventory-system/*.py

# 7. Install dependencies
cd /root/inventory-system
pip3 install -r requirements.txt --break-system-packages
```

### Get Telegram Chat ID

```bash
# Send a message to your bot first, then:
curl https://api.telegram.org/bot7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ/getUpdates | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2
```

Copy the number that appears.

### Update Configuration

```bash
ssh root@5.223.54.209
nano /root/inventory-system/run_inventory.sh

# Find: export TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
# Replace YOUR_TELEGRAM_CHAT_ID with the number from above
# Save: Ctrl+X, Y, Enter
```

### Start the System

```bash
# Create tmux session
tmux new -s inventory-bot

# Start monitoring
cd /root/inventory-system
./run_inventory.sh

# Should see:
# ========================================
# Inventory Management System
# ========================================
# Connected to existing Inventory sheet
# Connected to existing BOM sheet
# Telegram bot initialized
# Starting email monitoring (checking every 60 seconds)

# Detach: Press Ctrl+B, then D
```

### Verify It's Running

```bash
# Check tmux session
tmux ls
# Should show: inventory-bot: 1 windows

# Check logs
tail -f /root/inventory-system/inventory.log

# You should see periodic log entries every 60 seconds
```

## 📧 Testing the System

### Test 1: Purchase Order

1. Create a simple text document or image with:
   ```
   PURCHASE ORDER
   Product: Product X
   Quantity: 5
   ```

2. Email to: emailtest122221@gmail.com
3. Subject: "Purchase Order #001"
4. Attach the document

5. Within 60 seconds:
   - Check Telegram for inventory update
   - Material A should decrease by 10 (5 × 2)
   - Material B should decrease by 25 (5 × 5)

### Test 2: Supplier Invoice

1. Create a document with:
   ```
   TAX INVOICE
   Item: Material C
   Quantity: 100
   ```

2. Email to: emailtest122221@gmail.com
3. Subject: "Invoice #002"
4. Attach the document

5. Within 60 seconds:
   - Check Telegram for inventory update
   - Material C should increase by 100

## 📊 Access Google Sheet

https://docs.google.com/spreadsheets/d/1cJ04Z9gHcJLJMqcW_yXO0jaCY0t89OBEA-SwaUhtINA/edit

You'll see:
- **Sheet 1 (Inventory)**: Real-time stock levels
- **Sheet 2 (BOM)**: Product material requirements

## 🔧 Common Commands

```bash
# View live logs
tail -f /root/inventory-system/inventory.log

# View errors
tail -f /root/inventory-system/error.log

# Reattach to system
tmux attach -t inventory-bot

# Restart system
tmux kill-session -t inventory-bot
tmux new -s inventory-bot
cd /root/inventory-system
./run_inventory.sh
# Ctrl+B, D to detach

# Check system status
tmux ls
ps aux | grep inventory_monitor
```

## ❓ Troubleshooting

### "No module named 'gspread'"
```bash
cd /root/inventory-system
pip3 install -r requirements.txt --break-system-packages
```

### "Service account file not found"
```bash
cp /root/invoice-bot/service-account.json /root/inventory-system/
```

### "Failed to connect to Google Sheets"
- Verify service account has Editor access to the sheet
- Check GOOGLE_SHEET_ID in run_inventory.sh

### No Telegram messages
- Verify TELEGRAM_CHAT_ID is set correctly
- Test: `curl https://api.telegram.org/bot7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ/getMe`

### Emails not processing
- Check Gmail IMAP is enabled
- Verify App Password is correct
- Ensure email subject contains keywords: "Purchase Order", "Invoice", "Order", "PO", or "Quotation"

## 📁 Files Included

- `inventory_monitor.py` - Main application (AI-powered extraction)
- `requirements.txt` - Python dependencies
- `run_inventory.sh` - Startup script with environment variables
- `README.md` - Complete documentation
- `auto_deploy.py` - Automated deployment script
- `DEPLOYMENT_STEPS.md` - Detailed manual steps
- `QUICK_START.md` - This file

## 🔐 Credentials Summary

- **VPS**: root@5.223.54.209 (password: t0573066F)
- **Gmail**: emailtest122221@gmail.com
- **Gmail App Password**: gcki gxee syfu umgc
- **Telegram Bot**: 7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ
- **Replicate API**: [Contact system admin for token]
- **Google Sheet**: 1cJ04Z9gHcJLJMqcW_yXO0jaCY0t89OBEA-SwaUhtINA

## ✅ Success Checklist

- [ ] Files deployed to /root/inventory-system/
- [ ] Service account copied
- [ ] Dependencies installed
- [ ] Telegram Chat ID configured
- [ ] System running in tmux
- [ ] Test email sent and processed
- [ ] Telegram update received
- [ ] Google Sheet updated

## 📞 Support

Check logs for detailed error messages:
```bash
tail -100 /root/inventory-system/error.log
tail -100 /root/inventory-system/inventory.log
```

For more details, see `README.md` in the same directory.
