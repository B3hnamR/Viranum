from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class ProviderError(Exception):
    pass


class ProviderAPIError(ProviderError):
    def __init__(self, code: int, description: str):
        super().__init__(f"API error {code}: {description}")
        self.code = code
        self.description = description


class Provider(ABC):
    """Common interface for all virtual-number providers."""

    key: str  # lowercase key (e.g. "numberland", "5sim")
    display_name: str

    # Catalog
    @abstractmethod
    async def balance(self) -> Dict[str, Any]:
        """Return panel balance in a normalized dict: {BALANCE, CURRENCY}.
        Using keys consistent with current bot output.
        """

    @abstractmethod
    async def get_services(self) -> List[Dict[str, Any]]:
        """Return list of services. Normalized fields used by UI:
        id, name, name_en, active
        """

    @abstractmethod
    async def get_countries(self) -> List[Dict[str, Any]]:
        """Return list of countries. Normalized fields used by UI:
        id, name, name_en, emoji, active
        """

    @abstractmethod
    async def quote(
        self, *, service: Union[int, str], country: Union[int, str], operator: Union[int, str]
    ) -> Dict[str, Any]:
        """Return a normalized quote dict with keys: amount, count, repeat, time."""

    # Temporary numbers lifecycle
    @abstractmethod
    async def buy_temp(
        self,
        *,
        service: Union[int, str],
        country: Union[int, str],
        operator: Union[int, str],
        price: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """Return a normalized purchase dict with keys: ID, NUMBER, AREACODE, AMOUNT, REPEAT, TIME"""

    @abstractmethod
    async def status(self, *, id: Union[int, str]) -> Dict[str, Any]:
        """Return a normalized status dict with keys: RESULT, CODE, DESCRIPTION"""

    @abstractmethod
    async def cancel(self, *, id: Union[int, str]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def ban(self, *, id: Union[int, str]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def repeat(self, *, id: Union[int, str]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def close(self, *, id: Union[int, str]) -> Dict[str, Any]:
        pass

