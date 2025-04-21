
# MyPointCards for Windows

This project builds a standalone Windows `.exe` version of MyPointCards, which serves a local HTML file using a built-in Python web server and launches it in the default browser.

---

## 🛠 Prerequisites

Before building, make sure your environment includes:

- **Python 3.8+ for Windows**
- **Pip** installed (`python -m ensurepip`)
- **PyInstaller**
  ```bash
  pip install pyinstaller
  ```

---

## 📂 Folder Structure

Your project should look like this:

```
/windows
  ├── build.bat              # Script to create the EXE
  ├── make_windows_exe.py    # Converts HTML to a background server EXE
/assets
  └── logo.png               # Your base app logo
/mypointcards-v1.html        # HTML content to bundle
```

---

## 🚀 How to Build

1. **Edit** `mypointcards-v1.html` with your app content  
2. **Run** the build script:

```cmd
build.bat
```

This will:
- Kill any running instance of the app
- Delete the old `.exe`
- Embed your HTML
- Build a new `MyPointCards.exe` with icon

---

## 🧪 How It Works

- The `.exe` starts a background server on `localhost:8000`
- It opens the browser to show your app
- Includes a floating **"Exit Server"** button to shut down cleanly

---

## 📄 Output

You will get a portable EXE:

```
MyPointCards.exe
```

---

## 🧹 Cleanup

To remove previous builds:

```cmd
rmdir /s /q __pycache__
rmdir /s /q build
rmdir /s /q dist
del *.spec
del *_pc.py
```

---

## ❓ Troubleshooting

- Ensure no other app is using **port 8000**
- Check `error.log` if the EXE fails to start
- If build fails, try running `make_windows_exe.py` directly with:

```bash
python make_windows_exe.py --html ../mypointcards-v1.html --exec MyPointCards.exe --port 8000 --icon pc.ico
```

---

## 🔐 Notes

- This app runs fully **offline**
- No dependencies are required after build


