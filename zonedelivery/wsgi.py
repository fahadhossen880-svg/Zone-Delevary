"""
WSGI config for zonedelivery project.
"""

import os
from django.core.wsgi import get_wsgi_application
from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zonedelivery.settings')

# Auto-run migrations on app startup in production
if os.getenv('RENDER') == 'True':
    try:
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
    except Exception as e:
        print(f"Migration warning (non-fatal): {e}")

application = get_wsgi_application()
