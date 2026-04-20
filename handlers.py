"""
Telegram command handlers
"""

import logging
from typing import Dict

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from sheets_client import SheetsClient
from models import Transaction
from utils import (
    format_currency,
    format_number,
    format_dashboard_stats,
    format_low_stock_alerts,
    format_location_list,
    format_part_search,
    get_category_emoji,
    get_ranking_emoji,
)

logger = logging.getLogger(__name__)


class BotHandlers:
    def __init__(self, sheets_client: SheetsClient):
        self.sheets = sheets_client
        self._user_states: Dict[int, Dict] = {}  # user_id -> state

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_message = f"""👋 Halo *{user.first_name}*!

Selamat datang di *Bengkel Stock Monitor Bot* 🛠️

Bot ini membantu kamu monitor stok sparepart bengkel langsung dari Telegram.

━━━━━━━━━━━━━━━
📋 *Commands:*

🔍 `/cari <part_number>` — Cari part by nomor
📊 `/stats` — Lihat overview stok
📦 `/stok <lokasi>` — Lihat stok per gudang
⚠️ `/alerts` — Daftar low stock items
📋 `/help` — Bantuan

━━━━━━━━━━━━━━━

Mau mulai dari mana? 👇
"""
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """📋 *Bantuan Bot Bengkel Stock Monitor*

━━━━━━━━━━━━━━━
🛠️ *Commands:*

`/start` — Mulai bot
`/stats` — Overview stok lengkap
`/cari <part_number>` — Cari part tertentu
`/stok [lokasi]` — Lihat stok per gudang
`/alerts` — Items dengan stok rendah
`/help` — Help ini

━━━━━━━━━━━━━━━
💡 *Tips:*

• Ketik `/cari 06455K59A71` untuk cari part tertentu
• Ketik `/stok Utama` untuk lihat stok Gudang Utama
• Ketik `/alerts` untuk lihat items yang perlu di-restock

━━━━━━━━━━━━━━━
📞 *Butuh bantuan?*

Hubungi admin bot ini.
"""
        await update.message.reply_text(help_message, parse_mode='Markdown')

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show dashboard overview"""
        await update.message.reply_text("⏳ Fetching data...")

        try:
            stats = self.sheets.get_dashboard_stats()
            locations = self.sheets.get_all_locations()

            message = format_dashboard_stats(stats, locations)
            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await update.message.reply_text(
                "❌ Gagal mengambil data.\n"
                "Pastikan Google Sheets sudah di-share dengan service account."
            )

    async def cmd_cari(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cari <part_number> command"""
        if not context.args:
            await update.message.reply_text(
                "⚠️ Format: `/cari <part_number>`\n\n"
                "Contoh: `/cari 06455K59A71`"
            )
            return

        part_number = " ".join(context.args)
        await update.message.reply_text(f"🔍 Mencari `{part_number}`...", parse_mode='Markdown')

        try:
            parts = self.sheets.search_part(part_number)

            if not parts:
                await update.message.reply_text(
                    f"❌ Part `{part_number}` tidak ditemukan.\n"
                    "Coba gunakan part number yang berbeda."
                )
                return

            # Get inventory data for each part
            inventory = self.sheets.get_all_inventory()
            inventory_by_part = {}
            for inv in inventory:
                if inv.part_id not in inventory_by_part:
                    inventory_by_part[inv.part_id] = {'total_qty': 0, 'by_location': []}
                inventory_by_part[inv.part_id]['total_qty'] += inv.qty_available

            message = format_part_search(parts, inventory_by_part)
            message += f"\n\n_Ditemukan {len(parts)} part_"
            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error searching part: {e}")
            await update.message.reply_text("❌ Gagal mencari part. Silakan coba lagi.")

    async def cmd_stok(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stok [lokasi] command"""
        location_filter = " ".join(context.args) if context.args else None

        await update.message.reply_text("📦 Mengambil data stok...")

        try:
            locations = self.sheets.get_all_locations()

            if not location_filter:
                # Show all locations
                message = "📦 *Daftar Stok Per Lokasi*\n\n"

                for loc in locations:
                    stock_data = self.sheets.get_stock_by_location(location_id=loc.location_id)
                    if loc.location_id in stock_data:
                        items = stock_data[loc.location_id]['items']
                        total_qty = sum(item['qty'] for item in items)
                        total_value = sum(item['value'] for item in items)

                        message += f"📍 *{loc.name}*\n"
                        message += f"   Items: {len(items)} | Total Qty: {format_number(total_qty)} | Value: {format_currency(total_value)}\n\n"

                await update.message.reply_text(message, parse_mode='Markdown')

            else:
                # Filter by location name
                stock_data = self.sheets.get_stock_by_location(location_name=location_filter)

                if not stock_data:
                    loc_list = format_location_list(locations)
                    await update.message.reply_text(
                        f"❌ Lokasi '{location_filter}' tidak ditemukan.\n\n"
                        f"📍 Lokasi yang tersedia:\n{loc_list}",
                        parse_mode='Markdown'
                    )
                    return

                message = f"📦 *Stok untuk '{location_filter}'*\n\n"

                for loc_id, data in stock_data.items():
                    items = data['items']
                    loc = data['location']

                    total_qty = sum(item['qty'] for item in items)
                    total_value = sum(item['value'] for item in items)

                    message += f"📍 *{loc.name}*\n"
                    message += f"   Items: {len(items)} | Total Qty: {format_number(total_qty)} | Value: {format_currency(total_value)}\n\n"

                    # Show top 10 items by quantity
                    sorted_items = sorted(items, key=lambda x: x['qty'], reverse=True)[:10]

                    for item in sorted_items:
                        part = item['part']
                        cat_emoji = get_category_emoji(part.category)
                        rank_emoji = get_ranking_emoji(part.ranking)

                        message += f"{cat_emoji} {part.part_number} — {part.name[:30]}\n"
                        message += f"   Qty: {format_number(item['qty'])} | Value: {format_currency(item['value'])} {rank_emoji}\n"

                    message += "\n"

                await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error getting stock: {e}")
            await update.message.reply_text("❌ Gagal mengambil data stok. Silakan coba lagi.")

    async def cmd_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command"""
        threshold = 5  # Default threshold
        if context.args:
            try:
                threshold = int(context.args[0])
            except ValueError:
                pass

        await update.message.reply_text(f"⚠️ Mengecek low stock items...")

        try:
            low_stock = self.sheets.get_low_stock_items(threshold=threshold)
            message = format_low_stock_alerts(low_stock, threshold)
            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            await update.message.reply_text("❌ Gagal mengambil data alerts. Silakan coba lagi.")

    async def cmd_transaksi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /transaksi command - show recent transactions"""
        await update.message.reply_text("📋 Mengambil data transaksi terakhir...")

        try:
            transactions = self.sheets.get_transactions(limit=10)
            locations = self.sheets.get_all_locations()
            parts = self.sheets.get_all_parts()

            location_map = {loc.location_id: loc.name for loc in locations}
            part_map = {p.part_id: p for p in parts}

            if not transactions:
                await update.message.reply_text("❌ Belum ada transaksi.")
                return

            message = "📋 *10 Transaksi Terakhir*\n\n"

            for txn in transactions[:10]:
                loc_name = location_map.get(txn.location_id, txn.location_id)
                part = part_map.get(txn.part_id)

                type_emoji = "🟢" if txn.type == "IN" else "🔴"
                type_text = "MASUK" if txn.type == "IN" else "KELUAR"

                message += f"{type_emoji} *{type_text}* — {txn.date[:10]}\n"
                message += f"   Part: {part.part_number if part else 'Unknown'}\n"
                message += f"   Lokasi: {loc_name} | Qty: {txn.qty} | User: {txn.user}\n"
                if txn.notes:
                    message += f"   Notes: {txn.notes}\n"
                message += "\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            await update.message.reply_text("❌ Gagal mengambil data transaksi.")

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands"""
        await update.message.reply_text(
            "❓ Command tidak dikenal.\n\n"
            "Ketik `/help` untuk melihat daftar command yang tersedia.",
            parse_mode='Markdown'
        )
