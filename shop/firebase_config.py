import os
import firebase_admin
from firebase_admin import credentials, storage, db
from decouple import config

# Firebase configuration
FIREBASE_DATABASE_URL = config('FIREBASE_DATABASE_URL', default='')
FIREBASE_CREDENTIALS_PATH = config('FIREBASE_CREDENTIALS', default='').strip()
FIREBASE_PROJECT_ID = config('FIREBASE_PROJECT_ID', default='')
FIREBASE_PRIVATE_KEY_ID = config('FIREBASE_PRIVATE_KEY_ID', default='')
FIREBASE_PRIVATE_KEY = config('FIREBASE_PRIVATE_KEY', default='')
FIREBASE_CLIENT_EMAIL = config('FIREBASE_CLIENT_EMAIL', default='')
FIREBASE_CLIENT_ID = config('FIREBASE_CLIENT_ID', default='')
FIREBASE_AUTH_URI = config('FIREBASE_AUTH_URI', default='https://accounts.google.com/o/oauth2/auth')
FIREBASE_TOKEN_URI = config('FIREBASE_TOKEN_URI', default='https://oauth2.googleapis.com/token')
FIREBASE_AUTH_PROVIDER_X509_CERT_URL = config('FIREBASE_AUTH_PROVIDER_X509_CERT_URL', default='https://www.googleapis.com/oauth2/v1/certs')
FIREBASE_CLIENT_X509_CERT_URL = config('FIREBASE_CLIENT_X509_CERT_URL', default='')
FIREBASE_UNIVERSE_DOMAIN = config('FIREBASE_UNIVERSE_DOMAIN', default='googleapis.com')


def normalize_url(value, default=None):
    if not value:
        return default

    value = value.strip().strip('"').strip("'")

    if value.startswith('https://') or value.startswith('http://'):
        return value
    if value.startswith('https:/') and not value.startswith('https://'):
        return 'https://' + value[len('https:/'):].lstrip('/')
    if value.startswith('http:/') and not value.startswith('http://'):
        return 'http://' + value[len('http:/'):].lstrip('/')
    if value.startswith('//'):
        return 'https:' + value
    if value.startswith('/'):
        return f'https://{value.lstrip('/')}'

    return value


def _guess_database_url():
    if FIREBASE_DATABASE_URL:
        return normalize_url(FIREBASE_DATABASE_URL)

    if FIREBASE_PROJECT_ID:
        # Try the old Realtime DB URL pattern. If your project uses the newer default
        # Realtime DB domain, set FIREBASE_DATABASE_URL explicitly in .env.
        return f'https://{FIREBASE_PROJECT_ID}.firebaseio.com'

    return None

FIREBASE_DATABASE_URL = _guess_database_url()
if FIREBASE_DATABASE_URL:
    print(f'🔌 Firebase Realtime Database URL resolved as: {FIREBASE_DATABASE_URL}')
else:
    print('⚠️ Firebase Realtime Database URL is not configured; realtime DB writes will fail.')


def _resolve_service_account_path(path):
    if not path:
        return None

    if os.path.isabs(path) and os.path.exists(path):
        return path

    candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', path))
    if os.path.exists(candidate):
        return candidate

    if os.path.exists(path):
        return path

    return None


def _build_service_account_info():
    private_key = FIREBASE_PRIVATE_KEY.strip().strip('"').strip("'")
    if private_key:
        return {
            'type': 'service_account',
            'project_id': FIREBASE_PROJECT_ID,
            'private_key_id': FIREBASE_PRIVATE_KEY_ID,
            'private_key': private_key.replace('\\n', '\n'),
            'client_email': FIREBASE_CLIENT_EMAIL,
            'client_id': FIREBASE_CLIENT_ID,
            'auth_uri': normalize_url(FIREBASE_AUTH_URI, 'https://accounts.google.com/o/oauth2/auth'),
            'token_uri': normalize_url(FIREBASE_TOKEN_URI, 'https://oauth2.googleapis.com/token'),
            'auth_provider_x509_cert_url': normalize_url(FIREBASE_AUTH_PROVIDER_X509_CERT_URL, 'https://www.googleapis.com/oauth2/v1/certs'),
            'client_x509_cert_url': normalize_url(FIREBASE_CLIENT_X509_CERT_URL),
            'universe_domain': FIREBASE_UNIVERSE_DOMAIN,
        }
    return None


FIREBASE_CREDENTIALS_FILE = _resolve_service_account_path(FIREBASE_CREDENTIALS_PATH)

# Initialize Firebase (শুধু একবার initialize করুন)
try:
    firebase_admin.get_app()
except ValueError:
    try:
        if FIREBASE_CREDENTIALS_FILE:
            creds = credentials.Certificate(FIREBASE_CREDENTIALS_FILE)
        else:
            service_account_info = _build_service_account_info()
            if not service_account_info:
                raise ValueError('Firebase service account credentials are not configured')
            creds = credentials.Certificate(service_account_info)

        options = {
            'storageBucket': 'zone-delevary.appspot.com'
        }
        if FIREBASE_DATABASE_URL:
            options['databaseURL'] = FIREBASE_DATABASE_URL

        firebase_admin.initialize_app(creds, options)
        print('✅ Firebase initialized successfully!')
        if FIREBASE_DATABASE_URL:
            print(f'   Realtime DB: {FIREBASE_DATABASE_URL}')
    except Exception as e:
        print(f'❌ Firebase initialization error: {e}')


def get_firebase_bucket():
    """Firebase storage bucket return করুন"""
    try:
        return storage.bucket()
    except Exception as e:
        print(f"Error getting Firebase bucket: {e}")
        return None


def get_firebase_db_ref(path=None):
    """Firebase Realtime Database reference return করুন"""
    if not FIREBASE_DATABASE_URL:
        print("Firebase Realtime Database URL not configured.")
        return None

    try:
        return db.reference(path or '/')
    except Exception as e:
        print(f"Error getting Firebase DB reference ({path or '/'}), URL={FIREBASE_DATABASE_URL}: {e}")
        return None


def push_realtime_notification(notification):
    """একটি notification কে Firebase Realtime DB এ push করুন"""
    if not FIREBASE_DATABASE_URL:
        print(f"⚠️  Firebase Realtime Database not configured. Skipping notification sync for {notification.id}")
        return False
    
    try:
        ref = get_firebase_db_ref(f'notifications/{notification.user_id}/{notification.id}')
        if not ref:
            print(f"❌ Failed to get Firebase DB reference for notification {notification.id}")
            return False

        data = {
            'id': notification.id,
            'user_id': notification.user_id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'order_id': notification.order.order_id if notification.order else None,
            'is_read': notification.is_read,
            'is_deleted': notification.is_deleted,
            'read_at': notification.read_at.isoformat() if notification.read_at else None,
            'created_at': notification.created_at.isoformat() if notification.created_at else None,
        }
        ref.set(data)
        print(f"✅ Firebase notification synced: {notification.id}")
        return True
    except Exception as e:
        print(f"❌ Firebase push notification error for ID {notification.id}: {type(e).__name__}: {str(e)}")
        print(f"   Database URL: {FIREBASE_DATABASE_URL}")
        print(f"   Notification: {notification.title}")
        return False


def update_realtime_notification_status(notification):
    """Read / status update sync করুন Firebase Realtime DB এ"""
    if not FIREBASE_DATABASE_URL:
        print(f"⚠️  Firebase Realtime Database not configured. Skipping status update for {notification.id}")
        return False
    
    try:
        ref = get_firebase_db_ref(f'notifications/{notification.user_id}/{notification.id}')
        if not ref:
            print(f"❌ Failed to get Firebase DB reference for updating notification {notification.id}")
            return False

        ref.update({
            'is_read': notification.is_read,
            'read_at': notification.read_at.isoformat() if notification.read_at else None,
            'is_deleted': notification.is_deleted,
        })
        print(f"✅ Firebase notification status updated: {notification.id}")
        return True
    except Exception as e:
        print(f"❌ Firebase update notification status error for ID {notification.id}: {type(e).__name__}: {str(e)}")
        return False


def set_user_location(user_id, latitude, longitude, is_in_service, zones=None):
    """ব্যবহারকারীর location data Firebase Realtime DB এ আপডেট করুন"""
    try:
        if not user_id:
            return False

        ref = get_firebase_db_ref(f'locations/{user_id}')
        if not ref:
            return False

        data = {
            'latitude': latitude,
            'longitude': longitude,
            'is_in_service': is_in_service,
            'zones': zones or [],
            'last_checked': db.SERVER_TIMESTAMP,
        }
        ref.set(data)
        return True
    except Exception as e:
        print(f"Firebase set user location error: {e}")
        return False


def push_notification_preferences(user):
    """User notification preferences Firebase Realtime DB এ sync করুন"""
    try:
        if not user or not hasattr(user, 'notification_preference'):
            return False

        prefs = user.notification_preference
        ref = get_firebase_db_ref(f'user_preferences/{user.id}')
        if not ref:
            return False

        ref.set({
            'order_updates': prefs.order_updates,
            'order_confirmation': prefs.order_confirmation,
            'rider_assignments': prefs.rider_assignments,
            'general_notifications': prefs.general_notifications,
            'email_on_order_updates': prefs.email_on_order_updates,
            'email_on_delivery': prefs.email_on_delivery,
            'email_on_cancellation': prefs.email_on_cancellation,
            'email_digests': prefs.email_digests,
            'enable_sound': prefs.enable_sound,
            'enable_browser_notifications': prefs.enable_browser_notifications,
            'quiet_hours_enabled': prefs.quiet_hours_enabled,
            'quiet_hours_start': prefs.quiet_hours_start.isoformat() if prefs.quiet_hours_start else None,
            'quiet_hours_end': prefs.quiet_hours_end.isoformat() if prefs.quiet_hours_end else None,
            'updated_at': prefs.updated_at.isoformat() if prefs.updated_at else None,
        })
        return True
    except Exception as e:
        print(f"Firebase push notification preferences error: {e}")
        return False


def upload_to_firebase(file, destination_path):
    """
    Firebase এ file upload করুন
    
    Args:
        file: Django UploadedFile object
        destination_path: Firebase এ file path (e.g., 'products/image.jpg')
    
    Returns:
        Public URL অথবা None (error হলে)
    """
    try:
        bucket = get_firebase_bucket()
        if not bucket:
            return None
        
        blob = bucket.blob(destination_path)
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Public URL তৈরি করুন
        file.seek(0)  # Reset file pointer
        return f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{destination_path}?alt=media"
    
    except Exception as e:
        print(f"Firebase upload error: {e}")
        return None


def delete_from_firebase(destination_path):
    """Firebase থেকে file delete করুন"""
    try:
        bucket = get_firebase_bucket()
        if bucket:
            blob = bucket.blob(destination_path)
            blob.delete()
            return True
    except Exception as e:
        print(f"Firebase delete error: {e}")
    
    return False


def diagnose_firebase_config():
    """
    Firebase configuration की diagnostic report generate करें
    Server में Firebase issues debug करने के लिए उपयोगी
    """
    print("\n" + "="*60)
    print("🔍 FIREBASE CONFIGURATION DIAGNOSTIC REPORT")
    print("="*60)
    
    print("\n1️⃣  ENVIRONMENT VARIABLES:")
    print(f"   ✓ FIREBASE_PROJECT_ID: {'✅ SET' if FIREBASE_PROJECT_ID else '❌ NOT SET'}")
    print(f"   ✓ FIREBASE_DATABASE_URL: {'✅ SET' if FIREBASE_DATABASE_URL else '❌ NOT SET'}")
    if FIREBASE_DATABASE_URL:
        print(f"      → {FIREBASE_DATABASE_URL}")
    print(f"   ✓ FIREBASE_CLIENT_EMAIL: {'✅ SET' if FIREBASE_CLIENT_EMAIL else '❌ NOT SET'}")
    print(f"   ✓ FIREBASE_PRIVATE_KEY: {'✅ SET (****)' if FIREBASE_PRIVATE_KEY else '❌ NOT SET'}")
    print(f"   ✓ FIREBASE_CREDENTIALS_FILE: {'✅ ' + FIREBASE_CREDENTIALS_FILE if FIREBASE_CREDENTIALS_FILE else '❌ NOT SET'}")
    
    print("\n2️⃣  FIREBASE INITIALIZATION:")
    try:
        app = firebase_admin.get_app()
        print(f"   ✅ Firebase App initialized: {app.project_id if hasattr(app, 'project_id') else 'OK'}")
    except Exception as e:
        print(f"   ❌ Firebase App not initialized: {e}")
    
    print("\n3️⃣  DATABASE CONNECTIVITY TEST:")
    try:
        ref = get_firebase_db_ref('_test_connection')
        if ref:
            ref.set({'test': 'connection', 'timestamp': str(__import__('datetime').datetime.now())})
            print(f"   ✅ Database write test: SUCCESS")
            ref.delete()
        else:
            print(f"   ❌ Database reference is None")
    except Exception as e:
        print(f"   ❌ Database connectivity error: {type(e).__name__}: {str(e)}")
    
    print("\n4️⃣  STORAGE CONNECTIVITY TEST:")
    try:
        bucket = get_firebase_bucket()
        if bucket:
            print(f"   ✅ Storage bucket accessible: {bucket.name}")
        else:
            print(f"   ❌ Storage bucket is None")
    except Exception as e:
        print(f"   ❌ Storage connectivity error: {type(e).__name__}: {str(e)}")
    
    print("\n" + "="*60)
    print("⚠️  FIXES FOR COMMON ISSUES:")
    print("="*60)
    print("""
If you see 404 errors:
1. Check FIREBASE_DATABASE_URL format: https://PROJECT_ID.firebaseio.com
2. Verify FIREBASE_PROJECT_ID is correct in Firebase Console
3. Ensure Realtime Database is enabled in Firebase Console
4. Check Firebase Security Rules allow read/write from your app

If credentials are not set:
1. Download service account JSON from Firebase Console
2. Set FIREBASE_CREDENTIALS path, or set individual env variables
3. Restart the application

To enable realtime notifications:
1. Create Realtime Database in Firebase Console (Asia region recommended)
2. Set proper Security Rules:
   {
     "rules": {
       "notifications": {
         "$uid": {
           ".read": "$uid === auth.uid",
           ".write": "root.child('users').child(auth.uid).child('role').val() === 'admin' || $uid === auth.uid"
         }
       }
     }
   }
""")
    print("="*60 + "\n")
    
    return {
        'project_id_set': bool(FIREBASE_PROJECT_ID),
        'database_url_set': bool(FIREBASE_DATABASE_URL),
        'database_url': FIREBASE_DATABASE_URL,
        'credentials_set': bool(FIREBASE_CLIENT_EMAIL and FIREBASE_PRIVATE_KEY),
    }
