from django.http import JsonResponse
from django.urls import include, path

from apps.accounts.admin import site

urlpatterns = [
    path("health/", lambda request: JsonResponse({"status": "ok"})),
    path("admin/", site.urls),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.community.urls")),
    path("api/v1/", include("apps.face_search.urls")),
]
