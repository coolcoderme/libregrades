import json

import os

import sqlite3

from pathlib import Path





class ConfigStore:

    def __init__(self):

        base = Path.home() / ".libregrades"

        base.mkdir(exist_ok=True)

        self.config_path = base / "config.json"

        self.db_path = base / "cache.db"

        self._init_db()



    def _init_db(self):

        conn = sqlite3.connect(self.db_path)

        conn.execute(

            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)"

        )

        conn.commit()

        conn.close()



    def _read(self) -> dict:

        if self.config_path.exists():

            return json.loads(self.config_path.read_text())

        return {}



    def _write(self, data: dict):

        self.config_path.write_text(json.dumps(data, indent=2))



    def get_server_url(self) -> str:

        return self._read().get("server_url", "http://localhost")



    def get_server_code(self) -> str:

        return self._read().get("server_code", "")



    def get_district_name(self) -> str:

        return self._read().get("district_name", "")



    def set_server_url(self, url: str):

        data = self._read()

        data["server_url"] = url.rstrip("/")

        self._write(data)



    def set_server_identity(self, server_code: str, district_name: str = ""):

        data = self._read()

        data["server_code"] = server_code

        if district_name:

            data["district_name"] = district_name

        self._write(data)



    def get_tokens(self) -> tuple[str | None, str | None]:

        data = self._read()

        return data.get("access_token"), data.get("refresh_token")



    def set_tokens(self, access: str, refresh: str):

        data = self._read()

        data["access_token"] = access

        data["refresh_token"] = refresh

        self._write(data)



    def clear_tokens(self):

        data = self._read()

        data.pop("access_token", None)

        data.pop("refresh_token", None)

        self._write(data)

    def get_device_token(self) -> str:
        return self._read().get("device_token", "")

    def set_device_token(self, token: str):
        data = self._read()
        data["device_token"] = token
        self._write(data)



    def cache_set(self, key: str, value: dict):

        import time



        conn = sqlite3.connect(self.db_path)

        conn.execute(

            "INSERT OR REPLACE INTO cache (key, value, updated_at) VALUES (?, ?, ?)",

            (key, json.dumps(value), time.time()),

        )

        conn.commit()

        conn.close()



    def cache_get(self, key: str) -> dict | None:

        conn = sqlite3.connect(self.db_path)

        row = conn.execute("SELECT value FROM cache WHERE key = ?", (key,)).fetchone()

        conn.close()

        if row:

            return json.loads(row[0])

        return None

