"""
Data models for Bengkel Stock Monitor
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Part:
    part_id: str
    part_number: str
    name: str
    category: str
    unit_price: float
    ranking: str  # A/B/C/D/E

    @classmethod
    def from_row(cls, row: list) -> 'Part':
        return cls(
            part_id=row[0] if len(row) > 0 else '',
            part_number=row[1] if len(row) > 1 else '',
            name=row[2] if len(row) > 2 else '',
            category=row[3] if len(row) > 3 else '',
            unit_price=float(row[4]) if len(row) > 4 and row[4] else 0,
            ranking=row[5] if len(row) > 5 else 'E',
        )


@dataclass
class Location:
    location_id: str
    branch_code: str
    name: str
    profit_center: str

    @classmethod
    def from_row(cls, row: list) -> 'Location':
        return cls(
            location_id=row[0] if len(row) > 0 else '',
            branch_code=row[1] if len(row) > 1 else '',
            name=row[2] if len(row) > 2 else '',
            profit_center=row[3] if len(row) > 3 else '',
        )


@dataclass
class InventoryItem:
    id: str
    location_id: str
    part_id: str
    qty_available: float
    last_updated: str

    @classmethod
    def from_row(cls, row: list) -> 'InventoryItem':
        return cls(
            id=row[0] if len(row) > 0 else '',
            location_id=row[1] if len(row) > 1 else '',
            part_id=row[2] if len(row) > 2 else '',
            qty_available=float(row[3]) if len(row) > 3 and row[3] else 0,
            last_updated=row[4] if len(row) > 4 else '',
        )


@dataclass
class Transaction:
    id: str
    date: str
    location_id: str
    part_id: str
    type: str  # IN/OUT
    qty: float
    user: str
    notes: str

    @classmethod
    def from_row(cls, row: list) -> 'Transaction':
        return cls(
            id=row[0] if len(row) > 0 else '',
            date=row[1] if len(row) > 1 else '',
            location_id=row[2] if len(row) > 2 else '',
            part_id=row[3] if len(row) > 3 else '',
            type=row[4] if len(row) > 4 else '',
            qty=float(row[5]) if len(row) > 5 and row[5] else 0,
            user=row[6] if len(row) > 6 else '',
            notes=row[7] if len(row) > 7 else '',
        )


@dataclass
class StockInfo:
    part: Part
    location: Location
    qty_available: float
    total_value: float


@dataclass
class DashboardStats:
    total_skus: int
    total_value: float
    low_stock_count: int
    out_of_stock_count: int
    location_count: int
