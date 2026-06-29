let _selectedAssignmentId = null;
let _pollHandle = null;
let _selectedFiles = [];

window.onload = function () {
    if (!requireAuth()) return;
    fillSharedChrome();
    loadDoneAssignments();

    document.getElementById("studentFiles").addEventListener("change", handleFilesSelected);

    const dropZone = document.getElementById("dropZone");
    dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("bg-gray-100"); });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("bg-gray-100"));
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("bg-gray-100");
        const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith(".pdf"));
        setFiles(files);
    });
};

async function loadDoneAssignments() {
    const user_id = localStorage.getItem("user_id");
    const select = document.getElementById("assignmentSelect");

    try {
        const res = await apiFetch(`/assignments/dashboard/${user_id}`, { headers: authHeaders() });
        const assignments = await res.json();
        const done = assignments.filter(a => a.status === "DONE");

        if (done.length === 0) {
            select.innerHTML = `<option value="">No completed assignments found — generate one first</option>`;
            return;
        }

        select.innerHTML = `<option value="">Select an assignment...</option>` +
            done.map(a => `<option value="${a.id}">${a.title} (Due: ${formatDate(a.due_date)})</option>`).join("");
    } catch (e) {
        select.innerHTML = `<option value="">Could not load assignments</option>`;
    }
}

function handleFilesSelected() {
    const files = Array.from(document.getElementById("studentFiles").files);
    setFiles(files);
}

function setFiles(files) {
    _selectedFiles = files;
    const fileList = document.getElementById("fileList");

    if (files.length === 0) {
        fileList.classList.add("hidden");
        document.getElementById("dropZoneText").innerText = "Choose student PDFs or drag & drop";
        return;
    }

    document.getElementById("dropZoneText").innerText = `📎 ${files.length} file${files.length > 1 ? "s" : ""} selected`;
    fileList.classList.remove("hidden");
    fileList.innerHTML = files.map(f => {
        const studentName = f.name.replace(".pdf", "").replace(/_/g, " ").replace(/-/g, " ");
        return `
            <div class="flex items-center gap-3 bg-[#F9FAFB] border border-[#E5E7EB] px-4 py-2.5 rounded-xl">
                <span class="text-base">📄</span>
                <div class="flex-1 min-w-0">
                    <p class="text-xs font-bold text-[#1A1A1A] truncate">${studentName}</p>
                    <p class="text-[11px] text-gray-400">${f.name} · ${(f.size / 1024).toFixed(0)} KB</p>
                </div>
                <span class="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">Queued</span>
            </div>
        `;
    }).join("");
}

function showError(msg) {
    const b = document.getElementById("errorBanner");
    b.innerText = msg;
    b.classList.remove("hidden");
}

function clearError() {
    document.getElementById("errorBanner").classList.add("hidden");
}

async function submitEvaluation() {
    clearError();
    const assignmentId = document.getElementById("assignmentSelect").value;
    if (!assignmentId) return showError("Please select an assignment first.");
    if (_selectedFiles.length === 0) return showError("Please upload at least one student PDF.");

    _selectedAssignmentId = assignmentId;

    const btn = document.getElementById("submitBtn");
    const btnText = document.getElementById("submitBtnText");
    btn.disabled = true;
    btn.classList.add("opacity-60", "cursor-not-allowed");
    btnText.innerText = "Uploading student PDFs...";

    const formData = new FormData();
    _selectedFiles.forEach(f => formData.append("files", f));

    try {
        const res = await fetch(`${API}/evaluations/submit/${assignmentId}`, {
            method: "POST",
            headers: authHeadersNoContentType(),
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Upload failed");
        }

        const data = await res.json();
        document.getElementById("progressSection").classList.remove("hidden");
        document.getElementById("progTotal").innerText = data.submitted;
        btnText.innerText = "✅ Uploaded — grading in progress...";

        _pollHandle = setInterval(() => pollProgress(assignmentId), 3000);

    } catch (e) {
        showError(e.message);
        btn.disabled = false;
        btn.classList.remove("opacity-60", "cursor-not-allowed");
        btnText.innerText = "🚀 Start AI Evaluation";
    }
}

async function pollProgress(assignmentId) {
    try {
        const res = await apiFetch(`/evaluations/${assignmentId}/status`, { headers: authHeaders() });
        const data = await res.json();

        const total = data.total || 1;
        const done = data.summary?.DONE || 0;
        const pending = data.summary?.PENDING || 0;
        const processing = data.summary?.PROCESSING || 0;

        document.getElementById("progDone").innerText = done;
        document.getElementById("progPending").innerText = pending;
        document.getElementById("progProcessing").innerText = processing;
        document.getElementById("progressBar").style.width = `${Math.round((done / total) * 100)}%`;

        if (data.all_done && done > 0) {
            clearInterval(_pollHandle);
            document.getElementById("allDoneSection").classList.remove("hidden");
        }
    } catch (e) {
        console.warn("Poll error:", e.message);
    }
}

function goToResults() {
    window.location.href = `results.html?id=${_selectedAssignmentId}`;
}