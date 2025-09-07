#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نماذج قاعدة البيانات لنظام إدارة الأصول التقنية
Database Models for IT Asset Management System
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# النماذج (Models)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='user')  # admin, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assets = db.relationship('Asset', backref='category', lazy=True)

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    building = db.Column(db.String(100))
    floor = db.Column(db.String(50))
    room = db.Column(db.String(50))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assets = db.relationship('Asset', backref='location', lazy=True)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assets = db.relationship('Asset', backref='supplier', lazy=True)

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    
    # معلومات الجهاز
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    purchase_cost = db.Column(db.Float)
    warranty_expiry = db.Column(db.Date)
    
    # الحالة
    status = db.Column(db.String(20), default='active')  # active, maintenance, retired, lost
    condition = db.Column(db.String(20), default='good')  # excellent, good, fair, poor
    
    # معلومات إضافية
    specifications = db.Column(db.Text)  # JSON format
    notes = db.Column(db.Text)
    image_path = db.Column(db.String(200))
    
    # تواريخ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # العلاقات
    maintenance_records = db.relationship('MaintenanceRecord', backref='asset', lazy=True)
    assignments = db.relationship('AssetAssignment', backref='asset', lazy=True)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assignments = db.relationship('AssetAssignment', backref='employee', lazy=True)

class AssetAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class MaintenanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    maintenance_type = db.Column(db.String(50), nullable=False)  # preventive, corrective, emergency
    description = db.Column(db.Text, nullable=False)
    maintenance_date = db.Column(db.DateTime, default=datetime.utcnow)
    cost = db.Column(db.Float)
    technician = db.Column(db.String(100))
    status = db.Column(db.String(20), default='completed')  # scheduled, in_progress, completed, cancelled
    next_maintenance = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_order = db.Column(db.String(100), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, received, cancelled
    notes = db.Column(db.Text)
    invoice_file = db.Column(db.String(200))  # مسار ملف الفاتورة
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # العلاقات
    supplier = db.relationship('Supplier', backref='purchases')
    items = db.relationship('PurchaseItem', backref='purchase', lazy=True)

class PurchaseItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

class Custody(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    custody_number = db.Column(db.String(100), unique=True, nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    custody_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')  # active, returned, lost
    notes = db.Column(db.Text)
    barcode = db.Column(db.String(100), unique=True)  # باركود العهدة
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # العلاقات
    employee = db.relationship('Employee', backref='custodies')
    items = db.relationship('CustodyItem', backref='custody', lazy=True)

class CustodyItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    custody_id = db.Column(db.Integer, db.ForeignKey('custody.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    condition_given = db.Column(db.String(20), default='good')
    condition_returned = db.Column(db.String(20))
    notes = db.Column(db.Text)
    
    # العلاقات
    asset = db.relationship('Asset', backref='custody_items')

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    manager = db.Column(db.String(100))
    budget = db.Column(db.Float)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    software_name = db.Column(db.String(200), nullable=False)
    license_key = db.Column(db.String(500), nullable=False)
    license_type = db.Column(db.String(50), nullable=False)  # perpetual, subscription, trial
    purchase_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date)
    seats = db.Column(db.Integer, default=1)
    used_seats = db.Column(db.Integer, default=0)
    cost = db.Column(db.Float)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    status = db.Column(db.String(20), default='active')  # active, expired, cancelled
    notes = db.Column(db.Text)
    invoice_file = db.Column(db.String(200))  # مسار ملف الفاتورة
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # العلاقات
    supplier = db.relationship('Supplier', backref='licenses')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(100), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date)
    total_amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue, cancelled
    payment_method = db.Column(db.String(50))
    payment_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    invoice_file = db.Column(db.String(200))  # مسار ملف الفاتورة
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # العلاقات
    supplier = db.relationship('Supplier', backref='invoices')
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    tax_rate = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)

class Notification(db.Model):
    """نموذج الإشعارات"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # maintenance, warranty, license, system, security
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # null = للجميع
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'))  # مرتبط بأصل معين
    read = db.Column(db.Boolean, default=False)
    action_url = db.Column(db.String(200))  # رابط للإجراء المطلوب
    expires_at = db.Column(db.DateTime)  # تاريخ انتهاء الإشعار
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # العلاقات
    user = db.relationship('User', foreign_keys=[user_id], backref='notifications')
    asset = db.relationship('Asset', backref='notifications')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def to_dict(self):
        """تحويل الإشعار إلى قاموس"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'priority': self.priority,
            'read': self.read,
            'action_url': self.action_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'asset_name': self.asset.name if self.asset else None,
            'asset_tag': self.asset.asset_tag if self.asset else None
        }
    
    @staticmethod
    def create_maintenance_alert(asset, days_until_maintenance):
        """إنشاء تنبيه صيانة"""
        if days_until_maintenance <= 0:
            title = "صيانة مستحقة الآن"
            message = f"الأصل {asset.name} ({asset.asset_tag}) يحتاج صيانة عاجلة"
            priority = "urgent"
        elif days_until_maintenance <= 7:
            title = "صيانة مستحقة قريباً"
            message = f"الأصل {asset.name} ({asset.asset_tag}) يحتاج صيانة خلال {days_until_maintenance} أيام"
            priority = "high"
        else:
            title = "تذكير صيانة"
            message = f"الأصل {asset.name} ({asset.asset_tag}) يحتاج صيانة خلال {days_until_maintenance} يوم"
            priority = "normal"
        
        notification = Notification(
            title=title,
            message=message,
            type='maintenance',
            priority=priority,
            asset_id=asset.id,
            action_url=f'/assets/{asset.id}'
        )
        return notification
    
    @staticmethod
    def create_warranty_alert(asset, days_until_expiry):
        """إنشاء تنبيه انتهاء ضمان"""
        if days_until_expiry <= 0:
            title = "انتهى الضمان"
            message = f"انتهى ضمان الأصل {asset.name} ({asset.asset_tag})"
            priority = "high"
        elif days_until_expiry <= 30:
            title = "ضمان ينتهي قريباً"
            message = f"ضمان الأصل {asset.name} ({asset.asset_tag}) ينتهي خلال {days_until_expiry} يوم"
            priority = "normal"
        else:
            return None
        
        notification = Notification(
            title=title,
            message=message,
            type='warranty',
            priority=priority,
            asset_id=asset.id,
            action_url=f'/assets/{asset.id}'
        )
        return notification