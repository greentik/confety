#!/usr/bin/env python3
import socket
import json
import sys
import time
import argparse
import webbrowser

class DeviceClient:
    def __init__(self, host, port, username=None, password=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.socket = None
        self.connected = False
    
    def connect(self):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"Connected to server at {self.host}:{self.port}")
            
            # Handle authentication if needed
            data = self.socket.recv(1024).decode()
            try:
                auth_request = json.loads(data)
                if auth_request.get("type") == "auth_required":
                    if not self.username or not self.password:
                        self.username = input("Username: ")
                        self.password = input("Password: ")
                    
                    # Send credentials
                    auth_data = {
                        "username": self.username,
                        "password": self.password
                    }
                    self.socket.send(json.dumps(auth_data).encode())
                    
                    # Get authentication response
                    auth_response = json.loads(self.socket.recv(1024).decode())
                    if auth_response.get("type") == "auth_success":
                        print("Authentication successful")
                    else:
                        print("Authentication failed")
                        self.disconnect()
                        return False
            except json.JSONDecodeError:
                # Server might not require authentication
                pass
                
            return True
            
        except Exception as e:
            print(f"Error connecting to server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        if self.connected:
            try:
                # Send exit command
                self.send_command("exit")
                self.socket.close()
            except:
                pass
            finally:
                self.connected = False
                print("Disconnected from server")
    
    def send_command(self, command):
        """Send a command to the server"""
        if not self.connected:
            print("Not connected to server")
            return None
            
        try:
            # Send command as JSON
            cmd_data = {
                "type": "cmd",
                "command": command
            }
            self.socket.send(json.dumps(cmd_data).encode())
            
            # Get response
            response = self.socket.recv(4096).decode()
            try:
                # Try to parse as JSON
                json_response = json.loads(response)
                if json_response.get("type") == "cmd_response":
                    if json_response.get("status") == "success":
                        return json_response.get("output")
                    else:
                        print(f"Error: {json_response.get('error')}")
                        return None
                return json_response
            except json.JSONDecodeError:
                # Return raw response if not JSON
                return response
                
        except Exception as e:
            print(f"Error sending command: {e}")
            return None
    
    def get_system_info(self):
        """Get system information from the server"""
        if not self.connected:
            print("Not connected to server")
            return None
            
        try:
            # Request system info
            self.socket.send(json.dumps({"type": "system_info"}).encode())
            
            # Get response
            response = self.socket.recv(4096).decode()
            return json.loads(response)
            
        except Exception as e:
            print(f"Error getting system info: {e}")
            return None
    
    def get_active_connections(self):
        """Get information about active connections"""
        if not self.connected:
            print("Not connected to server")
            return None
            
        try:
            # Request active connections
            self.socket.send(json.dumps({"type": "active_connections"}).encode())
            
            # Get response
            response = self.socket.recv(4096).decode()
            return json.loads(response)
            
        except Exception as e:
            print(f"Error getting active connections: {e}")
            return None
    
    def ping(self):
        """Ping the server to check connection"""
        if not self.connected:
            print("Not connected to server")
            return False
            
        try:
            start_time = time.time()
            self.socket.send(json.dumps({"type": "ping"}).encode())
            response = json.loads(self.socket.recv(1024).decode())
            end_time = time.time()
            
            if response.get("type") == "pong":
                print(f"Ping successful: {(end_time - start_time) * 1000:.2f}ms")
                return True
            return False
            
        except Exception as e:
            print(f"Ping failed: {e}")
            return False
    
    def open_maps_url(self, url):
        """Открыть ссылку на карту в браузере"""
        try:
            print(f"Открываю карту в браузере: {url}")
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"Ошибка при открытии ссылки: {e}")
            return False
    
    def interactive_mode(self):
        """Enter interactive command mode"""
        if not self.connected:
            if not self.connect():
                return
                
        print("\n=== Device Control Client ===")
        print("Type 'exit' to quit, 'help' for commands")
        
        while self.connected:
            try:
                command = input("\n> ")
                
                if command.lower() == "exit":
                    self.disconnect()
                    break
                    
                elif command.lower() == "help":
                    print("Available commands:")
                    print("  exit             - Exit the client")
                    print("  help             - Show this help")
                    print("  ping             - Ping the server")
                    print("  sysinfo          - Get system information")
                    print("  connections      - Show active connections")
                    print("  map <ip or num>  - Open location map for IP or connection number")
                    print("  <shell command>  - Execute shell command on server")
                    
                elif command.lower() == "ping":
                    self.ping()
                    
                elif command.lower() == "sysinfo":
                    info = self.get_system_info()
                    if info:
                        print("\nSystem Information:")
                        for key, value in info.items():
                            if key != "type":
                                print(f"  {key}: {value}")
                
                elif command.lower() == "connections":
                    connections = self.get_active_connections()
                    if connections and connections.get("type") == "active_connections_response":
                        conn_data = connections.get("connections", {})
                        if conn_data:
                            print("\nActive connections:")
                            print("-" * 100)
                            print(f"{'#':<3} {'IP':<15} {'Port':<6} {'Username':<15} {'Location':<30} {'Connected At':<20}")
                            print("-" * 100)
                            
                            # Преобразуем словарь в список для нумерации
                            connections_list = []
                            for addr_str, data in conn_data.items():
                                # Преобразуем строковый ключ обратно в кортеж (ip, port)
                                addr_parts = addr_str.strip("()").split(", ")
                                if len(addr_parts) == 2:
                                    try:
                                        ip = addr_parts[0].strip("'")
                                        port = int(addr_parts[1])
                                        data["ip"] = ip
                                        data["port"] = port
                                        connections_list.append(data)
                                    except:
                                        connections_list.append(data)
                            
                            # Выводим пронумерованный список
                            for i, data in enumerate(connections_list, 1):
                                ip = data.get("ip", "Unknown")
                                port = data.get("port", "")
                                username = data.get("username", "Unknown")
                                location = data.get("location", "Unknown")
                                connected_at = data.get("connected_at", "")
                                maps_url = data.get("maps_url", "")
                                
                                # Сохраняем индекс для команды map
                                data["index"] = i
                                
                                print(f"{i:<3} {ip:<15} {str(port):<6} {username:<15} {location:<30} {connected_at:<20}")
                                if maps_url:
                                    print(f"    Карта: {maps_url}")
                            
                            # Сохраняем список для использования с командой map
                            self.last_connections = connections_list
                            
                        else:
                            print("No active connections")
                    else:
                        print("Failed to get active connections")
                
                elif command.lower().startswith("map "):
                    # Извлекаем аргумент - IP или номер подключения
                    arg = command.split(" ", 1)[1].strip()
                    
                    if hasattr(self, 'last_connections'):
                        if arg.isdigit():
                            # Ищем по номеру подключения
                            index = int(arg)
                            if 1 <= index <= len(self.last_connections):
                                conn = self.last_connections[index-1]
                                maps_url = conn.get("maps_url")
                                if maps_url:
                                    self.open_maps_url(maps_url)
                                else:
                                    print(f"Нет данных о местоположении для подключения #{index}")
                            else:
                                print(f"Подключение с номером {index} не найдено")
                        else:
                            # Ищем по IP
                            found = False
                            for conn in self.last_connections:
                                if conn.get("ip") == arg:
                                    maps_url = conn.get("maps_url")
                                    if maps_url:
                                        self.open_maps_url(maps_url)
                                        found = True
                                        break
                            
                            if not found:
                                print(f"Подключение с IP {arg} не найдено")
                    else:
                        print("Сначала выполните команду 'connections' для получения списка подключений")
                                
                elif command.strip():
                    # Execute shell command
                    result = self.send_command(command)
                    if result:
                        print(result)
                        
            except KeyboardInterrupt:
                print("\nExiting...")
                self.disconnect()
                break
                
            except Exception as e:
                print(f"Error: {e}")
                if not self.connected:
                    print("Connection lost. Reconnecting...")
                    if not self.connect():
                        break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Device Control Client")
    parser.add_argument("--host", default="localhost", help="Server host address (default: localhost)")
    parser.add_argument("--port", type=int, default=4444, help="Server port (default: 4444)")
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")
    parser.add_argument("--cmd", help="Execute a single command and exit")
    args = parser.parse_args()
    
    client = DeviceClient(args.host, args.port, args.username, args.password)
    
    if args.cmd:
        # Execute single command mode
        if client.connect():
            result = client.send_command(args.cmd)
            if result:
                print(result)
            client.disconnect()
    else:
        # Interactive mode
        client.interactive_mode() 