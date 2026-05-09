from pathlib import Path
import os
from decouple import config, Csv
import cloudinary
import cloudinary.uploader

# Conditional import for dj-database-url
try:
    import dj_database_url
except ImportError:
    dj_database_url = None

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# Environment Detection
IS_RENDER = os.getenv('RENDER') == 'True'
IS_PRODUCTION = IS_RENDER or os.getenv('ENVIRONMENT') == 'production'

# ============ SECRET KEY CONFIGURATION ============
# Set SECRET_KEY in environment variables for production
SECRET_KEY = config('SECRET_KEY', default='')

# ============ ADMIN LOGIN CONFIGURATION ============
# These values can be set in .env and used to bootstrap a default admin user.
ADMIN_USERNAME = config('ADMIN_USERNAME', default=None)
ADMIN_PASSWORD = config('ADMIN_PASSWORD', default=None)
ADMIN_EMAIL = config('ADMIN_EMAIL', default='admin@example.com')
ADMIN_CREATE_DEFAULT = config('ADMIN_CREATE_DEFAULT', default=False, cast=bool)

DEBUG = config('DEBUG', default=False if IS_PRODUCTION else True, cast=bool)

# Allowed Hosts Configuration
if IS_PRODUCTION:
    # Render production - read from environment variables
    env_hosts = os.getenv('ALLOWED_HOSTS', 'zone-delevary.onrender.com,zonedelevary.store,www.zonedelevary.store')
    ALLOWED_HOSTS = [host.strip() for host in env_hosts.split(',')]
else:
    # Development (ngrok, localhost)
    ALLOWED_HOSTS = [
        'localhost',
        '127.0.0.1',
        'zone-delevary.onrender.com',
        'zonedelevary.store',
        'www.zonedelevary.store',
    ]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',  # Cloudinary SDK
    'shop',
    'django_bootstrap5',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'zonedelivery.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': not IS_PRODUCTION,  # False in production when using custom loaders
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.csrf',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'shop.context_processors.language_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'zonedelivery.wsgi.application'

# ============ AUTHENTICATION CONFIGURATION ============
# Custom admin login and redirect URLs
LOGIN_URL = 'login'  # Use shop login page
LOGIN_REDIRECT_URL = 'home'  # Redirect to home after login

# ============ CACHING CONFIGURATION ============
redis_url = os.getenv('REDIS_URL')
if IS_PRODUCTION and redis_url:
    # Production with Redis
    try:
        CACHES = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': redis_url,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    'CONNECTION_POOL_KWARGS': {'max_connections': 50, 'retry_on_timeout': True},
                    'SOCKET_CONNECT_TIMEOUT': 5,
                    'SOCKET_TIMEOUT': 5,
                    'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
                }
            }
        }
    except Exception as e:
        # Fallback to database cache if Redis fails
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
                'LOCATION': 'django_cache_table',
            }
        }
else:
    # Development or no Redis - use appropriate cache backend
    if IS_PRODUCTION:
        # Production without Redis - use database cache
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
                'LOCATION': 'django_cache_table',
            }
        }
    else:
        # Development - use local memory cache
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'unique-snowflake',
                'TIMEOUT': 300,
            }
        }

# Session configuration - use database for reliability
# Production with Redis: use cache, Production without Redis: database, Development: database
if IS_PRODUCTION and redis_url:
    # Production with Redis - cache sessions for speed
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Development and Production without Redis - use database (most reliable)
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

SESSION_COOKIE_AGE = 2592000  # 1 month
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SECURE = IS_PRODUCTION  # HTTPS only in production
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection

# ============ DATABASE CONFIGURATION ============
# For Render: Set DATABASE_URL environment variable (auto-configured by Render)
# For Local Development: Uses SQLite automatically
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL and dj_database_url:
    # Use DATABASE_URL if available (Render production)
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_health_checks=True,
            conn_max_age=600,
        )
    }
else:
    # Local development - use SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True

# Language Support
LANGUAGES = [
    ('en', 'English'),
    ('bn', 'বাংলা'),
]

# Locale paths
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# ============ SECURITY & HTTPS CONFIGURATION ============
# Render এ কোন environment variable add করতে হবে না - সব default আছে
if IS_PRODUCTION:
    # Production (Render) - সব built-in defaults এ কাজ করবে
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    
    # CSRF Trusted Origins for Render - read from environment
    csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', 'https://localhost')
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins.split(',')]
    
    # Handle proxy headers from Render
    SECURE_PROXY_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
else:
    # Development (ngrok, localhost)
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SECURE = False
    csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,https://*.ngrok-free.dev,http://*.ngrok-free.dev')
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins.split(',')]

# ============ CLOUDINARY STORAGE CONFIGURATION ============
# Pure Cloudinary storage - No local fallback
DEFAULT_FILE_STORAGE = 'shop.storage.CloudinaryStorage'

# Django 5.1+ STORAGES configuration
STORAGES = {
    'default': {
        'BACKEND': 'shop.storage.CloudinaryStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Cloudinary configuration with decouple (loads from .env)
cloudinary.config(
    cloud_name=config('CLOUDINARY_CLOUD_NAME', default=''),
    api_key=config('CLOUDINARY_API_KEY', default=''),
    api_secret=config('CLOUDINARY_API_SECRET', default=''),
    secure=True
)

# Static & Media URLs
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # Local development fallback
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============ GOOGLE MAPS API CONFIGURATION ============
# Set GOOGLE_MAPS_API_KEY in environment variables
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# ============ GOOGLE OAUTH CONFIGURATION ============
GOOGLE_OAUTH_CLIENT_ID = config('GOOGLE_OAUTH_CLIENT_ID', default='')
GOOGLE_OAUTH_CLIENT_SECRET = config('GOOGLE_OAUTH_CLIENT_SECRET', default='')
GOOGLE_OAUTH_REDIRECT_URI = config('GOOGLE_OAUTH_REDIRECT_URI', default='http://localhost:8000/google-callback/')

# ============ PERFORMANCE OPTIMIZATION ============
# Use atomic database transactions for better performance
ATOMIC_REQUESTS = IS_PRODUCTION

# Optimize queries in templates
if IS_PRODUCTION:
    # Use cached templates with custom loaders
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]

# Logging for production monitoring
LOGGING = {
    'version': 1,
    'disable_existing_loggers': not DEBUG,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING' if IS_PRODUCTION else 'INFO',
        },
        'shop': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# Optimize ORM queries
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB
