# ============================================================================
# WEBAPP.PY - WEB ARAYÜZÜ V3 (TAM ÖZELLİKLİ)
# ============================================================================
# Mobil uyumlu, offline çalışan ERP web arayüzü
# DictLoader mimarisi ile TemplateNotFound hatası YOK
# ============================================================================

from flask import Flask, request, redirect, url_for, session, flash, render_template, jsonify, Response
import jinja2
import backend
from datetime import datetime, timedelta
from functools import wraps
import json

# ============================================================================
# FLASK UYGULAMASI
# ============================================================================

app = Flask(__name__)
app.secret_key = "super-secret-erp-key-2024-change-in-production"
app.config['JSON_AS_ASCII'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# ============================================================================
# YARDIMCI FONKSİYONLAR
# ============================================================================

def login_required(f):
    """Login gerektiren route'lar için decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Lütfen giriş yapın.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def format_currency(value):
    """Para birimi formatlar."""
    try:
        return f"{float(value):,.2f}"
    except:
        return "0.00"

def format_date(value, format='%d/%m/%Y'):
    """Tarih formatlar."""
    if not value:
        return ""
    try:
        if isinstance(value, str):
            value = datetime.strptime(value[:10], '%Y-%m-%d')
        return value.strftime(format)
    except:
        return value

# ============================================================================
# HTML TEMPLATE TANIMLARI
# ============================================================================

# ----------------------------------------------------------------------------
# 1. BASE TEMPLATE (MOBİL UYUMLU ANA ŞABLON)
# ----------------------------------------------------------------------------
BASE_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{% block title %}ERP Sistemi{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <meta name="theme-color" content="#4f46e5">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <style>
        :root {
            --primary: #4f46e5;
            --primary-dark: #4338ca;
            --secondary: #6366f1;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --info: #3b82f6;
            --dark: #1f2937;
            --light: #f3f4f6;
            --sidebar-width: 260px;
            --header-height: 60px;
        }
        * { -webkit-tap-highlight-color: transparent; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f8fafc;
            overflow-x: hidden;
            min-height: 100vh;
        }
        
        /* SIDEBAR */
        .sidebar {
            position: fixed;
            top: 0; left: 0;
            width: var(--sidebar-width);
            height: 100vh;
            background: linear-gradient(180deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            z-index: 1050;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            overflow-y: auto;
            overflow-x: hidden;
        }
        .sidebar::-webkit-scrollbar { width: 0; }
        
        @media (max-width: 991px) {
            .sidebar { transform: translateX(-100%); }
            .sidebar.show { transform: translateX(0); }
        }
        
        .sidebar-header {
            padding: 1.25rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            position: sticky;
            top: 0;
            background: inherit;
            z-index: 10;
        }
        .sidebar-header h5 { font-weight: 700; margin: 0; font-size: 1.1rem; }
        
        .sidebar-nav { padding: 0.75rem 0; }
        .nav-item { margin: 2px 8px; }
        .nav-link {
            color: rgba(255,255,255,0.8);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.2s;
            font-size: 0.9rem;
            font-weight: 500;
        }
        .nav-link:hover, .nav-link.active {
            background: rgba(255,255,255,0.15);
            color: white;
        }
        .nav-link.active { background: rgba(255,255,255,0.2); }
        .nav-link i { font-size: 1.15rem; width: 24px; text-align: center; }
        
        .nav-divider {
            height: 1px;
            background: rgba(255,255,255,0.1);
            margin: 0.75rem 1rem;
        }
        
        .sidebar-footer {
            position: sticky;
            bottom: 0;
            background: rgba(0,0,0,0.2);
            padding: 1rem;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        .user-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .user-avatar {
            width: 40px; height: 40px;
            background: rgba(255,255,255,0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }
        .user-details { flex: 1; min-width: 0; }
        .user-name { font-weight: 600; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .user-role { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }
        
        /* DROPDOWN FIX */
.dropdown-menu {
    z-index: 1050 !important;
}

.card .dropdown {
    position: static !important;
}

.card-body {
    overflow: visible !important;
}
        
        /* OVERLAY */
        .sidebar-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1040;
            backdrop-filter: blur(2px);
        }
        @media (max-width: 991px) {
            .sidebar-overlay.show { display: block; }
        }
        
        /* MAIN CONTENT */
        .main-content {
            margin-left: var(--sidebar-width);
            min-height: 100vh;
            transition: margin-left 0.3s;
        }
        @media (max-width: 991px) {
            .main-content { margin-left: 0; }
        }
        
        /* MOBILE HEADER */
        .mobile-header {
            display: none;
            position: sticky;
            top: 0;
            background: white;
            height: var(--header-height);
            padding: 0 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            z-index: 1030;
            align-items: center;
            gap: 1rem;
        }
        @media (max-width: 991px) {
            .mobile-header { display: flex; }
        }
        .menu-toggle {
            background: none;
            border: none;
            font-size: 1.5rem;
            color: var(--dark);
            padding: 0.25rem;
            cursor: pointer;
        }
        .mobile-title { flex: 1; font-weight: 600; font-size: 1.1rem; text-align: center; }
        
        /* DESKTOP HEADER */
        .page-header {
            background: white;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }
        @media (max-width: 991px) {
            .page-header { display: none; }
        }
        .page-title { font-size: 1.5rem; font-weight: 700; color: var(--dark); margin: 0; }
        
        /* CONTENT WRAPPER */
        .content-wrapper { padding: 1.5rem; }
        @media (max-width: 767px) {
            .content-wrapper { padding: 1rem; }
        }
        
        /* CARDS */
        .card {
            border: none;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            margin-bottom: 1rem;
            overflow: hidden;
        }
        .card-header {
            background: white;
            border-bottom: 1px solid #e5e7eb;
            padding: 1rem 1.25rem;
            font-weight: 600;
        }
        .card-body { padding: 1.25rem; }
        
        /* STAT CARDS */
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
            height: 100%;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .stat-icon {
            width: 48px; height: 48px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }
        .stat-value { font-size: 1.5rem; font-weight: 700; margin: 0.5rem 0 0.25rem; }
        .stat-label { color: #6b7280; font-size: 0.85rem; }
        
        @media (max-width: 576px) {
            .stat-card { padding: 1rem; }
            .stat-icon { width: 40px; height: 40px; font-size: 1.25rem; }
            .stat-value { font-size: 1.25rem; }
        }
        
        /* TABLES */
        .table { margin: 0; }
        .table th { 
            font-weight: 600; 
            font-size: 0.8rem; 
            text-transform: uppercase; 
            color: #6b7280;
            border-bottom-width: 1px;
        }
        .table td { vertical-align: middle; }
        
        /* MOBILE LIST CARDS */
        .mobile-list { display: none; }
        @media (max-width: 767px) {
            .desktop-table { display: none; }
            .mobile-list { display: block; }
        }
        .list-card {
            background: white;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .list-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.5rem;
        }
        .list-card-title { font-weight: 600; font-size: 1rem; }
        .list-card-body { font-size: 0.875rem; color: #6b7280; }
        .list-card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.75rem;
            padding-top: 0.75rem;
            border-top: 1px solid #e5e7eb;
        }
        
        /* BUTTONS */
        .btn { border-radius: 8px; font-weight: 500; padding: 0.5rem 1rem; }
        .btn-primary { background: var(--primary); border-color: var(--primary); }
        .btn-primary:hover { background: var(--primary-dark); border-color: var(--primary-dark); }
        .btn-success { background: var(--success); border-color: var(--success); }
        .btn-danger { background: var(--danger); border-color: var(--danger); }
        .btn-warning { background: var(--warning); border-color: var(--warning); color: #000; }
        
        /* FAB BUTTON */
        .fab {
            position: fixed;
            bottom: 1.5rem;
            right: 1.5rem;
            width: 56px; height: 56px;
            border-radius: 50%;
            background: var(--primary);
            color: white;
            border: none;
            font-size: 1.5rem;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
            z-index: 1020;
            display: none;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        @media (max-width: 991px) { .fab { display: flex; } }
        .fab:hover { transform: scale(1.05); box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5); }
        .fab:active { transform: scale(0.95); }
        
        /* BADGES */
        .badge { font-weight: 500; padding: 0.35em 0.65em; border-radius: 6px; }
        .badge-success { background: #d1fae5; color: #065f46; }
        .badge-danger { background: #fee2e2; color: #991b1b; }
        .badge-warning { background: #fef3c7; color: #92400e; }
        .badge-info { background: #dbeafe; color: #1e40af; }
        .badge-secondary { background: #e5e7eb; color: #374151; }
        
        /* FORMS */
        .form-control, .form-select {
            border-radius: 8px;
            border: 1px solid #d1d5db;
            padding: 0.625rem 0.875rem;
        }
        .form-control:focus, .form-select:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
        }
        .form-label { font-weight: 500; margin-bottom: 0.375rem; font-size: 0.875rem; }
        
        /* MODALS */
        .modal-content { border: none; border-radius: 16px; }
        .modal-header { border-bottom: 1px solid #e5e7eb; padding: 1rem 1.25rem; }
        .modal-title { font-weight: 600; }
        .modal-body { padding: 1.25rem; }
        .modal-footer { border-top: 1px solid #e5e7eb; padding: 1rem 1.25rem; }
        
        @media (max-width: 576px) {
            .modal-dialog { margin: 0.5rem; }
            .modal-content { border-radius: 12px; }
        }
        
        /* ALERTS */
        .alert { border: none; border-radius: 10px; }
        
        /* EMPTY STATE */
        .empty-state {
            text-align: center;
            padding: 3rem 1rem;
            color: #6b7280;
        }
        .empty-state i { font-size: 3rem; margin-bottom: 1rem; opacity: 0.5; }
        .empty-state h5 { color: var(--dark); margin-bottom: 0.5rem; }
        
        /* ANIMATIONS */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade { animation: fadeIn 0.3s ease-out; }
        
        /* SCROLLBAR */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
        
        /* QUICK ACTIONS */
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 0.75rem;
        }
        .quick-action-btn {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            transition: all 0.2s;
            text-decoration: none;
            color: var(--dark);
        }
        .quick-action-btn:hover {
            border-color: var(--primary);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            color: var(--primary);
        }
        .quick-action-btn i { font-size: 1.5rem; display: block; margin-bottom: 0.5rem; }
        .quick-action-btn span { font-size: 0.8rem; font-weight: 500; }
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% if session.user %}
    
    <!-- SIDEBAR OVERLAY -->
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
    
    <!-- SIDEBAR -->
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h5><i class="bi bi-grid-3x3-gap-fill me-2"></i>{{ company_name or 'ERP Sistemi' }}</h5>
        </div>
        
        <nav class="sidebar-nav">
            <ul class="nav flex-column">
                <li class="nav-item">
                    <a class="nav-link {% if request.endpoint == 'dashboard' %}active{% endif %}" href="{{ url_for('dashboard') }}">
                        <i class="bi bi-speedometer2"></i> Ana Panel
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link {% if 'customer' in request.endpoint|default('') %}active{% endif %}" href="{{ url_for('customers') }}">
                        <i class="bi bi-people"></i> Cariler
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link {% if 'check' in request.endpoint|default('') %}active{% endif %}" href="{{ url_for('checks') }}">
                        <i class="bi bi-credit-card-2-back"></i> Çek/Senet
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link {% if 'cash' in request.endpoint|default('') %}active{% endif %}" href="{{ url_for('cash_flow') }}">
                        <i class="bi bi-cash-stack"></i> Kasa
                    </a>
                </li>
                
                <div class="nav-divider"></div>
                
                <li class="nav-item">
                    <a class="nav-link {% if 'reminder' in request.endpoint|default('') %}active{% endif %}" href="{{ url_for('reminders') }}">
                        <i class="bi bi-bell"></i> Hatırlatıcılar
                        {% if pending_reminders %}<span class="badge bg-danger ms-auto">{{ pending_reminders }}</span>{% endif %}
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link {% if 'note' in request.endpoint|default('') %}active{% endif %}" href="{{ url_for('notes') }}">
                        <i class="bi bi-journal-text"></i> Notlar
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link {% if 'report' in request.endpoint|default('') %}active{% endif %}" href="{{ url_for('reports') }}">
                        <i class="bi bi-graph-up"></i> Raporlar
                    </a>
                </li>
                
                <div class="nav-divider"></div>
                
                <li class="nav-item">
                    <a class="nav-link {% if 'setting' in request.endpoint|default('') %}active{% endif %}" href="{{ url_for('settings') }}">
                        <i class="bi bi-gear"></i> Ayarlar
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link text-danger" href="{{ url_for('logout') }}">
                        <i class="bi bi-box-arrow-right"></i> Çıkış
                    </a>
                </li>
            </ul>
        </nav>
        
        <div class="sidebar-footer">
            <div class="user-info">
                <div class="user-avatar"><i class="bi bi-person"></i></div>
                <div class="user-details">
                    <div class="user-name">{{ session.user.full_name }}</div>
                    <div class="user-role">{{ session.user.role }}</div>
                </div>
            </div>
        </div>
    </aside>
    
    <!-- MAIN CONTENT -->
    <main class="main-content">
        <!-- MOBILE HEADER -->
        <header class="mobile-header">
            <button class="menu-toggle" onclick="toggleSidebar()">
                <i class="bi bi-list"></i>
            </button>
            <span class="mobile-title">{% block mobile_title %}ERP{% endblock %}</span>
            <div style="width: 32px;"></div>
        </header>
        
        <!-- CONTENT WRAPPER -->
        <div class="content-wrapper">
            <!-- DESKTOP HEADER -->
            <div class="page-header">
                <h1 class="page-title">{% block page_title %}Dashboard{% endblock %}</h1>
                <div>{% block header_actions %}{% endblock %}</div>
            </div>
            
            <!-- FLASH MESSAGES -->
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show animate-fade" role="alert">
                        <i class="bi bi-{% if category == 'success' %}check-circle{% elif category == 'danger' or category == 'error' %}x-circle{% elif category == 'warning' %}exclamation-triangle{% else %}info-circle{% endif %} me-2"></i>
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <!-- PAGE CONTENT -->
            {% block content %}{% endblock %}
        </div>
    </main>
    
    {% else %}
    {% block public_content %}{% endblock %}
    {% endif %}
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('show');
            document.getElementById('sidebarOverlay').classList.toggle('show');
        }
        
        // Close sidebar on link click (mobile)
        document.querySelectorAll('.sidebar .nav-link').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth < 992) {
                    toggleSidebar();
                }
            });
        });
        
        // Swipe to open sidebar
        let touchStartX = 0;
        document.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; });
        document.addEventListener('touchend', e => {
            const touchEndX = e.changedTouches[0].clientX;
            const diff = touchEndX - touchStartX;
            if (diff > 80 && touchStartX < 30) toggleSidebar();
            if (diff < -80 && document.getElementById('sidebar').classList.contains('show')) toggleSidebar();
        });
        
        // Format currency inputs
        document.querySelectorAll('input[data-type="currency"]').forEach(input => {
            input.addEventListener('blur', function() {
                const value = parseFloat(this.value.replace(/[^\d.-]/g, ''));
                if (!isNaN(value)) {
                    this.value = value.toFixed(2);
                }
            });
        });
    </script>
    {% block extra_js %}{% endblock %}
</body>
</html>
'''

# ----------------------------------------------------------------------------
# 2. LOGIN SAYFASI
# ----------------------------------------------------------------------------
LOGIN_HTML = '''
{% extends "base.html" %}
{% block title %}Giriş{% endblock %}
{% block public_content %}
<div class="min-vh-100 d-flex align-items-center justify-content-center p-4" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);">
    <div class="card shadow-lg animate-fade" style="width: 100%; max-width: 400px;">
        <div class="card-body p-4 p-md-5">
            <div class="text-center mb-4">
                <div class="rounded-circle bg-primary bg-opacity-10 d-inline-flex align-items-center justify-content-center mb-3" style="width: 80px; height: 80px;">
                    <i class="bi bi-shield-lock text-primary" style="font-size: 2.5rem;"></i>
                </div>
                <h4 class="fw-bold mb-1">Hoş Geldiniz</h4>
                <p class="text-muted small">Hesabınıza giriş yapın</p>
            </div>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                    <div class="alert alert-{{ category }} py-2 small">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Kullanıcı Adı</label>
                    <div class="input-group">
                        <span class="input-group-text"><i class="bi bi-person"></i></span>
                        <input type="text" class="form-control" name="username" required autofocus autocomplete="username">
                    </div>
                </div>
                <div class="mb-4">
                    <label class="form-label">Şifre</label>
                    <div class="input-group">
                        <span class="input-group-text"><i class="bi bi-lock"></i></span>
                        <input type="password" class="form-control" name="password" required autocomplete="current-password">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary w-100 py-2">
                    <i class="bi bi-box-arrow-in-right me-2"></i>Giriş Yap
                </button>
            </form>
            
            <div class="text-center mt-4">
                <small class="text-muted">Varsayılan: admin / admin123</small>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 3. DASHBOARD SAYFASI
# ----------------------------------------------------------------------------
DASHBOARD_HTML = '''
{% extends "base.html" %}
{% block title %}Ana Panel{% endblock %}
{% block page_title %}Ana Panel{% endblock %}
{% block mobile_title %}Ana Panel{% endblock %}

{% block content %}
<!-- ÖZET KARTLARI -->
<div class="row g-3 mb-4">
    <div class="col-6 col-lg-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <div class="stat-label">Kasa Bakiyesi</div>
                    <div class="stat-value text-primary">{{ "{:,.0f}".format(stats.cash_balance|default(0)) }}₺</div>
                </div>
                <div class="stat-icon" style="background: #ede9fe; color: #7c3aed;">
                    <i class="bi bi-wallet2"></i>
                </div>
            </div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <div class="stat-label">Toplam Alacak</div>
                    <div class="stat-value text-success">{{ "{:,.0f}".format(stats.total_receivables|default(0)) }}₺</div>
                </div>
                <div class="stat-icon" style="background: #d1fae5; color: #059669;">
                    <i class="bi bi-arrow-down-circle"></i>
                </div>
            </div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <div class="stat-label">Toplam Borç</div>
                    <div class="stat-value text-danger">{{ "{:,.0f}".format(stats.total_payables|default(0)) }}₺</div>
                </div>
                <div class="stat-icon" style="background: #fee2e2; color: #dc2626;">
                    <i class="bi bi-arrow-up-circle"></i>
                </div>
            </div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <div class="stat-label">Toplam Cari</div>
                    <div class="stat-value">{{ stats.total_customers|default(0) }}</div>
                </div>
                <div class="stat-icon" style="background: #dbeafe; color: #2563eb;">
                    <i class="bi bi-people"></i>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- ÇEK/SENET DURUMU -->
<div class="row g-3 mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span><i class="bi bi-credit-card-2-back me-2"></i>Çek/Senet Durumu</span>
                <a href="{{ url_for('checks') }}" class="btn btn-sm btn-outline-primary">Tümünü Gör</a>
            </div>
            <div class="card-body">
                <div class="row g-3">
                    <div class="col-6 col-md-3">
                        <div class="text-center p-3 rounded" style="background: #d1fae5;">
                            <div class="fw-bold text-success h4 mb-1">{{ "{:,.0f}".format(check_summary.incoming_pending_amount|default(0)) }}₺</div>
                            <div class="small text-muted">Alınan ({{ check_summary.incoming_pending_count|default(0) }})</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center p-3 rounded" style="background: #fee2e2;">
                            <div class="fw-bold text-danger h4 mb-1">{{ "{:,.0f}".format(check_summary.outgoing_pending_amount|default(0)) }}₺</div>
                            <div class="small text-muted">Verilen ({{ check_summary.outgoing_pending_count|default(0) }})</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center p-3 rounded" style="background: #fef3c7;">
                            <div class="fw-bold text-warning h4 mb-1">{{ check_summary.this_week_count|default(0) }}</div>
                            <div class="small text-muted">Bu Hafta Vadeli</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center p-3 rounded" style="background: #fecaca;">
                            <div class="fw-bold text-danger h4 mb-1">{{ check_summary.overdue_count|default(0) }}</div>
                            <div class="small text-muted">Vadesi Geçen</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- HIZLI İŞLEMLER + HATIRLATICILAR -->
<div class="row g-3 mb-4">
    <div class="col-12 col-lg-6">
        <div class="card h-100">
            <div class="card-header"><i class="bi bi-lightning me-2"></i>Hızlı İşlemler</div>
            <div class="card-body">
                <div class="quick-actions">
                    <a href="{{ url_for('customer_add') }}" class="quick-action-btn">
                        <i class="bi bi-person-plus text-primary"></i>
                        <span>Yeni Cari</span>
                    </a>
                    <a href="{{ url_for('check_add') }}" class="quick-action-btn">
                        <i class="bi bi-plus-circle text-success"></i>
                        <span>Çek/Senet Ekle</span>
                    </a>
                    <a href="{{ url_for('cash_flow_add') }}" class="quick-action-btn">
                        <i class="bi bi-cash text-info"></i>
                        <span>Kasa İşlemi</span>
                    </a>
                    <a href="{{ url_for('reminder_add') }}" class="quick-action-btn">
                        <i class="bi bi-bell text-warning"></i>
                        <span>Hatırlatıcı</span>
                    </a>
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-12 col-lg-6">
        <div class="card h-100">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span><i class="bi bi-bell me-2"></i>Yaklaşan Hatırlatıcılar</span>
                <a href="{{ url_for('reminders') }}" class="btn btn-sm btn-outline-primary">Tümü</a>
            </div>
            <div class="card-body">
                {% if upcoming_reminders %}
                    {% for reminder in upcoming_reminders[:5] %}
                    <div class="d-flex align-items-center gap-3 py-2 {% if not loop.last %}border-bottom{% endif %}">
                        <div class="rounded-circle d-flex align-items-center justify-content-center {% if reminder.display_status == 'overdue' %}bg-danger{% elif reminder.display_status == 'today' %}bg-warning{% else %}bg-info{% endif %} bg-opacity-10" style="width: 40px; height: 40px;">
                            <i class="bi bi-{% if reminder.reminder_type == 'check' %}credit-card{% elif reminder.reminder_type == 'payment' %}cash{% else %}bell{% endif %} {% if reminder.display_status == 'overdue' %}text-danger{% elif reminder.display_status == 'today' %}text-warning{% else %}text-info{% endif %}"></i>
                        </div>
                        <div class="flex-grow-1 min-width-0">
                            <div class="fw-semibold text-truncate">{{ reminder.title }}</div>
                            <div class="small text-muted">{{ reminder.due_date }}</div>
                        </div>
                        {% if reminder.display_status == 'overdue' %}
                            <span class="badge badge-danger">Gecikmiş</span>
                        {% elif reminder.display_status == 'today' %}
                            <span class="badge badge-warning">Bugün</span>
                        {% endif %}
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="text-center py-4 text-muted">
                        <i class="bi bi-check-circle d-block mb-2" style="font-size: 2rem;"></i>
                        Yaklaşan hatırlatıcı yok
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<!-- VADESİ YAKLAŞAN ÇEKLER -->
{% if upcoming_checks %}
<div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
        <span><i class="bi bi-exclamation-triangle text-warning me-2"></i>Vadesi Yaklaşan Çek/Senetler</span>
        <a href="{{ url_for('checks') }}?status=upcoming" class="btn btn-sm btn-outline-warning">Tümünü Gör</a>
    </div>
    <div class="card-body p-0">
        <div class="table-responsive desktop-table">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>No</th>
                        <th>Tür</th>
                        <th>Müşteri</th>
                        <th>Tutar</th>
                        <th>Vade</th>
                        <th>Kalan Gün</th>
                    </tr>
                </thead>
                <tbody>
                    {% for check in upcoming_checks[:5] %}
                    <tr>
                        <td><strong>{{ check.check_number }}</strong></td>
                        <td>
                            {% if check.check_type == 'incoming' %}
                                <span class="badge badge-success">Alınan</span>
                            {% else %}
                                <span class="badge badge-danger">Verilen</span>
                            {% endif %}
                        </td>
                        <td>{{ check.customer_name or '-' }}</td>
                        <td><strong>{{ "{:,.2f}".format(check.amount) }}₺</strong></td>
                        <td>{{ check.due_date }}</td>
                        <td>
                            {% if check.days_left < 0 %}
                                <span class="badge badge-danger">{{ check.days_left|abs }} gün geçti</span>
                            {% elif check.days_left == 0 %}
                                <span class="badge badge-warning">Bugün</span>
                            {% else %}
                                <span class="badge badge-info">{{ check.days_left }} gün</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="mobile-list p-3">
            {% for check in upcoming_checks[:5] %}
            <div class="list-card">
                <div class="list-card-header">
                    <span class="list-card-title">{{ check.check_number }}</span>
                    {% if check.check_type == 'incoming' %}
                        <span class="badge badge-success">Alınan</span>
                    {% else %}
                        <span class="badge badge-danger">Verilen</span>
                    {% endif %}
                </div>
                <div class="list-card-body">
                    <div>{{ check.customer_name or '-' }}</div>
                </div>
                <div class="list-card-footer">
                    <strong>{{ "{:,.2f}".format(check.amount) }}₺</strong>
                    <span>
                        {% if check.days_left < 0 %}
                            <span class="text-danger">{{ check.days_left|abs }} gün geçti</span>
                        {% elif check.days_left == 0 %}
                            <span class="text-warning">Bugün</span>
                        {% else %}
                            <span class="text-info">{{ check.days_left }} gün</span>
                        {% endif %}
                    </span>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endif %}
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 4. MÜŞTERİ LİSTESİ SAYFASI
# ----------------------------------------------------------------------------
CUSTOMERS_HTML = '''
{% extends "base.html" %}
{% block title %}Cariler{% endblock %}
{% block page_title %}Cari Hesaplar{% endblock %}
{% block mobile_title %}Cariler{% endblock %}

{% block header_actions %}
<a href="{{ url_for('customer_add') }}" class="btn btn-primary">
    <i class="bi bi-plus-lg me-1"></i>Yeni Cari
</a>
{% endblock %}

{% block content %}
<!-- FİLTRELER -->
<div class="card mb-3">
    <div class="card-body py-2">
        <form method="GET" class="row g-2 align-items-center">
            <div class="col-auto">
                <select name="type" class="form-select form-select-sm" onchange="this.form.submit()">
                    <option value="">Tüm Türler</option>
                    <option value="customer" {% if request.args.get('type') == 'customer' %}selected{% endif %}>Müşteri</option>
                    <option value="supplier" {% if request.args.get('type') == 'supplier' %}selected{% endif %}>Tedarikçi</option>
                </select>
            </div>
            <div class="col-auto">
                <select name="balance" class="form-select form-select-sm" onchange="this.form.submit()">
                    <option value="">Tüm Bakiyeler</option>
                    <option value="receivable" {% if request.args.get('balance') == 'receivable' %}selected{% endif %}>Alacaklı</option>
                    <option value="payable" {% if request.args.get('balance') == 'payable' %}selected{% endif %}>Borçlu</option>
                </select>
            </div>
            <div class="col">
                <div class="input-group input-group-sm">
                    <input type="text" name="search" class="form-control" placeholder="Ara..." value="{{ request.args.get('search', '') }}">
                    <button class="btn btn-outline-secondary" type="submit"><i class="bi bi-search"></i></button>
                </div>
            </div>
        </form>
    </div>
</div>

<!-- LİSTE -->
<div class="card">
    <div class="card-body p-0">
        <!-- DESKTOP TABLE -->
        <div class="table-responsive desktop-table">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Ad/Ünvan</th>
                        <th>Tür</th>
                        <th>Telefon</th>
                        <th>Şehir</th>
                        <th class="text-end">Bakiye</th>
                        <th class="text-center">İşlemler</th>
                    </tr>
                </thead>
                <tbody>
                    {% for customer in customers %}
                    <tr>
                        <td>
                            <a href="{{ url_for('customer_detail', id=customer.id) }}" class="text-decoration-none">
                                <strong>{{ customer.name }}</strong>
                            </a>
                        </td>
                        <td>
                            {% if customer.customer_type == 'customer' %}
                                <span class="badge badge-info">Müşteri</span>
                            {% else %}
                                <span class="badge badge-secondary">Tedarikçi</span>
                            {% endif %}
                        </td>
                        <td>{{ customer.phone or '-' }}</td>
                        <td>{{ customer.city or '-' }}</td>
                        <td class="text-end">
                            {% if customer.balance > 0 %}
                                <span class="text-success fw-bold">+{{ "{:,.2f}".format(customer.balance) }}₺</span>
                            {% elif customer.balance < 0 %}
                                <span class="text-danger fw-bold">{{ "{:,.2f}".format(customer.balance) }}₺</span>
                            {% else %}
                                <span class="text-muted">0,00₺</span>
                            {% endif %}
                        </td>
                        <td class="text-center">
                            <div class="btn-group btn-group-sm">
                                <a href="{{ url_for('customer_detail', id=customer.id) }}" class="btn btn-outline-primary" title="Detay">
                                    <i class="bi bi-eye"></i>
                                </a>
                                <a href="{{ url_for('customer_edit', id=customer.id) }}" class="btn btn-outline-secondary" title="Düzenle">
                                    <i class="bi bi-pencil"></i>
                                </a>
                            </div>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="6" class="text-center py-5 text-muted">
                            <i class="bi bi-inbox d-block mb-2" style="font-size: 2rem;"></i>
                            Kayıt bulunamadı
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <!-- MOBILE LIST -->
        <div class="mobile-list p-3">
            {% for customer in customers %}
            <a href="{{ url_for('customer_detail', id=customer.id) }}" class="text-decoration-none">
                <div class="list-card">
                    <div class="list-card-header">
                        <span class="list-card-title text-dark">{{ customer.name }}</span>
                        {% if customer.balance > 0 %}
                            <span class="text-success fw-bold">+{{ "{:,.0f}".format(customer.balance) }}₺</span>
                        {% elif customer.balance < 0 %}
                            <span class="text-danger fw-bold">{{ "{:,.0f}".format(customer.balance) }}₺</span>
                        {% else %}
                            <span class="text-muted">0₺</span>
                        {% endif %}
                    </div>
                    <div class="list-card-body">
                        <i class="bi bi-telephone me-1"></i>{{ customer.phone or '-' }}
                        {% if customer.city %}<span class="ms-3"><i class="bi bi-geo-alt me-1"></i>{{ customer.city }}</span>{% endif %}
                    </div>
                </div>
            </a>
            {% else %}
            <div class="empty-state">
                <i class="bi bi-inbox"></i>
                <h5>Kayıt bulunamadı</h5>
            </div>
            {% endfor %}
        </div>
    </div>
</div>

<!-- FAB BUTTON -->
<a href="{{ url_for('customer_add') }}" class="fab">
    <i class="bi bi-plus-lg"></i>
</a>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 5. MÜŞTERİ EKLEME/DÜZENLEME SAYFASI
# ----------------------------------------------------------------------------
CUSTOMER_FORM_HTML = '''
{% extends "base.html" %}
{% block title %}{{ 'Cari Düzenle' if customer else 'Yeni Cari' }}{% endblock %}
{% block page_title %}{{ 'Cari Düzenle' if customer else 'Yeni Cari Ekle' }}{% endblock %}
{% block mobile_title %}{{ 'Düzenle' if customer else 'Yeni Cari' }}{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-12 col-lg-8">
        <div class="card">
            <div class="card-body">
                <form method="POST">
                    <!-- TEMEL BİLGİLER -->
                    <h6 class="text-muted mb-3"><i class="bi bi-person me-2"></i>Temel Bilgiler</h6>
                    <div class="row g-3 mb-4">
                        <div class="col-md-8">
                            <label class="form-label">Ad / Ünvan *</label>
                            <input type="text" name="name" class="form-control" value="{{ customer.name if customer else '' }}" required>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Kısa Ad</label>
                            <input type="text" name="short_name" class="form-control" value="{{ customer.short_name if customer else '' }}">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Tür</label>
                            <select name="customer_type" class="form-select">
                                <option value="customer" {% if customer and customer.customer_type == 'customer' %}selected{% endif %}>Müşteri</option>
                                <option value="supplier" {% if customer and customer.customer_type == 'supplier' %}selected{% endif %}>Tedarikçi</option>
                                <option value="both" {% if customer and customer.customer_type == 'both' %}selected{% endif %}>Her İkisi</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Grup</label>
                            <input type="text" name="customer_group" class="form-control" value="{{ customer.customer_group if customer else '' }}" placeholder="Örn: VIP, Toptan">
                        </div>
                    </div>
                    
                    <!-- İLETİŞİM BİLGİLERİ -->
                    <h6 class="text-muted mb-3"><i class="bi bi-telephone me-2"></i>İletişim Bilgileri</h6>
                    <div class="row g-3 mb-4">
                        <div class="col-md-4">
                            <label class="form-label">Telefon</label>
                            <input type="tel" name="phone" class="form-control" value="{{ customer.phone if customer else '' }}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Telefon 2</label>
                            <input type="tel" name="phone2" class="form-control" value="{{ customer.phone2 if customer else '' }}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">WhatsApp</label>
                            <input type="tel" name="whatsapp_phone" class="form-control" value="{{ customer.whatsapp_phone if customer else '' }}" placeholder="Boşsa telefon kullanılır">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">E-posta</label>
                            <input type="email" name="email" class="form-control" value="{{ customer.email if customer else '' }}">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Website</label>
                            <input type="url" name="website" class="form-control" value="{{ customer.website if customer else '' }}">
                        </div>
                    </div>
                    
                    <!-- ADRES BİLGİLERİ -->
                    <h6 class="text-muted mb-3"><i class="bi bi-geo-alt me-2"></i>Adres Bilgileri</h6>
                    <div class="row g-3 mb-4">
                        <div class="col-12">
                            <label class="form-label">Adres</label>
                            <textarea name="address" class="form-control" rows="2">{{ customer.address if customer else '' }}</textarea>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Şehir</label>
                            <input type="text" name="city" class="form-control" value="{{ customer.city if customer else '' }}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">İlçe</label>
                            <input type="text" name="district" class="form-control" value="{{ customer.district if customer else '' }}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Posta Kodu</label>
                            <input type="text" name="postal_code" class="form-control" value="{{ customer.postal_code if customer else '' }}">
                        </div>
                    </div>
                    
                    <!-- TİCARİ BİLGİLER -->
                    <h6 class="text-muted mb-3"><i class="bi bi-building me-2"></i>Ticari Bilgiler</h6>
                    <div class="row g-3 mb-4">
                        <div class="col-md-4">
                            <label class="form-label">Vergi Dairesi</label>
                            <input type="text" name="tax_office" class="form-control" value="{{ customer.tax_office if customer else '' }}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Vergi No</label>
                            <input type="text" name="tax_number" class="form-control" value="{{ customer.tax_number if customer else '' }}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">TC Kimlik No</label>
                            <input type="text" name="id_number" class="form-control" value="{{ customer.id_number if customer else '' }}">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Kredi Limiti</label>
                            <div class="input-group">
                                <input type="number" step="0.01" name="credit_limit" class="form-control" value="{{ customer.credit_limit if customer else 0 }}">
                                <span class="input-group-text">₺</span>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Ödeme Vadesi (Gün)</label>
                            <input type="number" name="payment_term" class="form-control" value="{{ customer.payment_term if customer else 0 }}">
                        </div>
                    </div>
                    
                    <!-- NOTLAR -->
                    <div class="mb-4">
                        <label class="form-label">Notlar</label>
                        <textarea name="notes" class="form-control" rows="3">{{ customer.notes if customer else '' }}</textarea>
                    </div>
                    
                    <!-- BUTONLAR -->
                    <div class="d-flex justify-content-between">
                        <a href="{{ url_for('customers') }}" class="btn btn-outline-secondary">
                            <i class="bi bi-arrow-left me-1"></i>İptal
                        </a>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-check-lg me-1"></i>{{ 'Güncelle' if customer else 'Kaydet' }}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 6. MÜŞTERİ DETAY SAYFASI
# ----------------------------------------------------------------------------
CUSTOMER_DETAIL_HTML = '''
{% extends "base.html" %}
{% block title %}{{ customer.name }}{% endblock %}
{% block page_title %}{{ customer.name }}{% endblock %}
{% block mobile_title %}Cari Detay{% endblock %}

{% block header_actions %}
<div class="btn-group">
    <a href="{{ url_for('customer_edit', id=customer.id) }}" class="btn btn-outline-primary">
        <i class="bi bi-pencil me-1"></i>Düzenle
    </a>
    <a href="{{ url_for('customer_statement', id=customer.id) }}" class="btn btn-outline-secondary">
        <i class="bi bi-file-text me-1"></i>Ekstre
    </a>
    {% if whatsapp_enabled and customer.whatsapp_phone or customer.phone %}
    <a href="{{ customer.whatsapp_link }}" target="_blank" class="btn btn-success">
        <i class="bi bi-whatsapp me-1"></i>WhatsApp
    </a>
    {% endif %}
</div>
{% endblock %}

{% block content %}
<div class="row g-4">
    <!-- SOL KOLON - BİLGİLER -->
    <div class="col-12 col-lg-4">
        <!-- BAKİYE KARTI -->
        <div class="card mb-3">
            <div class="card-body text-center">
                <div class="mb-2 text-muted">Güncel Bakiye</div>
                {% if customer.balance > 0 %}
                    <div class="h2 text-success mb-1">+{{ "{:,.2f}".format(customer.balance) }}₺</div>
                    <span class="badge badge-success">Alacaklı</span>
                {% elif customer.balance < 0 %}
                    <div class="h2 text-danger mb-1">{{ "{:,.2f}".format(customer.balance) }}₺</div>
                    <span class="badge badge-danger">Borçlu</span>
                {% else %}
                    <div class="h2 text-muted mb-1">0,00₺</div>
                    <span class="badge badge-secondary">Bakiye Yok</span>
                {% endif %}
            </div>
        </div>
        
        <!-- İLETİŞİM BİLGİLERİ -->
        <div class="card mb-3">
            <div class="card-header"><i class="bi bi-info-circle me-2"></i>Bilgiler</div>
            <div class="card-body">
                <table class="table table-sm table-borderless mb-0">
                    <tr>
                        <td class="text-muted" style="width: 40%;">Tür</td>
                        <td>{{ 'Müşteri' if customer.customer_type == 'customer' else 'Tedarikçi' }}</td>
                    </tr>
                    {% if customer.phone %}
                    <tr>
                        <td class="text-muted">Telefon</td>
                        <td><a href="tel:{{ customer.phone }}">{{ customer.phone }}</a></td>
                    </tr>
                    {% endif %}
                    {% if customer.email %}
                    <tr>
                        <td class="text-muted">E-posta</td>
                        <td><a href="mailto:{{ customer.email }}">{{ customer.email }}</a></td>
                    </tr>
                    {% endif %}
                    {% if customer.city %}
                    <tr>
                        <td class="text-muted">Şehir</td>
                        <td>{{ customer.city }}{% if customer.district %}, {{ customer.district }}{% endif %}</td>
                    </tr>
                    {% endif %}
                    {% if customer.tax_number %}
                    <tr>
                        <td class="text-muted">Vergi No</td>
                        <td>{{ customer.tax_number }}</td>
                    </tr>
                    {% endif %}
                </table>
            </div>
        </div>
        
        <!-- HIZLI İŞLEMLER -->
        <div class="card">
            <div class="card-header"><i class="bi bi-lightning me-2"></i>Hızlı İşlemler</div>
            <div class="card-body">
                <div class="d-grid gap-2">
                    <a href="{{ url_for('cash_flow_add') }}?customer_id={{ customer.id }}&type=income" class="btn btn-outline-success btn-sm">
                        <i class="bi bi-plus-circle me-1"></i>Tahsilat Ekle
                    </a>
                    <a href="{{ url_for('cash_flow_add') }}?customer_id={{ customer.id }}&type=expense" class="btn btn-outline-danger btn-sm">
                        <i class="bi bi-dash-circle me-1"></i>Ödeme Ekle
                    </a>
                    <a href="{{ url_for('check_add') }}?customer_id={{ customer.id }}" class="btn btn-outline-primary btn-sm">
                        <i class="bi bi-credit-card me-1"></i>Çek/Senet Ekle
                    </a>
                </div>
            </div>
        </div>
    </div>
    
    <!-- SAĞ KOLON - HAREKETLER -->
    <div class="col-12 col-lg-8">
        <!-- SON HAREKETLER -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span><i class="bi bi-clock-history me-2"></i>Son Hareketler</span>
                <a href="{{ url_for('customer_statement', id=customer.id) }}" class="btn btn-sm btn-outline-primary">Tümünü Gör</a>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>Tarih</th>
                                <th>Açıklama</th>
                                <th class="text-end">Tutar</th>
                                <th class="text-end">Bakiye</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for trans in transactions[:10] %}
                            <tr>
                                <td>{{ trans.transaction_date }}</td>
                                <td>{{ trans.description or '-' }}</td>
                                <td class="text-end">
                                    {% if trans.transaction_type == 'credit' %}
                                        <span class="text-success">+{{ "{:,.2f}".format(trans.amount) }}₺</span>
                                    {% else %}
                                        <span class="text-danger">-{{ "{:,.2f}".format(trans.amount) }}₺</span>
                                    {% endif %}
                                </td>
                                <td class="text-end">{{ "{:,.2f}".format(trans.balance_after) }}₺</td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="4" class="text-center py-4 text-muted">Hareket bulunamadı</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- BEKLEYEN ÇEKLER -->
        {% if pending_checks %}
        <div class="card mt-3">
            <div class="card-header"><i class="bi bi-credit-card-2-back me-2"></i>Bekleyen Çek/Senetler</div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>No</th>
                                <th>Tür</th>
                                <th>Vade</th>
                                <th class="text-end">Tutar</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for check in pending_checks %}
                            <tr>
                                <td><a href="{{ url_for('check_detail', id=check.id) }}">{{ check.check_number }}</a></td>
                                <td>
                                    {% if check.check_type == 'incoming' %}
                                        <span class="badge badge-success">Alınan</span>
                                    {% else %}
                                        <span class="badge badge-danger">Verilen</span>
                                    {% endif %}
                                </td>
                                <td>{{ check.due_date }}</td>
                                <td class="text-end"><strong>{{ "{:,.2f}".format(check.remaining_amount) }}₺</strong></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}
'''

print("=" * 70)
print("✅ WEBAPP.PY - PARÇA 1/3 TAMAMLANDI!")
print("=" * 70)
print("📦 İçerik:")
print("  ✔️ Flask App + Yardımcı Fonksiyonlar")
print("  ✔️ BASE_HTML (Tam Mobil Uyumlu)")
print("  ✔️ LOGIN_HTML")
print("  ✔️ DASHBOARD_HTML")
print("  ✔️ CUSTOMERS_HTML (Liste)")
print("  ✔️ CUSTOMER_FORM_HTML (Ekle/Düzenle)")
print("  ✔️ CUSTOMER_DETAIL_HTML (Detay)")
print("=" * 70)# ============================================================================
# WEBAPP.PY - PARÇA 2/3: ÇEK/SENET + KASA + HATIRLATICI SAYFALARI
# ============================================================================

# ----------------------------------------------------------------------------
# 7. ÇEK/SENET LİSTESİ SAYFASI
# ----------------------------------------------------------------------------
CHECKS_HTML = '''
{% extends "base.html" %}
{% block title %}Çek/Senet{% endblock %}
{% block page_title %}Çek/Senet Takibi{% endblock %}
{% block mobile_title %}Çek/Senet{% endblock %}

{% block header_actions %}
<a href="{{ url_for('check_add') }}" class="btn btn-primary">
    <i class="bi bi-plus-lg me-1"></i>Yeni Ekle
</a>
{% endblock %}

{% block content %}
<!-- ÖZET KARTLARI -->
<div class="row g-3 mb-4">
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #10b981;">
            <div class="stat-label">Alınan (Bekleyen)</div>
            <div class="stat-value text-success">{{ "{:,.0f}".format(summary.incoming_pending_amount|default(0)) }}₺</div>
            <small class="text-muted">{{ summary.incoming_pending_count|default(0) }} Adet</small>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #ef4444;">
            <div class="stat-label">Verilen (Bekleyen)</div>
            <div class="stat-value text-danger">{{ "{:,.0f}".format(summary.outgoing_pending_amount|default(0)) }}₺</div>
            <small class="text-muted">{{ summary.outgoing_pending_count|default(0) }} Adet</small>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #f59e0b;">
            <div class="stat-label">Bu Hafta Vadeli</div>
            <div class="stat-value text-warning">{{ summary.this_week_count|default(0) }}</div>
            <small class="text-muted">{{ "{:,.0f}".format(summary.this_week_amount|default(0)) }}₺</small>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #dc2626;">
            <div class="stat-label">Vadesi Geçen</div>
            <div class="stat-value text-danger">{{ summary.overdue_count|default(0) }}</div>
            <small class="text-muted">{{ "{:,.0f}".format(summary.overdue_amount|default(0)) }}₺</small>
        </div>
    </div>
</div>

<!-- FİLTRELER -->
<div class="card mb-3">
    <div class="card-body py-2">
        <form method="GET" class="row g-2 align-items-center">
            <div class="col-auto">
                <select name="type" class="form-select form-select-sm" onchange="this.form.submit()">
                    <option value="">Tüm Türler</option>
                    <option value="incoming" {% if request.args.get('type') == 'incoming' %}selected{% endif %}>Alınan</option>
                    <option value="outgoing" {% if request.args.get('type') == 'outgoing' %}selected{% endif %}>Verilen</option>
                </select>
            </div>
            <div class="col-auto">
                <select name="status" class="form-select form-select-sm" onchange="this.form.submit()">
                    <option value="">Tüm Durumlar</option>
                    <option value="pending" {% if request.args.get('status') == 'pending' %}selected{% endif %}>Bekleyen</option>
                    <option value="upcoming" {% if request.args.get('status') == 'upcoming' %}selected{% endif %}>Yaklaşan</option>
                    <option value="overdue" {% if request.args.get('status') == 'overdue' %}selected{% endif %}>Gecikmiş</option>
                    <option value="cashed" {% if request.args.get('status') == 'cashed' %}selected{% endif %}>Tahsil Edilen</option>
                    <option value="endorsed" {% if request.args.get('status') == 'endorsed' %}selected{% endif %}>Ciro Edilen</option>
                    <option value="returned" {% if request.args.get('status') == 'returned' %}selected{% endif %}>İade</option>
                </select>
            </div>
            <div class="col">
                <input type="text" name="search" class="form-control form-control-sm" placeholder="Çek no, müşteri ara..." value="{{ request.args.get('search', '') }}">
            </div>
            <div class="col-auto">
                <button class="btn btn-sm btn-outline-primary" type="submit"><i class="bi bi-search"></i></button>
            </div>
        </form>
    </div>
</div>

<!-- LİSTE -->
<div class="card">
    <div class="card-body p-0">
        <!-- DESKTOP TABLE -->
        <div class="table-responsive desktop-table">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Çek/Senet No</th>
                        <th>Tür</th>
                        <th>Müşteri</th>
                        <th>Banka</th>
                        <th class="text-end">Tutar</th>
                        <th>Vade</th>
                        <th>Durum</th>
                        <th class="text-center">İşlem</th>
                    </tr>
                </thead>
                <tbody>
                    {% for check in checks %}
                    <tr class="{% if check.display_status == 'overdue' %}table-danger{% elif check.display_status == 'upcoming' %}table-warning{% endif %}">
                        <td>
                            <a href="{{ url_for('check_detail', id=check.id) }}" class="fw-bold text-decoration-none">
                                {{ check.check_number }}
                            </a>
                            <div class="small text-muted">
                                {% if check.payment_type == 'check' %}Çek{% else %}Senet{% endif %}
                            </div>
                        </td>
                        <td>
                            {% if check.check_type == 'incoming' %}
                                <span class="badge badge-success">Alınan</span>
                            {% else %}
                                <span class="badge badge-danger">Verilen</span>
                            {% endif %}
                        </td>
                        <td>{{ check.customer_name or '-' }}</td>
                        <td>
                            <small>{{ check.bank_name or '-' }}<br>{{ check.bank_branch or '' }}</small>
                        </td>
                        <td class="text-end">
                            <strong>{{ "{:,.2f}".format(check.amount) }}₺</strong>
                            {% if check.paid_amount > 0 and check.paid_amount < check.amount %}
                                <div class="small text-success">Ödenen: {{ "{:,.2f}".format(check.paid_amount) }}₺</div>
                            {% endif %}
                        </td>
                        <td>
                            {{ check.due_date }}
                            {% if check.days_until_due is not none and check.status == 'pending' %}
                                <div class="small {% if check.days_until_due < 0 %}text-danger{% elif check.days_until_due <= 7 %}text-warning{% else %}text-muted{% endif %}">
                                    {% if check.days_until_due < 0 %}
                                        {{ check.days_until_due|abs }} gün geçti
                                    {% elif check.days_until_due == 0 %}
                                        Bugün
                                    {% else %}
                                        {{ check.days_until_due }} gün kaldı
                                    {% endif %}
                                </div>
                            {% endif %}
                        </td>
                        <td>
                            {% if check.status == 'pending' %}
                                {% if check.display_status == 'overdue' %}
                                    <span class="badge badge-danger">Gecikmiş</span>
                                {% elif check.display_status == 'upcoming' %}
                                    <span class="badge badge-warning">Yaklaşan</span>
                                {% else %}
                                    <span class="badge badge-info">Bekliyor</span>
                                {% endif %}
                            {% elif check.status == 'cashed' %}
                                <span class="badge badge-success">Tahsil Edildi</span>
                            {% elif check.status == 'endorsed' %}
                                <span class="badge badge-secondary">Ciro Edildi</span>
                            {% elif check.status == 'returned' %}
                                <span class="badge badge-danger">İade</span>
                            {% elif check.status == 'cancelled' %}
                                <span class="badge badge-secondary">İptal</span>
                            {% endif %}
                        </td>
                        <td class="text-center">
                            <div class="dropdown">
                                <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                    <i class="bi bi-three-dots"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li><a class="dropdown-item" href="{{ url_for('check_detail', id=check.id) }}"><i class="bi bi-eye me-2"></i>Detay</a></li>
                                    {% if check.status == 'pending' %}
                                        <li><hr class="dropdown-divider"></li>
                                        <li><a class="dropdown-item text-success" href="#" onclick="processCheck({{ check.id }}, 'cashed')"><i class="bi bi-check-circle me-2"></i>Tahsil Et</a></li>
                                        <li><a class="dropdown-item" href="#" onclick="processCheck({{ check.id }}, 'partial')"><i class="bi bi-cash me-2"></i>Kısmi Tahsilat</a></li>
                                        {% if check.check_type == 'incoming' %}
                                            <li><a class="dropdown-item" href="#" data-bs-toggle="modal" data-bs-target="#endorseModal" data-check-id="{{ check.id }}"><i class="bi bi-arrow-repeat me-2"></i>Ciro Et</a></li>
                                        {% endif %}
                                        <li><hr class="dropdown-divider"></li>
                                        <li><a class="dropdown-item text-danger" href="#" onclick="processCheck({{ check.id }}, 'returned')"><i class="bi bi-x-circle me-2"></i>İade/Karşılıksız</a></li>
                                    {% endif %}
                                </ul>
                            </div>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="8" class="text-center py-5 text-muted">
                            <i class="bi bi-inbox d-block mb-2" style="font-size: 2rem;"></i>
                            Kayıt bulunamadı
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <!-- MOBILE LIST -->
        <div class="mobile-list p-3">
            {% for check in checks %}
            <div class="list-card {% if check.display_status == 'overdue' %}border-danger{% elif check.display_status == 'upcoming' %}border-warning{% endif %}" style="border-left: 3px solid;">
                <div class="list-card-header">
                    <div>
                        <a href="{{ url_for('check_detail', id=check.id) }}" class="list-card-title text-decoration-none">{{ check.check_number }}</a>
                        <div class="small">
                            {% if check.check_type == 'incoming' %}
                                <span class="badge badge-success">Alınan</span>
                            {% else %}
                                <span class="badge badge-danger">Verilen</span>
                            {% endif %}
                            {% if check.payment_type == 'check' %}<span class="badge badge-info">Çek</span>{% else %}<span class="badge badge-secondary">Senet</span>{% endif %}
                        </div>
                    </div>
                    <div class="text-end">
                        <strong>{{ "{:,.0f}".format(check.remaining_amount) }}₺</strong>
                        {% if check.status == 'pending' %}
                            {% if check.display_status == 'overdue' %}
                                <div class="small text-danger">Gecikmiş</div>
                            {% elif check.display_status == 'upcoming' %}
                                <div class="small text-warning">Yaklaşan</div>
                            {% endif %}
                        {% endif %}
                    </div>
                </div>
                <div class="list-card-body">
                    <div><i class="bi bi-person me-1"></i>{{ check.customer_name or '-' }}</div>
                    <div><i class="bi bi-bank me-1"></i>{{ check.bank_name or '-' }}</div>
                </div>
                <div class="list-card-footer">
                    <span><i class="bi bi-calendar me-1"></i>{{ check.due_date }}</span>
                    {% if check.status == 'pending' %}
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-success" onclick="processCheck({{ check.id }}, 'cashed')"><i class="bi bi-check"></i></button>
                            <a href="{{ url_for('check_detail', id=check.id) }}" class="btn btn-outline-primary"><i class="bi bi-eye"></i></a>
                        </div>
                    {% else %}
                        <span class="badge badge-{% if check.status == 'cashed' %}success{% elif check.status == 'returned' %}danger{% else %}secondary{% endif %}">
                            {% if check.status == 'cashed' %}Tahsil{% elif check.status == 'returned' %}İade{% elif check.status == 'endorsed' %}Ciro{% else %}{{ check.status }}{% endif %}
                        </span>
                    {% endif %}
                </div>
            </div>
            {% else %}
            <div class="empty-state">
                <i class="bi bi-credit-card-2-back"></i>
                <h5>Kayıt bulunamadı</h5>
            </div>
            {% endfor %}
        </div>
    </div>
</div>

<!-- FAB -->
<a href="{{ url_for('check_add') }}" class="fab"><i class="bi bi-plus-lg"></i></a>

<!-- CİRO MODAL -->
<div class="modal fade" id="endorseModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title"><i class="bi bi-arrow-repeat me-2"></i>Çek Ciro Et</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form id="endorseForm" method="POST" action="{{ url_for('check_endorse') }}">
                <div class="modal-body">
                    <input type="hidden" name="check_id" id="endorseCheckId">
                    <div class="mb-3">
                        <label class="form-label">Ciro Edilen Kişi/Firma *</label>
                        <input type="text" name="endorser_name" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Vergi/TC No</label>
                        <input type="text" name="endorser_tax_no" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Telefon</label>
                        <input type="text" name="endorser_phone" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Açıklama</label>
                        <textarea name="description" class="form-control" rows="2"></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">İptal</button>
                    <button type="submit" class="btn btn-primary">Ciro Et</button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- KISMİ TAHSİLAT MODAL -->
<div class="modal fade" id="partialModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title"><i class="bi bi-cash me-2"></i>Kısmi Tahsilat</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form id="partialForm" method="POST" action="{{ url_for('check_process') }}">
                <div class="modal-body">
                    <input type="hidden" name="check_id" id="partialCheckId">
                    <input type="hidden" name="status" value="partial">
                    <div class="mb-3">
                        <label class="form-label">Tahsil Edilecek Tutar *</label>
                        <div class="input-group">
                            <input type="number" step="0.01" name="amount" class="form-control" required>
                            <span class="input-group-text">₺</span>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Açıklama</label>
                        <textarea name="description" class="form-control" rows="2"></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">İptal</button>
                    <button type="submit" class="btn btn-success">Tahsil Et</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
function processCheck(checkId, status) {
    if (status === 'partial') {
        document.getElementById('partialCheckId').value = checkId;
        new bootstrap.Modal(document.getElementById('partialModal')).show();
        return;
    }
    
    const messages = {
        'cashed': 'Bu çek/senedi tahsil edildi olarak işaretlemek istiyor musunuz?',
        'returned': 'Bu çek/senedi iade/karşılıksız olarak işaretlemek istiyor musunuz?'
    };
    
    if (confirm(messages[status] || 'Bu işlemi yapmak istiyor musunuz?')) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '{{ url_for("check_process") }}';
        form.innerHTML = `<input name="check_id" value="${checkId}"><input name="status" value="${status}">`;
        document.body.appendChild(form);
        form.submit();
    }
}

// Ciro modal
document.getElementById('endorseModal').addEventListener('show.bs.modal', function(e) {
    const checkId = e.relatedTarget.dataset.checkId;
    document.getElementById('endorseCheckId').value = checkId;
});
</script>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 8. ÇEK/SENET EKLEME FORMU
# ----------------------------------------------------------------------------
CHECK_FORM_HTML = '''
{% extends "base.html" %}
{% block title %}{{ 'Çek/Senet Düzenle' if check else 'Yeni Çek/Senet' }}{% endblock %}
{% block page_title %}{{ 'Çek/Senet Düzenle' if check else 'Yeni Çek/Senet' }}{% endblock %}
{% block mobile_title %}{{ 'Düzenle' if check else 'Yeni Çek/Senet' }}{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-12 col-lg-8">
        <div class="card">
            <div class="card-body">
                <form method="POST">
                    <!-- TÜR SEÇİMİ -->
                    <div class="row g-3 mb-4">
                        <div class="col-md-6">
                            <label class="form-label">İşlem Türü *</label>
                            <select name="check_type" class="form-select" required>
                                <option value="incoming" {% if check and check.check_type == 'incoming' %}selected{% endif %} {% if request.args.get('type') == 'incoming' %}selected{% endif %}>Alınan (Müşteriden)</option>
                                <option value="outgoing" {% if check and check.check_type == 'outgoing' %}selected{% endif %} {% if request.args.get('type') == 'outgoing' %}selected{% endif %}>Verilen (Tedarikçiye)</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Ödeme Aracı *</label>
                            <select name="payment_type" class="form-select" required>
                                <option value="check" {% if check and check.payment_type == 'check' %}selected{% endif %}>Çek</option>
                                <option value="promissory_note" {% if check and check.payment_type == 'promissory_note' %}selected{% endif %}>Senet</option>
                            </select>
                        </div>
                    </div>
                    
                    <!-- ÇEK BİLGİLERİ -->
                    <h6 class="text-muted mb-3"><i class="bi bi-credit-card me-2"></i>Çek/Senet Bilgileri</h6>
                    <div class="row g-3 mb-4">
                        <div class="col-md-6">
                            <label class="form-label">Çek/Senet No *</label>
                            <input type="text" name="check_number" class="form-control" value="{{ check.check_number if check else '' }}" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Cari Hesap</label>
                            <select name="customer_id" class="form-select">
                                <option value="">Seçiniz</option>
                                {% for c in customers %}
                                    <option value="{{ c.id }}" {% if (check and check.customer_id == c.id) or request.args.get('customer_id')|int == c.id %}selected{% endif %}>{{ c.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Tutar *</label>
                            <div class="input-group">
                                <input type="number" step="0.01" name="amount" class="form-control" value="{{ check.amount if check else '' }}" required>
                                <span class="input-group-text">₺</span>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Düzenleme Tarihi</label>
                            <input type="date" name="issue_date" class="form-control" value="{{ check.issue_date if check else today }}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Vade Tarihi *</label>
                            <input type="date" name="due_date" class="form-control" value="{{ check.due_date if check else '' }}" required>
                        </div>
                    </div>
                    
                    <!-- BANKA BİLGİLERİ -->
                    <h6 class="text-muted mb-3"><i class="bi bi-bank me-2"></i>Banka Bilgileri</h6>
                    <div class="row g-3 mb-4">
                        <div class="col-md-4">
                            <label class="form-label">Banka Adı</label>
                            <input type="text" name="bank_name" class="form-control" value="{{ check.bank_name if check else '' }}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Şube</label>
                            <input type="text" name="bank_branch" class="form-control" value="{{ check.bank_branch if check else '' }}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Hesap No</label>
                            <input type="text" name="account_number" class="form-control" value="{{ check.account_number if check else '' }}">
                        </div>
                        <div class="col-12">
                            <label class="form-label">IBAN</label>
                            <input type="text" name="iban" class="form-control" value="{{ check.iban if check else '' }}" placeholder="TR...">
                        </div>
                    </div>
                    
                    <!-- KEŞİDECİ BİLGİLERİ -->
                    <h6 class="text-muted mb-3"><i class="bi bi-person-badge me-2"></i>Keşideci Bilgileri</h6>
                    <div class="row g-3 mb-4">
                        <div class="col-md-6">
                            <label class="form-label">Keşideci Adı</label>
                            <input type="text" name="drawer_name" class="form-control" value="{{ check.drawer_name if check else '' }}">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Keşideci Vergi/TC No</label>
                            <input type="text" name="drawer_tax_no" class="form-control" value="{{ check.drawer_tax_no if check else '' }}">
                        </div>
                    </div>
                    
                    <!-- NOTLAR -->
                    <div class="mb-4">
                        <label class="form-label">Notlar</label>
                        <textarea name="notes" class="form-control" rows="2">{{ check.notes if check else '' }}</textarea>
                    </div>
                    
                    <!-- BUTONLAR -->
                    <div class="d-flex justify-content-between">
                        <a href="{{ url_for('checks') }}" class="btn btn-outline-secondary">
                            <i class="bi bi-arrow-left me-1"></i>İptal
                        </a>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-check-lg me-1"></i>{{ 'Güncelle' if check else 'Kaydet' }}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 9. ÇEK/SENET DETAY SAYFASI
# ----------------------------------------------------------------------------
CHECK_DETAIL_HTML = '''
{% extends "base.html" %}
{% block title %}Çek/Senet #{{ check.check_number }}{% endblock %}
{% block page_title %}{{ check.check_number }}{% endblock %}
{% block mobile_title %}Çek Detay{% endblock %}

{% block header_actions %}
{% if check.status == 'pending' %}
<div class="btn-group">
    <button class="btn btn-success" onclick="processCheck({{ check.id }}, 'cashed')">
        <i class="bi bi-check-circle me-1"></i>Tahsil Et
    </button>
    <button type="button" class="btn btn-success dropdown-toggle dropdown-toggle-split" data-bs-toggle="dropdown"></button>
    <ul class="dropdown-menu">
        <li><a class="dropdown-item" href="#" onclick="processCheck({{ check.id }}, 'partial')"><i class="bi bi-cash me-2"></i>Kısmi Tahsilat</a></li>
        {% if check.check_type == 'incoming' %}
        <li><a class="dropdown-item" href="#" data-bs-toggle="modal" data-bs-target="#endorseModal"><i class="bi bi-arrow-repeat me-2"></i>Ciro Et</a></li>
        {% endif %}
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item text-danger" href="#" onclick="processCheck({{ check.id }}, 'returned')"><i class="bi bi-x-circle me-2"></i>İade/Karşılıksız</a></li>
    </ul>
</div>
{% endif %}
{% endblock %}

{% block content %}
<div class="row g-4">
    <!-- SOL KOLON -->
    <div class="col-12 col-lg-5">
        <!-- DURUM KARTI -->
        <div class="card mb-3">
            <div class="card-body text-center">
                {% if check.status == 'pending' %}
                    {% if check.display_status == 'overdue' %}
                        <div class="rounded-circle bg-danger bg-opacity-10 d-inline-flex align-items-center justify-content-center mb-3" style="width: 80px; height: 80px;">
                            <i class="bi bi-exclamation-triangle text-danger" style="font-size: 2.5rem;"></i>
                        </div>
                        <h5 class="text-danger">Vadesi Geçti</h5>
                        <p class="text-muted mb-0">{{ check.days_until_due|abs }} gün önce</p>
                    {% elif check.display_status == 'upcoming' %}
                        <div class="rounded-circle bg-warning bg-opacity-10 d-inline-flex align-items-center justify-content-center mb-3" style="width: 80px; height: 80px;">
                            <i class="bi bi-clock text-warning" style="font-size: 2.5rem;"></i>
                        </div>
                        <h5 class="text-warning">Vade Yaklaşıyor</h5>
                        <p class="text-muted mb-0">{{ check.days_until_due }} gün kaldı</p>
                    {% else %}
                        <div class="rounded-circle bg-info bg-opacity-10 d-inline-flex align-items-center justify-content-center mb-3" style="width: 80px; height: 80px;">
                            <i class="bi bi-hourglass-split text-info" style="font-size: 2.5rem;"></i>
                        </div>
                        <h5 class="text-info">Bekliyor</h5>
                        <p class="text-muted mb-0">{{ check.days_until_due }} gün kaldı</p>
                    {% endif %}
                {% elif check.status == 'cashed' %}
                    <div class="rounded-circle bg-success bg-opacity-10 d-inline-flex align-items-center justify-content-center mb-3" style="width: 80px; height: 80px;">
                        <i class="bi bi-check-circle text-success" style="font-size: 2.5rem;"></i>
                    </div>
                    <h5 class="text-success">Tahsil Edildi</h5>
                {% elif check.status == 'endorsed' %}
                    <div class="rounded-circle bg-secondary bg-opacity-10 d-inline-flex align-items-center justify-content-center mb-3" style="width: 80px; height: 80px;">
                        <i class="bi bi-arrow-repeat text-secondary" style="font-size: 2.5rem;"></i>
                    </div>
                    <h5 class="text-secondary">Ciro Edildi</h5>
                    <p class="text-muted mb-0">{{ check.endorser_name }}</p>
                {% elif check.status == 'returned' %}
                    <div class="rounded-circle bg-danger bg-opacity-10 d-inline-flex align-items-center justify-content-center mb-3" style="width: 80px; height: 80px;">
                        <i class="bi bi-x-circle text-danger" style="font-size: 2.5rem;"></i>
                    </div>
                    <h5 class="text-danger">İade/Karşılıksız</h5>
                {% endif %}
                
                <hr>
                
                <div class="h2 mb-1">{{ "{:,.2f}".format(check.amount) }}₺</div>
                {% if check.paid_amount > 0 and check.paid_amount < check.amount %}
                    <div class="text-success">Ödenen: {{ "{:,.2f}".format(check.paid_amount) }}₺</div>
                    <div class="text-warning">Kalan: {{ "{:,.2f}".format(check.remaining_amount) }}₺</div>
                {% endif %}
            </div>
        </div>
        
        <!-- BİLGİLER -->
        <div class="card">
            <div class="card-header"><i class="bi bi-info-circle me-2"></i>Detaylar</div>
            <div class="card-body">
                <table class="table table-sm table-borderless mb-0">
                    <tr>
                        <td class="text-muted" style="width: 40%;">Tür</td>
                        <td>
                            {% if check.check_type == 'incoming' %}
                                <span class="badge badge-success">Alınan</span>
                            {% else %}
                                <span class="badge badge-danger">Verilen</span>
                            {% endif %}
                            {% if check.payment_type == 'check' %}Çek{% else %}Senet{% endif %}
                        </td>
                    </tr>
                    <tr>
                        <td class="text-muted">Çek/Senet No</td>
                        <td><strong>{{ check.check_number }}</strong></td>
                    </tr>
                    {% if check.customer_name %}
                    <tr>
                        <td class="text-muted">Cari</td>
                        <td><a href="{{ url_for('customer_detail', id=check.customer_id) }}">{{ check.customer_name }}</a></td>
                    </tr>
                    {% endif %}
                    <tr>
                        <td class="text-muted">Vade Tarihi</td>
                        <td>{{ check.due_date }}</td>
                    </tr>
                    {% if check.bank_name %}
                    <tr>
                        <td class="text-muted">Banka</td>
                        <td>{{ check.bank_name }} {{ check.bank_branch or '' }}</td>
                    </tr>
                    {% endif %}
                    {% if check.drawer_name %}
                    <tr>
                        <td class="text-muted">Keşideci</td>
                        <td>{{ check.drawer_name }}</td>
                    </tr>
                    {% endif %}
                    {% if check.notes %}
                    <tr>
                        <td class="text-muted">Not</td>
                        <td>{{ check.notes }}</td>
                    </tr>
                    {% endif %}
                </table>
            </div>
        </div>
    </div>
    
    <!-- SAĞ KOLON - HAREKET GEÇMİŞİ -->
    <div class="col-12 col-lg-7">
        <div class="card">
            <div class="card-header"><i class="bi bi-clock-history me-2"></i>Hareket Geçmişi</div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>Tarih</th>
                                <th>İşlem</th>
                                <th>Tutar</th>
                                <th>Açıklama</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for trans in transactions %}
                            <tr>
                                <td>{{ trans.transaction_date[:16] }}</td>
                                <td>
                                    {% if trans.transaction_type == 'created' %}
                                        <span class="badge badge-info">Oluşturuldu</span>
                                    {% elif trans.transaction_type == 'partial_payment' %}
                                        <span class="badge badge-success">Kısmi Tahsilat</span>
                                    {% elif trans.transaction_type == 'cashed' %}
                                        <span class="badge badge-success">Tahsil Edildi</span>
                                    {% elif trans.transaction_type == 'endorsed' %}
                                        <span class="badge badge-secondary">Ciro Edildi</span>
                                    {% elif trans.transaction_type == 'returned' %}
                                        <span class="badge badge-danger">İade</span>
                                    {% else %}
                                        <span class="badge badge-secondary">{{ trans.transaction_type }}</span>
                                    {% endif %}
                                </td>
                                <td>
                                    {% if trans.amount > 0 %}
                                        {{ "{:,.2f}".format(trans.amount) }}₺
                                    {% else %}
                                        -
                                    {% endif %}
                                </td>
                                <td>{{ trans.description or '-' }}</td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="4" class="text-center py-4 text-muted">Hareket bulunamadı</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        {% if whatsapp_enabled and check.customer_phone and check.status == 'pending' %}
        <div class="card mt-3">
            <div class="card-header"><i class="bi bi-whatsapp me-2"></i>WhatsApp Hatırlatma</div>
            <div class="card-body">
                <p class="text-muted small">Müşteriye çek vadesi hakkında WhatsApp mesajı gönderin.</p>
                <a href="{{ check.whatsapp_link }}" target="_blank" class="btn btn-success">
                    <i class="bi bi-whatsapp me-2"></i>Mesaj Gönder
                </a>
            </div>
        </div>
        {% endif %}
    </div>
</div>

{% if check.status == 'pending' %}
<!-- CİRO MODAL -->
<div class="modal fade" id="endorseModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Çek Ciro Et</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form method="POST" action="{{ url_for('check_endorse') }}">
                <div class="modal-body">
                    <input type="hidden" name="check_id" value="{{ check.id }}">
                    <div class="mb-3">
                        <label class="form-label">Ciro Edilen Kişi/Firma *</label>
                        <input type="text" name="endorser_name" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Vergi/TC No</label>
                        <input type="text" name="endorser_tax_no" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Açıklama</label>
                        <textarea name="description" class="form-control" rows="2"></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">İptal</button>
                    <button type="submit" class="btn btn-primary">Ciro Et</button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- KISMİ TAHSİLAT MODAL -->
<div class="modal fade" id="partialModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Kısmi Tahsilat</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form method="POST" action="{{ url_for('check_process') }}">
                <div class="modal-body">
                    <input type="hidden" name="check_id" value="{{ check.id }}">
                    <input type="hidden" name="status" value="partial">
                    <div class="mb-3">
                        <label class="form-label">Tahsil Edilecek Tutar *</label>
                        <div class="input-group">
                            <input type="number" step="0.01" name="amount" class="form-control" max="{{ check.remaining_amount }}" required>
                            <span class="input-group-text">₺</span>
                        </div>
                        <small class="text-muted">Kalan: {{ "{:,.2f}".format(check.remaining_amount) }}₺</small>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Açıklama</label>
                        <textarea name="description" class="form-control" rows="2"></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">İptal</button>
                    <button type="submit" class="btn btn-success">Tahsil Et</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endif %}
{% endblock %}

{% block extra_js %}
<script>
function processCheck(checkId, status) {
    if (status === 'partial') {
        new bootstrap.Modal(document.getElementById('partialModal')).show();
        return;
    }
    
    const messages = {
        'cashed': 'Bu çek/senedi tahsil edildi olarak işaretlemek istiyor musunuz?',
        'returned': 'Bu çek/senedi iade/karşılıksız olarak işaretlemek istiyor musunuz?'
    };
    
    if (confirm(messages[status])) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '{{ url_for("check_process") }}';
        form.innerHTML = `<input name="check_id" value="${checkId}"><input name="status" value="${status}">`;
        document.body.appendChild(form);
        form.submit();
    }
}
</script>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 10. KASA LİSTESİ SAYFASI
# ----------------------------------------------------------------------------
CASHFLOW_HTML = '''
{% extends "base.html" %}
{% block title %}Kasa{% endblock %}
{% block page_title %}Kasa Yönetimi{% endblock %}
{% block mobile_title %}Kasa{% endblock %}

{% block header_actions %}
<div class="btn-group">
    <a href="{{ url_for('cash_flow_add') }}?type=income" class="btn btn-success">
        <i class="bi bi-plus-lg me-1"></i>Gelir
    </a>
    <a href="{{ url_for('cash_flow_add') }}?type=expense" class="btn btn-danger">
        <i class="bi bi-dash-lg me-1"></i>Gider
    </a>
</div>
{% endblock %}

{% block content %}
<!-- ÖZET KARTLARI -->
<div class="row g-3 mb-4">
    <div class="col-6 col-lg-3">
        <div class="stat-card">
            <div class="stat-label">Toplam Bakiye</div>
            <div class="stat-value {% if balance.balance >= 0 %}text-success{% else %}text-danger{% endif %}">
                {{ "{:,.0f}".format(balance.balance) }}₺
            </div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="stat-card">
            <div class="stat-label">Bugün Gelir</div>
            <div class="stat-value text-success">+{{ "{:,.0f}".format(balance.today_income) }}₺</div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="stat-card">
            <div class="stat-label">Bugün Gider</div>
            <div class="stat-value text-danger">-{{ "{:,.0f}".format(balance.today_expense) }}₺</div>
        </div>
    </div>
    <div class="col-6 col-lg-3">
        <div class="stat-card">
            <div class="stat-label">Bu Ay Net</div>
            <div class="stat-value {% if balance.month_balance >= 0 %}text-success{% else %}text-danger{% endif %}">
                {{ "{:,.0f}".format(balance.month_balance) }}₺
            </div>
        </div>
    </div>
</div>

<!-- FİLTRELER -->
<div class="card mb-3">
    <div class="card-body py-2">
        <form method="GET" class="row g-2 align-items-center">
            <div class="col-auto">
                <select name="type" class="form-select form-select-sm" onchange="this.form.submit()">
                    <option value="">Tümü</option>
                    <option value="income" {% if request.args.get('type') == 'income' %}selected{% endif %}>Gelirler</option>
                    <option value="expense" {% if request.args.get('type') == 'expense' %}selected{% endif %}>Giderler</option>
                </select>
            </div>
            <div class="col-auto">
                <select name="category" class="form-select form-select-sm" onchange="this.form.submit()">
                    <option value="">Tüm Kategoriler</option>
                    {% for cat in categories %}
                        <option value="{{ cat.name }}" {% if request.args.get('category') == cat.name %}selected{% endif %}>{{ cat.icon }} {{ cat.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-auto">
                <input type="date" name="start_date" class="form-control form-control-sm" value="{{ request.args.get('start_date', '') }}" onchange="this.form.submit()">
            </div>
            <div class="col-auto">
                <input type="date" name="end_date" class="form-control form-control-sm" value="{{ request.args.get('end_date', '') }}" onchange="this.form.submit()">
            </div>
        </form>
    </div>
</div>

<!-- LİSTE -->
<div class="card">
    <div class="card-body p-0">
        <div class="table-responsive desktop-table">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Tarih</th>
                        <th>Tür</th>
                        <th>Kategori</th>
                        <th>Açıklama</th>
                        <th>Cari</th>
                        <th class="text-end">Tutar</th>
                    </tr>
                </thead>
                <tbody>
                    {% for trans in transactions %}
                    <tr>
                        <td>{{ trans.transaction_date }}</td>
                        <td>
                            {% if trans.transaction_type == 'income' %}
                                <span class="badge badge-success">Gelir</span>
                            {% else %}
                                <span class="badge badge-danger">Gider</span>
                            {% endif %}
                        </td>
                        <td>
                            <span style="color: {{ trans.category_color or '#6c757d' }}">{{ trans.category_icon or '📁' }}</span>
                            {{ trans.category }}
                        </td>
                        <td>{{ trans.description or '-' }}</td>
                        <td>
                            {% if trans.customer_name %}
                                <a href="{{ url_for('customer_detail', id=trans.customer_id) }}">{{ trans.customer_name }}</a>
                            {% else %}
                                -
                            {% endif %}
                        </td>
                        <td class="text-end">
                            {% if trans.transaction_type == 'income' %}
                                <span class="text-success fw-bold">+{{ "{:,.2f}".format(trans.amount) }}₺</span>
                            {% else %}
                                <span class="text-danger fw-bold">-{{ "{:,.2f}".format(trans.amount) }}₺</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="6" class="text-center py-5 text-muted">
                            <i class="bi bi-inbox d-block mb-2" style="font-size: 2rem;"></i>
                            Kayıt bulunamadı
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="mobile-list p-3">
            {% for trans in transactions %}
            <div class="list-card">
                <div class="list-card-header">
                    <div>
                        {% if trans.transaction_type == 'income' %}
                            <span class="badge badge-success">Gelir</span>
                        {% else %}
                            <span class="badge badge-danger">Gider</span>
                        {% endif %}
                        <span class="ms-1">{{ trans.category }}</span>
                    </div>
                    {% if trans.transaction_type == 'income' %}
                        <span class="text-success fw-bold">+{{ "{:,.0f}".format(trans.amount) }}₺</span>
                    {% else %}
                        <span class="text-danger fw-bold">-{{ "{:,.0f}".format(trans.amount) }}₺</span>
                    {% endif %}
                </div>
                <div class="list-card-body">
                    {{ trans.description or '-' }}
                    {% if trans.customer_name %}
                        <div class="small"><i class="bi bi-person me-1"></i>{{ trans.customer_name }}</div>
                    {% endif %}
                </div>
                <div class="list-card-footer">
                    <span><i class="bi bi-calendar me-1"></i>{{ trans.transaction_date }}</span>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>

<!-- FAB -->
<button class="fab" data-bs-toggle="modal" data-bs-target="#quickAddModal">
    <i class="bi bi-plus-lg"></i>
</button>

<!-- HIZLI EKLEME MODAL -->
<div class="modal fade" id="quickAddModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Hızlı İşlem</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body text-center">
                <div class="d-grid gap-3">
                    <a href="{{ url_for('cash_flow_add') }}?type=income" class="btn btn-success btn-lg py-3">
                        <i class="bi bi-plus-circle me-2"></i>Gelir Ekle
                    </a>
                    <a href="{{ url_for('cash_flow_add') }}?type=expense" class="btn btn-danger btn-lg py-3">
                        <i class="bi bi-dash-circle me-2"></i>Gider Ekle
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 11. KASA EKLEME FORMU
# ----------------------------------------------------------------------------
CASHFLOW_FORM_HTML = '''
{% extends "base.html" %}
{% block title %}{{ 'Gelir Ekle' if trans_type == 'income' else 'Gider Ekle' }}{% endblock %}
{% block page_title %}{{ 'Gelir Ekle' if trans_type == 'income' else 'Gider Ekle' }}{% endblock %}
{% block mobile_title %}{{ 'Gelir' if trans_type == 'income' else 'Gider' }}{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-12 col-lg-6">
        <div class="card">
            <div class="card-body">
                <form method="POST">
                    <input type="hidden" name="transaction_type" value="{{ trans_type }}">
                    
                    <!-- TÜR GÖSTERGESİ -->
                    <div class="text-center mb-4">
                        {% if trans_type == 'income' %}
                            <div class="rounded-circle bg-success bg-opacity-10 d-inline-flex align-items-center justify-content-center mb-2" style="width: 60px; height: 60px;">
                                <i class="bi bi-plus-circle text-success" style="font-size: 2rem;"></i>
                            </div>
                            <h5 class="text-success">Gelir Kaydı</h5>
                        {% else %}
                            <div class="rounded-circle bg-danger bg-opacity-10 d-inline-flex align-items-center justify-content-center mb-2" style="width: 60px; height: 60px;">
                                <i class="bi bi-dash-circle text-danger" style="font-size: 2rem;"></i>
                            </div>
                            <h5 class="text-danger">Gider Kaydı</h5>
                        {% endif %}
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Tutar *</label>
                        <div class="input-group input-group-lg">
                            <input type="number" step="0.01" name="amount" class="form-control" required autofocus>
                            <span class="input-group-text">₺</span>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Kategori *</label>
                        <select name="category" class="form-select" required>
                            <option value="">Seçiniz</option>
                            {% for cat in categories %}
                                <option value="{{ cat.name }}">{{ cat.icon }} {{ cat.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Cari Hesap</label>
                        <select name="customer_id" class="form-select">
                            <option value="">Seçiniz (Opsiyonel)</option>
                            {% for c in customers %}
                                <option value="{{ c.id }}" {% if request.args.get('customer_id')|int == c.id %}selected{% endif %}>{{ c.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Tarih</label>
                        <input type="date" name="transaction_date" class="form-control" value="{{ today }}">
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Ödeme Yöntemi</label>
                        <select name="payment_method" class="form-select">
                            <option value="cash">Nakit</option>
                            <option value="bank">Banka/Havale</option>
                            <option value="credit_card">Kredi Kartı</option>
                            <option value="check">Çek</option>
                            <option value="other">Diğer</option>
                        </select>
                    </div>
                    
                    <div class="mb-4">
                        <label class="form-label">Açıklama</label>
                        <textarea name="description" class="form-control" rows="2" placeholder="İşlem detayı..."></textarea>
                    </div>
                    
                    <div class="d-flex justify-content-between">
                        <a href="{{ url_for('cash_flow') }}" class="btn btn-outline-secondary">
                            <i class="bi bi-arrow-left me-1"></i>İptal
                        </a>
                        <button type="submit" class="btn btn-{{ 'success' if trans_type == 'income' else 'danger' }}">
                            <i class="bi bi-check-lg me-1"></i>Kaydet
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 12. HATIRLATICILAR SAYFASI
# ----------------------------------------------------------------------------
REMINDERS_HTML = '''
{% extends "base.html" %}
{% block title %}Hatırlatıcılar{% endblock %}
{% block page_title %}Hatırlatıcılar{% endblock %}
{% block mobile_title %}Hatırlatıcılar{% endblock %}

{% block header_actions %}
<a href="{{ url_for('reminder_add') }}" class="btn btn-primary">
    <i class="bi bi-plus-lg me-1"></i>Yeni Hatırlatıcı
</a>
{% endblock %}

{% block content %}
<!-- ÖZET -->
<div class="row g-3 mb-4">
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #ef4444;">
            <div class="stat-label">Gecikmiş</div>
            <div class="stat-value text-danger">{{ summary.overdue|default(0) }}</div>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #f59e0b;">
            <div class="stat-label">Bugün</div>
            <div class="stat-value text-warning">{{ summary.today|default(0) }}</div>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #3b82f6;">
            <div class="stat-label">Yarın</div>
            <div class="stat-value text-info">{{ summary.tomorrow|default(0) }}</div>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #6b7280;">
            <div class="stat-label">Bu Hafta</div>
            <div class="stat-value">{{ summary.this_week|default(0) }}</div>
        </div>
    </div>
</div>

<!-- FİLTRELER -->
<div class="card mb-3">
    <div class="card-body py-2">
        <form method="GET" class="row g-2 align-items-center">
            <div class="col-auto">
                <select name="status" class="form-select form-select-sm" onchange="this.form.submit()">
                    <option value="">Tüm Bekleyenler</option>
                    <option value="overdue" {% if request.args.get('status') == 'overdue' %}selected{% endif %}>Gecikmiş</option>
                    <option value="today" {% if request.args.get('status') == 'today' %}selected{% endif %}>Bugün</option>
                    <option value="upcoming" {% if request.args.get('status') == 'upcoming' %}selected{% endif %}>Yaklaşan</option>
                    <option value="completed" {% if request.args.get('status') == 'completed' %}selected{% endif %}>Tamamlanan</option>
                </select>
            </div>
            <div class="col-auto">
                <select name="type" class="form-select form-select-sm" onchange="this.form.submit()">
                    <option value="">Tüm Türler</option>
                    <option value="general" {% if request.args.get('type') == 'general' %}selected{% endif %}>Genel</option>
                    <option value="check" {% if request.args.get('type') == 'check' %}selected{% endif %}>Çek/Senet</option>
                    <option value="payment" {% if request.args.get('type') == 'payment' %}selected{% endif %}>Ödeme</option>
                </select>
            </div>
            <div class="col-auto">
                <select name="priority" class="form-select form-select-sm" onchange="this.form.submit()">
                    <option value="">Tüm Öncelikler</option>
                    <option value="high" {% if request.args.get('priority') == 'high' %}selected{% endif %}>Yüksek</option>
                    <option value="normal" {% if request.args.get('priority') == 'normal' %}selected{% endif %}>Normal</option>
                    <option value="low" {% if request.args.get('priority') == 'low' %}selected{% endif %}>Düşük</option>
                </select>
            </div>
        </form>
    </div>
</div>

<!-- LİSTE -->
<div class="card">
    <div class="card-body p-0">
        <div class="mobile-list desktop-table p-3">
            {% for reminder in reminders %}
            <div class="list-card {% if reminder.display_status == 'overdue' %}border-danger{% elif reminder.display_status == 'today' %}border-warning{% endif %}" style="border-left: 3px solid;">
                <div class="list-card-header">
                    <div class="d-flex align-items-center gap-2">
                        <div class="rounded-circle d-flex align-items-center justify-content-center {% if reminder.priority == 'high' %}bg-danger{% elif reminder.priority == 'low' %}bg-secondary{% else %}bg-primary{% endif %} bg-opacity-10" style="width: 36px; height: 36px;">
                            {% if reminder.reminder_type == 'check' %}
                                <i class="bi bi-credit-card {% if reminder.priority == 'high' %}text-danger{% elif reminder.priority == 'low' %}text-secondary{% else %}text-primary{% endif %}"></i>
                            {% elif reminder.reminder_type == 'payment' %}
                                <i class="bi bi-cash {% if reminder.priority == 'high' %}text-danger{% elif reminder.priority == 'low' %}text-secondary{% else %}text-primary{% endif %}"></i>
                            {% else %}
                                <i class="bi bi-bell {% if reminder.priority == 'high' %}text-danger{% elif reminder.priority == 'low' %}text-secondary{% else %}text-primary{% endif %}"></i>
                            {% endif %}
                        </div>
                        <div>
                            <strong>{{ reminder.title }}</strong>
                            {% if reminder.is_recurring %}<i class="bi bi-arrow-repeat ms-1 text-muted" title="Tekrarlayan"></i>{% endif %}
                        </div>
                    </div>
                    <div>
                        {% if reminder.status == 'completed' %}
                            <span class="badge badge-success">Tamamlandı</span>
                        {% elif reminder.display_status == 'overdue' %}
                            <span class="badge badge-danger">Gecikmiş</span>
                        {% elif reminder.display_status == 'today' %}
                            <span class="badge badge-warning">Bugün</span>
                        {% elif reminder.display_status == 'tomorrow' %}
                            <span class="badge badge-info">Yarın</span>
                        {% endif %}
                    </div>
                </div>
                {% if reminder.description %}
                <div class="list-card-body">{{ reminder.description }}</div>
                {% endif %}
                <div class="list-card-footer">
                    <div>
                        <i class="bi bi-calendar me-1"></i>{{ reminder.due_date }}
                        {% if reminder.due_time %}<span class="ms-2"><i class="bi bi-clock me-1"></i>{{ reminder.due_time }}</span>{% endif %}
                        {% if reminder.customer_name %}
                            <span class="ms-2"><i class="bi bi-person me-1"></i>{{ reminder.customer_name }}</span>
                        {% endif %}
                    </div>
                    <div class="btn-group btn-group-sm">
                        {% if reminder.status != 'completed' %}
                            <button class="btn btn-success" onclick="completeReminder({{ reminder.id }})" title="Tamamla">
                                <i class="bi bi-check-lg"></i>
                            </button>
                        {% endif %}
                        <button class="btn btn-outline-danger" onclick="deleteReminder({{ reminder.id }})" title="Sil">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
            {% else %}
            <div class="empty-state">
                <i class="bi bi-bell-slash"></i>
                <h5>Hatırlatıcı bulunamadı</h5>
                <a href="{{ url_for('reminder_add') }}" class="btn btn-primary mt-3">
                    <i class="bi bi-plus-lg me-1"></i>Yeni Ekle
                </a>
            </div>
            {% endfor %}
        </div>
    </div>
</div>

<!-- FAB -->
<a href="{{ url_for('reminder_add') }}" class="fab"><i class="bi bi-plus-lg"></i></a>
{% endblock %}

{% block extra_js %}
<script>
function completeReminder(id) {
    if (confirm('Bu hatırlatıcıyı tamamlamak istiyor musunuz?')) {
        fetch('{{ url_for("reminder_complete") }}', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'id=' + id
        }).then(() => location.reload());
    }
}

function deleteReminder(id) {
    if (confirm('Bu hatırlatıcıyı silmek istiyor musunuz?')) {
        fetch('{{ url_for("reminder_delete") }}', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'id=' + id
        }).then(() => location.reload());
    }
}
</script>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 13. HATIRLATICI EKLEME FORMU
# ----------------------------------------------------------------------------
REMINDER_FORM_HTML = '''
{% extends "base.html" %}
{% block title %}Yeni Hatırlatıcı{% endblock %}
{% block page_title %}Yeni Hatırlatıcı{% endblock %}
{% block mobile_title %}Hatırlatıcı{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-12 col-lg-6">
        <div class="card">
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Başlık *</label>
                        <input type="text" name="title" class="form-control" required autofocus>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Açıklama</label>
                        <textarea name="description" class="form-control" rows="2"></textarea>
                    </div>
                    
                    <div class="row g-3 mb-3">
                        <div class="col-md-6">
                            <label class="form-label">Tarih *</label>
                            <input type="date" name="due_date" class="form-control" value="{{ today }}" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Saat</label>
                            <input type="time" name="due_time" class="form-control">
                        </div>
                    </div>
                    
                    <div class="row g-3 mb-3">
                        <div class="col-md-6">
                            <label class="form-label">Tür</label>
                            <select name="reminder_type" class="form-select">
                                <option value="general">Genel</option>
                                <option value="check">Çek/Senet</option>
                                <option value="payment">Ödeme</option>
                                <option value="meeting">Toplantı</option>
                                <option value="call">Arama</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Öncelik</label>
                            <select name="priority" class="form-select">
                                <option value="low">Düşük</option>
                                <option value="normal" selected>Normal</option>
                                <option value="high">Yüksek</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">İlişkili Cari</label>
                        <select name="related_customer_id" class="form-select">
                            <option value="">Seçiniz (Opsiyonel)</option>
                            {% for c in customers %}
                                <option value="{{ c.id }}">{{ c.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="mb-4">
                        <div class="form-check">
                            <input type="checkbox" name="is_recurring" class="form-check-input" id="isRecurring">
                            <label class="form-check-label" for="isRecurring">Tekrarlayan hatırlatıcı</label>
                        </div>
                    </div>
                    
                    <div id="recurringOptions" style="display: none;">
                        <div class="row g-3 mb-4">
                            <div class="col-md-6">
                                <label class="form-label">Tekrar Sıklığı</label>
                                <select name="recurrence_type" class="form-select">
                                    <option value="daily">Günlük</option>
                                    <option value="weekly">Haftalık</option>
                                    <option value="monthly">Aylık</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Bitiş Tarihi</label>
                                <input type="date" name="recurrence_end_date" class="form-control">
                            </div>
                        </div>
                    </div>
                    
                    <div class="d-flex justify-content-between">
                        <a href="{{ url_for('reminders') }}" class="btn btn-outline-secondary">
                            <i class="bi bi-arrow-left me-1"></i>İptal
                        </a>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-check-lg me-1"></i>Kaydet
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.getElementById('isRecurring').addEventListener('change', function() {
    document.getElementById('recurringOptions').style.display = this.checked ? 'block' : 'none';
});
</script>
{% endblock %}
'''

print("=" * 70)
print("✅ WEBAPP.PY - PARÇA 2/3 TAMAMLANDI!")
print("=" * 70)
print("📦 İçerik:")
print("  ✔️ CHECKS_HTML (Liste + Filtre + İşlemler)")
print("  ✔️ CHECK_FORM_HTML (Ekleme/Düzenleme)")
print("  ✔️ CHECK_DETAIL_HTML (Detay + Geçmiş)")
print("  ✔️ CASHFLOW_HTML (Kasa Liste)")
print("  ✔️ CASHFLOW_FORM_HTML (Gelir/Gider Ekleme)")
print("  ✔️ REMINDERS_HTML (Hatırlatıcı Liste)")
print("  ✔️ REMINDER_FORM_HTML (Hatırlatıcı Ekleme)")
print("=" * 70)# ============================================================================
# WEBAPP.PY - PARÇA 3/3: NOTLAR + RAPORLAR + AYARLAR + TÜM ROUTE'LAR
# ============================================================================

# ----------------------------------------------------------------------------
# 14. NOT DEFTERİ / GÖREVLER SAYFASI
# ----------------------------------------------------------------------------
NOTES_HTML = '''
{% extends "base.html" %}
{% block title %}Notlar{% endblock %}
{% block page_title %}Not Defteri & Görevler{% endblock %}
{% block mobile_title %}Notlar{% endblock %}

{% block header_actions %}
<div class="btn-group">
    <a href="{{ url_for('note_add') }}?type=note" class="btn btn-primary">
        <i class="bi bi-sticky me-1"></i>Not
    </a>
    <a href="{{ url_for('note_add') }}?type=task" class="btn btn-success">
        <i class="bi bi-check2-square me-1"></i>Görev
    </a>
</div>
{% endblock %}

{% block content %}
<!-- ÖZET -->
<div class="row g-3 mb-4">
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #ef4444;">
            <div class="stat-label">Gecikmiş Görev</div>
            <div class="stat-value text-danger">{{ task_summary.overdue|default(0) }}</div>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #f59e0b;">
            <div class="stat-label">Bugün</div>
            <div class="stat-value text-warning">{{ task_summary.due_today|default(0) }}</div>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #3b82f6;">
            <div class="stat-label">Bekleyen Görev</div>
            <div class="stat-value text-primary">{{ task_summary.pending|default(0) }}</div>
        </div>
    </div>
    <div class="col-6 col-md-3">
        <div class="stat-card" style="border-left: 4px solid #10b981;">
            <div class="stat-label">Tamamlanan</div>
            <div class="stat-value text-success">{{ task_summary.completed|default(0) }}</div>
        </div>
    </div>
</div>

<!-- TABS -->
<ul class="nav nav-tabs mb-3">
    <li class="nav-item">
        <a class="nav-link {% if not request.args.get('tab') or request.args.get('tab') == 'all' %}active{% endif %}" href="?tab=all">Tümü</a>
    </li>
    <li class="nav-item">
        <a class="nav-link {% if request.args.get('tab') == 'notes' %}active{% endif %}" href="?tab=notes">Notlar</a>
    </li>
    <li class="nav-item">
        <a class="nav-link {% if request.args.get('tab') == 'tasks' %}active{% endif %}" href="?tab=tasks">Görevler</a>
    </li>
    <li class="nav-item">
        <a class="nav-link {% if request.args.get('tab') == 'pinned' %}active{% endif %}" href="?tab=pinned">
            <i class="bi bi-pin-angle"></i> Sabitler
        </a>
    </li>
</ul>

<!-- NOT LİSTESİ -->
<div class="row g-3">
    {% for note in notes %}
    <div class="col-12 col-md-6 col-lg-4">
    <div class="card h-100" style="border-top: 4px solid {{ note.color or '#6366f1' }}; overflow: visible;">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="d-flex align-items-center gap-2">
                        {% if note.is_pinned %}
                            <i class="bi bi-pin-angle-fill text-warning"></i>
                        {% endif %}
                        {% if note.is_task %}
                            {% if note.task_status == 'completed' %}
                                <i class="bi bi-check-circle-fill text-success"></i>
                            {% else %}
                                <i class="bi bi-circle text-muted"></i>
                            {% endif %}
                        {% endif %}
                        <h6 class="mb-0 {% if note.is_task and note.task_status == 'completed' %}text-decoration-line-through text-muted{% endif %}">
                            {{ note.title }}
                        </h6>
                    </div>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-link text-muted p-0" data-bs-toggle="dropdown">
                            <i class="bi bi-three-dots-vertical"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end">
                            {% if note.is_task and note.task_status != 'completed' %}
                                <li><a class="dropdown-item" href="#" onclick="completeTask({{ note.id }})"><i class="bi bi-check-lg me-2"></i>Tamamla</a></li>
                            {% endif %}
                            <li><a class="dropdown-item" href="#" onclick="togglePin({{ note.id }})"><i class="bi bi-pin me-2"></i>{{ 'Sabitlemeyi Kaldır' if note.is_pinned else 'Sabitle' }}</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('note_edit', id=note.id) }}"><i class="bi bi-pencil me-2"></i>Düzenle</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="deleteNote({{ note.id }})"><i class="bi bi-trash me-2"></i>Sil</a></li>
                        </ul>
                    </div>
                </div>
                
                {% if note.content %}
                    <p class="text-muted small mb-2" style="white-space: pre-line;">{{ note.content[:150] }}{% if note.content|length > 150 %}...{% endif %}</p>
                {% endif %}
                
                <div class="d-flex justify-content-between align-items-center mt-auto">
                    <small class="text-muted">
                        {% if note.is_task and note.task_due_date %}
                            <i class="bi bi-calendar me-1"></i>{{ note.task_due_date }}
                            {% if note.display_status == 'overdue' %}
                                <span class="badge badge-danger ms-1">Gecikmiş</span>
                            {% elif note.display_status == 'due_today' %}
                                <span class="badge badge-warning ms-1">Bugün</span>
                            {% endif %}
                        {% else %}
                            {{ note.created_at[:10] }}
                        {% endif %}
                    </small>
                    {% if note.is_task %}
                        <span class="badge badge-{% if note.task_priority == 'high' %}danger{% elif note.task_priority == 'low' %}secondary{% else %}primary{% endif %}">
                            {{ note.task_priority|upper }}
                        </span>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
    {% else %}
    <div class="col-12">
        <div class="empty-state">
            <i class="bi bi-journal-text"></i>
            <h5>Henüz not eklenmemiş</h5>
            <div class="mt-3">
                <a href="{{ url_for('note_add') }}?type=note" class="btn btn-primary me-2">
                    <i class="bi bi-sticky me-1"></i>Not Ekle
                </a>
                <a href="{{ url_for('note_add') }}?type=task" class="btn btn-success">
                    <i class="bi bi-check2-square me-1"></i>Görev Ekle
                </a>
            </div>
        </div>
    </div>
    {% endfor %}
</div>

<!-- FAB -->
<button class="fab" data-bs-toggle="modal" data-bs-target="#quickNoteModal">
    <i class="bi bi-plus-lg"></i>
</button>

<!-- HIZLI EKLEME MODAL -->
<div class="modal fade" id="quickNoteModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Hızlı Ekle</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body text-center">
                <div class="d-grid gap-3">
                    <a href="{{ url_for('note_add') }}?type=note" class="btn btn-primary btn-lg py-3">
                        <i class="bi bi-sticky me-2"></i>Yeni Not
                    </a>
                    <a href="{{ url_for('note_add') }}?type=task" class="btn btn-success btn-lg py-3">
                        <i class="bi bi-check2-square me-2"></i>Yeni Görev
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
function completeTask(id) {
    fetch('{{ url_for("note_complete") }}', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'id=' + id
    }).then(() => location.reload());
}

function togglePin(id) {
    fetch('{{ url_for("note_toggle_pin") }}', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'id=' + id
    }).then(() => location.reload());
}

function deleteNote(id) {
    if (confirm('Bu notu silmek istiyor musunuz?')) {
        fetch('{{ url_for("note_delete") }}', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'id=' + id
        }).then(() => location.reload());
    }
}
</script>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 15. NOT EKLEME/DÜZENLEME FORMU
# ----------------------------------------------------------------------------
NOTE_FORM_HTML = '''
{% extends "base.html" %}
{% block title %}{{ 'Düzenle' if note else ('Yeni Görev' if is_task else 'Yeni Not') }}{% endblock %}
{% block page_title %}{{ 'Not Düzenle' if note else ('Yeni Görev' if is_task else 'Yeni Not') }}{% endblock %}
{% block mobile_title %}{{ 'Düzenle' if note else ('Görev' if is_task else 'Not') }}{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-12 col-lg-6">
        <div class="card">
            <div class="card-body">
                <form method="POST">
                    <input type="hidden" name="is_task" value="{{ '1' if is_task or (note and note.is_task) else '0' }}">
                    
                    <div class="mb-3">
                        <label class="form-label">Başlık *</label>
                        <input type="text" name="title" class="form-control" value="{{ note.title if note else '' }}" required autofocus>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">İçerik</label>
                        <textarea name="content" class="form-control" rows="5">{{ note.content if note else '' }}</textarea>
                    </div>
                    
                    {% if is_task or (note and note.is_task) %}
                    <div class="row g-3 mb-3">
                        <div class="col-md-6">
                            <label class="form-label">Bitiş Tarihi</label>
                            <input type="date" name="task_due_date" class="form-control" value="{{ note.task_due_date if note else today }}">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Öncelik</label>
                            <select name="task_priority" class="form-select">
                                <option value="low" {% if note and note.task_priority == 'low' %}selected{% endif %}>Düşük</option>
                                <option value="normal" {% if not note or note.task_priority == 'normal' %}selected{% endif %}>Normal</option>
                                <option value="high" {% if note and note.task_priority == 'high' %}selected{% endif %}>Yüksek</option>
                            </select>
                        </div>
                    </div>
                    {% endif %}
                    
                    <div class="row g-3 mb-3">
                        <div class="col-md-6">
                            <label class="form-label">Renk</label>
                            <input type="color" name="color" class="form-control form-control-color w-100" value="{{ note.color if note else '#6366f1' }}">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Kategori</label>
                            <input type="text" name="category" class="form-control" value="{{ note.category if note else '' }}" placeholder="İş, Kişisel, vb.">
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">İlişkili Cari</label>
                        <select name="related_customer_id" class="form-select">
                            <option value="">Seçiniz (Opsiyonel)</option>
                            {% for c in customers %}
                                <option value="{{ c.id }}" {% if note and note.related_customer_id == c.id %}selected{% endif %}>{{ c.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="mb-4">
                        <div class="form-check">
                            <input type="checkbox" name="is_pinned" class="form-check-input" id="isPinned" {% if note and note.is_pinned %}checked{% endif %}>
                            <label class="form-check-label" for="isPinned">Sabitle</label>
                        </div>
                    </div>
                    
                    <div class="d-flex justify-content-between">
                        <a href="{{ url_for('notes') }}" class="btn btn-outline-secondary">
                            <i class="bi bi-arrow-left me-1"></i>İptal
                        </a>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-check-lg me-1"></i>{{ 'Güncelle' if note else 'Kaydet' }}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 16. RAPORLAR SAYFASI
# ----------------------------------------------------------------------------
REPORTS_HTML = '''
{% extends "base.html" %}
{% block title %}Raporlar{% endblock %}
{% block page_title %}Raporlar{% endblock %}
{% block mobile_title %}Raporlar{% endblock %}

{% block content %}
<div class="row g-4">
    <!-- CARİ RAPORLARI -->
    <div class="col-12 col-md-6">
        <div class="card h-100">
            <div class="card-header bg-primary text-white">
                <i class="bi bi-people me-2"></i>Cari Raporları
            </div>
            <div class="list-group list-group-flush">
                <a href="{{ url_for('report_customer_balances') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-list-ul me-2"></i>Bakiye Listesi</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('report_customer_balances') }}?type=receivable" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-arrow-down-circle text-success me-2"></i>Alacak Raporu</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('report_customer_balances') }}?type=payable" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-arrow-up-circle text-danger me-2"></i>Borç Raporu</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
            </div>
        </div>
    </div>
    
    <!-- ÇEK/SENET RAPORLARI -->
    <div class="col-12 col-md-6">
        <div class="card h-100">
            <div class="card-header bg-success text-white">
                <i class="bi bi-credit-card-2-back me-2"></i>Çek/Senet Raporları
            </div>
            <div class="list-group list-group-flush">
                <a href="{{ url_for('report_checks') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-list-ul me-2"></i>Tüm Çek/Senetler</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('report_checks') }}?status=pending" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-hourglass-split text-warning me-2"></i>Bekleyen Çekler</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('report_checks') }}?status=overdue" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-exclamation-triangle text-danger me-2"></i>Vadesi Geçenler</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('report_aging') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-bar-chart me-2"></i>Yaşlandırma Analizi</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
            </div>
        </div>
    </div>
    
    <!-- GELİR/GİDER RAPORLARI -->
    <div class="col-12 col-md-6">
        <div class="card h-100">
            <div class="card-header bg-warning">
                <i class="bi bi-cash-stack me-2"></i>Gelir/Gider Raporları
            </div>
            <div class="list-group list-group-flush">
                <a href="{{ url_for('report_cashflow') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-graph-up me-2"></i>Gelir/Gider Özeti</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('report_cashflow') }}?type=income" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-plus-circle text-success me-2"></i>Gelir Detayı</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('report_cashflow') }}?type=expense" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-dash-circle text-danger me-2"></i>Gider Detayı</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
            </div>
        </div>
    </div>
    
    <!-- DİĞER RAPORLAR -->
    <div class="col-12 col-md-6">
        <div class="card h-100">
            <div class="card-header bg-info text-white">
                <i class="bi bi-file-earmark-bar-graph me-2"></i>Diğer Raporlar
            </div>
            <div class="list-group list-group-flush">
                <a href="{{ url_for('report_activity') }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-activity me-2"></i>Aktivite Raporu</span>
                    <i class="bi bi-chevron-right"></i>
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 17. RAPOR GÖRÜNTÜLEME SAYFASI (GENEL ŞABLON)
# ----------------------------------------------------------------------------
REPORT_VIEW_HTML = '''
{% extends "base.html" %}
{% block title %}{{ report_title }}{% endblock %}
{% block page_title %}{{ report_title }}{% endblock %}
{% block mobile_title %}Rapor{% endblock %}

{% block header_actions %}
<div class="btn-group">
    <a href="{{ export_url }}" class="btn btn-success">
        <i class="bi bi-download me-1"></i>CSV İndir
    </a>
    <button onclick="window.print()" class="btn btn-outline-secondary">
        <i class="bi bi-printer me-1"></i>Yazdır
    </button>
</div>
{% endblock %}

{% block extra_css %}
<style>
@media print {
    .sidebar, .mobile-header, .page-header, .fab, .btn-group, .no-print { display: none !important; }
    .main-content { margin-left: 0 !important; }
    .card { box-shadow: none !important; border: 1px solid #ddd !important; }
}
</style>
{% endblock %}

{% block content %}
<!-- FİLTRELER -->
<div class="card mb-3 no-print">
    <div class="card-body py-2">
        <form method="GET" class="row g-2 align-items-center">
            {% if show_date_filter %}
            <div class="col-auto">
                <input type="date" name="start_date" class="form-control form-control-sm" value="{{ request.args.get('start_date', '') }}" placeholder="Başlangıç">
            </div>
            <div class="col-auto">
                <input type="date" name="end_date" class="form-control form-control-sm" value="{{ request.args.get('end_date', '') }}" placeholder="Bitiş">
            </div>
            {% endif %}
            {% if show_type_filter %}
            <div class="col-auto">
                <select name="type" class="form-select form-select-sm">
                    <option value="">Tümü</option>
                    {% for opt in type_options %}
                        <option value="{{ opt.value }}" {% if request.args.get('type') == opt.value %}selected{% endif %}>{{ opt.label }}</option>
                    {% endfor %}
                </select>
            </div>
            {% endif %}
            {% if show_status_filter %}
            <div class="col-auto">
                <select name="status" class="form-select form-select-sm">
                    <option value="">Tüm Durumlar</option>
                    {% for opt in status_options %}
                        <option value="{{ opt.value }}" {% if request.args.get('status') == opt.value %}selected{% endif %}>{{ opt.label }}</option>
                    {% endfor %}
                </select>
            </div>
            {% endif %}
            <div class="col-auto">
                <button type="submit" class="btn btn-sm btn-primary">Filtrele</button>
            </div>
        </form>
    </div>
</div>

<!-- ÖZET -->
{% if summary %}
<div class="row g-3 mb-4">
    {% for key, item in summary.items() %}
    <div class="col-6 col-md-3">
        <div class="stat-card">
            <div class="stat-label">{{ item.label }}</div>
            <div class="stat-value {% if item.color %}text-{{ item.color }}{% endif %}">
                {% if item.is_currency %}{{ "{:,.0f}".format(item.value) }}₺{% else %}{{ item.value }}{% endif %}
            </div>
        </div>
    </div>
    {% endfor %}
</div>
{% endif %}

<!-- VERİ TABLOSU -->
<div class="card">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        {% for col in columns %}
                            <th class="{{ col.class or '' }}">{{ col.label }}</th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% for row in data %}
                    <tr>
                        {% for col in columns %}
                            <td class="{{ col.class or '' }}">
                                {% set value = row[col.key] %}
                                {% if col.type == 'currency' %}
                                    {% if col.color_condition and value < 0 %}
                                        <span class="text-danger">{{ "{:,.2f}".format(value) }}₺</span>
                                    {% elif col.color_condition and value > 0 %}
                                        <span class="text-success">+{{ "{:,.2f}".format(value) }}₺</span>
                                    {% else %}
                                        {{ "{:,.2f}".format(value) }}₺
                                    {% endif %}
                                {% elif col.type == 'badge' %}
                                    <span class="badge badge-{{ col.badge_map.get(value, 'secondary') }}">{{ col.label_map.get(value, value) }}</span>
                                {% elif col.type == 'link' %}
                                    <a href="{{ url_for(col.route, id=row[col.id_key]) }}">{{ value }}</a>
                                {% else %}
                                    {{ value or '-' }}
                                {% endif %}
                            </td>
                        {% endfor %}
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="{{ columns|length }}" class="text-center py-5 text-muted">
                            Veri bulunamadı
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- TOPLAM (varsa) -->
{% if totals %}
<div class="card mt-3">
    <div class="card-body">
        <div class="row text-center">
            {% for key, item in totals.items() %}
            <div class="col">
                <div class="text-muted small">{{ item.label }}</div>
                <div class="h4 mb-0 {% if item.color %}text-{{ item.color }}{% endif %}">
                    {% if item.is_currency %}{{ "{:,.2f}".format(item.value) }}₺{% else %}{{ item.value }}{% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endif %}
{% endblock %}
'''

# ----------------------------------------------------------------------------
# 18. AYARLAR SAYFASI
# ----------------------------------------------------------------------------
SETTINGS_HTML = '''
{% extends "base.html" %}
{% block title %}Ayarlar{% endblock %}
{% block page_title %}Ayarlar{% endblock %}
{% block mobile_title %}Ayarlar{% endblock %}

{% block content %}
<div class="row">
    <!-- SOL MENÜ -->
    <div class="col-12 col-lg-3 mb-4">
        <div class="card">
            <div class="list-group list-group-flush">
                <a href="#company" class="list-group-item list-group-item-action active" data-bs-toggle="list">
                    <i class="bi bi-building me-2"></i>Firma Bilgileri
                </a>
                <a href="#general" class="list-group-item list-group-item-action" data-bs-toggle="list">
                    <i class="bi bi-gear me-2"></i>Genel Ayarlar
                </a>
                <a href="#whatsapp" class="list-group-item list-group-item-action" data-bs-toggle="list">
                    <i class="bi bi-whatsapp me-2"></i>WhatsApp
                </a>
                <a href="#notifications" class="list-group-item list-group-item-action" data-bs-toggle="list">
                    <i class="bi bi-bell me-2"></i>Bildirimler
                </a>
                <a href="#categories" class="list-group-item list-group-item-action" data-bs-toggle="list">
                    <i class="bi bi-tags me-2"></i>Kategoriler
                </a>
                <a href="#backup" class="list-group-item list-group-item-action" data-bs-toggle="list">
                    <i class="bi bi-cloud-download me-2"></i>Yedekleme
                </a>
                <a href="#templates" class="list-group-item list-group-item-action" data-bs-toggle="list">
                    <i class="bi bi-file-text me-2"></i>Mesaj Şablonları
                </a>
            </div>
        </div>
    </div>
    
    <!-- SAĞ İÇERİK -->
    <div class="col-12 col-lg-9">
        <form method="POST" action="{{ url_for('settings_save') }}">
            <div class="tab-content">
                <!-- FİRMA BİLGİLERİ -->
                <div class="tab-pane fade show active" id="company">
                    <div class="card">
                        <div class="card-header"><i class="bi bi-building me-2"></i>Firma Bilgileri</div>
                        <div class="card-body">
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="form-label">Firma Adı</label>
                                    <input type="text" name="company.name" class="form-control" value="{{ settings.company.name.value if settings.company else '' }}">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Telefon</label>
                                    <input type="text" name="company.phone" class="form-control" value="{{ settings.company.phone.value if settings.company else '' }}">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">E-posta</label>
                                    <input type="email" name="company.email" class="form-control" value="{{ settings.company.email.value if settings.company else '' }}">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Vergi Dairesi</label>
                                    <input type="text" name="company.tax_office" class="form-control" value="{{ settings.company.tax_office.value if settings.company else '' }}">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Vergi No</label>
                                    <input type="text" name="company.tax_number" class="form-control" value="{{ settings.company.tax_number.value if settings.company else '' }}">
                                </div>
                                <div class="col-12">
                                    <label class="form-label">Adres</label>
                                    <textarea name="company.address" class="form-control" rows="2">{{ settings.company.address.value if settings.company else '' }}</textarea>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- GENEL AYARLAR -->
                <div class="tab-pane fade" id="general">
                    <div class="card">
                        <div class="card-header"><i class="bi bi-gear me-2"></i>Genel Ayarlar</div>
                        <div class="card-body">
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="form-label">Para Birimi</label>
                                    <select name="general.currency" class="form-select">
                                        <option value="TL" {% if settings.general and settings.general.currency.value == 'TL' %}selected{% endif %}>TL - Türk Lirası</option>
                                        <option value="USD" {% if settings.general and settings.general.currency.value == 'USD' %}selected{% endif %}>USD - Dolar</option>
                                        <option value="EUR" {% if settings.general and settings.general.currency.value == 'EUR' %}selected{% endif %}>EUR - Euro</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Tarih Formatı</label>
                                    <select name="general.date_format" class="form-select">
                                        <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                                        <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Çek Hatırlatma (Gün Önce)</label>
                                    <input type="number" name="reminder.check_reminder_days" class="form-control" value="{{ settings.reminder.check_reminder_days.value if settings.reminder else 3 }}">
                                </div>
                                <div class="col-md-6">
                                    <div class="form-check mt-4">
                                        <input type="checkbox" name="reminder.auto_create_check_reminder" class="form-check-input" id="autoReminder" {% if settings.reminder and settings.reminder.auto_create_check_reminder.value %}checked{% endif %}>
                                        <label class="form-check-label" for="autoReminder">Çek eklendiğinde otomatik hatırlatıcı</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- WHATSAPP AYARLARI -->
                <div class="tab-pane fade" id="whatsapp">
                    <div class="card">
                        <div class="card-header"><i class="bi bi-whatsapp me-2"></i>WhatsApp Ayarları</div>
                        <div class="card-body">
                            <div class="mb-4">
                                <div class="form-check form-switch">
                                    <input type="checkbox" name="whatsapp.enabled" class="form-check-input" id="waEnabled" {% if settings.whatsapp and settings.whatsapp.enabled.value %}checked{% endif %}>
                                    <label class="form-check-label" for="waEnabled"><strong>WhatsApp Entegrasyonunu Aktif Et</strong></label>
                                </div>
                                <small class="text-muted">Aktif edildiğinde müşterilere WhatsApp üzerinden mesaj gönderebilirsiniz.</small>
                            </div>
                            
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="form-label">API Tipi</label>
                                    <select name="whatsapp.api_type" class="form-select">
                                        <option value="web">WhatsApp Web (Ücretsiz)</option>
                                        <option value="business_api">Business API</option>
                                    </select>
                                    <small class="text-muted">WhatsApp Web seçeneği ücretsizdir ve tarayıcı üzerinden çalışır.</small>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Varsayılan Ülke Kodu</label>
                                    <input type="text" name="whatsapp.default_country_code" class="form-control" value="{{ settings.whatsapp.default_country_code.value if settings.whatsapp else '+90' }}">
                                </div>
                                <div class="col-12">
                                    <div class="form-check">
                                        <input type="checkbox" name="whatsapp.auto_send_check_reminder" class="form-check-input" id="waAutoCheck" {% if settings.whatsapp and settings.whatsapp.auto_send_check_reminder.value %}checked{% endif %}>
                                        <label class="form-check-label" for="waAutoCheck">Vadesi yaklaşan çekler için otomatik hatırlatma linki oluştur</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- BİLDİRİM AYARLARI -->
                <div class="tab-pane fade" id="notifications">
                    <div class="card">
                        <div class="card-header"><i class="bi bi-bell me-2"></i>Bildirim Ayarları</div>
                        <div class="card-body">
                            <div class="form-check mb-3">
                                <input type="checkbox" name="notification.browser_notifications" class="form-check-input" id="browserNotif" {% if settings.notification and settings.notification.browser_notifications.value %}checked{% endif %}>
                                <label class="form-check-label" for="browserNotif">Tarayıcı bildirimleri</label>
                            </div>
                            <div class="form-check mb-3">
                                <input type="checkbox" name="notification.email_notifications" class="form-check-input" id="emailNotif" {% if settings.notification and settings.notification.email_notifications.value %}checked{% endif %}>
                                <label class="form-check-label" for="emailNotif">E-posta bildirimleri</label>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- KATEGORİLER -->
                <div class="tab-pane fade" id="categories">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <span><i class="bi bi-tags me-2"></i>Gelir/Gider Kategorileri</span>
                            <button type="button" class="btn btn-sm btn-primary" data-bs-toggle="modal" data-bs-target="#addCategoryModal">
                                <i class="bi bi-plus"></i> Ekle
                            </button>
                        </div>
                        <div class="card-body p-0">
                            <table class="table table-hover mb-0">
                                <thead>
                                    <tr>
                                        <th>Kategori</th>
                                        <th>Tür</th>
                                        <th>Renk</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for cat in categories %}
                                    <tr>
                                        <td>{{ cat.icon }} {{ cat.name }}</td>
                                        <td>
                                            {% if cat.type == 'income' %}
                                                <span class="badge badge-success">Gelir</span>
                                            {% else %}
                                                <span class="badge badge-danger">Gider</span>
                                            {% endif %}
                                        </td>
                                        <td><span class="badge" style="background-color: {{ cat.color }};">{{ cat.color }}</span></td>
                                        <td>
                                            {% if not cat.is_default %}
                                                <button type="button" class="btn btn-sm btn-outline-danger" onclick="deleteCategory({{ cat.id }})">
                                                    <i class="bi bi-trash"></i>
                                                </button>
                                            {% endif %}
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                
                <!-- YEDEKLEME -->
                <div class="tab-pane fade" id="backup">
                    <div class="card">
                        <div class="card-header"><i class="bi bi-cloud-download me-2"></i>Yedekleme</div>
                        <div class="card-body">
                            <p class="text-muted">Veritabanınızı yedekleyebilir veya daha önce aldığınız bir yedeği geri yükleyebilirsiniz.</p>
                            <div class="d-flex gap-2">
                                <a href="{{ url_for('backup_download') }}" class="btn btn-success">
                                    <i class="bi bi-download me-2"></i>Yedek İndir
                                </a>
                            </div>
                            <hr>
                            <h6>Otomatik Yedekleme</h6>
                            <div class="form-check mb-2">
                                <input type="checkbox" name="backup.auto_backup" class="form-check-input" id="autoBackup" {% if settings.backup and settings.backup.auto_backup.value %}checked{% endif %}>
                                <label class="form-check-label" for="autoBackup">Otomatik yedekleme aktif</label>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- MESAJ ŞABLONLARI -->
                <div class="tab-pane fade" id="templates">
                    <div class="card">
                        <div class="card-header"><i class="bi bi-file-text me-2"></i>WhatsApp Mesaj Şablonları</div>
                        <div class="card-body">
                            {% for template in whatsapp_templates %}
                            <div class="mb-4 pb-3 border-bottom">
                                <label class="form-label fw-bold">{{ template.name }}</label>
                                <textarea name="template_{{ template.id }}" class="form-control" rows="3">{{ template.content }}</textarea>
                                <small class="text-muted">Değişkenler: {% for v in template.variables %}{{ '{' + v + '}' }}{% if not loop.last %}, {% endif %}{% endfor %}</small>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- KAYDET BUTONU -->
            <div class="mt-4">
                <button type="submit" class="btn btn-primary btn-lg">
                    <i class="bi bi-check-lg me-2"></i>Ayarları Kaydet
                </button>
            </div>
        </form>
    </div>
</div>

<!-- KATEGORİ EKLEME MODAL -->
<div class="modal fade" id="addCategoryModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Yeni Kategori</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form method="POST" action="{{ url_for('category_add') }}">
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">Kategori Adı</label>
                        <input type="text" name="name" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Tür</label>
                        <select name="type" class="form-select" required>
                            <option value="income">Gelir</option>
                            <option value="expense">Gider</option>
                        </select>
                    </div>
                    <div class="row g-3">
                        <div class="col-6">
                            <label class="form-label">İkon</label>
                            <input type="text" name="icon" class="form-control" placeholder="💰">
                        </div>
                        <div class="col-6">
                            <label class="form-label">Renk</label>
                            <input type="color" name="color" class="form-control form-control-color w-100" value="#6366f1">
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">İptal</button>
                    <button type="submit" class="btn btn-primary">Ekle</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
function deleteCategory(id) {
    if (confirm('Bu kategoriyi silmek istiyor musunuz?')) {
        fetch('{{ url_for("category_delete") }}', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'id=' + id
        }).then(() => location.reload());
    }
}
</script>
{% endblock %}
'''

# ============================================================================
# TEMPLATE SÖZLÜĞÜ
# ============================================================================

TEMPLATES = {
    'base.html': BASE_HTML,
    'login.html': LOGIN_HTML,
    'dashboard.html': DASHBOARD_HTML,
    'customers.html': CUSTOMERS_HTML,
    'customer_form.html': CUSTOMER_FORM_HTML,
    'customer_detail.html': CUSTOMER_DETAIL_HTML,
    'checks.html': CHECKS_HTML,
    'check_form.html': CHECK_FORM_HTML,
    'check_detail.html': CHECK_DETAIL_HTML,
    'cash_flow.html': CASHFLOW_HTML,
    'cash_flow_form.html': CASHFLOW_FORM_HTML,
    'reminders.html': REMINDERS_HTML,
    'reminder_form.html': REMINDER_FORM_HTML,
    'notes.html': NOTES_HTML,
    'note_form.html': NOTE_FORM_HTML,
    'reports.html': REPORTS_HTML,
    'report_view.html': REPORT_VIEW_HTML,
    'settings.html': SETTINGS_HTML,
}

# DictLoader ayarla
app.jinja_loader = jinja2.DictLoader(TEMPLATES)

# ============================================================================
# CONTEXT PROCESSORS
# ============================================================================

@app.context_processor
def inject_globals():
    """Tüm template'lerde kullanılacak global değişkenler."""
    context = {
        'now': datetime.now(),
        'today': datetime.now().strftime('%Y-%m-%d'),
        'company_name': backend.get_setting('company', 'name', 'ERP Sistemi'),
        'whatsapp_enabled': backend.is_whatsapp_enabled(),
    }
    
    if 'user' in session:
        # Bekleyen hatırlatıcı sayısı
        summary = backend.get_reminders_summary()
        context['pending_reminders'] = summary.get('overdue', 0) + summary.get('today', 0)
    
    return context

# ============================================================================
# ROUTE'LAR - AUTH
# ============================================================================

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = backend.login_user(username, password)
        if user:
            session.permanent = True
            session['user'] = user
            flash('Giriş başarılı!', 'success')
            return redirect(url_for('dashboard'))
        flash('Kullanıcı adı veya şifre hatalı!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Çıkış yapıldı.', 'info')
    return redirect(url_for('login'))

# ============================================================================
# ROUTE'LAR - DASHBOARD
# ============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    stats = backend.get_dashboard_stats()
    check_summary = backend.get_checks_summary()
    upcoming_checks = backend.get_upcoming_checks(7)
    upcoming_reminders = backend.get_upcoming_reminders(7)
    
    # ✅ BURAYI EKLE: days_left hesapla
    for check in upcoming_checks:
        if check.get('due_date'):
            try:
                due = datetime.strptime(check['due_date'], '%Y-%m-%d')
                check['days_left'] = (due.date() - datetime.now().date()).days
            except:
                check['days_left'] = 0
    
    return render_template('dashboard.html',
        stats=stats,
        check_summary=check_summary,
        upcoming_checks=upcoming_checks,
        upcoming_reminders=upcoming_reminders
    )

# ============================================================================
# ROUTE'LAR - MÜŞTERİLER
# ============================================================================

@app.route('/customers')
@login_required
def customers():
    customer_type = request.args.get('type')
    balance_type = request.args.get('balance')
    search = request.args.get('search')
    
    customers = backend.get_all_customers(customer_type=customer_type, search=search)
    
    if balance_type == 'receivable':
        customers = [c for c in customers if c['balance'] > 0]
    elif balance_type == 'payable':
        customers = [c for c in customers if c['balance'] < 0]
    
    return render_template('customers.html', customers=customers)

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def customer_add():
    if request.method == 'POST':
        data = {k: v for k, v in request.form.items() if v}
        data['created_by'] = session['user']['id']
        success, message, _ = backend.add_customer(**data)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('customers'))
    return render_template('customer_form.html', customer=None)

@app.route('/customers/<int:id>')
@login_required
def customer_detail(id):
    customer = backend.get_customer_by_id(id)
    if not customer:
        flash('Cari bulunamadı.', 'warning')
        return redirect(url_for('customers'))
    
    transactions = backend.get_customer_transactions(id, limit=20)
    pending_checks = backend.get_all_checks(customer_id=id, status='pending')
    
    # WhatsApp link oluştur
    if customer.get('whatsapp_phone') or customer.get('phone'):
        phone = customer.get('whatsapp_phone') or customer.get('phone')
        customer['whatsapp_link'] = backend.generate_whatsapp_link(phone, '')
    
    return render_template('customer_detail.html',
        customer=customer,
        transactions=transactions,
        pending_checks=pending_checks
    )

@app.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def customer_edit(id):
    customer = backend.get_customer_by_id(id)
    if not customer:
        flash('Cari bulunamadı.', 'warning')
        return redirect(url_for('customers'))
    
    if request.method == 'POST':
        data = {k: v for k, v in request.form.items() if v}
        success, message = backend.update_customer(id, **data)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('customer_detail', id=id))
    
    return render_template('customer_form.html', customer=customer)

@app.route('/customers/<int:id>/statement')
@login_required
def customer_statement(id):
    customer = backend.get_customer_by_id(id)
    if not customer:
        flash('Cari bulunamadı.', 'warning')
        return redirect(url_for('customers'))
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    statement = backend.get_customer_statement(id, start_date, end_date)
    
    # Export için
    if request.args.get('export') == 'csv':
        csv_data = backend.export_customer_statement_csv(id, start_date, end_date)
        return Response(csv_data, mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=ekstre_{id}.csv'})
    
    return render_template('report_view.html',
        report_title=f'{customer["name"]} - Hesap Ekstresi',
        export_url=url_for('customer_statement', id=id, export='csv', start_date=start_date, end_date=end_date),
        show_date_filter=True,
        data=statement.get('transactions', []),
        columns=[
            {'key': 'transaction_date', 'label': 'Tarih'},
            {'key': 'description', 'label': 'Açıklama'},
            {'key': 'amount', 'label': 'Tutar', 'type': 'currency', 'class': 'text-end'},
            {'key': 'balance_after', 'label': 'Bakiye', 'type': 'currency', 'class': 'text-end', 'color_condition': True},
        ],
        summary={
            'opening': {'label': 'Açılış Bakiyesi', 'value': statement.get('opening_balance', 0), 'is_currency': True},
            'debit': {'label': 'Toplam Borç', 'value': statement.get('total_debit', 0), 'is_currency': True, 'color': 'danger'},
            'credit': {'label': 'Toplam Alacak', 'value': statement.get('total_credit', 0), 'is_currency': True, 'color': 'success'},
            'closing': {'label': 'Kapanış Bakiyesi', 'value': statement.get('closing_balance', 0), 'is_currency': True},
        }
    )

# ============================================================================
# ROUTE'LAR - ÇEK/SENET
# ============================================================================

@app.route('/checks')
@login_required
def checks():
    check_type = request.args.get('type')
    status = request.args.get('status')
    search = request.args.get('search')
    
    checks = backend.get_all_checks(check_type=check_type, status=status, search=search)
    summary = backend.get_checks_summary()
    
    return render_template('checks.html', checks=checks, summary=summary)

@app.route('/checks/add', methods=['GET', 'POST'])
@login_required
def check_add():
    if request.method == 'POST':
        data = {
            'check_type': request.form.get('check_type'),
            'payment_type': request.form.get('payment_type'),
            'check_number': request.form.get('check_number'),
            'customer_id': int(request.form.get('customer_id')) if request.form.get('customer_id') else None,
            'bank_name': request.form.get('bank_name'),
            'bank_branch': request.form.get('bank_branch'),
            'account_number': request.form.get('account_number'),
            'iban': request.form.get('iban'),
            'amount': float(request.form.get('amount')),
            'issue_date': request.form.get('issue_date'),
            'due_date': request.form.get('due_date'),
            'drawer_name': request.form.get('drawer_name'),
            'drawer_tax_no': request.form.get('drawer_tax_no'),
            'notes': request.form.get('notes'),
            'created_by': session['user']['id']
        }
        success, message, _ = backend.add_check(**data)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('checks'))
    
    customers = backend.get_all_customers()
    return render_template('check_form.html', check=None, customers=customers)

@app.route('/checks/<int:id>')
@login_required
def check_detail(id):
    check = backend.get_check_by_id(id)
    if not check:
        flash('Çek/Senet bulunamadı.', 'warning')
        return redirect(url_for('checks'))
    
    transactions = backend.get_check_transactions(id)
    
    # Kalan tutar hesapla
    check['remaining_amount'] = check['amount'] - check['paid_amount']
    
    # Vadeye kalan gün
    if check['due_date']:
        due = datetime.strptime(check['due_date'], '%Y-%m-%d')
        check['days_until_due'] = (due.date() - datetime.now().date()).days
        if check['status'] == 'pending':
            if check['days_until_due'] < 0:
                check['display_status'] = 'overdue'
            elif check['days_until_due'] <= 7:
                check['display_status'] = 'upcoming'
            else:
                check['display_status'] = 'pending'
    
    # WhatsApp linki
    if check.get('customer_phone') and backend.is_whatsapp_enabled():
        wa_data = backend.prepare_check_reminder_message(id)
        check['whatsapp_link'] = wa_data.get('whatsapp_link', '')
    
    return render_template('check_detail.html', check=check, transactions=transactions)

@app.route('/checks/process', methods=['POST'])
@login_required
def check_process():
    check_id = int(request.form.get('check_id'))
    status = request.form.get('status')
    amount = float(request.form.get('amount', 0)) if request.form.get('amount') else None
    description = request.form.get('description', '')
    
    success, message = backend.process_check_payment(check_id, amount, status, description, session['user']['id'])
    flash(message, 'success' if success else 'danger')
    
    return redirect(request.referrer or url_for('checks'))

@app.route('/checks/endorse', methods=['POST'])
@login_required
def check_endorse():
    check_id = int(request.form.get('check_id'))
    endorser_name = request.form.get('endorser_name')
    endorser_tax_no = request.form.get('endorser_tax_no', '')
    endorser_phone = request.form.get('endorser_phone', '')
    description = request.form.get('description', '')
    
    success, message = backend.endorse_check(check_id, endorser_name, endorser_tax_no, endorser_phone, description, session['user']['id'])
    flash(message, 'success' if success else 'danger')
    
    return redirect(request.referrer or url_for('checks'))

# ============================================================================
# ROUTE'LAR - KASA
# ============================================================================

@app.route('/cash-flow')
@login_required
def cash_flow():
    trans_type = request.args.get('type')
    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    transactions = backend.get_cash_flow(start_date, end_date, category, trans_type)
    balance = backend.get_cash_balance()
    categories = backend.get_categories()
    
    return render_template('cash_flow.html',
        transactions=transactions,
        balance=balance,
        categories=categories
    )

@app.route('/cash-flow/add', methods=['GET', 'POST'])
@login_required
def cash_flow_add():
    trans_type = request.args.get('type', 'income')
    
    if request.method == 'POST':
        data = {
            'transaction_type': request.form.get('transaction_type'),
            'category': request.form.get('category'),
            'amount': float(request.form.get('amount')),
            'description': request.form.get('description', ''),
            'customer_id': int(request.form.get('customer_id')) if request.form.get('customer_id') else None,
            'payment_method': request.form.get('payment_method', 'cash'),
            'transaction_date': request.form.get('transaction_date'),
            'created_by': session['user']['id']
        }
        success, message, _ = backend.add_cash_transaction(**data)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('cash_flow'))
    
    categories = backend.get_categories(category_type=trans_type)
    customers = backend.get_all_customers()
    
    return render_template('cash_flow_form.html',
        trans_type=trans_type,
        categories=categories,
        customers=customers
    )

# ============================================================================
# ROUTE'LAR - HATIRLATICILAR
# ============================================================================

@app.route('/reminders')
@login_required
def reminders():
    status = request.args.get('status')
    reminder_type = request.args.get('type')
    priority = request.args.get('priority')
    include_completed = request.args.get('status') == 'completed'
    
    reminders = backend.get_reminders(status=status, reminder_type=reminder_type,
                                       priority=priority, include_completed=include_completed)
    summary = backend.get_reminders_summary()
    
    return render_template('reminders.html', reminders=reminders, summary=summary)

@app.route('/reminders/add', methods=['GET', 'POST'])
@login_required
def reminder_add():
    if request.method == 'POST':
        data = {
            'title': request.form.get('title'),
            'description': request.form.get('description', ''),
            'due_date': request.form.get('due_date'),
            'due_time': request.form.get('due_time') or None,
            'reminder_type': request.form.get('reminder_type', 'general'),
            'priority': request.form.get('priority', 'normal'),
            'is_recurring': 1 if request.form.get('is_recurring') else 0,
            'recurrence_type': request.form.get('recurrence_type') if request.form.get('is_recurring') else None,
            'recurrence_end_date': request.form.get('recurrence_end_date') or None,
            'related_customer_id': int(request.form.get('related_customer_id')) if request.form.get('related_customer_id') else None,
            'created_by': session['user']['id']
        }
        success, message, _ = backend.add_reminder(**data)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('reminders'))
    
    customers = backend.get_all_customers()
    return render_template('reminder_form.html', customers=customers)

@app.route('/reminders/complete', methods=['POST'])
@login_required
def reminder_complete():
    reminder_id = int(request.form.get('id'))
    success, message = backend.complete_reminder(reminder_id, session['user']['id'])
    return jsonify({'success': success, 'message': message})

@app.route('/reminders/delete', methods=['POST'])
@login_required
def reminder_delete():
    reminder_id = int(request.form.get('id'))
    success, message = backend.delete_reminder(reminder_id)
    return jsonify({'success': success, 'message': message})

# ============================================================================
# ROUTE'LAR - NOTLAR
# ============================================================================

@app.route('/notes')
@login_required
def notes():
    tab = request.args.get('tab', 'all')
    
    is_task = None
    is_pinned = None
    
    if tab == 'notes':
        is_task = 0
    elif tab == 'tasks':
        is_task = 1
    elif tab == 'pinned':
        is_pinned = 1
    
    notes = backend.get_notes(is_task=is_task, is_pinned=is_pinned)
    task_summary = backend.get_tasks_summary()
    
    return render_template('notes.html', notes=notes, task_summary=task_summary)

@app.route('/notes/add', methods=['GET', 'POST'])
@login_required
def note_add():
    is_task = request.args.get('type') == 'task'
    
    if request.method == 'POST':
        data = {
            'title': request.form.get('title'),
            'content': request.form.get('content', ''),
            'is_task': 1 if request.form.get('is_task') == '1' else 0,
            'task_due_date': request.form.get('task_due_date') or None,
            'task_priority': request.form.get('task_priority', 'normal'),
            'color': request.form.get('color', '#ffffff'),
            'category': request.form.get('category', ''),
            'is_pinned': 1 if request.form.get('is_pinned') else 0,
            'related_customer_id': int(request.form.get('related_customer_id')) if request.form.get('related_customer_id') else None,
            'created_by': session['user']['id']
        }
        success, message, _ = backend.add_note(**data)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('notes'))
    
    customers = backend.get_all_customers()
    return render_template('note_form.html', note=None, is_task=is_task, customers=customers)

@app.route('/notes/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def note_edit(id):
    note = backend.get_note_by_id(id)
    if not note:
        flash('Not bulunamadı.', 'warning')
        return redirect(url_for('notes'))
    
    if request.method == 'POST':
        data = {
            'title': request.form.get('title'),
            'content': request.form.get('content', ''),
            'task_due_date': request.form.get('task_due_date') or None,
            'task_priority': request.form.get('task_priority', 'normal'),
            'color': request.form.get('color', '#ffffff'),
            'category': request.form.get('category', ''),
            'is_pinned': 1 if request.form.get('is_pinned') else 0,
        }
        success, message = backend.update_note(id, **data)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('notes'))
    
    customers = backend.get_all_customers()
    return render_template('note_form.html', note=note, is_task=note.get('is_task'), customers=customers)

@app.route('/notes/complete', methods=['POST'])
@login_required
def note_complete():
    note_id = int(request.form.get('id'))
    success, message = backend.complete_task(note_id)
    return jsonify({'success': success, 'message': message})

@app.route('/notes/toggle-pin', methods=['POST'])
@login_required
def note_toggle_pin():
    note_id = int(request.form.get('id'))
    success, message = backend.toggle_pin_note(note_id)
    return jsonify({'success': success, 'message': message})

@app.route('/notes/delete', methods=['POST'])
@login_required
def note_delete():
    note_id = int(request.form.get('id'))
    success, message = backend.delete_note(note_id)
    return jsonify({'success': success, 'message': message})

# ============================================================================
# ROUTE'LAR - RAPORLAR
# ============================================================================

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/reports/customer-balances')
@login_required
def report_customer_balances():
    balance_type = request.args.get('type')
    data = backend.get_report_customer_balances(balance_type=balance_type)
    
    if request.args.get('export') == 'csv':
        csv_data = backend.export_customers_csv(balance_type)
        return Response(csv_data, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=cari_bakiyeler.csv'})
    
    # Toplamlar
    total_receivable = sum(c['balance'] for c in data if c['balance'] > 0)
    total_payable = sum(abs(c['balance']) for c in data if c['balance'] < 0)
    
    return render_template('report_view.html',
        report_title='Cari Bakiye Raporu',
        export_url=url_for('report_customer_balances', export='csv', type=balance_type),
        show_type_filter=True,
        type_options=[
            {'value': 'receivable', 'label': 'Alacaklılar'},
            {'value': 'payable', 'label': 'Borçlular'},
        ],
        data=data,
        columns=[
            {'key': 'name', 'label': 'Cari', 'type': 'link', 'route': 'customer_detail', 'id_key': 'id'},
            {'key': 'customer_type', 'label': 'Tür', 'type': 'badge', 'badge_map': {'customer': 'info', 'supplier': 'secondary'}, 'label_map': {'customer': 'Müşteri', 'supplier': 'Tedarikçi'}},
            {'key': 'phone', 'label': 'Telefon'},
            {'key': 'balance', 'label': 'Bakiye', 'type': 'currency', 'class': 'text-end', 'color_condition': True},
        ],
        totals={
            'receivable': {'label': 'Toplam Alacak', 'value': total_receivable, 'is_currency': True, 'color': 'success'},
            'payable': {'label': 'Toplam Borç', 'value': total_payable, 'is_currency': True, 'color': 'danger'},
            'net': {'label': 'Net', 'value': total_receivable - total_payable, 'is_currency': True},
        }
    )

@app.route('/reports/checks')
@login_required
def report_checks():
    check_type = request.args.get('type')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    report = backend.get_report_checks(start_date, end_date, check_type, status)
    
    if request.args.get('export') == 'csv':
        csv_data = backend.export_checks_csv(start_date, end_date, check_type, status)
        return Response(csv_data, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=cek_senet.csv'})
    
    return render_template('report_view.html',
        report_title='Çek/Senet Raporu',
        export_url=url_for('report_checks', export='csv', type=check_type, status=status, start_date=start_date, end_date=end_date),
        show_date_filter=True,
        show_type_filter=True,
        type_options=[
            {'value': 'incoming', 'label': 'Alınan'},
            {'value': 'outgoing', 'label': 'Verilen'},
        ],
        show_status_filter=True,
        status_options=[
            {'value': 'pending', 'label': 'Bekleyen'},
            {'value': 'cashed', 'label': 'Tahsil Edilen'},
            {'value': 'endorsed', 'label': 'Ciro Edilen'},
            {'value': 'returned', 'label': 'İade'},
        ],
        data=report.get('data', []),
        columns=[
            {'key': 'check_number', 'label': 'No'},
            {'key': 'check_type', 'label': 'Tür', 'type': 'badge', 'badge_map': {'incoming': 'success', 'outgoing': 'danger'}, 'label_map': {'incoming': 'Alınan', 'outgoing': 'Verilen'}},
            {'key': 'customer_name', 'label': 'Cari'},
            {'key': 'bank_name', 'label': 'Banka'},
            {'key': 'amount', 'label': 'Tutar', 'type': 'currency', 'class': 'text-end'},
            {'key': 'due_date', 'label': 'Vade'},
            {'key': 'status', 'label': 'Durum', 'type': 'badge', 'badge_map': {'pending': 'warning', 'cashed': 'success', 'endorsed': 'secondary', 'returned': 'danger'}, 'label_map': {'pending': 'Bekliyor', 'cashed': 'Tahsil', 'endorsed': 'Ciro', 'returned': 'İade'}},
        ],
        summary={
            'total': {'label': 'Toplam Çek/Senet', 'value': report.get('summary', {}).get('total_count', 0)},
            'amount': {'label': 'Toplam Tutar', 'value': report.get('summary', {}).get('total_amount', 0), 'is_currency': True},
            'remaining': {'label': 'Kalan Tutar', 'value': report.get('summary', {}).get('total_remaining', 0), 'is_currency': True, 'color': 'warning'},
        }
    )

@app.route('/reports/cash-flow')
@login_required
def report_cashflow():
    trans_type = request.args.get('type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    report = backend.get_report_cash_flow(start_date, end_date)
    
    if request.args.get('export') == 'csv':
        csv_data = backend.export_cash_flow_csv(start_date, end_date)
        return Response(csv_data, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=kasa_hareketleri.csv'})
    
    # Filtrele
    data = report.get('data', [])
    if trans_type:
        data = [t for t in data if t['transaction_type'] == trans_type]
    
    return render_template('report_view.html',
        report_title='Kasa Raporu',
        export_url=url_for('report_cashflow', export='csv', type=trans_type, start_date=start_date, end_date=end_date),
        show_date_filter=True,
        show_type_filter=True,
        type_options=[
            {'value': 'income', 'label': 'Gelirler'},
            {'value': 'expense', 'label': 'Giderler'},
        ],
        data=data,
        columns=[
            {'key': 'transaction_date', 'label': 'Tarih'},
            {'key': 'transaction_type', 'label': 'Tür', 'type': 'badge', 'badge_map': {'income': 'success', 'expense': 'danger'}, 'label_map': {'income': 'Gelir', 'expense': 'Gider'}},
            {'key': 'category', 'label': 'Kategori'},
            {'key': 'description', 'label': 'Açıklama'},
            {'key': 'customer_name', 'label': 'Cari'},
            {'key': 'amount', 'label': 'Tutar', 'type': 'currency', 'class': 'text-end'},
        ],
        summary={
            'income': {'label': 'Toplam Gelir', 'value': report.get('summary', {}).get('total_income', 0), 'is_currency': True, 'color': 'success'},
            'expense': {'label': 'Toplam Gider', 'value': report.get('summary', {}).get('total_expense', 0), 'is_currency': True, 'color': 'danger'},
            'net': {'label': 'Net', 'value': report.get('summary', {}).get('net', 0), 'is_currency': True},
        }
    )

@app.route('/reports/aging')
@login_required
def report_aging():
    aging = backend.get_report_aging()
    
    return render_template('report_view.html',
        report_title='Yaşlandırma Analizi',
        export_url='#',
        data=[
            {
                'period': 'Vadesi Gelmemiş',
                'incoming': aging.get('incoming', {}).get('current', {}).get('amount', 0),
                'incoming_count': aging.get('incoming', {}).get('current', {}).get('count', 0),
                'outgoing': aging.get('outgoing', {}).get('current', {}).get('amount', 0),
                'outgoing_count': aging.get('outgoing', {}).get('current', {}).get('count', 0),
            },
            {
                'period': '1-30 Gün',
                'incoming': aging.get('incoming', {}).get('1_30', {}).get('amount', 0),
                'incoming_count': aging.get('incoming', {}).get('1_30', {}).get('count', 0),
                'outgoing': aging.get('outgoing', {}).get('1_30', {}).get('amount', 0),
                'outgoing_count': aging.get('outgoing', {}).get('1_30', {}).get('count', 0),
            },
            {
                'period': '31-60 Gün',
                'incoming': aging.get('incoming', {}).get('31_60', {}).get('amount', 0),
                'incoming_count': aging.get('incoming', {}).get('31_60', {}).get('count', 0),
                'outgoing': aging.get('outgoing', {}).get('31_60', {}).get('amount', 0),
                'outgoing_count': aging.get('outgoing', {}).get('31_60', {}).get('count', 0),
            },
            {
                'period': '61-90 Gün',
                'incoming': aging.get('incoming', {}).get('61_90', {}).get('amount', 0),
                'incoming_count': aging.get('incoming', {}).get('61_90', {}).get('count', 0),
                'outgoing': aging.get('outgoing', {}).get('61_90', {}).get('amount', 0),
                'outgoing_count': aging.get('outgoing', {}).get('61_90', {}).get('count', 0),
            },
            {
                'period': '90+ Gün',
                'incoming': aging.get('incoming', {}).get('over_90', {}).get('amount', 0),
                'incoming_count': aging.get('incoming', {}).get('over_90', {}).get('count', 0),
                'outgoing': aging.get('outgoing', {}).get('over_90', {}).get('amount', 0),
                'outgoing_count': aging.get('outgoing', {}).get('over_90', {}).get('count', 0),
            },
        ],
        columns=[
            {'key': 'period', 'label': 'Dönem'},
            {'key': 'incoming', 'label': 'Alınan Tutar', 'type': 'currency', 'class': 'text-end'},
            {'key': 'incoming_count', 'label': 'Adet', 'class': 'text-end'},
            {'key': 'outgoing', 'label': 'Verilen Tutar', 'type': 'currency', 'class': 'text-end'},
            {'key': 'outgoing_count', 'label': 'Adet', 'class': 'text-end'},
        ]
    )

@app.route('/reports/activity')
@login_required
def report_activity():
    logs = backend.get_activity_logs(limit=100)
    
    return render_template('report_view.html',
        report_title='Aktivite Raporu',
        export_url='#',
        data=logs,
        columns=[
            {'key': 'created_at', 'label': 'Tarih'},
            {'key': 'user_name', 'label': 'Kullanıcı'},
            {'key': 'action', 'label': 'İşlem'},
            {'key': 'entity_type', 'label': 'Tür'},
            {'key': 'entity_id', 'label': 'ID'},
        ]
    )

# ============================================================================
# ROUTE'LAR - AYARLAR
# ============================================================================

@app.route('/settings', methods=['GET'])
@login_required
def settings():
    settings = backend.get_all_settings()
    categories = backend.get_categories()
    whatsapp_templates = backend.get_whatsapp_templates()
    
    return render_template('settings.html',
        settings=settings,
        categories=categories,
        whatsapp_templates=whatsapp_templates
    )

@app.route('/settings/save', methods=['POST'])
@login_required
def settings_save():
    # Form verilerini parse et
    settings_data = {}
    
    for key, value in request.form.items():
        if '.' in key:
            category, setting_key = key.split('.', 1)
            if category not in settings_data:
                settings_data[category] = {}
            
            # Checkbox değerleri
            if value == 'on':
                value = True
            elif key.startswith('whatsapp.') or key.startswith('notification.') or key.startswith('reminder.') or key.startswith('backup.'):
                # Boolean alanlar için
                if value not in ['True', 'False', '1', '0']:
                    continue
            
            settings_data[category][setting_key] = value
    
    # Checkbox'lar için (işaretlenmemiş olanlar)
    checkbox_fields = [
        'whatsapp.enabled', 'whatsapp.auto_send_check_reminder', 'whatsapp.auto_send_payment_reminder',
        'notification.browser_notifications', 'notification.email_notifications',
        'reminder.auto_create_check_reminder', 'backup.auto_backup'
    ]
    
    for field in checkbox_fields:
        if field not in request.form:
            category, key = field.split('.')
            if category not in settings_data:
                settings_data[category] = {}
            settings_data[category][key] = False
    
    # Ayarları kaydet
    success, message = backend.update_settings_bulk(settings_data)
    
    # WhatsApp şablonlarını kaydet
    for key, value in request.form.items():
        if key.startswith('template_'):
            template_id = int(key.replace('template_', ''))
            backend.update_whatsapp_template(template_id, content=value)
    
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('settings'))

@app.route('/category/add', methods=['POST'])
@login_required
def category_add():
    name = request.form.get('name')
    category_type = request.form.get('type')
    icon = request.form.get('icon', '')
    color = request.form.get('color', '#6c757d')
    
    success, message = backend.add_category(name, category_type, icon, color)
    flash(message, 'success' if success else 'danger')
    
    return redirect(url_for('settings') + '#categories')

@app.route('/category/delete', methods=['POST'])
@login_required
def category_delete():
    category_id = int(request.form.get('id'))
    success, message = backend.delete_category(category_id)
    
    return jsonify({'success': success, 'message': message})

# ============================================================================
# ROUTE'LAR - YEDEKLEME
# ============================================================================

@app.route('/backup/download')
@login_required
def backup_download():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"erp_backup_{timestamp}.db"
    
    success, message = backend.backup_database(backup_filename)
    
    if success:
        return Response(
            open(backup_filename, 'rb').read(),
            mimetype='application/octet-stream',
            headers={'Content-Disposition': f'attachment; filename={backup_filename}'}
        )
    else:
        flash(message, 'danger')
        return redirect(url_for('settings'))

# ============================================================================
# HATA SAYFALARI
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('base.html'), 500

# ============================================================================
# JINJA FILTRELARI
# ============================================================================

@app.template_filter('currency')
def currency_filter(value):
    return format_currency(value)

@app.template_filter('date')
def date_filter(value, fmt='%d/%m/%Y'):
    return format_date(value, fmt)

# ============================================================================
# UYGULAMA BAŞLATMA
# ============================================================================

if __name__ == '__main__':
    # Veritabanını başlat
    backend.init_db()
    
    print("=" * 70)
    print("🌐 ERP WEB UYGULAMASI BAŞLATILIYOR...")
    print("=" * 70)
    print(f"📍 Adres: http://127.0.0.1:5000")
    print(f"📍 Lokal Ağ: http://0.0.0.0:5000")
    print(f"👤 Kullanıcı: admin")
    print(f"🔑 Şifre: admin123")
    print("=" * 70)
    print("✨ ÖZELLİKLER:")
    print("  ✔️ Cari Hesap Yönetimi")
    print("  ✔️ Çek/Senet Takibi (Kısmi Tahsilat, Ciro)")
    print("  ✔️ Kasa Yönetimi (Gelir/Gider)")
    print("  ✔️ Hatırlatıcı Sistemi")
    print("  ✔️ Not Defteri & Görevler")
    print("  ✔️ WhatsApp Entegrasyonu")
    print("  ✔️ Detaylı Raporlar (CSV Export)")
    print("  ✔️ Tam Mobil Uyumlu")
    print("  ✔️ Offline Çalışma")
    print("=" * 70)
    
    # Flask uygulamasını başlat
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)