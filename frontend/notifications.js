// Wires up the 🔔 bell icon that appears in the header of every page.
// Expects a container with class "relative cursor-pointer ... text-lg" containing the bell emoji —
// matches the markup already present in every screen you shared.

let _notifPollHandle = null;

function findBellElement() {
    // The bell is the element whose text content starts with the bell emoji.
    const candidates = document.querySelectorAll("header .relative.cursor-pointer");
    for (const el of candidates) {
        if (el.textContent.includes("🔔")) return el;
    }
    return null;
}

function buildNotificationDropdown() {
    const dropdown = document.createElement("div");
    dropdown.id = "notifDropdown";
    dropdown.className =
        "hidden absolute right-0 top-9 bg-white border border-gray-100 shadow-xl rounded-2xl py-2 w-80 max-h-96 overflow-y-auto custom-scroll z-50 text-left";
    dropdown.innerHTML = `
        <div class="px-4 py-2 flex items-center justify-between border-b border-gray-50">
            <span class="text-xs font-bold text-[#1A1A1A]">Notifications</span>
            <button id="notifMarkAllRead" class="text-[10px] font-semibold text-gray-400 hover:text-black cursor-pointer">Mark all read</button>
        </div>
        <div id="notifList" class="flex flex-col"></div>
        <a href="notifications.html" class="block text-center text-[11px] font-semibold text-gray-400 hover:text-black py-2 border-t border-gray-50 transition">View all notifications</a>
    `;
    return dropdown;
}

const NOTIF_ICONS = {
    ASSIGNMENT_CREATED: "📝",
    ASSIGNMENT_READY: "✅",
    ASSIGNMENT_FAILED: "⚠️",
    ASSIGNMENT_DELETED: "🗑️",
    PROFILE_UPDATED: "👤",
    THEME_CHANGED: "🎨",
};

function timeAgo(isoString) {
    // Append Z if missing so JS treats it as UTC, not local time
    const normalized = isoString && !isoString.endsWith("Z")
        ? isoString + "Z"
        : isoString;
    const seconds = Math.floor((Date.now() - new Date(normalized).getTime()) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

async function renderNotifications() {
    const list = document.getElementById("notifList");
    if (!list) return;

    try {
        const res = await apiFetch("/notifications?limit=20", { headers: authHeaders() });
        const notifications = await res.json();

        const bellDot = document.getElementById("notifDot");
        const hasUnread = notifications.some(n => !n.is_read);
        if (bellDot) bellDot.classList.toggle("hidden", !hasUnread);

        if (notifications.length === 0) {
            list.innerHTML = `<div class="px-4 py-6 text-center text-xs text-gray-400">No notifications yet</div>`;
            return;
        }

        list.innerHTML = notifications.map(n => `
            <div class="px-4 py-2.5 flex items-start gap-2.5 hover:bg-gray-50 transition ${n.is_read ? "" : "bg-orange-50/40"}">
                <span class="text-base shrink-0">${NOTIF_ICONS[n.type] || "🔔"}</span>
                <div class="min-w-0">
                    <p class="text-xs font-bold text-[#1A1A1A] truncate">${n.title}</p>
                    <p class="text-[11px] text-gray-500 leading-snug">${n.message || ""}</p>
                    <p class="text-[10px] text-gray-400 mt-0.5">${timeAgo(n.created_at)}</p>
                </div>
            </div>
        `).join("");
    } catch (e) {
        list.innerHTML = `<div class="px-4 py-6 text-center text-xs text-gray-400">Could not load notifications</div>`;
    }
}

function initNotifications() {
    const bell = findBellElement();
    if (!bell) return;

    bell.style.position = "relative";

    // Tag the existing red dot span (already in the markup) so we can toggle it
    const existingDot = bell.querySelector("span.absolute");
    if (existingDot) {
        existingDot.id = "notifDot";
        existingDot.classList.add("hidden"); // start hidden until we know there's unread
    }

    const dropdown = buildNotificationDropdown();
    bell.appendChild(dropdown);

    bell.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown.classList.toggle("hidden");
        if (!dropdown.classList.contains("hidden")) {
            renderNotifications();
        }
    });

    document.addEventListener("click", () => dropdown.classList.add("hidden"));
    dropdown.addEventListener("click", (e) => e.stopPropagation());

    dropdown.querySelector("#notifMarkAllRead").addEventListener("click", async () => {
        try {
            await apiFetch("/notifications/read-all", { method: "PUT", headers: authHeaders() });
            renderNotifications();
        } catch (_) {}
    });

    // Initial check + light polling so the red dot appears without a refresh
    renderNotifications();
    _notifPollHandle = setInterval(renderNotifications, 15000);
}

document.addEventListener("DOMContentLoaded", () => {
    if (getToken()) initNotifications();
});