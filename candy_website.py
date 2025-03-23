#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import logging
import json
import os
import time
import socket
import requests
from datetime import datetime
import webbrowser
from functools import wraps
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/website.log"),
        logging.StreamHandler()
    ]
)

# Создаем специальный логгер для посетителей
visitor_logger = logging.getLogger('visitors')
visitor_logger.setLevel(logging.INFO)
visitor_handler = logging.FileHandler("logs/visitors.log")
visitor_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
visitor_logger.addHandler(visitor_handler)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')  # Замените на свой секретный ключ

# Хранение информации о посетителях
visitors = {}

# Функция для проверки аутентификации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def get_host_info(ip_address):
    """Получить информацию о хосте по IP-адресу"""
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except:
        return "Неизвестно"

def get_geolocation(ip_address):
    """Получить геолокацию по IP-адресу"""
    if ip_address == "127.0.0.1" or ip_address.startswith("192.168.") or ip_address.startswith("10."):
        # Локальный IP-адрес
        return {
            "country": "Local Network",
            "region": "Local Network",
            "city": "Local Network",
            "loc": "0,0",
            "maps_url": "https://www.google.com/maps/place/Your+Location",
            "is_local": True
        }
    
    try:
        # Используем бесплатный API ipinfo.io для определения геолокации
        response = requests.get(f"https://ipinfo.io/{ip_address}/json")
        if response.status_code == 200:
            data = response.json()
            # Создаем ссылку на Google Maps
            location = data.get("loc", "0,0")
            maps_url = f"https://www.google.com/maps/place/{location}"
            data["maps_url"] = maps_url
            data["is_local"] = False
            return data
    except Exception as e:
        logging.error(f"Error getting geolocation: {e}")
    
    # В случае ошибки возвращаем дефолтные значения
    return {
        "country": "Unknown",
        "region": "Unknown",
        "city": "Unknown",
        "loc": "0,0",
        "maps_url": "https://www.google.com/maps",
        "is_local": False
    }

@app.route('/')
def index():
    """Главная страница сайта про конфеты"""
    return render_template('index.html')

@app.route('/about')
def about():
    """Страница 'О нас'"""
    return render_template('about.html')

@app.route('/products')
def products():
    """Страница с продуктами"""
    return render_template('products.html')

@app.route('/contact')
def contact():
    """Страница контактов"""
    return render_template('contact.html')

@app.route('/api/visitor-info', methods=['POST'])
def visitor_info():
    """Получение информации о посетителе от JavaScript"""
    client_data = request.json
    
    # Получаем IP-адрес посетителя
    ip_address = request.remote_addr
    if request.headers.get('X-Forwarded-For'):
        ip_address = request.headers.get('X-Forwarded-For').split(',')[0]
    
    # Получаем дополнительную информацию
    hostname = get_host_info(ip_address)
    geo_info = get_geolocation(ip_address)
    location_str = f"{geo_info.get('city', 'Unknown')}, {geo_info.get('region', 'Unknown')}, {geo_info.get('country', 'Unknown')}"
    maps_url = geo_info.get('maps_url', 'https://www.google.com/maps')
    
    # Собираем всю информацию о посетителе
    visitor_id = f"{ip_address}_{int(time.time())}"
    visitor_data = {
        "id": visitor_id,
        "ip": ip_address,
        "visit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_agent": request.headers.get('User-Agent', 'Unknown'),
        "browser": client_data.get('browser', 'Unknown'),
        "os": client_data.get('os', 'Unknown'),
        "device": client_data.get('device', 'Unknown'),
        "screen_resolution": client_data.get('screen', 'Unknown'),
        "language": client_data.get('language', 'Unknown'),
        "referrer": client_data.get('referrer', 'Unknown'),
        "hostname": hostname,
        "location": location_str,
        "maps_url": maps_url,
        "cookies_enabled": client_data.get('cookiesEnabled', False),
        "javascript_enabled": True,  # если этот запрос дошел, значит JS включен
        "battery_level": client_data.get('batteryLevel', 'Unknown'),
        "is_charging": client_data.get('isCharging', 'Unknown'),
        "connection_type": client_data.get('connectionType', 'Unknown'),
        "time_zone": client_data.get('timeZone', 'Unknown'),
        "time_zone_offset": client_data.get('timeZoneOffset', 'Unknown'),
        "plugins": client_data.get('plugins', []),
        "webgl_data": client_data.get('webglData', 'Unknown'),
        "canvas_fingerprint": client_data.get('canvasFingerprint', 'Unknown'),
        "do_not_track": client_data.get('doNotTrack', 'Unknown'),
        "adblock_enabled": client_data.get('adblockEnabled', 'Unknown')
    }
    
    # Сохраняем информацию
    visitors[visitor_id] = visitor_data
    
    # Логирование
    info_message = f"Новый посетитель: {ip_address} из {location_str}"
    details = f"Браузер: {visitor_data['browser']}, ОС: {visitor_data['os']}, Устройство: {visitor_data['device']}"
    maps_info = f"Карта: {maps_url}"
    
    print("\n" + "="*50)
    print(info_message)
    print(details)
    print(maps_info)
    print("="*50)
    
    visitor_logger.info(info_message)
    visitor_logger.info(details)
    visitor_logger.info(maps_info)
    visitor_logger.info(f"Полная информация: {json.dumps(visitor_data, indent=2, ensure_ascii=False)}")
    
    # Отправляем OK клиенту
    return jsonify({"status": "success"})

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Страница входа в админ-панель"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Проверяем учетные данные (замените на свои)
        if username == os.getenv('ADMIN_USERNAME', 'admin') and password == os.getenv('ADMIN_PASSWORD', 'admin123'):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_visitors'))
        else:
            return render_template('admin_login.html', error='Неверные учетные данные')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Выход из админ-панели"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/visitors', methods=['GET'])
@login_required
def admin_visitors():
    """Страница просмотра посетителей"""
    return render_template('admin_visitors.html', visitors=visitors)

@app.route('/admin/visitor/<visitor_id>', methods=['GET'])
@login_required
def admin_visitor_detail(visitor_id):
    """Детальная информация о посетителе"""
    visitor = visitors.get(visitor_id)
    if not visitor:
        return "Посетитель не найден", 404
    
    return render_template('visitor_details.html', visitor=visitor, visitor_id=visitor_id)

@app.route('/admin/open-map/<visitor_id>', methods=['GET'])
@login_required
def admin_open_map(visitor_id):
    """Открыть карту местоположения посетителя"""
    visitor = visitors.get(visitor_id)
    if not visitor:
        return "Посетитель не найден", 404
    
    maps_url = visitor.get('maps_url', 'https://www.google.com/maps')
    webbrowser.open(maps_url)
    
    return "Карта открыта в браузере", 200

if __name__ == '__main__':
    # Инициализация
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static/css'):
        os.makedirs('static/css')
    if not os.path.exists('static/js'):
        os.makedirs('static/js')
    if not os.path.exists('static/images'):
        os.makedirs('static/images')
    
    host = '0.0.0.0'  # Слушаем на всех интерфейсах
    port = 5000
    
    print("\n" + "="*50)
    print(f"Запуск сайта про конфеты на http://{host}:{port}")
    print(f"Админка доступна на http://localhost:{port}/admin/login")
    print("="*50 + "\n")
    
    # Проверяем наличие модуля requests
    try:
        import requests
    except ImportError:
        print("\nВНИМАНИЕ: Модуль 'requests' не установлен.")
        print("Установите его командой: pip install requests")
        print("Определение геолокации будет отключено.\n")
    
    # Проверяем наличие модуля Flask
    try:
        import flask
    except ImportError:
        print("\nВНИМАНИЕ: Модуль 'flask' не установлен.")
        print("Установите его командой: pip install flask")
        print("Запуск сервера невозможен.\n")
        exit(1)
    
    # Запуск сервера
    app.run(host=host, port=port, debug=True) 