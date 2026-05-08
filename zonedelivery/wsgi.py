"""
WSGI config for zonedelivery project.
"""

import os
from django.core.wsgi import get_wsgi_application
from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zonedelivery.settings')

# Auto-run migrations and create admin on app startup in production
if os.getenv('RENDER') == 'True':
    try:
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
    except Exception as e:
        print(f"Migration warning (non-fatal): {e}")
    
    try:
        execute_from_command_line(['manage.py', 'create_admin_user'])
    except Exception as e:
        print(f"Admin creation warning (non-fatal): {e}")

application = get_wsgi_application()
