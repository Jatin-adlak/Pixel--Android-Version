from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.html import format_html


def csrf_failure(request, reason=""):
    embedded = request.headers.get("Origin") == "null"
    explanation = (
        "The browser submitted no page origin. Reload the Admin login page to load the current security policy, then sign in again. If this continues in an embedded browser, use a normal Chrome or Edge window."
        if embedded
        else "Reload the login page and try again. Keep cookies enabled and use the same localhost address throughout."
    )
    return HttpResponseForbidden(
        format_html(
            '<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PIXEL — sign in again</title><body style="background:#181A1D;color:#F7F4EB;font:16px system-ui;padding:40px;max-width:660px;margin:auto"><h1>Let’s reconnect.</h1><p>{}</p><p><a style="color:#93B4FF" href="{}/admin/">Open PIXEL Admin</a></p></body></html>',
            explanation,
            settings.BACKEND_URL,
        )
    )
