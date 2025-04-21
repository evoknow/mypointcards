#!/usr/bin/env python3
"""
make_dmg.py - Create a DMG distribution file for a macOS application

Usage:
    python make_dmg.py --app <path_to_app>

Options:
    --app <path>      Path to the .app bundle to package
    --output <path>   Output DMG filename (default: derived from app name)
    --volume-name <name>  Volume name for the DMG (default: derived from app name)
    --background <path>   Path to background image for the DMG
    --window-size <w,h>   Window size in pixels (default: 640,480)
    --icon-size <size>    Icon size in pixels (default: 128)
    --position <x,y>      Position of the app icon (default: 150,180)
    --applications-position <x,y>  Position of the Applications symlink (default: 480,180)
    --quiet              Suppress output messages
    --help               Show this help message
"""

import argparse
import os
import subprocess
import tempfile
import shutil
import plistlib
import sys
import time
from pathlib import Path


def run_command(cmd, quiet=False):
    """Run a shell command and return its output"""
    if not quiet:
        print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            check=True
        )
        if not quiet and result.stdout:
            print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def get_app_info(app_path):
    """Extract information from the app's Info.plist"""
    try:
        info_plist_path = os.path.join(app_path, "Contents", "Info.plist")
        with open(info_plist_path, 'rb') as f:
            info = plistlib.load(f)
        
        app_name = info.get('CFBundleName', os.path.basename(app_path).replace('.app', ''))
        app_version = info.get('CFBundleShortVersionString', '1.0')
        return app_name, app_version
    except Exception as e:
        print(f"Error reading app info: {e}")
        app_name = os.path.basename(app_path).replace('.app', '')
        return app_name, "1.0"


def create_dmg_ds_store(settings):
    """Create a DS_Store file with the specified settings"""
    applescript = f"""
    tell application "Finder"
        set mountPoint to POSIX file "{settings['temp_mount_point']}" as string
        tell disk mountPoint
            open
            set current view of container window to icon view
            set toolbar visible of container window to false
            set statusbar visible of container window to false
            set the bounds of container window to {{{settings['window_rect'][0]}, {settings['window_rect'][1]}, {settings['window_rect'][2]}, {settings['window_rect'][3]}}}
            set theViewOptions to the icon view options of container window
            set arrangement of theViewOptions to not arranged
            set icon size of theViewOptions to {settings['icon_size']}
            set background picture of theViewOptions to file ".background:{os.path.basename(settings['background_file'])}"
            
            -- Create position list
            make new alias file at container window to POSIX file "/Applications" with properties {{name:"Applications", position:{{{settings['applications_position'][0]}, {settings['applications_position'][1]}}}}}
            set position of item "{os.path.basename(settings['app_path'])}" of container window to {{{settings['app_position'][0]}, {settings['app_position'][1]}}}
            
            close
            open
            update without registering applications
            delay 5
            close
        end tell
        delay 5
    end tell
    """
    
    # Save the AppleScript to a temporary file
    script_file = os.path.join(tempfile.gettempdir(), "dmg_ds_store.scpt")
    with open(script_file, 'w') as f:
        f.write(applescript)
    
    # Run the AppleScript
    os.system(f"osascript {script_file}")
    os.unlink(script_file)


def make_dmg(args):
    """Create a DMG file for the specified application"""
    # Validate app path
    if not os.path.exists(args.app):
        print(f"Error: App not found at {args.app}")
        return 1
    
    if not os.path.isdir(args.app) or not args.app.endswith('.app'):
        print(f"Error: {args.app} is not a valid .app bundle")
        return 1
    
    # Get app information
    app_name, app_version = get_app_info(args.app)
    
    # Set up default values
    volume_name = args.volume_name or f"{app_name} {app_version}"
    output_dmg = args.output or f"{app_name}-{app_version}.dmg"
    
    print(f"Packaging {app_name} (version {app_version})...")
    
    # Create a temporary directory to hold contents
    temp_dir = os.path.join(tempfile.gettempdir(), f"dmg_contents_{int(time.time())}")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Copy the app to the temporary directory
        temp_app_path = os.path.join(temp_dir, os.path.basename(args.app))
        print(f"Copying {args.app} to temporary location...")
        shutil.copytree(args.app, temp_app_path)
        
        # Create a symlink to Applications in the temporary directory
        print("Creating Applications folder symlink...")
        os.symlink("/Applications", os.path.join(temp_dir, "Applications"))
        
        # If background image is provided, create a .background directory
        if args.background and os.path.exists(args.background):
            background_dir = os.path.join(temp_dir, ".background")
            os.makedirs(background_dir, exist_ok=True)
            shutil.copy2(args.background, os.path.join(background_dir, os.path.basename(args.background)))
        
        # Create the DMG directly from the temporary directory
        print("Creating DMG...")
        if os.path.exists(output_dmg):
            os.unlink(output_dmg)
            
        # Create temporary DMG first with standard format
        temp_dmg = os.path.join(tempfile.gettempdir(), f"temp_{app_name}.dmg")
        if os.path.exists(temp_dmg):
            os.unlink(temp_dmg)
            
        # Create DMG directly from the temporary folder
        run_command([
            "hdiutil", "create",
            "-srcfolder", temp_dir,
            "-volname", volume_name,
            "-format", "UDRW",
            temp_dmg
        ], args.quiet)
        
        # Mount the temporary DMG to configure it (if background image is provided)
        if args.background and os.path.exists(args.background):
            print("Mounting DMG to configure appearance...")
            device = run_command([
                "hdiutil", "attach",
                "-readwrite",
                "-noverify",
                "-noautoopen",
                temp_dmg
            ], args.quiet).strip().split('\n')[-1].split('\t')[0].strip()
            
            mount_point = f"/Volumes/{volume_name}"
            
            # Parse window size into dimensions
            window_size = [int(x) for x in args.window_size.split(',')]
            
            # Set up the DS_Store settings
            settings = {
                'temp_mount_point': mount_point,
                'window_rect': [0, 0, window_size[0], window_size[1]],
                'icon_size': args.icon_size,
                'background_file': os.path.join(mount_point, ".background", os.path.basename(args.background)),
                'app_path': os.path.join(mount_point, os.path.basename(args.app)),
                'app_position': [int(x) for x in args.position.split(',')],
                'applications_position': [int(x) for x in args.applications_position.split(',')]
            }
            
            # Configure the DS_Store
            create_dmg_ds_store(settings)
            
            # Unmount
            print("Finalizing DMG...")
            run_command(["hdiutil", "detach", device], args.quiet)
        
        # Convert to compressed format
        run_command([
            "hdiutil", "convert",
            temp_dmg,
            "-format", "UDZO",
            "-imagekey", "zlib-level=9",
            "-o", output_dmg
        ], args.quiet)
        
        print(f"DMG created successfully: {output_dmg}")
        return 0
    
    except Exception as e:
        print(f"Error creating DMG: {e}")
        return 1
    finally:
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        temp_dmg = os.path.join(tempfile.gettempdir(), f"temp_{app_name}.dmg")
        if os.path.exists(temp_dmg):
            os.unlink(temp_dmg)


def main():
    parser = argparse.ArgumentParser(description='Create a DMG distribution for a macOS application')
    parser.add_argument('--app', required=True, help='Path to the .app bundle to package')
    parser.add_argument('--output', help='Output DMG filename (default: derived from app name)')
    parser.add_argument('--volume-name', help='Volume name for the DMG (default: derived from app name)')
    parser.add_argument('--background', help='Path to background image for the DMG')
    parser.add_argument('--window-size', default='640,480', help='Window size in pixels (default: 640,480)')
    parser.add_argument('--icon-size', type=int, default=128, help='Icon size in pixels (default: 128)')
    parser.add_argument('--position', default='150,180', help='Position of the app icon (default: 150,180)')
    parser.add_argument('--applications-position', default='480,180', 
                        help='Position of the Applications symlink (default: 480,180)')
    parser.add_argument('--quiet', action='store_true', help='Suppress output messages')
    
    args = parser.parse_args()
    return make_dmg(args)


if __name__ == "__main__":
    sys.exit(main())
