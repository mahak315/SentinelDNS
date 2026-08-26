const API = "http://127.0.0.1:8000";

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
}

initialize();

setInterval(loadHealth, 10000);
setInterval(loadStats, 5000);
setInterval(loadEvents, 5000);
