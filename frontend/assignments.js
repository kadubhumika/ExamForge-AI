window.onload = function () {
    if (!requireAuth()) return;
    fillSharedChrome();

    const user_id = localStorage.getItem("user_id");
    loadAssignments(user_id);

    const searchInput = document.querySelector('input[placeholder="Search Assignment"]');
    if (searchInput) {
        let debounceHandle = null;
        searchInput.addEventListener("input", (e) => {
            clearTimeout(debounceHandle);
            debounceHandle = setTimeout(() => filterCards(e.target.value), 250);
        });
    }
};

let _allAssignments = [];

async function loadAssignments(user_id) {
    const grid = document.querySelector("main .grid");
    if (!grid) return;

    grid.innerHTML = `<p class="text-xs text-gray-400 col-span-2 text-center py-10">Loading assignments…</p>`;

    try {
        const res = await apiFetch(`/assignments/dashboard/${user_id}`, {
            method: "GET",
            headers: authHeaders()
        });
        _allAssignments = await res.json();
        renderCards(_allAssignments);
    } catch (e) {
        grid.innerHTML = `<p class="text-xs text-red-400 col-span-2 text-center py-10">Could not load assignments: ${e.message}</p>`;
    }
}

function statusMeta(status) {
    const map = {
        DONE: { label: "Ready to view", color: "text-green-600" },
        PROCESSING: { label: "Generating…", color: "text-blue-500" },
        PENDING: { label: "Queued", color: "text-amber-500" },
        FAILED: { label: "Generation failed", color: "text-red-500" },
    };
    return map[status] || map.PENDING;
}

function renderCards(assignments) {
    const grid = document.querySelector("main .grid");
    if (!grid) return;

    if (!assignments || assignments.length === 0) {
        grid.innerHTML = `
            <div class="col-span-2 bg-white border border-[#F3F4F6] rounded-3xl p-10 text-center">
                <p class="text-sm font-bold text-[#1A1A1A] mb-1">No assignments yet</p>
                <p class="text-xs text-gray-400">Create your first assignment to see it here.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = assignments.map((a, i) => {
        const meta = statusMeta(a.status);
        return `
        <div class="bg-white border border-[#F3F4F6] p-6 rounded-3xl shadow-xs relative flex flex-col justify-between min-h-[140px]" data-id="${a.id}">
            <div class="flex justify-between items-start">
                <h3 class="text-lg font-bold text-[#1A1A1A] tracking-tight">${a.title}</h3>
                <button onclick="toggleActionMenu(event, 'menu-${i}')" class="text-gray-400 hover:text-black font-bold p-1 rounded-full cursor-pointer text-base leading-none select-none transition">⋮</button>
            </div>
            <div class="flex justify-between items-center text-xs text-[#4B5563] mt-6">
                <span class="font-semibold ${meta.color}">${meta.label}</span>
                <span>Due : <strong class="font-bold text-[#1A1A1A]">${formatDate(a.due_date)}</strong></span>
            </div>
            <div id="menu-${i}" class="hidden absolute right-6 top-12 bg-white border border-gray-100 shadow-xl rounded-xl py-1.5 w-36 z-50">
                <button onclick="viewAssignment('${a.id}')" class="w-full text-left px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2 cursor-pointer">👁️ View Assignment</button>
                <button onclick="deleteAssignment('${a.id}')" class="w-full text-left px-4 py-2 text-xs font-semibold text-red-500 hover:bg-red-50 flex items-center gap-2 cursor-pointer border-t border-gray-50">🗑️ Delete</button>
            </div>
        </div>
        `;
    }).join("");
}

function filterCards(query) {
    const q = query.trim().toLowerCase();
    if (!q) {
        renderCards(_allAssignments);
        return;
    }
    renderCards(_allAssignments.filter(a => a.title.toLowerCase().includes(q)));
}

function viewAssignment(id) {
    window.location.href = `assignment_output.html?id=${id}`;
}

async function deleteAssignment(id) {
    if (!confirm("Delete this assignment? This cannot be undone.")) return;

    try {
        await apiFetch(`/assignments/${id}`, {
            method: "DELETE",
            headers: authHeaders()
        });
        _allAssignments = _allAssignments.filter(a => a.id !== id);
        renderCards(_allAssignments);
    } catch (e) {
        alert(`Could not delete assignment: ${e.message}`);
    }
}

function toggleActionMenu(event, menuId) {
    event.stopPropagation();
    const openMenus = document.querySelectorAll('[id^="menu-"]');
    openMenus.forEach(menu => {
        if (menu.id !== menuId) menu.classList.add('hidden');
    });
    const target = document.getElementById(menuId);
    target.classList.toggle('hidden');
}

document.addEventListener('click', () => {
    const openMenus = document.querySelectorAll('[id^="menu-"]');
    openMenus.forEach(menu => menu.classList.add('hidden'));
});