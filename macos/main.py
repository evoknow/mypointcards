#!/usr/bin/env python3
"""
Main entry point for the macOS app builder.
Parses arguments and coordinates the build process.
"""

import os
import sys
import argparse
import platform
import logging
import traceback
import time

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("main")

# Global exception handler
def global_exception_handler(exctype, value, tb):
    error_msg = f"Uncaught exception: {exctype.__name__}: {value}"
    logger.error(error_msg)
    for line in traceback.format_tb(tb):
        logger.error(line.rstrip())
    
    # Also write to a desktop log for debugging
    try:
        with open(os.path.expanduser("~/Desktop/main_error.log"), "a") as f:
            f.write(f"\n--- Error at {time.ctime()} ---\n")
            f.write(error_msg + "\n")
            f.write(traceback.format_exc())
    except:
        pass

# Set the global exception handler
sys.excepthook = global_exception_handler

# Ensure path includes the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try importing modules with better error handling
def safe_import(module_name):
    try:
        module = __import__(module_name)
        logger.info(f"Successfully imported {module_name}")
        return module
    except ImportError as e:
        logger.error(f"Could not import {module_name}: {e}")
        try:
            with open(os.path.expanduser(f"~/Desktop/import_error_{module_name}.log"), "w") as f:
                f.write(f"Error importing {module_name} at {time.ctime()}:\n")
                f.write(str(e) + "\n")
                f.write(traceback.format_exc())
        except:
            pass
        return None

# Import other modules with proper error handling
html_handler = safe_import("html_handler")
dock_handler = safe_import("dock_handler")
server = safe_import("server")
app_builder = safe_import("app_builder")

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Create a simple macOS app")
    parser.add_argument("--name", required=True, help="Name of the app")
    parser.add_argument("--html", help="Path to custom HTML file")
    parser.add_argument("--icon", help="Path to ICNS icon file")
    
    args = parser.parse_args()
    
    # Log the startup and arguments
    logger.info(f"Starting app builder with name={args.name}, html={args.html}, icon={args.icon}")
    
    # Write debug info
    with open(os.path.expanduser(f"~/Desktop/main_debug.log"), "w") as f:
        f.write(f"Starting at {time.ctime()}\n")
        f.write(f"Python: {sys.executable} {sys.version}\n")
        f.write(f"Platform: {platform.system()} {platform.version()}\n")
        f.write(f"Current directory: {os.getcwd()}\n")
        f.write(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}\n")
        f.write(f"Arguments: name={args.name}, html={args.html}, icon={args.icon}\n")
    
    if platform.system() != "Darwin":
        logger.warning("This script is designed for macOS. It may not work correctly on other platforms.")
    
    # Check if all required modules were imported
    if not all([html_handler, dock_handler, server, app_builder]):
        logger.error("Could not import all required modules. Check the logs for details.")
        return 1
    
    try:
        # Build the app
        success = app_builder.build_app(args.name, args.html, args.icon)
        
        if success:
            logger.info(f"Successfully built {args.name}.app")
            return 0
        else:
            logger.error(f"Failed to build {args.name}.app")
            return 1
            
    except Exception as e:
        logger.error(f"Error building app: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Set up additional file logging
    try:
        log_file = os.path.expanduser("~/Desktop/main_app.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
        logging.getLogger().addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not set up file logging: {e}")
    
    # Run the main function
    sys.exit(main())