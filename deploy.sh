#!/bin/bash
# Deployment Helper Script for Inventory Management System
# This script helps you deploy to the Hetzner VPS

set -e

echo "=========================================="
echo "Inventory System Deployment Helper"
echo "=========================================="
echo ""
echo "This script will guide you through deploying to:"
echo "VPS: 5.223.54.209"
echo "User: root"
echo "Password: t0573066F"
echo ""
echo "Files to deploy:"
echo "  - inventory_monitor.py"
echo "  - requirements.txt"
echo "  - run_inventory.sh"
echo "  - README.md"
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Check if files exist
if [ ! -f "inventory_monitor.py" ]; then
    echo "ERROR: inventory_monitor.py not found!"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

if [ ! -f "run_inventory.sh" ]; then
    echo "ERROR: run_inventory.sh not found!"
    exit 1
fi

echo ""
echo "Step 1: Creating directory on VPS..."
ssh root@5.223.54.209 'mkdir -p /root/inventory-system/attachments'

echo "Step 2: Copying files to VPS..."
scp inventory_monitor.py root@5.223.54.209:/root/inventory-system/
scp requirements.txt root@5.223.54.209:/root/inventory-system/
scp run_inventory.sh root@5.223.54.209:/root/inventory-system/
scp README.md root@5.223.54.209:/root/inventory-system/

echo "Step 3: Copying service account..."
ssh root@5.223.54.209 'cp /root/invoice-bot/service-account.json /root/inventory-system/'

echo "Step 4: Setting permissions..."
ssh root@5.223.54.209 'chmod +x /root/inventory-system/run_inventory.sh && chmod +x /root/inventory-system/inventory_monitor.py'

echo "Step 5: Installing dependencies..."
ssh root@5.223.54.209 'cd /root/inventory-system && pip3 install -r requirements.txt --break-system-packages'

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "IMPORTANT: Before starting the system, you need to:"
echo "1. Get your Telegram Chat ID:"
echo "   - Message your bot on Telegram"
echo "   - Run: curl https://api.telegram.org/bot7750510634:AAFsElc0jvsl8dbF_RF0JjQKHc05xGPb0sQ/getUpdates"
echo "   - Find the 'chat_id' number"
echo ""
echo "2. Update run_inventory.sh with your Chat ID:"
echo "   ssh root@5.223.54.209"
echo "   nano /root/inventory-system/run_inventory.sh"
echo "   # Change: export TELEGRAM_CHAT_ID=\"YOUR_TELEGRAM_CHAT_ID\""
echo ""
echo "3. Start the system:"
echo "   tmux new -s inventory-bot"
echo "   cd /root/inventory-system"
echo "   ./run_inventory.sh"
echo "   # Press Ctrl+B then D to detach"
echo ""
echo "4. View logs:"
echo "   tail -f /root/inventory-system/inventory.log"
echo ""
