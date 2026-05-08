web: gunicorn zonedelivery.wsgi:application --bind 0.0.0.0:$PORT --timeout 600 --workers 3
release: python manage.py migrate && python manage.py create_admin_user
