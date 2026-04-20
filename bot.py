"""
Bengkel Stock Monitor - Telegram Bot
Main entry point
"""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from sheets_client import SheetsClient
from mock_sheets_client import MockSheetsClient
from handlers import BotHandlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run the bot"""
    # Load environment variables
    load_dotenv()

    # Get configuration from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    credentials_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY', 'credentials.json')

    # Validate required configuration
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment variables!")
        logger.error("Please create a .env file with your bot token.")
        return

    if not spreadsheet_id:
        logger.error("GOOGLE_SHEETS_SPREADSHEET_ID is not set!")
        return

    # Check if credentials file exists
    if not os.path.exists(credentials_path):
        logger.warning(f"Credentials file not found: {credentials_path}")
        logger.warning("Please download your service account JSON and save it as credentials.json")
        logger.warning("Using mock data mode for demonstration...")

    # Initialize Google Sheets client
    use_mock = not os.path.exists(credentials_path)

    if use_mock:
        logger.warning("Credentials file not found. Using MOCK data mode.")
        sheets_client = MockSheetsClient(
            spreadsheet_id=spreadsheet_id
        )
        logger.info("Google Sheets client initialized (MOCK mode)")
    else:
        try:
            sheets_client = SheetsClient(
                spreadsheet_id=spreadsheet_id,
                credentials_path=credentials_path
            )
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            logger.error("Falling back to MOCK data mode.")
            sheets_client = MockSheetsClient(spreadsheet_id=spreadsheet_id)

    # Initialize handlers
    handlers = BotHandlers(sheets_client)

    # Build application
    application = Application.builder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", handlers.cmd_start))
    application.add_handler(CommandHandler("help", handlers.cmd_help))
    application.add_handler(CommandHandler("stats", handlers.cmd_stats))
    application.add_handler(CommandHandler("cari", handlers.cmd_cari))
    application.add_handler(CommandHandler("stok", handlers.cmd_stok))
    application.add_handler(CommandHandler("alerts", handlers.cmd_alerts))
    application.add_handler(CommandHandler("transaksi", handlers.cmd_transaksi))

    # Add fallback message handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handlers.unknown_command
    ))

    # Log startup
    logger.info("=" * 50)
    logger.info("Bengkel Stock Monitor Bot Starting...")
    logger.info("=" * 50)
    logger.info(f"Spreadsheet ID: {spreadsheet_id}")
    logger.info(f"Credentials: {credentials_path}")
    logger.info("Commands: /start, /help, /stats, /cari, /stok, /alerts, /transaksi")
    logger.info("=" * 50)

    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
