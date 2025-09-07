#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إعدادات نظام إدارة الأصول التقنية
IT Asset Management System Configuration
"""

import os
from datetime import timedelta

class Config:
    """إعدادات النظام الأساسية"""
    
    # إعدادات Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # إعدادات قاعدة البيانات
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///it_assets.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # إعدادات رفع الملفات
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # إعدادات الجلسة
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # True في الإنتاج مع HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # إعدادات البريد الإلكتروني (للإشعارات)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # إعدادات النظام
    ASSETS_PER_PAGE = 20
    MAINTENANCE_REMINDER_DAYS = 30
    WARRANTY_REMINDER_DAYS = 60
    
    # إعدادات QR Code
    QR_CODE_SIZE = 10
    QR_CODE_BORDER = 4
    
    # إعدادات التقارير
    REPORTS_FOLDER = 'static/reports'
    
    # إعدادات اللغة والمنطقة الزمنية
    LANGUAGES = ['ar', 'en']
    TIMEZONE = 'Asia/Riyadh'
    
    # إعدادات الأمان
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    @staticmethod
    def init_app(app):
        """تهيئة التطبيق مع الإعدادات"""
        # تهيئة رابط قاعدة البيانات (تصحيح postgres:// إلى postgresql:// عند الحاجة)
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
            app.config['SQLALCHEMY_DATABASE_URI'] = db_url

        # إنشاء المجلدات المطلوبة
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config.get('REPORTS_FOLDER', 'static/reports'), exist_ok=True)

class DevelopmentConfig(Config):
    """إعدادات بيئة التطوير"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///dev_it_assets.db'

class TestingConfig(Config):
    """إعدادات بيئة الاختبار"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """إعدادات بيئة الإنتاج"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///it_assets.db'
    SESSION_COOKIE_SECURE = True
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # تسجيل الأخطاء في الإنتاج
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/it_assets.log', maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('IT Asset Management System startup')

# خريطة الإعدادات
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# إعدادات الفئات الافتراضية
DEFAULT_CATEGORIES = [
    {
        'name': 'أجهزة الكمبيوتر',
        'description': 'أجهزة الكمبيوتر المكتبية والمحمولة'
    },
    {
        'name': 'الخوادم',
        'description': 'خوادم الشبكة وقواعد البيانات'
    },
    {
        'name': 'معدات الشبكة',
        'description': 'أجهزة التوجيه والتبديل والنقاط اللاسلكية'
    },
    {
        'name': 'الطابعات والماسحات',
        'description': 'طابعات وماسحات ضوئية وآلات تصوير'
    },
    {
        'name': 'الهواتف',
        'description': 'هواتف مكتبية ومحمولة'
    },
    {
        'name': 'الشاشات والعرض',
        'description': 'شاشات الكمبيوتر وأجهزة العرض'
    },
    {
        'name': 'أجهزة التخزين',
        'description': 'أقراص صلبة خارجية ووحدات التخزين'
    },
    {
        'name': 'معدات الأمان',
        'description': 'كاميرات المراقبة وأنظمة الإنذار'
    },
    {
        'name': 'أخرى',
        'description': 'معدات تقنية أخرى'
    }
]

# إعدادات المواقع الافتراضية
DEFAULT_LOCATIONS = [
    {
        'name': 'المبنى الرئيسي - الطابق الأول',
        'building': 'المبنى الرئيسي',
        'floor': 'الطابق الأول',
        'description': 'مكاتب الإدارة العامة'
    },
    {
        'name': 'المبنى الرئيسي - الطابق الثاني',
        'building': 'المبنى الرئيسي',
        'floor': 'الطابق الثاني',
        'description': 'مكاتب الموظفين'
    },
    {
        'name': 'قسم تقنية المعلومات',
        'building': 'المبنى التقني',
        'floor': 'الطابق الأرضي',
        'description': 'مركز البيانات والخوادم'
    },
    {
        'name': 'المستودع',
        'building': 'مبنى المستودعات',
        'floor': 'الطابق الأرضي',
        'description': 'تخزين المعدات'
    }
]

# حالات الأصول
ASSET_STATUSES = {
    'active': 'نشط',
    'maintenance': 'قيد الصيانة',
    'retired': 'متقاعد',
    'lost': 'مفقود',
    'damaged': 'تالف'
}

# الحالة الفنية
ASSET_CONDITIONS = {
    'excellent': 'ممتاز',
    'good': 'جيد',
    'fair': 'مقبول',
    'poor': 'ضعيف'
}

# أنواع الصيانة
MAINTENANCE_TYPES = {
    'preventive': 'صيانة وقائية',
    'corrective': 'صيانة إصلاحية',
    'emergency': 'صيانة طارئة',
    'upgrade': 'ترقية'
}

# حالات الصيانة
MAINTENANCE_STATUSES = {
    'scheduled': 'مجدولة',
    'in_progress': 'قيد التنفيذ',
    'completed': 'مكتملة',
    'cancelled': 'ملغية'
}