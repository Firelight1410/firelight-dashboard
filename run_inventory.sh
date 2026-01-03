#!/bin/bash
# Startup script for Inventory Management System
# This script sets all environment variables and runs the inventory monitor

# Exit on any error
set -e

echo "=========================================="
echo "Inventory Management System"
echo "=========================================="

# Set environment variables
export GMAIL_USER="emailtest122221@gmail.com"
export GMAIL_APP_PASSWORD="gcki gxee syfu umgc"
export TELEGRAM_BOT_TOKEN="7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ"
export TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"  # Replace with your Telegram chat ID
export REPLICATE_API_TOKEN="YOUR_REPLICATE_API_TOKEN"  # Replace with actual token
export GOOGLE_SHEET_ID="1cJ04Z9gHcJLJMqcW_yXO0jaCY0t89OBEA-SwaUhtINA"
export SERVICE_ACCOUNT_FILE="/root/inventory-system/service-account.json"

# Create necessary directories
mkdir -p /root/inventory-system/attachments

# Verify service account file exists
if [ ! -f "$SERVICE_ACCOUNT_FILE" ]; then
    echo "ERROR: Service account file not found at $SERVICE_ACCOUNT_FILE"
    echo "Please copy it from /root/invoice-bot/service-account.json"
    exit 1
fi

echo "Starting Inventory Monitor..."
echo "Monitoring: $GMAIL_USER"
echo "Google Sheet: $GOOGLE_SHEET_ID"
echo ""

# Run the inventory monitor
python3 /root/inventory-system/inventory_monitor.py
