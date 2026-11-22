from django.urls import path
from rest_framework.routers import DefaultRouter

from . import management_api as management
from . import views
from .media import DownloadView, MediaView
from .spotlight_api import SpotlightDetailView, SpotlightListView, SpotlightViewSet

router = DefaultRouter()
router.register("management/events", management.EventsViewSet, basename="manage-events")
router.register("management/spotlights", SpotlightViewSet, basename="manage-spotlights")
router.register(
    "management/publications", management.PublicationsViewSet, basename="manage-publications"
)
router.register("management/members", management.MembersViewSet, basename="manage-members")
router.register("management/comments", management.ModerationViewSet, basename="manage-comments")

urlpatterns = [
    path("spotlights/", SpotlightListView.as_view()),
    path("spotlights/<uuid:pk>/", SpotlightDetailView.as_view()),
    path("management/dashboard/", management.DashboardView.as_view()),
    path("management/storage/", management.StorageView.as_view()),
    path("management/events/<uuid:pk>/sync/", management.SyncView.as_view()),
    path("management/events/<uuid:pk>/photos/", management.GalleryUploadView.as_view()),
    path("publications/<uuid:pk>/download/", DownloadView.as_view()),
    path("media/<str:token>/", MediaView.as_view()),
    path("feed/", views.FeedView.as_view()),
    path("events/", views.EventsView.as_view()),
    path("events/<uuid:pk>/", views.EventView.as_view()),
    path("publications/<uuid:pk>/", views.PublicationView.as_view()),
    path("publications/<uuid:pk>/comments/", views.CommentsView.as_view()),
    path("publications/<uuid:pk>/<str:action>/", views.ReactionView.as_view()),
    path("comments/<int:pk>/", views.CommentView.as_view()),
    path("comments/<int:pk>/like/", views.CommentUnlikeView.as_view()),
    path("members/<str:username>/", views.MemberProfileView.as_view()),
    path("members/<str:username>/saved/", views.SavedView.as_view()),
    path("members/<str:username>/follow/", views.FollowView.as_view()),
    path("connections/", views.ConnectionsView.as_view()),
    path("connections/<int:pk>/", views.ConnectionView.as_view()),
    path("me/avatar/", views.AvatarView.as_view()),
] + router.urls
