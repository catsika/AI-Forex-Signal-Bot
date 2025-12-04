"""
Telegram Bot Handler with Interactive Buttons
Receives button clicks and executes trades on MT5
"""
import os
import json
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Store pending signals for execution
pending_signals = {}

class TelegramTradeBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.mt5_executor = None
        self.app = None
        
    def set_mt5_executor(self, executor):
        """Set the MT5 executor instance"""
        self.mt5_executor = executor
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "🤖 *AI Forex Trading Bot*\n\n"
            "I'll send you trading signals with BUY/SELL buttons.\n"
            "Tap a button to execute the trade on MT5!\n\n"
            "Commands:\n"
            "/status - Account status\n"
            "/positions - Open positions\n"
            "/close [ticket] - Close a position",
            parse_mode='Markdown'
        )
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self.mt5_executor:
            await update.message.reply_text("❌ MT5 not connected")
            return
        
        info = self.mt5_executor.get_account_info()
        if not info:
            await update.message.reply_text("❌ Could not get account info")
            return
        
        msg = (
            "📊 *Account Status*\n\n"
            f"💰 Balance: ${info['balance']:,.2f}\n"
            f"📈 Equity: ${info['equity']:,.2f}\n"
            f"💵 Profit: ${info['profit']:+,.2f}\n"
            f"🔒 Margin: ${info['margin']:,.2f}\n"
            f"💳 Free Margin: ${info['free_margin']:,.2f}\n"
            f"⚡ Leverage: 1:{info['leverage']}"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        if not self.mt5_executor:
            await update.message.reply_text("❌ MT5 not connected")
            return
        
        positions = self.mt5_executor.get_open_positions()
        
        if not positions:
            await update.message.reply_text("📭 No open positions")
            return
        
        msg = "📈 *Open Positions*\n\n"
        for p in positions:
            emoji = "🟢" if p['type'] == 'BUY' else "🔴"
            profit_emoji = "✅" if p['profit'] >= 0 else "❌"
            msg += (
                f"{emoji} *{p['symbol']}* {p['type']}\n"
                f"   Ticket: `{p['ticket']}`\n"
                f"   Volume: {p['volume']}\n"
                f"   Entry: {p['price_open']:.5f}\n"
                f"   SL: {p['sl']:.5f} | TP: {p['tp']:.5f}\n"
                f"   {profit_emoji} P/L: ${p['profit']:+.2f}\n\n"
            )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def close_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /close command"""
        if not self.mt5_executor:
            await update.message.reply_text("❌ MT5 not connected")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /close <ticket_number>")
            return
        
        try:
            ticket = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid ticket number")
            return
        
        result = self.mt5_executor.close_trade(ticket)
        
        if result['success']:
            await update.message.reply_text(f"✅ Position {ticket} closed!")
        else:
            await update.message.reply_text(f"❌ Failed: {result['error']}")
    
    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks for trade execution"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("execute_"):
            # Extract signal ID
            signal_id = data.replace("execute_", "")
            
            if signal_id not in pending_signals:
                await query.edit_message_text(
                    query.message.text + "\n\n❌ Signal expired or already executed"
                )
                return
            
            signal = pending_signals[signal_id]
            
            if not self.mt5_executor:
                await query.edit_message_text(
                    query.message.text + "\n\n❌ MT5 not connected"
                )
                return
            
            # Execute the trade
            result = self.mt5_executor.execute_trade(
                symbol=signal['symbol'],
                direction=signal['direction'],
                entry=signal['entry'],
                sl=signal['sl'],
                tp=signal['tp']
            )
            
            if result['success']:
                success_msg = (
                    f"\n\n✅ *TRADE EXECUTED*\n"
                    f"Order ID: `{result['order_id']}`\n"
                    f"Lot Size: {result['lot_size']}\n"
                    f"Price: {result['price']:.5f}"
                )
                await query.edit_message_text(
                    query.message.text + success_msg,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    query.message.text + f"\n\n❌ Failed: {result['error']}"
                )
            
            # Remove from pending
            del pending_signals[signal_id]
        
        elif data == "skip":
            await query.edit_message_text(
                query.message.text + "\n\n⏭️ Signal skipped"
            )
    
    def create_signal_message(self, signal: dict) -> tuple:
        """Create a signal message with buttons"""
        import uuid
        signal_id = str(uuid.uuid4())[:8]
        
        # Store signal for later execution
        pending_signals[signal_id] = signal
        
        direction_emoji = "🟢" if signal['direction'] == "BUY" else "🔴"
        
        msg = (
            f"{direction_emoji} *{signal['direction']} SIGNAL*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📍 *{signal['symbol']}*\n\n"
            f"💰 Entry: `{signal['entry']:.5f}`\n"
            f"🛑 Stop Loss: `{signal['sl']:.5f}`\n"
            f"🎯 Take Profit: `{signal['tp']:.5f}`\n\n"
            f"📊 Risk: ${signal.get('risk', 100)}\n"
            f"📈 R:R Ratio: 1:2.5\n\n"
        )
        
        if signal.get('ai_analysis'):
            msg += f"🤖 *AI Analysis:*\n{signal['ai_analysis']}\n\n"
        
        msg += "⚡ *Tap below to execute:*"
        
        # Create buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    f"✅ Execute {signal['direction']}", 
                    callback_data=f"execute_{signal_id}"
                )
            ],
            [
                InlineKeyboardButton("⏭️ Skip", callback_data="skip")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return msg, reply_markup
    
    async def send_signal(self, signal: dict):
        """Send a trading signal with interactive buttons"""
        msg, markup = self.create_signal_message(signal)
        
        try:
            async with Application.builder().token(self.token).build() as app:
                await app.bot.send_message(
                    chat_id=self.chat_id,
                    text=msg,
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram signal: {e}")
            return False
    
    def run(self):
        """Run the Telegram bot"""
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("positions", self.positions))
        self.app.add_handler(CommandHandler("close", self.close_position))
        self.app.add_handler(CallbackQueryHandler(self.handle_button))
        
        logger.info("🤖 Telegram bot started - listening for commands...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = TelegramTradeBot()
    bot.run()
