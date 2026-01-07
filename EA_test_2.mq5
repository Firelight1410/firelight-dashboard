//+------------------------------------------------------------------+
//|                                                    EA_test_2.mq5 |
//|                                           Expert Advisor Test 2 |
//+------------------------------------------------------------------+
#property copyright "EA_test_2"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//--- Input Parameters

// Debug
input bool Print_Debug = false;

// Entry - Moving Averages
input int Slow_SMA_Bias = 41;
input int Fast_EMA_Confirmation = 36;
input int Fast_SMA_DoubleCheck = 195;
input int Candles_Aligned_Before_Entry = 2;

// Entry - Stochastic Filter (ENABLED)
input bool Use_Stoch = true;
input int Stoch_K = 52;
input int Stoch_D = 21;
input int Stoch_Slowing = 30;

// Pyramiding (Ichimoku)
input bool Enable_Pyramid = true;
input int Max_Pyramid_Positions = 5;
input int ADX_Period = 14;
input int ADX_Threshold = 65;
input ENUM_TIMEFRAMES Ichimoku_Timeframe = PERIOD_H2; // 2 Hours!
input int Ichi_Tenkan = 28;
input int Ichi_Kijun = 33;
input int Ichi_Senkou = 372;
input int Candle_To_Check = 45;

// Risk & Exits
input double Initial_Lot = 1.0;
input int StopLoss_Pts = 4723;
input int TakeProfit_Pts = 9401;

// Trailing Stop
input bool Use_TSL = true;
input int TSL_Trigger = 1500;
input int TSL_Step = 500;

//--- Global Variables
int magic_number = 0185;
CTrade trade;

// Indicator handles
int handle_fast_ema;
int handle_slow_sma;
int handle_double_sma;
int handle_stoch;
int handle_ichimoku;
int handle_adx;

// Buffers
double fast_ema[];
double slow_sma[];
double double_sma[];
double stoch_k[];
double stoch_d[];
double ichi_tenkan[];
double ichi_kijun[];
double adx_main[];

// New bar detection
datetime last_bar_time = 0;

// Entry tracking
bool crossover_detected = false;
int crossover_direction = 0; // 1 = bullish, -1 = bearish
int aligned_bars_count = 0;

// Pyramid tracking
datetime last_position_time = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Set magic number
   trade.SetExpertMagicNumber(magic_number);

   // Initialize indicator handles
   handle_fast_ema = iMA(_Symbol, PERIOD_CURRENT, Fast_EMA_Confirmation, 0, MODE_EMA, PRICE_CLOSE);
   handle_slow_sma = iMA(_Symbol, PERIOD_CURRENT, Slow_SMA_Bias, 0, MODE_SMA, PRICE_CLOSE);
   handle_double_sma = iMA(_Symbol, PERIOD_CURRENT, Fast_SMA_DoubleCheck, 0, MODE_SMA, PRICE_CLOSE);

   if(Use_Stoch)
   {
      handle_stoch = iStochastic(_Symbol, PERIOD_CURRENT, Stoch_K, Stoch_D, Stoch_Slowing, MODE_SMA, STO_LOWHIGH);
   }

   if(Enable_Pyramid)
   {
      handle_ichimoku = iIchimoku(_Symbol, Ichimoku_Timeframe, Ichi_Tenkan, Ichi_Kijun, Ichi_Senkou);
      handle_adx = iADX(_Symbol, PERIOD_CURRENT, ADX_Period);
   }

   // Validate handles
   if(handle_fast_ema == INVALID_HANDLE || handle_slow_sma == INVALID_HANDLE || handle_double_sma == INVALID_HANDLE)
   {
      Print("Error initializing MA indicators");
      return INIT_FAILED;
   }

   if(Use_Stoch && handle_stoch == INVALID_HANDLE)
   {
      Print("Error initializing Stochastic indicator");
      return INIT_FAILED;
   }

   if(Enable_Pyramid && (handle_ichimoku == INVALID_HANDLE || handle_adx == INVALID_HANDLE))
   {
      Print("Error initializing Ichimoku or ADX indicators");
      return INIT_FAILED;
   }

   // Set array as series
   ArraySetAsSeries(fast_ema, true);
   ArraySetAsSeries(slow_sma, true);
   ArraySetAsSeries(double_sma, true);
   ArraySetAsSeries(stoch_k, true);
   ArraySetAsSeries(stoch_d, true);
   ArraySetAsSeries(ichi_tenkan, true);
   ArraySetAsSeries(ichi_kijun, true);
   ArraySetAsSeries(adx_main, true);

   if(Print_Debug)
      Print("EA_test_2 initialized successfully");

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Release indicator handles
   if(handle_fast_ema != INVALID_HANDLE) IndicatorRelease(handle_fast_ema);
   if(handle_slow_sma != INVALID_HANDLE) IndicatorRelease(handle_slow_sma);
   if(handle_double_sma != INVALID_HANDLE) IndicatorRelease(handle_double_sma);
   if(handle_stoch != INVALID_HANDLE) IndicatorRelease(handle_stoch);
   if(handle_ichimoku != INVALID_HANDLE) IndicatorRelease(handle_ichimoku);
   if(handle_adx != INVALID_HANDLE) IndicatorRelease(handle_adx);

   if(Print_Debug)
      Print("EA_test_2 deinitialized");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check for new bar
   bool is_new_bar = IsNewBar();

   // Update trailing stops on every tick
   if(Use_TSL)
   {
      UpdateTrailingStops();
   }

   // Process pyramiding on every tick if enabled
   if(Enable_Pyramid && is_new_bar)
   {
      ProcessPyramiding();
   }

   // Process entry signals only on new bars
   if(is_new_bar)
   {
      ProcessEntrySignals();
   }
}

//+------------------------------------------------------------------+
//| Check if new bar has formed                                      |
//+------------------------------------------------------------------+
bool IsNewBar()
{
   datetime current_time[];
   ArraySetAsSeries(current_time, true);

   if(CopyTime(_Symbol, PERIOD_CURRENT, 0, 1, current_time) <= 0)
      return false;

   if(last_bar_time != current_time[0])
   {
      last_bar_time = current_time[0];
      return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| Count positions with magic number                                |
//+------------------------------------------------------------------+
int CountPositions(int &direction)
{
   int count = 0;
   direction = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket))
      {
         if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
            PositionGetInteger(POSITION_MAGIC) == magic_number)
         {
            count++;
            if(direction == 0)
            {
               direction = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
            }
         }
      }
   }

   return count;
}

//+------------------------------------------------------------------+
//| Get time of last opened position                                 |
//+------------------------------------------------------------------+
datetime GetLastPositionTime()
{
   datetime latest_time = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket))
      {
         if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
            PositionGetInteger(POSITION_MAGIC) == magic_number)
         {
            datetime pos_time = (datetime)PositionGetInteger(POSITION_TIME);
            if(pos_time > latest_time)
               latest_time = pos_time;
         }
      }
   }

   return latest_time;
}

//+------------------------------------------------------------------+
//| Check MA crossover                                               |
//+------------------------------------------------------------------+
bool CheckMACrossover(int &signal)
{
   // Copy MA data
   if(CopyBuffer(handle_fast_ema, 0, 0, 3, fast_ema) <= 0) return false;
   if(CopyBuffer(handle_slow_sma, 0, 0, 3, slow_sma) <= 0) return false;

   // Check bullish crossover: EMA crosses above SMA
   if(fast_ema[2] < slow_sma[2] && fast_ema[1] > slow_sma[1])
   {
      signal = 1; // Bullish
      if(Print_Debug)
         Print("Bullish MA crossover detected");
      return true;
   }

   // Check bearish crossover: EMA crosses below SMA
   if(fast_ema[2] > slow_sma[2] && fast_ema[1] < slow_sma[1])
   {
      signal = -1; // Bearish
      if(Print_Debug)
         Print("Bearish MA crossover detected");
      return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| Check MA alignment for confirmation                              |
//+------------------------------------------------------------------+
bool CheckMAAlignment(int direction)
{
   // Copy MA data for current bar
   if(CopyBuffer(handle_fast_ema, 0, 0, 2, fast_ema) <= 0) return false;
   if(CopyBuffer(handle_slow_sma, 0, 0, 2, slow_sma) <= 0) return false;
   if(CopyBuffer(handle_double_sma, 0, 0, 2, double_sma) <= 0) return false;

   if(direction == 1) // Bullish: EMA(36) > SMA(195) > SMA(41)
   {
      if(fast_ema[1] > double_sma[1] && double_sma[1] > slow_sma[1])
      {
         if(Print_Debug)
            Print("Bullish MA alignment confirmed");
         return true;
      }
   }
   else if(direction == -1) // Bearish: EMA(36) < SMA(195) < SMA(41)
   {
      if(fast_ema[1] < double_sma[1] && double_sma[1] < slow_sma[1])
      {
         if(Print_Debug)
            Print("Bearish MA alignment confirmed");
         return true;
      }
   }

   return false;
}

//+------------------------------------------------------------------+
//| Check Stochastic filter                                          |
//+------------------------------------------------------------------+
bool CheckStochasticFilter(int direction)
{
   if(!Use_Stoch)
      return true;

   // Copy stochastic data for last 4 bars
   if(CopyBuffer(handle_stoch, 0, 0, 4, stoch_k) <= 0) return false;
   if(CopyBuffer(handle_stoch, 1, 0, 4, stoch_d) <= 0) return false;

   // Check within last 3 bars
   for(int i = 1; i <= 3; i++)
   {
      if(direction == 1) // Bullish: %K crossed above %D while both below 30
      {
         if(stoch_k[i+1] < stoch_d[i+1] && stoch_k[i] > stoch_d[i] &&
            stoch_k[i+1] < 30 && stoch_d[i+1] < 30)
         {
            if(Print_Debug)
               Print("Bullish Stochastic filter passed at bar ", i);
            return true;
         }
      }
      else if(direction == -1) // Bearish: %K crossed below %D while both above 70
      {
         if(stoch_k[i+1] > stoch_d[i+1] && stoch_k[i] < stoch_d[i] &&
            stoch_k[i+1] > 70 && stoch_d[i+1] > 70)
         {
            if(Print_Debug)
               Print("Bearish Stochastic filter passed at bar ", i);
            return true;
         }
      }
   }

   if(Print_Debug)
      Print("Stochastic filter NOT passed");

   return false;
}

//+------------------------------------------------------------------+
//| Process entry signals                                            |
//+------------------------------------------------------------------+
void ProcessEntrySignals()
{
   // Check if we already have positions
   int pos_direction = 0;
   int pos_count = CountPositions(pos_direction);

   if(pos_count > 0)
   {
      // Already have positions, don't look for new initial entries
      return;
   }

   // Step 1: Check for MA crossover
   int signal = 0;
   if(!crossover_detected)
   {
      if(CheckMACrossover(signal))
      {
         crossover_detected = true;
         crossover_direction = signal;
         aligned_bars_count = 0;

         if(Print_Debug)
            Print("Crossover detected, direction: ", crossover_direction);
      }
   }

   // Step 2: Count aligned bars after crossover
   if(crossover_detected)
   {
      if(CheckMAAlignment(crossover_direction))
      {
         aligned_bars_count++;

         if(Print_Debug)
            Print("Aligned bars count: ", aligned_bars_count);

         // Step 3: After 2 aligned bars, check Stochastic and enter
         if(aligned_bars_count >= Candles_Aligned_Before_Entry)
         {
            if(CheckStochasticFilter(crossover_direction))
            {
               // All conditions met, place order
               PlaceInitialOrder(crossover_direction);
            }
            else
            {
               if(Print_Debug)
                  Print("Stochastic filter failed, resetting crossover");
            }

            // Reset crossover detection
            crossover_detected = false;
            aligned_bars_count = 0;
         }
      }
      else
      {
         // Alignment broken, reset
         if(Print_Debug)
            Print("MA alignment broken, resetting crossover");

         crossover_detected = false;
         aligned_bars_count = 0;
      }
   }
}

//+------------------------------------------------------------------+
//| Place initial order                                              |
//+------------------------------------------------------------------+
void PlaceInitialOrder(int direction)
{
   double price, sl, tp;
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   // Normalize lot size
   double lot = NormalizeLot(Initial_Lot);

   if(direction == 1) // Buy
   {
      price = ask;
      sl = price - StopLoss_Pts * point;
      tp = price + TakeProfit_Pts * point;

      if(trade.Buy(lot, _Symbol, price, sl, tp, "EA_test_2 Initial Buy"))
      {
         last_position_time = TimeCurrent();
         if(Print_Debug)
            Print("BUY order placed: Lot=", lot, " Price=", price, " SL=", sl, " TP=", tp);
      }
      else
      {
         Print("Error placing BUY order: ", GetLastError());
      }
   }
   else if(direction == -1) // Sell
   {
      price = bid;
      sl = price + StopLoss_Pts * point;
      tp = price - TakeProfit_Pts * point;

      if(trade.Sell(lot, _Symbol, price, sl, tp, "EA_test_2 Initial Sell"))
      {
         last_position_time = TimeCurrent();
         if(Print_Debug)
            Print("SELL order placed: Lot=", lot, " Price=", price, " SL=", sl, " TP=", tp);
      }
      else
      {
         Print("Error placing SELL order: ", GetLastError());
      }
   }
}

//+------------------------------------------------------------------+
//| Process pyramiding                                               |
//+------------------------------------------------------------------+
void ProcessPyramiding()
{
   if(!Enable_Pyramid)
      return;

   // Step 1: Count existing positions
   int pos_direction = 0;
   int pos_count = CountPositions(pos_direction);

   if(pos_count == 0)
      return; // No positions to pyramid

   if(pos_count >= Max_Pyramid_Positions)
   {
      if(Print_Debug)
         Print("Max pyramid positions reached");
      return;
   }

   // Step 2: Check Ichimoku conditions on H2 timeframe
   if(CopyBuffer(handle_ichimoku, 0, 0, 2, ichi_tenkan) <= 0) return;
   if(CopyBuffer(handle_ichimoku, 1, 0, 2, ichi_kijun) <= 0) return;

   // Get current close on H2 timeframe
   double close_h2[];
   ArraySetAsSeries(close_h2, true);
   if(CopyClose(_Symbol, Ichimoku_Timeframe, 0, 2, close_h2) <= 0) return;

   bool ichimoku_signal = false;

   if(pos_direction == 1) // Long positions: Close > Kijun AND Close > Tenkan
   {
      if(close_h2[0] > ichi_kijun[0] && close_h2[0] > ichi_tenkan[0])
      {
         ichimoku_signal = true;
         if(Print_Debug)
            Print("Ichimoku bullish signal for pyramid");
      }
   }
   else if(pos_direction == -1) // Short positions: Close < Kijun AND Close < Tenkan
   {
      if(close_h2[0] < ichi_kijun[0] && close_h2[0] < ichi_tenkan[0])
      {
         ichimoku_signal = true;
         if(Print_Debug)
            Print("Ichimoku bearish signal for pyramid");
      }
   }

   if(!ichimoku_signal)
      return;

   // Step 3: Check ADX on current timeframe
   if(CopyBuffer(handle_adx, 0, 0, 2, adx_main) <= 0) return;

   if(adx_main[0] <= ADX_Threshold)
   {
      if(Print_Debug)
         Print("ADX too low for pyramid: ", adx_main[0], " <= ", ADX_Threshold);
      return;
   }

   if(Print_Debug)
      Print("ADX strong enough for pyramid: ", adx_main[0]);

   // Step 4: Check time spacing
   datetime last_pos_time = GetLastPositionTime();
   if(last_pos_time == 0)
      return;

   datetime current_time = TimeCurrent();
   int bars_since_last = (int)((current_time - last_pos_time) / PeriodSeconds(Ichimoku_Timeframe));

   if(bars_since_last < Candle_To_Check)
   {
      if(Print_Debug)
         Print("Not enough time since last position: ", bars_since_last, " < ", Candle_To_Check);
      return;
   }

   if(Print_Debug)
      Print("Time spacing OK: ", bars_since_last, " H2 bars since last position");

   // Step 5: Place pyramid order
   PlacePyramidOrder(pos_direction);
}

//+------------------------------------------------------------------+
//| Place pyramid order                                              |
//+------------------------------------------------------------------+
void PlacePyramidOrder(int direction)
{
   double price, sl, tp;
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   double lot = NormalizeLot(Initial_Lot);

   if(direction == 1) // Buy
   {
      price = ask;
      sl = price - StopLoss_Pts * point;
      tp = price + TakeProfit_Pts * point;

      if(trade.Buy(lot, _Symbol, price, sl, tp, "EA_test_2 Pyramid Buy"))
      {
         last_position_time = TimeCurrent();
         if(Print_Debug)
            Print("PYRAMID BUY order placed: Lot=", lot, " Price=", price);
      }
      else
      {
         Print("Error placing PYRAMID BUY order: ", GetLastError());
      }
   }
   else if(direction == -1) // Sell
   {
      price = bid;
      sl = price + StopLoss_Pts * point;
      tp = price - TakeProfit_Pts * point;

      if(trade.Sell(lot, _Symbol, price, sl, tp, "EA_test_2 Pyramid Sell"))
      {
         last_position_time = TimeCurrent();
         if(Print_Debug)
            Print("PYRAMID SELL order placed: Lot=", lot, " Price=", price);
      }
      else
      {
         Print("Error placing PYRAMID SELL order: ", GetLastError());
      }
   }
}

//+------------------------------------------------------------------+
//| Update trailing stops for all positions                          |
//+------------------------------------------------------------------+
void UpdateTrailingStops()
{
   if(!Use_TSL)
      return;

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket))
      {
         if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
            PositionGetInteger(POSITION_MAGIC) == magic_number)
         {
            double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
            double current_sl = PositionGetDouble(POSITION_SL);
            double current_tp = PositionGetDouble(POSITION_TP);

            ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

            if(pos_type == POSITION_TYPE_BUY)
            {
               // Calculate profit in points
               double profit_pts = (bid - open_price) / point;

               if(profit_pts >= TSL_Trigger)
               {
                  // Calculate new SL
                  double new_sl = bid - TSL_Step * point;

                  // Only move SL up (never down)
                  if(new_sl > current_sl)
                  {
                     if(trade.PositionModify(ticket, new_sl, current_tp))
                     {
                        if(Print_Debug)
                           Print("Trailing stop updated for BUY position #", ticket, " New SL: ", new_sl);
                     }
                     else
                     {
                        if(Print_Debug)
                           Print("Error updating trailing stop for #", ticket, ": ", GetLastError());
                     }
                  }
               }
            }
            else if(pos_type == POSITION_TYPE_SELL)
            {
               // Calculate profit in points
               double profit_pts = (open_price - ask) / point;

               if(profit_pts >= TSL_Trigger)
               {
                  // Calculate new SL
                  double new_sl = ask + TSL_Step * point;

                  // Only move SL down (never up)
                  if(new_sl < current_sl || current_sl == 0)
                  {
                     if(trade.PositionModify(ticket, new_sl, current_tp))
                     {
                        if(Print_Debug)
                           Print("Trailing stop updated for SELL position #", ticket, " New SL: ", new_sl);
                     }
                     else
                     {
                        if(Print_Debug)
                           Print("Error updating trailing stop for #", ticket, ": ", GetLastError());
                     }
                  }
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Normalize lot size                                               |
//+------------------------------------------------------------------+
double NormalizeLot(double lot)
{
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lot = MathMax(lot, min_lot);
   lot = MathMin(lot, max_lot);

   lot = MathFloor(lot / lot_step) * lot_step;

   return lot;
}
//+------------------------------------------------------------------+
