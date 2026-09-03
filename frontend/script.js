const API = (window.location.port === "8000" || !window.location.port) && window.location.protocol.startsWith("http")
    ? window.location.origin
    : `${window.location.protocol.startsWith("http") ? window.location.protocol : "http:"}//${window.location.hostname || "127.0.0.1"}:8000`;

const navItems = document.querySelectorAll(".nav-item");
const sections = document.querySelectorAll(".section");
const pageTitle = document.getElementById("page-title");

navItems.forEach(button => {
    button.addEventListener("click", () => {
        const target = button.dataset.section;

        navItems.forEach(item => item.classList.remove("active"));
        button.classList.add("active");

        sections.forEach(section => {
            section.classList.toggle("active", section.id === target);
        });

        pageTitle.textContent = button.textContent.trim();

        if (target === "events") {
            loadEvents("all-events");
        } else if (target === "devices") {
            loadDevices();
        } else if (target === "logs") {
            loadLogHistory();
        }
    });
});

async function api(path) {
    const response = await fetch(API + path);

    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
    }

    return response.json();
}

async function loadHealth() {
    try {
        const data = await api("/api/health");

        document.getElementById("system-status").textContent =
            String(data.status || "ONLINE").toUpperCase();

        if (data.model) {
            document.getElementById("model-name").textContent = data.model;
            document.getElementById("ml-model").textContent = data.model;
        }
    } catch (error) {
        document.getElementById("system-status").textContent = "OFFLINE";
        document.getElementById("system-status").style.color = "var(--red)";
        console.error("Health error:", error);
    }
}

async function loadStats() {
    try {
        const data = await api("/api/stats");

        const values = [
            ["total-queries", data.total_queries ?? data.total ?? "—"],
            ["blocked", data.blocked ?? data.blocked_queries ?? "—"],
            ["ml-detections", data.ml_detections ?? data.ml ?? "—"]
        ];

        values.forEach(([id, value]) => {
            document.getElementById(id).textContent = value;
        });

        if (data.model) {
            document.getElementById("model-name").textContent = data.model;
            document.getElementById("ml-model").textContent = data.model;
        }
    } catch (error) {
        console.error("Stats error:", error);
    }
}

function renderEvents(events, containerId = "event-list") {
    const container = document.getElementById(containerId);

    if (!container) return;

    if (!Array.isArray(events) || events.length === 0) {
        container.innerHTML = '<div class="empty">No DNS events available.</div>';
        return;
    }

    container.innerHTML = events.slice(-10).reverse().map(event => {
        const domain = event.domain || "unknown";
        const verdict = event.verdict || "ALLOW";
        const detection = event.detection || event.reason || "—";
        const timestamp = event.timestamp
            ? new Date(event.timestamp).toLocaleString()
            : "—";

        return `
            <div class="event">
                <div>
                    <div class="event-domain">${escapeHtml(domain)}</div>
                    <div class="event-meta">${escapeHtml(timestamp)} · ${escapeHtml(detection)}</div>
                </div>
                <span class="badge ${escapeHtml(verdict)}">${escapeHtml(verdict)}</span>
            </div>
        `;
    }).join("");
}

async function loadEvents(containerId = "event-list") {
    try {
        const possibleEndpoints = [
            "/api/events",
            "/api/dns/events",
            "/api/logs"
        ];

        for (const endpoint of possibleEndpoints) {
            try {
                const data = await api(endpoint);

                const events =
                    Array.isArray(data) ? data :
                    data.events || data.items || data.logs || [];

                if (Array.isArray(events)) {
                    renderEvents(events, containerId);
                    return;
                }
            } catch (_) {
                // Try the next endpoint.
            }
        }

        renderEvents([], containerId);

    } catch (error) {
        console.error("Events error:", error);
        renderEvents([], containerId);
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function initialize() {
    await Promise.all([
        loadHealth(),
        loadStats(),
        loadEvents()
    ]);

    const logSearch = document.getElementById("log-search");
    const verdictFilter = document.getElementById("log-verdict-filter");
    const btnReset = document.getElementById("btn-reset-filters");
    
    if (logSearch) logSearch.addEventListener("input", renderFilteredLogs);
    if (verdictFilter) verdictFilter.addEventListener("change", renderFilteredLogs);
    if (btnReset) {
        btnReset.addEventListener("click", () => {
            logSearch.value = "";
            verdictFilter.value = "";
            renderFilteredLogs();
        });
    }
}

initialize();

setInterval(loadHealth, 10000);
setInterval(loadStats, 5000);
setInterval(loadEvents, 5000);
setInterval(() => {
    const activeSection = document.querySelector(".section.active");
    if (activeSection) {
        if (activeSection.id === "devices") {
            loadDevices();
        } else if (activeSection.id === "logs") {
            loadLogHistory();
        }
    }
}, 5000);

let cachedLogs = [];

async function loadDevices() {
    const container = document.getElementById("connected-devices-list");
    if (!container) return;
    
    try {
        const data = await api("/api/devices");
        const devices = Array.isArray(data) ? data : data.devices || [];
        
        if (devices.length === 0) {
            container.innerHTML = '<div class="empty">No connected devices available.</div>';
            return;
        }
        
        container.innerHTML = devices.map(device => {
            const name = device.device_name || "DHCP Device";
            const ip = device.ip || "—";
            const status = device.status || "offline";
            const lastActive = device.last_active ? new Date(device.last_active).toLocaleString() : "—";
            const statusBadgeClass = status === "online" ? "ALLOW" : status === "idle" ? "MONITOR" : "BLOCK";
            
            return `
                <div class="event">
                    <div>
                        <div class="event-domain" style="font-size: 14px; font-weight: bold; color: var(--accent);">${escapeHtml(name)}</div>
                        <div class="event-meta" style="font-size: 11px; margin-top: 4px; color: var(--muted);">
                            IP: <strong>${escapeHtml(ip)}</strong> &middot; 
                            Last Active: ${escapeHtml(lastActive)} &middot; 
                            Queries: <strong>${device.total_queries}</strong> &middot; 
                            Threats Blocked: <span style="color: ${device.threats_blocked > 0 ? 'var(--red)' : 'var(--green)'}; font-weight: bold;">${device.threats_blocked}</span>
                        </div>
                    </div>
                    <span class="badge ${statusBadgeClass}">${status.toUpperCase()}</span>
                </div>
            `;
        }).join("");
    } catch (error) {
        console.error("Devices error:", error);
        container.innerHTML = '<div class="empty">Failed to load connected devices.</div>';
    }
}

async function loadLogHistory() {
    const container = document.getElementById("log-history-list");
    if (!container) return;
    
    try {
        const data = await api("/api/logs");
        cachedLogs = Array.isArray(data) ? data : data.events || data.items || data.logs || [];
        renderFilteredLogs();
    } catch (error) {
        console.error("Log history error:", error);
        container.innerHTML = '<div class="empty">Failed to load log history.</div>';
    }
}

function renderFilteredLogs() {
    const container = document.getElementById("log-history-list");
    if (!container) return;
    
    const searchVal = document.getElementById("log-search") ? document.getElementById("log-search").value.toLowerCase().trim() : "";
    const verdictVal = document.getElementById("log-verdict-filter") ? document.getElementById("log-verdict-filter").value : "";
    
    const filtered = cachedLogs.filter(log => {
        const matchesSearch = !searchVal || 
            (log.domain && log.domain.toLowerCase().includes(searchVal)) || 
            (log.source_ip && log.source_ip.toLowerCase().includes(searchVal));
        const matchesVerdict = !verdictVal || log.verdict === verdictVal;
        return matchesSearch && matchesVerdict;
    });
    
    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty">No logs match your filter criteria.</div>';
        return;
    }
    
    container.innerHTML = filtered.map(log => {
        const domain = log.domain || "unknown";
        const queryType = log.query_type || "A";
        const ip = log.source_ip || "—";
        const protocol = log.protocol || "UDP";
        const verdict = log.verdict || "ALLOW";
        const severity = log.severity || "INFORMATIONAL";
        const reason = log.reason || "Normal traffic";
        const time = log.timestamp ? new Date(log.timestamp).toLocaleString() : "—";
        
        return `
            <div class="event">
                <div>
                    <div class="event-domain">${escapeHtml(domain)} (${escapeHtml(queryType)})</div>
                    <div class="event-meta">
                        Time: ${escapeHtml(time)} &middot; 
                        Source: <strong>${escapeHtml(ip)}</strong> &middot; 
                        Protocol: <strong>${escapeHtml(protocol)}</strong> &middot; 
                        Risk Score: <strong>${((log.risk_score || 0) * 100).toFixed(1)}%</strong> &middot; 
                        Severity: <span style="font-weight: bold; color: ${severity === 'CRITICAL' || severity === 'HIGH' ? 'var(--red)' : severity === 'MEDIUM' ? 'var(--yellow)' : 'var(--muted)'}">${escapeHtml(severity)}</span> &middot; 
                        Details: ${escapeHtml(reason)}
                    </div>
                </div>
                <span class="badge ${verdict}">${escapeHtml(verdict)}</span>
            </div>
        `;
    }).join("");
}
