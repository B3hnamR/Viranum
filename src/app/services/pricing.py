from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..config import settings


@dataclass
class PricingRule:
    scope: str  # global | service | country | operator | combo
    service_id: Optional[str] = None
    country_id: Optional[str] = None
    operator: Optional[str] = None
    margin_percent: Optional[float] = None
    min_margin: Optional[int] = None
    round_to: Optional[int] = None
    active: bool = True


def round_to_step(value: float, step: int) -> int:
    if step <= 0:
        return int(round(value))
    return int((int(value) + step - 1) // step * step)


def calculate_price(
    base_amount: int,
    rule: Optional[PricingRule] = None,
    default_margin_percent: Optional[float] = None,
    default_round_to: Optional[int] = None,
    default_min_margin: Optional[int] = None,
) -> int:
    margin_percent = (
        rule.margin_percent if rule and rule.margin_percent is not None else default_margin_percent
    )
    round_to = rule.round_to if rule and rule.round_to is not None else default_round_to
    min_margin = rule.min_margin if rule and rule.min_margin is not None else default_min_margin

    if margin_percent is None:
        margin_percent = settings.BASE_MARKUP_PERCENT
    if round_to is None:
        round_to = settings.MARKUP_ROUND_TO
    if min_margin is None:
        min_margin = 0

    price_float = base_amount * (1.0 + margin_percent / 100.0)
    price = round_to_step(price_float, int(round_to))

    profit = price - base_amount
    if profit < min_margin:
        price = base_amount + min_margin
        price = round_to_step(price, int(round_to))

    return int(price)
