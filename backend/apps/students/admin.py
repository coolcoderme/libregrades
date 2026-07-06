from django.contrib import admin

from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "student_id",
        "full_name_display",
        "school",
        "grade_level",
        "enrollment_status",
    )
    list_filter = ("school", "grade_level", "enrollment_status")
    search_fields = (
        "student_id",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )
    list_select_related = ("user", "school")
    ordering = ("school__name", "grade_level", "user__last_name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Student",
            {
                "fields": (
                    "user",
                    "student_id",
                    "school",
                    "grade_level",
                    "enrollment_status",
                    "photo",
                )
            },
        ),
        (
            "Demographics",
            {
                "fields": ("date_of_birth", "gender", "address"),
                "classes": ("collapse",),
            },
        ),
        (
            "Record info",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Name")
    def full_name_display(self, obj):
        return obj.full_name

    def has_module_permission(self, request):
        return request.user.is_staff
