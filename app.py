#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام إدارة الأصول التقنية
IT Asset Management System
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import qrcode
import io
import base64
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json

from config import config, DEFAULT_CATEGORIES, DEFAULT_LOCATIONS
from models import db, User, Asset, Category, Location, Supplier, Employee, AssetAssignment, MaintenanceRecord, Purchase, PurchaseItem, Custody, CustodyItem, Department, License, Invoice, InvoiceItem, Notification

app = Flask(__name__)
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])
config[config_name].init_app(app)

# تهيئة قاعدة البيانات مع التطبيق
db.init_app(app)

# إنشاء الجداول والبيانات الافتراضية عند أول تشغيل على Render/الإنتاج
with app.app_context():
    try:
        db.create_all()

        # إنشاء مستخدم إداري افتراضي إن لم يوجد
        if not User.query.filter_by(username='admin').first():
            from werkzeug.security import generate_password_hash
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                full_name='مدير النظام',
                role='admin'
            )
            db.session.add(admin)

        # إنشاء الفئات الافتراضية إن لم توجد
        if Category.query.count() == 0:
            for cat in DEFAULT_CATEGORIES:
                db.session.add(Category(name=cat['name'], description=cat.get('description')))

        # إنشاء المواقع الافتراضية إن لم توجد
        if Location.query.count() == 0:
            for loc in DEFAULT_LOCATIONS:
                db.session.add(Location(
                    name=loc['name'],
                    building=loc.get('building'),
                    floor=loc.get('floor'),
                    description=loc.get('description')
                ))
        db.session.commit()
    except Exception:
        db.session.rollback()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة'

# إنشاء مجلد الرفع إذا لم يكن موجوداً
os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads'), exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



# الصفحات الرئيسية
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    # إحصائيات سريعة محسنة
    total_assets = Asset.query.count()
    active_assets = Asset.query.filter_by(status='active').count()
    maintenance_assets = Asset.query.filter_by(status='maintenance').count()
    retired_assets = Asset.query.filter_by(status='retired').count()
    
    # الأصول المضافة حديثاً (آخر 10 أصول)
    recent_assets = Asset.query.order_by(Asset.created_at.desc()).limit(10).all()
    
    # الصيانة المستحقة
    try:
        upcoming_maintenance = MaintenanceRecord.query.filter(
            MaintenanceRecord.next_maintenance <= datetime.now().date() + timedelta(days=30),
            MaintenanceRecord.status == 'scheduled'
        ).limit(5).all()
    except:
        upcoming_maintenance = []
    
    # إحصائيات الفئات للرسم البياني
    try:
        categories_stats = db.session.query(
            Category.name, 
            db.func.count(Asset.id)
        ).join(Asset).group_by(Category.name).all()
    except:
        categories_stats = []
    
    # عدد المستخدمين النشطين
    total_users = User.query.count()
    
    return render_template('dashboard.html',
                         total_assets=total_assets,
                         active_assets=active_assets,
                         maintenance_assets=maintenance_assets,
                         retired_assets=retired_assets,
                         recent_assets=recent_assets,
                         upcoming_maintenance=upcoming_maintenance,
                         categories_stats=categories_stats,
                         total_users=total_users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/assets')
@login_required
def assets():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category_id = request.args.get('category', type=int)
    status = request.args.get('status', '')
    
    query = Asset.query
    
    if search:
        query = query.filter(
            db.or_(
                Asset.name.contains(search),
                Asset.asset_tag.contains(search),
                Asset.serial_number.contains(search)
            )
        )
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if status:
        query = query.filter_by(status=status)
    
    assets = query.paginate(page=page, per_page=20, error_out=False)
    categories = Category.query.all()
    
    return render_template('assets/list.html', assets=assets, categories=categories)

@app.route('/assets/add', methods=['GET', 'POST'])
@login_required
def add_asset():
    if request.method == 'POST':
        asset = Asset(
            asset_tag=request.form['asset_tag'],
            name=request.form['name'],
            description=request.form.get('description'),
            category_id=request.form['category_id'],
            location_id=request.form.get('location_id') or None,
            supplier_id=request.form.get('supplier_id') or None,
            brand=request.form.get('brand'),
            model=request.form.get('model'),
            serial_number=request.form.get('serial_number'),
            purchase_cost=float(request.form['purchase_cost']) if request.form.get('purchase_cost') else None,
            status=request.form.get('status', 'active'),
            condition=request.form.get('condition', 'good'),
            specifications=request.form.get('specifications'),
            notes=request.form.get('notes'),
            created_by=current_user.id
        )
        
        # معالجة التواريخ
        if request.form.get('purchase_date'):
            asset.purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date()
        
        if request.form.get('warranty_expiry'):
            asset.warranty_expiry = datetime.strptime(request.form['warranty_expiry'], '%Y-%m-%d').date()
        
        # معالجة رفع الصورة
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(f"{asset.asset_tag}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                asset.image_path = filename
        
        db.session.add(asset)
        db.session.commit()
        
        flash('تم إضافة الأصل بنجاح', 'success')
        return redirect(url_for('assets'))
    
    categories = Category.query.all()
    locations = Location.query.all()
    suppliers = Supplier.query.all()
    
    return render_template('assets/add.html', categories=categories, locations=locations, suppliers=suppliers)

@app.route('/assets/<int:id>')
@login_required
def view_asset(id):
    asset = Asset.query.get_or_404(id)
    maintenance_records = MaintenanceRecord.query.filter_by(asset_id=id).order_by(MaintenanceRecord.maintenance_date.desc()).all()
    assignments = AssetAssignment.query.filter_by(asset_id=id).order_by(AssetAssignment.assigned_date.desc()).all()
    
    return render_template('assets/view.html', asset=asset, maintenance_records=maintenance_records, assignments=assignments)

@app.route('/assets/<int:id>/qr')
@login_required
def asset_qr(id):
    asset = Asset.query.get_or_404(id)
    
    # إنشاء QR Code
    qr_data = {
        'asset_tag': asset.asset_tag,
        'name': asset.name,
        'url': url_for('view_asset', id=asset.id, _external=True)
    }
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(qr_data, ensure_ascii=False))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # تحويل الصورة إلى base64
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return send_file(img_buffer, mimetype='image/png', as_attachment=True, 
                     download_name=f'qr_{asset.asset_tag}.png')

@app.route('/assets/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_asset(id):
    asset = Asset.query.get_or_404(id)
    
    if request.method == 'POST':
        asset.name = request.form['name']
        asset.description = request.form.get('description')
        asset.category_id = request.form['category_id']
        asset.location_id = request.form.get('location_id') or None
        asset.supplier_id = request.form.get('supplier_id') or None
        asset.brand = request.form.get('brand')
        asset.model = request.form.get('model')
        asset.serial_number = request.form.get('serial_number')
        asset.status = request.form.get('status', 'active')
        asset.condition = request.form.get('condition', 'good')
        asset.specifications = request.form.get('specifications')
        asset.notes = request.form.get('notes')
        asset.updated_at = datetime.utcnow()
        
        # معالجة التواريخ
        if request.form.get('purchase_date'):
            asset.purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date()
        
        if request.form.get('warranty_expiry'):
            asset.warranty_expiry = datetime.strptime(request.form['warranty_expiry'], '%Y-%m-%d').date()
        
        # معالجة التكلفة
        if request.form.get('purchase_cost'):
            asset.purchase_cost = float(request.form['purchase_cost'])
        
        # معالجة رفع الصورة
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(f"{asset.asset_tag}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                asset.image_path = filename
        
        db.session.commit()
        flash('تم تحديث الأصل بنجاح', 'success')
        return redirect(url_for('view_asset', id=asset.id))
    
    categories = Category.query.all()
    locations = Location.query.all()
    suppliers = Supplier.query.all()
    
    return render_template('assets/edit.html', asset=asset, categories=categories, 
                         locations=locations, suppliers=suppliers)

@app.route('/assets/<int:id>/delete', methods=['DELETE'])
@login_required
def delete_asset(id):
    asset = Asset.query.get_or_404(id)
    
    try:
        # حذف الصورة إذا كانت موجودة
        if asset.image_path:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], asset.image_path)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(asset)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'تم حذف الأصل بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء الحذف'})

# صفحات الصيانة
@app.route('/maintenance')
@login_required
def maintenance_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    maintenance_type = request.args.get('maintenance_type', '')
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = MaintenanceRecord.query
    
    if search:
        query = query.join(Asset).filter(
            db.or_(
                MaintenanceRecord.description.contains(search),
                Asset.name.contains(search),
                Asset.asset_tag.contains(search)
            )
        )
    
    if maintenance_type:
        query = query.filter_by(maintenance_type=maintenance_type)
    
    if status:
        query = query.filter_by(status=status)
    
    if date_from:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        query = query.filter(MaintenanceRecord.maintenance_date >= date_from_obj)
    
    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        query = query.filter(MaintenanceRecord.maintenance_date <= date_to_obj)
    
    maintenance_records = query.order_by(MaintenanceRecord.maintenance_date.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    # إحصائيات
    completed_count = MaintenanceRecord.query.filter_by(status='completed').count()
    in_progress_count = MaintenanceRecord.query.filter_by(status='in_progress').count()
    scheduled_count = MaintenanceRecord.query.filter_by(status='scheduled').count()
    overdue_count = MaintenanceRecord.query.filter(
        MaintenanceRecord.next_maintenance < datetime.now().date(),
        MaintenanceRecord.status == 'scheduled'
    ).count()
    
    assets = Asset.query.filter_by(status='active').all()
    
    return render_template('maintenance/list.html', 
                         maintenance_records=maintenance_records,
                         completed_count=completed_count,
                         in_progress_count=in_progress_count,
                         scheduled_count=scheduled_count,
                         overdue_count=overdue_count,
                         assets=assets)

@app.route('/maintenance/add', methods=['POST'])
@login_required
def add_maintenance():
    maintenance = MaintenanceRecord(
        asset_id=request.form['asset_id'],
        maintenance_type=request.form['maintenance_type'],
        description=request.form['description'],
        technician=request.form.get('technician'),
        status=request.form.get('status', 'scheduled'),
        notes=request.form.get('notes'),
        created_by=current_user.id
    )
    
    # معالجة التاريخ
    if request.form.get('maintenance_date'):
        maintenance.maintenance_date = datetime.strptime(request.form['maintenance_date'], '%Y-%m-%dT%H:%M')
    
    # معالجة التكلفة
    if request.form.get('cost'):
        maintenance.cost = float(request.form['cost'])
    
    # معالجة تاريخ الصيانة القادمة
    if request.form.get('next_maintenance'):
        maintenance.next_maintenance = datetime.strptime(request.form['next_maintenance'], '%Y-%m-%d').date()
    
    db.session.add(maintenance)
    db.session.commit()
    
    flash('تم إضافة سجل الصيانة بنجاح', 'success')
    return redirect(url_for('maintenance_list'))

@app.route('/maintenance/<int:id>/complete', methods=['POST'])
@login_required
def complete_maintenance(id):
    maintenance = MaintenanceRecord.query.get_or_404(id)
    maintenance.status = 'completed'
    maintenance.maintenance_date = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'تم إكمال الصيانة بنجاح'})

# صفحات التقارير
@app.route('/reports')
@login_required
def reports():
    return render_template('reports/index.html')

@app.route('/reports/assets')
@login_required
def assets_report():
    # تقرير الأصول
    assets = Asset.query.all()
    
    # إحصائيات
    total_assets = len(assets)
    active_assets = len([a for a in assets if a.status == 'active'])
    maintenance_assets = len([a for a in assets if a.status == 'maintenance'])
    retired_assets = len([a for a in assets if a.status == 'retired'])
    
    # توزيع الأصول حسب الفئة
    categories_stats = db.session.query(
        Category.name, 
        db.func.count(Asset.id).label('count')
    ).join(Asset).group_by(Category.name).all()
    
    # الأصول الأكثر تكلفة
    expensive_assets = Asset.query.filter(Asset.purchase_cost.isnot(None)).order_by(
        Asset.purchase_cost.desc()).limit(10).all()
    
    return render_template('reports/assets.html',
                         assets=assets,
                         total_assets=total_assets,
                         active_assets=active_assets,
                         maintenance_assets=maintenance_assets,
                         retired_assets=retired_assets,
                         categories_stats=categories_stats,
                         expensive_assets=expensive_assets)

@app.route('/reports/maintenance')
@login_required
def maintenance_report():
    # تقرير الصيانة
    maintenance_records = MaintenanceRecord.query.all()
    
    # إحصائيات الصيانة
    total_maintenance = len(maintenance_records)
    completed_maintenance = len([m for m in maintenance_records if m.status == 'completed'])
    total_cost = sum([m.cost for m in maintenance_records if m.cost])
    
    # الصيانة حسب النوع
    maintenance_by_type = db.session.query(
        MaintenanceRecord.maintenance_type,
        db.func.count(MaintenanceRecord.id).label('count')
    ).group_by(MaintenanceRecord.maintenance_type).all()
    
    # الأصول الأكثر صيانة
    assets_maintenance_count = db.session.query(
        Asset.name,
        Asset.asset_tag,
        db.func.count(MaintenanceRecord.id).label('maintenance_count')
    ).join(MaintenanceRecord).group_by(Asset.id).order_by(
        db.func.count(MaintenanceRecord.id).desc()).limit(10).all()
    
    return render_template('reports/maintenance.html',
                         maintenance_records=maintenance_records,
                         total_maintenance=total_maintenance,
                         completed_maintenance=completed_maintenance,
                         total_cost=total_cost,
                         maintenance_by_type=maintenance_by_type,
                         assets_maintenance_count=assets_maintenance_count)

# صفحات الموظفين
@app.route('/employees')
@login_required
def employees():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Employee.query
    
    if search:
        query = query.filter(
            db.or_(
                Employee.full_name.contains(search),
                Employee.employee_id.contains(search),
                Employee.department.contains(search)
            )
        )
    
    employees = query.paginate(page=page, per_page=20, error_out=False)
    
    return render_template('employees/list.html', employees=employees)

@app.route('/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if request.method == 'POST':
        employee = Employee(
            employee_id=request.form['employee_id'],
            full_name=request.form['full_name'],
            department=request.form.get('department'),
            position=request.form.get('position'),
            email=request.form.get('email'),
            phone=request.form.get('phone')
        )
        
        db.session.add(employee)
        db.session.commit()
        
        flash('تم إضافة الموظف بنجاح', 'success')
        return redirect(url_for('employees'))
    
    return render_template('employees/add.html')

@app.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    
    if request.method == 'POST':
        employee.full_name = request.form['full_name']
        employee.department = request.form.get('department')
        employee.position = request.form.get('position')
        employee.email = request.form.get('email')
        employee.phone = request.form.get('phone')
        
        db.session.commit()
        flash('تم تحديث بيانات الموظف بنجاح', 'success')
        return redirect(url_for('employees'))
    
    return render_template('employees/edit.html', employee=employee)

@app.route('/employees/<int:id>/delete', methods=['DELETE'])
@login_required
def delete_employee(id):
    employee = Employee.query.get_or_404(id)
    
    try:
        db.session.delete(employee)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم حذف الموظف بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء الحذف'})

# صفحات المواقع
@app.route('/locations')
@login_required
def locations():
    locations = Location.query.all()
    return render_template('locations/list.html', locations=locations)

@app.route('/locations/add', methods=['GET', 'POST'])
@login_required
def add_location():
    if request.method == 'POST':
        location = Location(
            name=request.form['name'],
            building=request.form.get('building'),
            floor=request.form.get('floor'),
            room=request.form.get('room'),
            description=request.form.get('description')
        )
        
        db.session.add(location)
        db.session.commit()
        
        flash('تم إضافة الموقع بنجاح', 'success')
        return redirect(url_for('locations'))
    
    return render_template('locations/add.html')

@app.route('/locations/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_location(id):
    location = Location.query.get_or_404(id)
    
    if request.method == 'POST':
        location.name = request.form['name']
        location.building = request.form.get('building')
        location.floor = request.form.get('floor')
        location.room = request.form.get('room')
        location.description = request.form.get('description')
        
        db.session.commit()
        flash('تم تحديث الموقع بنجاح', 'success')
        return redirect(url_for('locations'))
    
    return render_template('locations/edit.html', location=location)

@app.route('/locations/<int:id>/delete', methods=['DELETE'])
@login_required
def delete_location(id):
    location = Location.query.get_or_404(id)
    
    try:
        db.session.delete(location)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم حذف الموقع بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء الحذف'})

# صفحات الموردين
@app.route('/suppliers')
@login_required
def suppliers():
    suppliers = Supplier.query.all()
    return render_template('suppliers/list.html', suppliers=suppliers)

@app.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
def add_supplier():
    if request.method == 'POST':
        supplier = Supplier(
            name=request.form['name'],
            contact_person=request.form.get('contact_person'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address')
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        flash('تم إضافة المورد بنجاح', 'success')
        return redirect(url_for('suppliers'))
    
    return render_template('suppliers/add.html')

@app.route('/suppliers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    
    if request.method == 'POST':
        supplier.name = request.form['name']
        supplier.contact_person = request.form.get('contact_person')
        supplier.phone = request.form.get('phone')
        supplier.email = request.form.get('email')
        supplier.address = request.form.get('address')
        
        db.session.commit()
        flash('تم تحديث بيانات المورد بنجاح', 'success')
        return redirect(url_for('suppliers'))
    
    return render_template('suppliers/edit.html', supplier=supplier)

@app.route('/suppliers/<int:id>/delete', methods=['DELETE'])
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    
    try:
        db.session.delete(supplier)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم حذف المورد بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء الحذف'})

# مسارات التقارير
@app.route('/reports')
@login_required
def reports_index():
    """صفحة التقارير الرئيسية"""
    return render_template('reports/index.html')

@app.route('/reports/assets')
@login_required
def reports_assets():
    """تقرير الأصول"""
    # جمع البيانات للتقرير
    assets = Asset.query.all()
    
    # إحصائيات الأصول
    total_assets = len(assets)
    active_assets = len([a for a in assets if a.status == 'active'])
    maintenance_assets = len([a for a in assets if a.status == 'maintenance'])
    retired_assets = len([a for a in assets if a.status == 'retired'])
    
    # الأصول الأكثر تكلفة (أعلى 5)
    expensive_assets = Asset.query.filter(Asset.purchase_cost.isnot(None))\
                                 .order_by(Asset.purchase_cost.desc())\
                                 .limit(5).all()
    
    # إحصائيات الفئات
    try:
        categories_stats = db.session.query(
            Category.name, 
            db.func.count(Asset.id)
        ).join(Asset).group_by(Category.name).all()
    except:
        categories_stats = []
    
    # إحصائيات الحالة
    try:
        status_stats = db.session.query(
            Asset.status,
            db.func.count(Asset.id)
        ).group_by(Asset.status).all()
    except:
        status_stats = []
    
    # إحصائيات المواقع
    try:
        locations_stats = db.session.query(
            Location.name,
            db.func.count(Asset.id)
        ).join(Asset).group_by(Location.name).all()
    except:
        locations_stats = []
    
    return render_template('reports/assets.html',
                         total_assets=total_assets,
                         active_assets=active_assets,
                         maintenance_assets=maintenance_assets,
                         retired_assets=retired_assets,
                         expensive_assets=expensive_assets,
                         categories_stats=categories_stats,
                         status_stats=status_stats,
                         locations_stats=locations_stats,
                         assets=assets,
                         report_date=datetime.now().strftime('%Y-%m-%d %H:%M'))

@app.route('/reports/maintenance')
@login_required
def reports_maintenance():
    """تقرير الصيانة"""
    # جمع بيانات الصيانة
    maintenance_records = MaintenanceRecord.query.all()
    
    # إحصائيات الصيانة
    total_maintenance = len(maintenance_records)
    completed_maintenance = len([m for m in maintenance_records if m.status == 'completed'])
    
    # إجمالي التكلفة
    total_cost = sum([m.cost for m in maintenance_records if m.cost])
    
    # الصيانة حسب النوع
    try:
        maintenance_by_type = db.session.query(
            MaintenanceRecord.maintenance_type,
            db.func.count(MaintenanceRecord.id)
        ).group_by(MaintenanceRecord.maintenance_type).all()
    except:
        maintenance_by_type = []
    
    # الأصول الأكثر صيانة
    try:
        assets_maintenance_count = db.session.query(
            Asset.name,
            Asset.asset_tag,
            db.func.count(MaintenanceRecord.id)
        ).join(MaintenanceRecord).group_by(Asset.id)\
         .order_by(db.func.count(MaintenanceRecord.id).desc())\
         .limit(10).all()
    except:
        assets_maintenance_count = []
    
    return render_template('reports/maintenance.html',
                         total_maintenance=total_maintenance,
                         completed_maintenance=completed_maintenance,
                         total_cost=total_cost,
                         maintenance_by_type=maintenance_by_type,
                         assets_maintenance_count=assets_maintenance_count,
                         maintenance_records=maintenance_records)

# API endpoints للوحة التحكم والإشعارات
@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """API لجلب إحصائيات لوحة التحكم"""
    try:
        stats = {
            'total_assets': Asset.query.count(),
            'active_assets': Asset.query.filter_by(status='active').count(),
            'maintenance_count': Asset.query.filter_by(status='maintenance').count(),
            'users_count': User.query.count(),
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': 'فشل في جلب الإحصائيات'}), 500

@app.route('/api/dashboard/activities')
@login_required
def api_dashboard_activities():
    """API لجلب الأنشطة الحديثة"""
    try:
        # محاكاة الأنشطة الحديثة (يمكن ربطها بجدول سجل العمليات لاحقاً)
        activities = [
            {
                'type': 'create',
                'title': 'إضافة أصل جديد',
                'description': f'تم إضافة {Asset.query.count()} أصل إجمالي',
                'timestamp': datetime.now().isoformat()
            },
            {
                'type': 'maintenance',
                'title': 'صيانة مجدولة',
                'description': f'{Asset.query.filter_by(status="maintenance").count()} أصل قيد الصيانة',
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                'type': 'update',
                'title': 'تحديث النظام',
                'description': 'تم تحديث لوحة التحكم بنجاح',
                'timestamp': (datetime.now() - timedelta(hours=5)).isoformat()
            }
        ]
        
        return jsonify({'activities': activities})
    except Exception as e:
        return jsonify({'error': 'فشل في جلب الأنشطة'}), 500

# API endpoints للإشعارات
@app.route('/api/notifications')
@login_required
def api_notifications():
    """API لجلب الإشعارات"""
    try:
        # محاكاة الإشعارات (يمكن ربطها بقاعدة البيانات لاحقاً)
        notifications = [
            {
                'id': 1,
                'title': 'صيانة مستحقة',
                'message': 'يوجد 3 أصول تحتاج صيانة دورية',
                'type': 'maintenance',
                'read': False,
                'created_at': datetime.now().isoformat()
            },
            {
                'id': 2,
                'title': 'ضمان ينتهي قريباً',
                'message': 'ضمان جهاز الكمبيوتر PC-001 ينتهي خلال 15 يوم',
                'type': 'warranty',
                'read': False,
                'created_at': (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                'id': 3,
                'title': 'تحديث النظام',
                'message': 'تم تحديث نظام إدارة الأصول بنجاح',
                'type': 'system',
                'read': True,
                'created_at': (datetime.now() - timedelta(days=1)).isoformat()
            }
        ]
        
        return jsonify({'notifications': notifications})
    except Exception as e:
        return jsonify({'error': 'فشل في جلب الإشعارات'}), 500

@app.route('/api/notifications/count')
@login_required
def api_notifications_count():
    """API لجلب عدد الإشعارات غير المقروءة"""
    try:
        # محاكاة العدد (يمكن ربطها بقاعدة البيانات لاحقاً)
        unread_count = 2
        return jsonify({'unread_count': unread_count})
    except Exception as e:
        return jsonify({'error': 'فشل في جلب عدد الإشعارات'}), 500

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def api_mark_notification_read(notification_id):
    """API لتعليم إشعار كمقروء"""
    try:
        # محاكاة تعليم الإشعار كمقروء
        return jsonify({'success': True, 'message': 'تم تعليم الإشعار كمقروء'})
    except Exception as e:
        return jsonify({'error': 'فشل في تعليم الإشعار'}), 500

@app.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    """API لتعليم جميع الإشعارات كمقروءة"""
    try:
        # محاكاة تعليم جميع الإشعارات كمقروءة
        return jsonify({'success': True, 'message': 'تم تعليم جميع الإشعارات كمقروءة'})
    except Exception as e:
        return jsonify({'error': 'فشل في تعليم الإشعارات'}), 500

@app.route('/api/maintenance/alerts')
@login_required
def api_maintenance_alerts():
    """API لجلب تنبيهات الصيانة العاجلة"""
    try:
        # محاكاة تنبيهات الصيانة
        urgent_maintenance = []
        
        # فحص الأصول التي تحتاج صيانة عاجلة
        assets_needing_maintenance = Asset.query.filter_by(status='maintenance').count()
        
        if assets_needing_maintenance > 0:
            urgent_maintenance = [{'count': assets_needing_maintenance}]
        
        return jsonify({'urgent_maintenance': urgent_maintenance})
    except Exception as e:
        return jsonify({'error': 'فشل في جلب تنبيهات الصيانة'}), 500

# تسجيل وحدة الإدارة
from admin import admin_bp
app.register_blueprint(admin_bp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # إنشاء مستخدم افتراضي إذا لم يكن موجوداً
        if not User.query.first():
            admin = User(
                username='admin',
                email='admin@company.com',
                password_hash=generate_password_hash('admin123'),
                full_name='مدير النظام',
                role='admin'
            )
            db.session.add(admin)
            
            # إضافة فئات افتراضية
            for cat_data in DEFAULT_CATEGORIES:
                category = Category(**cat_data)
                db.session.add(category)
            
            # إضافة مواقع افتراضية
            for loc_data in DEFAULT_LOCATIONS:
                location = Location(**loc_data)
                db.session.add(location)
            
            db.session.commit()
    
        port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
