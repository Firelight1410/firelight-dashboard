//+------------------------------------------------------------------+
//|                                                   EA_test_1.mq5 |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "EA_test_1"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//--- Input Parameters
// Debug
input bool Print_Debug = false;

// Entry - Moving Averages
input int Slow_SMA_Bias = 175;
input int Fast_EMA_Confirmation = 109;
input int Fast_SMA_DoubleCheck = 102;
input int Candles_Aligned_Before_Entry = 7;

// Entry - Stochastic Filter (Optional)
input bool Use_Stoch = false;
input int Stoch_K = 55;
input int Stoch_D = 19;
input int Stoch_Slowing = 9;

// Pyramiding (Ichimoku)
input bool Enable_Pyramid = true;
input int Max_Pyramid_Positions = 5;
input int ADX_Period = 24;
input int ADX_Threshold = 25;
input ENUM_TIMEFRAMES Ichimoku_Timeframe = PERIOD_M20;
input int Ichi_Tenkan = 54;
input int Ichi_Kijun = 10;
input int Ichi_Senkou = 454;
input int Candle_To_Check = 28;

// Risk & Exits
input double Initial_Lot = 0.01;
input int StopLoss_Pts = 2004;
input int TakeProfit_Pts = 3200;

// Trailing Stop
input bool Use_TSL = true;
input int TSL_Trigger = 1663;
input int TSL_Step = 485;

//--- Global Variables
int handle_SlowSMA;
int handle_FastEMA;
int handle_FastSMA;
int handle_Stoch;
int handle_ADX;
int handle_Ichimoku;

CTrade trade;

datetime lastBarTime = 0;
int alignedBarsCount = 0;
bool crossoverDetected = false;
int crossoverDirection = 0; // 1 = bullish, -1 = bearish, 0 = none
datetime lastPositionTime = 0;

const int MAGIC_NUMBER = 123456;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize indicator handles
   handle_SlowSMA = iMA(_Symbol, PERIOD_CURRENT, Slow_SMA_Bias, 0, MODE_SMA, PRICE_CLOSE);
   handle_FastEMA = iMA(_Symbol, PERIOD_CURRENT, Fast_EMA_Confirmation, 0, MODE_EMA, PRICE_CLOSE);
   handle_FastSMA = iMA(_Symbol, PERIOD_CURRENT, Fast_SMA_DoubleCheck, 0, MODE_SMA, PRICE_CLOSE);

   if(Use_Stoch)
   {
      handle_Stoch = iStochastic(_Symbol, PERIOD_CURRENT, Stoch_K, Stoch_D, Stoch_Slowing, MODE_SMA, STO_LOWHIGH);
   }

   if(Enable_Pyramid)
   {
      handle_ADX = iADX(_Symbol, PERIOD_CURRENT, ADX_Period);
      handle_Ichimoku = iIchimoku(_Symbol, Ichimoku_Timeframe, Ichi_Tenkan, Ichi_Kijun, Ichi_Senkou);
   }

   // Validate handles
   if(handle_SlowSMA == INVALID_HANDLE || handle_FastEMA == INVALID_HANDLE || handle_FastSMA == INVALID_HANDLE)
   {
      Print("Error creating MA indicators");
      return(INIT_FAILED);
   }

   if(Use_Stoch && handle_Stoch == INVALID_HANDLE)
   {
      Print("Error creating Stochastic indicator");
      return(INIT_FAILED);
   }

   if(Enable_Pyramid && (handle_ADX == INVALID_HANDLE || handle_Ichimoku == INVALID_HANDLE))
   {
      Print("Error creating ADX or Ichimoku indicator");
      return(INIT_FAILED);
   }

   trade.SetExpertMagicNumber(MAGIC_NUMBER);
   trade.SetDeviationInPoints(10);
   trade.SetTypeFilling(ORDER_FILLING_FOK);
   trade.SetAsyncMode(false);

   if(Print_Debug)
      Print("EA_test_1 initialized successfully");

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(handle_SlowSMA != INVALID_HANDLE) IndicatorRelease(handle_SlowSMA);
   if(handle_FastEMA != INVALID_HANDLE) IndicatorRelease(handle_FastEMA);
   if(handle_FastSMA != INVALID_HANDLE) IndicatorRelease(handle_FastSMA);
   if(handle_Stoch != INVALID_HANDLE) IndicatorRelease(handle_Stoch);
   if(handle_ADX != INVALID_HANDLE) IndicatorRelease(handle_ADX);
   if(handle_Ichimoku != INVALID_HANDLE) IndicatorRelease(handle_Ichimoku);

   if(Print_Debug)
      Print("EA_test_1 deinitialized");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check for new bar
   bool isNewBar = CheckNewBar();

   // Initial entry logic - only on new bar
   if(isNewBar)
   {
      CheckInitialEntry();
   }

   // Pyramiding logic - every tick
   if(Enable_Pyramid)
   {
      CheckPyramid();
   }

   // Trailing stop logic - every tick
   if(Use_TSL)
   {
      ManageTrailingStop();
   }
}

//+------------------------------------------------------------------+
//| Check for new bar                                                |
//+------------------------------------------------------------------+
bool CheckNewBar()
{
   datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);

   if(currentBarTime != lastBarTime)
   {
      lastBarTime = currentBarTime;
      return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| Check MA alignment for a specific bar                            |
//+------------------------------------------------------------------+
bool CheckMAAlignment(int bar, int direction)
{
   double slowSMA[], fastEMA[], fastSMA[];
   ArraySetAsSeries(slowSMA, true);
   ArraySetAsSeries(fastEMA, true);
   ArraySetAsSeries(fastSMA, true);

   if(CopyBuffer(handle_SlowSMA, 0, bar, 1, slowSMA) <= 0) return false;
   if(CopyBuffer(handle_FastEMA, 0, bar, 1, fastEMA) <= 0) return false;
   if(CopyBuffer(handle_FastSMA, 0, bar, 1, fastSMA) <= 0) return false;

   if(direction == 1) // Bullish
   {
      return (fastEMA[0] > fastSMA[0] && fastSMA[0] > slowSMA[0]);
   }
   else if(direction == -1) // Bearish
   {
      return (fastEMA[0] < fastSMA[0] && fastSMA[0] < slowSMA[0]);
   }

   return false;
}

//+------------------------------------------------------------------+
//| Detect MA crossover                                              |
//+------------------------------------------------------------------+
int DetectCrossover()
{
   double slowSMA[], fastEMA[];
   ArraySetAsSeries(slowSMA, true);
   ArraySetAsSeries(fastEMA, true);

   if(CopyBuffer(handle_SlowSMA, 0, 0, 2, slowSMA) <= 0) return 0;
   if(CopyBuffer(handle_FastEMA, 0, 0, 2, fastEMA) <= 0) return 0;

   // Bullish crossover
   if(fastEMA[1] < slowSMA[1] && fastEMA[0] > slowSMA[0])
   {
      if(Print_Debug)
         Print("Bullish crossover detected at bar 0");
      return 1;
   }

   // Bearish crossover
   if(fastEMA[1] > slowSMA[1] && fastEMA[0] < slowSMA[0])
   {
      if(Print_Debug)
         Print("Bearish crossover detected at bar 0");
      return -1;
   }

   return 0;
}

//+------------------------------------------------------------------+
//| Check stochastic filter                                          |
//+------------------------------------------------------------------+
bool CheckStochasticFilter(int direction)
{
   if(!Use_Stoch) return true; // Skip if not enabled

   double stochMain[], stochSignal[];
   ArraySetAsSeries(stochMain, true);
   ArraySetAsSeries(stochSignal, true);

   if(CopyBuffer(handle_Stoch, 0, 0, 4, stochMain) <= 0) return false;
   if(CopyBuffer(handle_Stoch, 1, 0, 4, stochSignal) <= 0) return false;

   // Check last 3 bars for crossover
   for(int i = 0; i < 3; i++)
   {
      if(direction == 1) // Bullish - K crosses above D while both below 30
      {
         if(stochMain[i+1] < stochSignal[i+1] && stochMain[i] > stochSignal[i])
         {
            if(stochMain[i+1] < 30 && stochSignal[i+1] < 30)
            {
               if(Print_Debug)
                  Print("Bullish stochastic filter passed");
               return true;
            }
         }
      }
      else if(direction == -1) // Bearish - K crosses below D while both above 70
      {
         if(stochMain[i+1] > stochSignal[i+1] && stochMain[i] < stochSignal[i])
         {
            if(stochMain[i+1] > 70 && stochSignal[i+1] > 70)
            {
               if(Print_Debug)
                  Print("Bearish stochastic filter passed");
               return true;
            }
         }
      }
   }

   if(Print_Debug)
      Print("Stochastic filter not passed");

   return false;
}

//+------------------------------------------------------------------+
//| Check initial entry conditions                                   |
//+------------------------------------------------------------------+
void CheckInitialEntry()
{
   // Don't enter if we already have positions
   if(CountPositions() > 0)
   {
      // Reset confirmation tracking
      crossoverDetected = false;
      alignedBarsCount = 0;
      crossoverDirection = 0;
      return;
   }

   // Step 1: Detect crossover (only if not already tracking)
   if(!crossoverDetected)
   {
      int crossover = DetectCrossover();
      if(crossover != 0)
      {
         crossoverDetected = true;
         crossoverDirection = crossover;
         alignedBarsCount = 0;

         if(Print_Debug)
            Print("Crossover detected, starting 7-bar confirmation. Direction: ", crossoverDirection == 1 ? "LONG" : "SHORT");
      }
   }

   // Step 2: Count aligned bars
   if(crossoverDetected)
   {
      // Check if current bar (bar 0, which is now closed) maintains alignment
      if(CheckMAAlignment(0, crossoverDirection))
      {
         alignedBarsCount++;

         if(Print_Debug)
            Print("Bar aligned. Count: ", alignedBarsCount, "/", Candles_Aligned_Before_Entry);

         // Step 3: Check if we have 7 aligned bars
         if(alignedBarsCount >= Candles_Aligned_Before_Entry)
         {
            // Check stochastic filter
            if(CheckStochasticFilter(crossoverDirection))
            {
               // Step 4: Place order
               PlaceInitialOrder(crossoverDirection);
            }

            // Reset tracking
            crossoverDetected = false;
            alignedBarsCount = 0;
            crossoverDirection = 0;
         }
      }
      else
      {
         // Alignment broken, reset
         if(Print_Debug)
            Print("MA alignment broken, resetting confirmation count");

         crossoverDetected = false;
         alignedBarsCount = 0;
         crossoverDirection = 0;
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

   // Validate lot size
   double lotMin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lotMax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double lot = Initial_Lot;

   if(lot < lotMin) lot = lotMin;
   if(lot > lotMax) lot = lotMax;
   lot = MathRound(lot / lotStep) * lotStep;

   if(direction == 1) // BUY
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl = price - StopLoss_Pts * point;
      tp = price + TakeProfit_Pts * point;

      if(trade.Buy(lot, _Symbol, price, sl, tp, "EA_test_1 Initial Long"))
      {
         lastPositionTime = TimeCurrent();
         if(Print_Debug)
            Print("BUY order placed: Lot=", lot, " Price=", price, " SL=", sl, " TP=", tp);
      }
      else
      {
         if(Print_Debug)
            Print("BUY order failed: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
      }
   }
   else if(direction == -1) // SELL
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl = price + StopLoss_Pts * point;
      tp = price - TakeProfit_Pts * point;

      if(trade.Sell(lot, _Symbol, price, sl, tp, "EA_test_1 Initial Short"))
      {
         lastPositionTime = TimeCurrent();
         if(Print_Debug)
            Print("SELL order placed: Lot=", lot, " Price=", price, " SL=", sl, " TP=", tp);
      }
      else
      {
         if(Print_Debug)
            Print("SELL order failed: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
      }
   }
}

//+------------------------------------------------------------------+
//| Count positions with magic number                                |
//+------------------------------------------------------------------+
int CountPositions()
{
   int count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
            PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
         {
            count++;
         }
      }
   }

   return count;
}

//+------------------------------------------------------------------+
//| Get last position time                                           |
//+------------------------------------------------------------------+
datetime GetLastPositionTime()
{
   datetime lastTime = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
            PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
         {
            datetime posTime = (datetime)PositionGetInteger(POSITION_TIME);
            if(posTime > lastTime)
               lastTime = posTime;
         }
      }
   }

   return lastTime;
}

//+------------------------------------------------------------------+
//| Get current position direction                                   |
//+------------------------------------------------------------------+
int GetPositionDirection()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
            PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
         {
            ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            return (type == POSITION_TYPE_BUY) ? 1 : -1;
         }
      }
   }

   return 0;
}

//+------------------------------------------------------------------+
//| Check pyramid conditions                                         |
//+------------------------------------------------------------------+
void CheckPyramid()
{
   // Step 1: Count existing positions
   int posCount = CountPositions();

   if(posCount == 0 || posCount >= Max_Pyramid_Positions)
      return;

   int currentDirection = GetPositionDirection();
   if(currentDirection == 0)
      return;

   // Step 2: Check Ichimoku conditions on M20
   double close[], tenkan[], kijun[];
   ArraySetAsSeries(close, true);
   ArraySetAsSeries(tenkan, true);
   ArraySetAsSeries(kijun, true);

   if(CopyClose(_Symbol, Ichimoku_Timeframe, 0, 1, close) <= 0)
      return;

   if(CopyBuffer(handle_Ichimoku, 0, 0, 1, tenkan) <= 0) // Tenkan-sen
      return;

   if(CopyBuffer(handle_Ichimoku, 1, 0, 1, kijun) <= 0) // Kijun-sen
      return;

   bool ichimokuOK = false;

   if(currentDirection == 1) // Long positions
   {
      ichimokuOK = (close[0] > kijun[0] && close[0] > tenkan[0]);
   }
   else if(currentDirection == -1) // Short positions
   {
      ichimokuOK = (close[0] < kijun[0] && close[0] < tenkan[0]);
   }

   if(!ichimokuOK)
      return;

   // Step 3: Check ADX
   double adxMain[];
   ArraySetAsSeries(adxMain, true);

   if(CopyBuffer(handle_ADX, 0, 0, 1, adxMain) <= 0)
      return;

   if(adxMain[0] <= ADX_Threshold)
   {
      if(Print_Debug)
         Print("Pyramid skipped: ADX too low (", adxMain[0], ")");
      return;
   }

   // Step 4: Check time spacing
   datetime lastPosTime = GetLastPositionTime();
   if(lastPosTime == 0)
      lastPosTime = lastPositionTime;

   datetime currentTime = TimeCurrent();
   int barsSinceLast = (int)((currentTime - lastPosTime) / PeriodSeconds(Ichimoku_Timeframe));

   if(barsSinceLast < Candle_To_Check)
   {
      if(Print_Debug)
         Print("Pyramid skipped: Too soon. Bars since last: ", barsSinceLast, "/", Candle_To_Check);
      return;
   }

   // Step 5: Place pyramid order
   PlacePyramidOrder(currentDirection);
}

//+------------------------------------------------------------------+
//| Place pyramid order                                              |
//+------------------------------------------------------------------+
void PlacePyramidOrder(int direction)
{
   double price, sl, tp;
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   // Validate lot size
   double lotMin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lotMax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double lot = Initial_Lot;

   if(lot < lotMin) lot = lotMin;
   if(lot > lotMax) lot = lotMax;
   lot = MathRound(lot / lotStep) * lotStep;

   if(direction == 1) // BUY
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl = price - StopLoss_Pts * point;
      tp = price + TakeProfit_Pts * point;

      if(trade.Buy(lot, _Symbol, price, sl, tp, "EA_test_1 Pyramid Long"))
      {
         lastPositionTime = TimeCurrent();
         if(Print_Debug)
            Print("Pyramid BUY order placed: Lot=", lot, " Price=", price);
      }
      else
      {
         if(Print_Debug)
            Print("Pyramid BUY failed: ", trade.ResultRetcode());
      }
   }
   else if(direction == -1) // SELL
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl = price + StopLoss_Pts * point;
      tp = price - TakeProfit_Pts * point;

      if(trade.Sell(lot, _Symbol, price, sl, tp, "EA_test_1 Pyramid Short"))
      {
         lastPositionTime = TimeCurrent();
         if(Print_Debug)
            Print("Pyramid SELL order placed: Lot=", lot, " Price=", price);
      }
      else
      {
         if(Print_Debug)
            Print("Pyramid SELL failed: ", trade.ResultRetcode());
      }
   }
}

//+------------------------------------------------------------------+
//| Manage trailing stop                                             |
//+------------------------------------------------------------------+
void ManageTrailingStop()
{
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
            PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
         {
            ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
            double currentSL = PositionGetDouble(POSITION_SL);
            double currentTP = PositionGetDouble(POSITION_TP);

            double profitPts = 0;
            double newSL = 0;
            bool shouldModify = false;

            if(type == POSITION_TYPE_BUY)
            {
               // Calculate profit in points
               profitPts = (bid - openPrice) / point;

               // Check if TSL should activate
               if(profitPts >= TSL_Trigger)
               {
                  newSL = bid - (TSL_Step * point);

                  // Only move SL up
                  if(newSL > currentSL)
                  {
                     shouldModify = true;
                  }
               }
            }
            else if(type == POSITION_TYPE_SELL)
            {
               // Calculate profit in points
               profitPts = (openPrice - ask) / point;

               // Check if TSL should activate
               if(profitPts >= TSL_Trigger)
               {
                  newSL = ask + (TSL_Step * point);

                  // Only move SL down
                  if(newSL < currentSL || currentSL == 0)
                  {
                     shouldModify = true;
                  }
               }
            }

            // Modify stop loss
            if(shouldModify)
            {
               if(trade.PositionModify(ticket, newSL, currentTP))
               {
                  if(Print_Debug)
                     Print("Trailing stop updated for ticket ", ticket, " New SL: ", newSL);
               }
               else
               {
                  if(Print_Debug)
                     Print("Failed to modify SL for ticket ", ticket, ": ", trade.ResultRetcode());
               }
            }
         }
      }
   }
}
//+------------------------------------------------------------------+
