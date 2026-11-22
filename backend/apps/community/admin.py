from django.contrib import admin

from apps.accounts.admin import site
from apps.accounts.models import AuditLog

from .forms import EventForm, PublicationForm
from .models import DriveFolder, Event, Publication, Spotlight


class ContentAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if isinstance(obj, Publication):
            obj.author = request.user
        obj.full_clean()
        super().save_model(request, obj, form, change)
        AuditLog.objects.create(actor=request.user, action=f"{obj._meta.model_name}_saved")


@admin.register(Event, site=site)
class EventAdmin(ContentAdmin):
    form = EventForm
    actions = ["sync_photographs"]
    exclude = ["spotlight"]
    list_display = ["title", "tag", "starts_at", "published"]
    list_filter = ["published", "tag"]
    search_fields = ["title"]

    @admin.action(description="Sync photographs from linked Drive folders")
    def sync_photographs(self, request, queryset):
        from .synchronization import synchronize

        for event in queryset:
            try:
                count = synchronize(event, request.user)
                self.message_user(request, f"{event.title}: {count} photographs synchronized.")
            except Exception:
                self.message_user(
                    request,
                    f"{event.title}: sync failed; check folder access and server configuration.",
                    level="ERROR",
                )


@admin.register(Publication, site=site)
class PublicationAdmin(ContentAdmin):
    form = PublicationForm
    exclude = ["author"]
    list_display = ["title", "kind", "event", "published", "created_at"]
    list_filter = ["kind", "published", "tag"]
    search_fields = ["title", "event__title"]


site.register(DriveFolder, ContentAdmin)
site.register(Spotlight, ContentAdmin)
