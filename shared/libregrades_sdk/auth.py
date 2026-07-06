from dataclasses import dataclass
from typing import Any


@dataclass
class TokenPair:
    access: str
    refresh: str


class AuthClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def login(self, username: str, password: str) -> TokenPair:
        import requests

        r = requests.post(
            f"{self.base_url}/api/v1/auth/login/",
            json={"username": username, "password": password},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return TokenPair(access=data["access"], refresh=data["refresh"])

    def refresh(self, refresh_token: str) -> TokenPair:
        import requests

        r = requests.post(
            f"{self.base_url}/api/v1/auth/refresh/",
            json={"refresh": refresh_token},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return TokenPair(access=data["access"], refresh=data.get("refresh", refresh_token))
