import logging
from math import ceil

from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback
from rest_framework_simplejwt.exceptions import InvalidToken

logger = logging.getLogger(__name__)


def user_facing_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.error("Unhandled PIXEL API error", exc_info=exc)
        set_rollback()
        return Response(
            {"detail": "PIXEL couldn’t complete that request. Please try again in a moment."},
            status=500,
        )

    if isinstance(exc, (InvalidToken, exceptions.NotAuthenticated)):
        response.data["detail"] = "Please sign in to PIXEL again."
        response.data.pop("messages", None)
    elif isinstance(exc, Http404) or (
        isinstance(exc, exceptions.NotFound) and exc.detail == exc.default_detail
    ):
        response.data["detail"] = "This item is no longer available or you don’t have access to it."
    elif isinstance(exc, exceptions.PermissionDenied) and exc.detail == exc.default_detail:
        response.data["detail"] = "Your account doesn’t have permission to do this."
    elif isinstance(exc, (exceptions.ParseError, exceptions.UnsupportedMediaType)):
        response.data["detail"] = (
            "PIXEL couldn’t read what you sent. Check your input and try again."
        )
    elif isinstance(exc, exceptions.Throttled):
        message = (
            "Photo matching is busy."
            if exc.get_codes() == "face_search_busy"
            else "You’ve made too many attempts."
        )
        if exc.wait is not None:
            seconds = max(1, ceil(exc.wait))
            amount, unit = (ceil(seconds / 60), "minute") if seconds >= 60 else (seconds, "second")
            response.data["detail"] = (
                f"{message} Try again in {amount} {unit}{'s' if amount != 1 else ''}."
            )
        else:
            response.data["detail"] = f"{message} Wait a moment and try again."
    return response
