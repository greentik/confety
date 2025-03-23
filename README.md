# Python Device Control Server

A secure Python server for remote device management and command execution. This tool allows you to remotely execute commands on a device over a network.

## Features

- Secure authentication
- Execute shell commands remotely
- Get system information
- Multiple client connections
- Interactive client mode
- Logging of all activities
- Improved error handling
- JSON-based communication protocol

## Security Warning

**IMPORTANT**: This tool allows remote command execution on your device. Only use it on secure networks and with proper authentication enabled. Never expose the server directly to the internet without additional security measures (such as VPN or SSH tunneling).

## Requirements

- Python 3.6 or higher

## Quick Start

### Starting the Server

```bash
# Start with default settings (port 4444, authentication enabled)
python device_control_server.py

# Start with custom port
python device_control_server.py --port 5555

# Start without authentication (not recommended)
python device_control_server.py --no-auth

# Start with specific host interface
python device_control_server.py --host 192.168.1.100
```

Default credentials:
- Username: `admin`
- Password: `admin_password`

### Using the Client

```bash
# Connect to server on localhost
python device_control_client.py

# Connect to server on specific host and port
python device_control_client.py --host 192.168.1.100 --port 5555

# Connect with credentials
python device_control_client.py --username admin --password admin_password

# Execute a single command and exit
python device_control_client.py --cmd "ls -la"
```

## Client Commands

In interactive mode, the client supports the following commands:

- `exit` - Disconnect and exit the client
- `help` - Show help information
- `ping` - Check server connection and latency
- `sysinfo` - Get system information from the server
- Any other input will be executed as a shell command on the server

## Customizing

### Changing Default Credentials

Edit the `device_control_server.py` file and modify the `USERS` dictionary:

```python
USERS = {
    "admin": hashlib.sha256("admin_password".encode()).hexdigest(),
    "user2": hashlib.sha256("another_password".encode()).hexdigest()
}
```

### Adding More Functionality

The server and client use a simple JSON-based protocol that can be extended. To add a new command type:

1. Add a new command handler in the server's `handle_client` method
2. Add corresponding method in the client class
3. Update the client's help information

## Protocol

The server and client communicate using a simple JSON-based protocol:

```json
// Command request
{"type": "cmd", "command": "ls -la"}

// Command response
{"type": "cmd_response", "status": "success", "output": "file1.txt file2.txt"}

// Authentication request
{"type": "auth_required", "message": "Please authenticate"}

// Authentication response
{"type": "auth_success", "message": "Authentication successful"}

// System info request
{"type": "system_info"}

// System info response
{"type": "system_info_response", "hostname": "device1", "platform": "linux"}

// Ping request
{"type": "ping"}

// Ping response
{"type": "pong", "timestamp": 1622547891.123}
```

## Security Considerations

- Always change the default password
- Use on trusted networks only
- Consider encrypting the connection (e.g., using SSL/TLS)
- Implement more robust authentication if needed
- Monitor logs for unauthorized access attempts

## License

This software is provided as-is with no warranty. Use at your own risk. 