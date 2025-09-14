from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Union

import httpx
from loguru import logger

from ...config import settings
from ..base import Provider, ProviderAPIError


BASE_URL = "https://onlinesim.io/api"


class _HTTP:
    def __init__(self, api_key: str, timeout: float = 15.0) -> None:
        self.key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "_HTTP":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": "ViranumBot/1.0"})
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        q = params.copy() if params else {}
        q["apikey"] = self.key
        url = f"{BASE_URL}/{endpoint}"
        for attempt in range(3):
            try:
                r = await self._client.get(url, params=q)
                if r.status_code >= 500 and attempt < 2:
                    await asyncio.sleep(0.4 * (2**attempt))
                    continue
                r.raise_for_status()
                try:
                    return r.json()
                except Exception:
                    logger.error("Invalid JSON from OnlineSim: {} {}", r.status_code, r.text[:200])
                    raise ProviderAPIError(-1, "invalid json")
            except httpx.HTTPError as e:
                if attempt == 2:
                    raise ProviderAPIError(-1, str(e))
                await asyncio.sleep(0.4 * (2**attempt))


def _ok(data: Any) -> bool:
    # OnlineSim responses vary; consider presence of error as failure
    if isinstance(data, dict):
        if any(k in data for k in ("error", "error_msg", "errorCode")):
            return False
        # some endpoints use response:1
        if str(data.get("response", "1")) == "1":
            return True
        # some return balance only
        return True
    return False


def _normalize_service_name(code: str) -> str:
    mapping = {
        "tg": "Telegram",
        "wa": "WhatsApp",
        "fb": "Facebook",
        "vk": "VKontakte",
        "go": "Google",
        "ig": "Instagram",
        "tw": "Twitter",
    }
    return mapping.get(code, code.upper())


def _country_name(cid: str) -> str:
    names = {
        "7": "Russia",
        "380": "Ukraine",
        "1": "USA",
        "44": "United Kingdom",
        "49": "Germany",
        "90": "Turkey",
        "98": "Iran",
    }
    return names.get(cid, f"Country {cid}")


class OnlineSimProvider(Provider):
    def __init__(self, *, key: str, display_name: str) -> None:
        self.key = key
        self.display_name = display_name

    # ---------------- Catalog ----------------
    async def balance(self) -> Dict[str, Any]:
        if not settings.ONLINESIM_API_KEY:
            raise ProviderAPIError(-1, "missing ONLINESIM_API_KEY")
        async with _HTTP(settings.ONLINESIM_API_KEY) as http:
            data = await http.get("getBalance.php")
        if not _ok(data):
            raise ProviderAPIError(int(data.get("errorCode", -1) or -1), data.get("error_msg", "balance error"))
        # Known shapes: {balance: "...", ...} or {response:1, balance:"..."}
        bal = data.get("balance") or data.get("BALANCE") or data.get("money") or "0"
        return {"BALANCE": str(bal), "CURRENCY": "RUB"}

    async def get_services(self) -> List[Dict[str, Any]]:
        if not settings.ONLINESIM_API_KEY:
            raise ProviderAPIError(-1, "missing ONLINESIM_API_KEY")
        async with _HTTP(settings.ONLINESIM_API_KEY) as http:
            # Try global tariffs first (localized pricing, bigger page)
            data = await http.get(
                "getTariffs.php",
                {"locale_price": "1", "count": "200", "page": "1", "lang": "en"},
            )
        if not _ok(data):
            raise ProviderAPIError(int(data.get("errorCode", -1) or -1), data.get("error_msg", "tariffs error"))
        # Expected structures to support:
        # 1) {response:1, tariffs:{"7": {"tg": {...}, ...}, ...}}
        # 2) {response:1, tarifs:{...}}  (typo on some variants)
        # 3) {response:1, data:{...}}
        tariffs = data.get("tariffs") or data.get("tarifs") or data.get("data") or {}
        seen: Dict[str, bool] = {}
        out: List[Dict[str, Any]] = []
        for _cid, svs in tariffs.items():
            if not isinstance(svs, dict):
                continue
            for s_code in svs.keys():
                if s_code in seen:
                    continue
                seen[s_code] = True
                out.append({
                    "id": s_code,
                    "name": _normalize_service_name(s_code),
                    "name_en": _normalize_service_name(s_code),
                    "active": 1,
                })
        # sort by name
        out.sort(key=lambda x: x.get("name_en", ""))
        # Fallback: if empty, try a couple of common countries to extract service codes
        if not out:
            for test_c in ("7", "1", "44"):
                async with _HTTP(settings.ONLINESIM_API_KEY) as http:
                    d2 = await http.get(
                        "getTariffs.php",
                        {"country": test_c, "locale_price": "1", "count": "200", "page": "1", "lang": "en"},
                    )
                if not _ok(d2):
                    continue
                t2 = d2.get("tariffs") or d2.get("tarifs") or d2.get("data") or {}
                svs = t2.get(test_c, {}) if isinstance(t2, dict) else {}
                if isinstance(svs, dict):
                    for s_code in svs.keys():
                        if s_code in seen:
                            continue
                        seen[s_code] = True
                        out.append({
                            "id": s_code,
                            "name": _normalize_service_name(s_code),
                            "name_en": _normalize_service_name(s_code),
                            "active": 1,
                        })
            out.sort(key=lambda x: x.get("name_en", ""))
        return out

    async def get_countries(self) -> List[Dict[str, Any]]:
        if not settings.ONLINESIM_API_KEY:
            raise ProviderAPIError(-1, "missing ONLINESIM_API_KEY")
        async with _HTTP(settings.ONLINESIM_API_KEY) as http:
            data = await http.get(
                "getTariffs.php", {"locale_price": "1", "count": "200", "page": "1", "lang": "en"}
            )
        if not _ok(data):
            raise ProviderAPIError(int(data.get("errorCode", -1) or -1), data.get("error_msg", "tariffs error"))
        tariffs = data.get("tariffs") or data.get("tarifs") or data.get("data") or {}
        out: List[Dict[str, Any]] = []
        for cid in tariffs.keys():
            out.append({
                "id": str(cid),
                "name": _country_name(str(cid)),
                "name_en": _country_name(str(cid)),
                "emoji": "",
                "active": 1,
            })
        out.sort(key=lambda x: x.get("name_en", ""))
        return out

    async def quote(
        self, *, service: Union[int, str], country: Union[int, str], operator: Union[int, str]
    ) -> Dict[str, Any]:
        # OnlineSim does not have operator granularity in same way; ignore operator param
        if not settings.ONLINESIM_API_KEY:
            raise ProviderAPIError(-1, "missing ONLINESIM_API_KEY")
        async with _HTTP(settings.ONLINESIM_API_KEY) as http:
            data = await http.get(
                "getTariffs.php",
                {
                    "country": str(country),
                    "filter_service": str(service),
                    "locale_price": "1",
                    "count": "200",
                    "page": "1",
                    "lang": "en",
                },
            )
        if not _ok(data):
            raise ProviderAPIError(int(data.get("errorCode", -1) or -1), data.get("error_msg", "tariffs error"))
        tariffs = data.get("tariffs", {})
        svs = tariffs.get(str(country), {}) if isinstance(tariffs, dict) else {}
        ent = svs.get(str(service)) or svs.get(service) or {}
        amount = int(ent.get("cost", ent.get("price", 0)))
        count = int(ent.get("count", ent.get("numbers", 0)))
        repeat = "1"  # OnlineSim usually supports repeat (request next code)
        time_str = "00:20:00"
        return {"amount": amount, "count": count, "repeat": repeat, "time": time_str}

    async def buy_temp(
        self,
        *,
        service: Union[int, str],
        country: Union[int, str],
        operator: Union[int, str],
        price: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        if not settings.ONLINESIM_API_KEY:
            raise ProviderAPIError(-1, "missing ONLINESIM_API_KEY")
        async with _HTTP(settings.ONLINESIM_API_KEY) as http:
            data = await http.get(
                "getNum.php",
                {"service": str(service), "country": str(country), "lang": "en"},
            )
        if not _ok(data):
            raise ProviderAPIError(int(data.get("errorCode", -1) or -1), data.get("error_msg", "getNum error"))
        # Known shape: {response:1, tzid: "12345", number: "+7..."}
        tzid = str(data.get("tzid") or data.get("id") or "")
        number = str(data.get("number") or data.get("NUMBER") or "")
        areacode = ""  # not provided
        amount = int(price or 0)
        repeat = "1"
        time_str = "00:20:00"
        return {
            "RESULT": 1,
            "ID": tzid,
            "NUMBER": number,
            "AREACODE": areacode,
            "AMOUNT": amount,
            "REPEAT": repeat,
            "TIME": time_str,
        }

    async def status(self, *, id: Union[int, str]) -> Dict[str, Any]:
        if not settings.ONLINESIM_API_KEY:
            raise ProviderAPIError(-1, "missing ONLINESIM_API_KEY")
        async with _HTTP(settings.ONLINESIM_API_KEY) as http:
            data = await http.get("getState.php", {"tzid": str(id)})
        # getState may return list or dict. Try normalize
        item: Dict[str, Any] = {}
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            # sometimes returns {response:1, state:[...]}
            if isinstance(data.get("state"), list) and data["state"]:
                item = data["state"][0]
            else:
                item = data

        code = str(item.get("code") or "")
        msg = str(item.get("msg") or item.get("status") or "").lower()
        description = msg
        # Map to internal NumberStatus
        # Heuristics: presence of code -> CODE_RECEIVED; msg contains over/completed -> COMPLETED; cancel -> CANCELED; wait -> WAIT_CODE/WAIT_CODE_AGAIN
        if code:
            result = 2  # CODE_RECEIVED
        elif "over" in msg or "complete" in msg or "finish" in msg:
            result = 6
        elif "cancel" in msg or "ban" in msg:
            result = 3
        elif "again" in msg:
            result = 5
        else:
            result = 1
        return {"RESULT": result, "CODE": code, "DESCRIPTION": description}

    async def cancel(self, *, id: Union[int, str]) -> Dict[str, Any]:
        if not settings.ONLINESIM_API_KEY:
            raise ProviderAPIError(-1, "missing ONLINESIM_API_KEY")
        async with _HTTP(settings.ONLINESIM_API_KEY) as http:
            data = await http.get("setOperation.php", {"tzid": str(id), "op": "8"})
        return {"RESULT": 1 if _ok(data) else 0, "DESCRIPTION": str(data)}

    async def ban(self, *, id: Union[int, str]) -> Dict[str, Any]:
        # OnlineSim cancel covers it; use same endpoint
        return await self.cancel(id=id)

    async def repeat(self, *, id: Union[int, str]) -> Dict[str, Any]:
        if not settings.ONLINESIM_API_KEY:
            raise ProviderAPIError(-1, "missing ONLINESIM_API_KEY")
        async with _HTTP(settings.ONLINESIM_API_KEY) as http:
            data = await http.get("setOperation.php", {"tzid": str(id), "op": "3"})
        return {"RESULT": 1 if _ok(data) else 0, "DESCRIPTION": str(data)}

    async def close(self, *, id: Union[int, str]) -> Dict[str, Any]:
        if not settings.ONLINESIM_API_KEY:
            raise ProviderAPIError(-1, "missing ONLINESIM_API_KEY")
        async with _HTTP(settings.ONLINESIM_API_KEY) as http:
            data = await http.get("setOperation.php", {"tzid": str(id), "op": "6"})
        return {"RESULT": 1 if _ok(data) else 0, "DESCRIPTION": str(data)}
