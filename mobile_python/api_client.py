from __future__ import annotations

import json
from dataclasses import dataclass
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener


class ApiError(RuntimeError):
    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class ApiClient:
    base_url: str
    cookie_file: str | Path | None = None

    def __post_init__(self) -> None:
        cookie_path = Path(self.cookie_file).expanduser() if self.cookie_file else None
        self.cookie_file = cookie_path
        self.cookies = MozillaCookieJar(str(cookie_path) if cookie_path else None)
        if cookie_path and cookie_path.is_file():
            try:
                self.cookies.load(ignore_discard=True, ignore_expires=False)
            except (OSError, ValueError):
                # A damaged cookie file must never prevent the app from starting.
                self.cookies.clear()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))
        self.set_base_url(self.base_url)

    def set_base_url(self, value: str) -> None:
        value = value.strip().rstrip("/")
        if not value:
            self.base_url = ""
            return
        if not value.startswith(("http://", "https://")):
            value = f"http://{value}"
        parsed = urlsplit(value)
        try:
            parsed.port
        except ValueError as error:
            raise ApiError("Enter a valid server address and port.") from error
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ApiError("Enter a valid server address, for example http://192.168.1.100:3000.")
        self.base_url = value

    def _save_cookies(self) -> None:
        if not self.cookie_file:
            return
        try:
            self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
            self.cookies.save(ignore_discard=True, ignore_expires=False)
        except OSError:
            # Session persistence is helpful, but a read-only storage directory
            # should not break otherwise valid API requests.
            pass

    def request(self, path: str, method: str = "GET", body: dict[str, Any] | None = None, *, timeout: int = 20) -> Any:
        if not self.base_url:
            raise ApiError("Enter the Origin server address first.")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Origin-Client": "origin-ai-android",
            },
        )
        try:
            with self.opener.open(request, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                raw = response.read().decode("utf-8")
                self._save_cookies()
                if response.status == 204:
                    return None
                if "application/json" not in content_type:
                    raise ApiError("The server returned an unexpected response.", response.status)
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as error:
                    raise ApiError("The server returned invalid JSON.", response.status) from error
        except HTTPError as error:
            self._save_cookies()
            try:
                payload = json.loads(error.read().decode("utf-8"))
                message = payload.get("error", f"Request failed ({error.code}).")
            except Exception:
                message = f"Request failed ({error.code})."
            raise ApiError(message, error.code) from error
        except (URLError, TimeoutError) as error:
            raise ApiError("Cannot reach the Origin server. Check the server address and Wi-Fi connection.") from error

    def health(self) -> dict[str, Any]:
        return self.request("/api/health")

    def auth_status(self) -> dict[str, Any]:
        return self.request("/api/auth/status")

    def setup(self, email: str, display_name: str, display_name_ar: str, password: str, setup_token: str = "") -> dict[str, Any]:
        return self.request(
            "/api/auth/setup",
            "POST",
            {
                "email": email,
                "displayName": display_name,
                "displayNameAr": display_name_ar or display_name,
                "password": password,
                "setupToken": setup_token,
            },
        )

    def session(self) -> dict[str, Any]:
        return self.request("/api/auth/session")

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self.request("/api/auth/login", "POST", {"email": email, "password": password})

    def register(self, email: str, display_name: str, display_name_ar: str, password: str) -> dict[str, Any]:
        return self.request("/api/auth/register", "POST", {"email": email, "displayName": display_name, "displayNameAr": display_name_ar or display_name, "password": password})

    def logout(self) -> None:
        self.request("/api/auth/logout", "POST", {})

    def assets(self) -> list[dict[str, Any]]:
        return self.request("/api/assets")

    def stats(self) -> dict[str, Any]:
        return self.request("/api/stats")

    def market(self) -> list[dict[str, Any]]:
        return self.request("/api/market")

    def transfers(self) -> list[dict[str, Any]]:
        return self.request("/api/transfers")

    def create_asset(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("/api/assets", "POST", payload)

    def get_asset(self, asset_id: str) -> dict[str, Any]:
        return self.request(f"/api/assets/{quote(asset_id, safe='')}")

    def update_asset(self, asset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request(f"/api/assets/{quote(asset_id, safe='')}", "PATCH", payload)

    def delete_asset(self, asset_id: str) -> None:
        self.request(f"/api/assets/{quote(asset_id, safe='')}", "DELETE")

    def scan_asset(self, image_base64: str, mode: str = "photo") -> dict[str, Any]:
        return self.request("/api/assets/scan", "POST", {"imageBase64": image_base64, "mode": mode}, timeout=120)

    def add_maintenance(self, asset_id: str, title: str, description: str) -> dict[str, Any]:
        return self.request(f"/api/assets/{quote(asset_id, safe='')}/maintenance", "POST", {"title": title, "description": description})

    def list_for_sale(self, asset_id: str, price: float) -> dict[str, Any]:
        return self.request(f"/api/assets/{quote(asset_id, safe='')}/sell", "POST", {"marketPrice": price})

    def unlist_asset(self, asset_id: str) -> dict[str, Any]:
        return self.request(f"/api/assets/{quote(asset_id, safe='')}/unlist", "POST", {})

    def request_transfer(self, asset_id: str, email: str) -> dict[str, Any]:
        return self.request(f"/api/assets/{quote(asset_id, safe='')}/transfer", "POST", {"newOwner": email})

    def decide_transfer(self, request_id: str, action: str, acceptance_code: str = "") -> Any:
        return self.request(f"/api/transfers/{quote(request_id, safe='')}/{action}", "POST", {"acceptanceCode": acceptance_code})

    def reject_transfer(self, request_id: str) -> None:
        self.decide_transfer(request_id, "reject")

    def public_passport(self, asset_id: str) -> dict[str, Any]:
        return self.request(f"/api/public/passports/{quote(asset_id, safe='')}")

    def admin_summary(self) -> dict[str, int]:
        return self.request("/api/admin/summary")
