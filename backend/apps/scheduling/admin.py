from django.contrib import admin

from .models import Course, Enrollment, Period, Section


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "school", "credit_value")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("course", "term", "section_number", "teacher")
    list_filter = ("term",)


admin.site.register(Period)
admin.site.register(Enrollment)
