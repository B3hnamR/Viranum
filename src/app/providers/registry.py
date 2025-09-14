from __future__ import annotations

from typing import Dict, List

from ..config import settings
from .base import Provider
from .numberland.adapter import NumberlandProvider
from .onlinesim.adapter import OnlineSimProvider


def _parse_display_map(raw: str) -> Dict[str, str]:
    # Format: "numberland:Numberland|5sim:5SIM"
    out: Dict[str, str] = {}
    for part in (raw or "").split("|"):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            k, v = part.split(":", 1)
            k = k.strip()
            v = v.strip()
            if k:
                out[k] = v or k
        else:
            out[part] = part
    return out


def enabled_providers() -> List[str]:
    raw = (settings.ENABLED_PROVIDERS or "numberland").strip()
    keys = [x.strip() for x in raw.split(",") if x.strip()]
    return keys or ["numberland"]


def provider_display_name_map() -> Dict[str, str]:
    return _parse_display_map(settings.PROVIDERS_DISPLAY or "onlinesim:OnlineSim")


def get_provider(key: str) -> Provider:
    key = (key or "").strip().lower()
    display = provider_display_name_map().get(key, key)

    if key == "numberland":
        return NumberlandProvider(key=key, display_name=display)
    if key == "onlinesim":
        return OnlineSimProvider(key=key, display_name=display)

    # Future: add 5sim, sms-activate, etc.
    raise ValueError(f"Unknown provider key: {key}")
