from django.contrib import admin

from .models import Assignment, Grade, GradeCategory


@admin.register(GradeCategory)
class GradeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "weight")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "due_date", "max_points")


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("student", "assignment", "points", "is_missing")
