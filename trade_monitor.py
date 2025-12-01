"""
Trade Monitor - Tracks active trades and trailing stops

This module manages trade state and logs when stops are moved.
Critical for monitoring the trailing stop edge.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from notifier import send_trailing_stop_alert, send_trade_closed_alert

logger = logging.getLogger(__name__)

# Trade state file
TRADE_STATE_FILE = Path(__file__).parent / "active_trades.json"


class TradeMonitor:
    """
    Monitors active trades and manages trailing stops.
    
    The trailing stop is CRITICAL to the strategy's edge:
    - When price moves 1.5x risk in our favor, SL moves to breakeven + 20%
    - This turns many would-be losses into small wins or breakeven
    """
    
    def __init__(self):
        self.active_trades = {}
        self.trade_history = []
        self.load_state()
    
    def load_state(self):
        """Load active trades from file (for bot restarts)"""
        try:
            if TRADE_STATE_FILE.exists():
                with open(TRADE_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.active_trades = data.get('active_trades', {})
                    self.trade_history = data.get('history', [])
                    logger.info(f"Loaded {len(self.active_trades)} active trades")
        except Exception as e:
            logger.error(f"Error loading trade state: {e}")
            self.active_trades = {}
    
    def save_state(self):
        """Save active trades to file"""
        try:
            with open(TRADE_STATE_FILE, 'w') as f:
                json.dump({
                    'active_trades': self.active_trades,
                    'history': self.trade_history[-100:]  # Keep last 100
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving trade state: {e}")
    
    def open_trade(self, symbol: str, signal: str, entry_price: float, 
                   sl_price: float, tp_price: float, lot_size: float):
        """
        Record a new trade opening.
        """
        trade_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        risk_distance = abs(entry_price - sl_price)
        breakeven_target = entry_price + (1.5 * risk_distance) if signal == "BUY" else entry_price - (1.5 * risk_distance)
        
        trade = {
            'id': trade_id,
            'symbol': symbol,
            'type': signal,
            'entry_price': entry_price,
            'entry_time': datetime.now().isoformat(),
            'original_sl': sl_price,
            'current_sl': sl_price,
            'tp': tp_price,
            'lot_size': lot_size,
            'risk_distance': risk_distance,
            'breakeven_target': breakeven_target,
            'sl_moved_to_be': False,
            'highest_price': entry_price if signal == "BUY" else None,
            'lowest_price': entry_price if signal == "SELL" else None,
            'sl_updates': []
        }
        
        self.active_trades[trade_id] = trade
        self.save_state()
        
        logger.info(f"""
╔══════════════════════════════════════════════════════════════╗
║  📈 NEW TRADE OPENED                                         ║
╠══════════════════════════════════════════════════════════════╣
║  Symbol:     {symbol}
║  Direction:  {signal}
║  Entry:      {entry_price:.5f}
║  Stop Loss:  {sl_price:.5f}
║  Take Profit: {tp_price:.5f}
║  Lot Size:   {lot_size}
║  
║  ⚡ TRAILING STOP INFO:
║  Risk Distance:     {risk_distance:.5f}
║  Breakeven Target:  {breakeven_target:.5f}
║  (SL will move to BE+20% when price hits target)
╚══════════════════════════════════════════════════════════════╝
        """)
        
        return trade_id
    
    def update_price(self, symbol: str, current_high: float, current_low: float, current_close: float):
        """
        Update trade with current price and check for trailing stop adjustment.
        Call this on each new candle.
        """
        for trade_id, trade in list(self.active_trades.items()):
            if trade['symbol'] != symbol:
                continue
            
            entry_price = trade['entry_price']
            risk_dist = trade['risk_distance']
            
            if trade['type'] == 'BUY':
                # Track highest price
                if current_high > (trade['highest_price'] or entry_price):
                    trade['highest_price'] = current_high
                
                # Check for breakeven move
                if current_high >= trade['breakeven_target'] and not trade['sl_moved_to_be']:
                    new_sl = entry_price + (0.2 * risk_dist)
                    old_sl = trade['current_sl']
                    
                    if new_sl > old_sl:
                        trade['current_sl'] = new_sl
                        trade['sl_moved_to_be'] = True
                        trade['sl_updates'].append({
                            'time': datetime.now().isoformat(),
                            'old_sl': old_sl,
                            'new_sl': new_sl,
                            'reason': 'Breakeven move (1.5x risk reached)'
                        })
                        
                        logger.info(f"""
╔══════════════════════════════════════════════════════════════╗
║  🔄 TRAILING STOP ACTIVATED - {trade_id}                     
╠══════════════════════════════════════════════════════════════╣
║  Price hit breakeven target: {trade['breakeven_target']:.5f}
║  
║  ✅ STOP LOSS MOVED:
║     From: {old_sl:.5f} (original)
║     To:   {new_sl:.5f} (breakeven + 20% profit locked)
║  
║  💰 Trade is now RISK-FREE!
╚══════════════════════════════════════════════════════════════╝
                        """)
                        
                        # 🔔 SEND TELEGRAM ALERT
                        send_trailing_stop_alert(
                            symbol=symbol,
                            trade_type=trade['type'],
                            old_sl=old_sl,
                            new_sl=new_sl,
                            entry_price=entry_price,
                            current_price=current_close
                        )
                        
                        self.save_state()
                
                # Check for stop hit
                if current_low <= trade['current_sl']:
                    self._close_trade(trade_id, trade['current_sl'], 'SL_HIT')
                    
                # Check for TP hit
                elif current_high >= trade['tp']:
                    self._close_trade(trade_id, trade['tp'], 'TP_HIT')
                    
            elif trade['type'] == 'SELL':
                # Track lowest price
                if current_low < (trade['lowest_price'] or entry_price):
                    trade['lowest_price'] = current_low
                
                # Check for breakeven move
                if current_low <= trade['breakeven_target'] and not trade['sl_moved_to_be']:
                    new_sl = entry_price - (0.2 * risk_dist)
                    old_sl = trade['current_sl']
                    
                    if new_sl < old_sl:
                        trade['current_sl'] = new_sl
                        trade['sl_moved_to_be'] = True
                        trade['sl_updates'].append({
                            'time': datetime.now().isoformat(),
                            'old_sl': old_sl,
                            'new_sl': new_sl,
                            'reason': 'Breakeven move (1.5x risk reached)'
                        })
                        
                        logger.info(f"""
╔══════════════════════════════════════════════════════════════╗
║  🔄 TRAILING STOP ACTIVATED - {trade_id}                     
╠══════════════════════════════════════════════════════════════╣
║  Price hit breakeven target: {trade['breakeven_target']:.5f}
║  
║  ✅ STOP LOSS MOVED:
║     From: {old_sl:.5f} (original)
║     To:   {new_sl:.5f} (breakeven + 20% profit locked)
║  
║  💰 Trade is now RISK-FREE!
╚══════════════════════════════════════════════════════════════╝
                        """)
                        
                        # 🔔 SEND TELEGRAM ALERT
                        send_trailing_stop_alert(
                            symbol=symbol,
                            trade_type=trade['type'],
                            old_sl=old_sl,
                            new_sl=new_sl,
                            entry_price=entry_price,
                            current_price=current_close
                        )
                        
                        self.save_state()
                
                # Check for stop hit
                if current_high >= trade['current_sl']:
                    self._close_trade(trade_id, trade['current_sl'], 'SL_HIT')
                    
                # Check for TP hit
                elif current_low <= trade['tp']:
                    self._close_trade(trade_id, trade['tp'], 'TP_HIT')
    
    def _close_trade(self, trade_id: str, exit_price: float, reason: str):
        """Close a trade and log the result"""
        trade = self.active_trades.get(trade_id)
        if not trade:
            return
        
        entry_price = trade['entry_price']
        risk_dist = trade['risk_distance']
        
        if trade['type'] == 'BUY':
            pnl_ratio = (exit_price - entry_price) / risk_dist
        else:
            pnl_ratio = (entry_price - exit_price) / risk_dist
        
        pnl_dollars = pnl_ratio * 50  # $50 risk per trade
        result = 'WIN' if pnl_dollars > 0 else ('BREAKEVEN' if abs(pnl_dollars) < 5 else 'LOSS')
        
        trade['exit_price'] = exit_price
        trade['exit_time'] = datetime.now().isoformat()
        trade['pnl'] = pnl_dollars
        trade['result'] = result
        trade['exit_reason'] = reason
        
        # Log the close
        emoji = '✅' if result == 'WIN' else ('⚖️' if result == 'BREAKEVEN' else '❌')
        be_note = " (SL was at breakeven)" if trade['sl_moved_to_be'] else ""
        
        logger.info(f"""
╔══════════════════════════════════════════════════════════════╗
║  {emoji} TRADE CLOSED - {result}{be_note}
╠══════════════════════════════════════════════════════════════╣
║  Symbol:     {trade['symbol']}
║  Direction:  {trade['type']}
║  Entry:      {entry_price:.5f}
║  Exit:       {exit_price:.5f}
║  
║  P/L:        ${pnl_dollars:+.2f}
║  Reason:     {reason}
║  
║  Trailing Stop Used: {'YES ✓' if trade['sl_moved_to_be'] else 'NO'}
╚══════════════════════════════════════════════════════════════╝
        """)
        
        # 🔔 SEND TELEGRAM ALERT
        send_trade_closed_alert(
            symbol=trade['symbol'],
            trade_type=trade['type'],
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl_dollars,
            reason=reason
        )
        
        # Move to history
        self.trade_history.append(trade)
        del self.active_trades[trade_id]
        self.save_state()
    
    def get_stats(self):
        """Get trailing stop statistics from history"""
        if not self.trade_history:
            return "No trade history yet"
        
        total = len(self.trade_history)
        be_used = len([t for t in self.trade_history if t.get('sl_moved_to_be')])
        be_saved = len([t for t in self.trade_history if t.get('sl_moved_to_be') and t['pnl'] >= 0])
        
        wins = len([t for t in self.trade_history if t['result'] == 'WIN'])
        losses = len([t for t in self.trade_history if t['result'] == 'LOSS'])
        
        return f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 TRAILING STOP STATISTICS                                 ║
╠══════════════════════════════════════════════════════════════╣
║  Total Trades:         {total}
║  Wins:                 {wins}
║  Losses:               {losses}
║  Win Rate:             {wins/total*100:.1f}%
║  
║  Trailing Stop Usage:
║  - Times Activated:    {be_used} ({be_used/total*100:.1f}% of trades)
║  - Losses Saved:       {be_saved} (would have been losses)
║  
║  ⚡ Trailing stop is saving {be_saved/total*100:.1f}% of trades
╚══════════════════════════════════════════════════════════════╝
        """


# Global instance
trade_monitor = TradeMonitor()
