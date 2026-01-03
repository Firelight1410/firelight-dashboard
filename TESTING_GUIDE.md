# Testing Guide - Inventory Management System

## Pre-Test Checklist

Before testing, ensure:
- [ ] System is running in tmux: `tmux ls` shows "inventory-bot"
- [ ] Logs show monitoring started: `tail /root/inventory-system/inventory.log`
- [ ] Google Sheet is accessible
- [ ] Telegram bot is responding

## Test Suite

### Test 1: Basic Purchase Order - Digital Document

**Objective**: Verify PO processing with clear digital document

**Steps**:
1. Create a Word document or Google Doc with:
   ```
   PURCHASE ORDER #PO-001
   Date: 2026-01-03

   Product: Product X
   Quantity: 10
   ```

2. Save as PDF or take screenshot (PNG/JPG)

3. Email to: emailtest122221@gmail.com
   - Subject: "Purchase Order #PO-001"
   - Attach the document

4. Wait 60-90 seconds

**Expected Results**:
- ✅ Telegram receives inventory update message
- ✅ Material A: 1000 → 980 (decreased by 20 = 10 products × 2 material ratio)
- ✅ Material B: 1000 → 950 (decreased by 50 = 10 products × 5 material ratio)
- ✅ Other materials unchanged
- ✅ Google Sheet "Inventory" tab shows updated values
- ✅ Log shows: "Processing Purchase Order: Product X x 10"

**Verification**:
```bash
# Check logs
tail -20 /root/inventory-system/inventory.log | grep "Product X"

# Check Google Sheet
# Open: https://docs.google.com/spreadsheets/d/1cJ04Z9gHcJLJMqcW_yXO0jaCY0t89OBEA-SwaUhtINA/edit
```

---

### Test 2: Supplier Invoice - Material Receipt

**Objective**: Verify invoice processing and inventory addition

**Steps**:
1. Create a document with:
   ```
   TAX INVOICE
   Supplier: ABC Materials Ltd
   Invoice No: INV-2026-001

   Description: Material C
   Quantity: 500 units
   ```

2. Save as PDF or screenshot

3. Email to: emailtest122221@gmail.com
   - Subject: "Invoice INV-2026-001"
   - Attach the document

4. Wait 60-90 seconds

**Expected Results**:
- ✅ Telegram receives inventory update
- ✅ Material C: (current) → (current + 500)
- ✅ Google Sheet updated
- ✅ Log shows: "Processing Supplier Invoice: Material C x 500"

---

### Test 3: Handwritten Purchase Order

**Objective**: Test OCR on handwritten documents

**Steps**:
1. Write by hand on paper:
   ```
   Purchase Order
   Product Y - 3 pieces
   ```

2. Take clear photo with phone (good lighting)

3. Email photo to: emailtest122221@gmail.com
   - Subject: "Order from Site"

4. Wait 60-90 seconds

**Expected Results**:
- ✅ Telegram update received
- ✅ Material A: decreased by 9 (3 × 3)
- ✅ Material C: decreased by 3 (3 × 1)
- ✅ Log shows successful extraction

**Note**: If extraction fails, try with clearer handwriting or typed version

---

### Test 4: Low Stock Alert

**Objective**: Verify low stock warnings appear correctly

**Steps**:
1. Check current Material B stock in Google Sheet

2. Calculate how many Product X orders needed to bring Material B below 200:
   - If Material B is at 950 (after Test 1)
   - Need to decrease by 751 more
   - Each Product X uses 5× Material B
   - Need: 751 ÷ 5 = ~151 products

3. Create PO for Product X with quantity 151

4. Email to: emailtest122221@gmail.com
   - Subject: "Large Purchase Order"

5. Wait for processing

**Expected Results**:
- ✅ Telegram shows:
   ```
   🔺 **Material B: XXX units - MATERIAL LOW**
   ```
- ✅ Material B is below 200 in Google Sheet
- ✅ Warning emoji and bold formatting appear

---

### Test 5: Multiple Document Types

**Objective**: Test various document formats

**Test 5a - Excel Screenshot**:
1. Create Excel with columns: Product | Quantity
2. Add row: Product Z | 5
3. Screenshot the spreadsheet
4. Email as "Order via Excel"

**Expected**:
- Material D: decreased by 10 (5 × 2)
- Material E: decreased by 15 (5 × 3)

**Test 5b - Delivery Note (Invoice variant)**:
1. Create document:
   ```
   DELIVERY NOTE
   Material Received: Material F
   Qty: 200
   ```
2. Email subject: "Delivery Note"

**Expected**:
- Material F: increased by 200

---

### Test 6: Invalid/Edge Cases

**Objective**: Verify error handling

**Test 6a - Unknown Product**:
1. Email PO for "Product ABC" (not in BOM)
2. Expected: Logged warning, no inventory change

**Test 6b - No Attachments**:
1. Email with subject "Purchase Order" but no attachment
2. Expected: No processing, no errors

**Test 6c - Wrong File Type**:
1. Email with .docx or .txt attachment (not PDF/image)
2. Expected: Skipped, logged

**Test 6d - Irrelevant Subject**:
1. Email with subject "General Inquiry" with PO attachment
2. Expected: Not processed (subject doesn't match keywords)

---

### Test 7: Concurrent Processing

**Objective**: Test multiple emails in quick succession

**Steps**:
1. Send 3 emails within 1 minute:
   - PO for Product X (qty 2)
   - Invoice for Material A (qty 100)
   - PO for Product Y (qty 5)

2. Wait 2-3 minutes

**Expected Results**:
- ✅ All 3 emails processed
- ✅ 3 separate Telegram updates
- ✅ Inventory reflects all changes:
  - Material A: -4 +100 -15 = +81 net
  - Material B: -10
  - Material C: -5
- ✅ No race conditions or errors

---

### Test 8: End-to-End Workflow

**Objective**: Simulate real business scenario

**Scenario**: Customer orders → Stock depletion → Restock → Alert resolution

**Steps**:
1. **Initial State**: Check all materials in Sheet

2. **Customer Order 1**:
   - PO for Product X × 20
   - Verify inventory decreases

3. **Customer Order 2**:
   - PO for Product X × 30 more
   - Should trigger Material B low stock alert

4. **Restock Order**:
   - Invoice for Material B × 1000
   - Alert should disappear

5. **Final Check**:
   - All materials accounted for
   - No negative stock
   - Logs clean

---

## Automated Test Script

Save as `test_inventory.sh`:

```bash
#!/bin/bash

echo "🧪 Inventory System Test Suite"
echo "=============================="
echo ""

# Test 1: Check if system is running
echo "Test 1: System Status"
if tmux has-session -t inventory-bot 2>/dev/null; then
    echo "✅ Tmux session 'inventory-bot' is running"
else
    echo "❌ Tmux session NOT found"
    exit 1
fi

# Test 2: Check log file exists and is being updated
echo ""
echo "Test 2: Log Files"
if [ -f /root/inventory-system/inventory.log ]; then
    LAST_LOG=$(tail -1 /root/inventory-system/inventory.log)
    echo "✅ Log file exists"
    echo "   Last entry: $LAST_LOG"
else
    echo "❌ Log file not found"
fi

# Test 3: Check error log
echo ""
echo "Test 3: Error Log"
if [ -f /root/inventory-system/error.log ]; then
    ERROR_COUNT=$(wc -l < /root/inventory-system/error.log)
    if [ $ERROR_COUNT -eq 0 ]; then
        echo "✅ No errors logged"
    else
        echo "⚠️  $ERROR_COUNT error(s) in log"
        echo "   Last error:"
        tail -1 /root/inventory-system/error.log
    fi
fi

# Test 4: Check service account
echo ""
echo "Test 4: Service Account"
if [ -f /root/inventory-system/service-account.json ]; then
    echo "✅ Service account file exists"
else
    echo "❌ Service account file missing"
fi

# Test 5: Check Python dependencies
echo ""
echo "Test 5: Dependencies"
python3 -c "import gspread, replicate, telegram" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ All Python modules installed"
else
    echo "❌ Some Python modules missing"
fi

# Test 6: Recent activity
echo ""
echo "Test 6: Recent Activity (last 5 log entries)"
tail -5 /root/inventory-system/inventory.log

echo ""
echo "=============================="
echo "Test suite complete!"
```

Run with:
```bash
chmod +x test_inventory.sh
./test_inventory.sh
```

---

## Performance Benchmarks

Expected processing times:

| Operation | Time | Notes |
|-----------|------|-------|
| Email check cycle | 60s | Configurable in script |
| Replicate API call | 3-10s | Depends on document complexity |
| Google Sheet update | 1-2s | Per material update |
| Telegram send | <1s | Usually instant |
| **Total per email** | **5-15s** | From email arrival to notification |

---

## Monitoring Commands

```bash
# Live log monitoring
tail -f /root/inventory-system/inventory.log

# Filter for specific events
grep "Processing Purchase Order" /root/inventory-system/inventory.log
grep "Processing Supplier Invoice" /root/inventory-system/inventory.log
grep "Updated" /root/inventory-system/inventory.log

# Count processed emails today
grep "$(date +%Y-%m-%d)" /root/inventory-system/inventory.log | grep "Processing" | wc -l

# Check for errors
tail -20 /root/inventory-system/error.log

# View attachments processed
ls -lh /root/inventory-system/attachments/
```

---

## Test Data Reset

To reset inventory to initial state:

```bash
# Method 1: Via Google Sheets
# Open sheet, manually set all materials to 1000

# Method 2: Restart with fresh sheet
# Delete "Inventory" and "BOM" worksheets
# Restart system - it will recreate them

# Method 3: Direct Sheet update (requires gspread)
python3 << 'EOF'
import gspread
from google.oauth2.service_account import Credentials

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('/root/inventory-system/service-account.json', scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open_by_key('1cJ04Z9gHcJLJMqcW_yXO0jaCY0t89OBEA-SwaUhtINA')
inventory = sheet.worksheet('Inventory')

# Reset all to 1000
for i in range(2, 8):  # Rows 2-7
    inventory.update(f'B{i}', [[1000]])

print("✅ Inventory reset to 1000 for all materials")
EOF
```

---

## Success Criteria

System is working correctly if:

1. ✅ All emails matching keywords are processed within 90 seconds
2. ✅ Extraction accuracy >90% for clear documents
3. ✅ Telegram updates sent after every inventory change
4. ✅ Google Sheets always in sync with actual inventory
5. ✅ Low stock alerts appear when stock < 200
6. ✅ No errors in error.log during normal operation
7. ✅ System runs continuously without crashes
8. ✅ BOM calculations are accurate

---

## Troubleshooting Test Failures

### Email not processed
- Check subject has keywords: "Purchase Order", "Invoice", etc.
- Verify attachment is PDF/PNG/JPG
- Check email is marked as UNSEEN in Gmail
- Review inventory.log for processing attempt

### Wrong inventory calculation
- Verify BOM data in Sheet2
- Check product name matches exactly (case-insensitive)
- Review extraction result in logs

### No Telegram update
- Verify TELEGRAM_CHAT_ID is correct
- Test bot directly with curl command
- Check error.log for Telegram errors

### Extraction fails
- Ensure document has clear, readable text
- Try with simpler, typed document first
- Check Replicate API quota and status
- Review error.log for JSON parsing errors

---

## Next Steps After Testing

Once all tests pass:

1. Document any custom products in BOM sheet
2. Adjust reorder thresholds if needed (default: 200)
3. Set up regular monitoring (daily check of logs)
4. Configure email filters to highlight important POs
5. Train team on document format best practices
6. Consider backup/archive strategy for attachments

---

**Happy Testing! 🎉**
