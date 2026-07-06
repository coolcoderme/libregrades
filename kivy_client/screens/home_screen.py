from kivymd.uix.screen import MDScreen

from kivymd.uix.button import MDFlatButton

from kivymd.uix.dialog import MDDialog





class HomeScreen(MDScreen):

    welcome_text = "LibreGrades"

    notification_label = "Notifications"



    def on_enter(self):

        from main import app_model



        name = app_model.user.get("full_name") or app_model.user.get("username", "")

        self.welcome_text = f"Welcome, {name}"

        count = app_model.fetch_unread_notifications()

        self.notification_label = f"Notifications ({count})" if count else "Notifications"



    def logout(self):

        from main import app_model



        app_model.logout()

        self.manager.current = "login"



    def go(self, screen_name):

        self.manager.current = screen_name

