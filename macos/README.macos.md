
# MyPointCards for macOS

This project builds a macOS application bundle (`.app`) and DMG installer from a local HTML file and assets.

---

## 🛠 Prerequisites

- macOS with:
  - Python 3 installed
  - `sips` and `iconutil` (built-in on macOS)
  - `hdiutil` (for DMG creation, also built-in)

---

## 🚀 Build Steps

Follow these steps in order:

### 1. Generate App Icons

Run this to create all required icon sizes from the base logo:

```bash
./create_apple_icons.sh
```

This script generates multiple PNGs under `AppIcon.iconset/`.

---

### 2. Convert to `.icns`

Run this to convert the iconset into `AppIcon.icns`:

```bash
./convert_to_icns.sh AppIcon
```

This outputs:  
```
AppIcon.icns
```

---

### 3. Build the App & DMG

Finally, build the app and generate the `.dmg` installer:

```bash
./build
```

This creates:

- `MyPointCards.app` — macOS application bundle
- `MyPointCards-1.0.dmg` — installer for distribution

---

## 📁 Output Structure

```
MyPointCards.app/
└── Contents/
    ├── Info.plist
    ├── MacOS/
    │   └── MyPointCards
    └── Resources/
        ├── app.py
        ├── AppIcon.icns
        └── venv/
```

---

## 🧪 Behavior

- Launches in background (no dock icon)
- Runs a local server on port 8000
- Opens default browser to load your HTML
- Provides an “Exit Server” button
- Prevents multiple instances from running

---

## 🔄 Regenerate Anytime

To cleanly regenerate everything:

```bash
rm -rf AppIcon.iconset AppIcon.icns venv MyPointCards.app MyPointCards-1.0.dmg
./create_apple_icons.sh
./convert_to_icns.sh AppIcon
./build
```

---

## 📞 Need Help?

If any script fails, check file paths and permissions. All paths are relative to the `macos/` directory.

```
assets/logo.png       # Source logo
AppIcon.icns          # Final icon
mypointcards-v1.html  # App content
```

