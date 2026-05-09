"""
Management command to test order notification system
Run: python manage.py test_order_notification
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shop.models import Order, Zone, Notification
from shop.notification_service import update_order_notifications
import uuid


class Command(BaseCommand):
    help = 'Test order notification system for managers'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Order Notification Test ===\n'))
        
        # Check if zones exist
        zones = Zone.objects.filter(is_active=True)
        if not zones.exists():
            self.stdout.write(self.style.ERROR('❌ No active zones found. Create a zone first.'))
            return
        
        zone = zones.first()
        self.stdout.write(f'✓ Using zone: {zone.name}')
        
        # Check if managers exist for this zone
        managers = User.objects.filter(
            profile__role='manager',
            profile__zone_assigned=zone
        )
        self.stdout.write(f'ℹ Managers for {zone.name}: {managers.count()}')
        
        if managers.exists():
            for manager in managers:
                self.stdout.write(f'  - {manager.username} ({manager.email})')
        else:
            self.stdout.write(self.style.WARNING('  ⚠ No managers assigned to this zone!'))
        
        # Try to create a test order
        try:
            test_order = Order.objects.create(
                order_id=f"TEST-{uuid.uuid4().hex[:8].upper()}",
                zone=zone,
                customer_phone='01712345678',
                customer_email='test@example.com',
                customer_address='Test Address, Dhaka',
                total_amount=500,
                delivery_charge=zone.delivery_charge,
                payment_method='cash',
                status='pending'
            )
            self.stdout.write(f'✓ Test order created: {test_order.order_id}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to create test order: {str(e)}'))
            return
        
        # Trigger notification
        self.stdout.write('\n📢 Triggering manager notifications...')
        update_order_notifications(test_order, 'pending')
        
        # Check if notifications were created
        manager_notifications = Notification.objects.filter(
            order=test_order,
            notification_type='rider_assigned'
        )
        
        self.stdout.write(f'\n✓ Notifications created: {manager_notifications.count()}')
        
        if manager_notifications.exists():
            for notif in manager_notifications:
                sound_file = 'manager-order.mp3'
                email_status = '📧 (Email sent)' if notif.email_sent else '❌ (Email failed)'
                self.stdout.write(f'  - {notif.user.username}: {sound_file} {email_status}')
            self.stdout.write(self.style.SUCCESS('\n✅ Notification system working correctly!'))
        else:
            self.stdout.write(self.style.ERROR('❌ No notifications created. Check manager setup.'))
        
        # Cleanup test order
        test_order.delete()
        self.stdout.write(f'\nℹ Test order deleted.')
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Test Summary ==='))
        self.stdout.write(f'Zones: {zones.count()} active')
        self.stdout.write(f'Managers: {managers.count()}')
        self.stdout.write(f'Notifications created: {manager_notifications.count()}')
        self.stdout.write(f'Sound file: manager-order.mp3')
        self.stdout.write(f'Location: /media/notify/manager-order.mp3')
