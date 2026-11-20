"""企业员工管理系统全局配置。

文件职责：
    这是整个 Django 项目的“配置中心”。Django 启动后第一件事就是读取本文件：
    连哪台 MySQL、界面显示中文还是英文、时区、登录跳转地址、日志写到哪里、
    CSRF / 点击劫持等安全开关，全部由这里决定。页面上看到的一切行为背后都受本文件控制。

项目位置：
    d:\\ems\\program\\hrms\\settings.py，被 manage.py、wsgi.py、asgi.py 通过
    DJANGO_SETTINGS_MODULE='hrms.settings' 引用，是项目的“大脑配置文件”。

对应任务书：
    T1 环境与初始化（INSTALLED_APPS、数据库、模板、静态文件、媒体文件）；
    T4 登录（LOGIN_URL、SESSION_COOKIE_AGE、登录拦截中间件）；
    T5 RBAC（AUTH_USER_MODEL 指向自定义用户模型 app01.User）；
    T10 图表（静态资源与 AJAX 所需的 CSRF Cookie 配置）；
    T13 安全（安全响应头、DEBUG/ALLOWED_HOSTS 环境变量控制、分级日志）。

# 讲解要点：
# 1. 浏览器打开 127.0.0.1:8000，第一眼看到的是中文登录页（用户名、密码、图片验证码）。
#    对应本文件 LANGUAGE_CODE='zh-hans' 让界面变中文、LOGIN_URL='/login/' 指定未登录跳转地址、
#    以及 MIDDLEWARE 最后一行 LoginRequiredMiddleware 拦住“未登录直接访问内页”的请求。
# 2. 登录成功后进入首页，左侧出现“首页概览 / 部门管理 / 员工管理 / 考勤管理 …”侧边栏，
#    右侧首页有图表卡片，列表页里能看到中文姓名、部门、头像。这些数据全部来自 MySQL，
#    对应本文件 DATABASES 里的库名 hrms、账号 root、字符集 utf8mb4；
#    头像能显示则对应 MEDIA_URL / MEDIA_ROOT 与文件末尾的 static() 媒体路由配置。
# 3. 侧边栏菜单不是写死的，而是按权限码显示——权限来自自定义用户模型，
#    对应本文件 AUTH_USER_MODEL='app01.User'（必须在第一次迁移前配置好）。
# 4. 如果把 DJANGO_DEBUG 设为 False 重启，页面报错不再显示代码细节，
#    同时 logs/error.log 会记录错误——这就是本文件末尾“安全响应头 + RotatingFileHandler 分级日志”的效果。
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-hrms-course-design-2026-change-me-in-production',
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').strip().lower() == 'true'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver'
    ).split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app01',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'app01.middleware.login_required.LoginRequiredMiddleware',
]

ROOT_URLCONF = 'hrms.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'hrms.wsgi.application'
ASGI_APPLICATION = 'hrms.asgi.application'

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').strip().lower()

if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'hrms'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', '123456'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {'charset': 'utf8mb4'},
            'CONN_MAX_AGE': 60,
            'TEST': {'CHARSET': 'utf8mb4'},
        }
    }

AUTH_USER_MODEL = 'app01.User'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

SESSION_COOKIE_AGE = 60 * 60 * 24 * 14


LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False

if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'False') == 'True'
    SESSION_COOKIE_SECURE = os.environ.get('DJANGO_COOKIE_SECURE', 'False') == 'True'
    CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = 'same-origin'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'hrms.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'INFO',
            'encoding': 'utf-8',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'error.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'ERROR',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'app01': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
