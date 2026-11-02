# config/views.py
import hmac
import os

from django.core.management import call_command
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "db_unavailable"}, status=503)

@csrf_exempt
@require_POST
def run_scheduled_tasks(request):
    expected = settings.CRON_TOKEN
    received = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not expected or not hmac.compare_digest(received, expected):
        return JsonResponse({"detail": "No autorizado."}, status=403)

    call_command("cleanup_expired_uploads")
    call_command("reconcile_subscriptions")
    return JsonResponse({"status": "ok"})