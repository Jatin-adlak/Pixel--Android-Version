"""Administrator initiated Drive authorization, separate from member sign-in."""

import json
import os
import secrets
import time
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect

from apps.accounts.models import User
from apps.accounts.services import challenge


def connect(request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return HttpResponseBadRequest("Configure the backend Google OAuth client first.")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    request.session["drive_oauth"] = {
        "state": state,
        "verifier": verifier,
        "actor": str(request.user.pk),
        "started": time.time(),
    }
    return HttpResponseRedirect(
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(
            {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "response_type": "code",
                "scope": "https://www.googleapis.com/auth/drive",
                "access_type": "offline",
                "prompt": "consent select_account",
                "state": state,
                "code_challenge": challenge(verifier),
                "code_challenge_method": "S256",
            }
        )
    )


def finish(request):
    attempt = request.session.pop("drive_oauth", None)
    if not attempt or not secrets.compare_digest(attempt["state"], request.GET.get("state", "")):
        return HttpResponseBadRequest("Drive authorization has expired. Start again from Admin.")
    if (
        time.time() - attempt["started"] > 600
        or request.session.get("_auth_user_id") != attempt["actor"]
    ):
        return HttpResponseBadRequest("Sign in to Admin and start Drive authorization again.")
    actor = User.objects.filter(
        pk=attempt["actor"],
        is_active=True,
        is_staff=True,
        email_verified=True,
        role="Administrator",
    ).first()
    if not actor or request.GET.get("error") or not request.GET.get("code"):
        return HttpResponseBadRequest("Drive authorization was not completed.")
    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": request.GET["code"],
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
                "code_verifier": attempt["verifier"],
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("refresh_token"):
            return HttpResponseBadRequest(
                "Google did not issue offline access. Start authorization again."
            )
        path = settings.BASE_DIR / ".local" / "drive-oauth.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "type": "authorized_user",
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "refresh_token": payload["refresh_token"],
                }
            ),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except (requests.RequestException, ValueError, OSError):
        return HttpResponseBadRequest("Could not complete Drive authorization. Please try again.")
    from apps.accounts.models import AuditLog

    AuditLog.objects.create(actor=actor, action="drive_account_connected")
    return HttpResponseRedirect("/admin/community/publication/add/")
