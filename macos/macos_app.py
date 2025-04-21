#!/usr/bin/env python3
"""
macos_app.py - Create a native macOS application without py2app

Usage:
    python macos_app.py --name <appname> [--html <htmlfile>] [--icon <iconfile>]

Arguments:
    --name      The name for the application bundle
    --html      (Optional) Path to an HTML file to serve as the content
    --icon      (Optional) Path to an ICNS file for the app icon
"""

import os
import sys
import shutil
import argparse
import plistlib
import subprocess
from pathlib import Path

def modify_html_content(html_content):
    """Add exit button to the HTML content."""
    
    # Script to add to the HTML
    exit_script = """
    <style>
    #exit-button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #f44336;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        border: none;
        cursor: pointer;
        font-size: 16px;
        z-index: 9999;
    }
    #exit-button:hover {
        background-color: #d32f2f;
    }
    </style>
    
    <button id="exit-button" onclick="exitServer()">Exit Server</button>
    
    <script>
    function exitServer() {
        if (confirm('Are you sure you want to exit the server?')) {
            fetch('/exit', { method: 'POST' })
                .then(() => {
                    document.body.innerHTML = `
                        <div style="
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            font-family: Arial, sans-serif;
                            text-align: center;
                        ">
                            <h1>Server shutdown. You can close this window.</h1>
                        </div>
                    `;
                })
                .catch(err => {
                    console.error('Error shutting down server:', err);
                    alert('Error shutting down server. Please try again.');
                });
        }
    }
    </script>
    """
    
    # Add the exit button before the closing body tag
    if "</body>" in html_content:
        modified_html = html_content.replace("</body>", exit_script + "</body>")
    else:
        modified_html = html_content + exit_script
    
    return modified_html

def create_app_script(app_name, html_content=None):
    """Create the Python script for the standalone app."""
    
    # Handle HTML content embedding
    if html_content:
        # Add exit button to HTML content
        html_content = modify_html_content(html_content)
        # Convert the HTML content to a Python string
        html_content_str = repr(html_content)
    else:
        # Create a minimal HTML page with exit button
        minimal_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>WebApp</title>
        </head>
        <body>
            <h1>Web Server</h1>
            <p>Server is running.</p>
        </body>
        </html>
        """
        html_content = modify_html_content(minimal_html)
        html_content_str = repr(html_content)
    
    # Create the Python script that will be the core of our app
    app_script = f"""#!/usr/bin/env python3
# Web server app for {app_name}

import os
import sys
import socket
import http.server
import socketserver
import threading
import time
import signal
import atexit
import subprocess
import webbrowser

# Configuration
PORT = 8000
PID_FILE = "/tmp/{app_name.lower()}_app.pid"
LOCK_PORT = 12345
HTML_CONTENT = {html_content_str}
server = None

# Check if another instance is running using PID file
def is_already_running():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            try:
                pid = int(f.read().strip())
                # Check if process with this PID exists
                try:
                    os.kill(pid, 0)
                    print(f"Another instance is running (PID: {{pid}})")
                    return True
                except OSError:
                    print("Stale PID file found. Removing...")
                    os.unlink(PID_FILE)
            except (ValueError, FileNotFoundError):
                pass
    return False

# Check if a port is already in use
def check_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

# Write PID file
def write_pid_file():
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

# Remove PID file on exit
def remove_pid_file():
    if os.path.exists(PID_FILE):
        os.unlink(PID_FILE)

# Register cleanup function
atexit.register(remove_pid_file)

# Open browser
def open_browser():
    url = f"http://localhost:{{PORT}}/"
    print(f"Opening browser to {{url}}")
    
    try:
        subprocess.run(['open', url], check=True)
    except:
        try:
            webbrowser.open(url)
        except:
            print("Could not open browser")

# Handle signals
def signal_handler(sig, frame):
    print("Shutting down...")
    global server
    if server:
        server.shutdown()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Custom HTTP request handler
class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()
    
    def log_message(self, format, *args):
        return  # Suppress log messages

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
            return
        elif self.path == '/exit':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Shutting down server...')
            threading.Thread(target=lambda: (time.sleep(0.5), signal_handler(None, None))).start()
            return
        return super().do_GET()
    
    def do_POST(self):
        if self.path == '/exit':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Server shutting down...')
            threading.Thread(target=lambda: (time.sleep(0.5), signal_handler(None, None))).start()
            return
        
        self.send_response(405)  # Method Not Allowed
        self.end_headers()

def main():
    # Check if another instance is running
    if is_already_running():
        print("App is already running. Opening browser...")
        open_browser()
        return
    
    # Check if port is in use
    if check_port_in_use(PORT):
        print(f"Port {{PORT}} is already in use. Opening browser...")
        open_browser()
        return
    
    # Write PID file
    write_pid_file()
    
    # Start the server
    try:
        global server
        socketserver.TCPServer.allow_reuse_address = True
        server = socketserver.TCPServer(("localhost", PORT), CustomHTTPRequestHandler)
        
        print(f"{app_name} server started on port {{PORT}}")
        
        # Open browser in a separate thread
        threading.Thread(target=lambda: (time.sleep(0.5), open_browser())).start()
        
        # Start serving
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Error: {{e}}")
    finally:
        if server:
            server.shutdown()
        remove_pid_file()

if __name__ == "__main__":
    main()
"""
    return app_script

def create_app_launcher_script(app_name):
    """Create a launcher script for the app."""
    launcher_script = f"""#!/bin/bash
# Launcher script for {app_name}

# Get the directory of this script
DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )"

# Path to the Python executable in the app bundle
PYTHON_PATH="$DIR/../Resources/venv/bin/python3"

# Path to the app script
APP_SCRIPT="$DIR/../Resources/app.py"

# Launch the app in the background
"$PYTHON_PATH" "$APP_SCRIPT" "$@" &
"""
    return launcher_script

def check_requirements():
    """Check and install requirements."""
    try:
        # We don't need any external packages for this simplified version
        return True
    except Exception as e:
        print(f"Error checking requirements: {e}")
        return False

def create_macos_app(app_name, html_path=None, icon_path=None):
    """Create a simple macOS app bundle."""
    # Check requirements
    if not check_requirements():
        return False
    
    try:
        # Read HTML content if provided
        html_content = None
        if html_path and os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            print(f"Successfully loaded HTML content from {html_path}")
        elif html_path:
            print(f"Warning: HTML file {html_path} not found. Will serve a default page instead.")
        
        # Create app script
        app_script = create_app_script(app_name, html_content)
        
        # Create launcher script
        launcher_script = create_app_launcher_script(app_name)
        
        # Create app bundle structure
        app_bundle_name = f"{app_name}.app"
        contents_path = os.path.join(app_bundle_name, "Contents")
        macos_path = os.path.join(contents_path, "MacOS")
        resources_path = os.path.join(contents_path, "Resources")
        venv_path = os.path.join(resources_path, "venv")
        
        # Clean any existing bundle with the same name
        if os.path.exists(app_bundle_name):
            shutil.rmtree(app_bundle_name)
        
        # Create directories
        os.makedirs(macos_path, exist_ok=True)
        os.makedirs(resources_path, exist_ok=True)
        
        # Write app script
        with open(os.path.join(resources_path, "app.py"), 'w') as f:
            f.write(app_script)
        os.chmod(os.path.join(resources_path, "app.py"), 0o755)
        
        # Write launcher script
        with open(os.path.join(macos_path, app_name), 'w') as f:
            f.write(launcher_script)
        os.chmod(os.path.join(macos_path, app_name), 0o755)
        
        # Create a virtual environment in the app bundle
        print(f"Creating virtual environment in {venv_path}...")
        subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
        
        # Create Info.plist
        info_plist = {
            'CFBundleName': app_name,
            'CFBundleDisplayName': app_name,
            'CFBundleIdentifier': f'com.example.{app_name.lower()}',
            'CFBundleVersion': '1.0',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': '????',
            'CFBundleExecutable': app_name,
            'CFBundleDevelopmentRegion': 'English',
            'CFBundleInfoDictionaryVersion': '6.0',
            'NSHighResolutionCapable': True,
            'LSUIElement': True,  # No dock icon
            'LSMultipleInstancesProhibited': True,  # Prevent multiple instances
            'LSBackgroundOnly': True,  # Run in background only
        }
        
        # Copy icon to the bundle if provided
        if icon_path and os.path.exists(icon_path):
            icon_filename = os.path.basename(icon_path)
            resources_icon_path = os.path.join(resources_path, icon_filename)
            shutil.copy2(icon_path, resources_icon_path)
            print(f"Copied icon from {icon_path} to {resources_icon_path}")
            
            # Update Info.plist with icon info
            info_plist['CFBundleIconFile'] = icon_filename
        
        # Write Info.plist
        with open(os.path.join(contents_path, 'Info.plist'), 'wb') as fp:
            plistlib.dump(info_plist, fp)
        
        print(f"Successfully created application bundle: {app_bundle_name}")
        print(f"Bundle structure:")
        print(f"  {app_bundle_name}")
        print(f"  └── Contents")
        print(f"      ├── Info.plist")
        print(f"      ├── MacOS")
        print(f"      │   └── {app_name} (Launcher script)")
        print(f"      └── Resources")
        print(f"          ├── app.py (Main application)")
        if icon_path:
            print(f"          ├── {os.path.basename(icon_path)} (App icon)")
        print(f"          └── venv (Python virtual environment)")
        
        print("\nThis app will:")
        print("1. Run in the background (no dock icon)")
        print(f"2. Start a web server on port 8000 serving your content")
        print("3. Open a browser to view your content")
        print("4. Include an 'Exit Server' button in the web interface")
        print("5. Prevent multiple instances from running")
        
        return True
    
    except Exception as e:
        print(f"Error creating app: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Create a simple macOS application")
    parser.add_argument('--name', required=True, help='Name for the application bundle')
    parser.add_argument('--html', help='Path to an HTML file to serve as the content')
    parser.add_argument('--icon', help='Path to an ICNS icon file for the application')
    
    args = parser.parse_args()
    
    create_macos_app(args.name, args.html, args.icon)

if __name__ == "__main__":
    main()