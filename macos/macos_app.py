#!/usr/bin/env python3
"""
portable_macos_app.py - Create a portable macOS application without py2app

Usage:
    python portable_macos_app.py --name <appname> [--html <htmlfile>] [--icon <iconfile>]

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
    """Add exit button and error display to the HTML content."""
    
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
    .error-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.8);
        color: white;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        font-family: Arial, sans-serif;
        z-index: 10000;
        padding: 20px;
        text-align: center;
    }
    .error-content {
        background-color: #d32f2f;
        padding: 20px;
        border-radius: 8px;
        max-width: 80%;
        max-height: 80%;
        overflow-y: auto;
    }
    .error-title {
        font-size: 24px;
        margin-bottom: 20px;
    }
    .error-message {
        font-size: 16px;
        margin-bottom: 20px;
        white-space: pre-wrap;
        text-align: left;
    }
    .error-close {
        background-color: white;
        color: black;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        cursor: pointer;
        font-size: 16px;
        margin-top: 20px;
    }
    </style>
    
    <button id="exit-button" onclick="exitServer()">Exit Server</button>
    
    <script>
    // Error handling function
    function showError(title, message) {
        const overlay = document.createElement('div');
        overlay.className = 'error-overlay';
        
        overlay.innerHTML = `
            <div class="error-content">
                <div class="error-title">${title}</div>
                <div class="error-message">${message}</div>
                <button class="error-close" onclick="this.parentNode.parentNode.remove()">Close</button>
            </div>
        `;
        
        document.body.appendChild(overlay);
    }
    
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
    
    // Check for startup errors
    window.addEventListener('load', function() {
        fetch('/check-status')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError('Application Error', data.error);
                }
            })
            .catch(err => {
                console.error('Error checking application status:', err);
            });
    });
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
    
    # Create the Python script using string concatenation instead of f-strings
    app_script = """#!/usr/bin/env python3
# Web server app for """ + app_name + """

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
import json
import logging
import traceback

# App name (defined at the global scope)
APP_NAME = """ + repr(app_name) + """

# Setup logging
LOG_FILE = os.path.expanduser("~/Library/Logs/""" + app_name.lower() + """_app.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(APP_NAME)

# Configuration
PORT = 8000
PID_FILE = "/tmp/""" + app_name.lower() + """_app.pid"
HTML_CONTENT = """ + html_content_str + """
server = None
startup_error = None

# Get application path
def get_app_path():
    if getattr(sys, 'frozen', False):
        # Running as compiled bundle
        return os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

# Check if port is already in use
def check_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

# Display error message
def show_error_dialog(title, message):
    global startup_error
    startup_error = message
    logger.error("ERROR: %s - %s", title, message)
    
    # Try to show a native dialog for critical errors
    try:
        script = 'display dialog "' + message.replace('"', '\\"') + '" with title "' + title.replace('"', '\\"') + '" buttons {"OK"} default button "OK" with icon stop'
        subprocess.run(['osascript', '-e', script])
    except Exception as e:
        logger.error("Failed to show native error dialog: %s", e)

# Open browser
def open_browser():
    url = "http://localhost:%d/" % PORT
    logger.info("Opening browser to %s", url)
    
    try:
        subprocess.run(['open', url], check=True)
    except:
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.error("Could not open browser: %s", e)
            show_error_dialog("Browser Error", "Could not open browser: " + str(e))

# Handle signals
def signal_handler(sig, frame):
    logger.info("Shutting down...")
    global server
    if server:
        server.shutdown()
    # Always remove the PID file when exiting
    try:
        if os.path.exists(PID_FILE):
            os.unlink(PID_FILE)
            logger.info("Removed PID file on exit")
    except Exception as e:
        logger.error("Error removing PID file: %s", e)
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
        logger.debug(format % args)

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
            return
        elif self.path == '/check-status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = {"error": startup_error} if startup_error else {"status": "ok"}
            self.wfile.write(json.dumps(status).encode('utf-8'))
            return
        elif self.path == '/logs':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            try:
                with open(LOG_FILE, 'r') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            except Exception as e:
                self.wfile.write(("Error reading log file: " + str(e)).encode('utf-8'))
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
    global startup_error
    global server
    
    try:
        # Log system information
        logger.info("Starting " + APP_NAME)
        
        # Check if port is in use
        if check_port_in_use(PORT):
            # If port is in use, assume the app is already running
            # Just open the browser and exit
            logger.info("Port %d is already in use. Opening browser to existing instance.", PORT)
            open_browser()
            sys.exit(0)
        
        # Start the server
        try:
            socketserver.TCPServer.allow_reuse_address = True
            server = socketserver.TCPServer(("localhost", PORT), CustomHTTPRequestHandler)
            
            logger.info("%s server started on port %d", APP_NAME, PORT)
            
            # Write PID to file
            try:
                with open(PID_FILE, 'w') as f:
                    f.write(str(os.getpid()))
                logger.info("Created PID file with PID %d", os.getpid())
                
                # Register cleanup to remove PID file on exit
                atexit.register(lambda: os.path.exists(PID_FILE) and os.unlink(PID_FILE))
            except Exception as e:
                logger.error("Error creating PID file: %s", e)
            
            # Open browser in a separate thread
            threading.Thread(target=lambda: (time.sleep(0.5), open_browser())).start()
            
            # Start serving
            server.serve_forever()
            
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
            if server:
                server.shutdown()
        except Exception as e:
            error_msg = "Server error: " + str(e)
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            show_error_dialog("Server Error", error_msg)
            startup_error = error_msg
            sys.exit(1)
    except Exception as e:
        error_msg = "Critical error: " + str(e)
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        show_error_dialog("Critical Error", error_msg)
        startup_error = error_msg
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
    return app_script

def find_system_python():
    """Find the system Python interpreter."""
    try:
        # Try to find system Python
        result = subprocess.run(
            ["which", "python3"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip()
    except:
        # Fallback to common paths
        paths = [
            "/usr/bin/python3",
            "/usr/local/bin/python3",
            "/opt/homebrew/bin/python3"
        ]
        for path in paths:
            if os.path.exists(path):
                return path
    
    return None

def create_app_launcher_script(app_name):
    """Create a launcher script for the app."""
    launcher_script = """#!/bin/bash
# Launcher script for """ + app_name + """

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create log directory if it doesn't exist
mkdir -p "$HOME/Library/Logs"

# Log file
LOG_FILE="$HOME/Library/Logs/""" + app_name.lower() + """_launcher.log"

# Log function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Error handling function - ONLY used for critical errors
show_error() {
    # Only show error dialog for truly critical errors
    osascript -e "display dialog \\"$1\\" with title \\"Error: """ + app_name + """\\\" buttons {\\"OK\\"} default button \\"OK\\" with icon stop"
    log "CRITICAL ERROR: $1"
}

# Check if port 8000 is in use - if so, just open browser to the running instance
if nc -z localhost 8000 2>/dev/null; then
    log "App is already running on port 8000. Opening browser."
    open "http://localhost:8000/"
    exit 0
fi

# Path to the app script
APP_SCRIPT="$DIR/../Resources/app.py"

# Check if app script exists
if [ ! -f "$APP_SCRIPT" ]; then
    show_error "Application script not found at $APP_SCRIPT"
    exit 1
fi

# Find a working Python interpreter
PYTHON_PATHS=(
    # First try system Python
    "/usr/bin/python3"
    # Then try common Homebrew paths
    "/usr/local/bin/python3"
    "/opt/homebrew/bin/python3"
    # Then try macOS bundled Python
    "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
)

PYTHON_PATH=""
for path in "${PYTHON_PATHS[@]}"; do
    if [ -x "$path" ]; then
        # Test if Python works
        "$path" -c "import http.server, socketserver, webbrowser" 2>/dev/null
        if [ $? -eq 0 ]; then
            PYTHON_PATH="$path"
            break
        fi
    fi
done

# If no Python found, try to find it in PATH
if [ -z "$PYTHON_PATH" ]; then
    PYTHON_PATH=$(which python3 2>/dev/null)
    if [ -n "$PYTHON_PATH" ]; then
        "$PYTHON_PATH" -c "import http.server, socketserver, webbrowser" 2>/dev/null
        if [ $? -ne 0 ]; then
            PYTHON_PATH=""
        fi
    fi
fi

# If still no Python, error out
if [ -z "$PYTHON_PATH" ]; then
    show_error "Could not find a working Python 3 installation. Please install Python 3."
    exit 1
fi

# Log startup
log "Starting """ + app_name + """" 
log "Using Python: $PYTHON_PATH"
log "App script: $APP_SCRIPT"

# Launch the app and wait for it to exit
"$PYTHON_PATH" "$APP_SCRIPT" &

# Store the PID of the Python process
APP_PID=$!

# Log the process start
log "App started with PID $APP_PID"

# Wait a moment for the app to start
sleep 2

# Check if the process is still running
if kill -0 $APP_PID 2>/dev/null; then
    log "App is running successfully"
else
    # Only show error if port 8000 is not in use (meaning no app is running)
    if ! nc -z localhost 8000 2>/dev/null; then
        show_error "Failed to start application. Check logs at $LOG_FILE"
        exit 1
    else
        # If port is in use, another instance is probably running
        log "App not running but port 8000 is in use. Opening browser."
        open "http://localhost:8000/"
    fi
fi

exit 0
"""
    return launcher_script

def create_macos_app(app_name, html_path=None, icon_path=None):
    """Create a simple macOS app bundle."""
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
        
        # Create a README file with instructions
        readme_path = os.path.join(resources_path, "README.txt")
        readme_content = "README for " + app_name + """

This application is a web server that serves HTML content in a browser window.

If the application fails to start:
1. Check the logs at: ~/Library/Logs/""" + app_name.lower() + """_app.log
2. Make sure Python 3 is installed on your system
3. The application requires Python 3 with the following modules:
   - http.server (standard library)
   - socketserver (standard library)
   - webbrowser (standard library)

For support, please contact the developer.
"""
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
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
            # Show dock icon
            'LSUIElement': False,
            'LSMultipleInstancesProhibited': True,
            'LSBackgroundOnly': False,
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
        print(f"          ├── README.txt (Troubleshooting guide)")
        if icon_path:
            print(f"          ├── {os.path.basename(icon_path)} (App icon)")
        
        print("\nThis app will:")
        print("1. Show an app icon in the Dock")
        print(f"2. Start a web server on port 8000 serving your content")
        print("3. Open a browser to view your content")
        print("4. Include an 'Exit Server' button in the web interface")
        print("5. Prevent multiple instances from running")
        print("6. Work on any Mac with Python 3 installed")
        print("\nLog files are stored at:")
        print(f"- ~/Library/Logs/{app_name.lower()}_launcher.log (for startup issues)")
        print(f"- ~/Library/Logs/{app_name.lower()}_app.log (for application issues)")
        
        return True
    
    except Exception as e:
        print(f"Error creating app: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Create a portable macOS application")
    parser.add_argument('--name', required=True, help='Name for the application bundle')
    parser.add_argument('--html', help='Path to an HTML file to serve as the content')
    parser.add_argument('--icon', help='Path to an ICNS icon file for the application')
    
    args = parser.parse_args()
    
    create_macos_app(args.name, args.html, args.icon)

if __name__ == "__main__":
    main()