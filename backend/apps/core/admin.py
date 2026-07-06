from django.contrib import admin

from .models import AcademicYear, District, School, ServerIdentity, Term


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "code")
    list_filter = ("district",)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "start_date", "end_date", "is_current")


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "start_date", "end_date", "is_current")
    list_filter = ("school",)


@admin.register(ServerIdentity)
class ServerIdentityAdmin(admin.ModelAdmin):
    list_display = ("code", "created_at")
    readonly_fields = ("code", "created_at", "updated_at")

    def has_add_permission(self, request):
        return not ServerIdentity.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
