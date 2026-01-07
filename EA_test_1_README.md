# EA_test_1 - MetaTrader 5 Expert Advisor

## Overview
EA_test_1 is a sophisticated MT5 Expert Advisor that combines moving average crossover strategies with optional stochastic filtering, pyramiding capabilities using Ichimoku indicators, and trailing stop management.

## Key Features

### 1. Initial Entry System
- **MA Crossover Detection**: Uses Fast EMA(109) crossing Slow SMA(175)
- **7-Bar Confirmation**: Requires 7 consecutive bars with proper MA alignment (EMA > SMA(102) > SMA(175) for long)
- **Optional Stochastic Filter**: Can enable/disable stochastic confirmation for entries
- **Single Entry**: Only one initial position per signal

### 2. Pyramiding System
- **Up to 5 Positions**: Configurable maximum pyramid positions
- **Ichimoku Confirmation**: Uses Tenkan-sen and Kijun-sen on M20 timeframe
- **ADX Filter**: Ensures trend strength before adding positions
- **Time Spacing**: Minimum 28 M20 bars between pyramid entries

### 3. Risk Management
- **Fixed Stop Loss**: 2004 points from entry
- **Fixed Take Profit**: 3200 points from entry
- **Trailing Stop**: Activates at 1663 points profit, trails by 485 points
- **Adjustable Lot Size**: Default 0.01 lots (user configurable)

## Input Parameters

### Debug Settings
- `Print_Debug` (false): Enable detailed logging

### Entry - Moving Averages
- `Slow_SMA_Bias` (175): Period for slow SMA
- `Fast_EMA_Confirmation` (109): Period for fast EMA
- `Fast_SMA_DoubleCheck` (102): Period for confirmation SMA
- `Candles_Aligned_Before_Entry` (7): Required aligned bars

### Entry - Stochastic Filter
- `Use_Stoch` (false): Enable/disable stochastic filter
- `Stoch_K` (55): K period
- `Stoch_D` (19): D period
- `Stoch_Slowing` (9): Slowing period

### Pyramiding Settings
- `Enable_Pyramid` (true): Enable/disable pyramiding
- `Max_Pyramid_Positions` (5): Maximum total positions
- `ADX_Period` (24): ADX indicator period
- `ADX_Threshold` (25): Minimum ADX value for pyramid
- `Ichimoku_Timeframe` (M20): Timeframe for Ichimoku analysis
- `Ichi_Tenkan` (54): Tenkan-sen period
- `Ichi_Kijun` (10): Kijun-sen period
- `Ichi_Senkou` (454): Senkou span period
- `Candle_To_Check` (28): Minimum bars between pyramids

### Risk & Exits
- `Initial_Lot` (0.01): Lot size per position
- `StopLoss_Pts` (2004): Stop loss in points
- `TakeProfit_Pts` (3200): Take profit in points

### Trailing Stop
- `Use_TSL` (true): Enable/disable trailing stop
- `TSL_Trigger` (1663): Profit points to activate TSL
- `TSL_Step` (485): Distance to trail stop loss

## Trading Logic

### Initial Entry Process
1. **Crossover Detection**: EA detects when Fast EMA crosses Slow SMA
2. **Alignment Confirmation**: Monitors next 7 closed bars for proper MA alignment
3. **Stochastic Check** (if enabled): Verifies K/D crossover in oversold/overbought zones
4. **Order Placement**: Opens position at bar 8 opening

### Pyramid Entry Process
1. **Position Check**: Verifies current positions < Max_Pyramid_Positions
2. **Ichimoku Analysis**: Confirms price relative to Tenkan-sen and Kijun-sen on M20
3. **ADX Confirmation**: Ensures ADX > threshold for trend strength
4. **Time Spacing**: Validates minimum 28 M20 bars since last entry
5. **Add Position**: Opens additional position in same direction

### Exit Management
- **Fixed SL/TP**: Set at order placement
- **Trailing Stop**: Dynamically adjusts SL when profit threshold reached
- **Direction Specific**: Only trails in favorable direction

## Installation

1. Copy `EA_test_1.mq5` to your MT5 `Experts` folder:
   - `C:\Users\[YourName]\AppData\Roaming\MetaQuotes\Terminal\[Instance]\MQL5\Experts\`

2. Open MetaEditor and compile the EA

3. Restart MT5 or refresh the Navigator panel

4. Drag EA onto desired chart

## Usage Recommendations

### Testing
1. **Start with Demo Account**: Always test on demo first
2. **Recommended Timeframe**: H1 (as per original design)
3. **Initial Settings**: Use default parameters initially
4. **Enable Debug**: Set `Print_Debug = true` for initial testing

### Optimization Tips
- Test with `Use_Stoch = false` first for simpler entries
- Adjust `Max_Pyramid_Positions` based on risk tolerance
- Monitor `ADX_Threshold` - higher values = stricter trend requirements
- Consider disabling pyramiding (`Enable_Pyramid = false`) for conservative trading

### Risk Considerations
- Each pyramid position uses same lot size (compounding risk)
- Maximum exposure = `Initial_Lot * Max_Pyramid_Positions`
- StopLoss_Pts (2004) = ~20.04 pips on 5-digit broker
- Ensure adequate margin for maximum positions

## Technical Details

### Magic Number
- Fixed at 123456
- Used for position tracking and management

### New Bar Detection
- Uses closed candles only (not forming bar)
- Proper time-based bar detection

### Indicator Handles
- Efficient buffer management
- Proper cleanup in OnDeinit()

### Error Handling
- Validates indicator handles
- Checks lot size constraints
- Logs trade execution failures
- Handles buffer copy errors

## Key Points

1. **7-Bar Confirmation**: Critical feature - prevents premature entries
2. **Alignment Reset**: If MA alignment breaks during confirmation, count resets
3. **Points vs Pips**: All parameters in POINTS (5-digit: 10 points = 1 pip)
4. **Magic Number Filtering**: Only manages positions with magic 123456
5. **Pyramid Spacing**: 28 M20 bars ≈ 560 minutes ≈ 9.3 hours

## Troubleshooting

### No Entries
- Check if 7-bar confirmation is being maintained
- Verify stochastic filter isn't too restrictive (try disabling)
- Enable `Print_Debug` to see what's blocking entries

### Pyramiding Not Working
- Verify ADX is above threshold
- Check if 28 M20 bars have passed since last entry
- Ensure positions < Max_Pyramid_Positions

### Trailing Stop Issues
- Confirm profit exceeds TSL_Trigger (1663 points)
- Check broker allows SL modification
- Verify spread isn't causing SL conflicts

## Version History

### v1.00
- Initial release
- MA crossover with 7-bar confirmation
- Optional stochastic filter
- Ichimoku-based pyramiding
- ADX trend filter
- Trailing stop functionality

## Disclaimer
This EA is provided for educational and testing purposes. Always test thoroughly on a demo account before live trading. Past performance does not guarantee future results. Trading involves risk of loss.
