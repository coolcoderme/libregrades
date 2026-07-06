from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

import config.admin  # noqa: F401 — customize admin site branding

from apps.core.server_identity import server_info_payload


def health(_request):
    payload = {"status": "ok", "service": "libregrades", "framework": "django"}
    payload.update(server_info_payload())
    return JsonResponse(payload)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("", include("apps.portal.urls")),
    path("api/v1/", include("apps.core.api_urls")),
    path("api/v1/", include("apps.communications.api_urls")),
    path("api/v1/", include("apps.accounts.api_urls")),
    path("api/v1/", include("apps.students.api_urls")),
    path("api/v1/", include("apps.medical.api_urls")),
    path("api/v1/", include("apps.emergency.api_urls")),
    path("api/v1/", include("apps.scheduling.api_urls")),
    path("api/v1/", include("apps.grades.api_urls")),
    path("api/v1/", include("apps.credits.api_urls")),
    path("api/v1/", include("apps.attendance.api_urls")),
    path("api/v1/", include("apps.behavior.api_urls")),
    path("api/v1/", include("apps.notifications.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("", include("social_django.urls", namespace="social")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
