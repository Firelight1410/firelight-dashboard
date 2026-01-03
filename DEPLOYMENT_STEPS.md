# Manual Deployment Steps

Follow these steps to deploy the Inventory Management System to your Hetzner VPS.

## Step 1: Connect to VPS

```bash
ssh root@5.223.54.209
# Password: t0573066F
```

## Step 2: Create Directory Structure

Once connected, run:

```bash
mkdir -p /root/inventory-system/attachments
cd /root/inventory-system
```

## Step 3: Create requirements.txt

```bash
cat > /root/inventory-system/requirements.txt << 'EOFFILE'
gspread==6.0.0
google-auth==2.27.0
python-telegram-bot==20.7
replicate==0.25.1
Pillow==10.2.0
PyPDF2==3.0.1
EOFFILE
```

## Step 4: Create inventory_monitor.py

This is a large file. Copy it from your local system or use nano:

```bash
nano /root/inventory-system/inventory_monitor.py
```

Then paste the entire contents of `inventory_monitor.py` and save (Ctrl+X, Y, Enter).

**Alternative:** Use SCP from your local machine:
```bash
scp inventory_monitor.py root@5.223.54.209:/root/inventory-system/
```

## Step 5: Create run_inventory.sh

```bash
cat > /root/inventory-system/run_inventory.sh << 'EOFFILE'
#!/bin/bash
set -e

echo "=========================================="
echo "Inventory Management System"
echo "=========================================="

export GMAIL_USER="emailtest122221@gmail.com"
export GMAIL_APP_PASSWORD="gcki gxee syfu umgc"
export TELEGRAM_BOT_TOKEN="7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ"
export TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
export REPLICATE_API_TOKEN="YOUR_REPLICATE_API_TOKEN"
export GOOGLE_SHEET_ID="1cJ04Z9gHcJLJMqcW_yXO0jaCY0t89OBEA-SwaUhtINA"
export SERVICE_ACCOUNT_FILE="/root/inventory-system/service-account.json"

mkdir -p /root/inventory-system/attachments

if [ ! -f "$SERVICE_ACCOUNT_FILE" ]; then
    echo "ERROR: Service account file not found at $SERVICE_ACCOUNT_FILE"
    exit 1
fi

echo "Starting Inventory Monitor..."
echo "Monitoring: $GMAIL_USER"
echo ""

python3 /root/inventory-system/inventory_monitor.py
EOFFILE
```

## Step 6: Copy Service Account

```bash
cp /root/invoice-bot/service-account.json /root/inventory-system/
```

## Step 7: Set Permissions

```bash
chmod +x /root/inventory-system/run_inventory.sh
chmod +x /root/inventory-system/inventory_monitor.py
```

## Step 8: Install Dependencies

```bash
cd /root/inventory-system
pip3 install -r requirements.txt --break-system-packages
```

## Step 9: Get Telegram Chat ID

On your local machine or in a new terminal:

```bash
# First, send a message to your Telegram bot
# Then run:
curl https://api.telegram.org/bot7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ/getUpdates
```

Look for `"chat":{"id":YOUR_NUMBER` and note the number.

## Step 10: Update Chat ID

```bash
nano /root/inventory-system/run_inventory.sh

# Find this line:
# export TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"

# Replace with your actual chat ID, for example:
# export TELEGRAM_CHAT_ID="123456789"

# Save: Ctrl+X, Y, Enter
```

## Step 11: Test Installation

```bash
# Verify all files exist
ls -la /root/inventory-system/

# Should show:
# - inventory_monitor.py
# - run_inventory.sh (executable)
# - requirements.txt
# - service-account.json
# - attachments/ (directory)
```

## Step 12: Start the System

```bash
# Create tmux session
tmux new -s inventory-bot

# Run the system
cd /root/inventory-system
./run_inventory.sh

# You should see:
# "Inventory Management System Starting"
# "Google Sheets initialized successfully"
# "Starting email monitoring..."
```

## Step 13: Detach from tmux

Press: `Ctrl+B`, then press `D`

The system is now running in the background!

## Step 14: Verify System is Running

```bash
# List tmux sessions
tmux ls

# Should show: inventory-bot: 1 windows

# View logs
tail -f /root/inventory-system/inventory.log

# You should see regular log entries
```

## Quick Reference Commands

```bash
# Reattach to session
tmux attach -t inventory-bot

# Kill session
tmux kill-session -t inventory-bot

# View logs
tail -f /root/inventory-system/inventory.log
tail -f /root/inventory-system/error.log

# Restart system
tmux kill-session -t inventory-bot
tmux new -s inventory-bot
cd /root/inventory-system
./run_inventory.sh
# Ctrl+B, D to detach
```

## Testing

1. Send a test email to emailtest122221@gmail.com
2. Subject: "Purchase Order #TEST"
3. Attach a simple image with text: "Product X, Quantity: 5"
4. Wait 60 seconds
5. Check Telegram for inventory update
6. Check Google Sheet for changes

## Troubleshooting

If the system doesn't start:

```bash
# Check error log
cat /root/inventory-system/error.log

# Verify environment variables
cat /root/inventory-system/run_inventory.sh | grep export

# Test Python script directly
cd /root/inventory-system
source run_inventory.sh
python3 inventory_monitor.py
```
