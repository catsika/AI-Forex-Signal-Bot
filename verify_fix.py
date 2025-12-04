import unittest
from unittest.mock import patch, MagicMock
import asyncio
import notifier
from telegram_bot import TelegramTradeBot

class TestNotificationLogic(unittest.TestCase):
    
    @patch('notifier.requests.post')
    def test_notifier_success(self, mock_post):
        # Simulate success
        mock_post.return_value.status_code = 200
        result = notifier.send_telegram_alert("EURUSD", "BUY", 
                                            {'entry_min': 1.1, 'entry_max': 1.1, 'sl': 1.0, 'tp': 1.2, 'lot_size': 0.1, 'risk_amount': 50, 'potential_profit': 100}, 
                                            "Test reasoning")
        self.assertTrue(result, "Should return True on 200 OK")

    @patch('notifier.requests.post')
    def test_notifier_failure(self, mock_post):
        # Simulate failure
        mock_post.return_value.status_code = 500
        result = notifier.send_telegram_alert("EURUSD", "BUY", 
                                            {'entry_min': 1.1, 'entry_max': 1.1, 'sl': 1.0, 'tp': 1.2, 'lot_size': 0.1, 'risk_amount': 50, 'potential_profit': 100}, 
                                            "Test reasoning")
        self.assertFalse(result, "Should return False on 500 Error")

    async def async_test_telegram_bot(self):
        bot = TelegramTradeBot()
        bot.token = "TEST_TOKEN"
        bot.chat_id = "TEST_ID"
        
        # Mock Application.builder
        with patch('telegram_bot.Application.builder') as mock_builder:
            # Setup async context manager mock
            mock_app = MagicMock()
            mock_app.bot.send_message = MagicMock()
            
            # Make the build() return an async context manager
            mock_context = MagicMock()
            mock_context.__aenter__.return_value = mock_app
            mock_context.__aexit__.return_value = None
            
            # Make build() return the context manager
            mock_builder.return_value.token.return_value.build.return_value = mock_context
            
            # Make send_message awaitable
            future = asyncio.Future()
            future.set_result(True)
            mock_app.bot.send_message.return_value = future
            
            # Test Success
            result = await bot.send_signal({'symbol': 'EURUSD', 'direction': 'BUY', 'entry': 1.1, 'sl': 1.0, 'tp': 1.2})
            print(f"Async Bot Success Test: {result}")
            
            # Test Failure
            future_fail = asyncio.Future()
            future_fail.set_exception(Exception("Telegram Error"))
            mock_app.bot.send_message.return_value = future_fail
            
            result_fail = await bot.send_signal({'symbol': 'EURUSD', 'direction': 'BUY', 'entry': 1.1, 'sl': 1.0, 'tp': 1.2})
            print(f"Async Bot Failure Test: {result_fail}")

if __name__ == '__main__':
    # Run sync tests
    unittest.main(exit=False)
    
    # Run async test manually
    print("\nRunning Async Tests...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(TestNotificationLogic().async_test_telegram_bot())
    loop.close()
