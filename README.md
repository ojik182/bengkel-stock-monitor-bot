# Bengkel Stock Monitor Bot

Telegram bot untuk monitoring stok sparepart bengkel. Data diambil dari Google Sheets.

## Prerequisites

- Python 3.10+
- Telegram Bot Token (dari [@BotFather](https://t.me/BotFather))
- Google Cloud Console project dengan Sheets API enabled
- Service Account credentials (JSON file)

## Setup

### 1. Install Dependencies

```bash
pip install python-telegram-bot google-auth google-api-python-client python-dotenv pandas
```

### 2. Buat Telegram Bot

1. Buka [@BotFather](https://t.me/BotFather) di Telegram
2. Ketik `/newbot`
3. Ikuti instruksi, simpan bot token-nya

### 3. Setup Google Cloud Console

1. Buka [console.cloud.google.com](https://console.cloud.google.com)
2. Buat project baru
3. Enable **Google Sheets API**
4. Buat **Service Account** (IAM & Admin → Service Accounts → Create)
5. Download JSON credentials
6. Share Google Spreadsheet kamu dengan email service account

### 4. Configure Environment

Salin `.env.example` ke `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
GOOGLE_SERVICE_ACCOUNT_KEY=path/to/your/credentials.json
```

### 5. Persiapan Google Sheets

Pastikan spreadsheet kamu punya 4 sheet:
- **Parts** — master data part
- **Locations** — daftar lokasi gudang
- **Inventory** — stok per lokasi
- **Transactions** — log transaksi

Struktur setiap sheet (row pertama = header):

**Parts:**
| part_id | part_number | name | category | unit_price | ranking |
|---------|------------|------|----------|-----------|---------|

**Locations:**
| location_id | branch_code | name | profit_center |

**Inventory:**
| id | location_id | part_id | qty_available | last_updated |

**Transactions:**
| id | date | location_id | part_id | type | qty | user | notes |

### 6. Jalankan Bot

```bash
python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Mulai bot, tampilkan welcome message |
| `/stats` | Overview stok (total SKU, nilai stok, low stock) |
| `/cari <part_number>` | Cari part by part number |
| `/stok <lokasi>` | Lihat stok di lokasi tertentu |
| `/alerts` | Daftar low stock items (< 5 units) |
| `/transaksi` | Log transaksi baru |
| `/help` | Tampilkan help |

## Example Usage

```
/start
/stats
/cari 06455K59A71
/stok Gudang Utama
/alerts
```

## Google Sheets Integration

Bot membaca data langsung dari Google Sheets setiap kali ada request.
Cache sederhana diterapkan untuk menghindari rate limiting.

Untuk import CSV dari sistem internal, gunakan Apps Script di folder `scripts/`.

## Project Structure

```
bengkel-stock-monitor-bot/
├── bot.py                 # Main bot file
├── sheets_client.py       # Google Sheets API client
├── models.py              # Data models
├── handlers.py            # Telegram command handlers
├── utils.py               # Utility functions
├── scripts/
│   └── gsheet-importer.gs # Apps Script untuk import CSV
├── .env.example
├── requirements.txt
└── README.md
```

## License

MIT
