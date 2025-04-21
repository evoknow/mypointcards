
# MyPoint Cards

**MyPoint Cards** is a single-page web application (`mypointcards-v1.html`) that can also run as a **local native desktop application** on macOS and Windows. Developers can generate native binaries that host the HTML content on a local server and automatically open the app in the default web browser.

---

## 🖥 Desktop Native Versions

Native binaries can be built using:

- macOS: [macos/README.macos.md](macos/README.macos.md)
- Windows: [windows/README.windows.md](windows/README.windows.md)

Both platforms compile the HTML app into a standalone binary that runs a local web server and launches the browser.

---

## ⚙️ Behavior

- The binary launches a server on `localhost:<port>` (default: `8000`)
- Automatically opens the default browser to show the app
- Includes a floating **“Exit Server”** button to stop the server
- Prevents multiple instances — re-clicking the app opens the browser to the already running server
- If the server is left running, users can always revisit the app at:
  
  ```
  http://localhost:<port>
  ```

---

## 🔢 Port Configuration

- Default port: `8000`
- To change the port, edit the `build` (macOS) or `build.bat` (Windows) file and set the desired port number
- Only one instance of the app can run on a given port

---

## 🧪 Manual Server Checks

### macOS:
Check if the server is running on port 8000:

```bash
lsof -i :8000
```

Kill the server manually (based on PID):

```bash
kill -9 <PID>
```

### Windows:
Check if the port is being used:

```cmd
netstat -aon | findstr :8000
```

Kill the process:

```cmd
taskkill /PID <PID> /F
```

Or, if the executable is named `MyPointCards.exe`:

```cmd
taskkill /f /im MyPointCards.exe
```

---

## 🔒 Disclaimer

- No data is sent to any remote server.
- The app only fetches **featured images** from:  
  `https://featured.mypoint.cards`
- No analytics, tracking, or remote communication is performed by the app itself.

---

## 🌐 External Resources Used

The app references public CDN resources:

- JavaScript libraries (e.g., jQuery, Bootstrap)
- CSS stylesheets
- Google Fonts
- Giphy API for animated media

These are loaded via public networks and hosted externally. Network access is required to load these assets unless embedded manually in the future.

---

## 📦 Distribution

- macOS users install via `.dmg` file
- Windows users run the generated `.exe` file
- App can be distributed offline and used entirely without internet access after first load (except for Giphy or CDN fallback)


