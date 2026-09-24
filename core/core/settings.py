from pathlib import Path
from datetime import timedelta
from decouple import config,Csv
from corsheaders.defaults import default_headers
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", default="django-insecure-automatic-fallback-for-testing")

FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())




# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # django drf app
    "rest_framework",
    
    #simple jwt app
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    
    #djoser
    'djoser',
    
    
    
    #django anymail(it connect your django app to extenal sms application like brevo or resend etc)
    "anymail",
    
    #my django apps
    'booking',
    'events',
    'payment',
    'users',
    
    
    #drf spectular
    'drf_spectacular',
    
    #django silk 
    'silk',
    
    #django allauth cors
    "corsheaders",
]





MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    
    #cors header
    "corsheaders.middleware.CorsMiddleware",
    
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    #django silk middleware
    'silk.middleware.SilkyMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }



#new db
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='event_api_db'),
        'USER': config('DB_USER', default='event_api_user'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' 


#django customize users
AUTH_USER_MODEL='users.User'

#rest authentication
REST_FRAMEWORK = {
    #simple jwt auth class 
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    
    #drf spectular 
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    
    #throlling settings
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '60/minute',
        'auth_lock': '5/minute',
    }

}



#djoser settings
DJOSER = {
    'LOGIN_FIELD': 'email',
    'USER_CREATE_PASSWORD_RETYPE': False,
    'SEND_ACTIVATION_EMAIL': False,           #change to true before production
    'ACTIVATION_URL': 'account/verify-email/{uid}/{token}',  # matches your FRONTEND_URL pattern
    'PASSWORD_RESET_CONFIRM_URL': 'account/password/reset/confirm/{uid}/{token}',
    'EMAIL_FRONTEND_PROTOCOL': 'https' if not DEBUG else 'http',
    'EMAIL_FRONTEND_DOMAIN': 'abc.xyc',  #change it to your frontend domain
    'EMAIL_FRONTEND_SITE_NAME': 'PAIN EVENT TICKETING API', 
    'SERIALIZERS': {},
}




#simple jwt settings

SIMPLE_JWT = {
    #djoer jwt 
    'AUTH_HEADER_TYPES': ('JWT',),
    #other jwt settings
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
}



#drf sepctular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Event Ticketing API',
    'DESCRIPTION': 'An API to browse events, booking tickets and making payment with Paystack',
    'VERSION': '1.0.0',
}

 


# change CORS_ALLOWED_ORIGINS to your frontend's URL
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
] 
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (
    *default_headers,
)



#anymail settings
ANYMAIL = {
    "BREVO_API_KEY": config("BREVO_API_KEY"), # add your secret key in the .env too 
}

EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL") #in your env make sure it matches your sender email e.g noreply@pain.com


