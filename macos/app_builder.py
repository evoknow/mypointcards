# PyInstaller app builder for macOS with improved app startup.

import os
import sys
import shutil
import subprocess
import tempfile
import platform
import traceback
import re

# Import other modules
import html_handler
import dock_handler
import server
import time

def build_app(app_name, html_path=None, icon_path=None):
    # Build the macOS app using PyInstaller.
    
    print(f"Building app: {app_name}")
    
    # Check if PyInstaller is installed
    try:
        subprocess.run(["pyinstaller", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("PyInstaller is already installed.")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "PyInstaller"])
            print("PyInstaller installed successfully.")
        except subprocess.SubprocessError:
            print("Failed to install PyInstaller. Please install it manually:")
            print("    pip install PyInstaller")
            return False
    
    # Install PyObjC on macOS
    if platform.system() == "Darwin":
        try:
            print("Installing PyObjC dependencies...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyobjc-core", "pyobjc-framework-Cocoa"])
            print("PyObjC dependencies installed successfully.")
        except subprocess.SubprocessError:
            print("Warning: Failed to install PyObjC. The app may not show a Dock icon.")
    
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Get HTML content
            html_content = html_handler.get_html_content(html_path)
            
            # Create server script
            server_script = create_server_script(app_name, html_content)
            script_path = os.path.join(temp_dir, "server_script.py")
            
            with open(script_path, "w") as f:
                f.write(server_script)
            
            # Copy dock_handler.py to temp dir
            dock_handler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dock_handler.py"))
            temp_dock_handler_path = os.path.join(temp_dir, "dock_handler.py")
            
            try:
                shutil.copy2(dock_handler_path, temp_dock_handler_path)
                print(f"Copied dock_handler.py to {temp_dock_handler_path}")
            except Exception as e:
                print(f"Warning: Could not copy dock_handler.py: {e}")
                # Create the file if it doesn't exist
                try:
                    with open(dock_handler_path, "r") as src:
                        content = src.read()
                    with open(temp_dock_handler_path, "w") as dest:
                        dest.write(content)
                    print(f"Created dock_handler.py in {temp_dir}")
                except Exception as e2:
                    print(f"Error creating dock_handler.py: {e2}")
            
            # Make script executable
            os.chmod(script_path, 0o755)
            
            # Prepare icon if provided
            icon_path_str = ""
            if icon_path and os.path.exists(icon_path):
                # Use the absolute path to the icon
                icon_path = os.path.abspath(icon_path)
                icon_path_str = f"icon=r'{icon_path}',"
            
            # Create spec file
            app_name_lower = app_name.lower().replace(" ", "_")
            spec_content = create_spec_file(app_name, app_name_lower, script_path, temp_dir, icon_path_str)
            
            # Write the spec file
            spec_path = os.path.join(temp_dir, f"{app_name}.spec")
            with open(spec_path, "w") as f:
                f.write(spec_content)
            
            # Log debug info to desktop
            with open(os.path.expanduser(f"~/Desktop/{app_name}_build_debug.log"), "w") as f:
                f.write(f"Building app at {time.ctime()}\n")
                f.write(f"Temporary directory: {temp_dir}\n")
                f.write(f"Script path: {script_path}\n")
                f.write(f"Spec path: {spec_path}\n")
                f.write(f"Current directory: {os.getcwd()}\n")
                f.write(f"Python executable: {sys.executable}\n")
                
                # Check if dock_handler.py is in the temp dir
                f.write(f"dock_handler.py exists in temp dir: {os.path.exists(temp_dock_handler_path)}\n")
                
                # Print directory contents
                f.write("\nTemporary directory contents:\n")
                for filename in os.listdir(temp_dir):
                    filepath = os.path.join(temp_dir, filename)
                    f.write(f"  {filename} - {'dir' if os.path.isdir(filepath) else 'file'}\n")
            
            # Run PyInstaller with the spec file
            print("Building app with PyInstaller...")
            try:
                pyinstaller_cmd = ["pyinstaller", "--clean", spec_path]
                subprocess.run(pyinstaller_cmd, check=True, cwd=temp_dir)
            except subprocess.CalledProcessError as e:
                print(f"Error building app: {e}")
                return False
            
            # Copy app to current directory
            app_path = os.path.join(temp_dir, "dist", f"{app_name}.app")
            dest_path = os.path.join(os.getcwd(), f"{app_name}.app")
            
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            
            shutil.copytree(app_path, dest_path)
            
            print(f"\nSuccessfully created {app_name}.app")
            print(f"The app is located at: {os.path.abspath(dest_path)}")
            print("\nFeatures:")
            print("1. Shows an icon in the Dock when running")
            print("2. Serves your HTML content in a browser")
            print("3. Includes an 'Exit' button to shut down the server")
            print("4. Only allows one instance to run at a time")
            print("5. Clicking the Dock icon again reopens the browser")
            
            return True
            
    except Exception as e:
        import traceback
        error_message = traceback.format_exc()
        with open(os.path.expanduser(f"~/Desktop/{app_name}_error.log"), "w") as f:
            f.write(f"Error starting {app_name}:\n")
            f.write(error_message)
        traceback.print_exc()
        return False

def fix_regex_patterns(html_content):
    # Fix all problematic regex patterns in HTML content.
    # Fix iOS version detection regex
    html_content = html_content.replace(r'/OS (\d+)', r'/OS (\\d+)')
    html_content = html_content.replace(r'_(\d+)', r'_(\\d+)')
    html_content = html_content.replace(r'_?(\d+)?', r'_?(\\d+)?')
    
    # Fix CSS gradient regex patterns
    html_content = html_content.replace(r'/linear-gradient\(', r'/linear-gradient\\(')
    html_content = html_content.replace(r'([^)]+)\)', r'([^)]+)\\)')
    
    # Fix other common regex patterns that might cause issues
    html_content = html_content.replace(r'\s+', r'\\s+')  # Whitespace
    html_content = html_content.replace(r'\w+', r'\\w+')  # Word characters
    html_content = html_content.replace(r'\b', r'\\b')    # Word boundaries
    
    # Use regex to find and fix any remaining regex patterns
    # Look for regex literals (patterns between forward slashes)
    pattern = r'(/[^/\n]+/[gimuy]*)'
    
    def fix_escapes(match):
        regex = match.group(1)
        # Replace all backslashes with double backslashes if not already doubled
        regex = regex.replace('\\', '\\\\')
        # Fix double-escaped backslashes
        regex = regex.replace('\\\\\\\\', '\\\\')
        return regex
    
    html_content = re.sub(pattern, fix_escapes, html_content)
    
    return html_content

def create_server_script(app_name, html_content):
    # Generate the server script.
    
    # Fix any potential regex escaping issues in the HTML content
    html_content = fix_regex_patterns(html_content)
    
    # Start of the script - main Python server code
    script = f"""#!/usr/bin/env python3
# Web server for {app_name}

import os
import sys
import http.server
import socketserver
import threading
import time
import signal
import subprocess
import webbrowser
import tempfile
import socket
import atexit
import logging
import traceback
import urllib.request

# Set up a basic configuration for the root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("{app_name}")

# Add this to make the dock_handler module available
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Debug - write Python path info
with open(os.path.expanduser(f"~/Desktop/{app_name}_path_debug.log"), "w") as f:
    f.write(f"Python path at startup:\\n")
    for path in sys.path:
        f.write(f" - {{path}}\\n")
    f.write("\\nCurrent directory: " + os.getcwd() + "\\n")
    f.write("Script directory: " + os.path.dirname(os.path.abspath(__file__)) + "\\n")

try:
    # First try to import from the current directory
    import dock_handler
    logger.info("Successfully imported dock_handler module from current directory")
    with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
        f.write(f"Imported dock_handler from current directory\\n")
except ImportError as e:
    # If that fails, try to import from parent directories
    logger.warning(f"Could not import dock_handler from current directory: {{e}}")
    
    # Add parent directory to path
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, parent_dir)
    
    # Also add Resources directory for macOS app bundles
    resources_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Resources'))
    if os.path.exists(resources_dir):
        sys.path.insert(0, resources_dir)
    
    # Try importing again
    try:
        import dock_handler
        logger.info("Successfully imported dock_handler module from parent/resources directory")
        with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
            f.write(f"Imported dock_handler from parent/resources directory\\n")
    except ImportError as e2:
        logger.warning(f"Could not import dock_handler: {{e2}}")
        # Create a fallback dock_handler module
        try:
            with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                f.write(f"Creating fallback dock_handler module\\n")
                
            # Create an empty dock_handler.py in the current directory
            dock_handler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dock_handler.py')
            with open(dock_handler_path, 'w') as f:
                f.write('''# Fallback macOS Dock icon handling.

import os
import sys
import threading
import logging
import subprocess
import webbrowser
import socket

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dock_handler")

# Debug log file
DEBUG_LOG_FILE = os.path.expanduser("~/Desktop/dock_handler_fallback_debug.log")

# Initial log
with open(DEBUG_LOG_FILE, "a") as f:
    f.write("\\n--- Fallback dock handler initialized ---\\n")

# Check if port is already in use
def is_port_in_use(port=8000):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    except Exception as e:
        logger.error(f"Error checking port: {{e}}")
        return False

# Wait for server to be ready
def wait_for_server_ready(port=8000, max_attempts=20):
    # Wait until server is ready to accept connections.
    for i in range(max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) == 0:
                    logger.info(f"Server ready after {{i+1}} attempts")
                    with open(DEBUG_LOG_FILE, "a") as f:
                        f.write(f"Server ready after {{i+1}} attempts\\n")
                    return True
        except:
            pass
        time.sleep(0.1)
    logger.warning("Server failed to be ready in expected time")
    with open(DEBUG_LOG_FILE, "a") as f:
        f.write("Server failed to be ready in expected time\\n")
    return False

def open_browser():
    # Open web browser to the local server.
    url = "http://localhost:8000/"
    logger.info(f"Opening browser to {{url}}")
    
    # Check if the server is already running
    server_running = is_port_in_use()
    with open(DEBUG_LOG_FILE, "a") as f:
        f.write(f"Server running check: {{server_running}}\\n")
    
    # Wait for server to be ready if it's running
    if server_running:
        wait_for_server_ready()
    
    try:
        if sys.platform == 'darwin':
            subprocess.run(['open', url], check=True)
        else:
            webbrowser.open(url)
    except Exception as e:
        logger.error(f"Could not open browser: {{e}}")
        try:
            webbrowser.open_new(url)
        except Exception as e2:
            logger.error(f"Alternative browser method also failed: {{e2}}")

def setup_dock_icon():
    # Fallback function that does nothing but logs the attempt.
    with open(DEBUG_LOG_FILE, "a") as f:
        f.write("Fallback setup_dock_icon called, but no functionality available\\n")
    return False

def check_dock_status():
    # Return fallback status.
    status = {{
        "setup_complete": False,
        "delegate_exists": False,
        "click_count": 0,
    }}
    with open(DEBUG_LOG_FILE, "a") as f:
        f.write("Fallback check_dock_status called\\n")
    return status
''')
            
            # Now try to import it
            import dock_handler
            logger.info("Using fallback dock_handler module")
            with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                f.write(f"Using fallback dock_handler module\\n")
        except Exception as e3:
            logger.error(f"Failed to create fallback dock_handler: {{e3}}")
            with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                f.write(f"Failed to create fallback dock_handler: {{e3}}\\n")

# Setup logging to file
try:
    log_dir = os.path.expanduser("~/Library/Logs/{app_name}")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "{app_name.lower()}.log")

    # Add a file handler to the root logger
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
    
    logger.info(f"Logging initialized for {app_name}")
except Exception as e:
    logger.warning(f"Using console logging only: {{e}}")

# Create debug log
with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
    f.write(f"\\n--- Starting {app_name} at {{time.ctime()}} ---\\n")

# Global exception handler
def global_exception_handler(exctype, value, tb):
    error_msg = f"Uncaught exception: {{exctype.__name__}}: {{value}}"
    logger.error(error_msg)
    for line in traceback.format_tb(tb):
        logger.error(line.rstrip())

# Set global exception handler
sys.excepthook = global_exception_handler

# Configuration
PORT = 8000

# Store the actual HTML content in a variable
HTML_CONTENT = '''{html_content}'''

# Exit button script that gets injected 
EXIT_BUTTON_SCRIPT = '''
<style>
#exit-app-button {{
    position: fixed;
    bottom: 20px;
    right: 20px;
    background-color: #f44336;
    color: white;
    padding: 10px 20px;
    border-radius: 5px;
    border: none;
    cursor: pointer;
    z-index: 9999;
    font-family: Arial, sans-serif;
    font-size: 14px;
}}
#exit-app-button:hover {{
    background-color: #d32f2f;
}}
.exit-confirmation {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
    font-family: Arial, sans-serif;
}}
.exit-confirmation-box {{
    background-color: white;
    padding: 20px;
    border-radius: 5px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    max-width: 90%;
    width: 400px;
}}
.exit-confirmation-buttons {{
    margin-top: 20px;
}}
.exit-confirmation-buttons button {{
    padding: 8px 16px;
    margin: 0 10px;
    border-radius: 4px;
    border: none;
    cursor: pointer;
}}
.exit-cancel {{
    background-color: #e0e0e0;
}}
.exit-confirm {{
    background-color: #f44336;
    color: white;
}}
</style>

<button id="exit-app-button">Exit App</button>
<div class="exit-confirmation" id="exit-confirmation" style="display: none;">
    <div class="exit-confirmation-box">
        <h2>Confirm Exit</h2>
        <p>Are you sure you want to exit the application?</p>
        <div class="exit-confirmation-buttons">
            <button class="exit-cancel" id="exit-cancel">Cancel</button>
            <button class="exit-confirm" id="exit-confirm">Exit</button>
        </div>
    </div>
</div>

<script>
// Set up the exit button functionality
(function() {{
    // Exit button click handler
    document.getElementById('exit-app-button').addEventListener('click', function() {{
        document.getElementById('exit-confirmation').style.display = 'flex';
    }});
    
    // Cancel exit
    document.getElementById('exit-cancel').addEventListener('click', function() {{
        document.getElementById('exit-confirmation').style.display = 'none';
    }});
    
    // Confirm exit
    document.getElementById('exit-confirm').addEventListener('click', function() {{
        document.getElementById('exit-confirmation').style.display = 'none';
        
        // Show loading indicator
        const loadingHTML = `
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                      background-color: rgba(255,255,255,0.9); z-index: 10000;
                      display: flex; flex-direction: column; 
                      justify-content: center; align-items: center;">
                <h1>Shutting down...</h1>
                <p>Please wait while the application closes.</p>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', loadingHTML);
        
        // Send exit request to server
        fetch('/exit', {{ 
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'X-Exit-Requested-By': 'user-interface'
            }}
        }})
        .then(response => {{
            if (!response.ok) {{
                throw new Error('Server responded with an error');
            }}
            document.body.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;"><h1>Server shutdown. You can close this window.</h1></div>';
        }})
        .catch(err => {{
            alert('Error shutting down: ' + err);
        }});
    }});
    
    // Set up the tab close/refresh detector
    window.addEventListener('beforeunload', function(e) {{
        // Add server shutdown call when tab is closed or refreshed
        const exitBeacon = new Image();
        exitBeacon.src = '/exit?auto_close=true&t=' + new Date().getTime();
        
        // Use fetch with keepalive to ensure the request completes
        // even if the page is being unloaded
        navigator.sendBeacon('/exit', JSON.stringify({{
            reason: 'tab_closed',
            timestamp: new Date().toISOString()
        }}));
        
        // No need to show a confirmation dialog since the app will simply restart
        // We just return undefined to proceed with the close without a confirmation
        return undefined;
    }});
}})();
</script>
'''

# Check if port is already in use
def is_port_in_use():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', PORT)) == 0
    except Exception as e:
        logger.error(f"Error checking port: {{e}}")
        return False

# Wait for server to be ready
def wait_for_server_ready(max_attempts=20):
    # Wait until server is ready to accept connections.
    for i in range(max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', PORT)) == 0:
                    logger.info(f"Server ready after {{i+1}} attempts")
                    return True
        except:
            pass
        time.sleep(0.1)
    logger.warning("Server failed to be ready in expected time")
    return False

# Open browser - use the function from dock_handler module
def open_browser():
    # Try to use the dock_handler open_browser function if available
    if 'dock_handler' in sys.modules:
        try:
            dock_handler.open_browser()
            logger.info("Using dock_handler.open_browser()")
            return
        except Exception as e:
            logger.error(f"Error using dock_handler.open_browser(): {{e}}")
    
    # Fallback if dock_handler is not available
    url = f"http://localhost:{{PORT}}/"
    logger.info(f"Waiting for server to be ready before opening browser")
    
    # Wait for server to be ready before opening browser
    if not wait_for_server_ready():
        logger.error("Server not ready, attempting to open browser anyway")
    
    logger.info(f"Opening browser to {{url}}")
    
    try:
        if sys.platform == 'darwin':
            subprocess.run(['open', url], check=True)
        else:
            webbrowser.open(url)
    except Exception as e:
        logger.error(f"Could not open browser: {{e}}")
        try:
            webbrowser.open_new(url)
        except Exception as e2:
            logger.error(f"Alternative browser method also failed: {{e2}}")

# PID file
pid_file = os.path.join(tempfile.gettempdir(), "{app_name.lower()}.pid")
shutdown_in_progress = False

# Remove PID file on exit
def cleanup():
    if os.path.exists(pid_file):
        try:
            os.unlink(pid_file)
            logger.info("Removed PID file")
        except Exception as e:
            logger.error(f"Error removing PID file: {{e}}")

# Handle signals
def signal_handler(sig, frame):
    logger.info("Shutting down server...")
    cleanup()
    # Force exit the process - ensures complete termination
    os._exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Register cleanup function
atexit.register(cleanup)

# HTTPServer with shutdown support
class ShutdownHTTPServer(socketserver.TCPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shutdown_requested = False
        
    def server_close(self):
        # Override server_close to ensure proper cleanup.
        super().server_close()
        logger.info("Server closed.")

# Custom HTTP request handler
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(format % args)
    
    def do_GET(self):
        try:
            if self.path == '/':
                # Use the global HTML_CONTENT variable
                html_content = HTML_CONTENT
                
                # Always inject exit button right before </body>
                if "</body>" in html_content:
                    html_content = html_content.replace("</body>", EXIT_BUTTON_SCRIPT + "</body>")
                else:
                    html_content = html_content + EXIT_BUTTON_SCRIPT
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
                return
            elif self.path == '/open':
                # Endpoint to open browser with better logging
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Opening browser...')
                logger.info("Received /open request, opening browser")
                with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                    f.write(f"Received /open request at {{time.ctime()}}\\n")
                threading.Thread(target=open_browser).start()
                return
            elif self.path == '/ping':
                # Simple endpoint to check if server is running
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'pong')
                return
            elif self.path == '/setup-dock':
                # Endpoint to force setup of dock icon
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                
                if 'dock_handler' in sys.modules:
                    try:
                        result = dock_handler.setup_dock_icon()
                        self.wfile.write(f"Dock setup result: {{result}}".encode('utf-8'))
                        logger.info(f"Manual dock setup triggered: {{result}}")
                    except Exception as e:
                        error_msg = f"Error setting up dock: {{str(e)}}"
                        self.wfile.write(error_msg.encode('utf-8'))
                        logger.error(error_msg)
                else:
                    self.wfile.write(b"dock_handler module not available")
                return
            elif self.path == '/check-dock-handler':
                # Add an endpoint to check dock handler status
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                
                info = []
                
                # Check dock_handler
                if 'dock_handler' in sys.modules:
                    try:
                        info.append("dock_handler module: FOUND")
                        
                        # Check if it has the check_dock_status function
                        if hasattr(dock_handler, 'check_dock_status'):
                            status = dock_handler.check_dock_status()
                            info.append(f"Dock setup complete: {{status.get('setup_complete', False)}}")
                            info.append(f"Delegate exists: {{status.get('delegate_exists', False)}}")
                            info.append(f"App instance exists: {{status.get('app_instance_exists', False)}}")
                            info.append(f"Event thread alive: {{status.get('event_thread_alive', False)}}")
                            info.append(f"Dock click count: {{status.get('click_count', 0)}}")
                        else:
                            info.append("dock_handler.check_dock_status: NOT FOUND")
                    except Exception as e:
                        info.append(f"dock_handler error: {{str(e)}}")
                else:
                    info.append("dock_handler module: NOT FOUND")
                
                # Check PyObjC
                try:
                    import objc
                    info.append(f"PyObjC available: Yes")
                    if hasattr(objc, '__version__'):
                        info.append(f"PyObjC version: {{objc.__version__}}")
                except ImportError:
                    info.append("PyObjC available: No")
                
                # Check AppKit
                try:
                    import AppKit
                    info.append("AppKit available: Yes")
                except ImportError:
                    info.append("AppKit available: No")
                
                # Log and return the info
                info_text = "\\n".join(info)
                with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                    f.write(f"Dock handler check at {{time.ctime()}}:\\n{{info_text}}\\n")
                
                self.wfile.write(info_text.encode('utf-8'))
                return
            elif self.path == '/test-open':
                # Add a test endpoint for debugging browser opening
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                
                results = []
                
                # Try subprocess
                try:
                    subprocess.run(['open', f'http://localhost:{{PORT}}/'], check=True, timeout=2)
                    results.append("Subprocess method: SUCCESS")
                except Exception as e:
                    results.append(f"Subprocess method: FAILED - {{str(e)}}")
                
                # Try webbrowser
                try:
                    import webbrowser
                    browser_result = webbrowser.open(f'http://localhost:{{PORT}}/')
                    results.append(f"Webbrowser method: {{'' if browser_result else 'NOT '}}SUCCESS")
                except Exception as e:
                    results.append(f"Webbrowser method: FAILED - {{str(e)}}")
                
                # Try dock_handler
                if 'dock_handler' in sys.modules:
                    try:
                        results.append("dock_handler module: FOUND")
                        dock_handler.open_browser()
                        results.append("dock_handler.open_browser() called")
                    except Exception as e:
                        results.append(f"dock_handler error: {{str(e)}}")
                else:
                    results.append("dock_handler module: NOT FOUND")
                
                # Log and return results
                result_text = "\\n".join(results)
                with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                    f.write(f"Browser open test at {{time.ctime()}}:\\n{{result_text}}\\n")
                
                self.wfile.write(result_text.encode('utf-8'))
                return
            elif self.path.startswith('/exit') and 'auto_close=true' in self.path:
                # Handle beacon request from beforeunload event
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Shutting down from tab close')
                
                # Log the tab close request
                logger.info("Tab close request received. Shutting down...")
                with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                    f.write(f"Tab close request received at {time.ctime()}\\n")
                
                # Shutdown in separate thread
                def delayed_shutdown():
                    time.sleep(0.5)  # Give the browser time to process
                    
                    # Create a file to indicate successful shutdown trigger
                    try:
                        with open(os.path.expanduser(f"~/Desktop/{app_name}_tab_close_shutdown.txt"), "w") as f:
                            f.write(f"Shutdown triggered by tab close at {time.ctime()}\\n")
                    except:
                        pass
                    
                    # Force terminate the process
                    logger.info("Force terminating the process from tab close...")
                    cleanup()
                    os._exit(0)  # Use os._exit to ensure immediate termination
                
                threading.Thread(target=delayed_shutdown).start()
                return
                
            return super().do_GET()
        except Exception as e:
            logger.error(f"Error handling GET request: {{e}}")
            logger.error(traceback.format_exc())
            try:
                self.send_error(500, str(e))
            except:
                logger.error("Could not send error response")
    
    def do_POST(self):
        try:
            global shutdown_in_progress
            if self.path == '/exit' or self.path.startswith('/exit'):
                # Check if shutdown already in progress
                if shutdown_in_progress:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Shutdown already in progress...')
                    return
                
                # Mark shutdown as in progress
                shutdown_in_progress = True
                
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Shutting down server...')
                
                # Log the exit request
                request_source = "tab close (sendBeacon)" if 'Content-Type' in self.headers and 'text/plain' in self.headers['Content-Type'] else "exit button"
                logger.info(f"Exit request received from {{request_source}}. Shutting down...")
                with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                    f.write(f"Exit request received from {{request_source}} at {{time.ctime()}}\\n")
                
                # Shutdown in separate thread
                def delayed_shutdown():
                    time.sleep(0.5)  # Give the browser time to receive the response
                    
                    # Create a file to indicate successful shutdown trigger
                    try:
                        with open(os.path.expanduser(f"~/Desktop/{app_name}_shutdown_triggered.txt"), "w") as f:
                            f.write(f"Shutdown triggered at {{time.ctime()}}\\n")
                    except:
                        pass
                    
                    # Force terminate the process
                    logger.info("Force terminating the process...")
                    cleanup()
                    os._exit(0)  # Use os._exit to ensure immediate termination
                
                threading.Thread(target=delayed_shutdown).start()
                return
            
            self.send_response(405)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Method not allowed')
        except Exception as e:
            logger.error(f"Error handling POST request: {{e}}")
            logger.error(traceback.format_exc())
            try:
                self.send_error(500, str(e))
            except:
                logger.error("Could not send error response")

def main():
    try:
        # Set up dock icon if available
        if 'dock_handler' in sys.modules:
            try:
                logger.info("Setting up dock icon...")
                with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                    f.write(f"Setting up dock icon...\\n")
                dock_setup_result = dock_handler.setup_dock_icon()
                logger.info(f"Dock icon setup result: {{dock_setup_result}}")
                with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                    f.write(f"Dock icon setup result: {{dock_setup_result}}\\n")
            except Exception as e:
                logger.error(f"Error setting up dock icon: {{e}}")
                logger.error(traceback.format_exc())
                with open(os.path.expanduser(f"~/Desktop/{app_name}_debug.log"), "a") as f:
                    f.write(f"Error setting up dock icon: {{e}}\\n")
                    f.write(traceback.format_exc() + "\\n")
        
        # Check if already running
        if is_port_in_use():
            logger.info(f"Server is already running on port {{PORT}}")
            open_browser()
            return
        
        # Save PID to file
        try:
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.warning(f"Could not create PID file: {{e}}")
        
        # Start server
        try:
            # Use the custom HTTP server that supports proper shutdown
            ShutdownHTTPServer.allow_reuse_address = True
            with ShutdownHTTPServer(("localhost", PORT), RequestHandler) as httpd:
                logger.info(f"Server started at http://localhost:{{PORT}}")
                
                # Open browser after server has a chance to start up
                threading.Thread(target=lambda: (time.sleep(1.0), open_browser())).start()
                
                # Serve forever
                httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {{e}}")
            logger.error(traceback.format_exc())
        
        # Clean up
        cleanup()
        
    except Exception as e:
        logger.error(f"Critical error: {{e}}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Create a startup log to debug
    with open(os.path.expanduser(f"~/Desktop/{app_name}_startup.log"), "w") as f:
        f.write(f"Starting {app_name} at {{time.ctime()}}\\n")
        f.write(f"Python path: {{sys.executable}}\\n")
        f.write(f"Args: {{sys.argv}}\\n")
        f.flush()
        
    try:
        main()
    except Exception as e:
        with open(os.path.expanduser(f"~/Desktop/{app_name}_error.log"), "w") as f:
            f.write(f"Error starting {app_name}: {{str(e)}}\\n")
            f.write(traceback.format_exc())
"""
    
    return script

def create_spec_file(app_name, app_name_lower, script_path, temp_dir, icon_path_str):
    # Create the PyInstaller spec file.
    return f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Get the directory containing the script file
script_dir = os.path.dirname(os.path.abspath(r'{script_path}'))
current_dir = os.path.abspath(r'{temp_dir}')

# Add the dock_handler and other modules to the datas
datas = []

# Add dock_handler.py - this is critical for the dock icon to work
dock_handler_path = os.path.join(current_dir, 'dock_handler.py')
if os.path.exists(dock_handler_path):
    datas.append((dock_handler_path, '.'))
else:
    print("WARNING: dock_handler.py not found for bundling!")

# For debugging, list all files that will be included
print("\\nFiles included as data:")
for src, dest in datas:
    print(f"  {{src}} -> {{dest}}")
print()

a = Analysis(
    [r'{script_path}'],
    pathex=[current_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # macOS specific modules
        'AppKit', 
        'Foundation', 
        'objc', 
        'PyObjCTools', 
        'PyObjCTools.AppHelper',
        
        # Standard library modules
        'http.server',
        'socketserver',
        'webbrowser',
        'logging',
        'logging.handlers',
        'threading',
        'socket',
        'tempfile',
        'atexit',
        'signal',
        'urllib.request',
        'traceback',
        're',
        'os',
        'sys',
        'time',
        'shutil',
        'subprocess',
        
        # Local modules - critical for functionality
        'dock_handler'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_path_str}
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{app_name}',
)

app = BUNDLE(
    coll,
    name='{app_name}.app',
    {icon_path_str}
    bundle_identifier='com.example.{app_name_lower}',
    info_plist={{
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDocumentTypes': [{{
            'CFBundleTypeName': 'HTML',
            'CFBundleTypeRole': 'Viewer',
            'LSHandlerRank': 'Owner',
            'LSItemContentTypes': ['public.html'],
        }}],
        'LSUIElement': 0,
        'NSHighResolutionCapable': True,
        'CFBundleName': '{app_name}',
        'CFBundleDisplayName': '{app_name}',
        'CFBundleVersion': '1.0',
        'NSRequiresAquaSystemAppearance': False,
        'NSAppTransportSecurity': {{
            'NSAllowsLocalNetworking': True,
        }},
        'NSSupportsSuddenTermination': True,
    }},
)
"""