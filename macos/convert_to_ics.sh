#!/bin/bash
# convert_to_icns.sh

ICON_DIR="../assets/icons"
DEFAULT_ICON="$ICON_DIR/android-chrome-512x512.png"
FALLBACK_ICON="$ICON_DIR/android-chrome-192x192.png"

# Accept optional icon name
ICON_NAME=${1:-AppIcon}

# Determine source file
if [ -f "$DEFAULT_ICON" ]; then
    INPUT_FILE="$DEFAULT_ICON"
elif [ -f "$FALLBACK_ICON" ]; then
    INPUT_FILE="$FALLBACK_ICON"
else
    echo "No suitable source icon found in $ICON_DIR"
    exit 1
fi

echo "Using source: $INPUT_FILE"
ICONSET_DIR="${ICON_NAME}.iconset"

mkdir -p "$ICONSET_DIR"

# Generate all required sizes
sips -z 16 16     "$INPUT_FILE" --out "$ICONSET_DIR/icon_16x16.png"
sips -z 32 32     "$INPUT_FILE" --out "$ICONSET_DIR/icon_16x16@2x.png"
sips -z 32 32     "$INPUT_FILE" --out "$ICONSET_DIR/icon_32x32.png"
sips -z 64 64     "$INPUT_FILE" --out "$ICONSET_DIR/icon_32x32@2x.png"
sips -z 128 128   "$INPUT_FILE" --out "$ICONSET_DIR/icon_128x128.png"
sips -z 256 256   "$INPUT_FILE" --out "$ICONSET_DIR/icon_128x128@2x.png"
sips -z 256 256   "$INPUT_FILE" --out "$ICONSET_DIR/icon_256x256.png"
sips -z 512 512   "$INPUT_FILE" --out "$ICONSET_DIR/icon_256x256@2x.png"
sips -z 512 512   "$INPUT_FILE" --out "$ICONSET_DIR/icon_512x512.png"
sips -z 1024 1024 "$INPUT_FILE" --out "$ICONSET_DIR/icon_512x512@2x.png"

# Convert to .icns
iconutil -c icns "$ICONSET_DIR"

# Cleanup
rm -rf "$ICONSET_DIR"

echo "✅ Icon created: ${ICON_NAME}.icns"

