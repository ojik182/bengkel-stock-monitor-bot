"""
Utility functions for formatting and helpers
"""

from typing import Dict, List
from models import Part, Location


def format_currency(value: float) -> str:
    """Format number as Indonesian Rupiah"""
    if value >= 1_000_000_000:
        return f"Rp {value / 1_000_000_000:.2f}M"
    elif value >= 1_000_000:
        return f"Rp {value / 1_000_000:.2f}jt"
    elif value >= 1_000:
        return f"Rp {value / 1_000:.2f}Rb"
    else:
        return f"Rp {value:,.0f}"


def format_number(value: float) -> str:
    """Format number with thousand separators"""
    return f"{value:,.0f}".replace(",", ".")


def format_stock_list(items: List[Dict], show_location: bool = True) -> str:
    """Format a list of stock items for display"""
    if not items:
        return "Tidak ada data."

    lines = []
    for item in items:
        part = item['part']
        qty = item['qty']
        value = item['value']

        qty_str = format_number(qty)
        value_str = format_currency(value)

        # Color indicator based on quantity
        if qty == 0:
            qty_display = f"🔴 {qty_str}"
        elif qty < 5:
            qty_display = f"🟡 {qty_str}"
        else:
            qty_display = f"🟢 {qty_str}"

        line = f"📦 *{part.part_number}*\n"
        line += f"   {part.name}\n"
        line += f"   Kategori: {part.category} | Qty: {qty_display} | Value: {value_str}"

        if show_location and 'location' in item:
            line += f"\n   📍 {item['location'].name}"

        lines.append(line)

    return "\n\n".join(lines)


def format_part_search(parts: List[Part], inventory_data: Dict = None) -> str:
    """Format part search results"""
    if not parts:
        return "Part tidak ditemukan."

    lines = []
    for part in parts:
        line = f"📦 *{part.part_number}*\n"
        line += f"   {part.name}\n"
        line += f"   Kategori: {part.category} | Harga: {format_currency(part.unit_price)} | Ranking: {part.ranking}"

        if inventory_data and part.part_id in inventory_data:
            inv = inventory_data[part.part_id]
            line += f"\n   Stok Total: {format_number(inv['total_qty'])}"

        lines.append(line)

    return "\n\n".join(lines)


def format_location_list(locations: List[Location]) -> str:
    """Format list of locations"""
    if not locations:
        return "Tidak ada lokasi."

    lines = [f"📍 *Daftar Lokasi:*\n"]
    for loc in locations:
        lines.append(f"• {loc.name} ({loc.location_id})")

    return "\n".join(lines)


def format_dashboard_stats(stats: 'DashboardStats', locations: List[Location]) -> str:
    """Format dashboard statistics"""
    total_value_str = format_currency(stats.total_value)

    message = f"""📊 *Dashboard Stok Bengkel*

━━━━━━━━━━━━━━━
🔢 Total SKU: *{format_number(stats.total_skus)}*
💰 Nilai Stok: *{total_value_str}*
📍 Lokasi: *{stats.location_count}*
━━━━━━━━━━━━━━━

⚠️ *Low Stock (< 5):* {stats.low_stock_count} items
🚫 *Out of Stock:* {stats.out_of_stock_count} items

━━━━━━━━━━━━━━━
📍 *Daftar Lokasi:*
"""

    for loc in locations:
        message += f"\n• {loc.name} (`{loc.location_id}`)"

    message += "\n\n━━━━━━━━━━━━━━━\n"
    message += "_Updated setiap 1 menit_"

    return message


def format_low_stock_alerts(items: List[Dict], threshold: int = 5) -> str:
    """Format low stock alerts"""
    if not items:
        return f"✅ Semua stok aman! Tidak ada item dengan qty < {threshold}"

    lines = [f"⚠️ *Low Stock Alerts*\n(dibawah {threshold} unit)\n"]

    for item in items[:20]:  # Limit to 20 items
        part = item['part']
        total_qty = item['total_qty']

        qty_emoji = "🔴" if total_qty == 0 else "🟡"

        lines.append(
            f"{qty_emoji} *{part.part_number}* - {part.name}\n"
            f"   Total: {format_number(total_qty)} | Kategori: {part.category}"
        )

    if len(items) > 20:
        lines.append(f"\n_...dan {len(items) - 20} item lainnya_")

    return "\n\n".join(lines)


def get_ranking_emoji(ranking: str) -> str:
    """Get emoji for ranking"""
    ranking_map = {
        'A': '🏆',
        'B': '🥈',
        'C': '🥉',
        'D': '📉',
        'E': '⬇️',
    }
    return ranking_map.get(ranking.upper(), '📋')


def get_category_emoji(category: str) -> str:
    """Get emoji for category"""
    category_map = {
        'OIL': '🛢️',
        'BRAKE': '🛑',
        'PACC': '🎨',
        'CDKGP': '⛓️',
        'ELECT': '⚡',
        'BATT': '🔋',
        'TIRE': '🛞',
        'EC': '🌬️',
        'BLDRV': '⚙️',
        'RBR': '🔧',
        'GST': '🔩',
        'AHM': '🏍️',
        'VALVE': '💨',
        'DISK': '💿',
        'BATT': '🔋',
        'SPLUR': '🔥',
        'TIRE1': '🛞',
    }
    return category_map.get(category.upper()[:6], '📦')
