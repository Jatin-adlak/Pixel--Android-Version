import hashlib
import time

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.throttling import BaseThrottle

from .authentication import is_administrator
from .models import (
    AuditLog,
    AuthSession,
    GoogleIdentity,
    Moment,
    PolicyAcceptance,
    User,
)


class PixelAdminSite(admin.AdminSite):
    site_header = "PIXEL Administration"
    site_title = "PIXEL"

    def get_urls(self):
        from django.urls import path

        from apps.community.drive_oauth import connect

        return [
            path("connect-drive/", self.admin_view(connect), name="connect_drive")
        ] + super().get_urls()

    def has_permission(self, request):
        return is_administrator(request.user)

    def login(self, request, extra_context=None):
        if request.method == "POST" and not self.has_permission(request):
            window = 300
            bucket, elapsed = divmod(int(time.time()), window)
            address = BaseThrottle().get_ident(request)
            identity = request.POST.get("username", "").strip().lower()[:254]
            for kind, value, limit in (("address", address, 30), ("account", identity, 10)):
                if not value:
                    continue
                digest = hashlib.sha256(value.encode()).hexdigest()
                key = f"pixel:admin-login:{kind}:{bucket}:{digest}"
                if not cache.add(key, 1, timeout=window + 1):
                    if cache.incr(key) > limit:
                        return HttpResponse(
                            "Too many sign-in attempts. Wait a few minutes and try again.",
                            status=429,
                            headers={
                                "Retry-After": str(window - elapsed),
                                "Cache-Control": "no-store",
                            },
                        )
        return super().login(request, extra_context)


site = PixelAdminSite(name="pixel_admin")


class AccountCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "role", "display_name")


class AccountChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User, site=site)
class AccountAdmin(UserAdmin):
    add_form = AccountCreationForm
    form = AccountChangeForm
    list_display = ("email", "username", "role", "email_verified", "is_active")
    list_filter = ("role", "email_verified", "is_active")
    search_fields = ("email", "username", "display_name")
    ordering = ("email",)
    fieldsets = (
        ("Identity", {"fields": ("email", "username", "password", "display_name")}),
        (
            "Profile",
            {"fields": ("department", "year", "bio", "profile_completed", "tour_completed")},
        ),
        (
            "Access",
            {
                "fields": (
                    "role",
                    "email_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"fields": ("email", "display_name", "role", "password1", "password2")}),
    )


class ReadOnlyRecordAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


for model in (AuditLog, AuthSession, PolicyAcceptance, GoogleIdentity):
    site.register(model, ReadOnlyRecordAdmin)


@admin.register(Moment, site=site)
class MomentAdmin(admin.ModelAdmin):
    list_display = ("title", "published", "created_at")
    list_filter = ("published",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        AuditLog.objects.create(
            actor=request.user, action="moment_updated" if change else "moment_created"
        )

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        AuditLog.objects.create(actor=request.user, action="moment_deleted")


# Secret-bearing verification/OAuth records are deliberately not exposed in Admin.
