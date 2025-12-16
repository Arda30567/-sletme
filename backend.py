# ============================================================================
# BACKEND.PY - VERİ KATMANI V3 (TAM ÖZELLİKLİ)
# ============================================================================
# Küçük işletmeler için offline ERP sistemi
# 
# MODÜLLER:
# - Kullanıcı Yönetimi
# - Müşteri/Cari Hesap (Detaylı Borç/Alacak)
# - Çek/Senet Takibi (Kısmi Tahsilat, Ciro)
# - Kasa Yönetimi
# - Gelir/Gider Takibi (Kategorili, Grafikli)
# - Hatırlatıcı/Ajanda
# - Not Defteri/Görev Listesi
# - WhatsApp Entegrasyonu
# - Detaylı Ayarlar
# - Raporlar (Görüntüle + CSV/PDF Export)
# ============================================================================

import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
import csv
import io
import json
import urllib.parse
import os

# ============================================================================
# VERİTABANI AYARLARI
# ============================================================================

DB_NAME = "borc_takip.db"

def get_db_connection():
    """Veritabanı bağlantısı oluşturur."""
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"❌ Veritabanı bağlantı hatası: {e}")
        raise

def dict_from_row(row) -> Optional[Dict]:
    """SQLite Row objesini dict'e çevirir."""
    if row is None:
        return None
    return dict(row)

# ============================================================================
# VERİTABANI BAŞLATMA
# ============================================================================

def init_db():
    """Tüm tabloları oluşturur."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ================================================================
        # 1. KULLANICILAR TABLOSU
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                phone TEXT,
                email TEXT,
                avatar TEXT,
                last_login TIMESTAMP,
                login_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # ================================================================
        # 2. MÜŞTERİLER / CARİ HESAPLAR TABLOSU
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Temel Bilgiler
                name TEXT NOT NULL,
                short_name TEXT,
                customer_type TEXT DEFAULT 'customer',
                customer_group TEXT,
                -- İletişim
                phone TEXT,
                phone2 TEXT,
                whatsapp_phone TEXT,
                email TEXT,
                website TEXT,
                -- Adres
                address TEXT,
                city TEXT,
                district TEXT,
                postal_code TEXT,
                country TEXT DEFAULT 'Türkiye',
                -- Ticari Bilgiler
                tax_office TEXT,
                tax_number TEXT,
                id_number TEXT,
                -- Finansal
                credit_limit REAL DEFAULT 0,
                balance REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'TL',
                payment_term INTEGER DEFAULT 0,
                -- Diğer
                notes TEXT,
                tags TEXT,
                whatsapp_enabled INTEGER DEFAULT 1,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # ================================================================
        # 3. CARİ HESAP HAREKETLERİ
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_after REAL,
                description TEXT,
                reference_type TEXT,
                reference_id INTEGER,
                transaction_date DATE DEFAULT CURRENT_DATE,
                due_date DATE,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # ================================================================
        # 4. ÇEK/SENET TABLOSU
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Temel Bilgiler
                check_type TEXT NOT NULL,
                payment_type TEXT NOT NULL,
                customer_id INTEGER,
                check_number TEXT NOT NULL,
                -- Banka Bilgileri
                bank_name TEXT,
                bank_branch TEXT,
                bank_code TEXT,
                account_number TEXT,
                iban TEXT,
                -- Tutar Bilgileri
                amount REAL NOT NULL,
                paid_amount REAL DEFAULT 0,
                currency TEXT DEFAULT 'TL',
                -- Tarihler
                issue_date DATE,
                due_date DATE NOT NULL,
                -- Durum
                status TEXT DEFAULT 'pending',
                -- Ciro Bilgileri
                is_endorsed INTEGER DEFAULT 0,
                endorser_name TEXT,
                endorser_tax_no TEXT,
                endorser_phone TEXT,
                endorsement_date DATE,
                endorsed_to TEXT,
                -- Ek Bilgiler
                drawer_name TEXT,
                drawer_tax_no TEXT,
                notes TEXT,
                -- Sistem
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # ================================================================
        # 5. ÇEK/SENET HAREKETLERİ
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS check_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (check_id) REFERENCES checks (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # ================================================================
        # 6. KASA HAREKETLERİ
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cash_flow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_type TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'TL',
                exchange_rate REAL DEFAULT 1,
                description TEXT,
                customer_id INTEGER,
                check_id INTEGER,
                payment_method TEXT DEFAULT 'cash',
                reference_no TEXT,
                receipt_no TEXT,
                transaction_date DATE DEFAULT CURRENT_DATE,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id),
                FOREIGN KEY (check_id) REFERENCES checks (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # ================================================================
        # 7. GELİR/GİDER KATEGORİLERİ
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parent_id INTEGER,
                icon TEXT,
                color TEXT,
                is_default INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (parent_id) REFERENCES categories (id)
            )
        ''')
        
        # ================================================================
        # 8. HATIRLATICILAR / AJANDA
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                reminder_type TEXT DEFAULT 'general',
                priority TEXT DEFAULT 'normal',
                due_date DATE NOT NULL,
                due_time TIME,
                -- Tekrarlama
                is_recurring INTEGER DEFAULT 0,
                recurrence_type TEXT,
                recurrence_interval INTEGER DEFAULT 1,
                recurrence_end_date DATE,
                -- İlişkiler
                related_customer_id INTEGER,
                related_check_id INTEGER,
                -- Bildirim
                notify_before_days INTEGER DEFAULT 1,
                notify_via_whatsapp INTEGER DEFAULT 0,
                -- Durum
                status TEXT DEFAULT 'pending',
                snoozed_until TIMESTAMP,
                completed_at TIMESTAMP,
                -- Sistem
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (related_customer_id) REFERENCES customers (id),
                FOREIGN KEY (related_check_id) REFERENCES checks (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # ================================================================
        # 9. NOT DEFTERİ / GÖREVLER
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                note_type TEXT DEFAULT 'note',
                category TEXT,
                color TEXT DEFAULT '#ffffff',
                is_pinned INTEGER DEFAULT 0,
                is_archived INTEGER DEFAULT 0,
                -- Görev özellikleri
                is_task INTEGER DEFAULT 0,
                task_status TEXT DEFAULT 'pending',
                task_priority TEXT DEFAULT 'normal',
                task_due_date DATE,
                task_completed_at TIMESTAMP,
                -- İlişkiler
                related_customer_id INTEGER,
                -- Etiketler (JSON array)
                tags TEXT,
                -- Sistem
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (related_customer_id) REFERENCES customers (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # ================================================================
        # 10. WHATSAPP MESAJ GEÇMİŞİ
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                phone_number TEXT NOT NULL,
                message_type TEXT DEFAULT 'manual',
                message_template TEXT,
                message_content TEXT NOT NULL,
                related_type TEXT,
                related_id INTEGER,
                status TEXT DEFAULT 'pending',
                sent_at TIMESTAMP,
                error_message TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # ================================================================
        # 11. WHATSAPP ŞABLONLARI
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                template_type TEXT NOT NULL,
                content TEXT NOT NULL,
                variables TEXT,
                is_active INTEGER DEFAULT 1,
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ================================================================
        # 12. AYARLAR TABLOSU
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT,
                setting_type TEXT DEFAULT 'string',
                display_name TEXT,
                description TEXT,
                options TEXT,
                is_system INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                updated_at TIMESTAMP,
                UNIQUE(category, setting_key)
            )
        ''')
        
        # ================================================================
        # 13. AKTİVİTE LOGLARI
        # ================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        
        # ================================================================
        # VARSAYILAN VERİLERİ EKLE
        # ================================================================
        _insert_default_data(cursor, conn)
        
        conn.close()
        print("✅ Veritabanı başarıyla başlatıldı!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Veritabanı başlatma hatası: {e}")
        return False

def _insert_default_data(cursor, conn):
    """Varsayılan verileri ekler."""
    
    # Varsayılan admin kullanıcısı
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_password = hash_password("admin123")
        cursor.execute('''
            INSERT INTO users (username, password, full_name, role, email)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', admin_password, 'Sistem Yöneticisi', 'admin', 'admin@localhost'))
        print("✅ Varsayılan admin oluşturuldu (admin / admin123)")
    
    # Varsayılan kategoriler
    default_categories = [
        # Gelir kategorileri
        ('Satış', 'income', None, '💰', '#28a745', 1),
        ('Tahsilat', 'income', None, '💵', '#20c997', 1),
        ('Çek/Senet Tahsilatı', 'income', None, '📄', '#17a2b8', 1),
        ('Faiz Geliri', 'income', None, '📈', '#6f42c1', 1),
        ('Diğer Gelir', 'income', None, '➕', '#6c757d', 1),
        # Gider kategorileri
        ('Maaş/Personel', 'expense', None, '👥', '#dc3545', 1),
        ('Kira', 'expense', None, '🏠', '#fd7e14', 1),
        ('Fatura', 'expense', None, '📋', '#ffc107', 1),
        ('Malzeme/Stok', 'expense', None, '📦', '#007bff', 1),
        ('Ulaşım', 'expense', None, '🚗', '#6610f2', 1),
        ('Vergi', 'expense', None, '🏛️', '#e83e8c', 1),
        ('Banka Masrafları', 'expense', None, '🏦', '#795548', 1),
        ('Ofis Giderleri', 'expense', None, '🖨️', '#607d8b', 1),
        ('Diğer Gider', 'expense', None, '➖', '#6c757d', 1),
    ]
    
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        for name, ctype, parent, icon, color, is_default in default_categories:
            cursor.execute('''
                INSERT INTO categories (name, type, parent_id, icon, color, is_default)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, ctype, parent, icon, color, is_default))
    
    # Varsayılan ayarlar
    default_settings = [
        # Firma Bilgileri
        ('company', 'name', 'İşletmem', 'string', 'Firma Adı', 'Firmanızın adı', None, 0, 1),
        ('company', 'phone', '', 'string', 'Telefon', 'Firma telefonu', None, 0, 2),
        ('company', 'email', '', 'string', 'E-posta', 'Firma e-postası', None, 0, 3),
        ('company', 'address', '', 'text', 'Adres', 'Firma adresi', None, 0, 4),
        ('company', 'tax_office', '', 'string', 'Vergi Dairesi', None, None, 0, 5),
        ('company', 'tax_number', '', 'string', 'Vergi No', None, None, 0, 6),
        ('company', 'logo', '', 'image', 'Logo', 'Firma logosu', None, 0, 7),
        
        # Genel Ayarlar
        ('general', 'currency', 'TL', 'select', 'Para Birimi', None, '["TL","USD","EUR"]', 0, 1),
        ('general', 'date_format', 'DD/MM/YYYY', 'select', 'Tarih Formatı', None, '["DD/MM/YYYY","MM/DD/YYYY","YYYY-MM-DD"]', 0, 2),
        ('general', 'language', 'tr', 'select', 'Dil', None, '["tr","en"]', 0, 3),
        ('general', 'timezone', 'Europe/Istanbul', 'string', 'Saat Dilimi', None, None, 0, 4),
        
        # Hatırlatma Ayarları
        ('reminder', 'check_reminder_days', '3', 'integer', 'Çek Hatırlatma (Gün)', 'Vadeden kaç gün önce hatırlatılsın', None, 0, 1),
        ('reminder', 'payment_reminder_days', '7', 'integer', 'Ödeme Hatırlatma (Gün)', None, None, 0, 2),
        ('reminder', 'auto_create_check_reminder', '1', 'boolean', 'Otomatik Çek Hatırlatıcısı', 'Çek eklendiğinde otomatik hatırlatıcı oluştur', None, 0, 3),
        
        # WhatsApp Ayarları
        ('whatsapp', 'enabled', '0', 'boolean', 'WhatsApp Aktif', 'WhatsApp entegrasyonunu aktif et', None, 0, 1),
        ('whatsapp', 'api_type', 'web', 'select', 'API Tipi', None, '["web","business_api","twilio"]', 0, 2),
        ('whatsapp', 'default_country_code', '+90', 'string', 'Varsayılan Ülke Kodu', None, None, 0, 3),
        ('whatsapp', 'auto_send_check_reminder', '0', 'boolean', 'Otomatik Çek Hatırlatma', 'Vadesi yaklaşan çekler için otomatik mesaj', None, 0, 4),
        ('whatsapp', 'auto_send_payment_reminder', '0', 'boolean', 'Otomatik Ödeme Hatırlatma', 'Vadesi geçen ödemeler için otomatik mesaj', None, 0, 5),
        ('whatsapp', 'business_api_token', '', 'password', 'Business API Token', None, None, 0, 6),
        ('whatsapp', 'business_phone_id', '', 'string', 'Business Phone ID', None, None, 0, 7),
        
        # Bildirim Ayarları
        ('notification', 'browser_notifications', '1', 'boolean', 'Tarayıcı Bildirimleri', None, None, 0, 1),
        ('notification', 'email_notifications', '0', 'boolean', 'E-posta Bildirimleri', None, None, 0, 2),
        ('notification', 'daily_summary', '0', 'boolean', 'Günlük Özet', 'Her gün özet e-postası gönder', None, 0, 3),
        
        # Güvenlik Ayarları
        ('security', 'session_timeout', '30', 'integer', 'Oturum Zaman Aşımı (dk)', None, None, 1, 1),
        ('security', 'max_login_attempts', '5', 'integer', 'Maks. Giriş Denemesi', None, None, 1, 2),
        ('security', 'require_strong_password', '0', 'boolean', 'Güçlü Şifre Zorunlu', None, None, 1, 3),
        
        # Yedekleme Ayarları
        ('backup', 'auto_backup', '1', 'boolean', 'Otomatik Yedekleme', None, None, 0, 1),
        ('backup', 'backup_interval', 'daily', 'select', 'Yedekleme Sıklığı', None, '["daily","weekly","monthly"]', 0, 2),
        ('backup', 'backup_retention_days', '30', 'integer', 'Yedek Saklama (Gün)', None, None, 0, 3),
    ]
    
    for category, key, value, stype, display, desc, options, is_system, sort in default_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO settings 
            (category, setting_key, setting_value, setting_type, display_name, description, options, is_system, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (category, key, value, stype, display, desc, options, is_system, sort))
    
    # Varsayılan WhatsApp şablonları
    default_templates = [
        ('Çek Vade Hatırlatma', 'check_reminder', 
         'Sayın {customer_name},\n\n{due_date} tarihinde vadesi dolacak {amount} tutarındaki çekiniz bulunmaktadır.\n\nBilgilerinize sunarız.\n\n{company_name}',
         '["customer_name","due_date","amount","company_name"]'),
        ('Ödeme Hatırlatma', 'payment_reminder',
         'Sayın {customer_name},\n\nFirmamıza olan {amount} tutarındaki borcunuzun ödeme tarihi yaklaşmıştır.\n\nÖdemenizi {due_date} tarihine kadar yapmanızı rica ederiz.\n\n{company_name}',
         '["customer_name","amount","due_date","company_name"]'),
        ('Tahsilat Bildirimi', 'payment_received',
         'Sayın {customer_name},\n\n{amount} tutarındaki ödemeniz tarafımıza ulaşmıştır.\n\nTeşekkür ederiz.\n\n{company_name}',
         '["customer_name","amount","company_name"]'),
        ('Genel Bilgilendirme', 'general',
         'Sayın {customer_name},\n\n{message}\n\nSaygılarımızla,\n{company_name}',
         '["customer_name","message","company_name"]'),
    ]
    
    cursor.execute("SELECT COUNT(*) FROM whatsapp_templates")
    if cursor.fetchone()[0] == 0:
        for name, ttype, content, variables in default_templates:
            cursor.execute('''
                INSERT INTO whatsapp_templates (name, template_type, content, variables)
                VALUES (?, ?, ?, ?)
            ''', (name, ttype, content, variables))
    
    conn.commit()

# ============================================================================
# ŞİFRE YÖNETİMİ
# ============================================================================

def hash_password(password: str) -> str:
    """SHA256 ile şifre hash'ler."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Şifre doğrulama."""
    return hash_password(password) == hashed

# ============================================================================
# KULLANICI YÖNETİMİ
# ============================================================================

def login_user(username: str, password: str) -> Optional[Dict]:
    """Kullanıcı girişi yapar."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        hashed = hash_password(password)
        cursor.execute('''
            SELECT id, username, full_name, role, email, phone, is_active
            FROM users WHERE username = ? AND password = ? AND is_active = 1
        ''', (username, hashed))
        user = cursor.fetchone()
        
        if user:
            # Login bilgilerini güncelle
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                UPDATE users SET last_login = ?, login_count = login_count + 1 WHERE id = ?
            ''', (now, user['id']))
            conn.commit()
            
            # Log kaydet
            log_activity(user['id'], 'login', 'user', user['id'])
        
        conn.close()
        return dict_from_row(user)
    except sqlite3.Error as e:
        print(f"❌ Login hatası: {e}")
        return None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """ID ile kullanıcı getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict_from_row(user)
    except sqlite3.Error:
        return None

def get_all_users(active_only: bool = True) -> List[Dict]:
    """Tüm kullanıcıları listeler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT id, username, full_name, role, email, phone, last_login, is_active, created_at FROM users"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY full_name"
        cursor.execute(query)
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    except sqlite3.Error:
        return []

def add_user(username: str, password: str, full_name: str, role: str = 'user',
             email: str = "", phone: str = "") -> Tuple[bool, str]:
    """Yeni kullanıcı ekler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        hashed = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, password, full_name, role, email, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, hashed, full_name, role, email, phone))
        conn.commit()
        conn.close()
        return True, "Kullanıcı eklendi!"
    except sqlite3.IntegrityError:
        return False, "Bu kullanıcı adı zaten mevcut!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def update_user(user_id: int, **kwargs) -> Tuple[bool, str]:
    """Kullanıcı günceller."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if 'password' in kwargs and kwargs['password']:
            kwargs['password'] = hash_password(kwargs['password'])
        else:
            kwargs.pop('password', None)
        
        if not kwargs:
            return False, "Güncellenecek alan yok!"
        
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [user_id]
        
        cursor.execute(f"UPDATE users SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True, "Kullanıcı güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def change_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
    """Şifre değiştirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eski şifreyi kontrol et
        cursor.execute("SELECT password FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user or user['password'] != hash_password(old_password):
            conn.close()
            return False, "Mevcut şifre hatalı!"
        
        # Yeni şifreyi kaydet
        new_hashed = hash_password(new_password)
        cursor.execute("UPDATE users SET password = ?, updated_at = ? WHERE id = ?",
                      (new_hashed, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
        conn.commit()
        conn.close()
        return True, "Şifre başarıyla değiştirildi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

# ============================================================================
# MÜŞTERİ / CARİ HESAP YÖNETİMİ
# ============================================================================

def add_customer(name: str, customer_type: str = 'customer', **kwargs) -> Tuple[bool, str, int]:
    """Yeni müşteri/cari hesap ekler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Varsayılan değerler
        kwargs['name'] = name
        kwargs['customer_type'] = customer_type
        
        # WhatsApp numarasını otomatik ayarla
        if not kwargs.get('whatsapp_phone') and kwargs.get('phone'):
            kwargs['whatsapp_phone'] = kwargs['phone']
        
        columns = ', '.join(kwargs.keys())
        placeholders = ', '.join(['?' for _ in kwargs])
        values = list(kwargs.values())
        
        cursor.execute(f'''
            INSERT INTO customers ({columns}) VALUES ({placeholders})
        ''', values)
        
        customer_id = cursor.lastrowid
        conn.commit()
        
        # Log
        log_activity(kwargs.get('created_by', 1), 'create', 'customer', customer_id)
        
        conn.close()
        return True, "Cari hesap başarıyla eklendi!", customer_id
    except sqlite3.Error as e:
        return False, f"Hata: {e}", 0

def update_customer(customer_id: int, **kwargs) -> Tuple[bool, str]:
    """Müşteri günceller."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [customer_id]
        
        cursor.execute(f"UPDATE customers SET {fields} WHERE id = ?", values)
        conn.commit()
        
        log_activity(kwargs.get('updated_by', 1), 'update', 'customer', customer_id)
        
        conn.close()
        return True, "Cari hesap güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def delete_customer(customer_id: int, soft_delete: bool = True) -> Tuple[bool, str]:
    """Müşteri siler (soft delete varsayılan)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if soft_delete:
            cursor.execute("UPDATE customers SET is_active = 0, updated_at = ? WHERE id = ?",
                          (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), customer_id))
        else:
            cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        
        conn.commit()
        conn.close()
        return True, "Cari hesap silindi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def get_all_customers(customer_type: str = None, active_only: bool = True,
                      search: str = None, order_by: str = 'name') -> List[Dict]:
    """Müşterileri listeler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT c.*, 
                   (SELECT COUNT(*) FROM checks WHERE customer_id = c.id AND status = 'pending') as pending_checks,
                   (SELECT COALESCE(SUM(amount - paid_amount), 0) FROM checks 
                    WHERE customer_id = c.id AND check_type = 'incoming' AND status = 'pending') as incoming_checks_total,
                   (SELECT COALESCE(SUM(amount - paid_amount), 0) FROM checks 
                    WHERE customer_id = c.id AND check_type = 'outgoing' AND status = 'pending') as outgoing_checks_total
            FROM customers c WHERE 1=1
        '''
        params = []
        
        if active_only:
            query += " AND c.is_active = 1"
        if customer_type:
            query += " AND c.customer_type = ?"
            params.append(customer_type)
        if search:
            query += " AND (c.name LIKE ? OR c.phone LIKE ? OR c.email LIKE ? OR c.tax_number LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param, search_param])
        
        query += f" ORDER BY c.{order_by}"
        
        cursor.execute(query, params)
        customers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return customers
    except sqlite3.Error as e:
        print(f"❌ Müşteri listeleme hatası: {e}")
        return []

def get_customer_by_id(customer_id: int) -> Optional[Dict]:
    """ID ile müşteri getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*,
                   (SELECT COUNT(*) FROM checks WHERE customer_id = c.id) as total_checks,
                   (SELECT COUNT(*) FROM account_transactions WHERE customer_id = c.id) as total_transactions
            FROM customers c WHERE c.id = ?
        ''', (customer_id,))
        customer = cursor.fetchone()
        conn.close()
        return dict_from_row(customer)
    except sqlite3.Error:
        return None

def search_customers(query: str, limit: int = 10) -> List[Dict]:
    """Müşteri arar (autocomplete için)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        search = f"%{query}%"
        cursor.execute('''
            SELECT id, name, phone, balance, customer_type
            FROM customers 
            WHERE is_active = 1 AND (name LIKE ? OR phone LIKE ? OR short_name LIKE ?)
            ORDER BY name LIMIT ?
        ''', (search, search, search, limit))
        customers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return customers
    except sqlite3.Error:
        return []

def update_customer_balance(customer_id: int, amount: float, description: str = "",
                           ref_type: str = "", ref_id: int = None, 
                           transaction_date: str = None, due_date: str = None,
                           created_by: int = 1) -> Tuple[bool, str]:
    """Müşteri bakiyesini günceller ve hareket kaydeder."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Mevcut bakiyeyi al
        cursor.execute("SELECT balance FROM customers WHERE id = ?", (customer_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Müşteri bulunamadı!"
        
        new_balance = result['balance'] + amount
        
        # Bakiyeyi güncelle
        cursor.execute("UPDATE customers SET balance = ?, updated_at = ? WHERE id = ?",
                      (new_balance, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), customer_id))
        
        # Cari hareket kaydet
        trans_type = 'credit' if amount > 0 else 'debit'
        if not transaction_date:
            transaction_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT INTO account_transactions 
            (customer_id, transaction_type, amount, balance_after, description, 
             reference_type, reference_id, transaction_date, due_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_id, trans_type, abs(amount), new_balance, description,
              ref_type, ref_id, transaction_date, due_date, created_by))
        
        conn.commit()
        conn.close()
        return True, "Bakiye güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def get_customer_transactions(customer_id: int, start_date: str = None, 
                              end_date: str = None, limit: int = None) -> List[Dict]:
    """Müşteri cari hareketlerini getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT at.*, u.full_name as created_by_name
            FROM account_transactions at
            LEFT JOIN users u ON at.created_by = u.id
            WHERE at.customer_id = ?
        '''
        params = [customer_id]
        
        if start_date:
            query += " AND at.transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND at.transaction_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY at.created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        transactions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return transactions
    except sqlite3.Error:
        return []

def get_customer_statement(customer_id: int, start_date: str = None, end_date: str = None) -> Dict:
    """Müşteri hesap ekstresi getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Müşteri bilgisi
        customer = get_customer_by_id(customer_id)
        if not customer:
            return {}
        
        # Dönem başı bakiye
        opening_balance = 0
        if start_date:
            cursor.execute('''
                SELECT COALESCE(
                    (SELECT balance_after FROM account_transactions 
                     WHERE customer_id = ? AND transaction_date < ?
                     ORDER BY created_at DESC LIMIT 1), 0
                ) as opening
            ''', (customer_id, start_date))
            opening_balance = cursor.fetchone()['opening']
        
        # Hareketler
        transactions = get_customer_transactions(customer_id, start_date, end_date)
        
        # Özet
        total_debit = sum(t['amount'] for t in transactions if t['transaction_type'] == 'debit')
        total_credit = sum(t['amount'] for t in transactions if t['transaction_type'] == 'credit')
        
        conn.close()
        
        return {
            'customer': customer,
            'opening_balance': opening_balance,
            'transactions': transactions,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'closing_balance': customer['balance'],
            'period': {'start': start_date, 'end': end_date}
        }
    except sqlite3.Error:
        return {}

# ============================================================================
# AYARLAR YÖNETİMİ
# ============================================================================

def get_setting(category: str, key: str, default: Any = None) -> Any:
    """Tek bir ayarı getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT setting_value, setting_type FROM settings 
            WHERE category = ? AND setting_key = ?
        ''', (category, key))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            value = result['setting_value']
            stype = result['setting_type']
            
            # Tip dönüşümü
            if stype == 'integer':
                return int(value) if value else default
            elif stype == 'boolean':
                return value == '1'
            elif stype == 'json':
                return json.loads(value) if value else default
            elif stype == 'float':
                return float(value) if value else default
            else:
                return value if value else default
        return default
    except sqlite3.Error:
        return default

def get_settings_by_category(category: str) -> Dict:
    """Kategoriye göre tüm ayarları getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT setting_key, setting_value, setting_type, display_name, description, options
            FROM settings WHERE category = ? ORDER BY sort_order
        ''', (category,))
        
        settings = {}
        for row in cursor.fetchall():
            value = row['setting_value']
            stype = row['setting_type']
            
            if stype == 'integer':
                value = int(value) if value else 0
            elif stype == 'boolean':
                value = value == '1'
            elif stype == 'json':
                value = json.loads(value) if value else None
            
            settings[row['setting_key']] = {
                'value': value,
                'type': stype,
                'display_name': row['display_name'],
                'description': row['description'],
                'options': json.loads(row['options']) if row['options'] else None
            }
        
        conn.close()
        return settings
    except sqlite3.Error:
        return {}

def get_all_settings() -> Dict:
    """Tüm ayarları kategorilere göre gruplar."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM settings ORDER BY category")
        categories = [row['category'] for row in cursor.fetchall()]
        conn.close()
        
        all_settings = {}
        for cat in categories:
            all_settings[cat] = get_settings_by_category(cat)
        
        return all_settings
    except sqlite3.Error:
        return {}

def update_setting(category: str, key: str, value: Any) -> Tuple[bool, str]:
    """Ayar günceller."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Boolean değerleri dönüştür
        if isinstance(value, bool):
            value = '1' if value else '0'
        elif isinstance(value, (dict, list)):
            value = json.dumps(value)
        else:
            value = str(value)
        
        cursor.execute('''
            UPDATE settings SET setting_value = ?, updated_at = ?
            WHERE category = ? AND setting_key = ?
        ''', (value, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), category, key))
        
        conn.commit()
        conn.close()
        return True, "Ayar güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def update_settings_bulk(settings: Dict) -> Tuple[bool, str]:
    """Birden fazla ayarı günceller."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for category, items in settings.items():
            for key, value in items.items():
                if isinstance(value, bool):
                    value = '1' if value else '0'
                elif isinstance(value, (dict, list)):
                    value = json.dumps(value)
                else:
                    value = str(value)
                
                cursor.execute('''
                    UPDATE settings SET setting_value = ?, updated_at = ?
                    WHERE category = ? AND setting_key = ?
                ''', (value, now, category, key))
        
        conn.commit()
        conn.close()
        return True, "Ayarlar güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

# ============================================================================
# AKTİVİTE LOG
# ============================================================================

def log_activity(user_id: int, action: str, entity_type: str = None, 
                 entity_id: int = None, old_values: Dict = None, 
                 new_values: Dict = None):
    """Aktivite loglar."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_logs (user_id, action, entity_type, entity_id, old_values, new_values)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, action, entity_type, entity_id,
              json.dumps(old_values) if old_values else None,
              json.dumps(new_values) if new_values else None))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass

def get_activity_logs(user_id: int = None, entity_type: str = None, 
                      limit: int = 100) -> List[Dict]:
    """Aktivite loglarını getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT al.*, u.full_name as user_name
            FROM activity_logs al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE 1=1
        '''
        params = []
        
        if user_id:
            query += " AND al.user_id = ?"
            params.append(user_id)
        if entity_type:
            query += " AND al.entity_type = ?"
            params.append(entity_type)
        
        query += f" ORDER BY al.created_at DESC LIMIT {limit}"
        
        cursor.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return logs
    except sqlite3.Error:
        return []

print("=" * 70)
print("✅ BACKEND V3 - PARÇA 1/3 TAMAMLANDI!")
print("=" * 70)
print("📦 İçerik:")
print("  ✔️ Veritabanı Şeması (13 Tablo)")
print("  ✔️ Varsayılan Veriler (Kategoriler, Ayarlar, Şablonlar)")
print("  ✔️ Kullanıcı Yönetimi")
print("  ✔️ Müşteri/Cari Hesap Yönetimi (Detaylı)")
print("  ✔️ Cari Hareket & Ekstre")
print("  ✔️ Ayarlar Yönetimi")
print("  ✔️ Aktivite Log")
print("=" * 70)# ============================================================================
# BACKEND.PY - PARÇA 2/3: ÇEK/SENET + KASA + GELİR/GİDER
# ============================================================================

# ============================================================================
# ÇEK/SENET YÖNETİMİ (TAM ÖZELLİKLİ)
# ============================================================================

def add_check(check_type: str, payment_type: str, check_number: str, 
              amount: float, due_date: str, customer_id: int = None,
              bank_name: str = "", bank_branch: str = "", bank_code: str = "",
              account_number: str = "", iban: str = "", issue_date: str = None,
              drawer_name: str = "", drawer_tax_no: str = "", notes: str = "",
              created_by: int = 1) -> Tuple[bool, str, int]:
    """Yeni çek/senet ekler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not issue_date:
            issue_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT INTO checks (
                check_type, payment_type, customer_id, check_number,
                bank_name, bank_branch, bank_code, account_number, iban,
                amount, issue_date, due_date, drawer_name, drawer_tax_no,
                notes, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (check_type, payment_type, customer_id, check_number,
              bank_name, bank_branch, bank_code, account_number, iban,
              amount, issue_date, due_date, drawer_name, drawer_tax_no,
              notes, created_by))
        
        check_id = cursor.lastrowid
        
        # İlk hareket kaydı
        cursor.execute('''
            INSERT INTO check_transactions (check_id, transaction_type, amount, description, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (check_id, 'created', amount, 'Çek/Senet oluşturuldu', created_by))
        
        # Otomatik hatırlatıcı oluştur (ayarlardan kontrol)
        auto_reminder = get_setting('reminder', 'auto_create_check_reminder', True)
        reminder_days = get_setting('reminder', 'check_reminder_days', 3)
        
        if auto_reminder:
            reminder_date = (datetime.strptime(due_date, '%Y-%m-%d') - timedelta(days=reminder_days)).strftime('%Y-%m-%d')
            type_text = 'Çek' if payment_type == 'check' else 'Senet'
            direction_text = 'Alınan' if check_type == 'incoming' else 'Verilen'
            
            cursor.execute('''
                INSERT INTO reminders (title, description, reminder_type, priority, due_date,
                                      related_customer_id, related_check_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (f"{direction_text} {type_text} Vadesi - {check_number}",
                  f"Tutar: {amount:,.2f} TL\nVade: {due_date}",
                  'check', 'high', reminder_date, customer_id, check_id, created_by))
        
        conn.commit()
        log_activity(created_by, 'create', 'check', check_id)
        conn.close()
        
        return True, "Çek/Senet başarıyla eklendi!", check_id
    except sqlite3.Error as e:
        return False, f"Hata: {e}", 0

def update_check(check_id: int, **kwargs) -> Tuple[bool, str]:
    """Çek/Senet günceller."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [check_id]
        
        cursor.execute(f"UPDATE checks SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True, "Çek/Senet güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def get_all_checks(check_type: str = None, status: str = None, 
                   customer_id: int = None, start_date: str = None,
                   end_date: str = None, search: str = None,
                   order_by: str = 'due_date') -> List[Dict]:
    """Çek/Senetleri listeler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT c.*, 
                   cu.name as customer_name,
                   cu.phone as customer_phone,
                   u.full_name as created_by_name,
                   (c.amount - c.paid_amount) as remaining_amount,
                   CASE 
                       WHEN c.status = 'pending' AND date(c.due_date) < date('now') THEN 'overdue'
                       WHEN c.status = 'pending' AND date(c.due_date) <= date('now', '+7 days') THEN 'upcoming'
                       ELSE c.status
                   END as display_status,
                   CAST(julianday(c.due_date) - julianday('now') AS INTEGER) as days_until_due
            FROM checks c
            LEFT JOIN customers cu ON c.customer_id = cu.id
            LEFT JOIN users u ON c.created_by = u.id
            WHERE 1=1
        '''
        params = []
        
        if check_type:
            query += " AND c.check_type = ?"
            params.append(check_type)
        
        if status:
            if status == 'overdue':
                query += " AND c.status = 'pending' AND date(c.due_date) < date('now')"
            elif status == 'upcoming':
                query += " AND c.status = 'pending' AND date(c.due_date) >= date('now') AND date(c.due_date) <= date('now', '+7 days')"
            else:
                query += " AND c.status = ?"
                params.append(status)
        
        if customer_id:
            query += " AND c.customer_id = ?"
            params.append(customer_id)
        
        if start_date:
            query += " AND c.due_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND c.due_date <= ?"
            params.append(end_date)
        
        if search:
            query += " AND (c.check_number LIKE ? OR c.bank_name LIKE ? OR cu.name LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        query += f" ORDER BY c.{order_by}"
        
        cursor.execute(query, params)
        checks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return checks
    except sqlite3.Error as e:
        print(f"❌ Çek listeleme hatası: {e}")
        return []

def get_check_by_id(check_id: int) -> Optional[Dict]:
    """ID ile çek getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, cu.name as customer_name, cu.phone as customer_phone,
                   (c.amount - c.paid_amount) as remaining_amount
            FROM checks c
            LEFT JOIN customers cu ON c.customer_id = cu.id
            WHERE c.id = ?
        ''', (check_id,))
        check = cursor.fetchone()
        conn.close()
        return dict_from_row(check)
    except sqlite3.Error:
        return None

def process_check_payment(check_id: int, amount: float = None, status: str = 'cashed',
                          description: str = "", created_by: int = 1) -> Tuple[bool, str]:
    """
    Çek/Senet ödeme işlemi yapar.
    status: 'cashed' (tam tahsil), 'partial' (kısmi), 'returned' (iade), 'cancelled' (iptal)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Çeki getir
        cursor.execute('SELECT * FROM checks WHERE id = ?', (check_id,))
        check = cursor.fetchone()
        if not check:
            conn.close()
            return False, "Çek/Senet bulunamadı!"
        check = dict(check)
        
        if check['status'] != 'pending':
            conn.close()
            return False, "Bu çek zaten işlenmiş!"
        
        remaining = check['amount'] - check['paid_amount']
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.now().strftime('%Y-%m-%d')
        
        if status == 'partial':
            # Kısmi tahsilat
            if not amount or amount <= 0:
                conn.close()
                return False, "Geçerli bir tutar giriniz!"
            
            if amount > remaining:
                amount = remaining
            
            new_paid = check['paid_amount'] + amount
            new_status = 'cashed' if new_paid >= check['amount'] else 'pending'
            
            cursor.execute('''
                UPDATE checks SET paid_amount = ?, status = ?, updated_at = ? WHERE id = ?
            ''', (new_paid, new_status, now, check_id))
            
            cursor.execute('''
                INSERT INTO check_transactions (check_id, transaction_type, amount, description, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (check_id, 'partial_payment', amount, description or f"Kısmi tahsilat", created_by))
            
            # Kasaya gelir ekle (alınan çek ise)
            if check['check_type'] == 'incoming':
                cursor.execute('''
                    INSERT INTO cash_flow (transaction_type, category, amount, description, 
                                          customer_id, check_id, payment_method, transaction_date, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ('income', 'Çek/Senet Tahsilatı', amount,
                      f"Çek No: {check['check_number']} - Kısmi Tahsilat",
                      check['customer_id'], check_id, 'check', today, created_by))
                
                # Müşteri bakiyesini güncelle
                if check['customer_id']:
                    update_customer_balance(check['customer_id'], amount,
                                           f"Çek tahsilatı: {check['check_number']}",
                                           'check', check_id, today, None, created_by)
            
            message = f"Kısmi tahsilat yapıldı: {amount:,.2f} TL"
            
        elif status == 'cashed':
            # Tam tahsilat
            amount = remaining
            
            cursor.execute('''
                UPDATE checks SET paid_amount = amount, status = 'cashed', updated_at = ? WHERE id = ?
            ''', (now, check_id))
            
            cursor.execute('''
                INSERT INTO check_transactions (check_id, transaction_type, amount, description, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (check_id, 'cashed', amount, description or "Tam tahsilat", created_by))
            
            if check['check_type'] == 'incoming' and amount > 0:
                cursor.execute('''
                    INSERT INTO cash_flow (transaction_type, category, amount, description, 
                                          customer_id, check_id, payment_method, transaction_date, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ('income', 'Çek/Senet Tahsilatı', amount,
                      f"Çek No: {check['check_number']} - Tahsil Edildi",
                      check['customer_id'], check_id, 'check', today, created_by))
                
                if check['customer_id']:
                    update_customer_balance(check['customer_id'], amount,
                                           f"Çek tahsilatı: {check['check_number']}",
                                           'check', check_id, today, None, created_by)
            
            # İlgili hatırlatıcıları tamamla
            cursor.execute('''
                UPDATE reminders SET status = 'completed', completed_at = ?
                WHERE related_check_id = ? AND status = 'pending'
            ''', (now, check_id))
            
            message = "Çek/Senet tahsil edildi!"
            
        elif status == 'returned':
            # İade/Karşılıksız
            cursor.execute('''
                UPDATE checks SET status = 'returned', updated_at = ? WHERE id = ?
            ''', (now, check_id))
            
            cursor.execute('''
                INSERT INTO check_transactions (check_id, transaction_type, amount, description, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (check_id, 'returned', 0, description or "İade/Karşılıksız", created_by))
            
            # Daha önce kısmi tahsilat yapıldıysa iade et
            if check['paid_amount'] > 0 and check['check_type'] == 'incoming':
                cursor.execute('''
                    INSERT INTO cash_flow (transaction_type, category, amount, description, 
                                          customer_id, check_id, payment_method, transaction_date, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ('expense', 'Çek/Senet İadesi', check['paid_amount'],
                      f"Çek No: {check['check_number']} - Karşılıksız İade",
                      check['customer_id'], check_id, 'check', today, created_by))
                
                if check['customer_id']:
                    update_customer_balance(check['customer_id'], -check['paid_amount'],
                                           f"Karşılıksız çek iadesi: {check['check_number']}",
                                           'check', check_id, today, None, created_by)
            
            message = "Çek/Senet iade edildi!"
            
        elif status == 'cancelled':
            cursor.execute('''
                UPDATE checks SET status = 'cancelled', updated_at = ? WHERE id = ?
            ''', (now, check_id))
            
            cursor.execute('''
                INSERT INTO check_transactions (check_id, transaction_type, amount, description, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (check_id, 'cancelled', 0, description or "İptal edildi", created_by))
            
            message = "Çek/Senet iptal edildi!"
        
        else:
            conn.close()
            return False, "Geçersiz işlem türü!"
        
        conn.commit()
        log_activity(created_by, f'check_{status}', 'check', check_id)
        conn.close()
        return True, message
        
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def endorse_check(check_id: int, endorser_name: str, endorser_tax_no: str = "",
                  endorser_phone: str = "", endorsed_to: str = "",
                  description: str = "", created_by: int = 1) -> Tuple[bool, str]:
    """Çek ciro eder."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Çeki kontrol et
        cursor.execute('SELECT * FROM checks WHERE id = ? AND status = ?', (check_id, 'pending'))
        check = cursor.fetchone()
        if not check:
            conn.close()
            return False, "Çek bulunamadı veya ciro edilemez durumda!"
        check = dict(check)
        
        if check['check_type'] != 'incoming':
            conn.close()
            return False, "Sadece alınan çekler ciro edilebilir!"
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            UPDATE checks SET 
                status = 'endorsed', is_endorsed = 1,
                endorser_name = ?, endorser_tax_no = ?, endorser_phone = ?,
                endorsement_date = ?, endorsed_to = ?, updated_at = ?
            WHERE id = ?
        ''', (endorser_name, endorser_tax_no, endorser_phone, today, endorsed_to, now, check_id))
        
        cursor.execute('''
            INSERT INTO check_transactions (check_id, transaction_type, amount, description, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (check_id, 'endorsed', check['amount'], 
              description or f"Ciro: {endorser_name}", created_by))
        
        # Hatırlatıcıyı tamamla
        cursor.execute('''
            UPDATE reminders SET status = 'completed', completed_at = ?
            WHERE related_check_id = ? AND status = 'pending'
        ''', (now, check_id))
        
        conn.commit()
        log_activity(created_by, 'endorse', 'check', check_id)
        conn.close()
        return True, "Çek başarıyla ciro edildi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def get_check_transactions(check_id: int) -> List[Dict]:
    """Çek hareket geçmişini getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ct.*, u.full_name as created_by_name
            FROM check_transactions ct
            LEFT JOIN users u ON ct.created_by = u.id
            WHERE ct.check_id = ?
            ORDER BY ct.transaction_date DESC
        ''', (check_id,))
        transactions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return transactions
    except sqlite3.Error:
        return []

def get_checks_summary() -> Dict:
    """Çek/Senet özet istatistikleri."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        summary = {}
        
        # Alınan bekleyen
        cursor.execute('''
            SELECT COALESCE(SUM(amount - paid_amount), 0) as total, COUNT(*) as count
            FROM checks WHERE check_type = 'incoming' AND status = 'pending'
        ''')
        row = cursor.fetchone()
        summary['incoming_pending_amount'] = row['total']
        summary['incoming_pending_count'] = row['count']
        
        # Verilen bekleyen
        cursor.execute('''
            SELECT COALESCE(SUM(amount - paid_amount), 0) as total, COUNT(*) as count
            FROM checks WHERE check_type = 'outgoing' AND status = 'pending'
        ''')
        row = cursor.fetchone()
        summary['outgoing_pending_amount'] = row['total']
        summary['outgoing_pending_count'] = row['count']
        
        # Vadesi geçenler
        cursor.execute('''
            SELECT COUNT(*) as count, COALESCE(SUM(amount - paid_amount), 0) as total
            FROM checks WHERE status = 'pending' AND date(due_date) < date('now')
        ''')
        row = cursor.fetchone()
        summary['overdue_count'] = row['count']
        summary['overdue_amount'] = row['total']
        
        # Bu hafta vadesi dolanlar
        cursor.execute('''
            SELECT COUNT(*) as count, COALESCE(SUM(amount - paid_amount), 0) as total
            FROM checks WHERE status = 'pending' 
            AND date(due_date) >= date('now') AND date(due_date) <= date('now', '+7 days')
        ''')
        row = cursor.fetchone()
        summary['this_week_count'] = row['count']
        summary['this_week_amount'] = row['total']
        
        # Bu ay vadesi dolanlar
        cursor.execute('''
            SELECT COUNT(*) as count, COALESCE(SUM(amount - paid_amount), 0) as total
            FROM checks WHERE status = 'pending'
            AND strftime('%Y-%m', due_date) = strftime('%Y-%m', 'now')
        ''')
        row = cursor.fetchone()
        summary['this_month_count'] = row['count']
        summary['this_month_amount'] = row['total']
        
        # Ciro edilenler
        cursor.execute('''
            SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
            FROM checks WHERE status = 'endorsed'
        ''')
        row = cursor.fetchone()
        summary['endorsed_count'] = row['count']
        summary['endorsed_amount'] = row['total']
        
        conn.close()
        return summary
    except sqlite3.Error:
        return {}

def get_upcoming_checks(days: int = 7) -> List[Dict]:
    """Vadesi yaklaşan çek/senetleri getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        future_date = (today + timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT c.*, cu.name as customer_name,
                   CAST(julianday(c.due_date) - julianday('now') AS INTEGER) as days_left
            FROM checks c
            LEFT JOIN customers cu ON c.customer_id = cu.id
            WHERE c.status = 'pending'
            AND c.due_date <= ?
            AND c.due_date >= ?
            ORDER BY c.due_date ASC
        ''', (future_date, today.strftime('%Y-%m-%d')))
        
        checks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return checks
    except sqlite3.Error as e:
        print(f"❌ Vadesi yaklaşan çek sorgulama hatası: {e}")
        return []
def get_overdue_checks() -> List[Dict]:
    """Vadesi geçmiş çek/senetleri getirir."""
    return get_all_checks(status='overdue')

# ============================================================================
# KASA YÖNETİMİ
# ============================================================================

def add_cash_transaction(transaction_type: str, category: str, amount: float,
                         description: str = "", customer_id: int = None,
                         subcategory: str = "", payment_method: str = "cash",
                         reference_no: str = "", receipt_no: str = "",
                         transaction_date: str = None, created_by: int = 1) -> Tuple[bool, str, int]:
    """Kasa hareketi ekler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not transaction_date:
            transaction_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT INTO cash_flow (
                transaction_type, category, subcategory, amount, description,
                customer_id, payment_method, reference_no, receipt_no,
                transaction_date, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_type, category, subcategory, amount, description,
              customer_id, payment_method, reference_no, receipt_no,
              transaction_date, created_by))
        
        transaction_id = cursor.lastrowid
        
        # Müşteri bakiyesini güncelle
        if customer_id:
            balance_change = amount if transaction_type == 'income' else -amount
            cursor.execute("SELECT balance FROM customers WHERE id = ?", (customer_id,))
            result = cursor.fetchone()
            if result:
                new_balance = result['balance'] - balance_change  # Tahsilat = borç azalır
                cursor.execute("UPDATE customers SET balance = ? WHERE id = ?", (new_balance, customer_id))
                
                # Cari hareket kaydet
                trans_type = 'credit' if transaction_type == 'income' else 'debit'
                cursor.execute('''
                    INSERT INTO account_transactions 
                    (customer_id, transaction_type, amount, balance_after, description, 
                     reference_type, reference_id, transaction_date, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (customer_id, trans_type, amount, new_balance, description,
                      'cash_flow', transaction_id, transaction_date, created_by))
        
        conn.commit()
        log_activity(created_by, 'create', 'cash_flow', transaction_id)
        conn.close()
        return True, "Kasa hareketi kaydedildi!", transaction_id
    except sqlite3.Error as e:
        return False, f"Hata: {e}", 0

def get_cash_flow(start_date: str = None, end_date: str = None,
                  category: str = None, transaction_type: str = None,
                  customer_id: int = None, payment_method: str = None,
                  search: str = None, limit: int = None) -> List[Dict]:
    """Kasa hareketlerini listeler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT cf.*, c.name as customer_name, u.full_name as created_by_name,
                   cat.icon as category_icon, cat.color as category_color
            FROM cash_flow cf
            LEFT JOIN customers c ON cf.customer_id = c.id
            LEFT JOIN users u ON cf.created_by = u.id
            LEFT JOIN categories cat ON cf.category = cat.name AND cat.type = cf.transaction_type
            WHERE 1=1
        '''
        params = []
        
        if start_date:
            query += " AND cf.transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND cf.transaction_date <= ?"
            params.append(end_date)
        if category:
            query += " AND cf.category = ?"
            params.append(category)
        if transaction_type:
            query += " AND cf.transaction_type = ?"
            params.append(transaction_type)
        if customer_id:
            query += " AND cf.customer_id = ?"
            params.append(customer_id)
        if payment_method:
            query += " AND cf.payment_method = ?"
            params.append(payment_method)
        if search:
            query += " AND (cf.description LIKE ? OR cf.reference_no LIKE ? OR c.name LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        query += " ORDER BY cf.transaction_date DESC, cf.created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        transactions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return transactions
    except sqlite3.Error as e:
        print(f"❌ Kasa listeleme hatası: {e}")
        return []

def get_cash_balance() -> Dict:
    """Kasa bakiye özeti."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Genel toplam
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0) as total_expense
            FROM cash_flow
        ''')
        row = cursor.fetchone()
        total_income = row['total_income']
        total_expense = row['total_expense']
        
        # Bugünkü hareketler
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) as today_income,
                COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0) as today_expense
            FROM cash_flow WHERE transaction_date = date('now')
        ''')
        today = cursor.fetchone()
        
        # Bu ayki hareketler
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) as month_income,
                COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0) as month_expense
            FROM cash_flow WHERE strftime('%Y-%m', transaction_date) = strftime('%Y-%m', 'now')
        ''')
        month = cursor.fetchone()
        
        # Bu haftaki hareketler
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) as week_income,
                COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0) as week_expense
            FROM cash_flow WHERE transaction_date >= date('now', '-7 days')
        ''')
        week = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'today_income': today['today_income'],
            'today_expense': today['today_expense'],
            'today_balance': today['today_income'] - today['today_expense'],
            'week_income': week['week_income'],
            'week_expense': week['week_expense'],
            'week_balance': week['week_income'] - week['week_expense'],
            'month_income': month['month_income'],
            'month_expense': month['month_expense'],
            'month_balance': month['month_income'] - month['month_expense']
        }
    except sqlite3.Error:
        return {
            'total_income': 0, 'total_expense': 0, 'balance': 0,
            'today_income': 0, 'today_expense': 0, 'today_balance': 0,
            'week_income': 0, 'week_expense': 0, 'week_balance': 0,
            'month_income': 0, 'month_expense': 0, 'month_balance': 0
        }

def get_cash_flow_by_category(start_date: str = None, end_date: str = None,
                               transaction_type: str = None) -> List[Dict]:
    """Kategoriye göre kasa özeti."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT cf.category, cf.transaction_type,
                   COALESCE(SUM(cf.amount), 0) as total,
                   COUNT(*) as count,
                   cat.icon, cat.color
            FROM cash_flow cf
            LEFT JOIN categories cat ON cf.category = cat.name AND cat.type = cf.transaction_type
            WHERE 1=1
        '''
        params = []
        
        if start_date:
            query += " AND cf.transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND cf.transaction_date <= ?"
            params.append(end_date)
        if transaction_type:
            query += " AND cf.transaction_type = ?"
            params.append(transaction_type)
        
        query += " GROUP BY cf.category, cf.transaction_type ORDER BY total DESC"
        
        cursor.execute(query, params)
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return data
    except sqlite3.Error:
        return []

def get_cash_flow_by_date(start_date: str = None, end_date: str = None,
                          group_by: str = 'day') -> List[Dict]:
    """Tarihe göre kasa özeti (grafik için)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if group_by == 'day':
            date_format = '%Y-%m-%d'
            date_field = "date(cf.transaction_date)"
        elif group_by == 'week':
            date_format = '%Y-%W'
            date_field = "strftime('%Y-%W', cf.transaction_date)"
        elif group_by == 'month':
            date_format = '%Y-%m'
            date_field = "strftime('%Y-%m', cf.transaction_date)"
        else:
            date_format = '%Y'
            date_field = "strftime('%Y', cf.transaction_date)"
        
        query = f'''
            SELECT {date_field} as period,
                   COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) as income,
                   COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0) as expense
            FROM cash_flow cf
            WHERE 1=1
        '''
        params = []
        
        if start_date:
            query += " AND cf.transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND cf.transaction_date <= ?"
            params.append(end_date)
        
        query += f" GROUP BY {date_field} ORDER BY period"
        
        cursor.execute(query, params)
        data = [dict(row) for row in cursor.fetchall()]
        
        # Balance hesapla
        for item in data:
            item['balance'] = item['income'] - item['expense']
        
        conn.close()
        return data
    except sqlite3.Error:
        return []

# ============================================================================
# GELİR/GİDER KATEGORİLERİ
# ============================================================================

def get_categories(category_type: str = None, active_only: bool = True) -> List[Dict]:
    """Kategorileri listeler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM categories WHERE 1=1"
        params = []
        
        if category_type:
            query += " AND type = ?"
            params.append(category_type)
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY sort_order, name"
        
        cursor.execute(query, params)
        categories = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return categories
    except sqlite3.Error:
        return []

def add_category(name: str, category_type: str, icon: str = "", 
                 color: str = "#6c757d", parent_id: int = None) -> Tuple[bool, str]:
    """Yeni kategori ekler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO categories (name, type, parent_id, icon, color)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, category_type, parent_id, icon, color))
        conn.commit()
        conn.close()
        return True, "Kategori eklendi!"
    except sqlite3.IntegrityError:
        return False, "Bu kategori zaten mevcut!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def update_category(category_id: int, **kwargs) -> Tuple[bool, str]:
    """Kategori günceller."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [category_id]
        cursor.execute(f"UPDATE categories SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True, "Kategori güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def delete_category(category_id: int) -> Tuple[bool, str]:
    """Kategori siler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Varsayılan kategoriler silinemez
        cursor.execute("SELECT is_default FROM categories WHERE id = ?", (category_id,))
        result = cursor.fetchone()
        if result and result['is_default']:
            conn.close()
            return False, "Varsayılan kategoriler silinemez!"
        
        # Kullanımda mı kontrol et
        cursor.execute("SELECT COUNT(*) as c FROM cash_flow WHERE category = (SELECT name FROM categories WHERE id = ?)", (category_id,))
        if cursor.fetchone()['c'] > 0:
            # Soft delete
            cursor.execute("UPDATE categories SET is_active = 0 WHERE id = ?", (category_id,))
        else:
            cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        
        conn.commit()
        conn.close()
        return True, "Kategori silindi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

# ============================================================================
# FİNANSAL ÖZET (DASHBOARD İÇİN)
# ============================================================================

def get_dashboard_stats() -> Dict:
    """Dashboard için özet istatistikler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        stats = {}
        
        # Müşteri sayıları
        cursor.execute("SELECT COUNT(*) as c FROM customers WHERE is_active = 1")
        stats['total_customers'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM customers WHERE is_active = 1 AND customer_type = 'customer'")
        stats['customer_count'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM customers WHERE is_active = 1 AND customer_type = 'supplier'")
        stats['supplier_count'] = cursor.fetchone()['c']
        
        # Kasa
        cash = get_cash_balance()
        stats['cash_balance'] = cash['balance']
        stats['today_income'] = cash['today_income']
        stats['today_expense'] = cash['today_expense']
        stats['month_income'] = cash['month_income']
        stats['month_expense'] = cash['month_expense']
        
        # Alacak/Borç
        cursor.execute("SELECT COALESCE(SUM(balance), 0) as t FROM customers WHERE balance > 0 AND is_active = 1")
        stats['total_receivables'] = cursor.fetchone()['t']
        
        cursor.execute("SELECT COALESCE(SUM(ABS(balance)), 0) as t FROM customers WHERE balance < 0 AND is_active = 1")
        stats['total_payables'] = cursor.fetchone()['t']
        
        # Çek özeti
        check_summary = get_checks_summary()
        stats['check_summary'] = check_summary
        
        # Bugünkü hatırlatıcılar
        cursor.execute('''
            SELECT COUNT(*) as c FROM reminders 
            WHERE status = 'pending' AND date(due_date) <= date('now')
        ''')
        stats['pending_reminders'] = cursor.fetchone()['c']
        
        # Bugünkü görevler
        cursor.execute('''
            SELECT COUNT(*) as c FROM notes 
            WHERE is_task = 1 AND task_status = 'pending' AND date(task_due_date) <= date('now')
        ''')
        stats['pending_tasks'] = cursor.fetchone()['c']
        
        conn.close()
        return stats
    except sqlite3.Error as e:
        print(f"❌ Dashboard stats hatası: {e}")
        return {}

def get_financial_summary(start_date: str = None, end_date: str = None) -> Dict:
    """Detaylı finansal özet."""
    try:
        if not start_date:
            start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        summary = {
            'period': {'start': start_date, 'end': end_date},
            'income': {},
            'expense': {},
            'totals': {}
        }
        
        # Gelirler - kategoriye göre
        income_by_cat = get_cash_flow_by_category(start_date, end_date, 'income')
        summary['income']['by_category'] = income_by_cat
        summary['income']['total'] = sum(item['total'] for item in income_by_cat)
        
        # Giderler - kategoriye göre
        expense_by_cat = get_cash_flow_by_category(start_date, end_date, 'expense')
        summary['expense']['by_category'] = expense_by_cat
        summary['expense']['total'] = sum(item['total'] for item in expense_by_cat)
        
        # Toplamlar
        summary['totals']['income'] = summary['income']['total']
        summary['totals']['expense'] = summary['expense']['total']
        summary['totals']['net'] = summary['income']['total'] - summary['expense']['total']
        summary['totals']['profit_margin'] = (
            (summary['totals']['net'] / summary['income']['total'] * 100) 
            if summary['income']['total'] > 0 else 0
        )
        
        # Günlük trend (grafik için)
        summary['daily_trend'] = get_cash_flow_by_date(start_date, end_date, 'day')
        
        return summary
    except Exception as e:
        print(f"❌ Financial summary hatası: {e}")
        return {}

print("=" * 70)
print("✅ BACKEND V3 - PARÇA 2/3 TAMAMLANDI!")
print("=" * 70)
print("📦 İçerik:")
print("  ✔️ Çek/Senet Yönetimi (Tam)")
print("     - Ekleme, Güncelleme, Silme")
print("     - Kısmi Tahsilat")
print("     - Ciro İşlemi")
print("     - Hareket Geçmişi")
print("     - Otomatik Hatırlatıcı")
print("  ✔️ Kasa Yönetimi")
print("     - Gelir/Gider İşlemleri")
print("     - Bakiye Takibi")
print("     - Kategori Bazlı Analiz")
print("     - Tarih Bazlı Trend")
print("  ✔️ Gelir/Gider Kategorileri")
print("  ✔️ Dashboard İstatistikleri")
print("  ✔️ Finansal Özet Raporu")
print("=" * 70)# ============================================================================
# BACKEND.PY - PARÇA 3/3: HATIRLATICI + NOT DEFTERİ + WHATSAPP + RAPORLAR
# ============================================================================

# ============================================================================
# HATIRLATICI / AJANDA YÖNETİMİ
# ============================================================================

def add_reminder(title: str, due_date: str, description: str = "",
                 reminder_type: str = "general", priority: str = "normal",
                 due_time: str = None, is_recurring: int = 0,
                 recurrence_type: str = None, recurrence_interval: int = 1,
                 recurrence_end_date: str = None, related_customer_id: int = None,
                 related_check_id: int = None, notify_before_days: int = 1,
                 notify_via_whatsapp: int = 0, created_by: int = 1) -> Tuple[bool, str, int]:
    """Yeni hatırlatıcı ekler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reminders (
                title, description, reminder_type, priority, due_date, due_time,
                is_recurring, recurrence_type, recurrence_interval, recurrence_end_date,
                related_customer_id, related_check_id, notify_before_days,
                notify_via_whatsapp, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, description, reminder_type, priority, due_date, due_time,
              is_recurring, recurrence_type, recurrence_interval, recurrence_end_date,
              related_customer_id, related_check_id, notify_before_days,
              notify_via_whatsapp, created_by))
        
        reminder_id = cursor.lastrowid
        conn.commit()
        log_activity(created_by, 'create', 'reminder', reminder_id)
        conn.close()
        return True, "Hatırlatıcı eklendi!", reminder_id
    except sqlite3.Error as e:
        return False, f"Hata: {e}", 0

def update_reminder(reminder_id: int, **kwargs) -> Tuple[bool, str]:
    """Hatırlatıcı günceller."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [reminder_id]
        
        cursor.execute(f"UPDATE reminders SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True, "Hatırlatıcı güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def delete_reminder(reminder_id: int) -> Tuple[bool, str]:
    """Hatırlatıcı siler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()
        conn.close()
        return True, "Hatırlatıcı silindi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def get_reminders(status: str = None, reminder_type: str = None,
                  priority: str = None, start_date: str = None,
                  end_date: str = None, related_customer_id: int = None,
                  include_completed: bool = False) -> List[Dict]:
    """Hatırlatıcıları listeler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT r.*, 
                   c.name as customer_name, c.phone as customer_phone,
                   ch.check_number, ch.amount as check_amount,
                   CASE 
                       WHEN r.status = 'pending' AND date(r.due_date) < date('now') THEN 'overdue'
                       WHEN r.status = 'pending' AND date(r.due_date) = date('now') THEN 'today'
                       WHEN r.status = 'pending' AND date(r.due_date) = date('now', '+1 day') THEN 'tomorrow'
                       ELSE r.status
                   END as display_status,
                   CAST(julianday(r.due_date) - julianday('now') AS INTEGER) as days_left
            FROM reminders r
            LEFT JOIN customers c ON r.related_customer_id = c.id
            LEFT JOIN checks ch ON r.related_check_id = ch.id
            WHERE 1=1
        '''
        params = []
        
        if not include_completed:
            query += " AND r.status != 'completed'"
        
        if status:
            if status == 'overdue':
                query += " AND r.status = 'pending' AND date(r.due_date) < date('now')"
            elif status == 'today':
                query += " AND r.status = 'pending' AND date(r.due_date) = date('now')"
            elif status == 'tomorrow':
                query += " AND r.status = 'pending' AND date(r.due_date) = date('now', '+1 day')"
            elif status == 'upcoming':
                query += " AND r.status = 'pending' AND date(r.due_date) > date('now')"
            else:
                query += " AND r.status = ?"
                params.append(status)
        
        if reminder_type:
            query += " AND r.reminder_type = ?"
            params.append(reminder_type)
        
        if priority:
            query += " AND r.priority = ?"
            params.append(priority)
        
        if start_date:
            query += " AND r.due_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND r.due_date <= ?"
            params.append(end_date)
        
        if related_customer_id:
            query += " AND r.related_customer_id = ?"
            params.append(related_customer_id)
        
        query += " ORDER BY r.due_date ASC, r.priority DESC, r.due_time ASC"
        
        cursor.execute(query, params)
        reminders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return reminders
    except sqlite3.Error as e:
        print(f"❌ Hatırlatıcı listeleme hatası: {e}")
        return []

def get_reminder_by_id(reminder_id: int) -> Optional[Dict]:
    """ID ile hatırlatıcı getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, c.name as customer_name, ch.check_number
            FROM reminders r
            LEFT JOIN customers c ON r.related_customer_id = c.id
            LEFT JOIN checks ch ON r.related_check_id = ch.id
            WHERE r.id = ?
        ''', (reminder_id,))
        reminder = cursor.fetchone()
        conn.close()
        return dict_from_row(reminder)
    except sqlite3.Error:
        return None

def complete_reminder(reminder_id: int, created_by: int = 1) -> Tuple[bool, str]:
    """Hatırlatıcıyı tamamlar ve tekrarlayan ise yenisini oluşturur."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Mevcut hatırlatıcıyı getir
        cursor.execute('SELECT * FROM reminders WHERE id = ?', (reminder_id,))
        reminder = cursor.fetchone()
        if not reminder:
            conn.close()
            return False, "Hatırlatıcı bulunamadı!"
        reminder = dict(reminder)
        
        # Tamamla
        cursor.execute('''
            UPDATE reminders SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE id = ?
        ''', (now, now, reminder_id))
        
        # Tekrarlayan ise yeni oluştur
        if reminder['is_recurring'] and reminder['recurrence_type']:
            old_date = datetime.strptime(reminder['due_date'], '%Y-%m-%d')
            interval = reminder['recurrence_interval'] or 1
            
            if reminder['recurrence_type'] == 'daily':
                new_date = old_date + timedelta(days=interval)
            elif reminder['recurrence_type'] == 'weekly':
                new_date = old_date + timedelta(weeks=interval)
            elif reminder['recurrence_type'] == 'monthly':
                new_date = old_date + timedelta(days=30*interval)
            elif reminder['recurrence_type'] == 'yearly':
                new_date = old_date + timedelta(days=365*interval)
            else:
                new_date = None
            
            # Bitiş tarihi kontrolü
            if new_date:
                end_date = reminder.get('recurrence_end_date')
                if end_date and new_date > datetime.strptime(end_date, '%Y-%m-%d'):
                    new_date = None
            
            if new_date:
                cursor.execute('''
                    INSERT INTO reminders (
                        title, description, reminder_type, priority, due_date, due_time,
                        is_recurring, recurrence_type, recurrence_interval, recurrence_end_date,
                        related_customer_id, related_check_id, notify_before_days,
                        notify_via_whatsapp, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (reminder['title'], reminder['description'], reminder['reminder_type'],
                      reminder['priority'], new_date.strftime('%Y-%m-%d'), reminder['due_time'],
                      1, reminder['recurrence_type'], interval, reminder['recurrence_end_date'],
                      reminder['related_customer_id'], reminder['related_check_id'],
                      reminder['notify_before_days'], reminder['notify_via_whatsapp'], created_by))
        
        conn.commit()
        log_activity(created_by, 'complete', 'reminder', reminder_id)
        conn.close()
        return True, "Hatırlatıcı tamamlandı!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def snooze_reminder(reminder_id: int, snooze_until: str) -> Tuple[bool, str]:
    """Hatırlatıcıyı erteler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE reminders SET snoozed_until = ?, updated_at = ?
            WHERE id = ?
        ''', (snooze_until, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), reminder_id))
        conn.commit()
        conn.close()
        return True, "Hatırlatıcı ertelendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def get_today_reminders() -> List[Dict]:
    """Bugünkü hatırlatıcıları getirir."""
    return get_reminders(status='today')

def get_overdue_reminders() -> List[Dict]:
    """Gecikmiş hatırlatıcıları getirir."""
    return get_reminders(status='overdue')

def get_upcoming_reminders(days: int = 7) -> List[Dict]:
    """Yaklaşan hatırlatıcıları getirir."""
    end_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    return get_reminders(status='pending', end_date=end_date)

def get_reminders_summary() -> Dict:
    """Hatırlatıcı özeti."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        summary = {}
        
        cursor.execute('''
            SELECT COUNT(*) as c FROM reminders 
            WHERE status = 'pending' AND date(due_date) < date('now')
        ''')
        summary['overdue'] = cursor.fetchone()['c']
        
        cursor.execute('''
            SELECT COUNT(*) as c FROM reminders 
            WHERE status = 'pending' AND date(due_date) = date('now')
        ''')
        summary['today'] = cursor.fetchone()['c']
        
        cursor.execute('''
            SELECT COUNT(*) as c FROM reminders 
            WHERE status = 'pending' AND date(due_date) = date('now', '+1 day')
        ''')
        summary['tomorrow'] = cursor.fetchone()['c']
        
        cursor.execute('''
            SELECT COUNT(*) as c FROM reminders 
            WHERE status = 'pending' AND date(due_date) > date('now') 
            AND date(due_date) <= date('now', '+7 days')
        ''')
        summary['this_week'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM reminders WHERE status = 'pending'")
        summary['total_pending'] = cursor.fetchone()['c']
        
        conn.close()
        return summary
    except sqlite3.Error:
        return {}

# ============================================================================
# NOT DEFTERİ / GÖREV LİSTESİ YÖNETİMİ
# ============================================================================

def add_note(title: str, content: str = "", note_type: str = "note",
             category: str = "", color: str = "#ffffff", is_pinned: int = 0,
             is_task: int = 0, task_priority: str = "normal",
             task_due_date: str = None, related_customer_id: int = None,
             tags: List[str] = None, created_by: int = 1) -> Tuple[bool, str, int]:
    """Yeni not veya görev ekler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        tags_json = json.dumps(tags) if tags else None
        
        cursor.execute('''
            INSERT INTO notes (
                title, content, note_type, category, color, is_pinned,
                is_task, task_priority, task_due_date, related_customer_id,
                tags, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, content, note_type, category, color, is_pinned,
              is_task, task_priority, task_due_date, related_customer_id,
              tags_json, created_by))
        
        note_id = cursor.lastrowid
        conn.commit()
        log_activity(created_by, 'create', 'note', note_id)
        conn.close()
        return True, "Not eklendi!", note_id
    except sqlite3.Error as e:
        return False, f"Hata: {e}", 0

def update_note(note_id: int, **kwargs) -> Tuple[bool, str]:
    """Not/görev günceller."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if 'tags' in kwargs and isinstance(kwargs['tags'], list):
            kwargs['tags'] = json.dumps(kwargs['tags'])
        
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [note_id]
        
        cursor.execute(f"UPDATE notes SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True, "Not güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def delete_note(note_id: int) -> Tuple[bool, str]:
    """Not siler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        conn.close()
        return True, "Not silindi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def get_notes(note_type: str = None, is_task: int = None, task_status: str = None,
              category: str = None, is_pinned: int = None, is_archived: int = 0,
              related_customer_id: int = None, search: str = None,
              order_by: str = 'is_pinned DESC, created_at DESC') -> List[Dict]:
    """Notları/görevleri listeler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT n.*, c.name as customer_name,
                   CASE 
                       WHEN n.is_task = 1 AND n.task_status = 'pending' AND date(n.task_due_date) < date('now') THEN 'overdue'
                       WHEN n.is_task = 1 AND n.task_status = 'pending' AND date(n.task_due_date) = date('now') THEN 'due_today'
                       ELSE n.task_status
                   END as display_status
            FROM notes n
            LEFT JOIN customers c ON n.related_customer_id = c.id
            WHERE n.is_archived = ?
        '''
        params = [is_archived]
        
        if note_type:
            query += " AND n.note_type = ?"
            params.append(note_type)
        
        if is_task is not None:
            query += " AND n.is_task = ?"
            params.append(is_task)
        
        if task_status:
            if task_status == 'overdue':
                query += " AND n.is_task = 1 AND n.task_status = 'pending' AND date(n.task_due_date) < date('now')"
            elif task_status == 'due_today':
                query += " AND n.is_task = 1 AND n.task_status = 'pending' AND date(n.task_due_date) = date('now')"
            else:
                query += " AND n.task_status = ?"
                params.append(task_status)
        
        if category:
            query += " AND n.category = ?"
            params.append(category)
        
        if is_pinned is not None:
            query += " AND n.is_pinned = ?"
            params.append(is_pinned)
        
        if related_customer_id:
            query += " AND n.related_customer_id = ?"
            params.append(related_customer_id)
        
        if search:
            query += " AND (n.title LIKE ? OR n.content LIKE ? OR n.tags LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        query += f" ORDER BY {order_by}"
        
        cursor.execute(query, params)
        notes = [dict(row) for row in cursor.fetchall()]
        
        # Tags JSON'dan listeye çevir
        for note in notes:
            if note.get('tags'):
                try:
                    note['tags'] = json.loads(note['tags'])
                except:
                    note['tags'] = []
        
        conn.close()
        return notes
    except sqlite3.Error as e:
        print(f"❌ Not listeleme hatası: {e}")
        return []

def get_note_by_id(note_id: int) -> Optional[Dict]:
    """ID ile not getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT n.*, c.name as customer_name
            FROM notes n
            LEFT JOIN customers c ON n.related_customer_id = c.id
            WHERE n.id = ?
        ''', (note_id,))
        note = cursor.fetchone()
        conn.close()
        
        if note:
            note = dict(note)
            if note.get('tags'):
                try:
                    note['tags'] = json.loads(note['tags'])
                except:
                    note['tags'] = []
        
        return note
    except sqlite3.Error:
        return None

def complete_task(note_id: int) -> Tuple[bool, str]:
    """Görevi tamamlar."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            UPDATE notes SET task_status = 'completed', task_completed_at = ?, updated_at = ?
            WHERE id = ? AND is_task = 1
        ''', (now, now, note_id))
        conn.commit()
        conn.close()
        return True, "Görev tamamlandı!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def toggle_pin_note(note_id: int) -> Tuple[bool, str]:
    """Not sabitleme durumunu değiştirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE notes SET is_pinned = CASE WHEN is_pinned = 1 THEN 0 ELSE 1 END, updated_at = ?
            WHERE id = ?
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), note_id))
        conn.commit()
        conn.close()
        return True, "Not güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def archive_note(note_id: int, archive: bool = True) -> Tuple[bool, str]:
    """Notu arşivler/arşivden çıkarır."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE notes SET is_archived = ?, updated_at = ? WHERE id = ?
        ''', (1 if archive else 0, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), note_id))
        conn.commit()
        conn.close()
        return True, "Arşivlendi!" if archive else "Arşivden çıkarıldı!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def get_tasks_summary() -> Dict:
    """Görev özeti."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        summary = {}
        
        cursor.execute('''
            SELECT COUNT(*) as c FROM notes 
            WHERE is_task = 1 AND task_status = 'pending' AND date(task_due_date) < date('now')
        ''')
        summary['overdue'] = cursor.fetchone()['c']
        
        cursor.execute('''
            SELECT COUNT(*) as c FROM notes 
            WHERE is_task = 1 AND task_status = 'pending' AND date(task_due_date) = date('now')
        ''')
        summary['due_today'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM notes WHERE is_task = 1 AND task_status = 'pending'")
        summary['pending'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM notes WHERE is_task = 1 AND task_status = 'completed'")
        summary['completed'] = cursor.fetchone()['c']
        
        conn.close()
        return summary
    except sqlite3.Error:
        return {}

# ============================================================================
# WHATSAPP ENTEGRASYONU
# ============================================================================

def get_whatsapp_settings() -> Dict:
    """WhatsApp ayarlarını getirir."""
    return get_settings_by_category('whatsapp')

def is_whatsapp_enabled() -> bool:
    """WhatsApp aktif mi kontrol eder."""
    return get_setting('whatsapp', 'enabled', False)

def format_phone_for_whatsapp(phone: str) -> str:
    """Telefon numarasını WhatsApp formatına çevirir."""
    if not phone:
        return ""
    
    # Boşlukları ve özel karakterleri temizle
    phone = ''.join(filter(str.isdigit, phone))
    
    # Türkiye için düzenleme
    if phone.startswith('0'):
        phone = '90' + phone[1:]
    elif not phone.startswith('90') and len(phone) == 10:
        phone = '90' + phone
    
    return phone

def generate_whatsapp_link(phone: str, message: str) -> str:
    """WhatsApp Web linki oluşturur."""
    formatted_phone = format_phone_for_whatsapp(phone)
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{formatted_phone}?text={encoded_message}"

def generate_whatsapp_message(template_type: str, variables: Dict) -> str:
    """Şablondan mesaj oluşturur."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT content FROM whatsapp_templates 
            WHERE template_type = ? AND is_active = 1
        ''', (template_type,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return ""
        
        message = result['content']
        
        # Değişkenleri yerleştir
        for key, value in variables.items():
            message = message.replace(f"{{{key}}}", str(value))
        
        return message
    except sqlite3.Error:
        return ""

def get_whatsapp_templates(active_only: bool = True) -> List[Dict]:
    """WhatsApp şablonlarını listeler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM whatsapp_templates"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY template_type, name"
        cursor.execute(query)
        templates = [dict(row) for row in cursor.fetchall()]
        
        for template in templates:
            if template.get('variables'):
                try:
                    template['variables'] = json.loads(template['variables'])
                except:
                    template['variables'] = []
        
        conn.close()
        return templates
    except sqlite3.Error:
        return []

def add_whatsapp_template(name: str, template_type: str, content: str,
                          variables: List[str] = None) -> Tuple[bool, str]:
    """Yeni WhatsApp şablonu ekler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        vars_json = json.dumps(variables) if variables else None
        cursor.execute('''
            INSERT INTO whatsapp_templates (name, template_type, content, variables)
            VALUES (?, ?, ?, ?)
        ''', (name, template_type, content, vars_json))
        conn.commit()
        conn.close()
        return True, "Şablon eklendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def update_whatsapp_template(template_id: int, **kwargs) -> Tuple[bool, str]:
    """WhatsApp şablonu günceller."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if 'variables' in kwargs and isinstance(kwargs['variables'], list):
            kwargs['variables'] = json.dumps(kwargs['variables'])
        
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [template_id]
        cursor.execute(f"UPDATE whatsapp_templates SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True, "Şablon güncellendi!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def log_whatsapp_message(customer_id: int, phone_number: str, message_content: str,
                         message_type: str = "manual", message_template: str = None,
                         related_type: str = None, related_id: int = None,
                         status: str = "sent", created_by: int = 1) -> Tuple[bool, str]:
    """WhatsApp mesaj loglar."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO whatsapp_messages (
                customer_id, phone_number, message_type, message_template,
                message_content, related_type, related_id, status, sent_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_id, phone_number, message_type, message_template,
              message_content, related_type, related_id, status,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'), created_by))
        conn.commit()
        conn.close()
        return True, "Mesaj loglandı!"
    except sqlite3.Error as e:
        return False, f"Hata: {e}"

def get_whatsapp_messages(customer_id: int = None, start_date: str = None,
                          end_date: str = None, limit: int = 100) -> List[Dict]:
    """WhatsApp mesaj geçmişini getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT wm.*, c.name as customer_name, u.full_name as sent_by_name
            FROM whatsapp_messages wm
            LEFT JOIN customers c ON wm.customer_id = c.id
            LEFT JOIN users u ON wm.created_by = u.id
            WHERE 1=1
        '''
        params = []
        
        if customer_id:
            query += " AND wm.customer_id = ?"
            params.append(customer_id)
        if start_date:
            query += " AND date(wm.created_at) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date(wm.created_at) <= ?"
            params.append(end_date)
        
        query += f" ORDER BY wm.created_at DESC LIMIT {limit}"
        
        cursor.execute(query, params)
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return messages
    except sqlite3.Error:
        return []

def prepare_check_reminder_message(check_id: int) -> Dict:
    """Çek hatırlatma mesajı hazırlar."""
    check = get_check_by_id(check_id)
    if not check:
        return {}
    
    company_name = get_setting('company', 'name', 'Firmamız')
    
    variables = {
        'customer_name': check.get('customer_name', 'Sayın Müşterimiz'),
        'check_number': check['check_number'],
        'amount': f"{check['amount']:,.2f}",
        'due_date': check['due_date'],
        'bank_name': check.get('bank_name', ''),
        'company_name': company_name
    }
    
    message = generate_whatsapp_message('check_reminder', variables)
    phone = check.get('customer_phone', '')
    
    return {
        'phone': phone,
        'message': message,
        'whatsapp_link': generate_whatsapp_link(phone, message) if phone else '',
        'customer_id': check.get('customer_id'),
        'check_id': check_id
    }

def prepare_payment_reminder_message(customer_id: int) -> Dict:
    """Ödeme hatırlatma mesajı hazırlar."""
    customer = get_customer_by_id(customer_id)
    if not customer:
        return {}
    
    company_name = get_setting('company', 'name', 'Firmamız')
    
    variables = {
        'customer_name': customer['name'],
        'amount': f"{abs(customer['balance']):,.2f}",
        'due_date': datetime.now().strftime('%d/%m/%Y'),
        'company_name': company_name
    }
    
    message = generate_whatsapp_message('payment_reminder', variables)
    phone = customer.get('whatsapp_phone') or customer.get('phone', '')
    
    return {
        'phone': phone,
        'message': message,
        'whatsapp_link': generate_whatsapp_link(phone, message) if phone else '',
        'customer_id': customer_id
    }

# ============================================================================
# RAPORLAR VE EXPORT
# ============================================================================

def get_report_customer_balances(balance_type: str = None, 
                                  min_balance: float = None,
                                  order_by: str = 'balance DESC') -> List[Dict]:
    """Müşteri bakiye raporu."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT id, name, customer_type, phone, email, balance,
                   CASE 
                       WHEN balance > 0 THEN 'receivable'
                       WHEN balance < 0 THEN 'payable'
                       ELSE 'zero'
                   END as balance_type
            FROM customers WHERE is_active = 1
        '''
        params = []
        
        if balance_type == 'receivable':
            query += " AND balance > 0"
        elif balance_type == 'payable':
            query += " AND balance < 0"
        elif balance_type == 'non_zero':
            query += " AND balance != 0"
        
        if min_balance:
            query += " AND ABS(balance) >= ?"
            params.append(min_balance)
        
        query += f" ORDER BY {order_by}"
        
        cursor.execute(query, params)
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return data
    except sqlite3.Error:
        return []

def get_report_checks(start_date: str = None, end_date: str = None,
                      check_type: str = None, status: str = None,
                      customer_id: int = None) -> Dict:
    """Çek/Senet raporu."""
    try:
        checks = get_all_checks(check_type=check_type, status=status,
                               customer_id=customer_id, start_date=start_date,
                               end_date=end_date)
        
        # Özet hesapla
        summary = {
            'total_count': len(checks),
            'total_amount': sum(c['amount'] for c in checks),
            'total_paid': sum(c['paid_amount'] for c in checks),
            'total_remaining': sum(c['remaining_amount'] for c in checks),
            'by_status': {},
            'by_type': {}
        }
        
        for check in checks:
            # Status bazlı
            status = check['status']
            if status not in summary['by_status']:
                summary['by_status'][status] = {'count': 0, 'amount': 0}
            summary['by_status'][status]['count'] += 1
            summary['by_status'][status]['amount'] += check['amount']
            
            # Type bazlı
            ctype = check['check_type']
            if ctype not in summary['by_type']:
                summary['by_type'][ctype] = {'count': 0, 'amount': 0}
            summary['by_type'][ctype]['count'] += 1
            summary['by_type'][ctype]['amount'] += check['amount']
        
        return {'data': checks, 'summary': summary}
    except Exception:
        return {'data': [], 'summary': {}}

def get_report_cash_flow(start_date: str = None, end_date: str = None,
                          group_by: str = 'category') -> Dict:
    """Gelir/Gider raporu."""
    try:
        transactions = get_cash_flow(start_date=start_date, end_date=end_date)
        by_category = get_cash_flow_by_category(start_date, end_date)
        by_date = get_cash_flow_by_date(start_date, end_date, 'day')
        
        total_income = sum(t['amount'] for t in transactions if t['transaction_type'] == 'income')
        total_expense = sum(t['amount'] for t in transactions if t['transaction_type'] == 'expense')
        
        return {
            'data': transactions,
            'by_category': by_category,
            'by_date': by_date,
            'summary': {
                'total_income': total_income,
                'total_expense': total_expense,
                'net': total_income - total_expense,
                'transaction_count': len(transactions)
            }
        }
    except Exception:
        return {'data': [], 'by_category': [], 'by_date': [], 'summary': {}}

def get_report_customer_statement(customer_id: int, start_date: str = None,
                                   end_date: str = None) -> Dict:
    """Müşteri hesap ekstresi raporu."""
    return get_customer_statement(customer_id, start_date, end_date)

def get_report_aging(as_of_date: str = None) -> Dict:
    """Yaşlandırma raporu (Alacak/Borç vadelerine göre)."""
    try:
        if not as_of_date:
            as_of_date = datetime.now().strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Çek bazlı yaşlandırma
        aging_ranges = [
            ('current', 0, 0),
            ('1_30', 1, 30),
            ('31_60', 31, 60),
            ('61_90', 61, 90),
            ('over_90', 91, 9999)
        ]
        
        result = {'incoming': {}, 'outgoing': {}}
        
        for check_type in ['incoming', 'outgoing']:
            for range_name, min_days, max_days in aging_ranges:
                if range_name == 'current':
                    cursor.execute('''
                        SELECT COALESCE(SUM(amount - paid_amount), 0) as total, COUNT(*) as count
                        FROM checks 
                        WHERE check_type = ? AND status = 'pending' AND date(due_date) >= date(?)
                    ''', (check_type, as_of_date))
                else:
                    cursor.execute('''
                        SELECT COALESCE(SUM(amount - paid_amount), 0) as total, COUNT(*) as count
                        FROM checks 
                        WHERE check_type = ? AND status = 'pending' 
                        AND julianday(?) - julianday(due_date) BETWEEN ? AND ?
                    ''', (check_type, as_of_date, min_days, max_days))
                
                row = cursor.fetchone()
                result[check_type][range_name] = {
                    'amount': row['total'],
                    'count': row['count']
                }
        
        conn.close()
        return result
    except sqlite3.Error:
        return {}

# ============================================================================
# EXPORT FONKSİYONLARI
# ============================================================================

def export_to_csv(data: List[Dict], columns: List[str] = None) -> str:
    """Veriyi CSV formatına çevirir."""
    if not data:
        return ""
    
    output = io.StringIO()
    
    if columns:
        fieldnames = columns
    else:
        fieldnames = list(data[0].keys())
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue()

def export_customers_csv(balance_type: str = None) -> str:
    """Müşteri listesini CSV olarak export eder."""
    data = get_report_customer_balances(balance_type)
    columns = ['id', 'name', 'customer_type', 'phone', 'email', 'balance', 'balance_type']
    return export_to_csv(data, columns)

def export_checks_csv(start_date: str = None, end_date: str = None,
                       check_type: str = None, status: str = None) -> str:
    """Çek listesini CSV olarak export eder."""
    report = get_report_checks(start_date, end_date, check_type, status)
    columns = ['id', 'check_type', 'payment_type', 'check_number', 'customer_name',
               'bank_name', 'amount', 'paid_amount', 'remaining_amount', 'due_date', 'status']
    return export_to_csv(report['data'], columns)

def export_cash_flow_csv(start_date: str = None, end_date: str = None) -> str:
    """Kasa hareketlerini CSV olarak export eder."""
    transactions = get_cash_flow(start_date=start_date, end_date=end_date)
    columns = ['id', 'transaction_date', 'transaction_type', 'category', 'amount',
               'description', 'customer_name', 'payment_method']
    return export_to_csv(transactions, columns)

def export_customer_statement_csv(customer_id: int, start_date: str = None,
                                   end_date: str = None) -> str:
    """Müşteri ekstresini CSV olarak export eder."""
    statement = get_customer_statement(customer_id, start_date, end_date)
    if not statement or 'transactions' not in statement:
        return ""
    columns = ['id', 'transaction_date', 'transaction_type', 'amount', 
               'balance_after', 'description', 'reference_type']
    return export_to_csv(statement['transactions'], columns)

# ============================================================================
# YEDEKLEME
# ============================================================================

def backup_database(backup_path: str = None) -> Tuple[bool, str]:
    """Veritabanını yedekler."""
    try:
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"backup_{DB_NAME}_{timestamp}"
        
        conn = get_db_connection()
        backup_conn = sqlite3.connect(backup_path)
        conn.backup(backup_conn)
        backup_conn.close()
        conn.close()
        
        return True, f"Yedek oluşturuldu: {backup_path}"
    except Exception as e:
        return False, f"Yedekleme hatası: {e}"

def restore_database(backup_path: str) -> Tuple[bool, str]:
    """Veritabanını geri yükler."""
    try:
        if not os.path.exists(backup_path):
            return False, "Yedek dosyası bulunamadı!"
        
        backup_conn = sqlite3.connect(backup_path)
        conn = get_db_connection()
        backup_conn.backup(conn)
        conn.close()
        backup_conn.close()
        
        return True, "Veritabanı geri yüklendi!"
    except Exception as e:
        return False, f"Geri yükleme hatası: {e}"

# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("BACKEND V3 - TAM TEST")
    print("=" * 70)
    
    # Veritabanını başlat
    init_db()
    
    # Login test
    user = login_user("admin", "admin123")
    if user:
        print(f"✅ Login başarılı: {user['full_name']}")
    
    # Dashboard stats
    stats = get_dashboard_stats()
    print(f"📊 Dashboard: {stats}")
    
    # Ayarlar test
    company_name = get_setting('company', 'name')
    print(f"🏢 Firma: {company_name}")
    
    # WhatsApp test
    wa_enabled = is_whatsapp_enabled()
    print(f"📱 WhatsApp: {'Aktif' if wa_enabled else 'Pasif'}")
    
    # Hatırlatıcı özeti
    reminder_summary = get_reminders_summary()
    print(f"🔔 Hatırlatıcılar: {reminder_summary}")
    
    # Görev özeti
    task_summary = get_tasks_summary()
    print(f"📝 Görevler: {task_summary}")
    
    print("=" * 70)
    print("✅ Tüm testler tamamlandı!")
    print("=" * 70)