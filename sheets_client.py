"""
Google Sheets API client
"""

import os
import json
from typing import List, Optional, Dict
from datetime import datetime

from google.auth import load_credentials_from_file
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from models import Part, Location, InventoryItem, Transaction, DashboardStats


class SheetsClient:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def __init__(self, spreadsheet_id: str, credentials_path: Optional[str] = None):
        self.spreadsheet_id = spreadsheet_id
        self.service = self._get_service(credentials_path)
        self._cache: Dict[str, tuple] = {}
        self._cache_duration = 60  # seconds

    def _get_service(self, credentials_path: Optional[str] = None):
        """Initialize Google Sheets service"""
        creds = None

        # If credentials file path is provided, load from file
        if credentials_path and os.path.exists(credentials_path):
            creds = load_credentials_from_file(credentials_path, self.SCOPES)[0]
        # Otherwise try loading from env variable
        elif os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY'):
            creds_data = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY'))
            creds = load_credentials_from_file.__self__._build_credentials(
                creds_data, self.SCOPES
            )

        if not creds:
            raise ValueError(
                "No credentials found. Set GOOGLE_SERVICE_ACCOUNT_KEY env var "
                "or provide credentials.json path."
            )

        if creds.valid:
            pass
        elif creds.expired and creds.refresh_token:
            creds.refresh(Request())

        return build('sheets', 'v4', credentials=creds)

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache is still valid"""
        if key not in self._cache:
            return False
        _, timestamp = self._cache[key]
        return (datetime.now() - timestamp).total_seconds() < self._cache_duration

    def _get_sheet_data(self, range_name: str, force_refresh: bool = False) -> List[List]:
        """Fetch data from a sheet range"""
        if not force_refresh and self._is_cache_valid(range_name):
            return self._cache[range_name][0]

        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        ).execute()

        values = result.get('values', [])
        self._cache[range_name] = (values, datetime.now())
        return values

    def get_all_parts(self, force_refresh: bool = False) -> List[Part]:
        """Get all parts from Parts sheet"""
        values = self._get_sheet_data('Parts!A2:F', force_refresh)
        return [Part.from_row(row) for row in values if row]

    def get_all_locations(self, force_refresh: bool = False) -> List[Location]:
        """Get all locations from Locations sheet"""
        values = self._get_sheet_data('Locations!A2:D', force_refresh)
        return [Location.from_row(row) for row in values if row]

    def get_all_inventory(self, force_refresh: bool = False) -> List[InventoryItem]:
        """Get all inventory from Inventory sheet"""
        values = self._get_sheet_data('Inventory!A2:E', force_refresh)
        return [InventoryItem.from_row(row) for row in values if row]

    def get_transactions(self, limit: int = 50, force_refresh: bool = False) -> List[Transaction]:
        """Get recent transactions"""
        values = self._get_sheet_data(f'Transactions!A2:H{limit + 1}', force_refresh)
        return [Transaction.from_row(row) for row in values if row]

    def get_dashboard_stats(self) -> DashboardStats:
        """Calculate dashboard statistics"""
        parts = self.get_all_parts()
        locations = self.get_all_locations()
        inventory = self.get_all_inventory()

        # Create lookup maps
        part_map = {p.part_id: p for p in parts}
        location_map = {loc.location_id: loc for loc in locations}

        # Calculate totals
        total_skus = len(parts)
        total_value = 0
        low_stock_count = 0
        out_of_stock_count = 0

        inventory_by_part: Dict[str, float] = {}
        for inv in inventory:
            qty = inv.qty_available
            part = part_map.get(inv.part_id)
            if part:
                inventory_by_part[inv.part_id] = inventory_by_part.get(inv.part_id, 0) + qty
                total_value += qty * part.unit_price

                if qty == 0:
                    out_of_stock_count += 1
                elif qty < 5:
                    low_stock_count += 1

        return DashboardStats(
            total_skus=total_skus,
            total_value=total_value,
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_count,
            location_count=len(locations)
        )

    def search_part(self, part_number: str) -> List[Part]:
        """Search parts by part number (case-insensitive)"""
        parts = self.get_all_parts()
        return [p for p in parts if part_number.lower() in p.part_number.lower()]

    def get_stock_by_location(self, location_name: str = None, location_id: str = None) -> Dict:
        """Get stock summary for a location"""
        inventory = self.get_all_inventory()
        parts = self.get_all_parts()
        locations = self.get_all_locations()

        part_map = {p.part_id: p for p in parts}
        location_map = {loc.location_id: loc for loc in locations}

        if location_name:
            matching_locations = [
                loc for loc in locations
                if location_name.lower() in loc.name.lower()
            ]
            location_ids = [loc.location_id for loc in matching_locations]
        elif location_id:
            location_ids = [location_id]
        else:
            location_ids = [loc.location_id for loc in locations]

        results = {}
        for inv in inventory:
            if inv.location_id in location_ids:
                part = part_map.get(inv.part_id)
                if part:
                    if inv.location_id not in results:
                        results[inv.location_id] = {
                            'location': location_map.get(inv.location_id),
                            'items': []
                        }
                    results[inv.location_id]['items'].append({
                        'part': part,
                        'qty': inv.qty_available,
                        'value': inv.qty_available * part.unit_price
                    })

        return results

    def get_low_stock_items(self, threshold: int = 5) -> List[Dict]:
        """Get items with stock below threshold"""
        inventory = self.get_all_inventory()
        parts = self.get_all_parts()
        locations = self.get_all_locations()

        part_map = {p.part_id: p for p in parts}
        location_map = {loc.location_id: loc for loc in locations}

        inventory_by_part: Dict[str, Dict] = {}
        for inv in inventory:
            if inv.part_id not in inventory_by_part:
                inventory_by_part[inv.part_id] = {
                    'part': part_map.get(inv.part_id),
                    'total_qty': 0,
                    'by_location': []
                }
            inventory_by_part[inv.part_id]['total_qty'] += inv.qty_available
            inventory_by_part[inv.part_id]['by_location'].append({
                'location': location_map.get(inv.location_id),
                'qty': inv.qty_available
            })

        low_stock = [
            item for item in inventory_by_part.values()
            if item['total_qty'] < threshold
        ]
        return sorted(low_stock, key=lambda x: x['total_qty'])

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a new transaction (requires write access)"""
        # This would need write credentials, not read-only
        # For now, we'll mark this as TODO
        raise NotImplementedError(
            "Adding transactions requires write credentials. "
            "Please use the Google Sheets UI to manually add transactions."
        )
