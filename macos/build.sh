#!/bin/bash

set -e

APP_NAME="MyPointCards"
APP_FILE="${APP_NAME}.app"
HTML_FILE="../mypointcards-v1.html"
ICON_FILE="AppIcon.icns"
DMG_FILE="${APP_NAME}-1.0.dmg"

echo "🔧 Setting up Python virtual environment..."
python3 -m venv venv > /dev/null 2>&1
source venv/bin/activate

echo "🚀 Building macOS app bundle..."
./main.py --html "$HTML_FILE" --name "$APP_NAME" --icon "$ICON_FILE" > /dev/null

echo "📦 Creating DMG installer..."
./make_dmg.py --app "$APP_FILE" --output "$DMG_FILE" > /dev/null

if [ -f "$DMG_FILE" ]; then
    echo "✅ DMG created: $DMG_FILE"
else
    echo "❌ DMG creation failed"
    exit 1
fi

echo "📁 Final app bundle:"
ls -l "$APP_FILE/Contents" | grep -vE '^total' || true

