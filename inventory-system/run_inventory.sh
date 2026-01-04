#!/bin/bash
set -e

# Export environment variables
# IMPORTANT: Set these environment variables before running this script
# You can set them in your shell profile or in a separate .env file

export GMAIL_USER="${GMAIL_USER:-your-email@gmail.com}"
export GMAIL_APP_PASSWORD="${GMAIL_APP_PASSWORD:-your-app-password}"
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-your-telegram-bot-token}"
export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-your-chat-id}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-your-anthropic-api-key}"
export GOOGLE_SHEET_ID="${GOOGLE_SHEET_ID:-your-google-sheet-id}"
export SERVICE_ACCOUNT_FILE="${SERVICE_ACCOUNT_FILE:-/root/inventory-system/service-account.json}"

# Create necessary directories
mkdir -p /root/inventory-system/generated_pdfs
mkdir -p /root/inventory-system/attachments

# Run the inventory monitoring system
echo "Starting Inventory Management System..."
python3 /root/inventory-system/inventory_monitor.py
