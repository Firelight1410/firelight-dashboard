#!/bin/bash
set -e

# Export environment variables
# IMPORTANT: Set these environment variables before running this script
# You can set them in your shell profile or in a separate .env file

export TELEGRAM_BANK_BOT_TOKEN="${TELEGRAM_BANK_BOT_TOKEN:-your-bank-bot-token}"
export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-your-chat-id}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-your-anthropic-api-key}"
export GOOGLE_SHEET_ID="${GOOGLE_SHEET_ID:-your-google-sheet-id}"
export SERVICE_ACCOUNT_FILE="${SERVICE_ACCOUNT_FILE:-/root/inventory-system/service-account.json}"

# Create necessary directory
mkdir -p /root/inventory-system/bank_statements

# Run the bank statement reconciliation bot
echo "Starting Bank Statement Reconciliation Bot..."
python3 /root/inventory-system/bank_statement_bot.py
