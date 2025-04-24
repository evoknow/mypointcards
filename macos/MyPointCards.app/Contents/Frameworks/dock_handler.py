# Ultra-minimal dock handler with better process handling
import os
import sys
import threading
import time
import subprocess
import socket
import logging

# Simple console logging only
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dock_handler")

# Global variables - absolute minimum
_dock_icon_setup_complete = False

def is_port_in_use(port=8000):
    """Check if server port is in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    except Exception as e:
        logger.error(f"Error checking port: {e}")
        return False

def open_browser():
    """Open browser with direct command, no lock files."""
    logger.info("Opening browser")
    
    # Check if server is running first
    if not is_port_in_use(8000):
        logger.info("Server not running, cannot open browser")
        return
    
    # Just use direct subprocess call - simplest approach
    try:
        subprocess.run(['open', 'http://localhost:8000/'], 
                      check=False,
                      timeout=2)
    except Exception as e:
        logger.error(f"Error opening browser: {e}")

def setup_dock_icon():
    """Ultra-minimal dock icon setup with instance checking."""
    global _dock_icon_setup_complete
    
    # Only run on macOS
    if sys.platform != 'darwin':
        return False
    
    try:
        # Import required frameworks
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyRegular
            from Foundation import NSObject
            import objc
        except ImportError:
            return False
        
        # Simple delegate with just the essential method
        class AppDelegate(NSObject):
            def init(self):
                self = objc.super(AppDelegate, self).init()
                return self
            
            # Dock icon click handler
            def applicationShouldHandleReopen_hasVisibleWindows_(self, sender, flag):
                open_browser()
                return True
        
        # Basic app setup
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        
        # Set delegate
        delegate = AppDelegate.alloc().init()
        app.setDelegate_(delegate)
        
        # Simple event thread
        def run_events():
            from AppKit import NSDate
            from Foundation import NSRunLoop
            
            app.finishLaunching()
            
            # Basic event loop
            while True:
                try:
                    NSRunLoop.currentRunLoop().runUntilDate_(
                        NSDate.dateWithTimeIntervalSinceNow_(0.1)
                    )
                    time.sleep(0.05)
                except:
                    time.sleep(0.1)
        
        # Start event thread
        thread = threading.Thread(target=run_events)
        thread.daemon = True
        thread.start()
        
        _dock_icon_setup_complete = True
        return True
    
    except Exception:
        return False

def check_dock_status():
    """Minimal status check."""
    return {
        "setup_complete": _dock_icon_setup_complete
    }