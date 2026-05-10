"""
Management command to diagnose Firebase configuration issues
Usage: python manage.py test_firebase_config
"""
from django.core.management.base import BaseCommand, CommandError
from shop.firebase_config import diagnose_firebase_config


class Command(BaseCommand):
    help = 'Diagnose Firebase configuration and test connectivity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-suggestions',
            action='store_true',
            help='Show detailed fix suggestions for any issues found',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Running Firebase Configuration Diagnostic...\n'))
        
        result = diagnose_firebase_config()
        
        if not result['database_url_set']:
            self.stdout.write(self.style.ERROR('\n❌ ERROR: Firebase Realtime Database URL is not configured!'))
            self.stdout.write(self.style.ERROR('''
To fix this issue, set the FIREBASE_DATABASE_URL environment variable:

1. Get your database URL from Firebase Console:
   - Go to Realtime Database
   - Copy the URL (format: https://PROJECT_ID.firebaseio.com)

2. Add to .env file:
   FIREBASE_DATABASE_URL=https://YOUR_PROJECT_ID.firebaseio.com

3. Or set via environment variable on your server:
   export FIREBASE_DATABASE_URL="https://YOUR_PROJECT_ID.firebaseio.com"

4. Restart your application
'''))
            raise CommandError('Firebase configuration incomplete')
        
        if not result['credentials_set']:
            self.stdout.write(self.style.ERROR('\n❌ ERROR: Firebase credentials are not configured!'))
            self.stdout.write(self.style.ERROR('''
To fix this issue, set Firebase credentials:

1. Download service account JSON from Firebase Console:
   - Go to Project Settings → Service Accounts
   - Click "Generate New Private Key"

2. Option A - Use credentials file:
   - Place JSON file in your project root
   - Set in .env: FIREBASE_CREDENTIALS=path/to/credentials.json

3. Option B - Use environment variables:
   - Set these from the JSON file:
   FIREBASE_PROJECT_ID=...
   FIREBASE_PRIVATE_KEY_ID=...
   FIREBASE_PRIVATE_KEY=...
   FIREBASE_CLIENT_EMAIL=...
   FIREBASE_CLIENT_ID=...

4. Restart your application
'''))
            raise CommandError('Firebase credentials incomplete')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Firebase configuration looks good!'))
        self.stdout.write(self.style.WARNING('\n📝 Note: Notifications are now using this configuration'))
