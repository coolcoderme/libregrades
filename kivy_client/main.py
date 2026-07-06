from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivy.lang import Builder
from pathlib import Path

from model.app_model import AppModel
from screens.auth_screens import LoginScreen, SetupScreen
from screens.data_screens import (
    BehaviorScreen,
    CreditsScreen,
    EmergencyScreen,
    GradesScreen,
    MedicalScreen,
    MissingScreen,
    ScheduleScreen,
    TeacherSectionsScreen,
)
from screens.home_screen import HomeScreen

app_model = AppModel()


class LibreGradesApp(MDApp):
    title = "LibreGrades"
    theme_cls_primary_palette = "Blue"

    def build(self):
        kv_path = Path(__file__).parent / "libregrades.kv"
        Builder.load_file(str(kv_path))
        sm = MDScreenManager()
        sm.add_widget(SetupScreen(name="setup"))
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(GradesScreen(name="grades"))
        sm.add_widget(MissingScreen(name="missing"))
        sm.add_widget(ScheduleScreen(name="schedule"))
        sm.add_widget(CreditsScreen(name="credits"))
        sm.add_widget(MedicalScreen(name="medical"))
        sm.add_widget(EmergencyScreen(name="emergency"))
        sm.add_widget(BehaviorScreen(name="behavior"))
        sm.add_widget(TeacherSectionsScreen(name="teacher"))

        from services.config_store import ConfigStore

        store = ConfigStore()
        if store.get_tokens()[0]:
            sm.current = "login"
        else:
            sm.current = "setup"
        return sm


if __name__ == "__main__":
    LibreGradesApp().run()
