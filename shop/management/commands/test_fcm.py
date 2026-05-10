from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shop.firebase_config import send_fcm_notification_to_user, register_device_token
from shop.models import DeviceToken


class Command(BaseCommand):
    help = 'Test FCM notification functionality'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username to send test notification to')
        parser.add_argument('--token', type=str, help='FCM device token to register/test')
        parser.add_argument('--register-only', action='store_true', help='Only register token, don\'t send notification')

    def handle(self, *args, **options):
        username = options.get('username')
        token = options.get('token')
        register_only = options.get('register_only')

        if not username:
            self.stdout.write(self.style.ERROR('Please provide --username'))
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} not found'))
            return

        if token:
            # Register the device token
            device_token = register_device_token(user, token, 'android')
            if device_token:
                self.stdout.write(self.style.SUCCESS(f'Device token registered for {username}'))
            else:
                self.stdout.write(self.style.ERROR('Failed to register device token'))
                return

        if register_only:
            return

        # Send test FCM notification
        self.stdout.write(f'Sending test FCM notification to {username}...')
        successful_sends = send_fcm_notification_to_user(
            user=user,
            title='Test FCM Notification',
            body='This is a test push notification from ZoneDelivery',
            data={'test': 'true', 'timestamp': 'now'}
        )

        if successful_sends:
            self.stdout.write(self.style.SUCCESS(f'FCM notification sent successfully to {len(successful_sends)} device(s)'))
        else:
            self.stdout.write(self.style.WARNING('No FCM notifications were sent (no active tokens or all failed)'))

        # Show current device tokens
        tokens = DeviceToken.objects.filter(user=user, is_active=True)
        self.stdout.write(f'\nActive device tokens for {username}: {tokens.count()}')
        for token_obj in tokens:
            self.stdout.write(f'  - {token_obj.platform}: {token_obj.token[:20]}...')