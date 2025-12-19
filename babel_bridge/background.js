// Babel Bridge - Background Service Worker
// Connects to local Python server and reports active design tools.

let socket = null;
const PORT = 6789;
const WS_URL = `ws://localhost:${PORT}`;
const RECONNECT_INTERVAL = 5000;

// Connect to the local Python server
function connect() {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log("Babel Bridge Connected to Desktop App");
        checkActiveTab(); // Immediate check on connect
    };

    socket.onclose = () => {
        console.log("Babel Bridge Disconnected. Retrying...");
        setTimeout(connect, RECONNECT_INTERVAL);
    };

    socket.onerror = (err) => {
        console.error("Babel Bridge Socket Error:", err);
        socket.close();
    };
}

// Check current tab on connect
function checkActiveTab() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs && tabs.length > 0) {
            const tab = tabs[0];
            if (tab.url) {
                const app = detectApp(tab.url);
                sendContext(app, tab.url);
            }
        }
    });
}

// Ensure connection starts
connect();

// Send payload to Python
function sendContext(app, url) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            event: "context_change",
            app: app,
            url: url
        }));
    }
}

// Determine app from URL
function detectApp(url) {
    if (!url) return "null";

    if (url.includes("figma.com/file") || url.includes("figma.com/design")) {
        return "figma";
    }
    if (url.includes("photoshop.adobe.com")) {
        return "photoshop";
    }
    // Add more web tools here if needed

    return "null";
}

// Listener for Tab Switching
chrome.tabs.onActivated.addListener(async (activeInfo) => {
    try {
        const tab = await chrome.tabs.get(activeInfo.tabId);
        if (tab.url) {
            const app = detectApp(tab.url);
            sendContext(app, tab.url);
        }
    } catch (e) {
        console.error("Error reading tab:", e);
    }
});

// Listener for URL Updates (e.g. navigation within Tab)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.active) {
        const app = detectApp(tab.url);
        sendContext(app, tab.url);
    }
});
