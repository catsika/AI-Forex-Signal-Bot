"""
MetaTrader 5 Trade Executor
Connects to MT5 and executes trades from Telegram commands
"""
import MetaTrader5 as mt5
import logging
from config import RISK_PER_TRADE, ACCOUNT_SIZE

logger = logging.getLogger(__name__)

# MT5 Symbol mapping (yfinance -> MT5)
SYMBOL_MAP = {
    "EURUSD=X": "EURUSD",  # Adjust based on your broker's symbol
}

class MT5Executor:
    def __init__(self, login: int, password: str, server: str):
        self.login = login
        self.password = password
        self.server = server
        self.connected = False
    
    def connect(self) -> bool:
        """Initialize and connect to MT5"""
        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        authorized = mt5.login(
            login=self.login,
            password=self.password,
            server=self.server
        )
        
        if not authorized:
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False
        
        account_info = mt5.account_info()
        logger.info(f"✅ Connected to MT5: {account_info.name}")
        logger.info(f"   Balance: ${account_info.balance:,.2f}")
        logger.info(f"   Server: {account_info.server}")
        self.connected = True
        return True
    
    def disconnect(self):
        """Shutdown MT5 connection"""
        mt5.shutdown()
        self.connected = False
        logger.info("MT5 disconnected")
    
    def get_symbol_info(self, symbol: str):
        """Get symbol info and ensure it's available"""
        mt5_symbol = SYMBOL_MAP.get(symbol, symbol.replace("=X", ""))
        
        # Ensure symbol is selected
        if not mt5.symbol_select(mt5_symbol, True):
            logger.error(f"Failed to select symbol {mt5_symbol}")
            return None
        
        info = mt5.symbol_info(mt5_symbol)
        if info is None:
            logger.error(f"Symbol {mt5_symbol} not found")
            return None
        
        return info
    
    def calculate_lot_size(self, symbol: str, sl_pips: float) -> float:
        """Calculate lot size based on risk per trade"""
        info = self.get_symbol_info(symbol)
        if not info:
            return 0.01  # Default minimum
        
        mt5_symbol = SYMBOL_MAP.get(symbol, symbol.replace("=X", ""))
        
        # Get pip value
        # For forex pairs, 1 pip = 0.0001 (or 0.01 for JPY pairs)
        point = info.point
        pip_size = point * 10 if "JPY" not in mt5_symbol else point * 1
        
        # Calculate pip value per lot
        tick_value = info.trade_tick_value
        tick_size = info.trade_tick_size
        pip_value_per_lot = (pip_size / tick_size) * tick_value
        
        # Calculate lot size
        if sl_pips > 0 and pip_value_per_lot > 0:
            lot_size = RISK_PER_TRADE / (sl_pips * pip_value_per_lot)
        else:
            lot_size = 0.01
        
        # Round to broker's lot step
        lot_step = info.volume_step
        lot_size = round(lot_size / lot_step) * lot_step
        
        # Ensure within limits
        lot_size = max(info.volume_min, min(lot_size, info.volume_max))
        
        logger.info(f"Calculated lot size: {lot_size:.2f} for {sl_pips:.1f} pips SL")
        return lot_size
    
    def execute_trade(self, symbol: str, direction: str, entry: float, 
                      sl: float, tp: float) -> dict:
        """
        Execute a trade on MT5
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD=X")
            direction: "BUY" or "SELL"
            entry: Entry price (for market orders, this is indicative)
            sl: Stop loss price
            tp: Take profit price
        
        Returns:
            dict with success status and order details
        """
        if not self.connected:
            if not self.connect():
                return {"success": False, "error": "MT5 not connected"}
        
        mt5_symbol = SYMBOL_MAP.get(symbol, symbol.replace("=X", ""))
        info = self.get_symbol_info(symbol)
        
        if not info:
            return {"success": False, "error": f"Symbol {mt5_symbol} not available"}
        
        # Get current price
        tick = mt5.symbol_info_tick(mt5_symbol)
        if tick is None:
            return {"success": False, "error": "Failed to get current price"}
        
        # Determine order type and price
        if direction == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        
        # Calculate SL in pips for lot sizing
        sl_distance = abs(entry - sl)
        pip_size = info.point * 10 if "JPY" not in mt5_symbol else info.point
        sl_pips = sl_distance / pip_size
        
        # Calculate lot size
        lot_size = self.calculate_lot_size(symbol, sl_pips)
        
        # Prepare order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mt5_symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,  # Max slippage in points
            "magic": 123456,  # EA identifier
            "comment": "AI-Forex-Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result is None:
            return {"success": False, "error": f"Order failed: {mt5.last_error()}"}
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                "success": False, 
                "error": f"Order rejected: {result.comment}",
                "retcode": result.retcode
            }
        
        logger.info(f"✅ Trade executed: {direction} {lot_size} {mt5_symbol}")
        logger.info(f"   Order ID: {result.order}")
        logger.info(f"   Price: {result.price}")
        
        return {
            "success": True,
            "order_id": result.order,
            "symbol": mt5_symbol,
            "direction": direction,
            "lot_size": lot_size,
            "price": result.price,
            "sl": sl,
            "tp": tp
        }
    
    def close_trade(self, ticket: int) -> dict:
        """Close a specific trade by ticket number"""
        position = mt5.positions_get(ticket=ticket)
        
        if not position:
            return {"success": False, "error": "Position not found"}
        
        position = position[0]
        symbol = position.symbol
        
        # Determine close direction
        if position.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": position.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "AI-Forex-Bot Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"success": False, "error": result.comment}
        
        return {"success": True, "closed_ticket": ticket}
    
    def get_open_positions(self) -> list:
        """Get all open positions"""
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        return [{
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": "BUY" if p.type == 0 else "SELL",
            "volume": p.volume,
            "price_open": p.price_open,
            "sl": p.sl,
            "tp": p.tp,
            "profit": p.profit
        } for p in positions]
    
    def get_account_info(self) -> dict:
        """Get account information"""
        info = mt5.account_info()
        if info is None:
            return {}
        
        return {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "profit": info.profit,
            "leverage": info.leverage
        }


# Test connection
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    login = int(os.getenv("MT5_LOGIN", 0))
    password = os.getenv("MT5_PASSWORD", "")
    server = os.getenv("MT5_SERVER", "")
    
    if login and password and server:
        executor = MT5Executor(login, password, server)
        if executor.connect():
            print("\n📊 Account Info:")
            info = executor.get_account_info()
            for k, v in info.items():
                print(f"   {k}: {v}")
            
            print("\n📈 Open Positions:")
            positions = executor.get_open_positions()
            if positions:
                for p in positions:
                    print(f"   {p}")
            else:
                print("   No open positions")
            
            executor.disconnect()
    else:
        print("❌ MT5 credentials not set in .env")
        print("Add: MT5_LOGIN, MT5_PASSWORD, MT5_SERVER")
