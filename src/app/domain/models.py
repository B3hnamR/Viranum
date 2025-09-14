from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Balance:
    balance: str
    currency: str = "Toman"


@dataclass
class Quote:
    amount: int
    count: int
    repeat: bool
    time: str  # HH:MM:SS


@dataclass
class PurchaseResult:
    id: str
    number: str
    areacode: str
    amount: int
    repeat: bool
    time: str


@dataclass
class StatusResult:
    result: int
    code: str = ""
    description: str = ""

