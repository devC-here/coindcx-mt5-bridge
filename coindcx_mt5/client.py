from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from .models import OrderRequest

API_URL = "https://api.coindcx.com"
class CoinDCXError(RuntimeError): pass
class CoinDCXAPIError(CoinDCXError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"CoinDCX returned HTTP {status}: {body}")
        self.status, self.body = status, body
Transport = Callable[[str, bytes, dict[str, str], float], tuple[int, bytes]]

def _urllib_transport(url: str, body: bytes, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response: # noqa: S310 fixed HTTPS API URL
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        raise CoinDCXError(f"Could not reach CoinDCX: {exc.reason}") from exc

class CoinDCXClient:
    """CoinDCX Spot client. Dry-run by default; live orders need per-call confirmation."""
    def __init__(self, api_key: str | None = None, api_secret: str | None = None, *, live_trading: bool = False, timeout: float = 10.0, transport: Transport = _urllib_transport) -> None:
        self.api_key = api_key or os.getenv("COINDCX_API_KEY")
        self.api_secret = api_secret or os.getenv("COINDCX_API_SECRET")
        self.live_trading, self.timeout, self._transport = live_trading, timeout, transport
    @staticmethod
    def _json_bytes(payload: dict[str, object]) -> bytes:
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    def _signed_post(self, path: str, payload: dict[str, object]) -> Any:
        if not self.api_key or not self.api_secret:
            raise CoinDCXError("Set COINDCX_API_KEY and COINDCX_API_SECRET before live requests")
        body = self._json_bytes(payload)
        signature = hmac.new(self.api_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        status, response = self._transport(f"{API_URL}{path}", body, {"Content-Type": "application/json", "X-AUTH-APIKEY": self.api_key, "X-AUTH-SIGNATURE": signature}, self.timeout)
        decoded = response.decode("utf-8", errors="replace")
        if not 200 <= status < 300: raise CoinDCXAPIError(status, decoded)
        try: return json.loads(decoded)
        except json.JSONDecodeError as exc: raise CoinDCXError(f"CoinDCX returned invalid JSON: {decoded}") from exc
    def balances(self) -> Any:
        return self._signed_post("/exchange/v1/users/balances", {"timestamp": int(time.time() * 1000)})
    def place_order(self, order: OrderRequest, *, confirm_live: bool = False) -> dict[str, Any]:
        payload = order.payload(int(time.time() * 1000))
        if not self.live_trading: return {"dry_run": True, "endpoint": "/exchange/v1/orders/create", "payload": payload}
        if not confirm_live: raise CoinDCXError("Live trading needs confirm_live=True for each order")
        return {"dry_run": False, "response": self._signed_post("/exchange/v1/orders/create", payload)}
