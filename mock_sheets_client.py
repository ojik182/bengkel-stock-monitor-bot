"""
Mock sheets client for demonstration without credentials
"""

from models import Part, Location, InventoryItem, Transaction, DashboardStats
from typing import List, Dict


MOCK_PARTS = [
    Part(part_id='p1', part_number='06455K59A71', name='PAD SET,FR BRAKE', category='BRAKE', unit_price=69662, ranking='A'),
    Part(part_id='p2', part_number='082322MAK0LN9', name='OLI MPX1 10W30 SL 0,8L FED', category='OIL', unit_price=38626, ranking='A'),
    Part(part_id='p3', part_number='082322MAK1LN1', name='OLI MPX1 10W30 SL 1L IDE', category='OIL', unit_price=52754, ranking='A'),
    Part(part_id='p4', part_number='31500KZR602', name='BATTERY(GTZ6V)', category='BATT', unit_price=241819, ranking='A'),
    Part(part_id='p5', part_number='06430K44V80', name='SHOE SET,BRAKE', category='BRAKE', unit_price=43424, ranking='C'),
    Part(part_id='p6', part_number='17210K0JN00', name='ELEMENT COMP,AIR/C', category='EC', unit_price=42918, ranking='A'),
    Part(part_id='p7', part_number='23100K1ABA0', name='BELT DRIVE, KIT', category='BLDRV', unit_price=99187, ranking='C'),
    Part(part_id='p8', part_number='06401K18900', name='DRIVE CHAIN KIT', category='CDKGP', unit_price=239806, ranking='A'),
]

MOCK_LOCATIONS = [
    Location(location_id='DXK-UTAMA', branch_code='DXK', name='Gudang Utama', profit_center='583'),
    Location(location_id='DXK-SANDAI', branch_code='DXK', name='Gudang Part Sandai', profit_center='583'),
]

MOCK_INVENTORY = [
    InventoryItem(id='i1', location_id='DXK-UTAMA', part_id='p1', qty_available=284, last_updated='2026-04-20'),
    InventoryItem(id='i2', location_id='DXK-UTAMA', part_id='p2', qty_available=497, last_updated='2026-04-20'),
    InventoryItem(id='i3', location_id='DXK-UTAMA', part_id='p3', qty_available=94, last_updated='2026-04-20'),
    InventoryItem(id='i4', location_id='DXK-UTAMA', part_id='p4', qty_available=26, last_updated='2026-04-20'),
    InventoryItem(id='i5', location_id='DXK-UTAMA', part_id='p5', qty_available=33, last_updated='2026-04-20'),
    InventoryItem(id='i6', location_id='DXK-UTAMA', part_id='p6', qty_available=15, last_updated='2026-04-20'),
    InventoryItem(id='i7', location_id='DXK-SANDAI', part_id='p7', qty_available=30, last_updated='2026-04-20'),
    InventoryItem(id='i8', location_id='DXK-SANDAI', part_id='p1', qty_available=10, last_updated='2026-04-20'),
    InventoryItem(id='i9', location_id='DXK-UTAMA', part_id='p8', qty_available=4, last_updated='2026-04-20'),
]

MOCK_TRANSACTIONS = [
    Transaction(id='t1', date='2026-04-20 09:30', location_id='DXK-UTAMA', part_id='p1', type='OUT', qty=2, user='Ahmad', notes='Service Honda Beat'),
    Transaction(id='t2', date='2026-04-20 10:15', location_id='DXK-UTAMA', part_id='p2', type='OUT', qty=4, user='Budi', notes='Ganti oli cust ABC'),
    Transaction(id='t3', date='2026-04-20 11:00', location_id='DXK-SANDAI', part_id='p7', type='IN', qty=10, user='Admin', notes='Restock dari supplier'),
]


class MockSheetsClient:
    """Mock sheets client for demonstration"""

    def __init__(self, spreadsheet_id: str = None, credentials_path: str = None):
        self.spreadsheet_id = spreadsheet_id
        print("⚠️  Using MOCK data mode (no credentials required)")
        print("    To use real data, set up GOOGLE_SERVICE_ACCOUNT_KEY in .env")

    def get_all_parts(self, force_refresh: bool = False) -> List[Part]:
        return MOCK_PARTS

    def get_all_locations(self, force_refresh: bool = False) -> List[Location]:
        return MOCK_LOCATIONS

    def get_all_inventory(self, force_refresh: bool = False) -> List[InventoryItem]:
        return MOCK_INVENTORY

    def get_transactions(self, limit: int = 50, force_refresh: bool = False) -> List[Transaction]:
        return MOCK_TRANSACTIONS[:limit]

    def get_dashboard_stats(self) -> DashboardStats:
        return DashboardStats(
            total_skus=len(MOCK_PARTS),
            total_value=sum(p.unit_price * inv.qty_available for p in MOCK_PARTS for inv in MOCK_INVENTORY if inv.part_id == p.part_id),
            low_stock_count=2,  # p8 and p6 are low
            out_of_stock_count=0,
            location_count=len(MOCK_LOCATIONS)
        )

    def search_part(self, part_number: str) -> List[Part]:
        return [p for p in MOCK_PARTS if part_number.lower() in p.part_number.lower()]

    def get_stock_by_location(self, location_name: str = None, location_id: str = None) -> Dict:
        results = {}
        for inv in MOCK_INVENTORY:
            if location_id and inv.location_id == location_id:
                part = next((p for p in MOCK_PARTS if p.part_id == inv.part_id), None)
                loc = next((l for l in MOCK_LOCATIONS if l.location_id == inv.location_id), None)
                if part and loc:
                    if inv.location_id not in results:
                        results[inv.location_id] = {'location': loc, 'items': []}
                    results[inv.location_id]['items'].append({
                        'part': part,
                        'qty': inv.qty_available,
                        'value': inv.qty_available * part.unit_price
                    })
        return results

    def get_low_stock_items(self, threshold: int = 5) -> List[Dict]:
        inventory_by_part = {}
        for inv in MOCK_INVENTORY:
            if inv.part_id not in inventory_by_part:
                part = next((p for p in MOCK_PARTS if p.part_id == inv.part_id), None)
                loc = next((l for l in MOCK_LOCATIONS if l.location_id == inv.location_id), None)
                inventory_by_part[inv.part_id] = {
                    'part': part,
                    'total_qty': 0,
                    'by_location': []
                }
            inventory_by_part[inv.part_id]['total_qty'] += inv.qty_available
            inventory_by_part[inv.part_id]['by_location'].append({
                'location': loc,
                'qty': inv.qty_available
            })

        return [
            item for item in inventory_by_part.values()
            if item['total_qty'] < threshold
        ]
