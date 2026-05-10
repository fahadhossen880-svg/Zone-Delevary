from shop.translations import get_translation
import os

def language_context(request):
    """
    Add language and translation function to all templates
    """
    try:
        language = request.LANGUAGE_CODE or 'bn'
    except:
        language = 'bn'
    
    try:
        return {
            'current_language': language,
            'get_translation': lambda text: get_translation(text, language),
        }
    except Exception as e:
        # Fallback if anything goes wrong
        return {
            'current_language': 'bn',
            'get_translation': lambda text: text,
        }


def firebase_config(request):
    """
    Add Firebase configuration for web FCM
    """
    return {
        'firebase_config': {
            'api_key': os.getenv('FIREBASE_API_KEY', ''),
            'auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN', 'zone-delevary.firebaseapp.com'),
            'project_id': os.getenv('FIREBASE_PROJECT_ID', 'zone-delevary'),
            'storage_bucket': os.getenv('FIREBASE_STORAGE_BUCKET', 'zone-delevary.appspot.com'),
            'messaging_sender_id': os.getenv('FIREBASE_MESSAGING_SENDER_ID', ''),
            'app_id': os.getenv('FIREBASE_APP_ID', ''),
            'measurement_id': os.getenv('FIREBASE_MEASUREMENT_ID', ''),
            'vapid_key': os.getenv('FIREBASE_VAPID_KEY', ''),
        }
    }
