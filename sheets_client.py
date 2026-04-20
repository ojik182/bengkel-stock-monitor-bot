"""
Google Sheets API client for Bengkel Stock Monitor
Reads directly from "Stock Sparepart" sheet with flat structure
"""

import os
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Column indices (0-based in our parsed data, 1-based in Sheets)
COL_KODE_PRODUCT = 5  # F
COL_NAMA_BARANG = 6    # G
COL_KATEGORI = 4       # E
COL_LOKASI = 8         # I
COL_HARGA = 16         # Q
COL_QTY_AVAILABLE = 17  # R
COL_AMOUNT = 18        # S
COL_RANGKING = 21      # V

# Location mapping
LOCATION_MAPPING = {
    'Physical Locations / DXK / Stock': 'DXK-UTAMA',
    'Physical Locations / DXK / Stock / DXK-POSSV02 POS Service Sandai': 'DXK-SANDAI'
}


@dataclass
class Part:
    part_id: str
    part_number: str
    name: str
    category: str
    unit_price: float
    ranking: str


@dataclass
class Location:
    location_id: str
    branch_code: str
    name: str
    profit_center: str


@dataclass
class InventoryItem:
    id: str
    location_id: str
    part_id: str
    qty_available: float
    last_updated: str


@dataclass
class DashboardStats:
    total_skus: int
    total_value: float
    low_stock_count: int
    out_of_stock_count: int
    location_count: int


class SheetsClient:
    def __init__(self, spreadsheet_id: str, credentials_path: str = None):
        self.spreadsheet_id = spreadsheet_id
        self.logger = logging.getLogger(__name__)
        self._cache = {}
        self._cache_timeout = 60  # seconds
        self._last_fetch = None

        if credentials_path and os.path.exists(credentials_path):
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=SCOPES
            )
        else:
            # Try to get from env variable
            key_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY')
            if key_json:
                import json
                from google.oauth2.service_account import Credentials
                info = json.loads(key_json)
                self.credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
            else:
                self.logger.warning("No credentials found, using mock data")
                self.credentials = None

    def _parse_indonesian_number(self, value) -> float:
        """Parse Indonesian number format: 123.456,78 -> 123456.78"""
        if not value:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        
        # Remove spaces
        value = str(value).strip()
        
        # Handle empty
        if not value or value == '-' or value == '':
            return 0.0
        
        # Remove thousand separators (dots) and replace decimal comma with dot
        # First, check if it has decimal comma
        has_decimal = ',' in value and '.' in value
        if has_decimal:
            # Format: 123.456.789,00 (Indonesian)
            value = value.replace('.', '').replace(',', '.')
        elif ',' in value and value.count(',') == 1:
            # Format: 1234,56 (might be decimal)
            value = value.replace(',', '.')
        else:
            # Format: 123.456 (thousand separators only)
            value = value.replace('.', '')
        
        try:
            return float(value)
        except:
            return 0.0

    def _get_all_rows(self, force_refresh: bool = False) -> List[List]:
        """Fetch all rows from Stock Sparepart sheet"""
        import time
        
        # Check cache
        if not force_refresh and self._cache.get('rows') and self._last_fetch:
            if time.time() - self._last_fetch < self._cache_timeout:
                return self._cache['rows']
        
        if not self.credentials:
            return []
        
        try:
            service = build('sheets', 'v4', credentials=self.credentials)
            
            # Read from "Stock Sparepart" sheet
            result = service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="'Stock Sparepart'!A:V"  # Columns A to V
            ).execute()
            
            rows = result.get('values', [])
            self._cache['rows'] = rows
            self._last_fetch = time.time()
            
            self.logger.info(f"Fetched {len(rows)} rows from Stock Sparepart")
            return rows
            
        except Exception as e:
            self.logger.error(f"Error fetching data: {e}")
            return []

    def get_all_parts(self, force_refresh: bool = False) -> List[Part]:
        """Extract unique parts from the flat data"""
        rows = self._get_all_rows(force_refresh)
        
        if not rows:
            return []
        
        # Skip header row (row 0) and empty rows
        parts_map = {}
        
        for row in rows[3:]:  # Start from row 4 (index 3) to skip headers
            if len(row) <= COL_KODE_PRODUCT:
                continue
            
            part_number = row[COL_KODE_PRODUCT] if COL_KODE_PRODUCT < len(row) else ''
            if not part_number:
                continue
            
            # Deduplicate by part_number
            if part_number not in parts_map:
                name = row[COL_NAMA_BARANG] if COL_NAMA_BARANG < len(row) else ''
                category = row[COL_KATEGORI] if COL_KATEGORI < len(row) else ''
                harga = row[COL_HARGA] if COL_HARGA < len(row) else '0'
                ranking = row[COL_RANGKING] if COL_RANGKING < len(row) else 'E'
                
                parts_map[part_number] = Part(
                    part_id=part_number,  # Use part_number as ID
                    part_number=part_number,
                    name=name,
                    category=category,
                    unit_price=self._parse_indonesian_number(harga),
                    ranking=ranking
                )
        
        return list(parts_map.values())

    def get_all_locations(self, force_refresh: bool = False) -> List[Location]:
        """Extract unique locations from the flat data"""
        rows = self._get_all_rows(force_refresh)
        
        locations_map = {}
        
        for row in rows[3:]:
            if len(row) <= COL_LOKASI:
                continue
            
            location_path = row[COL_LOKASI] if COL_LOKASI < len(row) else ''
            if not location_path:
                continue
            
            # Map to short code
            location_id = LOCATION_MAPPING.get(location_path, 'DXK-UTAMA')
            
            if location_id not in locations_map:
                locations_map[location_id] = Location(
                    location_id=location_id,
                    branch_code='DXK',
                    name='Gudang Utama' if 'UTAMA' in location_id else 'Gudang Part Sandai',
                    profit_center='583'
                )
        
        return list(locations_map.values())

    def get_all_inventory(self, force_refresh: bool = False) -> List[InventoryItem]:
        """Extract inventory items (part + location + qty) from flat data"""
        rows = self._get_all_rows(force_refresh)
        
        inventory = []
        
        for idx, row in enumerate(rows[3:]):
            if len(row) <= COL_KODE_PRODUCT:
                continue
            
            part_number = row[COL_KODE_PRODUCT] if COL_KODE_PRODUCT < len(row) else ''
            location_path = row[COL_LOKASI] if COL_LOKASI < len(row) else ''
            qty_str = row[COL_QTY_AVAILABLE] if COL_QTY_AVAILABLE < len(row) else '0'
            
            if not part_number or not location_path:
                continue
            
            location_id = LOCATION_MAPPING.get(location_path, 'DXK-UTAMA')
            qty = self._parse_indonesian_number(qty_str)
            
            inventory.append(InventoryItem(
                id=f"inv-{idx}",
                location_id=location_id,
                part_id=part_number,
                qty_available=qty,
                last_updated=''
            ))
        
        return inventory

    def get_dashboard_stats(self) -> DashboardStats:
        """Calculate dashboard statistics"""
        parts = self.get_all_parts()
        locations = self.get_all_locations()
        inventory = self.get_all_inventory()
        
        # Calculate total unique SKUs
        total_skus = len(parts)
        
        # Calculate total value (sum of qty * price for each inventory item)
        total_value = 0
        part_prices = {p.part_number: p.unit_price for p in parts}
        
        low_stock_count = 0
        out_of_stock_count = 0
        seen_parts = set()
        
        for inv in inventory:
            price = part_prices.get(inv.part_id, 0)
            total_value += inv.qty_available * price
            
            # Count low/out of stock (dedupe by part_id)
            if inv.part_id not in seen_parts:
                seen_parts.add(inv.part_id)
                if inv.qty_available == 0:
                    out_of_stock_count += 1
                elif inv.qty_available < 5:
                    low_stock_count += 1
        
        return DashboardStats(
            total_skus=total_skus,
            total_value=total_value,
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_count,
            location_count=len(locations)
        )

    def search_part(self, part_number: str) -> List[Part]:
        """Search parts by part number"""
        parts = self.get_all_parts()
        query = part_number.lower().replace(' ', '')
        return [p for p in parts if query in p.part_number.lower().replace(' ', '')]

    def get_stock_by_location(self, location_name: str = None, location_id: str = None) -> Dict:
        """Get stock grouped by location"""
        parts = self.get_all_parts()
        inventory = self.get_all_inventory()
        locations = self.get_all_locations()
        
        location_map = {loc.location_id: loc for loc in locations}
        part_map = {p.part_id: p for p in parts}
        
        results = {}
        
        for inv in inventory:
            loc = location_map.get(inv.location_id)
            part = part_map.get(inv.part_id)
            
            if not loc:
                continue
            
            # Apply filters
            if location_id and inv.location_id != location_id:
                continue
            if location_name and location_name.lower() not in loc.name.lower():
                continue
            
            if inv.location_id not in results:
                results[inv.location_id] = {'location': loc, 'items': []}
            
            results[inv.location_id]['items'].append({
                'part': part,
                'qty': inv.qty_available,
                'value': inv.qty_available * (part.unit_price if part else 0)
            })
        
        return results

    def get_low_stock_items(self, threshold: int = 5) -> List[Dict]:
        """Get items with stock below threshold"""
        parts = self.get_all_parts()
        inventory = self.get_all_inventory()
        
        # Aggregate qty by part
        qty_by_part = {}
        for inv in inventory:
            if inv.part_id not in qty_by_part:
                qty_by_part[inv.part_id] = 0
            qty_by_part[inv.part_id] += inv.qty_available
        
        part_map = {p.part_id: p for p in parts}
        
        low_stock = []
        for part_id, total_qty in qty_by_part.items():
            if total_qty < threshold and total_qty > 0:
                part = part_map.get(part_id)
                if part:
                    low_stock.append({
                        'part': part,
                        'total_qty': total_qty
                    })
        
        # Sort by qty ascending
        low_stock.sort(key=lambda x: x['total_qty'])
        return low_stock

    def get_transactions(self, limit: int = 50, force_refresh: bool = False) -> List:
        """Transactions not available in this sheet structure"""
        return []
