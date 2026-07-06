from django.contrib import admin

from . import models

admin.site.register(models.Rubric)
admin.site.register(models.LearningStandard)
admin.site.register(models.StudentGoal)
admin.site.register(models.InterventionPlan)
admin.site.register(models.FeedbackTicket)
admin.site.register(models.WebhookEndpoint)
