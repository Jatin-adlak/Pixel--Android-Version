"""Read-only connectivity check; never prints tokens or private keys."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from apps.community.media import drive_session

with drive_session() as session:
    for label, folder in [('Posts', '1Fq_95ZS0QFq31cuLXfDwkCda3OpODgkP'), ('Moments', '10Q0nvDwGMXU8Mc-o1U5QFaY_5r4p2Eqp')]:
        response = session.get(f'https://www.googleapis.com/drive/v3/files/{folder}', params={'fields': 'id,name,mimeType,capabilities(canAddChildren,canDownload)', 'supportsAllDrives': 'true'}, timeout=20)
        print(label, response.status_code, response.json().get('name', response.json().get('error', {}).get('status', 'unavailable')))
