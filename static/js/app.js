document.addEventListener("DOMContentLoaded", () => {
    
    // --- Dashboard Logic ---
    const overlay = document.getElementById('emergency-overlay');
    const logList = document.getElementById('log-list');
    
    let emergencyTimeout = null;

    function activateEmergency(laneNumber, timestamp, message = "AMBULANCE DETECTED") {
        // Highlight specific lane
        const specificLane = document.getElementById(`lane-${laneNumber}`);
        if(specificLane) {
            specificLane.classList.add('emergency');
            
            // Update Priority Indicator
            const indicator = document.getElementById(`priority-${laneNumber}`);
            if(indicator) indicator.textContent = "PRIORITY";

            // Update the overlay text if provided
            const overlayText = specificLane.querySelector('.lane-alert-overlay');
            if(overlayText && message) {
                overlayText.textContent = message;
            }
        }

        // Add Log Entry
        const li = document.createElement('li');
        li.className = 'log-entry alert-entry';
        li.innerHTML = `
            <span class="timestamp">${timestamp}</span>
            <span class="entry-msg">${message}</span>
        `;
        // Prepend to show newest at top
        logList.insertBefore(li, logList.firstChild);

        // Limit log entries to last 50
        if (logList.children.length > 50) {
            logList.removeChild(logList.lastChild);
        }

        // Auto-disable emergency mode after 8 seconds of no detections
        // Each lane can have its own independent timer now
        setTimeout(() => {
            if(specificLane) {
                specificLane.classList.remove('emergency');
                const indicator = document.getElementById(`priority-${laneNumber}`);
                if(indicator) indicator.textContent = "NORMAL";
            }
        }, 8000);
    }

    // Connect to FastAPI WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    console.log("Connecting to WebSocket:", wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'alert' && data.lane) {
                activateEmergency(data.lane, data.timestamp, data.message);
            }
        } catch (e) {
            console.error("Failed to parse WS message:", e);
        }
    };

    ws.onopen = () => {
        console.log("WebSocket connected.");
        const li = document.createElement('li');
        li.className = 'log-entry normal-entry';
        li.innerHTML = `
            <span class="timestamp">${new Date().toLocaleTimeString()}</span>
            <span class="entry-msg">WebSocket Connected. Monitoring Streams...</span>
        `;
        logList.insertBefore(li, logList.firstChild);
    };

    ws.onclose = () => {
        console.log("WebSocket disconnected.");
        const li = document.createElement('li');
        li.className = 'log-entry alert-entry';
        li.innerHTML = `
            <span class="timestamp">${new Date().toLocaleTimeString()}</span>
            <span class="entry-msg">CONNECTION LOST. Attempting Reconnect...</span>
        `;
        logList.insertBefore(li, logList.firstChild);
        // Simple reconnect logic
        setTimeout(() => window.location.reload(), 5000);
    };
});
