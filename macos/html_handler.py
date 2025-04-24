"""
HTML content handling for the macOS app.
Manages default HTML and exit button injection.
"""

import os
import logging

logger = logging.getLogger("html_handler")

def get_html_content(html_path=None):
    """Get HTML content either from a file or use default."""
    default_html = """<!DOCTYPE html>
<html>
<head>
    <title>Web App</title>
    <style>
    body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 20px;
    }
    #exit-app-button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #f44336;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        border: none;
        cursor: pointer;
        z-index: 9999;
    }
    #exit-app-button:hover {
        background-color: #d32f2f;
    }
    .exit-confirmation {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    }
    .exit-confirmation-box {
        background-color: white;
        padding: 20px;
        border-radius: 5px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    .exit-confirmation-buttons {
        margin-top: 20px;
    }
    .exit-confirmation-buttons button {
        padding: 8px 16px;
        margin: 0 10px;
        border-radius: 4px;
        border: none;
        cursor: pointer;
    }
    .exit-cancel {
        background-color: #e0e0e0;
    }
    .exit-confirm {
        background-color: #f44336;
        color: white;
    }
    </style>
</head>
<body>
    <h1>Web Server</h1>
    <p>Server is running.</p>
    <button id="exit-app-button">Exit App</button>
    
    <script>
    // Create the exit confirmation dialog
    const exitConfirmationHTML = `
        <div class="exit-confirmation" id="exit-confirmation" style="display: none;">
            <div class="exit-confirmation-box">
                <h2>Confirm Exit</h2>
                <p>Are you sure you want to exit the application?</p>
                <div class="exit-confirmation-buttons">
                    <button class="exit-cancel" id="exit-cancel">Cancel</button>
                    <button class="exit-confirm" id="exit-confirm">Exit</button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', exitConfirmationHTML);
    
    // Exit button handler with confirmation
    document.getElementById('exit-app-button').addEventListener('click', function() {
        document.getElementById('exit-confirmation').style.display = 'flex';
    });
    
    // Cancel exit
    document.getElementById('exit-cancel').addEventListener('click', function() {
        document.getElementById('exit-confirmation').style.display = 'none';
    });
    
    // Confirm exit
    document.getElementById('exit-confirm').addEventListener('click', function() {
        document.getElementById('exit-confirmation').style.display = 'none';
        
        // Show loading indicator
        const loadingHTML = `
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                        background-color: rgba(255,255,255,0.9); z-index: 10000;
                        display: flex; flex-direction: column; 
                        justify-content: center; align-items: center;">
                <h1>Shutting down...</h1>
                <p>Please wait while the application closes.</p>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', loadingHTML);
        
        // Send exit request to server
        fetch('/exit', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Exit-Requested-By': 'user-interface'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Server responded with an error');
            }
            document.body.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;"><h1>Server shutdown. You can close this window.</h1></div>';
        })
        .catch(err => {
            alert('Error shutting down: ' + err);
        });
    });
    
    // Set up the tab close/refresh detector
    window.addEventListener('beforeunload', function(e) {
        // Add server shutdown call when tab is closed or refreshed
        const exitBeacon = new Image();
        exitBeacon.src = '/exit?auto_close=true&t=' + new Date().getTime();
        
        // Use sendBeacon for more reliable shutdown when page unloads
        navigator.sendBeacon('/exit', JSON.stringify({
            reason: 'tab_closed',
            timestamp: new Date().toISOString()
        }));
        
        // No need to show a confirmation dialog
        return undefined;
    });
    
    // Function to detect iOS version (with properly escaped regex)
    function getIOSVersion() {
        if (/iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream) {
            const match = navigator.userAgent.match(/OS (\\d+)_(\\d+)_?(\\d+)?/);
            return match ? {
                major: parseInt(match[1], 10),
                minor: parseInt(match[2], 10),
                patch: parseInt(match[3] || 0, 10)
            } : null;
        }
        return null;
    }
    </script>
</body>
</html>"""

    # Read custom HTML content if provided
    html_content = default_html
    if html_path and os.path.exists(html_path):
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            logger.info(f"Using HTML content from {html_path}")
            
            # Ensure we have the exit button
            html_content = ensure_exit_button(html_content)
        except Exception as ex:
            logger.error(f"Error reading HTML file: {ex}")
            logger.info("Using default HTML content instead")
    
    return html_content

def ensure_exit_button(html_content):
    """Ensure the HTML content has an exit button."""
    exit_button = """
<button id="exit-app-button" style="position: fixed; bottom: 20px; right: 20px; background-color: #f44336; color: white; padding: 10px 20px; border-radius: 5px; border: none; cursor: pointer; z-index: 9999;">Exit App</button>
"""
    exit_styles = """
<style>
#exit-app-button:hover {
    background-color: #d32f2f;
}
.exit-confirmation {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
}
.exit-confirmation-box {
    background-color: white;
    padding: 20px;
    border-radius: 5px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
}
.exit-confirmation-buttons {
    margin-top: 20px;
}
.exit-confirmation-buttons button {
    padding: 8px 16px;
    margin: 0 10px;
    border-radius: 4px;
    border: none;
    cursor: pointer;
}
.exit-cancel {
    background-color: #e0e0e0;
}
.exit-confirm {
    background-color: #f44336;
    color: white;
}
</style>
"""
    exit_confirmation = """
<div class="exit-confirmation" id="exit-confirmation" style="display: none;">
    <div class="exit-confirmation-box">
        <h2>Confirm Exit</h2>
        <p>Are you sure you want to exit the application?</p>
        <div class="exit-confirmation-buttons">
            <button class="exit-cancel" id="exit-cancel">Cancel</button>
            <button class="exit-confirm" id="exit-confirm">Exit</button>
        </div>
    </div>
</div>
"""
    exit_script = """
<script>
// Exit button handler with confirmation
document.addEventListener('DOMContentLoaded', function() {
    // Add exit confirmation if not present
    if (!document.getElementById('exit-confirmation')) {
        const exitConfirmationHTML = `
            <div class="exit-confirmation" id="exit-confirmation" style="display: none;">
                <div class="exit-confirmation-box">
                    <h2>Confirm Exit</h2>
                    <p>Are you sure you want to exit the application?</p>
                    <div class="exit-confirmation-buttons">
                        <button class="exit-cancel" id="exit-cancel">Cancel</button>
                        <button class="exit-confirm" id="exit-confirm">Exit</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', exitConfirmationHTML);
    }

    // Ensure exit button exists
    if (!document.getElementById('exit-app-button')) {
        var exitButton = document.createElement('button');
        exitButton.id = 'exit-app-button';
        exitButton.innerHTML = 'Exit App';
        exitButton.style.position = 'fixed';
        exitButton.style.bottom = '20px';
        exitButton.style.right = '20px';
        exitButton.style.backgroundColor = '#f44336';
        exitButton.style.color = 'white';
        exitButton.style.padding = '10px 20px';
        exitButton.style.borderRadius = '5px';
        exitButton.style.border = 'none';
        exitButton.style.cursor = 'pointer';
        exitButton.style.zIndex = '9999';
        document.body.appendChild(exitButton);
    }
    
    // Handle exit button click
    document.getElementById('exit-app-button').addEventListener('click', function() {
        document.getElementById('exit-confirmation').style.display = 'flex';
    });
    
    // Cancel exit
    document.getElementById('exit-cancel').addEventListener('click', function() {
        document.getElementById('exit-confirmation').style.display = 'none';
    });
    
    // Confirm exit
    document.getElementById('exit-confirm').addEventListener('click', function() {
        document.getElementById('exit-confirmation').style.display = 'none';
        
        // Show loading indicator
        const loadingHTML = `
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                      background-color: rgba(255,255,255,0.9); z-index: 10000;
                      display: flex; flex-direction: column; 
                      justify-content: center; align-items: center;">
                <h1>Shutting down...</h1>
                <p>Please wait while the application closes.</p>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', loadingHTML);
        
        // Send exit request to server
        fetch('/exit', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Exit-Requested-By': 'user-interface'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Server responded with an error');
            }
            document.body.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;"><h1>Server shutdown. You can close this window.</h1></div>';
        })
        .catch(err => {
            alert('Error shutting down: ' + err);
        });
    });
});

// Set up the tab close/refresh detector
window.addEventListener('beforeunload', function(e) {
    // Add server shutdown call when tab is closed or refreshed
    const exitBeacon = new Image();
    exitBeacon.src = '/exit?auto_close=true&t=' + new Date().getTime();
    
    // Use sendBeacon for more reliable shutdown when page unloads
    navigator.sendBeacon('/exit', JSON.stringify({
        reason: 'tab_closed',
        timestamp: new Date().toISOString()
    }));
    
    // No need to show a confirmation dialog
    return undefined;
});

// Function to detect iOS version
function getIOSVersion() {
    if (/iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream) {
        const match = navigator.userAgent.match(/OS (\\\\d+)_(\\\\d+)_?(\\\\d+)?/);
        return match ? {
            major: parseInt(match[1], 10),
            minor: parseInt(match[2], 10),
            patch: parseInt(match[3] || 0, 10)
        } : null;
    }
    return null;
}
</script>
"""
    
    # Add styles to head if needed
    if "<head>" in html_content and "</head>" in html_content and "exit-confirmation" not in html_content:
        html_content = html_content.replace("</head>", exit_styles + "</head>")
    
    # Add to HTML content
    modified_content = html_content
    
    # Add exit confirmation dialog
    if "</body>" in modified_content and "exit-confirmation" not in modified_content:
        modified_content = modified_content.replace("</body>", exit_confirmation + "</body>")
    
    # Add exit button if needed
    if "exit-app-button" not in modified_content and "</body>" in modified_content:
        modified_content = modified_content.replace("</body>", exit_button + "</body>")
    
    # Add exit script for functionality
    if "</body>" in modified_content:
        modified_content = modified_content.replace("</body>", exit_script + "</body>")
    
    return modified_content