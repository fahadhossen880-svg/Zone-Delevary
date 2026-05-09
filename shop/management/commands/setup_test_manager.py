"""
Management command to setup test manager for notification testing
Run: python manage.py setup_test_manager
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shop.models import Zone, UserProfile


class Command(BaseCommand):
    help = 'Setup test manager for notification testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Setting up Test Manager ===\n'))
        
        # Get or create zone
        zone, created = Zone.objects.get_or_create(
            name='Test Zone',
            defaults={
                'delivery_charge': 50,
                'latitude': 23.8103,
                'longitude': 90.4125,
                'radius': 2000,
                'is_active': True
            }
        )
        self.stdout.write(f'✓ Zone: {zone.name}')
        
        # Check existing managers
        managers = User.objects.filter(profile__role='manager')
        self.stdout.write(f'\nExisting managers: {managers.count()}')
        for m in managers:
            zone_name = m.profile.zone_assigned.name if m.profile.zone_assigned else 'None'
            self.stdout.write(f'  - {m.username} (Zone: {zone_name})')
        
        # Create test manager if needed
        manager_user, created = User.objects.get_or_create(
            username='test_manager',
            defaults={'email': 'manager@test.com'}
        )
        
        if created:
            manager_user.set_password('password123')
            manager_user.save()
            self.stdout.write(self.style.SUCCESS('\n✓ Created test manager user'))
        
        # Create or get profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=manager_user,
            defaults={
                'role': 'manager',
                'zone_assigned': zone
            }
        )
        
        # Update profile with manager role and zone
        profile.role = 'manager'
        profile.zone_assigned = zone
        profile.save()
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Manager setup complete:'))
        self.stdout.write(f'  Username: test_manager')
        self.stdout.write(f'  Password: password123')
        self.stdout.write(f'  Zone: {zone.name}')
        self.stdout.write(f'  Email: manager@test.com')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Ready to test order notifications!'))
        self.stdout.write('Run: python manage.py test_order_notification')
