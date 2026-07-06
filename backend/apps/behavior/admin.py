from django.contrib import admin

from .models import BehaviorIncident


@admin.register(BehaviorIncident)
class BehaviorIncidentAdmin(admin.ModelAdmin):
    list_display = ("student", "incident_date", "incident_type", "parent_visible")
