import argparse
import base64
import os
import socket
import subprocess
import webbrowser
from pathlib import Path

# Template for the server script
HTML_TEMPLATE = '''
import http.server
import socketserver
import base64
import threading
import os
import webbrowser
import traceback
import subprocess
import socket
import time

PORT = {port_num}

html_data = base64.b64decode("""{html_data}""").decode('utf-8')

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to log to console even in no-console mode
        print(format % args)

    def do_GET(self):
        print("Received GET request for: " + self.path)
        if self.path == '/' or self.path == '' or self.path == '/index.html':
            try:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Content-Length', str(len(html_data.encode('utf-8'))))
                self.end_headers()
                self.wfile.write(html_data.encode('utf-8'))
                print("Successfully served HTML content")
            except Exception as e:
                print("Error serving HTML: " + str(e))
                with open("error.log", "a") as log:
                    log.write("Error serving HTML: " + str(e) + "\\n" + traceback.format_exc() + "\\n")
        elif self.path == '/shutdown-msg':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h2>You can now close this window.</h2></body></html>")
        else:
            print("Path not found: " + self.path)
            self.send_error(404)

    def do_POST(self):
        if self.path == '/exit':
            self.send_response(200)
            self.end_headers()
            threading.Thread(target=shutdown).start()
        else:
            self.send_error(404)

def shutdown():
    print('Shutting down server...')
    os._exit(0)

# Global flag to indicate server is ready
server_ready = threading.Event()

def open_browser():
    # Wait for server to be ready before opening browser
    if server_ready.wait(timeout=10):  # Wait up to 10 seconds
        print("Server is ready, opening browser...")
        # Add a small delay to ensure socket is fully ready
        time.sleep(0.5)
        try:
            webbrowser.open("http://localhost:" + str(PORT))
            print("Browser opened successfully")
        except Exception as e:
            print("Error opening browser: " + str(e))
    else:
        print("Timeout waiting for server to start")

def is_port_responsive(port):
    """Test if the port is not just open but responding to HTTP requests."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(("localhost", port))
            # Send a simple HTTP request
            s.sendall(b"GET / HTTP/1.1\\r\\nHost: localhost\\r\\n\\r\\n")
            # Read a bit of the response to confirm the server is responsive
            response = s.recv(1024)
            return bool(response)
    except:
        return False

if __name__ == '__main__':
    try:
        # Check if port is already in use
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(("localhost", PORT))
            if result == 0:
                print("Port " + str(PORT) + " is already in use. Opening browser to the existing server.")
                
                # Test if the server is responding
                if is_port_responsive(PORT):
                    # If the port is actually responding, open the browser to it
                    webbrowser.open("http://localhost:" + str(PORT))
                    print("Browser opened to existing server")
                    os._exit(0)
                else:
                    print("Port is in use but not responding properly. Will try to start our own server.")
        
        print("Starting server on http://localhost:" + str(PORT))
        
        # Allow socket reuse to avoid "address already in use" errors
        socketserver.TCPServer.allow_reuse_address = True
        
        # Start browser opening in a separate thread
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Custom TCPServer that sets ready flag when it starts
        class ReadyTCPServer(socketserver.TCPServer):
            def server_bind(self):
                socketserver.TCPServer.server_bind(self)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Signal that the server is ready to accept connections
                print("Server socket bound, setting ready flag")
                server_ready.set()
                
        # Create and start server
        with ReadyTCPServer(("localhost", PORT), Handler) as httpd:
            print("Server created, starting to serve on port " + str(PORT))
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("Server stopped by keyboard interrupt")
            except Exception as e:
                print("Server error: " + str(e))
                with open("error.log", "w") as log:
                    log.write("Server error: " + str(e) + "\\n" + traceback.format_exc())
                subprocess.Popen(['notepad.exe', 'error.log'])
    except Exception as e:
        print("Startup error: " + str(e))
        with open("error.log", "w") as log:
            log.write("Startup error: " + str(e) + "\\n" + traceback.format_exc())
        subprocess.Popen(['notepad.exe', 'error.log'])
'''

def inject_exit_button(html: str) -> str:
    button_html = '''\n<button onclick="fetch('/exit', {method: 'POST'}).then(() => window.location.href='/shutdown-msg')" style="position: fixed; bottom: 10px; right: 10px; z-index: 9999;">Exit Server</button>\n'''
    if '</body>' in html:
        return html.replace('</body>', button_html + '</body>')
    return html + button_html

def is_port_in_use(port):
    """Check if a port is in use by attempting to connect to it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        result = s.connect_ex(('localhost', port))
        return result == 0

def main():
    parser = argparse.ArgumentParser(description="Create Windows EXE that serves local HTML page.")
    parser.add_argument('--html', required=True, help='HTML file to embed')
    parser.add_argument('--exec', help='Output .exe filename')
    parser.add_argument('--port', type=int, default=8000, help='Port to serve on')
    parser.add_argument('--icon', help='Path to .ico file for the EXE icon')
    args = parser.parse_args()

    html_path = Path(args.html)
    if not html_path.exists():
        print("HTML file does not exist.")
        return

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    html = inject_exit_button(html)
    encoded_html = base64.b64encode(html.encode('utf-8')).decode('utf-8')

    script_name = html_path.stem + '_pc.py'
    with open(script_name, 'w', encoding='utf-8') as f:
        f.write(HTML_TEMPLATE.format(port_num=args.port, html_data=encoded_html))

    out_exe = args.exec if args.exec else html_path.stem + '.exe'

    pyinstaller_cmd = [
        'pyinstaller',
        '--onefile',
        '--noconsole',
    ]
    if args.icon:
        pyinstaller_cmd.append(f'--icon={args.icon}')
    pyinstaller_cmd.append(script_name)

    subprocess.run(pyinstaller_cmd, check=True)

    dist_exe = Path('dist') / Path(script_name).with_suffix('.exe').name
    final_path = Path(out_exe)

    if dist_exe.exists():
        if final_path.exists():
            try:
                final_path.unlink()
            except Exception as e:
                print(f"Failed to remove existing file '{final_path}': {e}")
                return
        dist_exe.replace(final_path)
        print(f'Executable created: {final_path}')
    else:
        print('Executable not found in dist/. Check PyInstaller logs.')

if __name__ == '__main__':
    main()