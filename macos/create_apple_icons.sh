#!/bin/bash

ASSET_DIR=../assets
ICON_DIR=$ASSET_DIR/icons
TOOL=magick

# Generate standard favicon sizes
$TOOL $ASSET_DIR/logo.png -resize 16x16 $ICON_DIR/favicon-16x16.png
$TOOL $ASSET_DIR/logo.png -resize 32x32 $ICON_DIR/favicon-32x32.png
$TOOL $ASSET_DIR/logo.png -resize 48x48 $ICON_DIR/favicon-48x48.png

# Generate iOS icons
$TOOL $ASSET_DIR/logo.png -resize 57x57 $ICON_DIR/apple-touch-icon-57x57.png
$TOOL $ASSET_DIR/logo.png -resize 60x60 $ICON_DIR/apple-touch-icon-60x60.png
$TOOL $ASSET_DIR/logo.png -resize 72x72 $ICON_DIR/apple-touch-icon-72x72.png
$TOOL $ASSET_DIR/logo.png -resize 76x76 $ICON_DIR/apple-touch-icon-76x76.png
$TOOL $ASSET_DIR/logo.png -resize 114x114 $ICON_DIR/apple-touch-icon-114x114.png
$TOOL $ASSET_DIR/logo.png -resize 120x120 $ICON_DIR/apple-touch-icon-120x120.png
$TOOL $ASSET_DIR/logo.png -resize 144x144 $ICON_DIR/apple-touch-icon-144x144.png
$TOOL $ASSET_DIR/logo.png -resize 152x152 $ICON_DIR/apple-touch-icon-152x152.png
$TOOL $ASSET_DIR/logo.png -resize 180x180 $ICON_DIR/apple-touch-icon-180x180.png
$TOOL $ASSET_DIR/logo.png -resize 180x180 $ICON_DIR/apple-touch-icon.png

# Generate standard Android icons
$TOOL $ASSET_DIR/logo.png -resize 192x192 $ICON_DIR/android-chrome-192x192.png
$TOOL $ASSET_DIR/logo.png -resize 512x512 $ICON_DIR/android-chrome-512x512.png

# Create favicon.ico with multiple sizes in one file
$TOOL $ASSET_DIR/logo.png -define icon:auto-resize=16,32,48 $ICON_DIR/favicon.ico
