from typing import Any, Optional

import requests

from libregrades_sdk.auth import AuthClient, TokenPair


class LibreGradesClient:
    def __init__(self, base_url: str, access_token: Optional[str] = None, refresh_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.auth = AuthClient(base_url)

    def login(self, username: str, password: str) -> dict:
        tokens = self.auth.login(username, password)
        self.access_token = tokens.access
        self.refresh_token = tokens.refresh
        return self.me()

    def _headers(self) -> dict:
        if not self.access_token:
            raise RuntimeError("Not authenticated")
        return {"Authorization": f"Bearer {self.access_token}"}

    def _get(self, path: str, **params) -> Any:
        r = requests.get(f"{self.base_url}{path}", headers=self._headers(), params=params, timeout=30)
        if r.status_code == 401 and self.refresh_token:
            tokens = self.auth.refresh(self.refresh_token)
            self.access_token = tokens.access
            self.refresh_token = tokens.refresh
            r = requests.get(f"{self.base_url}{path}", headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> Any:
        r = requests.post(f"{self.base_url}{path}", headers=self._headers(), json=data, timeout=30)
        r.raise_for_status()
        return r.json()

    def me(self) -> dict:
        return self._get("/api/v1/auth/me/")

    def server_info(self) -> dict:
        import requests

        r = requests.get(f"{self.base_url}/api/v1/server/", timeout=30)
        r.raise_for_status()
        return r.json()

    def student_me(self) -> dict:
        return self._get("/api/v1/students/me/")

    def parent_children(self) -> list:
        return self._get("/api/v1/parents/children/")

    def student_grades(self, student_id: int) -> list:
        return self._get(f"/api/v1/students/{student_id}/grades/")

    def student_missing(self, student_id: int) -> list:
        return self._get(f"/api/v1/students/{student_id}/missing-assignments/")

    def student_schedule(self, student_id: int) -> list:
        return self._get(f"/api/v1/students/{student_id}/schedule/")

    def student_credits(self, student_id: int) -> dict:
        return self._get(f"/api/v1/students/{student_id}/credits/")

    def student_medical(self, student_id: int) -> dict:
        return self._get(f"/api/v1/students/{student_id}/medical/")

    def my_medical(self) -> dict:
        return self._get("/api/v1/auth/me/medical/")

    def student_emergency(self, student_id: int) -> list:
        return self._get(f"/api/v1/students/{student_id}/emergency-contacts/")

    def student_behavior(self, student_id: int) -> list:
        return self._get(f"/api/v1/students/{student_id}/behavior/")

    def student_attendance(self, student_id: int) -> list:
        return self._get(f"/api/v1/students/{student_id}/attendance/")

    def teacher_sections(self) -> list:
        return self._get("/api/v1/sections/")

    def section_gradebook(self, section_id: int) -> dict:
        return self._get(f"/api/v1/sections/{section_id}/gradebook/")

    def submit_grade(self, section_id: int, student_id: int, assignment_id: int, points) -> dict:
        return self._post(
            f"/api/v1/sections/{section_id}/gradebook/",
            {
                "student_id": student_id,
                "assignment_id": assignment_id,
                "points": points,
            },
        )

    def notifications(self) -> list:
        return self._get("/api/v1/notifications/")

    def unread_notification_count(self) -> int:
        return int(self._get("/api/v1/notifications/unread-count/").get("count", 0))

    def register_device(self, token: str, platform: str = "kivy") -> dict:
        return self._post("/api/v1/notifications/register-device/", {"token": token, "platform": platform})

    def notification_preferences(self) -> dict:
        return self._get("/api/v1/notifications/preferences/")
