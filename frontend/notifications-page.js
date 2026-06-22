window.onload = function () {
    if (!requireAuth()) return;
    fillSharedChrome();
    loadNotificationPage();
};

async function loadNotificationPage() {
    const list = document.getElementById("notifPageList");
    list.innerHTML = `<p class="text-xs text-gray-400 text-center py-10">Loading…</p>`;

    try {
        const res = await apiFetch("/notifications?limit=100", { headers: authHeaders() });
        const notifications = await res.json();

        if (notifications.length === 0) {
            list.innerHTML = `<p class="text-xs text-gray-400 text-center py-10">No notifications yet</p>`;
            return;
        }

        list.innerHTML = notifications.map(n => `
            <div class="flex items-start gap-3 px-4 py-3 rounded-2xl ${n.is_read ? "" : "bg-orange-50/60"} hover:bg-gray-50 transition cursor-pointer" onclick="markRead('${n.id}', this)">
                <span class="text-lg shrink-0 mt-0.5">${NOTIF_ICONS[n.type] || "🔔"}</span>
                <div class="min-w-0 flex-1">
                    <p class="text-sm font-bold text-[#1A1A1A]">${n.title}</p>
                    <p class="text-xs text-gray-500 leading-snug mt-0.5">${n.message || ""}</p>
                    <p class="text-[11px] text-gray-400 mt-1">${timeAgo(n.created_at)}</p>
                </div>
                ${n.is_read ? "" : `<span class="w-2 h-2 bg-[#FF5A36] rounded-full mt-1.5 shrink-0"></span>`}
            </div>
        `).join("");
    } catch (e) {
        list.innerHTML = `<p class="text-xs text-red-400 text-center py-10">Could not load notifications: ${e.message}</p>`;
    }
}

async function markRead(id, el) {
    try {
        await apiFetch(`/notifications/${id}/read`, { method: "PUT", headers: authHeaders() });
        el.classList.remove("bg-orange-50/60");
        const dot = el.querySelector("span.bg-\\[\\#FF5A36\\]");
        if (dot) dot.remove();
    } catch (_) {}
}

async function markAllRead() {
    try {
        await apiFetch("/notifications/read-all", { method: "PUT", headers: authHeaders() });
        loadNotificationPage();
    } catch (e) {
        alert("Could not mark all as read");
    }
}