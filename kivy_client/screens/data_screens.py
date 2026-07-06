from kivymd.uix.screen import MDScreen
from kivymd.uix.list import MDList, OneLineListItem
from kivy.clock import Clock
from kivy.properties import StringProperty


class GradesScreen(MDScreen):
    status = StringProperty("Loading...")

    def on_enter(self):
        Clock.schedule_once(lambda _: self.load_data(), 0)

    def load_data(self):
        from main import app_model

        items = app_model.fetch_grades()
        lst = self.ids.grade_list
        lst.clear_widgets()
        if not items:
            self.status = "No grades (offline cache may be empty)"
            return
        self.status = f"{len(items)} grade(s)"
        for g in items:
            title = g.get("assignment_title", "")
            score = g.get("points")
            max_pts = g.get("max_points")
            text = f"{g.get('course_code', '')} — {title}"
            if score is not None:
                text += f"  [{score}/{max_pts}]"
            elif g.get("is_missing"):
                text += "  [MISSING]"
            lst.add_widget(OneLineListItem(text=text))


class MissingScreen(MDScreen):
    status = StringProperty("Loading...")

    def on_enter(self):
        Clock.schedule_once(lambda _: self.load_data(), 0)

    def load_data(self):
        from main import app_model

        items = app_model.fetch_missing()
        lst = self.ids.missing_list
        lst.clear_widgets()
        self.status = f"{len(items)} missing assignment(s)"
        for m in items:
            lst.add_widget(
                OneLineListItem(
                    text=f"{m.get('course_code')} — {m.get('title')} (due {m.get('due_date')})"
                )
            )


class ScheduleScreen(MDScreen):
    def on_enter(self):
        Clock.schedule_once(lambda _: self.load_data(), 0)

    def load_data(self):
        from main import app_model

        items = app_model.fetch_schedule()
        lst = self.ids.schedule_list
        lst.clear_widgets()
        for e in items:
            sec = e.get("section", {})
            course = sec.get("course_code", "")
            period = sec.get("period_name", "")
            lst.add_widget(OneLineListItem(text=f"{period} — {course}"))


class CreditsScreen(MDScreen):
    summary_text = StringProperty("Loading...")

    def on_enter(self):
        Clock.schedule_once(lambda _: self.load_data(), 0)

    def load_data(self):
        from main import app_model

        data = app_model.fetch_credits()
        summary = data.get("summary", {})
        total = summary.get("total_credits", 0)
        required = summary.get("credits_required", 220)
        pct = summary.get("percent_complete", 0)
        self.summary_text = f"{total} / {required} credits ({pct:.0f}%)"
        lst = self.ids.credits_list
        lst.clear_widgets()
        for c in data.get("credits", []):
            lst.add_widget(
                OneLineListItem(
                    text=f"{c.get('course_code')} — {c.get('credits')} cr ({c.get('letter_grade')})"
                )
            )


class MedicalScreen(MDScreen):
    info_text = StringProperty("Loading...")

    def on_enter(self):
        Clock.schedule_once(lambda _: self.load_data(), 0)

    def load_data(self):
        from main import app_model

        data = app_model.fetch_medical()
        lines = []
        if data.get("doctor_name"):
            lines.append(f"Doctor: {data['doctor_name']} {data.get('doctor_phone', '')}")
        for a in data.get("allergies", []):
            allergen = a.get("allergen") if isinstance(a, dict) else a
            lines.append(f"Allergy: {allergen}")
        for m in data.get("medications", []):
            name = m.get("name") if isinstance(m, dict) else m
            lines.append(f"Med: {name}")
        self.info_text = "\n".join(lines) if lines else "No medical info on file."


class EmergencyScreen(MDScreen):
    def on_enter(self):
        Clock.schedule_once(lambda _: self.load_data(), 0)

    def load_data(self):
        from main import app_model

        items = app_model.fetch_emergency()
        lst = self.ids.emergency_list
        lst.clear_widgets()
        for c in items:
            lst.add_widget(
                OneLineListItem(
                    text=f"{c.get('name')} ({c.get('relationship')}) — {c.get('phone_primary')}"
                )
            )


class BehaviorScreen(MDScreen):
    def on_enter(self):
        Clock.schedule_once(lambda _: self.load_data(), 0)

    def load_data(self):
        from main import app_model

        items = app_model.fetch_behavior()
        lst = self.ids.behavior_list
        lst.clear_widgets()
        for i in items:
            lst.add_widget(
                OneLineListItem(
                    text=f"{i.get('incident_date')} — {i.get('incident_type')}: {i.get('description', '')[:40]}"
                )
            )


class TeacherSectionsScreen(MDScreen):
    def on_enter(self):
        Clock.schedule_once(lambda _: self.load_data(), 0)

    def load_data(self):
        from main import app_model

        items = app_model.fetch_sections()
        lst = self.ids.sections_list
        lst.clear_widgets()
        for s in items:
            lst.add_widget(
                OneLineListItem(
                    text=f"{s.get('course_code')} — Section {s.get('section_number')}",
                    on_release=lambda x, sid=s.get("id"): self.open_gradebook(sid),
                )
            )

    def open_gradebook(self, section_id):
        from kivymd.uix.dialog import MDDialog
        from main import app_model

        try:
            gb = app_model.client.section_gradebook(section_id)
            text = f"Gradebook: {gb.get('course')} — {len(gb.get('rows', []))} students"
        except Exception as e:
            text = f"Could not load gradebook: {e}"
        MDDialog(title="Gradebook", text=text).open()
