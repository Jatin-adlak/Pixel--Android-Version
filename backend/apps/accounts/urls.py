from django.urls import path

from . import views

urlpatterns = [
    path("auth/config/", views.ConfigView.as_view()),
    path("auth/register/", views.RegisterView.as_view()),
    path("auth/verify/", views.VerifyView.as_view()),
    path("auth/resend-verification/", views.ResendVerificationView.as_view()),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/refresh/", views.RefreshView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("auth/google/start/", views.GoogleStartView.as_view()),
    path("auth/google/callback/", views.GoogleCallbackView.as_view()),
    path("auth/google/exchange/", views.GoogleExchangeView.as_view()),
    path("me/", views.MeView.as_view()),
    path("me/username/", views.UsernameView.as_view()),
    path("me/profile/", views.ProfileView.as_view()),
    path("me/tour/", views.TourView.as_view()),
    path("users/", views.UserSearchView.as_view()),
    path("moments/", views.MomentsView.as_view()),
    path("users/<str:username>/", views.PublicProfileView.as_view()),
    path("management/status/", views.AdminStatusView.as_view()),
]
