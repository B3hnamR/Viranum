from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from ...services.numberland_client import NumberlandClient, NumberlandAPIError
from ..base import Provider, ProviderAPIError


class NumberlandProvider(Provider):
    def __init__(self, *, key: str, display_name: str) -> None:
        self.key = key
        self.display_name = display_name

    # ---------------- Catalog ----------------
    async def balance(self) -> Dict[str, Any]:
        async with NumberlandClient() as cl:
            try:
                data = await cl.balance()
            except NumberlandAPIError as e:
                raise ProviderAPIError(getattr(e, "code", -1), getattr(e, "description", str(e)))
        # normalize casing
        bal = data.get("BALANCE") or data.get("balance") or "0"
        cur = data.get("CURRENCY") or data.get("currency") or "Toman"
        return {"BALANCE": str(bal), "CURRENCY": str(cur)}

    async def get_services(self) -> List[Dict[str, Any]]:
        async with NumberlandClient() as cl:
            data = await cl.get_services()
        # already list; keep as-is (contains id, name, name_en, active)
        return data if isinstance(data, list) else []

    async def get_countries(self) -> List[Dict[str, Any]]:
        async with NumberlandClient() as cl:
            data = await cl.get_countries()
        return data if isinstance(data, list) else []

    async def quote(
        self, *, service: Union[int, str], country: Union[int, str], operator: Union[int, str]
    ) -> Dict[str, Any]:
        async with NumberlandClient() as cl:
            info = await cl.get_info(service=service, country=country, operator=operator)
        item: Optional[Dict[str, Any]] = None
        if isinstance(info, dict) and info.get("amount"):
            item = info
        elif isinstance(info, list) and info:
            item = info[0]
        if not item:
            return {"amount": 0, "count": 0, "repeat": "0", "time": "00:20:00"}
        return {
            "amount": int(item.get("amount", 0)),
            "count": int(item.get("count", 0)),
            "repeat": str(item.get("repeat", "0")),
            "time": str(item.get("time", "00:20:00")),
        }

    # --------------- Temporary lifecycle ---------------
    async def buy_temp(
        self,
        *,
        service: Union[int, str],
        country: Union[int, str],
        operator: Union[int, str],
        price: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        async with NumberlandClient() as cl:
            try:
                res = await cl.get_num(service=service, country=country, operator=operator, price=price)
            except NumberlandAPIError as e:
                raise ProviderAPIError(getattr(e, "code", -1), getattr(e, "description", str(e)))
        return {
            "RESULT": int(res.get("RESULT", 1)),
            "ID": str(res.get("ID", "")),
            "NUMBER": str(res.get("NUMBER", "")),
            "AREACODE": str(res.get("AREACODE", "")),
            "AMOUNT": int(res.get("AMOUNT", 0)),
            "REPEAT": str(res.get("REPEAT", "0")),
            "TIME": str(res.get("TIME", "00:20:00")),
        }

    async def status(self, *, id: Union[int, str]) -> Dict[str, Any]:
        async with NumberlandClient() as cl:
            res = await cl.check_status(id=id)
        return {
            "RESULT": int(res.get("RESULT", 0)),
            "CODE": str(res.get("CODE", "")) if res.get("CODE") is not None else "",
            "DESCRIPTION": str(res.get("DESCRIPTION", "")) if res.get("DESCRIPTION") is not None else "",
        }

    async def cancel(self, *, id: Union[int, str]) -> Dict[str, Any]:
        async with NumberlandClient() as cl:
            res = await cl.cancel_number(id=id)
        return {"RESULT": int(res.get("RESULT", 0)), "DESCRIPTION": str(res.get("DESCRIPTION", ""))}

    async def ban(self, *, id: Union[int, str]) -> Dict[str, Any]:
        async with NumberlandClient() as cl:
            res = await cl.ban_number(id=id)
        return {"RESULT": int(res.get("RESULT", 0)), "DESCRIPTION": str(res.get("DESCRIPTION", ""))}

    async def repeat(self, *, id: Union[int, str]) -> Dict[str, Any]:
        async with NumberlandClient() as cl:
            res = await cl.repeat(id=id)
        return {"RESULT": int(res.get("RESULT", 0)), "DESCRIPTION": str(res.get("DESCRIPTION", ""))}

    async def close(self, *, id: Union[int, str]) -> Dict[str, Any]:
        async with NumberlandClient() as cl:
            res = await cl.close_number(id=id)
        return {"RESULT": int(res.get("RESULT", 0)), "DESCRIPTION": str(res.get("DESCRIPTION", ""))}

