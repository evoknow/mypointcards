"""
HTTP server implementation for the macOS app with improved browser opening and dock icon handling.
"""

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
from functools import lru_cache

logger = logging.getLogger("server")

# Configuration
PORT = 8000
BROWSER_LOCK_FILE = os.path.expanduser("~/Desktop/.browser_lock")

def setup_logging(app_name):
    """Set up logging for the server."""
    try:
        log_dir = os.path.expanduser(f"~/Library/Logs/{app_name}")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{app_name.lower()}.log")

        # Use INFO level for more detailed logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        logger.info(f"Logging initialized for {app_name}")
    except Exception as e:
        # Fallback logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        logger.warning(f"Using console logging only: {e}")

# Check if port is already in use
def is_port_in_use():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', PORT)) == 0
    except Exception as e:
        logger.error(f"Error checking port: {e}")
        return False

# Wait for server to be ready
def wait_for_server_ready():
    """Wait until server is ready to accept connections."""
    max_attempts = 10
    for i in range(max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', PORT)) == 0:
                    logger.info(f"Server ready after {i+1} attempts")
                    return True
        except:
            pass
        time.sleep(0.1)
    logger.warning("Server failed to be ready in expected time")
    return False

# Open browser with direct method
def open_browser():
    """Open browser directly without using lock files."""
    # No lock file checking - just open browser directly
    try:
        logger.info("Opening browser directly...")
        # Use direct subprocess call - simplest approach
        subprocess.run(
            ['open', f'http://localhost:{PORT}/'],
            check=False,
            capture_output=True,
            timeout=2
        )
    except Exception as e:
        logger.error(f"Error opening browser: {e}")
        # Try alternate methods if main one fails
        try:
            os.system(f'open http://localhost:{PORT}/')
            logger.info("Used os.system fallback")
        except:
            logger.error("All browser opening methods failed")

# Exit button script that gets injected into the HTML
EXIT_BUTTON_SCRIPT = """
<style>
#exit-app-button {
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
}
#exit-app-button:hover {
    background-color: #d32f2f;
}
.exit-confirmation {
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
}
.exit-confirmation-box {
    background-color: white;
    padding: 20px;
    border-radius: 5px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    max-width: 90%;
    width: 400px;
}
.exit-confirmation-buttons {
    margin-top: 20px;
}
.exit-confirmation-buttons button {
    padding: 8px 16px;
    margin: 0 10px;
    border-radius: 4px;
    border: none;
    cursor: pointer;
}
.exit-cancel {
    background-color: #e0e0e0;
}
.exit-confirm {
    background-color: #f44336;
    color: white;
}
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
(function() {
    // Exit button click handler
    document.getElementById('exit-app-button').addEventListener('click', function() {
        document.getElementById('exit-confirmation').style.display = 'flex';
    });
    
    // Cancel exit
    document.getElementById('exit-cancel').addEventListener('click', function() {
        document.getElementById('exit-confirmation').style.display = 'none';
    });
    
    // Confirm exit
    document.getElementById('exit-confirm').addEventListener('click', function() {
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
        fetch('/exit', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Exit-Requested-By': 'user-interface'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Server responded with an error');
            }
            document.body.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;"><h1>Server shutdown. You can close this window.</h1></div>';
        })
        .catch(err => {
            alert('Error shutting down: ' + err);
        });
    });
    
    // Set up the tab close/refresh detector
    window.addEventListener('beforeunload', function(e) {
        // Add server shutdown call when tab is closed or refreshed
        const exitBeacon = new Image();
        exitBeacon.src = '/exit?auto_close=true&t=' + new Date().getTime();
        
        // Use fetch with keepalive to ensure the request completes
        // even if the page is being unloaded
        navigator.sendBeacon('/exit', JSON.stringify({
            reason: 'tab_closed',
            timestamp: new Date().toISOString()
        }));
        
        // No need to show a confirmation dialog since the app will simply restart
        // We just return undefined to proceed with the close without a confirmation
        return undefined;
    });
})();
</script>
"""

class ServerHandler:
    """Handles HTTP server operations."""
    
    def __init__(self, app_name, html_content):
        self.app_name = app_name
        self.html_content = html_content
        self.pid_file = os.path.join(tempfile.gettempdir(), f"{app_name.lower()}.pid")
        self.shutdown_in_progress = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Register cleanup function
        atexit.register(self.cleanup)
    
    def cleanup(self):
        """Remove PID file on exit."""
        if os.path.exists(self.pid_file):
            try:
                os.unlink(self.pid_file)
                logger.info("Removed PID file")
            except Exception as e:
                logger.error(f"Error removing PID file: {e}")
    
    def signal_handler(self, sig, frame):
        """Handle signals."""
        logger.info("Shutting down server...")
        self.cleanup()
        sys.exit(0)
    
    @lru_cache(maxsize=1)
    def get_modified_html(self):
        """Get the modified HTML content with exit button (cached)."""
        html_content = self.html_content
        
        # Always inject exit button before </body>
        if "</body>" in html_content:
            return html_content.replace("</body>", EXIT_BUTTON_SCRIPT + "</body>")
        else:
            return html_content + EXIT_BUTTON_SCRIPT
    
    # Custom HTTP request handler
    class RequestHandler(http.server.SimpleHTTPRequestHandler):
        html_content = None  # Set by outer class
        server_handler = None  # Set by outer class
        
        def log_message(self, format, *args):
            logger.info(format % args)
        
        def do_GET(self):
            try:
                if self.path == '/':
                    # Get the HTML content and inject exit button if not already present
                    modified_content = self.server_handler.get_modified_html()
                    
                    # Send the modified content
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(modified_content.encode('utf-8'))
                    return
                elif self.path == '/open':
                    # Simplified endpoint for browser opening
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Browser open request received')
                    
                    # Open browser directly without using lock files
                    open_browser()
                    return
                elif self.path == '/ping':
                    # Simple endpoint to check if server is running
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'pong')
                    return
                elif self.path == '/status':
                    # Simple status endpoint
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    
                    status = {
                        "server": "running",
                        "time": time.ctime()
                    }
                    
                    self.wfile.write(str(status).encode('utf-8'))
                    return
                elif self.path.startswith('/exit') and 'auto_close=true' in self.path:
                    # Handle beacon request from beforeunload event
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Shutting down from tab close')
                    
                    # Log the tab close request
                    logger.info("Tab close request received. Shutting down...")
                    
                    # Shutdown in separate thread
                    def delayed_shutdown():
                        time.sleep(0.5)  # Give the browser time to process
                        
                        # Create a file to indicate successful shutdown trigger
                        try:
                            with open(os.path.expanduser(f"~/Desktop/{self.server_handler.app_name}_tab_close_shutdown.txt"), "w") as f:
                                f.write(f"Shutdown triggered by tab close at {time.ctime()}\n")
                        except:
                            pass
                        
                        # Use the outer class's signal handler
                        self.server_handler.signal_handler(signal.SIGTERM, None)
                    
                    threading.Thread(target=delayed_shutdown).start()
                    return
                return super().do_GET()
            except Exception as e:
                logger.error(f"Error handling GET request: {e}")
                logger.error(traceback.format_exc())
                try:
                    self.send_error(500, str(e))
                except:
                    logger.error("Could not send error response")
        
        def do_POST(self):
            try:
                if self.path == '/exit' or self.path.startswith('/exit'):
                    # Check if shutdown already in progress
                    if self.server_handler.shutdown_in_progress:
                        self.send_response(200)
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(b'Shutdown already in progress...')
                        return
                    
                    # Mark shutdown as in progress
                    self.server_handler.shutdown_in_progress = True
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Shutting down server...')
                    
                    # Log the exit request
                    request_source = "tab close (sendBeacon)" if 'Content-Type' in self.headers and 'text/plain' in self.headers['Content-Type'] else "exit button"
                    logger.info(f"Exit request received from {request_source}. Shutting down...")
                    
                    # Shutdown in separate thread with a clear visible indicator
                    def delayed_shutdown():
                        time.sleep(0.5)
                        try:
                            with open(os.path.expanduser(f"~/Desktop/{self.server_handler.app_name}_shutdown_triggered.txt"), "w") as f:
                                f.write(f"Shutdown triggered at {time.ctime()}\n")
                        except:
                            pass
                        # Use the outer class's signal handler
                        self.server_handler.signal_handler(signal.SIGTERM, None)
                    
                    threading.Thread(target=delayed_shutdown).start()
                    return
                
                self.send_response(405)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Method not allowed')
            except Exception as e:
                logger.error(f"Error handling POST request: {e}")
                logger.error(traceback.format_exc())
                try:
                    self.send_error(500, str(e))
                except:
                    logger.error("Could not send error response")
    
    def start_server(self):
        """Start the HTTP server."""
        try:
            # Setup request handler
            handler_class = self.RequestHandler
            handler_class.html_content = self.html_content
            handler_class.server_handler = self  # Pass reference to outer class
            
            # Check if already running
            if is_port_in_use():
                logger.info(f"Server is already running on port {PORT}")
                # Open browser if server is already running
                open_browser()
                # Exit this instance gracefully
                logger.info("Exiting this instance since server is already running")
                sys.exit(0)
            
            # Save PID to file
            try:
                with open(self.pid_file, 'w') as f:
                    f.write(str(os.getpid()))
            except Exception as e:
                logger.warning(f"Could not create PID file: {e}")
            
            # Start server
            try:
                socketserver.TCPServer.allow_reuse_address = True
                httpd = socketserver.TCPServer(("localhost", PORT), handler_class)
                httpd.server_handler = self  # Pass reference to outer class
                
                logger.info(f"Server started at http://localhost:{PORT}")
                
                # Start the server in a separate thread
                server_thread = threading.Thread(target=httpd.serve_forever)
                server_thread.daemon = True
                server_thread.start()
                
                # Wait for server to be ready
                time.sleep(1.0)
                
                # Try to set up dock handler
                try:
                    import dock_handler
                    dock_handler.setup_dock_icon()
                except ImportError:
                    logger.warning("dock_handler module not available")
                except Exception as e:
                    logger.error(f"Error setting up dock handler: {e}")
                
                # Open browser after server is ready
                open_browser()
                
                # Keep the main thread alive
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Server stopped by user")
                finally:
                    httpd.shutdown()
            except KeyboardInterrupt:
                logger.info("Server stopped by user")
            except Exception as e:
                logger.error(f"Server error: {e}")
                logger.error(traceback.format_exc())
            
            # Clean up
            self.cleanup()
            
        except Exception as e:
            logger.error(f"Critical error: {e}")
            logger.error(traceback.format_exc())