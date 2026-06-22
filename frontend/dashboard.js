window.onload = function () {
    if (!requireAuth()) return;

    fillSharedChrome();

    const user_id = localStorage.getItem("user_id");

    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        let debounceHandle = null;
        searchInput.addEventListener("input", (e) => {
            clearTimeout(debounceHandle);
            debounceHandle = setTimeout(() => search(e.target.value), 300);
        });
    }

    loadDashboard(user_id);
};

async function loadDashboard(user_id) {
    const main = document.querySelector("main");
    const emptyStateSection = main ? main.querySelector("section") : null;

    try {
        const res = await apiFetch(`/assignments/dashboard/${user_id}`, {
            method: "GET",
            headers: authHeaders()
        });
        const assignments = await res.json();

        if (!assignments || assignments.length === 0) {
            return;
        }

        if (emptyStateSection) {
            renderRecentAssignments(emptyStateSection, assignments.slice(0, 4));
        }
    } catch (e) {
        console.error("Could not load dashboard:", e.message);
    }
}

function renderRecentAssignments(container, assignments) {
    const statusBadge = (status) => {
        const map = {
            DONE: { label: "Ready", classes: "bg-green-50 text-green-700" },
            PROCESSING: { label: "Generating…", classes: "bg-blue-50 text-blue-700" },
            PENDING: { label: "Queued", classes: "bg-amber-50 text-amber-700" },
            FAILED: { label: "Failed", classes: "bg-red-50 text-red-700" },
        };
        const s = map[status] || map.PENDING;
        return `<span class="${s.classes} text-[10px] font-bold px-2 py-1 rounded-md">${s.label}</span>`;
    };

    container.outerHTML = `
        <section class="bg-white rounded-3xl flex-1 flex flex-col p-6 shadow-xs border border-[#F3F4F6]">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-bold text-[#1A1A1A] tracking-tight">Recent Assignments</h2>
                <a href="assignment.html" class="text-xs font-semibold text-gray-500 hover:text-black transition">View all →</a>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                ${assignments.map(a => `
                    <a href="assignment_output.html?id=${a.id}" class="border border-[#F3F4F6] rounded-2xl p-4 flex flex-col gap-2 hover:shadow-md transition">
                        <div class="flex justify-between items-start gap-2">
                            <h3 class="text-sm font-bold text-[#1A1A1A] leading-snug">${a.title}</h3>
                            ${statusBadge(a.status)}
                        </div>
                        <p class="text-[11px] text-gray-400">Due: ${formatDate(a.due_date)}</p>
                    </a>
                `).join("")}
            </div>
        </section>
    `;
}

async function search(query) {
    const school_id = localStorage.getItem("school_id");
    if (!query) return;

    try {
        const res = await apiFetch(
            `/assignments/search?school_id=${school_id}&query=${encodeURIComponent(query)}`,
            { method: "GET", headers: authHeaders() }
        );
        const data = await res.json();
        console.log("Search results:", data);
    } catch (e) {
        console.error("Search failed:", e.message);
    }
}