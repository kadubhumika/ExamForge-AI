window.onload = function () {
    if (!requireAuth()) return;
    fillSharedChrome();

    const user_id = localStorage.getItem("user_id");
    loadLibrary(user_id);

    document.getElementById("librarySearch").addEventListener("input", applyFilters);
    document.getElementById("filterStatus").addEventListener("change", applyFilters);
    document.getElementById("sortOrder").addEventListener("change", applyFilters);
};

let _libraryItems = [];

async function loadLibrary(user_id) {
    const grid = document.getElementById("libraryGrid");
    grid.innerHTML = `<p class="text-xs text-gray-400 col-span-2 text-center py-10">Loading your library…</p>`;

    try {
        const res = await apiFetch(`/assignments/my-library/${user_id}`, {
            method: "GET",
            headers: authHeaders()
        });
        const data = await res.json();

        document.getElementById("statTotal").innerText = data.total_count;
        document.getElementById("statCompleted").innerText = data.completed_count;
        document.getElementById("statPending").innerText = data.pending_count;

        _libraryItems = data.items || [];
        applyFilters();
    } catch (e) {
        grid.innerHTML = `<p class="text-xs text-red-400 col-span-2 text-center py-10">Could not load library: ${e.message}</p>`;
    }
}

function applyFilters() {
    const query = document.getElementById("librarySearch").value.trim().toLowerCase();
    const statusFilter = document.getElementById("filterStatus").value;
    const sortOrder = document.getElementById("sortOrder").value;

    let items = [..._libraryItems];

    if (query) {
        items = items.filter(i => i.title.toLowerCase().includes(query));
    }
    if (statusFilter === "completed") {
        items = items.filter(i => i.is_completed);
    } else if (statusFilter === "pending") {
        items = items.filter(i => !i.is_completed);
    }

    if (sortOrder === "newest") {
        items.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    } else if (sortOrder === "oldest") {
        items.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    } else if (sortOrder === "due") {
        items.sort((a, b) => new Date(a.due_date || 0) - new Date(b.due_date || 0));
    }

    renderLibraryCards(items);
}

function renderLibraryCards(items) {
    const grid = document.getElementById("libraryGrid");

    if (!items || items.length === 0) {
        grid.innerHTML = `
            <div class="col-span-2 bg-white rounded-3xl flex flex-col items-center justify-center p-10 text-center shadow-xs border border-[#F3F4F6] min-h-[300px]">
                <div class="text-4xl mb-4 select-none">📚</div>
                <h2 class="text-xl font-bold text-[#111827] mb-2 tracking-tight">No assignments in your library yet</h2>
                <p class="text-xs text-[#6B7280] leading-relaxed max-w-[440px] mb-6">
                    Create your first assignment to start building your library.
                </p>
                <a href="create_assignment.html" class="bg-[#111827] hover:bg-black text-white px-5 py-2.5 rounded-xl font-semibold text-xs flex items-center gap-2 cursor-pointer shadow-md transition">
                    <span>➕</span> Create Assignment
                </a>
            </div>
        `;
        return;
    }

    grid.innerHTML = items.map(item => {
        const badge = item.is_completed
            ? `<span class="bg-green-50 text-green-700 text-[10px] font-bold px-2 py-1 rounded-md shrink-0 flex items-center gap-1"><span>✅</span> Completed</span>`
            : `<span class="bg-amber-50 text-amber-700 text-[10px] font-bold px-2 py-1 rounded-md shrink-0 flex items-center gap-1"><span>⏳</span> ${item.status === 'PROCESSING' ? 'Generating' : item.status === 'FAILED' ? 'Failed' : 'Pending'}</span>`;

        const downloadBtn = item.status === "DONE"
            ? `<button onclick="downloadAssignment('${item.assignment_id}')" class="bg-[#F3F4F6] hover:bg-[#E5E7EB] text-[#1A1A1A] font-semibold text-xs px-3 py-1.5 rounded-lg transition cursor-pointer">Download</button>`
            : `<button disabled class="bg-[#F3F4F6] text-gray-300 font-semibold text-xs px-3 py-1.5 rounded-lg cursor-not-allowed">Download</button>`;

        return `
        <div class="bg-white border border-[#F3F4F6] p-5 rounded-2xl shadow-xs flex flex-col justify-between gap-4 transition hover:shadow-md">
            <div class="flex justify-between items-start gap-2">
                <div class="flex gap-2.5 items-start">
                    <span class="text-xl mt-0.5 shrink-0">📄</span>
                    <div>
                        <h3 class="text-base font-bold text-[#1A1A1A] tracking-tight leading-snug">${item.title}</h3>
                        <p class="text-[11px] text-[#828282] mt-0.5">Created: ${formatDate(item.created_at)}</p>
                    </div>
                </div>
                ${badge}
            </div>

            <div class="flex items-center justify-between border-t border-gray-50 pt-3 mt-1">
                <span class="text-xs text-[#6B7280]">Due: <strong class="font-bold text-[#1A1A1A]">${formatDate(item.due_date)}</strong></span>
                <div class="flex gap-1.5">
                    <button onclick="window.location.href='assignment_output.html?id=${item.assignment_id}'" class="bg-[#F3F4F6] hover:bg-[#E5E7EB] text-[#1A1A1A] font-semibold text-xs px-3 py-1.5 rounded-lg transition cursor-pointer">View</button>
                    ${downloadBtn}
                    <button onclick="deleteLibraryItem('${item.assignment_id}')" class="hover:bg-red-50 text-red-500 font-semibold text-xs px-3 py-1.5 rounded-lg transition cursor-pointer">Delete</button>
                </div>
            </div>
        </div>
        `;
    }).join("");
}

async function downloadAssignment(id) {
    try {
        const res = await apiFetch(`/assignments/${id}/download`, {
            method: "GET",
            headers: authHeaders()
        });
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "assignment.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        alert(`Could not download: ${e.message}`);
    }
}

async function deleteLibraryItem(id) {
    if (!confirm("Delete this assignment? This cannot be undone.")) return;
    try {
        await apiFetch(`/assignments/${id}`, { method: "DELETE", headers: authHeaders() });
        _libraryItems = _libraryItems.filter(i => i.assignment_id !== id);
        applyFilters();
        document.getElementById("statTotal").innerText = _libraryItems.length;
        document.getElementById("statCompleted").innerText = _libraryItems.filter(i => i.is_completed).length;
        document.getElementById("statPending").innerText = _libraryItems.filter(i => !i.is_completed).length;
    } catch (e) {
        alert(`Could not delete: ${e.message}`);
    }
}