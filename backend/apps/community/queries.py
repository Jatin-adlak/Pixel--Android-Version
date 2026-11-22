from django.conf import settings
from django.db.models import Count, Exists, OuterRef, Q
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.views import Onboarded, public_profile

from .models import Follow, ProfileImage, Publication, Reaction


def page(request, queryset, serialize):
    paginator = PageNumberPagination()
    items = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response([serialize(item) for item in items])


def visible(viewer=None):
    items = (
        Publication.objects.filter(published=True, available=True, event__published=True)
        .select_related("author", "author__profile_image", "event")
        .annotate(
            total_likes=Count("reactions", filter=Q(reactions__action="like"), distinct=True),
            total_comments=Count("comments", distinct=True),
        )
    )
    if viewer is not None:
        items = items.annotate(
            viewer_liked=Exists(
                Reaction.objects.filter(publication_id=OuterRef("pk"), user=viewer, action="like")
            ),
            viewer_saved=Exists(
                Reaction.objects.filter(publication_id=OuterRef("pk"), user=viewer, action="save")
            ),
        )
    return items.order_by("-created_at", "-id")


def identity(user, viewer=None):
    try:
        avatar = user.profile_image.url
        if user.profile_image.drive_file_id:
            from .media import delivery_url

            avatar = delivery_url(user.profile_image, viewer or user, "thumbnail")
    except ProfileImage.DoesNotExist:
        avatar = ""
    return {
        **public_profile(user),
        "avatar_url": avatar,
    }


def content(item, viewer):
    from .media import delivery_url
    from .post_media import images

    if not hasattr(item, "viewer_liked"):
        item = visible(viewer).get(pk=item.pk)
    return {
        "id": str(item.id),
        "kind": item.kind,
        "images": images(item, viewer),
        "image_width": item.image_dimensions.get(item.drive_file_id, {}).get("width"),
        "image_height": item.image_dimensions.get(item.drive_file_id, {}).get("height"),
        "title": item.title,
        "caption": item.caption,
        "tag": item.tag,
        "cover_url": item.cover_url
        or (
            delivery_url(item, viewer, "thumbnail")
            if item.drive_file_id or item.cover_drive_file_id
            else item.preview_url
        ),
        "preview_url": delivery_url(item, viewer, "preview")
        if item.drive_file_id
        else item.preview_url,
        "video_url": delivery_url(item, viewer, "play") if item.drive_file_id else item.preview_url,
        "event_id": str(item.event_id),
        "event_title": item.event.title,
        "author": identity(item.author),
        "created_at": item.created_at,
        "like_count": item.total_likes,
        "comment_count": item.total_comments,
        "liked": item.viewer_liked,
        "saved": item.viewer_saved,
    }


def event_data(item, viewer=None):
    result = {
        key: getattr(item, key)
        for key in [
            "id",
            "title",
            "tag",
            "description",
            "venue",
            "starts_at",
            "ends_at",
            "cover_url",
            "form_url",
        ]
    }
    if item.cover_drive_file_id and viewer is not None:
        from .media import delivery_url

        result["cover_url"] = delivery_url(item, viewer, "thumbnail")
    if hasattr(item, "publications"):
        result["photo_count"] = item.publications.filter(
            kind="photo", published=True, available=True
        ).count()
    return result


def ensure_pixel(user):
    pixel = User.objects.filter(
        email=settings.MAIN_ADMIN_EMAIL, is_active=True, email_verified=True, role="Administrator"
    ).first()
    if pixel and pixel != user:
        Follow.objects.update_or_create(
            follower=user, target=pixel, defaults={"accepted": True, "mandatory": True}
        )


class MemberView(APIView):
    permission_classes = [Onboarded]


def comment_data(item, viewer):
    return {
        "id": item.id,
        "text": item.text,
        "parent_id": item.parent_id,
        "author": identity(item.author),
        "created_at": item.created_at,
        "like_count": item.likes.count(),
        "liked": item.likes.filter(user=viewer).exists(),
        "can_delete": viewer == item.author or viewer.role == "Administrator",
    }


def profile_data(user, viewer):
    ensure_pixel(user)
    relation = Follow.objects.filter(follower=viewer, target=user).first()
    saved = Reaction.objects.filter(user=user, action="save", publication__in=visible())
    if user != viewer and not (relation and relation.accepted):
        saved = saved.exclude(publication__kind="photo")
    return {
        **identity(user, viewer),
        "saved_count": saved.count(),
        "followers": user.incoming_follows.filter(accepted=True).count(),
        "following": user.outgoing_follows.filter(accepted=True).count(),
        "follow_state": "accepted"
        if relation and relation.accepted
        else "pending"
        if relation
        else "none",
        "mandatory": bool(relation and relation.mandatory),
        "can_see_photos": viewer == user or bool(relation and relation.accepted),
    }
