from django.urls import path

from .views import FaceSearchCreate, FaceSearchResults, FaceSearchStatus

urlpatterns = [
    path("events/<uuid:event_id>/face-search/", FaceSearchCreate.as_view()),
    path("face-search/<uuid:pk>/", FaceSearchStatus.as_view()),
    path("face-search/<uuid:pk>/results/", FaceSearchResults.as_view()),
]
