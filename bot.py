"""
Bengkel Stock Monitor - Telegram Bot
Main entry point
"""

import os
import logging
import json
import tempfile

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
    credentials_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY')

    # Validate required configuration
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment variables!")
        return

    if not spreadsheet_id:
        logger.error("GOOGLE_SHEETS_SPREADSHEET_ID is not set!")
        return

    # Determine credentials approach
    credentials_path = None
    
    if credentials_json and credentials_json.startswith('{'):
        # JSON string content - write to temp file for google-auth
        try:
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(json.loads(credentials_json), temp_file)
            temp_file.close()
            credentials_path = temp_file.name
            logger.info("Using credentials from GOOGLE_SERVICE_ACCOUNT_KEY env var")
        except Exception as e:
            logger.error(f"Failed to parse credentials JSON: {e}")
            credentials_path = None

    elif credentials_json and os.path.exists(credentials_json):
        # It's a file path
        credentials_path = credentials_json
        logger.info(f"Using credentials from file: {credentials_path}")
    
    else:
        logger.warning("No valid credentials found. Using MOCK data mode.")

    # Initialize Google Sheets client
    if credentials_path:
        try:
            sheets_client = SheetsClient(
                spreadsheet_id=spreadsheet_id,
                credentials_path=credentials_path
            )
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            logger.warning("Falling back to MOCK data mode.")
            sheets_client = MockSheetsClient(spreadsheet_id=spreadsheet_id)
    else:
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
    logger.info(f"Credentials: {'file' if credentials_path else 'mock'}")
    logger.info("Commands: /start, /help, /stats, /cari, /stok, /alerts, /transaksi")
    logger.info("=" * 50)

    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == '__main__':
    main()
