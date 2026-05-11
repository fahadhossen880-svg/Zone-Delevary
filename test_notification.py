#!/usr/bin/env python
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zonedelivery.settings')
django.setup()

from django.contrib.auth.models import User
from shop.notification_service import create_notification

def test_notification():
    try:
        # Get first user
        user = User.objects.first()
        if not user:
            print("❌ No users found")
            return

        print(f"✅ Testing with user: {user.username}")

        # Create test notification
        notif = create_notification(
            user=user,
            notification_type='general',
            title='🔔 Test Notification with Sound',
            message='This should play sound when viewed!',
        )

        if notif:
            print(f"✅ Notification created: ID {notif.id}")
            print(f"   Title: {notif.title}")
            print(f"   Message: {notif.message}")
            print("   Sound file: manager-order.mp3 (will play on frontend)")
        else:
            print("❌ Failed to create notification")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_notification()