from kivymd.uix.screen import MDScreen

from kivy.properties import StringProperty





class SetupScreen(MDScreen):

    server_url = StringProperty("http://localhost")

    server_code = StringProperty("")

    district_name = StringProperty("")

    status = StringProperty("")



    def on_pre_enter(self):

        from services.config_store import ConfigStore



        store = ConfigStore()

        self.server_url = store.get_server_url()

        self.server_code = store.get_server_code()

        self.district_name = store.get_district_name()

        self.status = ""



    def save_server(self):

        from libregrades_sdk.client import LibreGradesClient

        from services.config_store import ConfigStore



        url = self.ids.server_input.text.strip().rstrip("/")

        if not url:

            self.status = "Enter a server URL."

            return

        try:

            info = LibreGradesClient(url).server_info()

        except Exception as exc:

            self.status = f"Could not reach server: {exc}"

            return



        code = info.get("server_code", "")

        district = info.get("district_name", "")

        if not code:

            self.status = "Server did not return a server code."

            return



        entered = self.ids.code_input.text.strip()

        if entered != code:

            self.status = f"Code mismatch. This server is {code}."

            return



        store = ConfigStore()

        store.set_server_url(url)

        store.set_server_identity(code, district)

        self.server_code = code

        self.district_name = district

        self.status = ""

        self.manager.current = "login"





class LoginScreen(MDScreen):

    error = StringProperty("")

    server_label = StringProperty("")



    def on_pre_enter(self):

        from services.config_store import ConfigStore



        store = ConfigStore()

        code = store.get_server_code()

        district = store.get_district_name()

        if code and district:

            self.server_label = f"{district} · Server {code}"

        elif code:

            self.server_label = f"Server {code}"

        else:

            self.server_label = store.get_server_url()



    def do_login(self):

        from main import app_model



        username = self.ids.username.text.strip()

        password = self.ids.password.text

        try:

            user = app_model.login(username, password)

            role = user.get("role")

            if role in ("teacher", "school_admin", "district_admin"):

                self.manager.current = "teacher"

            else:

                self.manager.current = "home"

            self.error = ""

        except Exception as e:

            self.error = str(e)

