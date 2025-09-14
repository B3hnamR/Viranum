from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Union

import httpx
from loguru import logger

from ..config import settings


BASE_URL = "https://api.numberland.ir/v2.php"


class NumberlandError(Exception):
    pass


class NumberlandHTTPError(NumberlandError):
    def __init__(self, status_code: int, message: str):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class NumberlandInvalidResponse(NumberlandError):
    pass


class NumberlandAPIError(NumberlandError):
    def __init__(self, code: int, description: str):
        super().__init__(f"API error {code}: {description}")
        self.code = code
        self.description = description


NEGATIVE_RESULT_MAP = {
    -901: "apikey not found",
    -902: "method invalid",
    -990: "number id invalid",
    -900: "other technical error",
    # getnum specific
    -202: "parameters not found",
    -204: "this number is not active",
    -205: "no balance",
    -210: "service is not active",
    -211: "operator is not active",
    -212: "country is not active",
    # checkstatus specific
    -304: "number id not found",
}


class NumberlandClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = BASE_URL,
        timeout: float = 15.0,
        max_retries: int = 2,
        backoff_factor: float = 0.6,
        http2: bool = False,
    ) -> None:
        self.api_key = api_key or settings.NUMBERLAND_API_KEY
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.http2 = http2
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "NumberlandClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def _ensure_client(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                http2=self.http2,
                headers={"User-Agent": "ViranumBot/1.0"},
            )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(
        self, method_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, Any], list]:
        if not self.api_key:
            raise NumberlandError("Missing NUMBERLAND_API_KEY")

        q = {"apikey": self.api_key, "method": method_name}
        if params:
            q.update(params)

        await self._ensure_client()
        assert self._client is not None

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                r = await self._client.get(self.base_url, params=q)
                if r.status_code >= 400:
                    # 5xx -> retry, 4xx -> fail fast
                    if 500 <= r.status_code < 600 and attempt < self.max_retries:
                        delay = self.backoff_factor * (2**attempt)
                        logger.warning(
                            "HTTP {} for method {}, retrying in {}s (attempt {}/{})",
                            r.status_code,
                            method_name,
                            delay,
                            attempt + 1,
                            self.max_retries,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise NumberlandHTTPError(r.status_code, r.text)

                data = r.json()
                # Some endpoints return list directly (e.g., getcountry, getservice)
                if isinstance(data, list):
                    return data

                if not isinstance(data, dict):
                    raise NumberlandInvalidResponse("Unexpected JSON structure")

                # RESULT can be 'RESULT' or 'result' and might be str or int
                result_val = None
                if "RESULT" in data:
                    try:
                        result_val = int(data["RESULT"])
                    except Exception:
                        result_val = data["RESULT"]
                elif "result" in data:
                    try:
                        result_val = int(data["result"])
                    except Exception:
                        result_val = data["result"]

                if isinstance(result_val, int) and result_val < 0:
                    desc = data.get("DESCRIPTION") or NEGATIVE_RESULT_MAP.get(result_val, "")
                    raise NumberlandAPIError(result_val, desc or "negative result")

                return data
            except httpx.RequestError as e:
                last_exc = e
                if attempt < self.max_retries:
                    delay = self.backoff_factor * (2**attempt)
                    logger.warning(
                        "Network error for method {}: {}. Retrying in {}s (attempt {}/{})",
                        method_name,
                        e,
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise NumberlandHTTPError(-1, str(e))
            except ValueError as e:  # JSON decode error
                last_exc = e
                if attempt < self.max_retries:
                    delay = self.backoff_factor * (2**attempt)
                    logger.warning(
                        "JSON decode error for method {}: {}. Retrying in {}s (attempt {}/{})",
                        method_name,
                        e,
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise NumberlandInvalidResponse("Invalid JSON response")

        assert last_exc is not None
        raise NumberlandError(str(last_exc))

    # --------------- Public API methods ---------------

    async def balance(self) -> Dict[str, Any]:
        return await self._get("balance")

    async def get_info(
        self,
        *,
        service: Optional[Union[int, str]] = None,
        country: Optional[Union[int, str]] = None,
        operator: Optional[Union[int, str]] = None,
    ) -> Union[Dict[str, Any], list]:
        params: Dict[str, Any] = {}
        if service is not None:
            params["service"] = str(service)
        if country is not None:
            params["country"] = str(country)
        if operator is not None:
            params["operator"] = str(operator)
        return await self._get("getinfo", params)

    async def get_num(
        self,
        *,
        service: Union[int, str],
        country: Union[int, str],
        operator: Union[int, str],
        price: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        params = {
            "service": str(service),
            "country": str(country),
            "operator": str(operator),
        }
        if price is not None:
            params["price"] = str(price)
        return await self._get("getnum", params)

    async def check_status(self, *, id: Union[int, str]) -> Dict[str, Any]:
        return await self._get("checkstatus", {"id": str(id)})

    async def cancel_number(self, *, id: Union[int, str]) -> Dict[str, Any]:
        return await self._get("cancelnumber", {"id": str(id)})

    async def ban_number(self, *, id: Union[int, str]) -> Dict[str, Any]:
        return await self._get("bannumber", {"id": str(id)})

    async def repeat(self, *, id: Union[int, str]) -> Dict[str, Any]:
        return await self._get("repeat", {"id": str(id)})

    async def close_number(self, *, id: Union[int, str]) -> Dict[str, Any]:
        return await self._get("closenumber", {"id": str(id)})

    async def get_countries(self) -> Union[list, Dict[str, Any]]:
        return await self._get("getcountry")

    async def get_services(self) -> Union[list, Dict[str, Any]]:
        return await self._get("getservice")

    async def spnumbers_list(self) -> Dict[str, Any]:
        return await self._get("spnumberslist")

    async def spnumbers_tree(self) -> Dict[str, Any]:
        return await self._get("spnumberstree")

    async def get_sp_number(self, *, number_id: Union[int, str]) -> Dict[str, Any]:
        return await self._get("getspnumber", {"id": str(number_id)})

    async def my_sp_numbers(self) -> Dict[str, Any]:
        return await self._get("myspnumbers")


# Convenience async context manager factory
async def get_client() -> NumberlandClient:
    client = NumberlandClient()
    await client._ensure_client()
    return client
