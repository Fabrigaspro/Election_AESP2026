from pathlib import Path
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from environ import Env

env = Env()
Env.read_env()
ENVIRONMENT = env("ENVIRONMENT", default="production")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY') 

# SECURITY WARNING: don't run with debug turned on in production!
if ENVIRONMENT == "development":
    DEBUG = True  
else:
    DEBUG = True  

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'electionaesp2026iuget.up.railway.app', '.railway.app', ]

# ⚠️ Pour Railway - Configuration de sécurité
CSRF_TRUSTED_ORIGINS = [
    'https://electionaesp2026iuget.up.railway.app',
    'https://*.railway.app',
]

# Configuration CSRF critique
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # Doit être False pour que JavaScript puisse lire le token
CSRF_USE_SESSIONS = False
#CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'

#CSRF_COOKIE_DOMAIN = '.railway.app'  # Pour tous les sous-domaines Railway
CSRF_COOKIE_SAMESITE = 'Lax'  # 'None' peut causer des problèmes

# Configuration session
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'  # None Important pour les iframes et cross-origin
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1209600

# Configuration sécurité
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',
    'cloudinary_storage', 
    'vote_app',
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
    'vote_app.middleware.SessionManagementMiddleware',
]

ROOT_URLCONF = 'election_project.urls'

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
                'django.template.context_processors.csrf',
            ],
        },
    },
]

WSGI_APPLICATION = 'election_project.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
} 

POSTGRES_LOCALLY = False
if ENVIRONMENT == 'production' or POSTGRES_LOCALLY == True:
    import dj_database_url
    DATABASES['default']=dj_database_url.parse(env('DATABASE_URL'))

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
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Douala'
USE_TZ = True
USE_I18N = True
USE_L10N = True

# Si vous voulez supporter plusieurs langues
LANGUAGES = [
    ('fr', 'French'),
    ('en', 'English'),
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Configuration Cloudinary
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': env('CLOUDINARY_API_KEY'),
    'API_SECRET': env('CLOUDINARY_API_SECRET'),
    'SECURE': True,
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.RawMediaCloudinaryStorage'


# --- Vérification automatique du reçu étudiant par IA ---
# Clé API à définir dans les variables d'environnement Railway (jamais dans le code).
# Sans clé, les inscriptions restent "en attente" pour validation manuelle.
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default='')
RECEIPT_AI_MODEL = env('RECEIPT_AI_MODEL', default='claude-haiku-5-5')
RECEIPT_AI_TIMEOUT = 25                      # secondes (gunicorn coupe à 30 s par défaut)
ACADEMIC_YEAR = env('ACADEMIC_YEAR', default='2026/2027')   # année du scrutin
ECOLE = env('ECOLE', default='SOUTH POLYTECH')   # année du scrutin
RECEIPT_EXPECTED_AMOUNT = env.int('RECEIPT_EXPECTED_AMOUNT', default=0)  # FCFA, 0 = ne pas contrôler
RECEIPT_REQUIRE_QR = True
RECEIPT_NAME_THRESHOLD = 0.85                # tolérance de lecture par mot du nom
RECEIPT_MIN_CONFIDENCE = 0.6                 # confiance minimale de lecture
RECEIPT_REQUIRE_YEAR = env.bool('RECEIPT_REQUIRE_YEAR', default=True)
RECEIPT_REQUIRE_ECOLE = env.bool('RECEIPT_REQUIRE_YEAR', default=True)
RECEIPT_STRICT_SPECIALITE = env.bool('RECEIPT_STRICT_SPECIALITE', default=False)  # True = une spécialité différente bloque la validation auto
# Moteur de lecture du reçu : 'auto' (Claude -> OCR.space -> OCR local, selon les clés présentes), 'claude', 'ocrspace' ou 'ocr'
RECEIPT_ENGINE = env('RECEIPT_ENGINE', default='auto')
# OCR.space (gratuit : ~25 000 requêtes/mois, images <= 1 Mo). Clé à mettre dans Railway : OCR_SPACE_API_KEY
OCR_SPACE_API_KEY = env('OCR_SPACE_API_KEY', default='')
OCR_SPACE_URL = env('OCR_SPACE_URL', default='https://api.ocr.space/parse/image')
OCR_SPACE_LANGUAGE = env('OCR_SPACE_LANGUAGE', default='fre')
OCR_SPACE_ENGINE = env.int('OCR_SPACE_ENGINE', default=2)      # 1 ou 2
OCR_SPACE_TIMEOUT = 25                       # secondes
OCR_SPACE_CONFIDENCE = 0.85                  # OCR.space ne donne pas de confiance : valeur fixe
# Mots qui doivent figurer sur un vrai reçu (en-tête de l'établissement), sans espaces ni accents
RECEIPT_ISSUER_KEYWORDS = ['IUGET', 'SOUTHPOLYTECH']
REGISTER_MAX_PER_IP_PER_HOUR = 15            # limite anti-abus (coût IA + faux comptes)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')