from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

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
        user = request.user
        return bool(
            user.is_active
            and user.is_staff
            and user.email_verified
            and user.role == User.Role.ADMINISTRATOR
        )


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
