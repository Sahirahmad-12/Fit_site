# ✅ REPLACE WITH THIS
import os
from pathlib import Path
import dj_database_url
import cloudinary
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get('DEBUG', 'False') == 'True'
SECRET_KEY = os.environ.get('SECRET_KEY') or (
    'django-insecure-local-development-key' if DEBUG else os.environ['SECRET_KEY']
)
API_KEY = os.environ.get("INTERNAL_API_KEY", "")

# ── ALLOWED_HOSTS ─────────────────────────────────────────────────────────
# Never use ["*"] in production — it accepts requests spoofing any Host header
if DEBUG:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
else:
    ALLOWED_HOSTS = [
        'entergym.onrender.com',
        'www.entergym.onrender.com',
    ]

CSRF_TRUSTED_ORIGINS = [
    "https://entergym.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'AuthFit',
    'cloudinary',
    'cloudinary_storage',
    'Shop',
    'notifications',
]

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",
    "default_theme_mode": "auto",
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'AuthFit.middleware.SecurityHeadersMiddleware',  # ← add this
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

ROOT_URLCONF = 'Fitness.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'AuthFit.context_processors.gym_config',
                'notifications.context_processors.vapid_key',
            ],
        },
    }
]

WSGI_APPLICATION = 'Fitness.wsgi.application'

cloudinary_credentials = (
    os.environ.get('CLOUDINARY_CLOUD_NAME'),
    os.environ.get('CLOUDINARY_API_KEY'),
    os.environ.get('CLOUDINARY_API_SECRET'),
)
if all(cloudinary_credentials):
    cloudinary.config(
        cloud_name=cloudinary_credentials[0],
        api_key=cloudinary_credentials[1],
        api_secret=cloudinary_credentials[2],
        secure=True,
    )
elif not DEBUG:
    cloudinary.config(
        cloud_name=os.environ['CLOUDINARY_CLOUD_NAME'],
        api_key=os.environ['CLOUDINARY_API_KEY'],
        api_secret=os.environ['CLOUDINARY_API_SECRET'],
        secure=True,
    )

if not DEBUG or all(cloudinary_credentials):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
STATICFILES_STORAGE    = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

if DEBUG and not os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.parse(os.environ['DATABASE_URL'])
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True

STATIC_URL      = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT     = os.path.join(BASE_DIR, "staticfiles_build")
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year, in seconds


REDIS_URL = os.environ.get('REDIS_URL')
if DEBUG and not REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
else:
    REDIS_URL = os.environ['REDIS_URL']
    CACHES = {
        "default": {
            "BACKEND":  "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                **({"CONNECTION_POOL_KWARGS": {"ssl_cert_reqs": None}}
                   if REDIS_URL.startswith('rediss://') else {})
            }
        }
    }

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_CLAIMS = {"sub": f"mailto:{os.environ.get('VAPID_EMAIL')}"}

LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/'
LOGOUT_REDIRECT_URL = '/'

# ── Session & Cookie Security ─────────────────────────────────────────────
SESSION_ENGINE       = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS  = 'default'
SESSION_COOKIE_AGE   = 86400        # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE   = not DEBUG  # True in production (HTTPS only)

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE   = not DEBUG

# ── File upload limits ────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Gym Config (server-side only — never sent to browser directly) ────────
GYM_LATITUDE      = float(os.environ.get('GYM_LATITUDE',      21.2179))
GYM_LONGITUDE     = float(os.environ.get('GYM_LONGITUDE',     81.3311))
GYM_RADIUS_METERS = float(os.environ.get('GYM_RADIUS_METERS', 100))

FIREBASE_CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    "firebase-credentials.json"
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'shop': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.security': {        # log security events
            'handlers': ['console'],
            'level': 'WARNING',
        },
    },
}

if not DEBUG:
    SECURE_HSTS_SECONDS        = 31536000   # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD        = True
    SECURE_SSL_REDIRECT        = True
    SECURE_PROXY_SSL_HEADER    = ('HTTP_X_FORWARDED_PROTO', 'https')


JAZZMIN_SETTINGS = {
    "site_title":   "EnterGYM Admin",
    "site_header":  "EnterGYM Dashboard",
    "site_brand":   "EnterGYM",
    "welcome_sign": "Welcome to EnterGYM Control Panel",
    "site_logo":    "images/Logo.png",
    "site_icon":    "images/Logo.png",
    "copyright":    "EnterGYM",
    "topmenu_links": [
        {"name": "Support", "url": "https://wa.me/917000032565", "new_window": True},
    ],
    "usermenu_links": [
        {"name": "Support", "url": "https://wa.me/917000032565", "new_window": True},
    ],
    "show_sidebar":          True,
    "navigation_expanded":   True,
    "order_with_respect_to": [
        "AuthFit", "AuthFit.enrollment", "AuthFit.attendance",
        "AuthFit.membershipplan", "AuthFit.trainer",
        "AuthFit.contact", "AuthFit.gymnotification", "auth",
    ],
    "icons": {
        "AuthFit":                   "fas fa-dumbbell",
        "AuthFit.attendence":        "fas fa-clipboard-user",
        "AuthFit.contact":           "fas fa-address-book",
        "AuthFit.enrollment":        "fas fa-id-card",
        "AuthFit.gymnotification":   "fas fa-bell",
        "AuthFit.membershipplan":    "fas fa-layer-group",
        "AuthFit.trainer":           "fas fa-user-tie",
        "auth":                      "fas fa-users-cog",
        "auth.user":                 "fas fa-user",
        "auth.group":                "fas fa-users",
    },
    "changeform_format":     "horizontal_tabs",
    "related_modal_active":  False,
    "custom_css":            "css/admin_custom.css",
    "custom_links": {
        "EnterGYM": [
            {
                "name": "Visit Website",
                "url":  "https://entergym.onrender.com/",
                "icon": "fas fa-globe",
                "new_window": True,
            },
            {
                "name": "Support",
                "url":  "https://wa.me/917000032565",
                "icon": "fas fa-headset",
                "new_window": True,
            },
        ]
    }
}