from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.authentication import is_administrator

from .models import Comment, CommentLike, Event, Reaction
from .queries import MemberView, comment_data, content, ensure_pixel, event_data, page, visible


class FeedView(MemberView):
    def get(self, request):
        ensure_pixel(request.user)
        items = visible(request.user)
        for field in ["kind", "tag", "event_id"]:
            value = request.query_params.get(field)
            if value:
                if field == "event_id":
                    from uuid import UUID

                    try:
                        UUID(value)
                    except ValueError as exc:
                        raise ValidationError("Invalid event ID.") from exc
                items = items.filter(**{("tag__iexact" if field == "tag" else field): value})
        return page(request, items, lambda item: content(item, request.user))


class EventsView(MemberView):
    def get(self, request):
        items = Event.objects.filter(published=True, spotlight=False).order_by("-starts_at", "-id")
        if request.query_params.get("q"):
            items = items.filter(title__icontains=request.query_params["q"][:160])
        if request.query_params.get("tag"):
            items = items.filter(tag__iexact=request.query_params["tag"][:40])
        items = items.annotate(
            photo_count=Count(
                "publications",
                filter=Q(
                    publications__kind="photo",
                    publications__published=True,
                    publications__available=True,
                ),
            )
        )
        return page(request, items, lambda item: event_data(item, request.user))


class EventView(MemberView):
    def get(self, request, pk):
        return Response(event_data(get_object_or_404(Event, pk=pk, published=True), request.user))


class PublicationView(MemberView):
    def get(self, request, pk):
        return Response(content(get_object_or_404(visible(request.user), pk=pk), request.user))


class ReactionView(MemberView):
    def put(self, request, pk, action):
        return self.update(request, pk, action, True)

    def delete(self, request, pk, action):
        return self.update(request, pk, action, False)

    def update(self, request, pk, action, enabled):
        if action not in ["like", "save"]:
            raise ValidationError("Unknown action.")
        item = get_object_or_404(visible(request.user), pk=pk)
        if enabled:
            Reaction.objects.get_or_create(user=request.user, publication=item, action=action)
        else:
            Reaction.objects.filter(user=request.user, publication=item, action=action).delete()
        return Response(content(visible(request.user).get(pk=item.pk), request.user))


class CommentsView(MemberView):
    def get(self, request, pk):
        item = get_object_or_404(visible(request.user), pk=pk)
        comments = (
            item.comments.select_related("author", "author__profile_image")
            .annotate(
                total_likes=Count("likes"),
                viewer_liked=Exists(
                    CommentLike.objects.filter(comment_id=OuterRef("pk"), user=request.user)
                ),
            )
            .order_by("created_at", "id")
        )
        return page(request, comments, lambda c: comment_data(c, request.user))

    def post(self, request, pk):
        item = get_object_or_404(visible(request.user), pk=pk)
        text = request.data.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            raise ValidationError("Write a comment of 1–2000 characters.")
        parent = None
        if request.data.get("parent_id"):
            from rest_framework import serializers

            parent_id = serializers.IntegerField(min_value=1).run_validation(
                request.data["parent_id"]
            )
            parent = get_object_or_404(Comment, pk=parent_id, publication=item)
        comment = Comment.objects.create(
            publication=item, author=request.user, text=text.strip(), parent=parent
        )
        return Response(comment_data(comment, request.user), status=201)


class CommentView(MemberView):
    def delete(self, request, pk):
        item = get_object_or_404(Comment, pk=pk, publication__in=visible())
        if item.author != request.user and not is_administrator(request.user):
            raise PermissionDenied()
        item.delete()
        return Response(status=204)

    def put(self, request, pk):
        item = get_object_or_404(Comment, pk=pk, publication__in=visible())
        CommentLike.objects.get_or_create(user=request.user, comment=item)
        return Response(comment_data(item, request.user))


class CommentUnlikeView(MemberView):
    def delete(self, request, pk):
        item = get_object_or_404(Comment, pk=pk, publication__in=visible())
        item.likes.filter(user=request.user).delete()
        return Response(comment_data(item, request.user))
