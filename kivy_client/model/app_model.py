from libregrades_sdk.client import LibreGradesClient

from services.config_store import ConfigStore
import uuid


class AppModel:
    def __init__(self):
        self.store = ConfigStore()
        access, refresh = self.store.get_tokens()
        self.client = LibreGradesClient(
            self.store.get_server_url(), access_token=access, refresh_token=refresh
        )
        self.user = None
        self.student = None
        self.children = []

    def save_session(self):
        if self.client.access_token:
            self.store.set_tokens(self.client.access_token, self.client.refresh_token or "")

    def login(self, username: str, password: str):
        self.user = self.client.login(username, password)
        self.save_session()
        self._register_device()
        role = self.user.get("role")
        if role == "student":
            self.student = self.client.student_me()
        elif role == "parent":
            self.children = self.client.parent_children()
            if self.children:
                self.student = self.children[0]
        self.sync_offline_cache()
        return self.user

    def logout(self):
        self.store.clear_tokens()
        self.user = None
        self.student = None
        self.children = []

    def current_student_id(self) -> int | None:
        if self.student:
            return self.student.get("id")
        return None

    def fetch_grades(self):
        sid = self.current_student_id()
        if not sid:
            return []
        try:
            data = self.client.student_grades(sid)
            self.store.cache_set(f"grades_{sid}", {"items": data})
            return data
        except Exception:
            cached = self.store.cache_get(f"grades_{sid}")
            return cached.get("items", []) if cached else []

    def fetch_missing(self):
        sid = self.current_student_id()
        if not sid:
            return []
        try:
            data = self.client.student_missing(sid)
            self.store.cache_set(f"missing_{sid}", {"items": data})
            return data
        except Exception:
            cached = self.store.cache_get(f"missing_{sid}")
            return cached.get("items", []) if cached else []

    def fetch_schedule(self):
        sid = self.current_student_id()
        if not sid:
            return []
        try:
            data = self.client.student_schedule(sid)
            self.store.cache_set(f"schedule_{sid}", {"items": data})
            return data
        except Exception:
            cached = self.store.cache_get(f"schedule_{sid}")
            return cached.get("items", []) if cached else []

    def fetch_credits(self):
        sid = self.current_student_id()
        if not sid:
            return {}
        try:
            data = self.client.student_credits(sid)
            self.store.cache_set(f"credits_{sid}", data)
            return data
        except Exception:
            return self.store.cache_get(f"credits_{sid}") or {}

    def fetch_medical(self):
        sid = self.current_student_id()
        try:
            if sid and self.user.get("role") in ("student", "parent"):
                return self.client.student_medical(sid)
            return self.client.my_medical()
        except Exception:
            return {}

    def fetch_emergency(self):
        sid = self.current_student_id()
        if not sid:
            return []
        try:
            return self.client.student_emergency(sid)
        except Exception:
            return []

    def fetch_behavior(self):
        sid = self.current_student_id()
        if not sid:
            return []
        try:
            return self.client.student_behavior(sid)
        except Exception:
            return []

    def fetch_sections(self):
        try:
            return self.client.teacher_sections()
        except Exception:
            return []

    def _register_device(self):
        token = self.store.get_device_token()
        if not token:
            token = str(uuid.uuid4())
            self.store.set_device_token(token)
        try:
            self.client.register_device(token, platform="kivy")
        except Exception:
            pass

    def fetch_unread_notifications(self) -> int:
        try:
            return self.client.unread_notification_count()
        except Exception:
            return 0

    def sync_offline_cache(self):
        """Prefetch key data for offline use in the Kivy app."""
        sid = self.current_student_id()
        if sid:
            self.fetch_grades()
            self.fetch_missing()
            self.fetch_schedule()
            self.fetch_credits()
        try:
            self.fetch_unread_notifications()
        except Exception:
            pass
